"""
Migración MariaDB → PostgreSQL con reconexión automática y lotes
"""
import asyncio
import asyncpg
import pymysql
import uuid
import json
from datetime import datetime, date

MARIA_CONFIG = dict(host='72.60.241.216', port=8000, user='admin', password='Proyectomoda@04072001', database='proyecto_moda', connect_timeout=15)
PG_DSN = 'postgres://admin:admin@72.60.241.216:9090/datos?sslmode=disable'

id_maps = {}

def get_uuid(tabla, old_id):
    if old_id is None or old_id == 0 or old_id == '':
        return None
    if tabla not in id_maps:
        id_maps[tabla] = {}
    if old_id not in id_maps[tabla]:
        id_maps[tabla][old_id] = str(uuid.uuid4())
    return id_maps[tabla][old_id]

def safe_date(val):
    if val is None or val == '':
        return None
    s = str(val)
    if '0000' in s:
        return None
    if isinstance(val, (date, datetime)):
        return val
    return None

def safe_datetime(val):
    """Para campos timestamp - retorna datetime o default"""
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

async def exec_batch(sql, params_list, label=""):
    """Ejecutar batch con reconexión automática"""
    BATCH_SIZE = 50
    total = len(params_list)
    done = 0
    for i in range(0, total, BATCH_SIZE):
        batch = params_list[i:i+BATCH_SIZE]
        retries = 3
        while retries > 0:
            try:
                conn = await get_conn()
                async with conn.transaction():
                    for params in batch:
                        await conn.execute(sql, *params)
                await conn.close()
                done += len(batch)
                break
            except Exception as e:
                retries -= 1
                if retries == 0:
                    print(f"  ERROR en {label}: {e}")
                    raise
                await asyncio.sleep(1)
                try:
                    await conn.close()
                except:
                    pass
    print(f"  {done}/{total} {label} insertados")
    return done

async def exec_sql(sql):
    """Ejecutar SQL simple con reconexión"""
    retries = 3
    while retries > 0:
        try:
            conn = await get_conn()
            await conn.execute(sql)
            await conn.close()
            return
        except Exception as e:
            retries -= 1
            if retries == 0:
                print(f"  ERROR: {e}")
            await asyncio.sleep(1)
            try:
                await conn.close()
            except:
                pass

def read_mariadb():
    print("Leyendo MariaDB...")
    conn = pymysql.connect(**MARIA_CONFIG)
    cursor = conn.cursor(pymysql.cursors.DictCursor)
    data = {}
    tables = [
        'marca', 'tipo', 'entalle', 'tela', 'hilo', 'hilo_especifico',
        'color', 'talla', 'modelo', 'registro', 'persona', 'servicio',
        'servicios_produccion', 'colores_produccion', 'tallas_produccion',
        'marca_tipo', 'tipo_entalle', 'entalle_tela', 'hilo_hilo_especifico',
        'servicio_persona', 'servicio_tipo', 'estado', 'tipo_color',
        'empresa', 'historial_registro',
    ]
    for t in tables:
        cursor.execute(f'SELECT * FROM {t}')
        data[t] = cursor.fetchall()
        print(f"  {t}: {len(data[t])}")
    conn.close()
    return data

