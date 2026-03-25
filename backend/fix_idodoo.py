"""Fix: Re-migrar id_odoo y glosa/observaciones usando matching por multiples campos"""
import asyncio, asyncpg, pymysql, json
from datetime import datetime

MARIA_CONFIG = dict(host='72.60.241.216', port=8000, user='admin', password='Proyectomoda@04072001', database='proyecto_moda', connect_timeout=15)
PG_DSN = 'postgres://admin:admin@72.60.241.216:9090/datos?sslmode=disable'

async def main():
    # 1. Read MariaDB records with all matching fields
    print("Leyendo MariaDB...")
    conn_m = pymysql.connect(**MARIA_CONFIG)
    cursor = conn_m.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute('''
        SELECT r.id, r.n_corte, r.id_odoo, r.glosa,
               r.id_modelo, r.id_hilo_especifico, r.id_estado,
               r.fecha_hora, r.urgencia,
               m.detalle as modelo_nombre,
               e.detalle as estado_nombre
        FROM registro r
        LEFT JOIN modelo m ON r.id_modelo = m.id
        LEFT JOIN estado e ON r.id_estado = e.id
        ORDER BY r.id ASC
    ''')
    maria_all = cursor.fetchall()
    
    # Also get tallas per registro for better matching
    cursor.execute('''
        SELECT tp.id_registro, 
               GROUP_CONCAT(CONCAT(t.detalle, ':', tp.cantidad) ORDER BY t.detalle SEPARATOR ',') as tallas_str,
               SUM(tp.cantidad) as total_prendas
        FROM tallas_produccion tp
        JOIN talla t ON tp.id_talla = t.id
        GROUP BY tp.id_registro
    ''')
    maria_tallas = {r['id_registro']: r for r in cursor.fetchall()}
    conn_m.close()
    
    print(f"  MariaDB registros: {len(maria_all)}")
    
    # 2. Read PG records
    print("Leyendo PostgreSQL...")
    conn = await asyncpg.connect(PG_DSN, timeout=15, command_timeout=60)
    pg_all = await conn.fetch('''
        SELECT r.id, r.n_corte, r.id_odoo, r.observaciones,
               r.modelo_id, r.hilo_especifico_id, r.estado, r.curva,
               r.fecha_creacion, r.urgente, r.tallas,
               m.nombre as modelo_nombre
        FROM produccion.prod_registros r
        LEFT JOIN produccion.prod_modelos m ON r.modelo_id = m.id
    ''')
    await conn.close()
    print(f"  PG registros: {len(pg_all)}")
    
    # 3. Build matching strategy
    # Strategy: match by (n_corte, modelo_nombre, total_prendas) as composite key
    # For NULL n_cortes, use (modelo_nombre, fecha, total_prendas)
    
    # Calculate total_prendas for PG records
    pg_records = []
    for pg in pg_all:
        tallas = json.loads(pg['tallas']) if isinstance(pg['tallas'], str) else (pg['tallas'] or [])
        total = sum(t.get('cantidad', 0) for t in tallas) if tallas else 0
        pg_records.append({
            'id': pg['id'],
            'n_corte': pg['n_corte'] or '',
            'modelo_nombre': (pg['modelo_nombre'] or '').upper(),
            'total_prendas': total,
            'fecha': pg['fecha_creacion'],
            'estado': pg['estado'] or '',
            'curva': pg['curva'] or '',
            'matched': False
        })
    
    # Build match indices
    updates = []
    matched_count = 0
    unmatched = []
    
    for m_rec in maria_all:
        nc = m_rec['n_corte'] or ''
        mod = (m_rec['modelo_nombre'] or '').upper()
        m_odoo = str(m_rec['id_odoo'] or '') if m_rec['id_odoo'] else None
        m_glosa = m_rec['glosa'] or None
        m_tallas = maria_tallas.get(m_rec['id'], {})
        m_total = m_tallas.get('total_prendas', 0) or 0
        m_fecha = m_rec['fecha_hora']
        m_estado = (m_rec['estado_nombre'] or '').replace('.', '').replace('_', ' ').strip()
        
        # Try to find matching PG record
        best_match = None
        best_score = 0
        
        for pg in pg_records:
            if pg['matched']:
                continue
            
            score = 0
            # n_corte match (strongest signal)
            if nc and pg['n_corte'] == nc:
                score += 10
            elif nc and pg['n_corte'] != nc:
                continue  # If both have n_corte but differ, skip
            
            # modelo match
            if mod and pg['modelo_nombre'] == mod:
                score += 5
            elif mod and pg['modelo_nombre'] != mod:
                continue  # Different model, skip
            
            # total prendas match
            if m_total > 0 and pg['total_prendas'] == m_total:
                score += 3
            
            # fecha match
            if m_fecha and pg['fecha']:
                try:
                    m_date = m_fecha.date() if hasattr(m_fecha, 'date') else m_fecha
                    pg_date = pg['fecha'].date() if hasattr(pg['fecha'], 'date') else pg['fecha']
                    if m_date == pg_date:
                        score += 2
                except:
                    pass
            
            # estado match
            if m_estado and pg['estado'] and m_estado.lower() in pg['estado'].lower():
                score += 1
            
            if score > best_score:
                best_score = score
                best_match = pg
        
        if best_match and best_score >= 5:
            best_match['matched'] = True
            matched_count += 1
            if m_odoo or m_glosa:
                updates.append((best_match['id'], m_odoo, m_glosa))
        else:
            if m_odoo or m_glosa:
                unmatched.append(f"MariaDB id={m_rec['id']}, nc={nc}, mod={mod}, odoo={m_odoo}")
    
    print(f"\nMatched: {matched_count}/{len(maria_all)}")
    print(f"Updates to apply: {len(updates)}")
    print(f"Unmatched with data: {len(unmatched)}")
    if unmatched[:3]:
        for u in unmatched[:3]:
            print(f"  {u}")
    
    # 4. Apply updates
    print("\nAplicando actualizaciones...")
    conn = await asyncpg.connect(PG_DSN, timeout=15, command_timeout=60)
    updated = 0
    for uid, odoo, glosa in updates:
        try:
            if odoo and glosa:
                await conn.execute("UPDATE produccion.prod_registros SET id_odoo = $1, observaciones = $2 WHERE id = $3", odoo, glosa, uid)
            elif odoo:
                await conn.execute("UPDATE produccion.prod_registros SET id_odoo = $1, observaciones = NULL WHERE id = $2", odoo, uid)
            elif glosa:
                await conn.execute("UPDATE produccion.prod_registros SET observaciones = $1 WHERE id = $2", glosa, uid)
            updated += 1
        except Exception as e:
            print(f"  Error: {e}")
            try: await conn.close()
            except: pass
            conn = await asyncpg.connect(PG_DSN, timeout=15, command_timeout=60)
    await conn.close()
    
    print(f"Actualizados: {updated}")
    
    # 5. Verify
    conn = await asyncpg.connect(PG_DSN, timeout=15, command_timeout=30)
    row = await conn.fetchrow("SELECT n_corte, id_odoo, observaciones FROM produccion.prod_registros WHERE n_corte = '046-2026'")
    if row:
        print(f"\nVerificacion 046-2026: id_odoo={row['id_odoo']}, obs={row['observaciones']}")
    await conn.close()
    
    print("\nCOMPLETADO")

if __name__ == '__main__':
    asyncio.run(main())
