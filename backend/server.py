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

# Tipo
class TipoBase(BaseModel):
    nombre: str

class TipoCreate(TipoBase):
    pass

class Tipo(TipoBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Entalle
class EntalleBase(BaseModel):
    nombre: str

class EntalleCreate(EntalleBase):
    pass

class Entalle(EntalleBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Tela
class TelaBase(BaseModel):
    nombre: str

class TelaCreate(TelaBase):
    pass

class Tela(TelaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Hilo
class HiloBase(BaseModel):
    nombre: str

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
async def get_tipos():
    tipos = await db.tipos.find({}, {"_id": 0}).to_list(1000)
    for t in tipos:
        if isinstance(t.get('created_at'), str):
            t['created_at'] = datetime.fromisoformat(t['created_at'])
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
    await db.tipos.update_one({"id": tipo_id}, {"$set": {"nombre": input.nombre}})
    result['nombre'] = input.nombre
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
async def get_entalles():
    entalles = await db.entalles.find({}, {"_id": 0}).to_list(1000)
    for e in entalles:
        if isinstance(e.get('created_at'), str):
            e['created_at'] = datetime.fromisoformat(e['created_at'])
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
    await db.entalles.update_one({"id": entalle_id}, {"$set": {"nombre": input.nombre}})
    result['nombre'] = input.nombre
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
async def get_telas():
    telas = await db.telas.find({}, {"_id": 0}).to_list(1000)
    for t in telas:
        if isinstance(t.get('created_at'), str):
            t['created_at'] = datetime.fromisoformat(t['created_at'])
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
    await db.telas.update_one({"id": tela_id}, {"$set": {"nombre": input.nombre}})
    result['nombre'] = input.nombre
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
async def get_hilos():
    hilos = await db.hilos.find({}, {"_id": 0}).to_list(1000)
    for h in hilos:
        if isinstance(h.get('created_at'), str):
            h['created_at'] = datetime.fromisoformat(h['created_at'])
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
    await db.hilos.update_one({"id": hilo_id}, {"$set": {"nombre": input.nombre}})
    result['nombre'] = input.nombre
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
        "estados_count": estados_count
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
