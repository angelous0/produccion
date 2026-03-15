"""
Migración 002: Refactorización Estructural de Producción
- Tipificación fuerte de items (tipo_item enum)
- Rollos con campos de costo
- Tabla prod_orden_etapa para etapas productivas
- Estados de OP como enum
- Nuevas tablas: prod_consumo_mp, prod_servicio_orden, prod_wip_movimiento, prod_ingreso_pt
- Migración de datos desde tablas legacy
- NO borra tablas viejas (quedan deprecated)
"""
import asyncio
import asyncpg
from datetime import datetime

DATABASE_URL = "postgres://admin:admin@72.60.241.216:9091/datos?sslmode=disable"

async def backup_tables(conn):
    """Crea backup de tablas que serán modificadas"""
    print("=== FASE 0: BACKUP DE TABLAS ===")
    
    backup_tables = [
        'prod_inventario',
        'prod_inventario_rollos', 
        'prod_registros',
        'prod_inventario_salidas',
        'prod_registro_costos_servicio',
        'prod_movimientos_produccion'
    ]
    
    for table in backup_tables:
        backup_name = f"{table}_backup_{datetime.now().strftime('%Y%m%d_%H%M')}"
        try:
            # Check if table exists
            exists = await conn.fetchval(f"""
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'produccion' AND table_name = $1
                )
            """, table)
            
            if exists:
                await conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS produccion.{backup_name} AS 
                    SELECT * FROM produccion.{table}
                """)
                count = await conn.fetchval(f"SELECT COUNT(*) FROM produccion.{backup_name}")
                print(f"  ✓ Backup {backup_name}: {count} rows")
        except Exception as e:
            print(f"  ⚠ Backup {table}: {e}")


async def migrate_tipo_item(conn):
    """Fase 1A: Agregar tipo_item a prod_inventario"""
    print("\n=== FASE 1A: TIPO_ITEM EN PROD_INVENTARIO ===")
    
    # Add tipo_item column if not exists
    col_exists = await conn.fetchval("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'produccion' 
            AND table_name = 'prod_inventario' 
            AND column_name = 'tipo_item'
        )
    """)
    
    if not col_exists:
        await conn.execute("""
            ALTER TABLE produccion.prod_inventario 
            ADD COLUMN tipo_item VARCHAR(20) DEFAULT 'MP'
        """)
        print("  ✓ Columna tipo_item agregada")
    else:
        print("  - Columna tipo_item ya existe")
    
    # Migrate based on categoria and existing tipo_articulo
    await conn.execute("""
        UPDATE produccion.prod_inventario SET tipo_item = 
            CASE 
                WHEN tipo_articulo = 'PT' THEN 'PT'
                WHEN categoria ILIKE '%tela%' THEN 'MP'
                WHEN categoria ILIKE '%avio%' THEN 'AVIO'
                WHEN categoria ILIKE '%servicio%' THEN 'SERVICIO'
                ELSE 'MP'
            END
        WHERE tipo_item IS NULL OR tipo_item = 'MP'
    """)
    
    # Count by type
    counts = await conn.fetch("""
        SELECT tipo_item, COUNT(*) as cnt 
        FROM produccion.prod_inventario 
        GROUP BY tipo_item
    """)
    for c in counts:
        print(f"  - {c['tipo_item']}: {c['cnt']} items")


