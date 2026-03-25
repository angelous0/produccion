"""Fix: Agregar campos faltantes (curva, id_odoo, observaciones) y actualizar datos"""
import asyncio, asyncpg, pymysql, json
from datetime import datetime

MARIA_CONFIG = dict(host='72.60.241.216', port=8000, user='admin', password='Proyectomoda@04072001', database='proyecto_moda', connect_timeout=15)
PG_DSN = 'postgres://admin:admin@72.60.241.216:9090/datos?sslmode=disable'

async def get_conn():
    return await asyncpg.connect(PG_DSN, timeout=15, command_timeout=30)

async def main():
    # Read MariaDB data
    print("Leyendo MariaDB...")
    conn_m = pymysql.connect(**MARIA_CONFIG)
    cursor = conn_m.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT id, n_corte, id_odoo, glosa FROM registro')
    maria_regs = cursor.fetchall()
    print(f"  Registros MariaDB: {len(maria_regs)}")

    # Build n_corte -> data mapping (using id for unique mapping)
    # We need to map MariaDB id -> PG uuid via n_corte
    maria_by_id = {r['id']: r for r in maria_regs}

    conn_m.close()

    # ── 1. Agregar columnas si no existen ───────────────────────
    print("\nAgregando columnas...")
    conn = await get_conn()
    try:
        await conn.execute("ALTER TABLE produccion.prod_registros ADD COLUMN IF NOT EXISTS id_odoo VARCHAR(50)")
        print("  id_odoo: OK")
    except Exception as e:
        print(f"  id_odoo: {e}")

    try:
        await conn.execute("ALTER TABLE produccion.prod_registros ADD COLUMN IF NOT EXISTS observaciones TEXT")
        print("  observaciones: OK")
    except Exception as e:
        print(f"  observaciones: {e}")
    await conn.close()

    # ── 2. Generar curva desde tallas JSONB ─────────────────────
    print("\nGenerando curva desde tallas...")
    conn = await get_conn()
    rows = await conn.fetch("SELECT id, tallas FROM produccion.prod_registros WHERE tallas IS NOT NULL AND tallas != '[]'")
    print(f"  Registros con tallas: {len(rows)}")

    updated = 0
    BATCH = 50
    for i in range(0, len(rows), BATCH):
        batch = rows[i:i+BATCH]
        try:
            c = await get_conn()
            async with c.transaction():
                for r in batch:
                    tallas = json.loads(r['tallas']) if isinstance(r['tallas'], str) else r['tallas']
                    parts = []
                    for t in tallas:
                        nombre = t.get('talla_nombre', '')
                        cant = t.get('cantidad', 0)
                        if nombre and cant:
                            parts.append(f"{nombre}:{cant}")
                    curva = ", ".join(parts) if parts else ""
                    if curva:
                        await c.execute("UPDATE produccion.prod_registros SET curva = $1 WHERE id = $2", curva, r['id'])
                        updated += 1
            await c.close()
        except Exception as e:
            print(f"  Error batch curva: {e}")
            try: await c.close()
            except: pass

    await conn.close()
    print(f"  Curva actualizada: {updated} registros")

    # ── 3. Mapear MariaDB id -> PG uuid para id_odoo y glosa ───
    print("\nMapeando IDs MariaDB -> PostgreSQL...")
    # Strategy: match by n_corte + model (some n_cortes may repeat, but most are unique)
    # Actually, since we inserted in order, we can match by insertion order

    # Read all PG registros
    conn = await get_conn()
    pg_regs = await conn.fetch("SELECT id, n_corte FROM produccion.prod_registros ORDER BY fecha_creacion ASC")
    await conn.close()

    # Read MariaDB in same order
    conn_m = pymysql.connect(**MARIA_CONFIG)
    cursor = conn_m.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT id, n_corte, id_odoo, glosa FROM registro ORDER BY id ASC')
    maria_ordered = cursor.fetchall()
    conn_m.close()

    # Match by position (same insertion order)
    if len(pg_regs) == len(maria_ordered):
        print(f"  Match perfecto: {len(pg_regs)} registros")
    else:
        print(f"  WARN: PG={len(pg_regs)} vs MariaDB={len(maria_ordered)}")

    # ── 4. Actualizar id_odoo y observaciones ───────────────────
    print("\nActualizando id_odoo y observaciones...")
    count_odoo = 0
    count_obs = 0
    updates = []
    for i, pg_reg in enumerate(pg_regs):
        if i >= len(maria_ordered):
            break
        m = maria_ordered[i]
        id_odoo = m.get('id_odoo') or ''
        glosa = m.get('glosa') or ''
        if id_odoo or glosa:
            updates.append((pg_reg['id'], id_odoo if id_odoo else None, glosa if glosa else None))
            if id_odoo: count_odoo += 1
            if glosa: count_obs += 1

    # Execute in batches
    for i in range(0, len(updates), BATCH):
        batch = updates[i:i+BATCH]
        try:
            c = await get_conn()
            async with c.transaction():
                for uid, odoo, obs in batch:
                    if odoo and obs:
                        await c.execute("UPDATE produccion.prod_registros SET id_odoo = $1, observaciones = $2 WHERE id = $3", odoo, obs, uid)
                    elif odoo:
                        await c.execute("UPDATE produccion.prod_registros SET id_odoo = $1 WHERE id = $2", odoo, uid)
                    elif obs:
                        await c.execute("UPDATE produccion.prod_registros SET observaciones = $1 WHERE id = $2", obs, uid)
            await c.close()
        except Exception as e:
            print(f"  Error batch update: {e}")
            try: await c.close()
            except: pass

    print(f"  id_odoo: {count_odoo} actualizados")
    print(f"  observaciones: {count_obs} actualizados")

    print("\n" + "="*50)
    print("COMPLETADO")
    print("="*50)

if __name__ == '__main__':
    asyncio.run(main())
