"""Migración de inventario/materia prima: MariaDB → PostgreSQL"""
import asyncio, asyncpg, pymysql, uuid, json
from datetime import datetime, date
from decimal import Decimal

MARIA_CONFIG = dict(host='72.60.241.216', port=8000, user='admin', password='Proyectomoda@04072001', database='proyecto_moda', connect_timeout=15)
PG_DSN = 'postgres://admin:admin@72.60.241.216:9090/datos?sslmode=disable'
EMPRESA_ID = 8

id_maps = {}

def get_uuid(tabla, old_id):
    if old_id is None or old_id == 0:
        return None
    if tabla not in id_maps:
        id_maps[tabla] = {}
    if old_id not in id_maps[tabla]:
        id_maps[tabla][old_id] = str(uuid.uuid4())
    return id_maps[tabla][old_id]

def safe_date(val):
    if val is None or str(val) == '0000-00-00':
        return None
    if isinstance(val, (date, datetime)):
        return val
    return None

def safe_float(val):
    if val is None:
        return 0.0
    return float(val)

async def get_conn():
    return await asyncpg.connect(PG_DSN, timeout=15, command_timeout=30)

async def exec_batch(sql, params_list, label=""):
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
                    print(f"  ERROR {label}: {e}")
                    done += len(batch)  # skip batch
                    break
                await asyncio.sleep(1)
                try: await conn.close()
                except: pass
    print(f"  {done}/{total} {label}")
    return done