async def migrate_rollos(conn):
    """Fase 1B: Agregar campos de costo a rollos"""
    print("\n=== FASE 1B: CAMPOS DE COSTO EN ROLLOS ===")
    
    # Add new columns
    new_cols = [
        ('metros_iniciales', 'NUMERIC(14,4)'),
        ('metros_saldo', 'NUMERIC(14,4)'),
        ('costo_unitario_metro', 'NUMERIC(18,6)'),
        ('costo_total_inicial', 'NUMERIC(18,2)'),
        ('lote', 'VARCHAR(100)'),
        ('color_id', 'VARCHAR'),
        ('estado', 'VARCHAR(20) DEFAULT \'ACTIVO\'')
    ]
    
    for col_name, col_type in new_cols:
        col_exists = await conn.fetchval("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'produccion' 
                AND table_name = 'prod_inventario_rollos' 
                AND column_name = $1
            )
        """, col_name)
        
        if not col_exists:
            await conn.execute(f"""
                ALTER TABLE produccion.prod_inventario_rollos 
                ADD COLUMN {col_name} {col_type}
            """)
            print(f"  ✓ Columna {col_name} agregada")
        else:
            print(f"  - Columna {col_name} ya existe")
    
    # Migrate data from existing columns
    await conn.execute("""
        UPDATE produccion.prod_inventario_rollos r
        SET 
            metros_iniciales = COALESCE(metros_iniciales, metraje),
            metros_saldo = COALESCE(metros_saldo, metraje_disponible),
            costo_unitario_metro = COALESCE(costo_unitario_metro, (
                SELECT ing.costo_unitario 
                FROM produccion.prod_inventario_ingresos ing 
                WHERE ing.id = r.ingreso_id
            )),
            costo_total_inicial = COALESCE(costo_total_inicial, metraje * (
                SELECT ing.costo_unitario 
                FROM produccion.prod_inventario_ingresos ing 
                WHERE ing.id = r.ingreso_id
            )),
            estado = CASE 
                WHEN activo = false THEN 'BAJA'
                WHEN metraje_disponible <= 0 THEN 'AGOTADO'
                ELSE 'ACTIVO'
            END
        WHERE metros_iniciales IS NULL OR metros_saldo IS NULL
    """)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM produccion.prod_inventario_rollos")
    print(f"  ✓ {count} rollos actualizados")


async def create_orden_etapa(conn):
    """Fase 1C: Crear tabla de etapas productivas"""
    print("\n=== FASE 1C: TABLA PROD_ORDEN_ETAPA ===")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS produccion.prod_orden_etapa (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            empresa_id INTEGER NOT NULL,
            codigo VARCHAR(50) NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            descripcion TEXT,
            orden INT DEFAULT 10,
            activo BOOLEAN DEFAULT true,
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(empresa_id, codigo)
        )
    """)
    print("  ✓ Tabla prod_orden_etapa creada")
    
    # Insert default etapas from ESTADOS_PRODUCCION
    etapas_default = [
        ('CORTE', 'Corte', 10),
        ('COSTURA', 'Costura', 20),
        ('ATRAQUE', 'Atraque', 30),
        ('LAVANDERIA', 'Lavandería', 40),
        ('ACABADO', 'Acabado', 50),
        ('ALMACEN_PT', 'Almacén PT', 60),
    ]
    
    for codigo, nombre, orden in etapas_default:
        await conn.execute("""
            INSERT INTO produccion.prod_orden_etapa (empresa_id, codigo, nombre, orden)
            VALUES (6, $1, $2, $3)
            ON CONFLICT (empresa_id, codigo) DO NOTHING
        """, codigo, nombre, orden)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM produccion.prod_orden_etapa")
    print(f"  ✓ {count} etapas configuradas")


