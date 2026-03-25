"""Fix: Corregir campo curva en prod_registros usando datos reales de MariaDB tallas_produccion.curva"""
import asyncio, asyncpg, pymysql

MARIA_CONFIG = dict(host='72.60.241.216', port=8000, user='admin', password='Proyectomoda@04072001', database='proyecto_moda', connect_timeout=15)
PG_DSN = 'postgres://admin:admin@72.60.241.216:9090/datos?sslmode=disable'

async def main():
    # 1. Read curva from MariaDB tallas_produccion
    print("Leyendo curva real desde MariaDB tallas_produccion...")
    conn_m = pymysql.connect(**MARIA_CONFIG)
    cursor = conn_m.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute("""
        SELECT r.id as registro_id, r.n_corte,
               GROUP_CONCAT(tp.curva ORDER BY tp.id SEPARATOR '-') as curva_real
        FROM registro r
        JOIN tallas_produccion tp ON tp.id_registro = r.id
        WHERE tp.curva IS NOT NULL AND tp.curva > 0
        GROUP BY r.id, r.n_corte
        ORDER BY r.id ASC
    """)
    maria_curvas = cursor.fetchall()
    print(f"  Registros con curva en MariaDB: {len(maria_curvas)}")
    
    # Build mapping by n_corte
    curva_by_ncorte = {}
    for r in maria_curvas:
        # Clean curva: remove trailing .0 from floats like "2.0-4.0-4.0-2.0"
        curva = r['curva_real']
        if curva:
            parts = curva.split('-')
            clean_parts = []
            for p in parts:
                try:
                    val = float(p)
                    clean_parts.append(str(int(val)) if val == int(val) else p)
                except:
                    clean_parts.append(p)
            curva = '-'.join(clean_parts)
        curva_by_ncorte[r['n_corte']] = curva
    
    conn_m.close()
    
    # 2. Read PG registros
    print("\nLeyendo registros PostgreSQL...")
    conn = await asyncpg.connect(PG_DSN, timeout=15, command_timeout=30)
    pg_regs = await conn.fetch("SELECT id, n_corte, curva FROM produccion.prod_registros")
    await conn.close()
    print(f"  Total registros PG: {len(pg_regs)}")
    
    # 3. Match by n_corte and update
    updates = []
    for pg in pg_regs:
        ncorte = pg['n_corte']
        if ncorte in curva_by_ncorte:
            new_curva = curva_by_ncorte[ncorte]
            if new_curva and new_curva != pg['curva']:
                updates.append((pg['id'], new_curva))
    
    print(f"  Registros a actualizar: {len(updates)}")
    
    # Show first 5 changes
    for uid, curva in updates[:5]:
        pg_row = next(r for r in pg_regs if r['id'] == uid)
        print(f"    {pg_row['n_corte']}: \"{pg_row['curva']}\" -> \"{curva}\"")
    
    # 4. Execute updates in batches
    BATCH = 50
    updated = 0
    for i in range(0, len(updates), BATCH):
        batch = updates[i:i+BATCH]
        try:
            c = await asyncpg.connect(PG_DSN, timeout=15, command_timeout=30)
            async with c.transaction():
                for uid, curva in batch:
                    await c.execute("UPDATE produccion.prod_registros SET curva = $1 WHERE id = $2", curva, uid)
                    updated += 1
            await c.close()
        except Exception as e:
            print(f"  Error batch: {e}")
            try: await c.close()
            except: pass
    
    print(f"\n{'='*50}")
    print(f"Curva corregida: {updated} registros actualizados")
    
    # Verify specific record
    conn = await asyncpg.connect(PG_DSN, timeout=15, command_timeout=30)
    row = await conn.fetchrow("SELECT n_corte, curva FROM produccion.prod_registros WHERE n_corte = '046-2026'")
    if row:
        print(f"Verificacion 046-2026: curva = \"{row['curva']}\"")
    await conn.close()
    print(f"{'='*50}")

if __name__ == '__main__':
    asyncio.run(main())