async def main():
    # Read MariaDB
    print("Leyendo MariaDB...")
    conn_m = pymysql.connect(**MARIA_CONFIG)
    cursor = conn_m.cursor(pymysql.cursors.DictCursor)

    cursor.execute('SELECT * FROM materia_prima_categoria')
    categorias = {r['id']: r['detalle'] for r in cursor.fetchall()}
    print(f"  Categorías: {categorias}")

    cursor.execute('SELECT * FROM materia_prima_clasificacion')
    clasificaciones = {r['id']: r['detalle'] for r in cursor.fetchall()}
    print(f"  Clasificaciones: {clasificaciones}")

    cursor.execute('SELECT * FROM materia_prima')
    items = cursor.fetchall()
    print(f"  Materia prima: {len(items)}")

    cursor.execute('SELECT * FROM materia_prima_ingresos')
    ingresos = cursor.fetchall()
    print(f"  Ingresos: {len(ingresos)}")

    cursor.execute('SELECT * FROM materia_prima_salida')
    salidas = cursor.fetchall()
    print(f"  Salidas: {len(salidas)}")

    # Also need marca mapping from previous migration
    cursor.execute('SELECT id, detalle FROM marca')
    marcas_m = {r['id']: r['detalle'] for r in cursor.fetchall()}

    cursor.execute('SELECT id, detalle FROM tipo')
    tipos_m = {r['id']: r['detalle'] for r in cursor.fetchall()}

    conn_m.close()

    # Get existing marca/tipo UUIDs from PostgreSQL
    print("\nCargando mapeos de PostgreSQL...")
    conn_pg = await get_conn()
    marca_rows = await conn_pg.fetch("SELECT id, nombre FROM produccion.prod_marcas")
    marca_name_to_uuid = {r['nombre']: r['id'] for r in marca_rows}

    tipo_rows = await conn_pg.fetch("SELECT id, nombre FROM produccion.prod_tipos")
    tipo_name_to_uuid = {r['nombre']: r['id'] for r in tipo_rows}
    await conn_pg.close()

    # Calculate stock per item
    ingresos_by_item = {}
    for ing in ingresos:
        iid = ing['ID_MATERIA_PRIMA']
        ingresos_by_item[iid] = ingresos_by_item.get(iid, 0) + safe_float(ing['CANTIDAD'])

    salidas_by_item = {}
    for sal in salidas:
        iid = sal['id_materia_prima']
        salidas_by_item[iid] = salidas_by_item.get(iid, 0) + safe_float(sal['cantidad'])

    # ── 1. Limpiar inventario existente ─────────────────────────
    print("\nLimpiando inventario...")
    try:
        c = await get_conn()
        await c.execute("DELETE FROM produccion.prod_inventario_salidas")
        await c.execute("DELETE FROM produccion.prod_inventario_ingresos")
        await c.execute("DELETE FROM produccion.prod_inventario")
        await c.close()
        print("  Limpiado")
    except Exception as e:
        print(f"  Error limpieza: {e}")
        try: await c.close()
        except: pass

    # ── 2. Migrar items de inventario ───────────────────────────
    print("\nMigrando items de inventario...")
    params = []
    for item in items:
        uid = get_uuid('materia_prima', item['id'])
        nombre = item['detalle'] or ''
        categoria = categorias.get(item['id_categoria'], 'Otros')
        clasificacion = clasificaciones.get(item['id_clasificacion'], 'Otros')

        # tipo_articulo basado en clasificación
        if clasificacion == 'Telas':
            tipo_articulo = 'TELA'
            unidad = 'METROS'
        elif clasificacion == 'Avios':
            tipo_articulo = 'AVIO'
            unidad = 'UNIDADES'
        else:
            tipo_articulo = 'OTRO'
            unidad = 'UNIDADES'

        stock = ingresos_by_item.get(item['id'], 0) - salidas_by_item.get(item['id'], 0)
        costo = safe_float(item['costo'])

        params.append((
            uid, nombre, categoria, unidad, 0,  # stock_minimo
            round(stock, 2), False,  # control_por_rollos
            datetime.now(), EMPRESA_ID, None,  # marca_id
            tipo_articulo, costo, costo, True,  # activo
            nombre,  # codigo = nombre
        ))

    await exec_batch(
        """INSERT INTO produccion.prod_inventario 
        (id, nombre, categoria, unidad_medida, stock_minimo, stock_actual, control_por_rollos,
         created_at, empresa_id, marca_id, tipo_articulo, precio_ref, costo_promedio, activo, codigo)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
        params, "items inventario"
    )

    # ── 3. Migrar ingresos ──────────────────────────────────────
    print("Migrando ingresos...")
    params = []
    for ing in ingresos:
        uid = get_uuid('ingreso', ing['ID'])
        item_id = get_uuid('materia_prima', ing['ID_MATERIA_PRIMA'])
        if not item_id:
            continue
        cantidad = safe_float(ing['CANTIDAD'])
        costo = safe_float(ing['COSTO'])
        fecha = safe_date(ing['fecha']) or datetime.now()

        # Marca y tipo para observaciones
        marca_n = marcas_m.get(ing.get('ID_MARCA'), '')
        tipo_n = tipos_m.get(ing.get('ID_TIPO'), '')
        obs = f"{marca_n} - {tipo_n}".strip(' -') if marca_n or tipo_n else ''

        params.append((
            uid, item_id, cantidad, cantidad,  # cantidad_disponible = cantidad
            costo, obs, '', obs,
            datetime.combine(fecha, datetime.min.time()) if isinstance(fecha, date) and not isinstance(fecha, datetime) else fecha,
            EMPRESA_ID,
        ))

    await exec_batch(
        """INSERT INTO produccion.prod_inventario_ingresos 
        (id, item_id, cantidad, cantidad_disponible, costo_unitario, proveedor, numero_documento, observaciones, fecha, empresa_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
        params, "ingresos"
    )

    # ── 4. Migrar salidas ───────────────────────────────────────
    print("Migrando salidas...")
    params = []
    for sal in salidas:
        uid = get_uuid('salida', sal['id'])
        item_id = get_uuid('materia_prima', sal['id_materia_prima'])
        if not item_id:
            continue
        cantidad = safe_float(sal['cantidad'])
        costo = safe_float(sal['costo'])
        fecha = safe_date(sal['fecha']) or datetime.now()

        marca_n = marcas_m.get(sal.get('ID_MARCA'), '')
        tipo_n = tipos_m.get(sal.get('ID_TIPO'), '')
        obs = f"{marca_n} - {tipo_n}".strip(' -') if marca_n or tipo_n else ''

        params.append((
            uid, item_id, cantidad, None,  # registro_id
            obs, costo,
            datetime.combine(fecha, datetime.min.time()) if isinstance(fecha, date) and not isinstance(fecha, datetime) else fecha,
            EMPRESA_ID,
        ))

    await exec_batch(
        """INSERT INTO produccion.prod_inventario_salidas 
        (id, item_id, cantidad, registro_id, observaciones, costo_total, fecha, empresa_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
        params, "salidas"
    )

    print("\n" + "="*50)
    print("MIGRACION INVENTARIO COMPLETADA")
    print("="*50)

if __name__ == '__main__':
    asyncio.run(main())