async def migrate_registros_estado(conn):
    """Fase 1D: Agregar estado_op a prod_registros"""
    print("\n=== FASE 1D: ESTADO_OP EN PROD_REGISTROS ===")
    
    # Add estado_op column
    col_exists = await conn.fetchval("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'produccion' 
            AND table_name = 'prod_registros' 
            AND column_name = 'estado_op'
        )
    """)
    
    if not col_exists:
        await conn.execute("""
            ALTER TABLE produccion.prod_registros 
            ADD COLUMN estado_op VARCHAR(20) DEFAULT 'EN_PROCESO'
        """)
        print("  ✓ Columna estado_op agregada")
    
    # Add etapa_actual_id column
    col_exists = await conn.fetchval("""
        SELECT EXISTS(
            SELECT 1 FROM information_schema.columns 
            WHERE table_schema = 'produccion' 
            AND table_name = 'prod_registros' 
            AND column_name = 'etapa_actual_id'
        )
    """)
    
    if not col_exists:
        await conn.execute("""
            ALTER TABLE produccion.prod_registros 
            ADD COLUMN etapa_actual_id VARCHAR
        """)
        print("  ✓ Columna etapa_actual_id agregada")
    
    # Migrate estado to estado_op
    await conn.execute("""
        UPDATE produccion.prod_registros SET estado_op = 
            CASE 
                WHEN estado = 'CERRADA' THEN 'CERRADA'
                WHEN estado = 'ANULADA' THEN 'ANULADA'
                WHEN estado = 'Para Corte' THEN 'ABIERTA'
                ELSE 'EN_PROCESO'
            END
        WHERE estado_op IS NULL OR estado_op = 'EN_PROCESO'
    """)
    
    # Map etapa from estado
    await conn.execute("""
        UPDATE produccion.prod_registros r
        SET etapa_actual_id = (
            SELECT e.id FROM produccion.prod_orden_etapa e
            WHERE e.empresa_id = 6
            AND e.codigo = CASE 
                WHEN r.estado ILIKE '%corte%' THEN 'CORTE'
                WHEN r.estado ILIKE '%costura%' THEN 'COSTURA'
                WHEN r.estado ILIKE '%atraque%' THEN 'ATRAQUE'
                WHEN r.estado ILIKE '%lavander%' THEN 'LAVANDERIA'
                WHEN r.estado ILIKE '%acabado%' THEN 'ACABADO'
                WHEN r.estado ILIKE '%almac%' OR r.estado ILIKE '%tienda%' THEN 'ALMACEN_PT'
                ELSE 'CORTE'
            END
            LIMIT 1
        )
        WHERE etapa_actual_id IS NULL
    """)
    
    counts = await conn.fetch("""
        SELECT estado_op, COUNT(*) as cnt 
        FROM produccion.prod_registros 
        GROUP BY estado_op
    """)
    for c in counts:
        print(f"  - {c['estado_op']}: {c['cnt']} OPs")


async def create_consumo_mp(conn):
    """Fase 1E: Crear tabla prod_consumo_mp"""
    print("\n=== FASE 1E: TABLA PROD_CONSUMO_MP ===")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS produccion.prod_consumo_mp (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            empresa_id INTEGER NOT NULL,
            orden_id VARCHAR NOT NULL,
            item_id VARCHAR NOT NULL,
            rollo_id VARCHAR,
            talla_id VARCHAR,
            cantidad NUMERIC(14,4) NOT NULL,
            costo_unitario NUMERIC(18,6) NOT NULL DEFAULT 0,
            costo_total NUMERIC(18,2) NOT NULL DEFAULT 0,
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            observaciones TEXT,
            salida_id VARCHAR,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT fk_consumo_orden FOREIGN KEY (orden_id) 
                REFERENCES produccion.prod_registros(id) ON DELETE CASCADE,
            CONSTRAINT fk_consumo_item FOREIGN KEY (item_id) 
                REFERENCES produccion.prod_inventario(id),
            CONSTRAINT fk_consumo_rollo FOREIGN KEY (rollo_id) 
                REFERENCES produccion.prod_inventario_rollos(id)
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_consumo_mp_orden ON produccion.prod_consumo_mp(orden_id)
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_consumo_mp_item ON produccion.prod_consumo_mp(item_id)
    """)
    
    print("  ✓ Tabla prod_consumo_mp creada")
    
    # Migrate from prod_inventario_salidas where registro_id is not null
    migrated = await conn.execute("""
        INSERT INTO produccion.prod_consumo_mp 
            (empresa_id, orden_id, item_id, rollo_id, talla_id, cantidad, 
             costo_unitario, costo_total, fecha, observaciones, salida_id)
        SELECT 
            COALESCE(s.empresa_id, 6),
            s.registro_id,
            s.item_id,
            s.rollo_id,
            s.talla_id,
            s.cantidad,
            CASE WHEN s.cantidad > 0 THEN COALESCE(s.costo_total, 0) / s.cantidad ELSE 0 END,
            COALESCE(s.costo_total, 0),
            COALESCE(s.fecha, NOW())::date,
            s.observaciones,
            s.id
        FROM produccion.prod_inventario_salidas s
        WHERE s.registro_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM produccion.prod_consumo_mp c WHERE c.salida_id = s.id
        )
    """)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM produccion.prod_consumo_mp")
    print(f"  ✓ {count} consumos migrados desde salidas")


