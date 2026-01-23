import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Mapeo de colecciones antiguas a nuevas
COLLECTIONS_MAP = {
    "marcas": "prod_marcas",
    "tipos": "prod_tipos",
    "entalles": "prod_entalles",
    "telas": "prod_telas",
    "hilos": "prod_hilos",
    "tallas_catalogo": "prod_tallas_catalogo",
    "colores_catalogo": "prod_colores_catalogo",
    "rutas_produccion": "prod_rutas_produccion",
    "servicios_produccion": "prod_servicios_produccion",
    "modelos": "prod_modelos",
    "registros": "prod_registros",
    "inventario": "prod_inventario",
    "inventario_ingresos": "prod_inventario_ingresos",
    "inventario_salidas": "prod_inventario_salidas",
    "inventario_ajustes": "prod_inventario_ajustes",
    "inventario_rollos": "prod_inventario_rollos",
    "personas_produccion": "prod_personas_produccion",
    "movimientos_produccion": "prod_movimientos_produccion",
    "mermas": "prod_mermas",
    "guias_remision": "prod_guias_remision",
}

async def migrate():
    print("=" * 60)
    print("INICIANDO MIGRACIÓN DE COLECCIONES")
    print("=" * 60)
    
    for old_name, new_name in COLLECTIONS_MAP.items():
        old_col = db[old_name]
        new_col = db[new_name]
        
        # Contar documentos en colección antigua
        old_count = await old_col.count_documents({})
        
        if old_count == 0:
            print(f"⚪ {old_name}: vacía, saltando...")
            continue
        
        print(f"\n🔄 Migrando {old_name} -> {new_name} ({old_count} documentos)")
        
        # Obtener todos los documentos
        docs = await old_col.find({}).to_list(None)
        
        if docs:
            # Insertar en nueva colección
            await new_col.insert_many(docs)
            new_count = await new_col.count_documents({})
            print(f"   ✅ Insertados {new_count} documentos en {new_name}")
            
            # Eliminar colección antigua
            await old_col.drop()
            print(f"   🗑️  Eliminada colección {old_name}")
    
    print("\n" + "=" * 60)
    print("✅ MIGRACIÓN COMPLETADA")
    print("=" * 60)
    
    # Mostrar resumen
    print("\nResumen de colecciones nuevas:")
    for new_name in COLLECTIONS_MAP.values():
        count = await db[new_name].count_documents({})
        if count > 0:
            print(f"   📁 {new_name}: {count} documentos")

if __name__ == "__main__":
    asyncio.run(migrate())