async def migrate(data):
    # ── 1. Limpiar ──────────────────────────────────────────────
    print("\nLimpiando tablas...")
    # Usar TRUNCATE CASCADE para limpiar completamente
    truncate_groups = [
        'prod_guias_remision, prod_arreglos, prod_fallados, prod_mermas',
        'prod_movimientos_produccion, prod_registro_tallas, prod_actividad_historial',
        'prod_incidencia, prod_paralizacion',
        'prod_registros',
        'prod_modelos',
        'prod_personas_produccion, prod_servicios_produccion',
        'prod_colores_catalogo, prod_colores_generales',
        'prod_tallas_catalogo, prod_hilos_especificos, prod_hilos',
        'prod_telas, prod_entalles, prod_tipos, prod_marcas',
        'prod_rutas_produccion',
    ]
    for tg in truncate_groups:
        try:
            tables_q = ', '.join([f'produccion.{t.strip()}' for t in tg.split(',')])
            await exec_sql(f'TRUNCATE TABLE {tables_q} CASCADE')
        except Exception as e:
            # Fallback to DELETE
            for t in tg.split(','):
                try:
                    await exec_sql(f'DELETE FROM produccion.{t.strip()}')
                except:
                    pass
    print("  Tablas limpiadas")

    # ── 2. Marcas ───────────────────────────────────────────────
    print("\nMigrando marcas...")
    params = []
    for m in data['marca']:
        if not m['detalle']:
            continue
        params.append((get_uuid('marca', m['id']), m['detalle'], m['secuencia'], datetime.now()))
    await exec_batch(
        "INSERT INTO produccion.prod_marcas (id, nombre, orden, created_at) VALUES ($1,$2,$3,$4)",
        params, "marcas"
    )

    # ── 3. Tipos ────────────────────────────────────────────────
    print("Migrando tipos...")
    tipo_marcas = {}
    for mt in data['marca_tipo']:
        tid = mt['id_tipo']
        if tid not in tipo_marcas:
            tipo_marcas[tid] = []
        mu = get_uuid('marca', mt['id_marca'])
        if mu:
            tipo_marcas[tid].append(mu)

    params = []
    for t in data['tipo']:
        if not t['detalle']:
            continue
        params.append((get_uuid('tipo', t['id']), t['detalle'], json.dumps(tipo_marcas.get(t['id'], [])), 0, datetime.now()))
    await exec_batch(
        "INSERT INTO produccion.prod_tipos (id, nombre, marca_ids, orden, created_at) VALUES ($1,$2,$3,$4,$5)",
        params, "tipos"
    )

    # ── 4. Entalles ─────────────────────────────────────────────
    print("Migrando entalles...")
    entalle_tipos = {}
    for te in data['tipo_entalle']:
        eid = te['id_entalle']
        if eid not in entalle_tipos:
            entalle_tipos[eid] = []
        tu = get_uuid('tipo', te['id_tipo'])
        if tu:
            entalle_tipos[eid].append(tu)

    params = []
    for e in data['entalle']:
        if not e['detalle']:
            continue
        params.append((get_uuid('entalle', e['id']), e['detalle'], json.dumps(entalle_tipos.get(e['id'], [])), 0, datetime.now()))
    await exec_batch(
        "INSERT INTO produccion.prod_entalles (id, nombre, tipo_ids, orden, created_at) VALUES ($1,$2,$3,$4,$5)",
        params, "entalles"
    )

    # ── 5. Telas ────────────────────────────────────────────────
    print("Migrando telas...")
    tela_ents = {}
    for et in data['entalle_tela']:
        tid = et['id_tela']
        if tid not in tela_ents:
            tela_ents[tid] = []
        eu = get_uuid('entalle', et['id_entalle'])
        if eu:
            tela_ents[tid].append(eu)

    params = []
    for t in data['tela']:
        if not t['detalle']:
            continue
        params.append((get_uuid('tela', t['id']), t['detalle'], json.dumps(tela_ents.get(t['id'], [])), 0, datetime.now()))
    await exec_batch(
        "INSERT INTO produccion.prod_telas (id, nombre, entalle_ids, orden, created_at) VALUES ($1,$2,$3,$4,$5)",
        params, "telas"
    )

    # ── 6. Hilos ────────────────────────────────────────────────
    print("Migrando hilos...")
    params = [(get_uuid('hilo', h['id']), h['detalle'], 0, datetime.now()) for h in data['hilo'] if h['detalle']]
    await exec_batch(
        "INSERT INTO produccion.prod_hilos (id, nombre, orden, created_at) VALUES ($1,$2,$3,$4)",
        params, "hilos"
    )

    # ── 7. Hilos Específicos ────────────────────────────────────
    print("Migrando hilos específicos...")
    params = [(get_uuid('hilo_especifico', h['id']), h['detalle'], 0, datetime.now()) for h in data['hilo_especifico'] if h['detalle']]
    await exec_batch(
        "INSERT INTO produccion.prod_hilos_especificos (id, nombre, orden, created_at) VALUES ($1,$2,$3,$4)",
        params, "hilos específicos"
    )

    # ── 8. Colores ──────────────────────────────────────────────
    print("Migrando colores generales...")
    color_generales = sorted(set(c['color_general'] for c in data['color'] if c['color_general']))
    cg_map = {}
    params = []
    for idx, cg in enumerate(color_generales):
        uid = str(uuid.uuid4())
        cg_map[cg] = uid
        params.append((uid, cg, idx + 1, datetime.now()))
    await exec_batch(
        "INSERT INTO produccion.prod_colores_generales (id, nombre, orden, created_at) VALUES ($1,$2,$3,$4)",
        params, "colores generales"
    )

    print("Migrando colores catálogo...")
    params = []
    for c in data['color']:
        if not c['detalle']:
            continue
        params.append((get_uuid('color', c['id']), c['detalle'], c['color_general'] or None, cg_map.get(c['color_general']), 0, datetime.now()))
    await exec_batch(
        "INSERT INTO produccion.prod_colores_catalogo (id, nombre, color_general, color_general_id, orden, created_at) VALUES ($1,$2,$3,$4,$5,$6)",
        params, "colores catálogo"
    )

    # ── 9. Tallas ───────────────────────────────────────────────
    print("Migrando tallas...")
    params = [(get_uuid('talla', t['id']), t['detalle'], 0, datetime.now()) for t in data['talla'] if t['detalle']]
    await exec_batch(
        "INSERT INTO produccion.prod_tallas_catalogo (id, nombre, orden, created_at) VALUES ($1,$2,$3,$4)",
        params, "tallas"
    )

    # ── 10. Servicios ───────────────────────────────────────────
    print("Migrando servicios...")
    params = [(get_uuid('servicio', s['id']), s['detalle'], s['costo'], s['secuencia'], datetime.now()) for s in data['servicio'] if s['detalle']]
    await exec_batch(
        "INSERT INTO produccion.prod_servicios_produccion (id, nombre, tarifa, orden, created_at) VALUES ($1,$2,$3,$4,$5)",
        params, "servicios"
    )

    # ── 11. Personas ────────────────────────────────────────────
    print("Migrando personas...")
    persona_srvs = {}
    for sp in data['servicio_persona']:
        pid = sp['id_persona']
        if pid not in persona_srvs:
            persona_srvs[pid] = []
        su = get_uuid('servicio', sp['id_servicio'])
        if su:
            persona_srvs[pid].append(su)

    params = []
    for p in data['persona']:
        if not p['detalle']:
            continue
        tipo = 'EXTERNO' if p.get('tipo') == 'Externo' else 'INTERNO'
        params.append((get_uuid('persona', p['id']), p['detalle'], tipo, json.dumps(persona_srvs.get(p['id'], [])), p.get('estado', 1) == 1, 0, datetime.now()))
    await exec_batch(
        "INSERT INTO produccion.prod_personas_produccion (id, nombre, tipo_persona, servicios, activo, orden, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7)",
        params, "personas"
    )

    # ── 12. Ruta ────────────────────────────────────────────────
    print("Creando ruta...")
    srvs_ord = sorted([s for s in data['servicio'] if s['detalle']], key=lambda s: s['secuencia'])
    etapas = [{"servicio_id": get_uuid('servicio', s['id']), "servicio_nombre": s['detalle'], "orden": s['secuencia']} for s in srvs_ord]
    ruta_id = str(uuid.uuid4())
    id_maps['ruta'] = {1: ruta_id}
    await exec_batch(
        "INSERT INTO produccion.prod_rutas_produccion (id, nombre, etapas, created_at) VALUES ($1,$2,$3,$4)",
        [(ruta_id, 'Ruta Principal', json.dumps(etapas), datetime.now())], "ruta"
    )

    # ── 13. Modelos ─────────────────────────────────────────────
    print("Migrando modelos...")
    reg_by_modelo = {}
    for r in data['registro']:
        mid = r['id_modelo']
        if mid not in reg_by_modelo:
            reg_by_modelo[mid] = r

    params = []
    for m in data['modelo']:
        if not m['detalle']:
            continue
        reg = reg_by_modelo.get(m['id'], {})
        params.append((
            get_uuid('modelo', m['id']), m['detalle'],
            get_uuid('marca', reg.get('id_marca')),
            get_uuid('tipo', reg.get('id_tipo')),
            get_uuid('entalle', reg.get('id_entalle')),
            get_uuid('tela', reg.get('id_tela')),
            get_uuid('hilo', reg.get('id_hilo')),
            ruta_id, datetime.now()
        ))
    await exec_batch(
        """INSERT INTO produccion.prod_modelos (id, nombre, marca_id, tipo_id, entalle_id, tela_id, hilo_id, ruta_produccion_id, created_at) 
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
        params, "modelos"
    )

    # ── 14. Pre-calcular tallas y colores por registro ──────────
    print("Preparando tallas y colores...")
    tallas_by_reg = {}
    tp_id_to_data = {}
    for tp in data['tallas_produccion']:
        rid = tp['id_registro']
        talla_uuid = get_uuid('talla', tp['id_talla'])
        talla_nombre = next((t['detalle'] for t in data['talla'] if t['id'] == tp['id_talla']), '')
        if rid not in tallas_by_reg:
            tallas_by_reg[rid] = []
        tallas_by_reg[rid].append({"talla_id": talla_uuid, "talla_nombre": talla_nombre, "cantidad": tp['cantidad'], "nombre": ""})
        tp_id_to_data[tp['id']] = {"talla_id": talla_uuid, "talla_nombre": talla_nombre, "rid": rid}

    colores_by_tp = {}
    for cp in data['colores_produccion']:
        tpid = cp['id_tallas_produccion']
        if tpid not in colores_by_tp:
            colores_by_tp[tpid] = []
        color_uuid = get_uuid('color', cp['id_color'])
        color_nombre = next((c['detalle'] for c in data['color'] if c['id'] == cp['id_color']), '')
        colores_by_tp[tpid].append({"color_id": color_uuid, "color_nombre": color_nombre, "cantidad": cp['cantidad']})

    dist_colores_by_reg = {}
    for tp in data['tallas_produccion']:
        rid = tp['id_registro']
        tpid = tp['id']
        td = tp_id_to_data.get(tpid, {})
        if rid not in dist_colores_by_reg:
            dist_colores_by_reg[rid] = []
        colores = colores_by_tp.get(tpid, [])
        cantidad_total = sum(c['cantidad'] for c in colores) if colores else tp['cantidad']
        dist_colores_by_reg[rid].append({
            "talla_id": td.get("talla_id", ""),
            "talla_nombre": td.get("talla_nombre", ""),
            "cantidad_total": cantidad_total,
            "colores": colores
        })

    estado_map = {}
    for e in data['estado']:
        estado_map[e['ID']] = (e['DETALLE'] or '').replace('.', '').replace('_', ' ').strip()

    # ── 15. Registros ───────────────────────────────────────────
    print("Migrando registros...")
    params = []
    for r in data['registro']:
        uid = get_uuid('registro', r['id'])
        params.append((
            uid,
            str(r.get('n_corte', '')),
            get_uuid('modelo', r['id_modelo']),
            estado_map.get(r['id_estado'], ''),
            r.get('urgencia', 0) == 1,
            json.dumps(tallas_by_reg.get(r['id'], [])),
            json.dumps(dist_colores_by_reg.get(r['id'], [])),
            r.get('fecha_hora') if isinstance(r.get('fecha_hora'), (date, datetime)) and '0000' not in str(r.get('fecha_hora', '')) else datetime.now(),
            get_uuid('hilo_especifico', r.get('id_hilo_especifico')),
            1,
            '',
        ))
    await exec_batch(
        """INSERT INTO produccion.prod_registros 
        (id, n_corte, modelo_id, estado, urgente, tallas, distribucion_colores, 
         fecha_creacion, hilo_especifico_id, empresa_id, curva)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
        params, "registros"
    )

    # ── 16. Movimientos ─────────────────────────────────────────
    print("Migrando movimientos...")
    params = []
    for sp in data['servicios_produccion']:
        registro_id = get_uuid('registro', sp['id_registro'])
        servicio_id = get_uuid('servicio', sp['id_servicio'])
        if not registro_id or not servicio_id:
            continue
        persona_id = get_uuid('persona', sp['id_persona'])
        fi = safe_date(sp.get('fecha_inicio'))
        ff = safe_date(sp.get('fecha_fin'))
        cant = sp.get('cantidad', 0)
        params.append((
            get_uuid('servicios_produccion', sp['id']),
            registro_id, servicio_id, persona_id,
            cant, cant if ff else 0, 0,
            float(sp.get('costo', 0) or 0),
            fi, ff,
            (sp.get('glosa') or '')[:500],
            safe_datetime(sp.get('actualizacion')),
            0,
        ))
    await exec_batch(
        """INSERT INTO produccion.prod_movimientos_produccion 
        (id, registro_id, servicio_id, persona_id, cantidad_enviada, cantidad_recibida,
         diferencia, costo_calculado, fecha_inicio, fecha_fin, observaciones, created_at, tarifa_aplicada)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)""",
        params, "movimientos"
    )

    # ── 17. Historial ───────────────────────────────────────────
    print("Migrando historial...")
    params = []
    for h in data['historial_registro']:
        registro_id = get_uuid('registro', h['id_registro'])
        if not registro_id:
            continue
        estado = estado_map.get(h['id_estado'], '')
        params.append((
            str(uuid.uuid4()), 'CAMBIO_ESTADO', 'prod_registros',
            registro_id, '',
            json.dumps({"estado": estado, "accion": h.get('accion', '')}),
            safe_datetime(h.get('fecha_hora'))
        ))
    await exec_batch(
        """INSERT INTO produccion.prod_actividad_historial 
        (id, tipo_accion, tabla_afectada, registro_id, descripcion, datos_nuevos, created_at) 
        VALUES ($1,$2,$3,$4,$5,$6,$7)""",
        params, "historial"
    )

    print("\n" + "="*50)
    print("MIGRACION COMPLETADA EXITOSAMENTE")
    print("="*50)

async def main():
    data = read_mariadb()
    await migrate(data)

if __name__ == '__main__':
    asyncio.run(main())