async def create_servicio_orden(conn):
    """Fase 1F: Crear tabla prod_servicio_orden"""
    print("\n=== FASE 1F: TABLA PROD_SERVICIO_ORDEN ===")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS produccion.prod_servicio_orden (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            empresa_id INTEGER NOT NULL,
            orden_id VARCHAR NOT NULL,
            servicio_id VARCHAR,
            persona_id VARCHAR,
            proveedor_texto VARCHAR(200),
            documento_tipo VARCHAR(50),
            documento_numero VARCHAR(100),
            descripcion TEXT,
            cantidad_enviada INT DEFAULT 0,
            cantidad_recibida INT DEFAULT 0,
            cantidad_merma INT DEFAULT 0,
            tarifa_unitaria NUMERIC(18,4) DEFAULT 0,
            costo_total NUMERIC(18,2) NOT NULL DEFAULT 0,
            fecha_inicio DATE,
            fecha_fin DATE,
            estado VARCHAR(20) DEFAULT 'PENDIENTE',
            observaciones TEXT,
            legacy_movimiento_id VARCHAR,
            legacy_costo_id VARCHAR,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT fk_servicio_orden FOREIGN KEY (orden_id) 
                REFERENCES produccion.prod_registros(id) ON DELETE CASCADE
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_servicio_orden_orden ON produccion.prod_servicio_orden(orden_id)
    """)
    
    print("  ✓ Tabla prod_servicio_orden creada")
    
    # Migrate from prod_movimientos_produccion
    await conn.execute("""
        INSERT INTO produccion.prod_servicio_orden 
            (empresa_id, orden_id, servicio_id, persona_id, 
             cantidad_enviada, cantidad_recibida, cantidad_merma,
             tarifa_unitaria, costo_total, fecha_inicio, fecha_fin,
             estado, observaciones, legacy_movimiento_id)
        SELECT 
            6,
            m.registro_id,
            m.servicio_id,
            m.persona_id,
            m.cantidad_enviada,
            m.cantidad_recibida,
            m.diferencia,
            CASE WHEN m.cantidad_recibida > 0 
                THEN COALESCE(m.costo_calculado, 0) / m.cantidad_recibida 
                ELSE 0 
            END,
            COALESCE(m.costo_calculado, 0),
            m.fecha_inicio,
            m.fecha_fin,
            CASE 
                WHEN m.cantidad_recibida > 0 THEN 'COMPLETADO'
                WHEN m.cantidad_enviada > 0 THEN 'EN_PROCESO'
                ELSE 'PENDIENTE'
            END,
            m.observaciones,
            m.id
        FROM produccion.prod_movimientos_produccion m
        WHERE m.registro_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM produccion.prod_servicio_orden s WHERE s.legacy_movimiento_id = m.id
        )
    """)
    
    # Migrate from prod_registro_costos_servicio (those without movimiento match)
    await conn.execute("""
        INSERT INTO produccion.prod_servicio_orden 
            (empresa_id, orden_id, proveedor_texto, descripcion,
             costo_total, fecha_inicio, estado, legacy_costo_id)
        SELECT 
            c.empresa_id,
            c.registro_id,
            c.proveedor_texto,
            c.descripcion,
            c.monto,
            c.fecha,
            'COMPLETADO',
            c.id
        FROM produccion.prod_registro_costos_servicio c
        WHERE NOT EXISTS (
            SELECT 1 FROM produccion.prod_servicio_orden s WHERE s.legacy_costo_id = c.id
        )
    """)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM produccion.prod_servicio_orden")
    print(f"  ✓ {count} servicios migrados")


async def create_wip_movimiento(conn):
    """Fase 1G: Crear tabla prod_wip_movimiento"""
    print("\n=== FASE 1G: TABLA PROD_WIP_MOVIMIENTO ===")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS produccion.prod_wip_movimiento (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            empresa_id INTEGER NOT NULL,
            orden_id VARCHAR NOT NULL,
            origen_tipo VARCHAR(20) NOT NULL,
            origen_id VARCHAR NOT NULL,
            costo NUMERIC(18,2) NOT NULL,
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            descripcion TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT fk_wip_orden FOREIGN KEY (orden_id) 
                REFERENCES produccion.prod_registros(id) ON DELETE CASCADE
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_wip_orden ON produccion.prod_wip_movimiento(orden_id)
    """)
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_wip_origen ON produccion.prod_wip_movimiento(origen_tipo, origen_id)
    """)
    
    print("  ✓ Tabla prod_wip_movimiento creada")
    
    # Populate from prod_consumo_mp
    await conn.execute("""
        INSERT INTO produccion.prod_wip_movimiento 
            (empresa_id, orden_id, origen_tipo, origen_id, costo, fecha, descripcion)
        SELECT 
            c.empresa_id,
            c.orden_id,
            'CONSUMO_MP',
            c.id,
            c.costo_total,
            c.fecha,
            'Consumo MP: ' || COALESCE(i.nombre, '')
        FROM produccion.prod_consumo_mp c
        LEFT JOIN produccion.prod_inventario i ON c.item_id = i.id
        WHERE NOT EXISTS (
            SELECT 1 FROM produccion.prod_wip_movimiento w 
            WHERE w.origen_tipo = 'CONSUMO_MP' AND w.origen_id = c.id
        )
    """)
    
    # Populate from prod_servicio_orden
    await conn.execute("""
        INSERT INTO produccion.prod_wip_movimiento 
            (empresa_id, orden_id, origen_tipo, origen_id, costo, fecha, descripcion)
        SELECT 
            s.empresa_id,
            s.orden_id,
            'SERVICIO',
            s.id,
            s.costo_total,
            COALESCE(s.fecha_fin, s.fecha_inicio, CURRENT_DATE),
            'Servicio: ' || COALESCE(s.descripcion, srv.nombre, 'Externo')
        FROM produccion.prod_servicio_orden s
        LEFT JOIN produccion.prod_servicios_produccion srv ON s.servicio_id = srv.id
        WHERE s.costo_total > 0
        AND NOT EXISTS (
            SELECT 1 FROM produccion.prod_wip_movimiento w 
            WHERE w.origen_tipo = 'SERVICIO' AND w.origen_id = s.id
        )
    """)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM produccion.prod_wip_movimiento")
    print(f"  ✓ {count} movimientos WIP generados")


async def create_ingreso_pt(conn):
    """Fase 1H: Crear tabla prod_ingreso_pt"""
    print("\n=== FASE 1H: TABLA PROD_INGRESO_PT ===")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS produccion.prod_ingreso_pt (
            id VARCHAR PRIMARY KEY DEFAULT gen_random_uuid()::text,
            empresa_id INTEGER NOT NULL,
            cierre_id VARCHAR,
            orden_id VARCHAR NOT NULL,
            item_pt_id VARCHAR NOT NULL,
            cantidad NUMERIC(14,4) NOT NULL,
            costo_unitario NUMERIC(18,6) NOT NULL,
            costo_total NUMERIC(18,2) NOT NULL,
            almacen_destino_id VARCHAR,
            fecha DATE NOT NULL DEFAULT CURRENT_DATE,
            ingreso_inventario_id VARCHAR,
            created_at TIMESTAMP DEFAULT NOW(),
            CONSTRAINT fk_ingreso_pt_orden FOREIGN KEY (orden_id) 
                REFERENCES produccion.prod_registros(id),
            CONSTRAINT fk_ingreso_pt_item FOREIGN KEY (item_pt_id) 
                REFERENCES produccion.prod_inventario(id)
        )
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ingreso_pt_orden ON produccion.prod_ingreso_pt(orden_id)
    """)
    
    print("  ✓ Tabla prod_ingreso_pt creada")
    
    # Migrate from existing cierres
    await conn.execute("""
        INSERT INTO produccion.prod_ingreso_pt 
            (empresa_id, cierre_id, orden_id, item_pt_id, cantidad, 
             costo_unitario, costo_total, fecha, ingreso_inventario_id)
        SELECT 
            c.empresa_id,
            c.id,
            c.registro_id,
            r.pt_item_id,
            c.qty_terminada,
            c.costo_unit_pt,
            c.costo_total,
            c.fecha,
            c.pt_ingreso_id
        FROM produccion.prod_registro_cierre c
        JOIN produccion.prod_registros r ON c.registro_id = r.id
        WHERE r.pt_item_id IS NOT NULL
        AND NOT EXISTS (
            SELECT 1 FROM produccion.prod_ingreso_pt p WHERE p.cierre_id = c.id
        )
    """)
    
    count = await conn.fetchval("SELECT COUNT(*) FROM produccion.prod_ingreso_pt")
    print(f"  ✓ {count} ingresos PT migrados")


