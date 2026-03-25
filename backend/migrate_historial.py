"""Solo migrar historial (el resto ya está migrado)"""
import asyncio, asyncpg, pymysql, uuid, json
from datetime import datetime, date

MARIA_CONFIG = dict(host='72.60.241.216', port=8000, user='admin', password='Proyectomoda@04072001', database='proyecto_moda', connect_timeout=15)
PG_DSN = 'postgres://admin:admin@72.60.241.216:9090/datos?sslmode=disable'

def safe_datetime(val):
    if val is None or val == '':
        return datetime.now()
    s = str(val)
    if '0000' in s:
        return datetime.now()
    if isinstance(val, datetime):
        return val
    if isinstance(val, date):
        return datetime(val.year, val.month, val.day)
    return datetime.now()

async def get_conn():
    return await asyncpg.connect(PG_DSN, timeout=15, command_timeout=30)

async def main():
    # Read MariaDB
    conn_m = pymysql.connect(**MARIA_CONFIG)
    cursor = conn_m.cursor(pymysql.cursors.DictCursor)
    
    cursor.execute('SELECT * FROM historial_registro')
    historial = cursor.fetchall()
    print(f"Historial: {len(historial)}")
    
    cursor.execute('SELECT * FROM estado')
    estados = cursor.fetchall()
    estado_map = {e['ID']: (e['DETALLE'] or '').replace('.','').replace('_',' ').strip() for e in estados}
    
    conn_m.close()
    
    # Get registro_id mapping from PostgreSQL (n_corte -> id)
    conn_pg = await get_conn()
    
    # Build mapping: old registro id -> new uuid via n_corte
    # Read MariaDB registros for mapping
    conn_m = pymysql.connect(**MARIA_CONFIG)
    cursor = conn_m.cursor(pymysql.cursors.DictCursor)
    cursor.execute('SELECT id, n_corte FROM registro')
    maria_regs = {r['id']: str(r['n_corte']) for r in cursor.fetchall()}
    conn_m.close()
    
    # Read PostgreSQL registros
    pg_regs = await conn_pg.fetch("SELECT id, n_corte FROM produccion.prod_registros")
    ncorte_to_uuid = {r['n_corte']: r['id'] for r in pg_regs}
    await conn_pg.close()
    
    # Build old_id -> new_uuid mapping
    old_to_new = {}
    for old_id, ncorte in maria_regs.items():
        if ncorte in ncorte_to_uuid:
            old_to_new[old_id] = ncorte_to_uuid[ncorte]
    
    print(f"Mapped {len(old_to_new)} registros")
    
    # Clear existing historial
    c = await get_conn()
    await c.execute("DELETE FROM produccion.prod_actividad_historial")
    await c.close()
    
    # Insert in batches
    BATCH = 50
    done = 0
    params_all = []
    for h in historial:
        reg_id = old_to_new.get(h['id_registro'])
        if not reg_id:
            continue
        estado = estado_map.get(h['id_estado'], '')
        params_all.append((
            str(uuid.uuid4()), 'CAMBIO_ESTADO', 'prod_registros',
            reg_id, f'Estado: {estado}',
            json.dumps({"estado": estado, "accion": h.get('accion', '')}),
            safe_datetime(h.get('fecha_hora'))
        ))
    
    for i in range(0, len(params_all), BATCH):
        batch = params_all[i:i+BATCH]
        try:
            c = await get_conn()
            async with c.transaction():
                for p in batch:
                    await c.execute(
                        """INSERT INTO produccion.prod_actividad_historial 
                        (id, tipo_accion, tabla_afectada, registro_id, descripcion, datos_nuevos, created_at) 
                        VALUES ($1,$2,$3,$4,$5,$6,$7)""", *p)
            await c.close()
            done += len(batch)
        except Exception as e:
            print(f"Error batch: {e}")
            try:
                await c.close()
            except:
                pass
    
    print(f"Historial: {done}/{len(params_all)} insertados")
    print("COMPLETADO")

asyncio.run(main())
