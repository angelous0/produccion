import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import asyncpg
import json
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

MONGO_URL = os.environ['MONGO_URL']
MONGO_DB = os.environ['DB_NAME']
POSTGRES_URL = "postgres://admin:admin@72.60.241.216:9091/datos?sslmode=disable"

TABLES_SQL = """
DROP TABLE IF EXISTS prod_guias_remision CASCADE;
DROP TABLE IF EXISTS prod_mermas CASCADE;
DROP TABLE IF EXISTS prod_movimientos_produccion CASCADE;
DROP TABLE IF EXISTS prod_personas_produccion CASCADE;
DROP TABLE IF EXISTS prod_inventario_rollos CASCADE;
DROP TABLE IF EXISTS prod_inventario_ajustes CASCADE;
DROP TABLE IF EXISTS prod_inventario_salidas CASCADE;
DROP TABLE IF EXISTS prod_inventario_ingresos CASCADE;
DROP TABLE IF EXISTS prod_inventario CASCADE;
DROP TABLE IF EXISTS prod_registros CASCADE;
DROP TABLE IF EXISTS prod_modelos CASCADE;
DROP TABLE IF EXISTS prod_servicios_produccion CASCADE;
DROP TABLE IF EXISTS prod_rutas_produccion CASCADE;
DROP TABLE IF EXISTS prod_colores_catalogo CASCADE;
DROP TABLE IF EXISTS prod_tallas_catalogo CASCADE;
DROP TABLE IF EXISTS prod_hilos CASCADE;
DROP TABLE IF EXISTS prod_telas CASCADE;
DROP TABLE IF EXISTS prod_entalles CASCADE;
DROP TABLE IF EXISTS prod_tipos CASCADE;
DROP TABLE IF EXISTS prod_marcas CASCADE;

CREATE TABLE prod_marcas (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_tipos (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    marca_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_entalles (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_telas (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    entalle_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_hilos (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tela_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_tallas_catalogo (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    orden INTEGER DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_colores_catalogo (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    codigo_hex VARCHAR(20) DEFAULT '',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_rutas_produccion (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT DEFAULT '',
    etapas JSONB DEFAULT '[]',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_servicios_produccion (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT DEFAULT '',
    tarifa DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_modelos (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    marca_id VARCHAR(36),
    tipo_id VARCHAR(36),
    entalle_id VARCHAR(36),
    tela_id VARCHAR(36),
    hilo_id VARCHAR(36),
    ruta_produccion_id VARCHAR(36),
    materiales JSONB DEFAULT '[]',
    servicios_ids JSONB DEFAULT '[]',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_registros (
    id VARCHAR(36) PRIMARY KEY,
    n_corte VARCHAR(100) NOT NULL,
    modelo_id VARCHAR(36),
    curva VARCHAR(100) DEFAULT '',
    estado VARCHAR(100) DEFAULT 'Para Corte',
    urgente BOOLEAN DEFAULT FALSE,
    tallas JSONB DEFAULT '[]',
    distribucion_colores JSONB DEFAULT '[]',
    fecha_creacion TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_inventario (
    id VARCHAR(36) PRIMARY KEY,
    codigo VARCHAR(100) UNIQUE NOT NULL,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT DEFAULT '',
    categoria VARCHAR(100) DEFAULT 'Otros',
    unidad_medida VARCHAR(50) DEFAULT 'unidad',
    stock_minimo INTEGER DEFAULT 0,
    stock_actual DECIMAL(10,2) DEFAULT 0,
    control_por_rollos BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_inventario_ingresos (
    id VARCHAR(36) PRIMARY KEY,
    item_id VARCHAR(36),
    cantidad DECIMAL(10,2) DEFAULT 0,
    cantidad_disponible DECIMAL(10,2) DEFAULT 0,
    costo_unitario DECIMAL(10,2) DEFAULT 0,
    proveedor VARCHAR(255) DEFAULT '',
    numero_documento VARCHAR(100) DEFAULT '',
    observaciones TEXT DEFAULT '',
    fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_inventario_salidas (
    id VARCHAR(36) PRIMARY KEY,
    item_id VARCHAR(36),
    cantidad DECIMAL(10,2) DEFAULT 0,
    registro_id VARCHAR(36),
    observaciones TEXT DEFAULT '',
    rollo_id VARCHAR(36),
    costo_total DECIMAL(10,2) DEFAULT 0,
    detalle_fifo JSONB DEFAULT '[]',
    fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_inventario_ajustes (
    id VARCHAR(36) PRIMARY KEY,
    item_id VARCHAR(36),
    tipo VARCHAR(20),
    cantidad DECIMAL(10,2) DEFAULT 0,
    motivo VARCHAR(255) DEFAULT '',
    observaciones TEXT DEFAULT '',
    fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_inventario_rollos (
    id VARCHAR(36) PRIMARY KEY,
    item_id VARCHAR(36),
    ingreso_id VARCHAR(36),
    numero_rollo VARCHAR(100) DEFAULT '',
    metraje DECIMAL(10,2) DEFAULT 0,
    metraje_disponible DECIMAL(10,2) DEFAULT 0,
    ancho DECIMAL(10,2) DEFAULT 0,
    tono VARCHAR(100) DEFAULT '',
    observaciones TEXT DEFAULT '',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_personas_produccion (
    id VARCHAR(36) PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) DEFAULT 'externo',
    telefono VARCHAR(50) DEFAULT '',
    email VARCHAR(255) DEFAULT '',
    direccion TEXT DEFAULT '',
    servicios JSONB DEFAULT '[]',
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_movimientos_produccion (
    id VARCHAR(36) PRIMARY KEY,
    registro_id VARCHAR(36),
    servicio_id VARCHAR(36),
    persona_id VARCHAR(36),
    cantidad_enviada INTEGER DEFAULT 0,
    cantidad_recibida INTEGER DEFAULT 0,
    diferencia INTEGER DEFAULT 0,
    costo_calculado DECIMAL(10,2) DEFAULT 0,
    fecha_inicio DATE,
    fecha_fin DATE,
    observaciones TEXT DEFAULT '',
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_mermas (
    id VARCHAR(36) PRIMARY KEY,
    registro_id VARCHAR(36),
    movimiento_id VARCHAR(36),
    servicio_id VARCHAR(36),
    persona_id VARCHAR(36),
    cantidad INTEGER DEFAULT 0,
    motivo TEXT DEFAULT '',
    fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prod_guias_remision (
    id VARCHAR(36) PRIMARY KEY,
    numero_guia VARCHAR(50) DEFAULT '',
    movimiento_id VARCHAR(36),
    registro_id VARCHAR(36),
    servicio_id VARCHAR(36),
    persona_id VARCHAR(36),
    cantidad INTEGER DEFAULT 0,
    observaciones TEXT DEFAULT '',
    fecha TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

def parse_datetime(value):
    if value is None:
        return datetime.now()
    if isinstance(value, datetime):
        return value.replace(tzinfo=None)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.replace(tzinfo=None)
        except:
            return datetime.now()
    return datetime.now()

def parse_date(value):
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
            return dt.date()
        except:
            try:
                return datetime.strptime(value, '%Y-%m-%d').date()
            except:
                return None
    return None

async def migrate():
    print("=" * 60)
    print("MIGRANDO DE MONGODB A POSTGRESQL")
    print("=" * 60)
    
    mongo_client = AsyncIOMotorClient(MONGO_URL)
    mongo_db = mongo_client[MONGO_DB]
    pg_conn = await asyncpg.connect(POSTGRES_URL)
    
    print("\n📦 Creando tablas en PostgreSQL...")
    await pg_conn.execute(TABLES_SQL)
    print("   ✅ Tablas creadas")
    
    collections_config = [
        ("prod_marcas", ["id", "nombre", "created_at"]),
        ("prod_tipos", ["id", "nombre", "marca_ids", "created_at"]),
        ("prod_entalles", ["id", "nombre", "tipo_ids", "created_at"]),
        ("prod_telas", ["id", "nombre", "entalle_ids", "created_at"]),
        ("prod_hilos", ["id", "nombre", "tela_ids", "created_at"]),
        ("prod_tallas_catalogo", ["id", "nombre", "orden", "created_at"]),
        ("prod_colores_catalogo", ["id", "nombre", "codigo_hex", "created_at"]),
        ("prod_rutas_produccion", ["id", "nombre", "descripcion", "etapas", "created_at"]),
        ("prod_servicios_produccion", ["id", "nombre", "descripcion", "tarifa", "created_at"]),
        ("prod_modelos", ["id", "nombre", "marca_id", "tipo_id", "entalle_id", "tela_id", "hilo_id", "ruta_produccion_id", "materiales", "servicios_ids", "created_at"]),
        ("prod_registros", ["id", "n_corte", "modelo_id", "curva", "estado", "urgente", "tallas", "distribucion_colores", "fecha_creacion"]),
        ("prod_inventario", ["id", "codigo", "nombre", "descripcion", "categoria", "unidad_medida", "stock_minimo", "stock_actual", "control_por_rollos", "created_at"]),
        ("prod_inventario_ingresos", ["id", "item_id", "cantidad", "cantidad_disponible", "costo_unitario", "proveedor", "numero_documento", "observaciones", "fecha"]),
        ("prod_inventario_salidas", ["id", "item_id", "cantidad", "registro_id", "observaciones", "rollo_id", "costo_total", "detalle_fifo", "fecha"]),
        ("prod_inventario_ajustes", ["id", "item_id", "tipo", "cantidad", "motivo", "observaciones", "fecha"]),
        ("prod_inventario_rollos", ["id", "item_id", "ingreso_id", "numero_rollo", "metraje", "metraje_disponible", "ancho", "tono", "observaciones", "activo", "created_at"]),
        ("prod_personas_produccion", ["id", "nombre", "tipo", "telefono", "email", "direccion", "servicios", "activo", "created_at"]),
        ("prod_movimientos_produccion", ["id", "registro_id", "servicio_id", "persona_id", "cantidad_enviada", "cantidad_recibida", "diferencia", "costo_calculado", "fecha_inicio", "fecha_fin", "observaciones", "created_at"]),
        ("prod_mermas", ["id", "registro_id", "movimiento_id", "servicio_id", "persona_id", "cantidad", "motivo", "fecha"]),
        ("prod_guias_remision", ["id", "numero_guia", "movimiento_id", "registro_id", "servicio_id", "persona_id", "cantidad", "observaciones", "fecha"]),
    ]
    
    jsonb_fields = ["marca_ids", "tipo_ids", "entalle_ids", "tela_ids", "etapas", "materiales", "servicios_ids", "tallas", "distribucion_colores", "detalle_fifo", "servicios"]
    datetime_fields = ["created_at", "fecha", "fecha_creacion"]
    date_fields = ["fecha_inicio", "fecha_fin"]
    
    for collection_name, fields in collections_config:
        mongo_col = mongo_db[collection_name]
        docs = await mongo_col.find({}).to_list(None)
        
        if not docs:
            print(f"⚪ {collection_name}: vacía")
            continue
        
        print(f"\n🔄 Migrando {collection_name} ({len(docs)} docs)")
        migrated = 0
        
        for doc in docs:
            values = []
            for field in fields:
                val = doc.get(field)
                
                if field in jsonb_fields:
                    val = json.dumps(val if val else [])
                elif field in datetime_fields:
                    val = parse_datetime(val)
                elif field in date_fields:
                    val = parse_date(val)
                elif val is None:
                    if field in ["descripcion", "observaciones", "motivo", "telefono", "email", "direccion", "proveedor", "numero_documento", "curva", "tono", "numero_rollo", "codigo_hex", "numero_guia", "tipo"]:
                        val = ""
                    elif field in ["orden", "stock_minimo", "cantidad", "cantidad_enviada", "cantidad_recibida", "diferencia"]:
                        val = 0
                    elif field in ["tarifa", "stock_actual", "cantidad_disponible", "costo_unitario", "costo_total", "metraje", "metraje_disponible", "ancho", "costo_calculado"]:
                        val = 0.0
                    elif field in ["urgente", "control_por_rollos"]:
                        val = False
                    elif field == "activo":
                        val = True
                
                values.append(val)
            
            placeholders = ", ".join([f"${i+1}" for i in range(len(fields))])
            fields_str = ", ".join(fields)
            
            try:
                await pg_conn.execute(f"INSERT INTO {collection_name} ({fields_str}) VALUES ({placeholders})", *values)
                migrated += 1
            except Exception as e:
                print(f"   ⚠️ Error: {e}")
        
        print(f"   ✅ {migrated} registros migrados")
    
    await pg_conn.close()
    mongo_client.close()
    
    print("\n" + "=" * 60)
    print("✅ MIGRACIÓN A POSTGRESQL COMPLETADA")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(migrate())