async def create_views(conn):
    """Fase 1I: Crear vistas útiles"""
    print("\n=== FASE 1I: VISTAS ===")
    
    # Vista de resumen WIP por orden
    await conn.execute("""
        CREATE OR REPLACE VIEW produccion.v_wip_resumen AS
        SELECT 
            orden_id,
            SUM(CASE WHEN origen_tipo = 'CONSUMO_MP' THEN costo ELSE 0 END) as costo_mp,
            SUM(CASE WHEN origen_tipo = 'SERVICIO' THEN costo ELSE 0 END) as costo_servicio,
            SUM(CASE WHEN origen_tipo = 'AJUSTE' THEN costo ELSE 0 END) as costo_ajuste,
            SUM(costo) as costo_total,
            COUNT(*) as total_movimientos
        FROM produccion.prod_wip_movimiento
        GROUP BY orden_id
    """)
    print("  ✓ Vista v_wip_resumen creada")
    
    # Vista de órdenes con info completa
    await conn.execute("""
        CREATE OR REPLACE VIEW produccion.v_orden_completa AS
        SELECT 
            r.id,
            r.n_corte,
            r.empresa_id,
            r.modelo_id,
            m.nombre as modelo_nombre,
            r.pt_item_id,
            pt.codigo as pt_codigo,
            pt.nombre as pt_nombre,
            r.estado,
            r.estado_op,
            r.etapa_actual_id,
            e.nombre as etapa_nombre,
            r.fecha_creacion,
            r.urgente,
            COALESCE((SELECT SUM(cantidad_real) FROM produccion.prod_registro_tallas WHERE registro_id = r.id), 0) as total_prendas,
            COALESCE(w.costo_mp, 0) as costo_mp,
            COALESCE(w.costo_servicio, 0) as costo_servicio,
            COALESCE(w.costo_total, 0) as costo_wip_total
        FROM produccion.prod_registros r
        LEFT JOIN produccion.prod_modelos m ON r.modelo_id = m.id
        LEFT JOIN produccion.prod_inventario pt ON r.pt_item_id = pt.id
        LEFT JOIN produccion.prod_orden_etapa e ON r.etapa_actual_id = e.id
        LEFT JOIN produccion.v_wip_resumen w ON r.id = w.orden_id
    """)
    print("  ✓ Vista v_orden_completa creada")


