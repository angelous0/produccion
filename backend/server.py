from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from datetime import datetime, timezone

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ==================== MODELOS PYDANTIC ====================

# Marca
class MarcaBase(BaseModel):
    nombre: str

class MarcaCreate(MarcaBase):
    pass

class Marca(MarcaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Tipo - relacionado con Marcas (muchos a muchos)
class TipoBase(BaseModel):
    nombre: str
    marca_ids: List[str] = []

class TipoCreate(TipoBase):
    pass

class Tipo(TipoBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Entalle - relacionado con Tipos (muchos a muchos)
class EntalleBase(BaseModel):
    nombre: str
    tipo_ids: List[str] = []

class EntalleCreate(EntalleBase):
    pass

class Entalle(EntalleBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Tela - relacionado con Entalles (muchos a muchos)
class TelaBase(BaseModel):
    nombre: str
    entalle_ids: List[str] = []

class TelaCreate(TelaBase):
    pass

class Tela(TelaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Hilo - relacionado con Telas (muchos a muchos)
class HiloBase(BaseModel):
    nombre: str
    tela_ids: List[str] = []

class HiloCreate(HiloBase):
    pass

class Hilo(HiloBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== TALLAS Y COLORES (TABLAS MAESTRAS) ====================

# Talla (tabla maestra)
class TallaBase(BaseModel):
    nombre: str
    orden: int = 0

class TallaCreate(TallaBase):
    pass

class Talla(TallaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Color (tabla maestra)
class ColorBase(BaseModel):
    nombre: str
    codigo_hex: str = ""

class ColorCreate(ColorBase):
    pass

class Color(ColorBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== MODELO ====================

class ModeloBase(BaseModel):
    nombre: str
    marca_id: str
    tipo_id: str
    entalle_id: str
    tela_id: str
    hilo_id: str

class ModeloCreate(ModeloBase):
    pass

class Modelo(ModeloBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ModeloConRelaciones(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    nombre: str
    marca_id: str
    tipo_id: str
    entalle_id: str
    tela_id: str
    hilo_id: str
    marca_nombre: Optional[str] = None
    tipo_nombre: Optional[str] = None
    entalle_nombre: Optional[str] = None
    tela_nombre: Optional[str] = None
    hilo_nombre: Optional[str] = None
    created_at: datetime

# ==================== REGISTRO DE PRODUCCIÓN ====================

# Estructura para cantidades por talla
class TallaCantidadItem(BaseModel):
    talla_id: str
    talla_nombre: str = ""
    cantidad: int = 0

# Estructura para distribución de colores por talla
class ColorDistribucion(BaseModel):
    color_id: str
    color_nombre: str = ""
    cantidad: int = 0

class TallaConColores(BaseModel):
    talla_id: str
    talla_nombre: str = ""
    cantidad_total: int = 0
    colores: List[ColorDistribucion] = []

# Registro de producción
class RegistroBase(BaseModel):
    n_corte: str
    modelo_id: str
    curva: str = ""
    estado: str = "Para Corte"
    urgente: bool = False

class RegistroCreate(RegistroBase):
    tallas: List[TallaCantidadItem] = []
    distribucion_colores: List[TallaConColores] = []

class Registro(RegistroBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tallas: List[TallaCantidadItem] = []
    distribucion_colores: List[TallaConColores] = []

class RegistroConRelaciones(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    n_corte: str
    modelo_id: str
    curva: str
    estado: str
    urgente: bool
    fecha_creacion: datetime
    tallas: List[TallaCantidadItem] = []
    distribucion_colores: List[TallaConColores] = []
    modelo_nombre: Optional[str] = None
    marca_nombre: Optional[str] = None
    tipo_nombre: Optional[str] = None
    entalle_nombre: Optional[str] = None
    tela_nombre: Optional[str] = None
    hilo_nombre: Optional[str] = None

# Lista de estados disponibles
ESTADOS_PRODUCCION = [
    "Para Corte",
    "Corte",
    "Para Costura",
    "Costura",
    "Para Atraque",
    "Atraque",
    "Para Lavandería",
    "Muestra Lavanderia",
    "Lavandería",
    "Para Acabado",
    "Acabado",
    "Almacén PT",
    "Tienda"
]

# ==================== ENDPOINTS MARCA ====================

@api_router.get("/marcas", response_model=List[Marca])
async def get_marcas():
    marcas = await db.marcas.find({}, {"_id": 0}).to_list(1000)
    for m in marcas:
        if isinstance(m.get('created_at'), str):
            m['created_at'] = datetime.fromisoformat(m['created_at'])
    return marcas

@api_router.post("/marcas", response_model=Marca)
async def create_marca(input: MarcaCreate):
    marca = Marca(**input.model_dump())
    doc = marca.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.marcas.insert_one(doc)
    return marca

@api_router.put("/marcas/{marca_id}", response_model=Marca)
async def update_marca(marca_id: str, input: MarcaCreate):
    result = await db.marcas.find_one({"id": marca_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    await db.marcas.update_one({"id": marca_id}, {"$set": {"nombre": input.nombre}})
    result['nombre'] = input.nombre
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Marca(**result)

@api_router.delete("/marcas/{marca_id}")
async def delete_marca(marca_id: str):
    result = await db.marcas.delete_one({"id": marca_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Marca no encontrada")
    return {"message": "Marca eliminada"}

# ==================== ENDPOINTS TIPO ====================

@api_router.get("/tipos", response_model=List[Tipo])
async def get_tipos(marca_id: str = None):
    query = {}
    if marca_id:
        query = {"marca_ids": marca_id}
    tipos = await db.tipos.find(query, {"_id": 0}).to_list(1000)
    for t in tipos:
        if isinstance(t.get('created_at'), str):
            t['created_at'] = datetime.fromisoformat(t['created_at'])
        if 'marca_ids' not in t:
            t['marca_ids'] = []
    return tipos

@api_router.post("/tipos", response_model=Tipo)
async def create_tipo(input: TipoCreate):
    tipo = Tipo(**input.model_dump())
    doc = tipo.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tipos.insert_one(doc)
    return tipo

@api_router.put("/tipos/{tipo_id}", response_model=Tipo)
async def update_tipo(tipo_id: str, input: TipoCreate):
    result = await db.tipos.find_one({"id": tipo_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    update_data = input.model_dump()
    await db.tipos.update_one({"id": tipo_id}, {"$set": update_data})
    result.update(update_data)
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Tipo(**result)

@api_router.delete("/tipos/{tipo_id}")
async def delete_tipo(tipo_id: str):
    result = await db.tipos.delete_one({"id": tipo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tipo no encontrado")
    return {"message": "Tipo eliminado"}

# ==================== ENDPOINTS ENTALLE ====================

@api_router.get("/entalles", response_model=List[Entalle])
async def get_entalles(tipo_id: str = None):
    query = {}
    if tipo_id:
        query = {"tipo_ids": tipo_id}
    entalles = await db.entalles.find(query, {"_id": 0}).to_list(1000)
    for e in entalles:
        if isinstance(e.get('created_at'), str):
            e['created_at'] = datetime.fromisoformat(e['created_at'])
        if 'tipo_ids' not in e:
            e['tipo_ids'] = []
    return entalles

@api_router.post("/entalles", response_model=Entalle)
async def create_entalle(input: EntalleCreate):
    entalle = Entalle(**input.model_dump())
    doc = entalle.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.entalles.insert_one(doc)
    return entalle

@api_router.put("/entalles/{entalle_id}", response_model=Entalle)
async def update_entalle(entalle_id: str, input: EntalleCreate):
    result = await db.entalles.find_one({"id": entalle_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Entalle no encontrado")
    update_data = input.model_dump()
    await db.entalles.update_one({"id": entalle_id}, {"$set": update_data})
    result.update(update_data)
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Entalle(**result)

@api_router.delete("/entalles/{entalle_id}")
async def delete_entalle(entalle_id: str):
    result = await db.entalles.delete_one({"id": entalle_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Entalle no encontrado")
    return {"message": "Entalle eliminado"}

# ==================== ENDPOINTS TELA ====================

@api_router.get("/telas", response_model=List[Tela])
async def get_telas(entalle_id: str = None):
    query = {}
    if entalle_id:
        query = {"entalle_ids": entalle_id}
    telas = await db.telas.find(query, {"_id": 0}).to_list(1000)
    for t in telas:
        if isinstance(t.get('created_at'), str):
            t['created_at'] = datetime.fromisoformat(t['created_at'])
        if 'entalle_ids' not in t:
            t['entalle_ids'] = []
    return telas

@api_router.post("/telas", response_model=Tela)
async def create_tela(input: TelaCreate):
    tela = Tela(**input.model_dump())
    doc = tela.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.telas.insert_one(doc)
    return tela

@api_router.put("/telas/{tela_id}", response_model=Tela)
async def update_tela(tela_id: str, input: TelaCreate):
    result = await db.telas.find_one({"id": tela_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Tela no encontrada")
    update_data = input.model_dump()
    await db.telas.update_one({"id": tela_id}, {"$set": update_data})
    result.update(update_data)
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Tela(**result)

@api_router.delete("/telas/{tela_id}")
async def delete_tela(tela_id: str):
    result = await db.telas.delete_one({"id": tela_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Tela no encontrada")
    return {"message": "Tela eliminada"}

# ==================== ENDPOINTS HILO ====================

@api_router.get("/hilos", response_model=List[Hilo])
async def get_hilos(tela_id: str = None):
    query = {}
    if tela_id:
        query = {"tela_ids": tela_id}
    hilos = await db.hilos.find(query, {"_id": 0}).to_list(1000)
    for h in hilos:
        if isinstance(h.get('created_at'), str):
            h['created_at'] = datetime.fromisoformat(h['created_at'])
        if 'tela_ids' not in h:
            h['tela_ids'] = []
    return hilos

@api_router.post("/hilos", response_model=Hilo)
async def create_hilo(input: HiloCreate):
    hilo = Hilo(**input.model_dump())
    doc = hilo.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.hilos.insert_one(doc)
    return hilo

@api_router.put("/hilos/{hilo_id}", response_model=Hilo)
async def update_hilo(hilo_id: str, input: HiloCreate):
    result = await db.hilos.find_one({"id": hilo_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Hilo no encontrado")
    update_data = input.model_dump()
    await db.hilos.update_one({"id": hilo_id}, {"$set": update_data})
    result.update(update_data)
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Hilo(**result)

@api_router.delete("/hilos/{hilo_id}")
async def delete_hilo(hilo_id: str):
    result = await db.hilos.delete_one({"id": hilo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Hilo no encontrado")
    return {"message": "Hilo eliminado"}

# ==================== ENDPOINTS TALLA (TABLA MAESTRA) ====================

@api_router.get("/tallas-catalogo", response_model=List[Talla])
async def get_tallas_catalogo():
    tallas = await db.tallas_catalogo.find({}, {"_id": 0}).to_list(1000)
    for t in tallas:
        if isinstance(t.get('created_at'), str):
            t['created_at'] = datetime.fromisoformat(t['created_at'])
    return sorted(tallas, key=lambda x: x.get('orden', 0))

@api_router.post("/tallas-catalogo", response_model=Talla)
async def create_talla_catalogo(input: TallaCreate):
    talla = Talla(**input.model_dump())
    doc = talla.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.tallas_catalogo.insert_one(doc)
    return talla

@api_router.put("/tallas-catalogo/{talla_id}", response_model=Talla)
async def update_talla_catalogo(talla_id: str, input: TallaCreate):
    result = await db.tallas_catalogo.find_one({"id": talla_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Talla no encontrada")
    await db.tallas_catalogo.update_one({"id": talla_id}, {"$set": input.model_dump()})
    result.update(input.model_dump())
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Talla(**result)

@api_router.delete("/tallas-catalogo/{talla_id}")
async def delete_talla_catalogo(talla_id: str):
    result = await db.tallas_catalogo.delete_one({"id": talla_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Talla no encontrada")
    return {"message": "Talla eliminada"}

# ==================== ENDPOINTS COLOR (TABLA MAESTRA) ====================

@api_router.get("/colores-catalogo", response_model=List[Color])
async def get_colores_catalogo():
    colores = await db.colores_catalogo.find({}, {"_id": 0}).to_list(1000)
    for c in colores:
        if isinstance(c.get('created_at'), str):
            c['created_at'] = datetime.fromisoformat(c['created_at'])
    return colores

@api_router.post("/colores-catalogo", response_model=Color)
async def create_color_catalogo(input: ColorCreate):
    color = Color(**input.model_dump())
    doc = color.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.colores_catalogo.insert_one(doc)
    return color

@api_router.put("/colores-catalogo/{color_id}", response_model=Color)
async def update_color_catalogo(color_id: str, input: ColorCreate):
    result = await db.colores_catalogo.find_one({"id": color_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Color no encontrado")
    await db.colores_catalogo.update_one({"id": color_id}, {"$set": input.model_dump()})
    result.update(input.model_dump())
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Color(**result)

@api_router.delete("/colores-catalogo/{color_id}")
async def delete_color_catalogo(color_id: str):
    result = await db.colores_catalogo.delete_one({"id": color_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Color no encontrado")
    return {"message": "Color eliminado"}

# ==================== ENDPOINTS MODELO ====================

@api_router.get("/modelos", response_model=List[ModeloConRelaciones])
async def get_modelos():
    modelos = await db.modelos.find({}, {"_id": 0}).to_list(1000)
    result = []
    for m in modelos:
        if isinstance(m.get('created_at'), str):
            m['created_at'] = datetime.fromisoformat(m['created_at'])
        
        marca = await db.marcas.find_one({"id": m.get('marca_id')}, {"_id": 0, "nombre": 1})
        tipo = await db.tipos.find_one({"id": m.get('tipo_id')}, {"_id": 0, "nombre": 1})
        entalle = await db.entalles.find_one({"id": m.get('entalle_id')}, {"_id": 0, "nombre": 1})
        tela = await db.telas.find_one({"id": m.get('tela_id')}, {"_id": 0, "nombre": 1})
        hilo = await db.hilos.find_one({"id": m.get('hilo_id')}, {"_id": 0, "nombre": 1})
        
        m['marca_nombre'] = marca['nombre'] if marca else None
        m['tipo_nombre'] = tipo['nombre'] if tipo else None
        m['entalle_nombre'] = entalle['nombre'] if entalle else None
        m['tela_nombre'] = tela['nombre'] if tela else None
        m['hilo_nombre'] = hilo['nombre'] if hilo else None
        
        result.append(ModeloConRelaciones(**m))
    return result

@api_router.post("/modelos", response_model=Modelo)
async def create_modelo(input: ModeloCreate):
    modelo = Modelo(**input.model_dump())
    doc = modelo.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.modelos.insert_one(doc)
    return modelo

@api_router.put("/modelos/{modelo_id}", response_model=Modelo)
async def update_modelo(modelo_id: str, input: ModeloCreate):
    result = await db.modelos.find_one({"id": modelo_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    update_data = input.model_dump()
    await db.modelos.update_one({"id": modelo_id}, {"$set": update_data})
    result.update(update_data)
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return Modelo(**result)

@api_router.delete("/modelos/{modelo_id}")
async def delete_modelo(modelo_id: str):
    result = await db.modelos.delete_one({"id": modelo_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Modelo no encontrado")
    return {"message": "Modelo eliminado"}

# ==================== ENDPOINTS REGISTRO ====================

@api_router.get("/estados")
async def get_estados():
    return {"estados": ESTADOS_PRODUCCION}

@api_router.get("/registros", response_model=List[RegistroConRelaciones])
async def get_registros():
    registros = await db.registros.find({}, {"_id": 0}).to_list(1000)
    result = []
    for r in registros:
        if isinstance(r.get('fecha_creacion'), str):
            r['fecha_creacion'] = datetime.fromisoformat(r['fecha_creacion'])
        
        modelo = await db.modelos.find_one({"id": r.get('modelo_id')}, {"_id": 0})
        if modelo:
            r['modelo_nombre'] = modelo.get('nombre')
            
            marca = await db.marcas.find_one({"id": modelo.get('marca_id')}, {"_id": 0, "nombre": 1})
            tipo = await db.tipos.find_one({"id": modelo.get('tipo_id')}, {"_id": 0, "nombre": 1})
            entalle = await db.entalles.find_one({"id": modelo.get('entalle_id')}, {"_id": 0, "nombre": 1})
            tela = await db.telas.find_one({"id": modelo.get('tela_id')}, {"_id": 0, "nombre": 1})
            hilo = await db.hilos.find_one({"id": modelo.get('hilo_id')}, {"_id": 0, "nombre": 1})
            
            r['marca_nombre'] = marca['nombre'] if marca else None
            r['tipo_nombre'] = tipo['nombre'] if tipo else None
            r['entalle_nombre'] = entalle['nombre'] if entalle else None
            r['tela_nombre'] = tela['nombre'] if tela else None
            r['hilo_nombre'] = hilo['nombre'] if hilo else None
        
        # Asegurar campos de tallas y colores
        if 'tallas' not in r:
            r['tallas'] = []
        if 'distribucion_colores' not in r:
            r['distribucion_colores'] = []
        
        # Actualizar nombres de tallas desde el catálogo
        for talla in r['tallas']:
            talla_cat = await db.tallas_catalogo.find_one({"id": talla.get('talla_id')}, {"_id": 0, "nombre": 1})
            if talla_cat:
                talla['talla_nombre'] = talla_cat['nombre']
        
        # Actualizar nombres de colores en distribución desde el catálogo
        for dist in r['distribucion_colores']:
            # Actualizar nombre de talla
            talla_cat = await db.tallas_catalogo.find_one({"id": dist.get('talla_id')}, {"_id": 0, "nombre": 1})
            if talla_cat:
                dist['talla_nombre'] = talla_cat['nombre']
            # Actualizar nombres de colores
            for color in dist.get('colores', []):
                color_cat = await db.colores_catalogo.find_one({"id": color.get('color_id')}, {"_id": 0, "nombre": 1})
                if color_cat:
                    color['color_nombre'] = color_cat['nombre']
            
        result.append(RegistroConRelaciones(**r))
    return result

@api_router.get("/registros/{registro_id}", response_model=RegistroConRelaciones)
async def get_registro(registro_id: str):
    r = await db.registros.find_one({"id": registro_id}, {"_id": 0})
    if not r:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    if isinstance(r.get('fecha_creacion'), str):
        r['fecha_creacion'] = datetime.fromisoformat(r['fecha_creacion'])
    
    modelo = await db.modelos.find_one({"id": r.get('modelo_id')}, {"_id": 0})
    if modelo:
        r['modelo_nombre'] = modelo.get('nombre')
        
        marca = await db.marcas.find_one({"id": modelo.get('marca_id')}, {"_id": 0, "nombre": 1})
        tipo = await db.tipos.find_one({"id": modelo.get('tipo_id')}, {"_id": 0, "nombre": 1})
        entalle = await db.entalles.find_one({"id": modelo.get('entalle_id')}, {"_id": 0, "nombre": 1})
        tela = await db.telas.find_one({"id": modelo.get('tela_id')}, {"_id": 0, "nombre": 1})
        hilo = await db.hilos.find_one({"id": modelo.get('hilo_id')}, {"_id": 0, "nombre": 1})
        
        r['marca_nombre'] = marca['nombre'] if marca else None
        r['tipo_nombre'] = tipo['nombre'] if tipo else None
        r['entalle_nombre'] = entalle['nombre'] if entalle else None
        r['tela_nombre'] = tela['nombre'] if tela else None
        r['hilo_nombre'] = hilo['nombre'] if hilo else None
    
    if 'tallas' not in r:
        r['tallas'] = []
    if 'distribucion_colores' not in r:
        r['distribucion_colores'] = []
    
    # Actualizar nombres de tallas desde el catálogo
    for talla in r['tallas']:
        talla_cat = await db.tallas_catalogo.find_one({"id": talla.get('talla_id')}, {"_id": 0, "nombre": 1})
        if talla_cat:
            talla['talla_nombre'] = talla_cat['nombre']
    
    # Actualizar nombres de colores en distribución desde el catálogo
    for dist in r['distribucion_colores']:
        talla_cat = await db.tallas_catalogo.find_one({"id": dist.get('talla_id')}, {"_id": 0, "nombre": 1})
        if talla_cat:
            dist['talla_nombre'] = talla_cat['nombre']
        for color in dist.get('colores', []):
            color_cat = await db.colores_catalogo.find_one({"id": color.get('color_id')}, {"_id": 0, "nombre": 1})
            if color_cat:
                color['color_nombre'] = color_cat['nombre']
    
    return RegistroConRelaciones(**r)

@api_router.post("/registros", response_model=Registro)
async def create_registro(input: RegistroCreate):
    registro = Registro(**input.model_dump())
    doc = registro.model_dump()
    doc['fecha_creacion'] = doc['fecha_creacion'].isoformat()
    await db.registros.insert_one(doc)
    return registro

@api_router.put("/registros/{registro_id}", response_model=Registro)
async def update_registro(registro_id: str, input: RegistroCreate):
    result = await db.registros.find_one({"id": registro_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    update_data = input.model_dump()
    await db.registros.update_one({"id": registro_id}, {"$set": update_data})
    result.update(update_data)
    if isinstance(result.get('fecha_creacion'), str):
        result['fecha_creacion'] = datetime.fromisoformat(result['fecha_creacion'])
    return Registro(**result)

@api_router.delete("/registros/{registro_id}")
async def delete_registro(registro_id: str):
    result = await db.registros.delete_one({"id": registro_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    return {"message": "Registro eliminado"}

# ==================== ENDPOINTS ESTADÍSTICAS ====================

@api_router.get("/stats")
async def get_stats():
    marcas_count = await db.marcas.count_documents({})
    tipos_count = await db.tipos.count_documents({})
    entalles_count = await db.entalles.count_documents({})
    telas_count = await db.telas.count_documents({})
    hilos_count = await db.hilos.count_documents({})
    modelos_count = await db.modelos.count_documents({})
    registros_count = await db.registros.count_documents({})
    registros_urgentes = await db.registros.count_documents({"urgente": True})
    tallas_count = await db.tallas_catalogo.count_documents({})
    colores_count = await db.colores_catalogo.count_documents({})
    
    # Stats de inventario
    inventario_items = await db.inventario.count_documents({})
    ingresos_count = await db.inventario_ingresos.count_documents({})
    salidas_count = await db.inventario_salidas.count_documents({})
    ajustes_count = await db.inventario_ajustes.count_documents({})
    
    estados_count = {}
    for estado in ESTADOS_PRODUCCION:
        count = await db.registros.count_documents({"estado": estado})
        estados_count[estado] = count
    
    return {
        "marcas": marcas_count,
        "tipos": tipos_count,
        "entalles": entalles_count,
        "telas": telas_count,
        "hilos": hilos_count,
        "modelos": modelos_count,
        "registros": registros_count,
        "registros_urgentes": registros_urgentes,
        "tallas": tallas_count,
        "colores": colores_count,
        "estados_count": estados_count,
        "inventario_items": inventario_items,
        "ingresos_count": ingresos_count,
        "salidas_count": salidas_count,
        "ajustes_count": ajustes_count
    }

# ==================== INVENTARIO FIFO ====================

# Categorías de inventario
CATEGORIAS_INVENTARIO = ["Telas", "Avios", "Otros"]

# Modelos de Inventario

class ItemInventarioBase(BaseModel):
    codigo: str
    nombre: str
    descripcion: str = ""
    categoria: str = "Otros"  # Telas, Avios, Otros
    unidad_medida: str = "unidad"
    stock_minimo: int = 0
    control_por_rollos: bool = False  # Solo para Telas

class ItemInventarioCreate(ItemInventarioBase):
    pass

class ItemInventario(ItemInventarioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stock_actual: float = 0  # Cambiado a float para metraje
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ItemInventarioConStock(ItemInventario):
    lotes: List[dict] = []

# Modelo de Rollo (para telas con control por rollos)
class RolloBase(BaseModel):
    item_id: str
    ingreso_id: str
    numero_rollo: str
    metraje: float
    ancho: float = 0.0
    tono: str = ""
    observaciones: str = ""

class RolloCreate(RolloBase):
    pass

class Rollo(RolloBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    metraje_disponible: float = 0.0  # Para FIFO de rollos
    activo: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class RolloConDetalles(Rollo):
    item_nombre: str = ""
    item_codigo: str = ""

# Ingreso de Inventario (Entrada)
class IngresoInventarioBase(BaseModel):
    item_id: str
    cantidad: float  # Cambiado a float para metraje
    costo_unitario: float = 0.0
    proveedor: str = ""
    numero_documento: str = ""
    observaciones: str = ""

class IngresoInventarioCreate(IngresoInventarioBase):
    rollos: List[dict] = []  # Lista de rollos si el item tiene control_por_rollos

class IngresoInventario(IngresoInventarioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cantidad_disponible: float = 0  # Para FIFO, cantidad aún disponible de este lote

class IngresoConDetalles(IngresoInventario):
    item_nombre: str = ""
    item_codigo: str = ""
    rollos_count: int = 0

# Salida de Inventario (vinculada a Registro)
class SalidaInventarioBase(BaseModel):
    item_id: str
    cantidad: float  # Cambiado a float para metraje
    registro_id: Optional[str] = None
    observaciones: str = ""
    rollo_id: Optional[str] = None  # Si es salida de un rollo específico

class SalidaInventarioCreate(SalidaInventarioBase):
    pass

class SalidaInventario(SalidaInventarioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    costo_total: float = 0.0  # Calculado según FIFO
    detalle_fifo: List[dict] = []  # Detalle de qué lotes se usaron

class SalidaConDetalles(SalidaInventario):
    item_nombre: str = ""
    item_codigo: str = ""
    registro_n_corte: Optional[str] = None
    rollo_numero: Optional[str] = None

# Ajuste de Inventario
class AjusteInventarioBase(BaseModel):
    item_id: str
    tipo: str  # "entrada" o "salida"
    cantidad: float  # Cambiado a float
    motivo: str = ""
    observaciones: str = ""

class AjusteInventarioCreate(AjusteInventarioBase):
    pass

class AjusteInventario(AjusteInventarioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AjusteConDetalles(AjusteInventario):
    item_nombre: str = ""
    item_codigo: str = ""

# ==================== ENDPOINTS ITEMS INVENTARIO ====================

@api_router.get("/inventario", response_model=List[ItemInventario])
async def get_inventario():
    items = await db.inventario.find({}, {"_id": 0}).to_list(1000)
    for item in items:
        if isinstance(item.get('created_at'), str):
            item['created_at'] = datetime.fromisoformat(item['created_at'])
    return items

@api_router.get("/inventario-categorias")
async def get_categorias():
    """Obtener lista de categorías disponibles"""
    return {"categorias": CATEGORIAS_INVENTARIO}

@api_router.get("/inventario/{item_id}")
async def get_item_inventario(item_id: str):
    item = await db.inventario.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    if isinstance(item.get('created_at'), str):
        item['created_at'] = datetime.fromisoformat(item['created_at'])
    
    # Obtener lotes disponibles (FIFO)
    ingresos = await db.inventario_ingresos.find(
        {"item_id": item_id, "cantidad_disponible": {"$gt": 0}},
        {"_id": 0}
    ).sort("fecha", 1).to_list(100)
    
    for ing in ingresos:
        if isinstance(ing.get('fecha'), str):
            ing['fecha'] = datetime.fromisoformat(ing['fecha'])
    
    item['lotes'] = ingresos
    
    # Si tiene control por rollos, obtener rollos activos
    if item.get('control_por_rollos'):
        rollos = await db.inventario_rollos.find(
            {"item_id": item_id, "activo": True, "metraje_disponible": {"$gt": 0}},
            {"_id": 0}
        ).to_list(500)
        for rollo in rollos:
            if isinstance(rollo.get('created_at'), str):
                rollo['created_at'] = datetime.fromisoformat(rollo['created_at'])
        item['rollos'] = rollos
    
    return item

@api_router.post("/inventario", response_model=ItemInventario)
async def create_item_inventario(input: ItemInventarioCreate):
    # Verificar código único
    existing = await db.inventario.find_one({"codigo": input.codigo})
    if existing:
        raise HTTPException(status_code=400, detail="El código ya existe")
    
    item = ItemInventario(**input.model_dump())
    doc = item.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.inventario.insert_one(doc)
    return item

@api_router.put("/inventario/{item_id}", response_model=ItemInventario)
async def update_item_inventario(item_id: str, input: ItemInventarioCreate):
    result = await db.inventario.find_one({"id": item_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    # Verificar código único si cambió
    if input.codigo != result.get('codigo'):
        existing = await db.inventario.find_one({"codigo": input.codigo, "id": {"$ne": item_id}})
        if existing:
            raise HTTPException(status_code=400, detail="El código ya existe")
    
    update_data = input.model_dump()
    await db.inventario.update_one({"id": item_id}, {"$set": update_data})
    result.update(update_data)
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return ItemInventario(**result)

@api_router.delete("/inventario/{item_id}")
async def delete_item_inventario(item_id: str):
    result = await db.inventario.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    # También eliminar movimientos relacionados
    await db.inventario_ingresos.delete_many({"item_id": item_id})
    await db.inventario_salidas.delete_many({"item_id": item_id})
    await db.inventario_ajustes.delete_many({"item_id": item_id})
    return {"message": "Item eliminado"}

# ==================== ENDPOINTS INGRESOS ====================

@api_router.get("/inventario-ingresos", response_model=List[IngresoConDetalles])
async def get_ingresos():
    ingresos = await db.inventario_ingresos.find({}, {"_id": 0}).to_list(1000)
    result = []
    for ing in ingresos:
        if isinstance(ing.get('fecha'), str):
            ing['fecha'] = datetime.fromisoformat(ing['fecha'])
        
        item = await db.inventario.find_one({"id": ing.get('item_id')}, {"_id": 0, "nombre": 1, "codigo": 1})
        ing['item_nombre'] = item['nombre'] if item else ""
        ing['item_codigo'] = item['codigo'] if item else ""
        
        # Contar rollos de este ingreso
        rollos_count = await db.inventario_rollos.count_documents({"ingreso_id": ing['id']})
        ing['rollos_count'] = rollos_count
        
        result.append(IngresoConDetalles(**ing))
    return sorted(result, key=lambda x: x.fecha, reverse=True)

@api_router.post("/inventario-ingresos", response_model=IngresoInventario)
async def create_ingreso(input: IngresoInventarioCreate):
    # Verificar que el item existe
    item = await db.inventario.find_one({"id": input.item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
    
    # Si tiene control por rollos, la cantidad se calcula de los rollos
    rollos_data = input.rollos if hasattr(input, 'rollos') else []
    
    if item.get('control_por_rollos') and rollos_data:
        # Calcular cantidad total desde los rollos
        cantidad_total = sum(r.get('metraje', 0) for r in rollos_data)
        ingreso_data = input.model_dump()
        ingreso_data['cantidad'] = cantidad_total
        ingreso_data.pop('rollos', None)
        ingreso = IngresoInventario(**ingreso_data)
    else:
        ingreso_data = input.model_dump()
        ingreso_data.pop('rollos', None)
        ingreso = IngresoInventario(**ingreso_data)
    
    ingreso.cantidad_disponible = ingreso.cantidad
    
    doc = ingreso.model_dump()
    doc['fecha'] = doc['fecha'].isoformat()
    await db.inventario_ingresos.insert_one(doc)
    
    # Si hay rollos, crearlos
    if item.get('control_por_rollos') and rollos_data:
        for rollo_data in rollos_data:
            rollo = Rollo(
                item_id=input.item_id,
                ingreso_id=ingreso.id,
                numero_rollo=rollo_data.get('numero_rollo', ''),
                metraje=rollo_data.get('metraje', 0),
                ancho=rollo_data.get('ancho', 0),
                tono=rollo_data.get('tono', ''),
                observaciones=rollo_data.get('observaciones', ''),
                metraje_disponible=rollo_data.get('metraje', 0)
            )
            rollo_doc = rollo.model_dump()
            rollo_doc['created_at'] = rollo_doc['created_at'].isoformat()
            await db.inventario_rollos.insert_one(rollo_doc)
    
    # Actualizar stock del item
    await db.inventario.update_one(
        {"id": input.item_id},
        {"$inc": {"stock_actual": ingreso.cantidad}}
    )
    
    return ingreso

@api_router.delete("/inventario-ingresos/{ingreso_id}")
async def delete_ingreso(ingreso_id: str):
    ingreso = await db.inventario_ingresos.find_one({"id": ingreso_id}, {"_id": 0})
    if not ingreso:
        raise HTTPException(status_code=404, detail="Ingreso no encontrado")
    
    # Solo se puede eliminar si la cantidad disponible es igual a la cantidad original
    if ingreso.get('cantidad_disponible', 0) != ingreso.get('cantidad', 0):
        raise HTTPException(status_code=400, detail="No se puede eliminar un ingreso que ya tiene salidas")
    
    # Eliminar rollos asociados
    await db.inventario_rollos.delete_many({"ingreso_id": ingreso_id})
    
    await db.inventario_ingresos.delete_one({"id": ingreso_id})
    
    # Restar del stock
    await db.inventario.update_one(
        {"id": ingreso['item_id']},
        {"$inc": {"stock_actual": -ingreso['cantidad']}}
    )
    
    return {"message": "Ingreso eliminado"}

# ==================== ENDPOINTS ROLLOS ====================

@api_router.get("/inventario-rollos")
async def get_rollos(item_id: str = None, activo: bool = None):
    query = {}
    if item_id:
        query['item_id'] = item_id
    if activo is not None:
        query['activo'] = activo
        if activo:
            query['metraje_disponible'] = {"$gt": 0}
    
    rollos = await db.inventario_rollos.find(query, {"_id": 0}).to_list(1000)
    result = []
    for rollo in rollos:
        if isinstance(rollo.get('created_at'), str):
            rollo['created_at'] = datetime.fromisoformat(rollo['created_at'])
        
        item = await db.inventario.find_one({"id": rollo.get('item_id')}, {"_id": 0, "nombre": 1, "codigo": 1})
        rollo['item_nombre'] = item['nombre'] if item else ""
        rollo['item_codigo'] = item['codigo'] if item else ""
        
        result.append(rollo)
    return sorted(result, key=lambda x: x['created_at'], reverse=True)

@api_router.get("/inventario-rollos/{rollo_id}")
async def get_rollo(rollo_id: str):
    rollo = await db.inventario_rollos.find_one({"id": rollo_id}, {"_id": 0})
    if not rollo:
        raise HTTPException(status_code=404, detail="Rollo no encontrado")
    
    if isinstance(rollo.get('created_at'), str):
        rollo['created_at'] = datetime.fromisoformat(rollo['created_at'])
    
    item = await db.inventario.find_one({"id": rollo.get('item_id')}, {"_id": 0, "nombre": 1, "codigo": 1})
    rollo['item_nombre'] = item['nombre'] if item else ""
    rollo['item_codigo'] = item['codigo'] if item else ""
    
    return rollo

# ==================== ENDPOINTS SALIDAS ====================

@api_router.get("/inventario-salidas", response_model=List[SalidaConDetalles])
async def get_salidas(registro_id: str = None):
    query = {}
    if registro_id:
        query['registro_id'] = registro_id
    
    salidas = await db.inventario_salidas.find(query, {"_id": 0}).to_list(1000)
    result = []
    for sal in salidas:
        if isinstance(sal.get('fecha'), str):
            sal['fecha'] = datetime.fromisoformat(sal['fecha'])
        
        item = await db.inventario.find_one({"id": sal.get('item_id')}, {"_id": 0, "nombre": 1, "codigo": 1})
        sal['item_nombre'] = item['nombre'] if item else ""
        sal['item_codigo'] = item['codigo'] if item else ""
        
        if sal.get('registro_id'):
            registro = await db.registros.find_one({"id": sal.get('registro_id')}, {"_id": 0, "n_corte": 1})
            sal['registro_n_corte'] = registro['n_corte'] if registro else None
        
        # Si tiene rollo_id, obtener número de rollo
        if sal.get('rollo_id'):
            rollo = await db.inventario_rollos.find_one({"id": sal.get('rollo_id')}, {"_id": 0, "numero_rollo": 1})
            sal['rollo_numero'] = rollo['numero_rollo'] if rollo else None
        
        result.append(SalidaConDetalles(**sal))
    return sorted(result, key=lambda x: x.fecha, reverse=True)

@api_router.post("/inventario-salidas", response_model=SalidaInventario)
async def create_salida(input: SalidaInventarioCreate):
    # Verificar que el item existe
    item = await db.inventario.find_one({"id": input.item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
    
    # Verificar stock suficiente
    if item.get('stock_actual', 0) < input.cantidad:
        raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {item.get('stock_actual', 0)}")
    
    # Si hay registro_id, verificar que existe
    if input.registro_id:
        registro = await db.registros.find_one({"id": input.registro_id})
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    # Si es salida de un rollo específico
    if input.rollo_id:
        rollo = await db.inventario_rollos.find_one({"id": input.rollo_id}, {"_id": 0})
        if not rollo:
            raise HTTPException(status_code=404, detail="Rollo no encontrado")
        if rollo.get('metraje_disponible', 0) < input.cantidad:
            raise HTTPException(status_code=400, detail=f"Metraje insuficiente en rollo. Disponible: {rollo.get('metraje_disponible', 0)}")
        
        # Obtener el ingreso del rollo para el costo
        ingreso = await db.inventario_ingresos.find_one({"id": rollo['ingreso_id']}, {"_id": 0})
        costo_unitario = ingreso.get('costo_unitario', 0) if ingreso else 0
        costo_total = input.cantidad * costo_unitario
        
        detalle_fifo = [{
            "rollo_id": input.rollo_id,
            "cantidad": input.cantidad,
            "costo_unitario": costo_unitario,
            "numero_rollo": rollo.get('numero_rollo', '')
        }]
        
        # Actualizar metraje disponible del rollo
        await db.inventario_rollos.update_one(
            {"id": input.rollo_id},
            {"$inc": {"metraje_disponible": -input.cantidad}}
        )
        
        # Actualizar cantidad disponible del ingreso
        await db.inventario_ingresos.update_one(
            {"id": rollo['ingreso_id']},
            {"$inc": {"cantidad_disponible": -input.cantidad}}
        )
    else:
        # FIFO normal: obtener lotes ordenados por fecha y consumir
        ingresos = await db.inventario_ingresos.find(
            {"item_id": input.item_id, "cantidad_disponible": {"$gt": 0}},
            {"_id": 0}
        ).sort("fecha", 1).to_list(100)
        
        cantidad_restante = input.cantidad
        costo_total = 0.0
        detalle_fifo = []
        
        for ingreso in ingresos:
            if cantidad_restante <= 0:
                break
            
            disponible = ingreso.get('cantidad_disponible', 0)
            consumir = min(disponible, cantidad_restante)
            
            costo_unitario = ingreso.get('costo_unitario', 0)
            costo_total += consumir * costo_unitario
            
            detalle_fifo.append({
                "ingreso_id": ingreso['id'],
                "cantidad": consumir,
                "costo_unitario": costo_unitario,
                "fecha_ingreso": ingreso.get('fecha')
            })
            
            # Actualizar cantidad disponible del ingreso
            await db.inventario_ingresos.update_one(
                {"id": ingreso['id']},
                {"$inc": {"cantidad_disponible": -consumir}}
            )
            
            cantidad_restante -= consumir
        
        if cantidad_restante > 0:
            raise HTTPException(status_code=400, detail="No hay suficiente stock en los lotes")
    
    salida = SalidaInventario(**input.model_dump())
    salida.costo_total = costo_total
    salida.detalle_fifo = detalle_fifo
    
    doc = salida.model_dump()
    doc['fecha'] = doc['fecha'].isoformat()
    await db.inventario_salidas.insert_one(doc)
    
    # Actualizar stock del item
    await db.inventario.update_one(
        {"id": input.item_id},
        {"$inc": {"stock_actual": -input.cantidad}}
    )
    
    return salida

@api_router.delete("/inventario-salidas/{salida_id}")
async def delete_salida(salida_id: str):
    salida = await db.inventario_salidas.find_one({"id": salida_id}, {"_id": 0})
    if not salida:
        raise HTTPException(status_code=404, detail="Salida no encontrada")
    
    # Revertir FIFO: devolver cantidades a los lotes
    for detalle in salida.get('detalle_fifo', []):
        if detalle.get('rollo_id'):
            # Si era salida de rollo, restaurar metraje del rollo
            await db.inventario_rollos.update_one(
                {"id": detalle['rollo_id']},
                {"$inc": {"metraje_disponible": detalle['cantidad']}}
            )
            # Obtener el ingreso_id del rollo
            rollo = await db.inventario_rollos.find_one({"id": detalle['rollo_id']}, {"_id": 0, "ingreso_id": 1})
            if rollo:
                await db.inventario_ingresos.update_one(
                    {"id": rollo['ingreso_id']},
                    {"$inc": {"cantidad_disponible": detalle['cantidad']}}
                )
        elif detalle.get('ingreso_id'):
            await db.inventario_ingresos.update_one(
                {"id": detalle['ingreso_id']},
                {"$inc": {"cantidad_disponible": detalle['cantidad']}}
            )
    
    await db.inventario_salidas.delete_one({"id": salida_id})
    
    # Restaurar stock
    await db.inventario.update_one(
        {"id": salida['item_id']},
        {"$inc": {"stock_actual": salida['cantidad']}}
    )
    
    return {"message": "Salida eliminada y stock restaurado"}

# ==================== ENDPOINTS AJUSTES ====================

@api_router.get("/inventario-ajustes", response_model=List[AjusteConDetalles])
async def get_ajustes():
    ajustes = await db.inventario_ajustes.find({}, {"_id": 0}).to_list(1000)
    result = []
    for aj in ajustes:
        if isinstance(aj.get('fecha'), str):
            aj['fecha'] = datetime.fromisoformat(aj['fecha'])
        
        item = await db.inventario.find_one({"id": aj.get('item_id')}, {"_id": 0, "nombre": 1, "codigo": 1})
        aj['item_nombre'] = item['nombre'] if item else ""
        aj['item_codigo'] = item['codigo'] if item else ""
        
        result.append(AjusteConDetalles(**aj))
    return sorted(result, key=lambda x: x.fecha, reverse=True)

@api_router.post("/inventario-ajustes", response_model=AjusteInventario)
async def create_ajuste(input: AjusteInventarioCreate):
    # Verificar que el item existe
    item = await db.inventario.find_one({"id": input.item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
    
    # Verificar tipo válido
    if input.tipo not in ["entrada", "salida"]:
        raise HTTPException(status_code=400, detail="Tipo debe ser 'entrada' o 'salida'")
    
    # Si es salida, verificar stock suficiente
    if input.tipo == "salida":
        if item.get('stock_actual', 0) < input.cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {item.get('stock_actual', 0)}")
    
    ajuste = AjusteInventario(**input.model_dump())
    doc = ajuste.model_dump()
    doc['fecha'] = doc['fecha'].isoformat()
    await db.inventario_ajustes.insert_one(doc)
    
    # Actualizar stock según tipo
    incremento = input.cantidad if input.tipo == "entrada" else -input.cantidad
    await db.inventario.update_one(
        {"id": input.item_id},
        {"$inc": {"stock_actual": incremento}}
    )
    
    return ajuste

@api_router.delete("/inventario-ajustes/{ajuste_id}")
async def delete_ajuste(ajuste_id: str):
    ajuste = await db.inventario_ajustes.find_one({"id": ajuste_id}, {"_id": 0})
    if not ajuste:
        raise HTTPException(status_code=404, detail="Ajuste no encontrado")
    
    # Revertir el ajuste
    incremento = -ajuste['cantidad'] if ajuste['tipo'] == "entrada" else ajuste['cantidad']
    
    # Verificar que no quede negativo si era entrada
    if ajuste['tipo'] == "entrada":
        item = await db.inventario.find_one({"id": ajuste['item_id']}, {"_id": 0})
        if item and item.get('stock_actual', 0) < ajuste['cantidad']:
            raise HTTPException(status_code=400, detail="No se puede eliminar: dejaría el stock negativo")
    
    await db.inventario_ajustes.delete_one({"id": ajuste_id})
    
    await db.inventario.update_one(
        {"id": ajuste['item_id']},
        {"$inc": {"stock_actual": incremento}}
    )
    
    return {"message": "Ajuste eliminado"}

# ==================== ENDPOINTS REPORTES INVENTARIO ====================

@api_router.get("/inventario-movimientos")
async def get_movimientos(
    item_id: str = None,
    tipo: str = None,  # "ingreso", "salida", "ajuste"
    fecha_desde: str = None,
    fecha_hasta: str = None
):
    """Reporte general de todos los movimientos de inventario"""
    movimientos = []
    
    # Filtrar ingresos
    if not tipo or tipo == "ingreso":
        query_ingresos = {}
        if item_id:
            query_ingresos['item_id'] = item_id
        
        ingresos = await db.inventario_ingresos.find(query_ingresos, {"_id": 0}).to_list(5000)
        for ing in ingresos:
            if isinstance(ing.get('fecha'), str):
                ing['fecha'] = datetime.fromisoformat(ing['fecha'])
            
            # Filtrar por fecha
            if fecha_desde:
                fecha_d = datetime.fromisoformat(fecha_desde)
                if ing['fecha'] < fecha_d:
                    continue
            if fecha_hasta:
                fecha_h = datetime.fromisoformat(fecha_hasta)
                if ing['fecha'] > fecha_h:
                    continue
            
            item = await db.inventario.find_one({"id": ing.get('item_id')}, {"_id": 0, "nombre": 1, "codigo": 1})
            movimientos.append({
                "id": ing['id'],
                "fecha": ing['fecha'].isoformat(),
                "tipo": "ingreso",
                "item_id": ing['item_id'],
                "item_codigo": item['codigo'] if item else "",
                "item_nombre": item['nombre'] if item else "",
                "cantidad": ing['cantidad'],
                "costo_unitario": ing.get('costo_unitario', 0),
                "costo_total": ing['cantidad'] * ing.get('costo_unitario', 0),
                "proveedor": ing.get('proveedor', ''),
                "documento": ing.get('numero_documento', ''),
                "observaciones": ing.get('observaciones', ''),
                "registro_n_corte": None
            })
    
    # Filtrar salidas
    if not tipo or tipo == "salida":
        query_salidas = {}
        if item_id:
            query_salidas['item_id'] = item_id
        
        salidas = await db.inventario_salidas.find(query_salidas, {"_id": 0}).to_list(5000)
        for sal in salidas:
            if isinstance(sal.get('fecha'), str):
                sal['fecha'] = datetime.fromisoformat(sal['fecha'])
            
            if fecha_desde:
                fecha_d = datetime.fromisoformat(fecha_desde)
                if sal['fecha'] < fecha_d:
                    continue
            if fecha_hasta:
                fecha_h = datetime.fromisoformat(fecha_hasta)
                if sal['fecha'] > fecha_h:
                    continue
            
            item = await db.inventario.find_one({"id": sal.get('item_id')}, {"_id": 0, "nombre": 1, "codigo": 1})
            registro_n_corte = None
            if sal.get('registro_id'):
                registro = await db.registros.find_one({"id": sal.get('registro_id')}, {"_id": 0, "n_corte": 1})
                registro_n_corte = registro['n_corte'] if registro else None
            
            movimientos.append({
                "id": sal['id'],
                "fecha": sal['fecha'].isoformat(),
                "tipo": "salida",
                "item_id": sal['item_id'],
                "item_codigo": item['codigo'] if item else "",
                "item_nombre": item['nombre'] if item else "",
                "cantidad": -sal['cantidad'],  # Negativo para salidas
                "costo_unitario": sal.get('costo_total', 0) / sal['cantidad'] if sal['cantidad'] > 0 else 0,
                "costo_total": sal.get('costo_total', 0),
                "proveedor": "",
                "documento": "",
                "observaciones": sal.get('observaciones', ''),
                "registro_n_corte": registro_n_corte
            })
    
    # Filtrar ajustes
    if not tipo or tipo == "ajuste":
        query_ajustes = {}
        if item_id:
            query_ajustes['item_id'] = item_id
        
        ajustes = await db.inventario_ajustes.find(query_ajustes, {"_id": 0}).to_list(5000)
        for aj in ajustes:
            if isinstance(aj.get('fecha'), str):
                aj['fecha'] = datetime.fromisoformat(aj['fecha'])
            
            if fecha_desde:
                fecha_d = datetime.fromisoformat(fecha_desde)
                if aj['fecha'] < fecha_d:
                    continue
            if fecha_hasta:
                fecha_h = datetime.fromisoformat(fecha_hasta)
                if aj['fecha'] > fecha_h:
                    continue
            
            item = await db.inventario.find_one({"id": aj.get('item_id')}, {"_id": 0, "nombre": 1, "codigo": 1})
            cantidad = aj['cantidad'] if aj['tipo'] == "entrada" else -aj['cantidad']
            
            movimientos.append({
                "id": aj['id'],
                "fecha": aj['fecha'].isoformat(),
                "tipo": f"ajuste_{aj['tipo']}",
                "item_id": aj['item_id'],
                "item_codigo": item['codigo'] if item else "",
                "item_nombre": item['nombre'] if item else "",
                "cantidad": cantidad,
                "costo_unitario": 0,
                "costo_total": 0,
                "proveedor": "",
                "documento": "",
                "observaciones": f"{aj.get('motivo', '')} - {aj.get('observaciones', '')}".strip(' - '),
                "registro_n_corte": None
            })
    
    # Ordenar por fecha descendente
    movimientos.sort(key=lambda x: x['fecha'], reverse=True)
    return movimientos


@api_router.get("/inventario-kardex/{item_id}")
async def get_kardex(item_id: str):
    """Kardex de un item específico - historial con saldos"""
    
    # Verificar que el item existe
    item = await db.inventario.find_one({"id": item_id}, {"_id": 0})
    if not item:
        raise HTTPException(status_code=404, detail="Item no encontrado")
    
    movimientos = []
    
    # Obtener ingresos
    ingresos = await db.inventario_ingresos.find({"item_id": item_id}, {"_id": 0}).to_list(5000)
    for ing in ingresos:
        if isinstance(ing.get('fecha'), str):
            ing['fecha'] = datetime.fromisoformat(ing['fecha'])
        movimientos.append({
            "fecha": ing['fecha'],
            "tipo": "Ingreso",
            "documento": ing.get('numero_documento', '') or ing.get('proveedor', ''),
            "entrada": ing['cantidad'],
            "salida": 0,
            "costo_unitario": ing.get('costo_unitario', 0),
            "costo_total": ing['cantidad'] * ing.get('costo_unitario', 0),
            "observaciones": ing.get('observaciones', ''),
            "id": ing['id']
        })
    
    # Obtener salidas
    salidas = await db.inventario_salidas.find({"item_id": item_id}, {"_id": 0}).to_list(5000)
    for sal in salidas:
        if isinstance(sal.get('fecha'), str):
            sal['fecha'] = datetime.fromisoformat(sal['fecha'])
        
        documento = ""
        if sal.get('registro_id'):
            registro = await db.registros.find_one({"id": sal.get('registro_id')}, {"_id": 0, "n_corte": 1})
            documento = f"Corte #{registro['n_corte']}" if registro else ""
        
        movimientos.append({
            "fecha": sal['fecha'],
            "tipo": "Salida",
            "documento": documento,
            "entrada": 0,
            "salida": sal['cantidad'],
            "costo_unitario": sal.get('costo_total', 0) / sal['cantidad'] if sal['cantidad'] > 0 else 0,
            "costo_total": sal.get('costo_total', 0),
            "observaciones": sal.get('observaciones', ''),
            "id": sal['id']
        })
    
    # Obtener ajustes
    ajustes = await db.inventario_ajustes.find({"item_id": item_id}, {"_id": 0}).to_list(5000)
    for aj in ajustes:
        if isinstance(aj.get('fecha'), str):
            aj['fecha'] = datetime.fromisoformat(aj['fecha'])
        
        es_entrada = aj['tipo'] == "entrada"
        movimientos.append({
            "fecha": aj['fecha'],
            "tipo": f"Ajuste ({aj['tipo']})",
            "documento": aj.get('motivo', ''),
            "entrada": aj['cantidad'] if es_entrada else 0,
            "salida": aj['cantidad'] if not es_entrada else 0,
            "costo_unitario": 0,
            "costo_total": 0,
            "observaciones": aj.get('observaciones', ''),
            "id": aj['id']
        })
    
    # Ordenar por fecha ascendente para calcular saldos
    movimientos.sort(key=lambda x: x['fecha'])
    
    # Calcular saldos
    saldo = 0
    for mov in movimientos:
        saldo += mov['entrada'] - mov['salida']
        mov['saldo'] = saldo
        mov['fecha'] = mov['fecha'].isoformat()
    
    return {
        "item": {
            "id": item['id'],
            "codigo": item['codigo'],
            "nombre": item['nombre'],
            "unidad_medida": item.get('unidad_medida', 'unidad'),
            "stock_actual": item.get('stock_actual', 0)
        },
        "movimientos": movimientos
    }

# ==================== SERVICIOS DE PRODUCCIÓN ====================

class ServicioProduccionBase(BaseModel):
    nombre: str
    secuencia: int = 0
    tarifa: float = 0.0  # Tarifa por prenda

class ServicioProduccionCreate(ServicioProduccionBase):
    pass

class ServicioProduccion(ServicioProduccionBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

@api_router.get("/servicios-produccion", response_model=List[ServicioProduccion])
async def get_servicios_produccion():
    servicios = await db.servicios_produccion.find({}, {"_id": 0}).to_list(1000)
    for s in servicios:
        if isinstance(s.get('created_at'), str):
            s['created_at'] = datetime.fromisoformat(s['created_at'])
    return sorted(servicios, key=lambda x: x.get('secuencia', 0))

@api_router.post("/servicios-produccion", response_model=ServicioProduccion)
async def create_servicio_produccion(input: ServicioProduccionCreate):
    servicio = ServicioProduccion(**input.model_dump())
    doc = servicio.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.servicios_produccion.insert_one(doc)
    return servicio

@api_router.put("/servicios-produccion/{servicio_id}", response_model=ServicioProduccion)
async def update_servicio_produccion(servicio_id: str, input: ServicioProduccionCreate):
    result = await db.servicios_produccion.find_one({"id": servicio_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    await db.servicios_produccion.update_one({"id": servicio_id}, {"$set": input.model_dump()})
    result.update(input.model_dump())
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return ServicioProduccion(**result)

@api_router.delete("/servicios-produccion/{servicio_id}")
async def delete_servicio_produccion(servicio_id: str):
    # Verificar si tiene movimientos asociados
    movimientos_count = await db.movimientos_produccion.count_documents({"servicio_id": servicio_id})
    if movimientos_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: tiene {movimientos_count} movimiento(s) de producción asociado(s)"
        )
    
    # Verificar si tiene personas asignadas
    personas_count = await db.personas_produccion.count_documents({"servicio_ids": servicio_id})
    if personas_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: tiene {personas_count} persona(s) asignada(s)"
        )
    
    result = await db.servicios_produccion.delete_one({"id": servicio_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return {"message": "Servicio eliminado"}

# ==================== PERSONAS DE PRODUCCIÓN ====================

class ServicioPersona(BaseModel):
    servicio_id: str
    tarifa: float = 0.0  # Tarifa específica de esta persona para este servicio

class PersonaProduccionBase(BaseModel):
    nombre: str
    servicios: List[ServicioPersona] = []  # Lista de servicios con tarifa por cada uno
    telefono: str = ""
    activo: bool = True
    orden: int = 0  # Para ordenar manualmente

class PersonaProduccionCreate(PersonaProduccionBase):
    pass

class PersonaProduccion(PersonaProduccionBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PersonaConServicios(PersonaProduccion):
    servicios_detalle: List[dict] = []  # Con nombre del servicio incluido

@api_router.get("/personas-produccion")
async def get_personas_produccion(servicio_id: str = None, activo: bool = None):
    query = {}
    if servicio_id:
        query['servicios.servicio_id'] = servicio_id
    if activo is not None:
        query['activo'] = activo
    
    personas = await db.personas_produccion.find(query, {"_id": 0}).to_list(1000)
    result = []
    for p in personas:
        if isinstance(p.get('created_at'), str):
            p['created_at'] = datetime.fromisoformat(p['created_at'])
        
        # Obtener detalles de servicios (nombre + tarifa)
        servicios_detalle = []
        servicios_nombres = []
        # Soportar tanto el nuevo formato (servicios) como el antiguo (servicio_ids)
        servicios_list = p.get('servicios', [])
        if not servicios_list and p.get('servicio_ids'):
            # Migrar formato antiguo
            servicios_list = [{"servicio_id": sid, "tarifa": 0} for sid in p.get('servicio_ids', [])]
        
        for s in servicios_list:
            sid = s.get('servicio_id') if isinstance(s, dict) else s
            tarifa = s.get('tarifa', 0) if isinstance(s, dict) else 0
            servicio = await db.servicios_produccion.find_one({"id": sid}, {"_id": 0, "nombre": 1})
            if servicio:
                servicios_detalle.append({
                    "servicio_id": sid,
                    "servicio_nombre": servicio['nombre'],
                    "tarifa": tarifa
                })
                servicios_nombres.append(servicio['nombre'])
        
        p['servicios_detalle'] = servicios_detalle
        p['servicios_nombres'] = servicios_nombres  # Para compatibilidad
        
        result.append(p)
    return sorted(result, key=lambda x: (x.get('orden', 0), x.get('nombre', '')))

@api_router.post("/personas-produccion", response_model=PersonaProduccion)
async def create_persona_produccion(input: PersonaProduccionCreate):
    persona = PersonaProduccion(**input.model_dump())
    doc = persona.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.personas_produccion.insert_one(doc)
    return persona

@api_router.put("/personas-produccion/{persona_id}", response_model=PersonaProduccion)
async def update_persona_produccion(persona_id: str, input: PersonaProduccionCreate):
    result = await db.personas_produccion.find_one({"id": persona_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    await db.personas_produccion.update_one({"id": persona_id}, {"$set": input.model_dump()})
    result.update(input.model_dump())
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return PersonaProduccion(**result)

@api_router.delete("/personas-produccion/{persona_id}")
async def delete_persona_produccion(persona_id: str):
    # Verificar si tiene movimientos asociados
    movimientos_count = await db.movimientos_produccion.count_documents({"persona_id": persona_id})
    if movimientos_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"No se puede eliminar: tiene {movimientos_count} movimiento(s) de producción asociado(s)"
        )
    
    result = await db.personas_produccion.delete_one({"id": persona_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    return {"message": "Persona eliminada"}

# ==================== MOVIMIENTOS DE PRODUCCIÓN ====================

class MovimientoProduccionBase(BaseModel):
    registro_id: str
    servicio_id: str
    persona_id: str
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    cantidad: int = 0
    tarifa_aplicada: float = 0.0  # Tarifa editable (puede diferir de la del servicio)
    observaciones: str = ""

class MovimientoProduccionCreate(MovimientoProduccionBase):
    pass

class MovimientoProduccion(MovimientoProduccionBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MovimientoConDetalles(MovimientoProduccion):
    servicio_nombre: str = ""
    persona_nombre: str = ""
    registro_n_corte: str = ""
    costo: float = 0.0  # Calculado: cantidad * tarifa_aplicada

@api_router.get("/movimientos-produccion")
async def get_movimientos_produccion(registro_id: str = None):
    query = {}
    if registro_id:
        query['registro_id'] = registro_id
    
    movimientos = await db.movimientos_produccion.find(query, {"_id": 0}).to_list(5000)
    result = []
    for m in movimientos:
        if isinstance(m.get('created_at'), str):
            m['created_at'] = datetime.fromisoformat(m['created_at'])
        
        # Obtener nombres
        servicio = await db.servicios_produccion.find_one({"id": m.get('servicio_id')}, {"_id": 0, "nombre": 1, "tarifa": 1})
        persona = await db.personas_produccion.find_one({"id": m.get('persona_id')}, {"_id": 0, "nombre": 1})
        registro = await db.registros.find_one({"id": m.get('registro_id')}, {"_id": 0, "n_corte": 1})
        
        m['servicio_nombre'] = servicio['nombre'] if servicio else ""
        m['persona_nombre'] = persona['nombre'] if persona else ""
        m['registro_n_corte'] = registro['n_corte'] if registro else ""
        m['tarifa_servicio'] = servicio.get('tarifa', 0) if servicio else 0  # Tarifa referencial del servicio
        # El costo se calcula con la tarifa_aplicada del movimiento (la que el usuario ingresó)
        tarifa_mov = m.get('tarifa_aplicada', 0)
        m['costo'] = tarifa_mov * m.get('cantidad', 0)
        
        result.append(m)
    return sorted(result, key=lambda x: x.get('created_at'), reverse=True)

@api_router.post("/movimientos-produccion", response_model=MovimientoProduccion)
async def create_movimiento_produccion(input: MovimientoProduccionCreate):
    # Verificar que el registro existe
    registro = await db.registros.find_one({"id": input.registro_id})
    if not registro:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    
    # Verificar que el servicio existe
    servicio = await db.servicios_produccion.find_one({"id": input.servicio_id})
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    # Verificar que la persona existe y tiene el servicio asignado
    persona = await db.personas_produccion.find_one({"id": input.persona_id}, {"_id": 0})
    if not persona:
        raise HTTPException(status_code=404, detail="Persona no encontrada")
    if input.servicio_id not in persona.get('servicio_ids', []):
        raise HTTPException(status_code=400, detail="La persona no tiene asignado este servicio")
    
    movimiento = MovimientoProduccion(**input.model_dump())
    doc = movimiento.model_dump()
    doc['created_at'] = doc['created_at'].isoformat()
    await db.movimientos_produccion.insert_one(doc)
    return movimiento

@api_router.put("/movimientos-produccion/{movimiento_id}", response_model=MovimientoProduccion)
async def update_movimiento_produccion(movimiento_id: str, input: MovimientoProduccionCreate):
    result = await db.movimientos_produccion.find_one({"id": movimiento_id}, {"_id": 0})
    if not result:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    
    update_data = input.model_dump()
    await db.movimientos_produccion.update_one({"id": movimiento_id}, {"$set": update_data})
    result.update(update_data)
    if isinstance(result.get('created_at'), str):
        result['created_at'] = datetime.fromisoformat(result['created_at'])
    return MovimientoProduccion(**result)

@api_router.delete("/movimientos-produccion/{movimiento_id}")
async def delete_movimiento_produccion(movimiento_id: str):
    result = await db.movimientos_produccion.delete_one({"id": movimiento_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Movimiento no encontrado")
    return {"message": "Movimiento eliminado"}

# ==================== REPORTE DE PRODUCTIVIDAD ====================

@api_router.get("/reporte-productividad")
async def get_reporte_productividad(
    fecha_desde: str = None,
    fecha_hasta: str = None,
    servicio_id: str = None,
    persona_id: str = None
):
    query = {}
    if servicio_id:
        query['servicio_id'] = servicio_id
    if persona_id:
        query['persona_id'] = persona_id
    
    movimientos = await db.movimientos_produccion.find(query, {"_id": 0}).to_list(10000)
    
    # Filtrar por fecha
    if fecha_desde or fecha_hasta:
        movimientos_filtrados = []
        for m in movimientos:
            fecha = m.get('fecha_inicio') or m.get('fecha_fin')
            if not fecha:
                continue
            if fecha_desde and fecha < fecha_desde:
                continue
            if fecha_hasta and fecha > fecha_hasta:
                continue
            movimientos_filtrados.append(m)
        movimientos = movimientos_filtrados
    
    # Calcular totales por persona
    totales_persona = {}
    # Calcular totales por servicio
    totales_servicio = {}
    # Calcular totales por persona-servicio
    detalle_persona_servicio = {}
    
    for m in movimientos:
        persona_id_m = m.get('persona_id')
        servicio_id_m = m.get('servicio_id')
        cantidad = m.get('cantidad', 0)
        
        # Usar tarifa_aplicada del movimiento (la que el usuario ingresó)
        tarifa = m.get('tarifa_aplicada', 0)
        costo = cantidad * tarifa
        
        # Obtener datos del servicio para mostrar nombre
        servicio = await db.servicios_produccion.find_one({"id": servicio_id_m}, {"_id": 0, "tarifa": 1, "nombre": 1})
        
        # Por persona
        if persona_id_m not in totales_persona:
            persona = await db.personas_produccion.find_one({"id": persona_id_m}, {"_id": 0, "nombre": 1})
            totales_persona[persona_id_m] = {
                "persona_id": persona_id_m,
                "persona_nombre": persona['nombre'] if persona else "Desconocido",
                "total_cantidad": 0,
                "total_costo": 0,
                "movimientos": 0
            }
        totales_persona[persona_id_m]['total_cantidad'] += cantidad
        totales_persona[persona_id_m]['total_costo'] += costo
        totales_persona[persona_id_m]['movimientos'] += 1
        
        # Por servicio
        if servicio_id_m not in totales_servicio:
            totales_servicio[servicio_id_m] = {
                "servicio_id": servicio_id_m,
                "servicio_nombre": servicio['nombre'] if servicio else "Desconocido",
                "tarifa": servicio.get('tarifa', 0) if servicio else 0,  # Tarifa referencial
                "total_cantidad": 0,
                "total_costo": 0,
                "movimientos": 0
            }
        totales_servicio[servicio_id_m]['total_cantidad'] += cantidad
        totales_servicio[servicio_id_m]['total_costo'] += costo
        totales_servicio[servicio_id_m]['movimientos'] += 1
        
        # Detalle persona-servicio
        key = f"{persona_id_m}_{servicio_id_m}"
        if key not in detalle_persona_servicio:
            persona = await db.personas_produccion.find_one({"id": persona_id_m}, {"_id": 0, "nombre": 1})
            detalle_persona_servicio[key] = {
                "persona_id": persona_id_m,
                "persona_nombre": persona['nombre'] if persona else "Desconocido",
                "servicio_id": servicio_id_m,
                "servicio_nombre": servicio['nombre'] if servicio else "Desconocido",
                "tarifa": tarifa,
                "total_cantidad": 0,
                "total_costo": 0,
                "movimientos": 0
            }
        detalle_persona_servicio[key]['total_cantidad'] += cantidad
        detalle_persona_servicio[key]['total_costo'] += costo
        detalle_persona_servicio[key]['movimientos'] += 1
    
    # Calcular totales generales
    total_general_cantidad = sum(p['total_cantidad'] for p in totales_persona.values())
    total_general_costo = sum(p['total_costo'] for p in totales_persona.values())
    total_general_movimientos = sum(p['movimientos'] for p in totales_persona.values())
    
    return {
        "por_persona": sorted(list(totales_persona.values()), key=lambda x: x['total_cantidad'], reverse=True),
        "por_servicio": sorted(list(totales_servicio.values()), key=lambda x: x['total_cantidad'], reverse=True),
        "detalle": sorted(list(detalle_persona_servicio.values()), key=lambda x: (x['persona_nombre'], x['servicio_nombre'])),
        "totales": {
            "cantidad": total_general_cantidad,
            "costo": total_general_costo,
            "movimientos": total_general_movimientos
        }
    }

# Root endpoint
@api_router.get("/")
async def root():
    return {"message": "API Módulo Producción Textil"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