async def verify_migration(conn):
    """Verificar estado final"""
    print("\n=== VERIFICACIÓN FINAL ===")
    
    tables = [
        'prod_inventario',
        'prod_inventario_rollos',
        'prod_registros',
        'prod_orden_etapa',
        'prod_consumo_mp',
        'prod_servicio_orden',
        'prod_wip_movimiento',
        'prod_ingreso_pt'
    ]
    
    for table in tables:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM produccion.{table}")
        print(f"  {table}: {count} registros")
    
    # Verify WIP consistency
    wip_total = await conn.fetchval("""
        SELECT SUM(costo_total) FROM produccion.v_wip_resumen
    """)
    print(f"\n  Total WIP acumulado: {wip_total or 0:.2f}")


async def migrate():
    """Ejecuta la migración completa"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("=" * 60)
        print("MIGRACIÓN 002: REFACTORIZACIÓN PRODUCCIÓN")
        print("=" * 60)
        
        async with conn.transaction():
            await backup_tables(conn)
            await migrate_tipo_item(conn)
            await migrate_rollos(conn)
            await create_orden_etapa(conn)
            await migrate_registros_estado(conn)
            await create_consumo_mp(conn)
            await create_servicio_orden(conn)
            await create_wip_movimiento(conn)
            await create_ingreso_pt(conn)
            await create_views(conn)
            await verify_migration(conn)
        
        print("\n" + "=" * 60)
        print("✓ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print("\nTablas legacy preservadas (deprecated):")
        print("  - prod_movimientos_produccion")
        print("  - prod_registro_costos_servicio")
        print("\nNuevas tablas activas:")
        print("  - prod_consumo_mp")
        print("  - prod_servicio_orden")
        print("  - prod_wip_movimiento")
        print("  - prod_ingreso_pt")
        print("  - prod_orden_etapa")
        
    except Exception as e:
        print(f"\n❌ ERROR EN MIGRACIÓN: {e}")
        raise
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
