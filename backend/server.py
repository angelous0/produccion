from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, JSONResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import asyncpg
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
import uuid
from uuid import uuid4

from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
import json
import io
from passlib.context import CryptContext
from jose import JWTError, jwt
from models import ReorderRequest

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# PostgreSQL connection - Use shared pool from db.py
from db import get_pool, close_pool, safe_acquire

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'tu-clave-secreta-muy-segura-cambiar-en-produccion-2024')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 8760  # 1 año - uso interno, sin expiración práctica

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer(auto_error=False)

# Pool is now managed by db.py - removed local pool variable


# ==================== DDL HELPERS (TABLAS NUEVAS) ====================

async def ensure_bom_tables():
    """Crea tablas nuevas necesarias para BOM (sin modificar tablas existentes).

    Nota: no se crean FKs porque el resto del proyecto no las usa.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Tabla relación Modelo ↔ Tallas
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prod_modelo_tallas (
                id VARCHAR PRIMARY KEY,
                modelo_id VARCHAR NOT NULL,
                talla_id VARCHAR NOT NULL,
                activo BOOLEAN DEFAULT TRUE,
                orden INT DEFAULT 10,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_modelo_tallas_modelo ON prod_modelo_tallas(modelo_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_modelo_tallas_talla ON prod_modelo_tallas(talla_id)"
        )
        await conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_modelo_talla_activo
            ON prod_modelo_tallas(modelo_id, talla_id)
            WHERE activo = TRUE
            """
        )

        # Tabla BOM por modelo (talla_id NULL = general, talla_id definido = por talla)
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS prod_modelo_bom_linea (
                id VARCHAR PRIMARY KEY,
                modelo_id VARCHAR NOT NULL,
                inventario_id VARCHAR NOT NULL,
                talla_id VARCHAR NULL,
                unidad_base VARCHAR DEFAULT 'PRENDA',
                cantidad_base NUMERIC(14,4) NOT NULL,
                orden INT DEFAULT 10,
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bom_modelo_id ON prod_modelo_bom_linea(modelo_id)"
        )
        # Si la tabla ya existía de antes, aseguramos columnas nuevas sin romper datos
        await conn.execute("ALTER TABLE prod_modelo_bom_linea ADD COLUMN IF NOT EXISTS orden INT DEFAULT 10")
        await conn.execute("ALTER TABLE prod_modelo_bom_linea ADD COLUMN IF NOT EXISTS bom_id VARCHAR NULL")
        await conn.execute("ALTER TABLE prod_modelo_bom_linea ADD COLUMN IF NOT EXISTS tipo_componente VARCHAR DEFAULT 'TELA'")
        await conn.execute("ALTER TABLE prod_modelo_bom_linea ADD COLUMN IF NOT EXISTS merma_pct NUMERIC(5,2) DEFAULT 0")
        await conn.execute("ALTER TABLE prod_modelo_bom_linea ADD COLUMN IF NOT EXISTS cantidad_total NUMERIC(14,4) NULL")
        await conn.execute("ALTER TABLE prod_modelo_bom_linea ADD COLUMN IF NOT EXISTS es_opcional BOOLEAN DEFAULT FALSE")
        await conn.execute("ALTER TABLE prod_modelo_bom_linea ADD COLUMN IF NOT EXISTS etapa_id VARCHAR NULL")
        await conn.execute("ALTER TABLE prod_modelo_bom_linea ADD COLUMN IF NOT EXISTS observaciones TEXT NULL")

        # Tabla cabecera BOM
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_bom_cabecera (
                id VARCHAR PRIMARY KEY,
                modelo_id VARCHAR NOT NULL,
                codigo VARCHAR,
                version INT NOT NULL DEFAULT 1,
                estado VARCHAR NOT NULL DEFAULT 'BORRADOR',
                vigente_desde TIMESTAMP NULL,
                vigente_hasta TIMESTAMP NULL,
                observaciones TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_bom_cab_modelo ON prod_bom_cabecera(modelo_id)")
        await conn.execute("ALTER TABLE prod_bom_cabecera ADD COLUMN IF NOT EXISTS nombre VARCHAR NULL")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_bom_linea_bom_id ON prod_modelo_bom_linea(bom_id)")

        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bom_inventario_id ON prod_modelo_bom_linea(inventario_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bom_talla_id ON prod_modelo_bom_linea(talla_id)"
        )
        # Old constraint was too restrictive - needs to include bom_id for multiple versions
        await conn.execute("DROP INDEX IF EXISTS uq_bom_linea_activo")
        await conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_bom_linea_activo_v2
            ON prod_modelo_bom_linea(bom_id, inventario_id, COALESCE(talla_id, '__NULL__'))
            WHERE activo = TRUE
            """
        )


    # Asegurar columnas nuevas en prod_registros
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE prod_registros ADD COLUMN IF NOT EXISTS id_odoo VARCHAR(50)")
        await conn.execute("ALTER TABLE prod_registros ADD COLUMN IF NOT EXISTS observaciones TEXT")
        await conn.execute("ALTER TABLE prod_registros ADD COLUMN IF NOT EXISTS skip_validacion_estado BOOLEAN DEFAULT FALSE")

        # Tabla de motivos de incidencia (catálogo administrable)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_motivos_incidencia (
                id VARCHAR PRIMARY KEY,
                nombre VARCHAR NOT NULL UNIQUE,
                activo BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        # Seed defaults si tabla vacía
        count = await conn.fetchval("SELECT COUNT(*) FROM prod_motivos_incidencia")
        if count == 0:
            defaults = ['Falta Material', 'Falta Avíos', 'Retraso Taller', 'Calidad', 'Cambio Prioridad', 'Sin Capacidad', 'Reprogramación', 'Otro']
            for nombre in defaults:
                await conn.execute(
                    "INSERT INTO prod_motivos_incidencia (id, nombre) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    str(uuid.uuid4()), nombre
                )

        # Agregar columna paraliza a incidencias existentes
        await conn.execute("ALTER TABLE prod_incidencia ADD COLUMN IF NOT EXISTS paraliza BOOLEAN DEFAULT FALSE")
        await conn.execute("ALTER TABLE prod_incidencia ADD COLUMN IF NOT EXISTS paralizacion_id VARCHAR")
        await conn.execute("ALTER TABLE prod_incidencia ADD COLUMN IF NOT EXISTS comentario_resolucion TEXT")
        # Expandir columna tipo de varchar(30) a VARCHAR sin limite
        await conn.execute("ALTER TABLE prod_incidencia ALTER COLUMN tipo TYPE VARCHAR")
        await conn.execute("ALTER TABLE prod_incidencia ALTER COLUMN usuario TYPE VARCHAR")

        # Tabla de conversacion/hilo por registro
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_conversacion (
                id VARCHAR PRIMARY KEY,
                registro_id VARCHAR NOT NULL,
                mensaje_padre_id VARCHAR,
                autor VARCHAR NOT NULL,
                mensaje TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("ALTER TABLE prod_conversacion ADD COLUMN IF NOT EXISTS estado VARCHAR DEFAULT 'normal'")
        await conn.execute("ALTER TABLE prod_conversacion ADD COLUMN IF NOT EXISTS fijado BOOLEAN DEFAULT FALSE")

        # Avance porcentaje en servicios y movimientos
        await conn.execute("ALTER TABLE prod_servicios_produccion ADD COLUMN IF NOT EXISTS usa_avance_porcentaje BOOLEAN DEFAULT FALSE")
        await conn.execute("ALTER TABLE prod_movimientos_produccion ADD COLUMN IF NOT EXISTS avance_porcentaje INTEGER")
        await conn.execute("ALTER TABLE prod_movimientos_produccion ADD COLUMN IF NOT EXISTS avance_updated_at TIMESTAMP")
        # Historial de avances
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS produccion.prod_avance_historial (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                movimiento_id VARCHAR NOT NULL,
                avance_porcentaje INTEGER NOT NULL,
                usuario VARCHAR,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)


# ==================== FASE 2: Tablas de Reservas y Requerimiento ====================
    return pool
async def ensure_fase2_tables():
    """Crea las tablas necesarias para Fase 2: Reservas + Requerimiento MP"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # 1) prod_registro_tallas: Cantidades reales por talla (normalizado)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_registro_tallas (
                id VARCHAR PRIMARY KEY,
                registro_id VARCHAR NOT NULL,
                talla_id VARCHAR NOT NULL,
                cantidad_real INT NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_registro_tallas_registro ON prod_registro_tallas(registro_id)"
        )
        await conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_registro_talla ON prod_registro_tallas(registro_id, talla_id)"
        )

        # 2) prod_registro_requerimiento_mp: Resultado de explosión BOM
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_registro_requerimiento_mp (
                id VARCHAR PRIMARY KEY,
                registro_id VARCHAR NOT NULL,
                item_id VARCHAR NOT NULL,
                talla_id VARCHAR NULL,
                cantidad_requerida NUMERIC(14,4) NOT NULL DEFAULT 0,
                cantidad_reservada NUMERIC(14,4) NOT NULL DEFAULT 0,
                cantidad_consumida NUMERIC(14,4) NOT NULL DEFAULT 0,
                estado VARCHAR NOT NULL DEFAULT 'PENDIENTE',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_req_mp_registro ON prod_registro_requerimiento_mp(registro_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_req_mp_item ON prod_registro_requerimiento_mp(item_id)"
        )
        # Unique index con COALESCE para manejar talla_id NULL
        await conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_req_mp_registro_item_talla
            ON prod_registro_requerimiento_mp(registro_id, item_id, COALESCE(talla_id, '__NULL__'))
        """)

        # 3) prod_inventario_reservas: Cabecera de reservas
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_inventario_reservas (
                id VARCHAR PRIMARY KEY,
                registro_id VARCHAR NOT NULL,
                estado VARCHAR NOT NULL DEFAULT 'ACTIVA',
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reservas_registro ON prod_inventario_reservas(registro_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reservas_estado ON prod_inventario_reservas(estado)"
        )

        # 4) prod_inventario_reservas_linea: Líneas de reservas
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_inventario_reservas_linea (
                id VARCHAR PRIMARY KEY,
                reserva_id VARCHAR NOT NULL,
                item_id VARCHAR NOT NULL,
                talla_id VARCHAR NULL,
                cantidad_reservada NUMERIC(14,4) NOT NULL DEFAULT 0,
                cantidad_liberada NUMERIC(14,4) NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reservas_linea_reserva ON prod_inventario_reservas_linea(reserva_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_reservas_linea_item ON prod_inventario_reservas_linea(item_id)"
        )

        # 5) Agregar talla_id a prod_inventario_salidas si no existe
        await conn.execute(
            "ALTER TABLE prod_inventario_salidas ADD COLUMN IF NOT EXISTS talla_id VARCHAR NULL"
        )

        # 6) Agregar ignorar_alerta_stock a prod_inventario si no existe
        await conn.execute(
            "ALTER TABLE prod_inventario ADD COLUMN IF NOT EXISTS ignorar_alerta_stock BOOLEAN DEFAULT FALSE"
        )

        # 7) Línea de negocio en modelos, registros, ingresos y salidas
        await conn.execute("ALTER TABLE prod_modelos ADD COLUMN IF NOT EXISTS linea_negocio_id INTEGER NULL")
        await conn.execute("ALTER TABLE prod_registros ADD COLUMN IF NOT EXISTS linea_negocio_id INTEGER NULL")
        await conn.execute("ALTER TABLE prod_inventario_ingresos ADD COLUMN IF NOT EXISTS linea_negocio_id INTEGER NULL")
        await conn.execute("ALTER TABLE prod_inventario_salidas ADD COLUMN IF NOT EXISTS linea_negocio_id INTEGER NULL")

        # 8) Jerarquía Base → Modelo (variante) → Registro
        await conn.execute("ALTER TABLE prod_modelos ADD COLUMN IF NOT EXISTS base_id VARCHAR NULL")
        await conn.execute("ALTER TABLE prod_modelos ADD COLUMN IF NOT EXISTS hilo_especifico_id VARCHAR NULL")
        await conn.execute("ALTER TABLE prod_modelos ADD COLUMN IF NOT EXISTS muestra_modelo_id VARCHAR NULL")
        await conn.execute("ALTER TABLE prod_modelos ADD COLUMN IF NOT EXISTS muestra_base_id VARCHAR NULL")



app = FastAPI()

# Handler global para desconexiones de BD remota
@app.exception_handler(asyncpg.exceptions.ConnectionDoesNotExistError)
async def db_connection_error_handler(request, exc):
    import logging
    logging.warning(f"BD remota desconectada en {request.url.path}: {exc}")
    import db as _db
    try:
        if _db.pool and not _db.pool._closed:
            await _db.pool.close()
    except Exception:
        pass
    _db.pool = None
    return JSONResponse(status_code=503, content={"detail": "Conexión con la base de datos perdida. Intente de nuevo."})

@app.exception_handler(asyncpg.exceptions.InterfaceError)
async def db_interface_error_handler(request, exc):
    import logging
    logging.warning(f"Error interfaz BD en {request.url.path}: {exc}")
    import db as _db
    try:
        if _db.pool and not _db.pool._closed:
            await _db.pool.close()
    except Exception:
        pass
    _db.pool = None
    return JSONResponse(status_code=503, content={"detail": "Error de conexión con la base de datos. Intente de nuevo."})

api_router = APIRouter(prefix="/api")

# ==================== AUTENTICACIÓN ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="No autenticado")
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Token inválido")
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM prod_usuarios WHERE id = $1 AND activo = true", user_id)
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
        return dict(user)

async def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtiene el usuario actual si hay token, sino retorna None"""
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except:
        return None

def check_permission(user: dict, tabla: str, accion: str) -> bool:
    """Verifica si el usuario tiene permiso para una acción en una tabla"""
    if not user:
        return False
    
    rol = user.get('rol', 'lectura')
    
    # Admin tiene todos los permisos
    if rol == 'admin':
        return True
    
    # Lectura solo puede ver
    if rol == 'lectura':
        return accion == 'ver'
    
    # Usuario: verificar permisos personalizados
    permisos = user.get('permisos', {})
    if isinstance(permisos, str):
        permisos = json.loads(permisos) if permisos else {}
    
    tabla_permisos = permisos.get(tabla, {})
    return tabla_permisos.get(accion, False)

def require_permission(tabla: str, accion: str):
    """Decorador para requerir permisos en endpoints"""
    async def permission_checker(current_user: dict = Depends(get_current_user)):
        if not check_permission(current_user, tabla, accion):
            raise HTTPException(status_code=403, detail=f"No tienes permiso para {accion} en {tabla}")
        return current_user
    return permission_checker

# ==================== MODELOS PYDANTIC ====================

# Modelos de Usuario
class UserLogin(BaseModel):
    username: str
    password: str

class UserCreate(BaseModel):
    username: str
    email: Optional[str] = None
    password: str
    nombre_completo: Optional[str] = None
    rol: str = "usuario"
    permisos: dict = {}

class UserUpdate(BaseModel):
    email: Optional[str] = None
    nombre_completo: Optional[str] = None
    rol: Optional[str] = None
    permisos: Optional[dict] = None
    activo: Optional[bool] = None

class UserChangePassword(BaseModel):
    current_password: str
    new_password: str

class MarcaBase(BaseModel):
    nombre: str
    orden: int = 0

class MarcaCreate(MarcaBase):
    pass

class Marca(MarcaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TipoBase(BaseModel):
    nombre: str
    marca_ids: List[str] = []
    orden: int = 0

class TipoCreate(TipoBase):
    pass

class Tipo(TipoBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EntalleBase(BaseModel):
    nombre: str
    tipo_ids: List[str] = []
    orden: int = 0

class EntalleCreate(EntalleBase):
    pass

class Entalle(EntalleBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TelaBase(BaseModel):
    nombre: str
    entalle_ids: List[str] = []
    orden: int = 0

class TelaCreate(TelaBase):
    pass

class Tela(TelaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class HiloBase(BaseModel):
    nombre: str
    tela_ids: List[str] = []
    orden: int = 0

class HiloCreate(HiloBase):
    pass

class Hilo(HiloBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TallaBase(BaseModel):
    nombre: str
    orden: int = 0

class TallaCreate(TallaBase):
    pass

class Talla(TallaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ColorGeneralBase(BaseModel):
    nombre: str
    orden: int = 0

class ColorGeneralCreate(ColorGeneralBase):
    pass

class ColorGeneral(ColorGeneralBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ColorBase(BaseModel):
    nombre: str
    codigo_hex: str = ""
    color_general_id: Optional[str] = None
    orden: int = 0

class ColorCreate(ColorBase):
    pass

class Color(ColorBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# Hilos Específicos (catálogo independiente vinculado a registros)
class HiloEspecificoBase(BaseModel):
    nombre: str
    codigo: str = ""
    color: str = ""
    descripcion: str = ""
    orden: int = 0

class HiloEspecificoCreate(HiloEspecificoBase):
    pass

class HiloEspecifico(HiloEspecificoBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class EtapaRuta(BaseModel):
    nombre: str
    servicio_id: Optional[str] = None
    orden: float = 0
    obligatorio: bool = True
    aparece_en_estado: bool = True
    es_cierre: bool = False

class RutaProduccionBase(BaseModel):
    nombre: str
    descripcion: str = ""
    etapas: List[EtapaRuta] = []

class RutaProduccionCreate(RutaProduccionBase):
    pass

class RutaProduccion(RutaProduccionBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ModeloBase(BaseModel):
    nombre: str
    marca_id: str
    tipo_id: str
    entalle_id: str
    tela_id: str
    hilo_id: str
    ruta_produccion_id: Optional[str] = None
    servicios_ids: List[str] = []
    pt_item_id: Optional[str] = None
    linea_negocio_id: Optional[int] = None
    base_id: Optional[str] = None
    hilo_especifico_id: Optional[str] = None
    muestra_modelo_id: Optional[str] = None
    muestra_base_id: Optional[str] = None

class ModeloCreate(ModeloBase):
    pass

class Modelo(ModeloBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TallaCantidadItem(BaseModel):
    model_config = ConfigDict(extra="allow")
    talla_id: str
    nombre: Optional[str] = ""
    talla_nombre: Optional[str] = ""
    cantidad: int = 0


# ==================== BOM / RECETA ====================

class ModeloTallaBase(BaseModel):
    talla_id: str
    orden: int = 10
    activo: bool = True

class ModeloTallaCreate(ModeloTallaBase):
    pass

class ModeloTallaUpdate(BaseModel):
    orden: Optional[int] = None
    activo: Optional[bool] = None

class ModeloTallaOut(BaseModel):
    id: str
    modelo_id: str
    talla_id: str
    talla_nombre: Optional[str] = None
    orden: int = 10
    activo: bool = True
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class ModeloBomLineaBase(BaseModel):
    inventario_id: str
    talla_id: Optional[str] = None  # NULL = general
    cantidad_base: float
    activo: bool = True

class ModeloBomLineaCreate(ModeloBomLineaBase):
    pass

class ModeloBomLineaUpdate(BaseModel):
    inventario_id: Optional[str] = None
    talla_id: Optional[str] = None
    cantidad_base: Optional[float] = None
    activo: Optional[bool] = None

class ModeloBomLineaOut(BaseModel):
    id: str
    modelo_id: str
    inventario_id: str
    inventario_nombre: Optional[str] = None
    inventario_codigo: Optional[str] = None
    talla_id: Optional[str] = None
    talla_nombre: Optional[str] = None
    unidad_base: Optional[str] = None
    cantidad_base: float
    orden: Optional[int] = None
    activo: bool
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    talla_nombre: str = ""
    cantidad: int = 0

class ColorDistribucion(BaseModel):
    color_id: str
    color_nombre: str = ""
    cantidad: int = 0

class TallaConColores(BaseModel):
    talla_id: str
    talla_nombre: str = ""
    cantidad_total: int = 0
    colores: List[ColorDistribucion] = []

class RegistroBase(BaseModel):
    n_corte: str
    modelo_id: str
    curva: str = ""
    estado: str = "Para Corte"
    urgente: bool = False
    hilo_especifico_id: Optional[str] = None
    pt_item_id: Optional[str] = None
    lq_odoo_id: Optional[str] = None
    empresa_id: Optional[int] = 8
    id_odoo: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_entrega_final: Optional[str] = None
    linea_negocio_id: Optional[int] = None

class RegistroCreate(RegistroBase):
    tallas: List[TallaCantidadItem] = []
    distribucion_colores: List[TallaConColores] = []

class Registro(RegistroBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha_creacion: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tallas: List[TallaCantidadItem] = []
    distribucion_colores: List[TallaConColores] = []

ESTADOS_PRODUCCION = [
    "Para Corte", "Corte", "Para Costura", "Costura", "Para Atraque", "Atraque",
    "Para Lavandería", "Muestra Lavanderia", "Lavandería", "Para Acabado",
    "Acabado", "Almacén PT", "Tienda"
]

class ServicioBase(BaseModel):
    nombre: str
    descripcion: str = ""
    tarifa: float = 0
    orden: Optional[int] = None
    usa_avance_porcentaje: bool = False

class ServicioCreate(ServicioBase):
    pass

class Servicio(ServicioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PersonaServicio(BaseModel):
    servicio_id: str
    tarifa: float = 0

class PersonaBase(BaseModel):
    nombre: str
    tipo: str = "externo"
    telefono: str = ""
    email: str = ""
    direccion: str = ""
    servicios: List[PersonaServicio] = []
    activo: bool = True
    tipo_persona: str = "EXTERNO"
    unidad_interna_id: Optional[int] = None

class PersonaCreate(PersonaBase):
    pass

class Persona(PersonaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MovimientoBase(BaseModel):
    registro_id: str
    servicio_id: str
    persona_id: str
    cantidad_enviada: int = 0
    cantidad_recibida: int = 0
    tarifa_aplicada: float = 0
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    fecha_esperada_movimiento: Optional[str] = None
    responsable_movimiento: Optional[str] = None
    observaciones: str = ""
    avance_porcentaje: Optional[int] = None

class MovimientoCreate(MovimientoBase):
    pass

class Movimiento(MovimientoBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    diferencia: int = 0
    costo_calculado: float = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class ItemInventarioBase(BaseModel):
    codigo: str
    nombre: str
    descripcion: str = ""
    categoria: str = "Otros"
    unidad_medida: str = "unidad"
    stock_minimo: int = 0
    control_por_rollos: bool = False
    linea_negocio_id: Optional[int] = None

class ItemInventarioCreate(ItemInventarioBase):
    pass

class ItemInventario(ItemInventarioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    stock_actual: float = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class IngresoInventarioBase(BaseModel):
    item_id: str
    cantidad: float
    costo_unitario: float = 0.0
    proveedor: str = ""
    numero_documento: str = ""
    observaciones: str = ""

class IngresoInventarioCreate(IngresoInventarioBase):
    rollos: List[dict] = []
    empresa_id: int = 7
    linea_negocio_id: Optional[int] = None

class IngresoInventario(IngresoInventarioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    cantidad_disponible: float = 0

class SalidaInventarioBase(BaseModel):
    item_id: str
    cantidad: float
    registro_id: Optional[str] = None
    talla_id: Optional[str] = None
    observaciones: str = ""
    rollo_id: Optional[str] = None

class SalidaInventarioCreate(SalidaInventarioBase):
    linea_negocio_id: Optional[int] = None

class SalidaInventario(SalidaInventarioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    costo_total: float = 0.0
    detalle_fifo: List[dict] = []


# ==================== FASE 2: Modelos Pydantic ====================

class RegistroTallaBase(BaseModel):
    talla_id: str
    cantidad_real: int = 0

class RegistroTallaCreate(RegistroTallaBase):
    pass

class RegistroTallaUpdate(BaseModel):
    cantidad_real: int

class RegistroTallaBulkUpdate(BaseModel):
    tallas: List[RegistroTallaBase]

class RequerimientoMPOut(BaseModel):
    id: str
    registro_id: str
    item_id: str
    item_codigo: Optional[str] = None
    item_nombre: Optional[str] = None
    item_unidad: Optional[str] = None
    control_por_rollos: bool = False
    talla_id: Optional[str] = None
    talla_nombre: Optional[str] = None
    cantidad_requerida: float
    cantidad_reservada: float
    cantidad_consumida: float
    pendiente_reservar: float = 0
    pendiente_consumir: float = 0
    estado: str

class ReservaLineaInput(BaseModel):
    item_id: str
    talla_id: Optional[str] = None
    cantidad: float

class ReservaCreateInput(BaseModel):
    lineas: List[ReservaLineaInput]

class LiberarReservaLineaInput(BaseModel):
    item_id: str
    talla_id: Optional[str] = None
    cantidad: float

class LiberarReservaInput(BaseModel):
    lineas: List[LiberarReservaLineaInput]

class DisponibilidadItemOut(BaseModel):
    item_id: str
    item_codigo: Optional[str] = None
    item_nombre: Optional[str] = None
    stock_actual: float
    total_reservado: float
    disponible: float
    control_por_rollos: bool


class AjusteInventarioBase(BaseModel):
    item_id: str
    tipo: str
    cantidad: float
    motivo: str = ""
    observaciones: str = ""
    rollo_id: Optional[str] = None

class AjusteInventarioCreate(AjusteInventarioBase):
    pass

class AjusteInventario(AjusteInventarioBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class MermaBase(BaseModel):
    registro_id: str
    movimiento_id: str
    servicio_id: str
    persona_id: str
    cantidad: int = 0
    motivo: str = ""

class MermaCreate(MermaBase):
    pass

class Merma(MermaBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class GuiaRemisionBase(BaseModel):
    movimiento_id: str
    registro_id: str
    servicio_id: str
    persona_id: str
    cantidad: int = 0
    observaciones: str = ""

class GuiaRemisionCreate(GuiaRemisionBase):
    pass

class GuiaRemision(GuiaRemisionBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    numero_guia: str = ""
    fecha: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

# ==================== HELPERS ====================

def row_to_dict(row):
    if row is None:
        return None
    return dict(row)

def parse_jsonb(val):
    if val is None:
        return []
    if isinstance(val, str):
        return json.loads(val)
    return val

# ==================== HISTORIAL DE ACTIVIDAD ====================

async def registrar_actividad(
    pool,
    usuario_id: str,
    usuario_nombre: str,
    tipo_accion: str,
    tabla_afectada: str = None,
    registro_id: str = None,
    registro_nombre: str = None,
    descripcion: str = None,
    datos_anteriores: dict = None,
    datos_nuevos: dict = None,
    ip_address: str = None
):
    """Registra una actividad en el historial"""
    actividad_id = str(uuid.uuid4())
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO prod_actividad_historial 
               (id, usuario_id, usuario_nombre, tipo_accion, tabla_afectada, registro_id, registro_nombre, descripcion, datos_anteriores, datos_nuevos, ip_address, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, NOW())""",
            actividad_id, usuario_id, usuario_nombre, tipo_accion, tabla_afectada,
            registro_id, registro_nombre, descripcion,
            json.dumps(datos_anteriores) if datos_anteriores else None,
            json.dumps(datos_nuevos) if datos_nuevos else None,
            ip_address
        )

def limpiar_datos_sensibles(datos: dict) -> dict:
    """Elimina campos sensibles de los datos para el historial"""
    if not datos:
        return datos
    datos_limpio = dict(datos)
    campos_sensibles = ['password', 'password_hash', 'hashed_password', 'token', 'access_token']
    for campo in campos_sensibles:
        if campo in datos_limpio:
            datos_limpio[campo] = '***'
    return datos_limpio

def verificar_permiso(user: dict, tabla: str, accion: str) -> bool:
    """
    Verifica si el usuario tiene permiso para realizar una acción en una tabla
    accion: 'ver', 'crear', 'editar', 'eliminar'
    """
    if user['rol'] == 'admin':
        return True
    if user['rol'] == 'lectura':
        return accion == 'ver'
    
    permisos = user.get('permisos', {})
    if isinstance(permisos, str):
        permisos = json.loads(permisos) if permisos else {}
    
    permisos_tabla = permisos.get(tabla, {})
    return permisos_tabla.get(accion, False)

def require_permiso(tabla: str, accion: str):
    """Decorator/helper para requerir permiso en un endpoint"""
    async def check_permission(current_user: dict = Depends(get_current_user)):
        if not verificar_permiso(current_user, tabla, accion):
            raise HTTPException(
                status_code=403, 
                detail=f"No tienes permiso para {accion} en {tabla}"
            )
        return current_user
    return check_permission

# ==================== ENDPOINTS AUTENTICACIÓN ====================




# --- Conexión externa a módulo de Muestras ---
import asyncpg as asyncpg_ext

_muestra_pool = None
async def get_muestra_pool():
    global _muestra_pool
    if _muestra_pool is None:
        _muestra_pool = await asyncpg_ext.create_pool(
            host="72.60.241.216", port=9090, database="datos",
            user="admin", password="admin", min_size=1, max_size=3
        )
    return _muestra_pool


@api_router.get("/muestras-modelos")
async def get_muestras_modelos(search: str = ""):
    try:
        pool = await get_muestra_pool()
        async with pool.acquire() as conn:
            if search:
                rows = await conn.fetch("""
                    SELECT m.id, m.nombre, m.aprobado, m.activo,
                        b.nombre as base_nombre, h.nombre as hilo_nombre
                    FROM muestra.modelos m
                    LEFT JOIN muestra.bases b ON b.id = m.base_id
                    LEFT JOIN muestra.hilos h ON h.id = m.hilo_id
                    WHERE m.activo = true AND (
                        LOWER(m.nombre) LIKE $1 OR LOWER(b.nombre) LIKE $1 OR LOWER(h.nombre) LIKE $1
                    )
                    ORDER BY m.orden, m.nombre
                """, f"%{search.lower()}%")
            else:
                rows = await conn.fetch("""
                    SELECT m.id, m.nombre, m.aprobado, m.activo,
                        b.nombre as base_nombre, h.nombre as hilo_nombre
                    FROM muestra.modelos m
                    LEFT JOIN muestra.bases b ON b.id = m.base_id
                    LEFT JOIN muestra.hilos h ON h.id = m.hilo_id
                    WHERE m.activo = true
                    ORDER BY m.orden, m.nombre
                """)
            return [{**dict(r), "nombre": r["nombre"].replace("Modelo - ", "").replace("Modelo -", "")} for r in rows]
    except Exception as e:
        return {"error": str(e), "items": []}


@api_router.get("/muestras-bases")
async def get_muestras_bases(search: str = ""):
    try:
        pool = await get_muestra_pool()
        async with pool.acquire() as conn:
            query = """
                SELECT b.id, b.nombre,
                    h.nombre as hilo_nombre,
                    m.nombre as marca_nombre, tp.nombre as tipo_nombre,
                    e.nombre as entalle_nombre, t.nombre as tela_nombre
                FROM muestra.bases b
                LEFT JOIN muestra.hilos h ON h.id = b.hilo_id
                LEFT JOIN muestra.muestras_base mb ON mb.id = b.muestra_base_id
                LEFT JOIN muestra.marcas m ON m.id = mb.marca_id
                LEFT JOIN muestra.tipos_producto tp ON tp.id = mb.tipo_producto_id
                LEFT JOIN muestra.entalles e ON e.id = mb.entalle_id
                LEFT JOIN muestra.telas t ON t.id = mb.tela_id
                WHERE b.activo = true
            """
            if search:
                query += " AND (LOWER(b.nombre) LIKE $1 OR LOWER(m.nombre) LIKE $1 OR LOWER(tp.nombre) LIKE $1)"
                rows = await conn.fetch(query + " ORDER BY b.nombre", f"%{search.lower()}%")
            else:
                rows = await conn.fetch(query + " ORDER BY b.nombre")
            return [dict(r) for r in rows]
    except Exception as e:
        return {"error": str(e), "items": []}



@api_router.get("/modelos")
async def get_modelos(
    limit: int = 50,
    offset: int = 0,
    search: str = "",
    marca: str = "",
    tipo: str = "",
    entalle: str = "",
    tela: str = "",
    all: str = "",
    tipo_modelo: str = "",
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # If all=true, return all modelos without pagination (for dropdowns/selects)
        if all == "true":
            rows = await conn.fetch("""
                SELECT m.*,
                    ma.nombre as marca_nombre,
                    t.nombre as tipo_nombre,
                    e.nombre as entalle_nombre,
                    te.nombre as tela_nombre,
                    h.nombre as hilo_nombre,
                    he.nombre as hilo_especifico_nombre,
                    rp.nombre as ruta_nombre,
                    inv.nombre as pt_item_nombre,
                    inv.codigo as pt_item_codigo,
                    ln.nombre as linea_negocio_nombre,
                    base_m.nombre as base_nombre,
                    COALESCE(reg_count.total, 0) as registros_count,
                    COALESCE(var_count.total, 0) as variantes_count
                FROM prod_modelos m
                LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
                LEFT JOIN prod_tipos t ON m.tipo_id = t.id
                LEFT JOIN prod_entalles e ON m.entalle_id = e.id
                LEFT JOIN prod_telas te ON m.tela_id = te.id
                LEFT JOIN prod_hilos h ON m.hilo_id = h.id
                LEFT JOIN prod_hilos_especificos he ON m.hilo_especifico_id = he.id
                LEFT JOIN prod_rutas_produccion rp ON m.ruta_produccion_id = rp.id
                LEFT JOIN prod_inventario inv ON m.pt_item_id = inv.id
                LEFT JOIN finanzas2.cont_linea_negocio ln ON m.linea_negocio_id = ln.id
                LEFT JOIN prod_modelos base_m ON m.base_id = base_m.id
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) as total FROM prod_registros r WHERE r.modelo_id = m.id
                ) reg_count ON true
                LEFT JOIN LATERAL (
                    SELECT COUNT(*) as total FROM prod_modelos v WHERE v.base_id = m.id
                ) var_count ON true
                WHERE ($1 = '' OR ($1 = 'base' AND m.base_id IS NULL) OR ($1 = 'variante' AND m.base_id IS NOT NULL))
                ORDER BY m.created_at DESC
            """, tipo_modelo)
            result = []
            for r in rows:
                d = row_to_dict(r)
                d['servicios_ids'] = parse_jsonb(d.get('servicios_ids'))
                result.append(d)

            # Resolve muestra names from external DB
            muestra_ids = [d['muestra_modelo_id'] for d in result if d.get('muestra_modelo_id')]
            muestra_base_ids = [d['muestra_base_id'] for d in result if d.get('muestra_base_id')]
            if muestra_ids or muestra_base_ids:
                try:
                    m_pool = await get_muestra_pool()
                    async with m_pool.acquire() as m_conn:
                        if muestra_ids:
                            m_rows = await m_conn.fetch(
                                "SELECT m.id, m.nombre, h.nombre as hilo_nombre FROM muestra.modelos m LEFT JOIN muestra.hilos h ON h.id = m.hilo_id WHERE m.id = ANY($1::text[])",
                                muestra_ids
                            )
                            m_map = {str(r['id']): f"{r['nombre'].replace('Modelo - ', '').replace('Modelo -', '')} ({r['hilo_nombre'] or '-'})" for r in m_rows}
                            for d in result:
                                if d.get('muestra_modelo_id'):
                                    d['muestra_nombre'] = m_map.get(d['muestra_modelo_id'], '')
                        if muestra_base_ids:
                            b_rows = await m_conn.fetch(
                                """SELECT b.id, b.nombre, m.nombre as marca, tp.nombre as tipo, e.nombre as entalle, t.nombre as tela
                                FROM muestra.bases b
                                LEFT JOIN muestra.muestras_base mb ON mb.id = b.muestra_base_id
                                LEFT JOIN muestra.marcas m ON m.id = mb.marca_id
                                LEFT JOIN muestra.tipos_producto tp ON tp.id = mb.tipo_producto_id
                                LEFT JOIN muestra.entalles e ON e.id = mb.entalle_id
                                LEFT JOIN muestra.telas t ON t.id = mb.tela_id
                                WHERE b.id = ANY($1::text[])""",
                                muestra_base_ids
                            )
                            b_map = {str(r['id']): r['nombre'] for r in b_rows}
                            b_info_map = {str(r['id']): f"Marca: {r['marca'] or '-'} | Tipo: {r['tipo'] or '-'} | Entalle: {r['entalle'] or '-'} | Tela: {r['tela'] or '-'}" for r in b_rows}
                            for d in result:
                                if d.get('muestra_base_id'):
                                    d['muestra_base_nombre'] = b_map.get(d['muestra_base_id'], '')
                                    d['muestra_base_info'] = b_info_map.get(d['muestra_base_id'], '')
                except Exception:
                    pass

            return result

        # Build WHERE clause dynamically for paginated query
        conditions = []
        params = []
        param_idx = 1

        if tipo_modelo == 'base':
            conditions.append("m.base_id IS NULL")
        elif tipo_modelo == 'variante':
            conditions.append("m.base_id IS NOT NULL")

        if search:
            conditions.append(f"(m.nombre ILIKE ${param_idx} OR ma.nombre ILIKE ${param_idx} OR t.nombre ILIKE ${param_idx} OR e.nombre ILIKE ${param_idx} OR te.nombre ILIKE ${param_idx})")
            params.append(f"%{search}%")
            param_idx += 1

        if marca:
            conditions.append(f"ma.nombre = ${param_idx}")
            params.append(marca)
            param_idx += 1

        if tipo:
            conditions.append(f"t.nombre = ${param_idx}")
            params.append(tipo)
            param_idx += 1

        if entalle:
            conditions.append(f"e.nombre = ${param_idx}")
            params.append(entalle)
            param_idx += 1

        if tela:
            conditions.append(f"te.nombre = ${param_idx}")
            params.append(tela)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Count total
        count_row = await conn.fetchrow(f"""
            SELECT COUNT(*) as total
            FROM prod_modelos m
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            LEFT JOIN prod_tipos t ON m.tipo_id = t.id
            LEFT JOIN prod_entalles e ON m.entalle_id = e.id
            LEFT JOIN prod_telas te ON m.tela_id = te.id
            WHERE {where_clause}
        """, *params)
        total = count_row['total']

        # Get paginated data
        rows = await conn.fetch(f"""
            SELECT m.*,
                ma.nombre as marca_nombre,
                t.nombre as tipo_nombre,
                e.nombre as entalle_nombre,
                te.nombre as tela_nombre,
                h.nombre as hilo_nombre,
                he.nombre as hilo_especifico_nombre,
                rp.nombre as ruta_nombre,
                inv.nombre as pt_item_nombre,
                inv.codigo as pt_item_codigo,
                ln.nombre as linea_negocio_nombre,
                base_m.nombre as base_nombre,
                COALESCE(reg_count.total, 0) as registros_count,
                COALESCE(var_count.total, 0) as variantes_count
            FROM prod_modelos m
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            LEFT JOIN prod_tipos t ON m.tipo_id = t.id
            LEFT JOIN prod_entalles e ON m.entalle_id = e.id
            LEFT JOIN prod_telas te ON m.tela_id = te.id
            LEFT JOIN prod_hilos h ON m.hilo_id = h.id
            LEFT JOIN prod_hilos_especificos he ON m.hilo_especifico_id = he.id
            LEFT JOIN prod_rutas_produccion rp ON m.ruta_produccion_id = rp.id
            LEFT JOIN prod_inventario inv ON m.pt_item_id = inv.id
            LEFT JOIN finanzas2.cont_linea_negocio ln ON m.linea_negocio_id = ln.id
            LEFT JOIN prod_modelos base_m ON m.base_id = base_m.id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) as total FROM prod_registros r WHERE r.modelo_id = m.id
            ) reg_count ON true
            LEFT JOIN LATERAL (
                SELECT COUNT(*) as total FROM prod_modelos v WHERE v.base_id = m.id
            ) var_count ON true
            WHERE {where_clause}
            ORDER BY m.created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """, *params, limit, offset)
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['servicios_ids'] = parse_jsonb(d.get('servicios_ids'))
            result.append(d)

        # Resolve muestra names from external DB
        muestra_ids = [d['muestra_modelo_id'] for d in result if d.get('muestra_modelo_id')]
        if muestra_ids:
            try:
                m_pool = await get_muestra_pool()
                async with m_pool.acquire() as m_conn:
                    m_rows = await m_conn.fetch(
                        "SELECT m.id, m.nombre, h.nombre as hilo_nombre FROM muestra.modelos m LEFT JOIN muestra.hilos h ON h.id = m.hilo_id WHERE m.id = ANY($1::text[])",
                        muestra_ids
                    )
                    m_map = {str(r['id']): f"{r['nombre']} ({r['hilo_nombre'] or '-'})" for r in m_rows}
                    for d in result:
                        if d.get('muestra_modelo_id'):
                            d['muestra_nombre'] = m_map.get(d['muestra_modelo_id'], '')
            except Exception:
                pass

        return {"items": result, "total": total, "limit": limit, "offset": offset}

@api_router.get("/modelos-filtros")
async def get_modelos_filtros():
    """Retorna valores únicos de marca, tipo, entalle y tela para filtros de modelos."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        marcas = await conn.fetch("SELECT DISTINCT ma.nombre FROM prod_modelos m JOIN prod_marcas ma ON m.marca_id = ma.id WHERE ma.nombre IS NOT NULL ORDER BY ma.nombre")
        tipos = await conn.fetch("SELECT DISTINCT t.nombre FROM prod_modelos m JOIN prod_tipos t ON m.tipo_id = t.id WHERE t.nombre IS NOT NULL ORDER BY t.nombre")
        entalles = await conn.fetch("SELECT DISTINCT e.nombre FROM prod_modelos m JOIN prod_entalles e ON m.entalle_id = e.id WHERE e.nombre IS NOT NULL ORDER BY e.nombre")
        telas = await conn.fetch("SELECT DISTINCT te.nombre FROM prod_modelos m JOIN prod_telas te ON m.tela_id = te.id WHERE te.nombre IS NOT NULL ORDER BY te.nombre")
        return {
            "marcas": [r['nombre'] for r in marcas],
            "tipos": [r['nombre'] for r in tipos],
            "entalles": [r['nombre'] for r in entalles],
            "telas": [r['nombre'] for r in telas],
        }


@api_router.get("/modelos/{modelo_id}")
async def get_modelo_detalle(modelo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT m.*, he.nombre as hilo_especifico_nombre, base_m.nombre as base_nombre
            FROM prod_modelos m
            LEFT JOIN prod_hilos_especificos he ON m.hilo_especifico_id = he.id
            LEFT JOIN prod_modelos base_m ON m.base_id = base_m.id
            WHERE m.id = $1
        """, modelo_id)
        if not row:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")

        d = row_to_dict(row)
        return d


@api_router.get("/modelos/{modelo_id}/variantes")
async def get_modelo_variantes(modelo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT m.*, he.nombre as hilo_especifico_nombre,
                COALESCE(reg_count.total, 0) as registros_count
            FROM prod_modelos m
            LEFT JOIN prod_hilos_especificos he ON m.hilo_especifico_id = he.id
            LEFT JOIN LATERAL (
                SELECT COUNT(*) as total FROM prod_registros r WHERE r.modelo_id = m.id
            ) reg_count ON true
            WHERE m.base_id = $1
            ORDER BY m.nombre
        """, modelo_id)
        return [row_to_dict(r) for r in rows]


# ==================== MODELO ↔ TALLAS (BOM) ====================

@api_router.get("/modelos/{modelo_id}/tallas")
async def get_modelo_tallas(modelo_id: str, activo: str = "true"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT mt.*, tc.nombre as talla_nombre
            FROM prod_modelo_tallas mt
            LEFT JOIN prod_tallas_catalogo tc ON mt.talla_id = tc.id
            WHERE mt.modelo_id = $1
        """
        params = [modelo_id]
        if activo == "true":
            query += " AND mt.activo = true"
        elif activo == "false":
            query += " AND mt.activo = false"
        query += " ORDER BY mt.orden ASC, mt.created_at ASC"
        rows = await conn.fetch(query, *params)

    result = []
    for r in rows:
        d = row_to_dict(r)
        if isinstance(d.get('created_at'), datetime):
            d['created_at'] = d['created_at'].strftime('%d/%m/%Y %H:%M')
        if isinstance(d.get('updated_at'), datetime):
            d['updated_at'] = d['updated_at'].strftime('%d/%m/%Y %H:%M')
        result.append(d)
    return result


@api_router.post("/modelos/{modelo_id}/tallas")
async def add_modelo_talla(modelo_id: str, data: ModeloTallaCreate, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    # Validar talla activa en catálogo
    pool = await get_pool()
    async with pool.acquire() as conn:
        talla = await conn.fetchrow("SELECT * FROM prod_tallas_catalogo WHERE id=$1", data.talla_id)
        if not talla:
            raise HTTPException(status_code=404, detail="Talla no encontrada")
        # Nota: prod_tallas_catalogo no tiene campo 'activo' en este proyecto; todas las tallas del catálogo se consideran disponibles.


        # Validación duplicado activo (mensaje claro)
        exists = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_modelo_tallas WHERE modelo_id=$1 AND talla_id=$2 AND activo=true",
            modelo_id,
            data.talla_id,
        )
        if exists and int(exists) > 0:
            raise HTTPException(status_code=400, detail="La talla ya está agregada (activa) en este modelo")

        new_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO prod_modelo_tallas (id, modelo_id, talla_id, activo, orden, created_at, updated_at)
            VALUES ($1,$2,$3,$4,$5,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            """,
            new_id,
            modelo_id,
            data.talla_id,
            bool(data.activo),
            int(data.orden),
        )

        row = await conn.fetchrow(
            """
            SELECT mt.*, tc.nombre as talla_nombre
            FROM prod_modelo_tallas mt
            LEFT JOIN prod_tallas_catalogo tc ON mt.talla_id = tc.id
            WHERE mt.id = $1
            """,
            new_id,
        )

    return row_to_dict(row)


@api_router.put("/modelos/{modelo_id}/tallas/{rel_id}")
async def update_modelo_talla(modelo_id: str, rel_id: str, data: ModeloTallaUpdate, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rel = await conn.fetchrow("SELECT * FROM prod_modelo_tallas WHERE id=$1 AND modelo_id=$2", rel_id, modelo_id)
        if not rel:
            raise HTTPException(status_code=404, detail="Relación modelo-talla no encontrada")

        orden = data.orden if data.orden is not None else rel.get('orden')
        activo_val = data.activo if data.activo is not None else rel.get('activo')

        # Si se intenta reactivar, validar no duplicado activo
        if bool(activo_val) and not bool(rel.get('activo')):
            exists = await conn.fetchval(
                "SELECT COUNT(*) FROM prod_modelo_tallas WHERE modelo_id=$1 AND talla_id=$2 AND activo=true AND id<>$3",
                modelo_id,
                rel.get('talla_id'),
                rel_id,
            )
            if exists and int(exists) > 0:
                raise HTTPException(status_code=400, detail="Ya existe una talla activa duplicada para este modelo")

        await conn.execute(
            "UPDATE prod_modelo_tallas SET orden=$1, activo=$2, updated_at=CURRENT_TIMESTAMP WHERE id=$3",
            int(orden),
            bool(activo_val),
            rel_id,
        )

        row = await conn.fetchrow(
            """
            SELECT mt.*, tc.nombre as talla_nombre
            FROM prod_modelo_tallas mt
            LEFT JOIN prod_tallas_catalogo tc ON mt.talla_id = tc.id
            WHERE mt.id = $1
            """,
            rel_id,
        )

    return row_to_dict(row)


@api_router.delete("/modelos/{modelo_id}/tallas/{rel_id}")
async def delete_modelo_talla(modelo_id: str, rel_id: str, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rel = await conn.fetchrow("SELECT * FROM prod_modelo_tallas WHERE id=$1 AND modelo_id=$2", rel_id, modelo_id)
        if not rel:
            raise HTTPException(status_code=404, detail="Relación modelo-talla no encontrada")

        await conn.execute(
            "UPDATE prod_modelo_tallas SET activo=false, updated_at=CURRENT_TIMESTAMP WHERE id=$1",
            rel_id,
        )

    return {"message": "Talla desactivada"}


# ==================== BOM POR MODELO ====================

@api_router.get("/modelos/{modelo_id}/bom")
async def get_modelo_bom(modelo_id: str, activo: str = "true"):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT bl.*, i.nombre as inventario_nombre, i.codigo as inventario_codigo,
                   tc.nombre as talla_nombre
            FROM prod_modelo_bom_linea bl
            LEFT JOIN prod_inventario i ON bl.inventario_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON bl.talla_id = tc.id
            WHERE bl.modelo_id = $1
        """
        params = [modelo_id]
        if activo == "true":
            query += " AND bl.activo = true"
        elif activo == "false":
            query += " AND bl.activo = false"
        query += " ORDER BY bl.orden ASC, bl.created_at ASC"
        rows = await conn.fetch(query, *params)

    result = []
    for r in rows:
        d = row_to_dict(r)
        if isinstance(d.get('created_at'), datetime):
            d['created_at'] = d['created_at'].strftime('%d/%m/%Y %H:%M')
        if isinstance(d.get('updated_at'), datetime):
            d['updated_at'] = d['updated_at'].strftime('%d/%m/%Y %H:%M')
        result.append(d)
    return result


@api_router.post("/modelos/{modelo_id}/bom")
async def add_modelo_bom_linea(modelo_id: str, data: ModeloBomLineaCreate, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    # Validaciones
    if data.cantidad_base is None or float(data.cantidad_base) <= 0:
        raise HTTPException(status_code=400, detail="cantidad_base debe ser mayor a 0")


    pool = await get_pool()
    async with pool.acquire() as conn:
        # Inventario debe existir
        inv = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id=$1", data.inventario_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")

        # Si talla_id viene, debe pertenecer a tallas activas del modelo
        talla_id = data.talla_id
        if talla_id:
            exists_talla = await conn.fetchval(
                "SELECT COUNT(*) FROM prod_modelo_tallas WHERE modelo_id=$1 AND talla_id=$2 AND activo=true",
                modelo_id,
                talla_id,
            )
            if not exists_talla or int(exists_talla) == 0:
                raise HTTPException(status_code=400, detail="La talla no pertenece a este modelo (o está inactiva)")

        # Duplicado activo exacto
        exists = await conn.fetchval(
            """
            SELECT COUNT(*)
            FROM prod_modelo_bom_linea
            WHERE modelo_id=$1
              AND inventario_id=$2
              AND talla_id IS NOT DISTINCT FROM $3
              AND activo=true
            """,
            modelo_id,
            data.inventario_id,
            talla_id,
        )
        if exists and int(exists) > 0:
            raise HTTPException(status_code=400, detail="Ya existe una línea activa duplicada para este item y talla")

        new_id = str(uuid4())
        await conn.execute(
            """
            INSERT INTO prod_modelo_bom_linea (id, modelo_id, inventario_id, talla_id, unidad_base, cantidad_base, orden, activo, created_at, updated_at)
            VALUES ($1,$2,$3,$4,'PRENDA',$5,$6,$7,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
            """,
            new_id,
            modelo_id,
            data.inventario_id,
            talla_id,
            float(data.cantidad_base),
            10,
            bool(data.activo),
        )

        row = await conn.fetchrow(
            """
            SELECT bl.*, i.nombre as inventario_nombre, i.codigo as inventario_codigo,
                   tc.nombre as talla_nombre
            FROM prod_modelo_bom_linea bl
            LEFT JOIN prod_inventario i ON bl.inventario_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON bl.talla_id = tc.id
            WHERE bl.id = $1
            """,
            new_id,
        )

    return row_to_dict(row)


@api_router.post("/modelos/{modelo_id}/bom/copiar-de/{source_modelo_id}")
async def copiar_bom_de_modelo(modelo_id: str, source_modelo_id: str, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    """Copia todas las líneas BOM activas de un modelo fuente al modelo destino."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        source_lines = await conn.fetch(
            "SELECT inventario_id, talla_id, unidad_base, cantidad_base, orden FROM prod_modelo_bom_linea WHERE modelo_id=$1 AND activo=true ORDER BY orden",
            source_modelo_id
        )
        if not source_lines:
            raise HTTPException(status_code=404, detail="El modelo fuente no tiene líneas BOM activas")

        count = 0
        for sl in source_lines:
            exists = await conn.fetchval(
                "SELECT COUNT(*) FROM prod_modelo_bom_linea WHERE modelo_id=$1 AND inventario_id=$2 AND talla_id IS NOT DISTINCT FROM $3 AND activo=true",
                modelo_id, sl['inventario_id'], sl['talla_id']
            )
            if exists and int(exists) > 0:
                continue
            new_id = str(uuid4())
            await conn.execute(
                "INSERT INTO prod_modelo_bom_linea (id, modelo_id, inventario_id, talla_id, unidad_base, cantidad_base, orden, activo, created_at, updated_at) VALUES ($1,$2,$3,$4,$5,$6,$7,true,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                new_id, modelo_id, sl['inventario_id'], sl['talla_id'], sl['unidad_base'], sl['cantidad_base'], sl['orden']
            )
            count += 1
        return {"message": f"Se copiaron {count} líneas BOM", "lineas_copiadas": count}




@api_router.put("/modelos/{modelo_id}/bom/reorder")
async def reorder_modelo_bom(modelo_id: str, request: ReorderRequest, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    """Reordena líneas BOM de un modelo."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        ids = [it.id for it in request.items]
        if not ids:
            return {"message": "Sin cambios", "items_updated": 0}

        rows = await conn.fetch(
            "SELECT id FROM prod_modelo_bom_linea WHERE modelo_id=$1 AND id = ANY($2::varchar[])",
            modelo_id,
            ids,
        )
        found = {r['id'] for r in rows}
        missing = [i for i in ids if i not in found]
        if missing:
            raise HTTPException(status_code=400, detail="Hay líneas BOM que no pertenecen a este modelo")

        for item in request.items:
            await conn.execute(
                "UPDATE prod_modelo_bom_linea SET orden=$1, updated_at=CURRENT_TIMESTAMP WHERE id=$2",
                int(item.orden),
                item.id,
            )

    return {"message": "Orden actualizado", "items_updated": len(request.items)}


@api_router.put("/modelos/{modelo_id}/bom/{linea_id}")
async def update_modelo_bom_linea(modelo_id: str, linea_id: str, data: ModeloBomLineaUpdate, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        bl = await conn.fetchrow("SELECT * FROM prod_modelo_bom_linea WHERE id=$1 AND modelo_id=$2", linea_id, modelo_id)
        if not bl:
            raise HTTPException(status_code=404, detail="Línea BOM no encontrada")

        inventario_id = data.inventario_id if data.inventario_id is not None else bl.get('inventario_id')
        talla_id = data.talla_id if data.talla_id is not None else bl.get('talla_id')
        cantidad_base = float(data.cantidad_base) if data.cantidad_base is not None else float(bl.get('cantidad_base'))
        activo_val = bool(data.activo) if data.activo is not None else bool(bl.get('activo'))

        if cantidad_base <= 0:
            raise HTTPException(status_code=400, detail="cantidad_base debe ser mayor a 0")

        # Validar inventario existe
        inv = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id=$1", inventario_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")

        # Validar talla pertenece al modelo si aplica
        if talla_id:
            exists_talla = await conn.fetchval(
                "SELECT COUNT(*) FROM prod_modelo_tallas WHERE modelo_id=$1 AND talla_id=$2 AND activo=true",
                modelo_id,
                talla_id,
            )
            if not exists_talla or int(exists_talla) == 0:
                raise HTTPException(status_code=400, detail="La talla no pertenece a este modelo (o está inactiva)")

        # Duplicado activo exacto (si activo=true)
        if activo_val:
            exists = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM prod_modelo_bom_linea
                WHERE modelo_id=$1
                  AND inventario_id=$2
                  AND talla_id IS NOT DISTINCT FROM $3
                  AND activo=true
                  AND id<>$4
                """,
                modelo_id,
                inventario_id,
                talla_id,
                linea_id,
            )
            if exists and int(exists) > 0:
                raise HTTPException(status_code=400, detail="Ya existe una línea activa duplicada para este item y talla")

        await conn.execute(
            """
            UPDATE prod_modelo_bom_linea
            SET inventario_id=$1, talla_id=$2, cantidad_base=$3, activo=$4, updated_at=CURRENT_TIMESTAMP
            WHERE id=$5
            """,
            inventario_id,
            talla_id,
            cantidad_base,
            activo_val,
            linea_id,
        )

        row = await conn.fetchrow(
            """
            SELECT bl.*, i.nombre as inventario_nombre, i.codigo as inventario_codigo,
                   tc.nombre as talla_nombre
            FROM prod_modelo_bom_linea bl
            LEFT JOIN prod_inventario i ON bl.inventario_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON bl.talla_id = tc.id
            WHERE bl.id = $1
            """,
            linea_id,
        )

    return row_to_dict(row)


@api_router.delete("/modelos/{modelo_id}/bom/{linea_id}")
async def delete_modelo_bom_linea(modelo_id: str, linea_id: str, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    pool = await get_pool()
    async with pool.acquire() as conn:
        bl = await conn.fetchrow("SELECT * FROM prod_modelo_bom_linea WHERE id=$1 AND modelo_id=$2", linea_id, modelo_id)
        if not bl:
            raise HTTPException(status_code=404, detail="Línea BOM no encontrada")
        
        await conn.execute("UPDATE prod_modelo_bom_linea SET activo=false, updated_at=CURRENT_TIMESTAMP WHERE id=$1", linea_id)
    
    return {"message": "Línea desactivada", "action": "deactivated"}


@api_router.delete("/modelos/{modelo_id}/bom/{linea_id}/hard")
async def hard_delete_modelo_bom_linea(modelo_id: str, linea_id: str, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    """Elimina físicamente la línea BOM solo si no está vinculada en producción.

    Por ahora la única vinculación real existente en el sistema es la propia tabla BOM.
    En fases futuras, cuando exista Registro/OP, aquí se validará contra esas tablas.

    Comportamiento:
    - Si detecta uso/vinculación: desactiva (activo=false)
    - Si no: borra físicamente
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        bl = await conn.fetchrow(
            "SELECT * FROM prod_modelo_bom_linea WHERE id=$1 AND modelo_id=$2",
            linea_id,
            modelo_id,
        )
        if not bl:
            raise HTTPException(status_code=404, detail="Línea BOM no encontrada")

        # Placeholder de validación de vínculo. En esta fase no existe Registro/OP.
        vinculada = False

        if vinculada:
            await conn.execute(
                "UPDATE prod_modelo_bom_linea SET activo=false, updated_at=CURRENT_TIMESTAMP WHERE id=$1",
                linea_id,
            )
            return {"action": "deactivated", "message": "Línea vinculada: se desactivó"}

        await conn.execute("DELETE FROM prod_modelo_bom_linea WHERE id=$1", linea_id)
        return {"action": "deleted", "message": "Línea eliminada"}


@api_router.post("/modelos")
async def create_modelo(input: ModeloCreate):
    modelo = Modelo(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        servicios_json = json.dumps(modelo.servicios_ids)
        pt_item_id = modelo.pt_item_id or None
        base_id = modelo.base_id or None
        hilo_especifico_id = modelo.hilo_especifico_id or None
        muestra_modelo_id = modelo.muestra_modelo_id or None
        muestra_base_id = modelo.muestra_base_id or None
        await conn.execute(
            """INSERT INTO prod_modelos (id, nombre, marca_id, tipo_id, entalle_id, tela_id, hilo_id, 
               ruta_produccion_id, servicios_ids, pt_item_id, linea_negocio_id, base_id, hilo_especifico_id, muestra_modelo_id, muestra_base_id, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16)""",
            modelo.id, modelo.nombre, modelo.marca_id, modelo.tipo_id, modelo.entalle_id, modelo.tela_id,
            modelo.hilo_id, modelo.ruta_produccion_id, servicios_json, pt_item_id, modelo.linea_negocio_id, base_id, hilo_especifico_id, muestra_modelo_id, muestra_base_id, modelo.created_at.replace(tzinfo=None)
        )
    return modelo

@api_router.put("/modelos/{modelo_id}")
async def update_modelo(modelo_id: str, input: ModeloCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_modelos WHERE id = $1", modelo_id)
        if not result:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")
        servicios_json = json.dumps(input.servicios_ids)
        pt_item_id = input.pt_item_id or None
        base_id = input.base_id or None
        hilo_especifico_id = input.hilo_especifico_id or None
        muestra_modelo_id = input.muestra_modelo_id or None
        muestra_base_id = input.muestra_base_id or None
        await conn.execute(
            """UPDATE prod_modelos SET nombre=$1, marca_id=$2, tipo_id=$3, entalle_id=$4, tela_id=$5, hilo_id=$6,
               ruta_produccion_id=$7, servicios_ids=$8, pt_item_id=$9, linea_negocio_id=$10, base_id=$12, hilo_especifico_id=$13, muestra_modelo_id=$14, muestra_base_id=$15 WHERE id=$11""",
            input.nombre, input.marca_id, input.tipo_id, input.entalle_id, input.tela_id, input.hilo_id,
            input.ruta_produccion_id, servicios_json, pt_item_id, input.linea_negocio_id, modelo_id, base_id, hilo_especifico_id, muestra_modelo_id, muestra_base_id
        )
        return {**row_to_dict(result), **input.model_dump()}

@api_router.delete("/modelos/{modelo_id}")
async def delete_modelo(modelo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_modelos WHERE id = $1", modelo_id)
        return {"message": "Modelo eliminado"}

@api_router.post("/modelos/{modelo_id}/crear-pt")
async def crear_pt_para_modelo(modelo_id: str):
    """Auto-crea un Artículo PT para el modelo y lo vincula"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        modelo = await conn.fetchrow("SELECT * FROM prod_modelos WHERE id = $1", modelo_id)
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")
        
        if modelo['pt_item_id']:
            existing = await conn.fetchrow("SELECT id, nombre FROM prod_inventario WHERE id = $1", modelo['pt_item_id'])
            if existing:
                return {"message": "El modelo ya tiene un PT vinculado", "pt_item_id": modelo['pt_item_id'], "pt_item_nombre": existing['nombre']}
        
        # Generate unique code PT-XXX
        max_code = await conn.fetchval("SELECT codigo FROM prod_inventario WHERE tipo_item = 'PT' ORDER BY codigo DESC LIMIT 1")
        if max_code and max_code.startswith('PT-'):
            try:
                num = int(max_code.replace('PT-', '')) + 1
            except ValueError:
                num = 1
        else:
            num = 1
        nuevo_codigo = f"PT-{num:03d}"
        
        pt_id = str(uuid.uuid4())
        nombre_pt = modelo['nombre']
        
        await conn.execute("""
            INSERT INTO prod_inventario (id, codigo, nombre, tipo_item, categoria, unidad_medida, empresa_id, stock_actual, activo)
            VALUES ($1, $2, $3, 'PT', 'PT', 'unidad', 7, 0, true)
        """, pt_id, nuevo_codigo, nombre_pt)
        
        await conn.execute("UPDATE prod_modelos SET pt_item_id = $1 WHERE id = $2", pt_id, modelo_id)
        
        return {"pt_item_id": pt_id, "pt_item_codigo": nuevo_codigo, "pt_item_nombre": nombre_pt}

@api_router.get("/items-pt")
async def get_items_pt():
    """Lista solo items de tipo PT para selectores"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, codigo, nombre FROM prod_inventario WHERE tipo_item = 'PT' AND activo = true ORDER BY nombre")
        return [row_to_dict(r) for r in rows]


# ==================== ENDPOINTS REGISTROS ====================

@api_router.get("/estados")
async def get_estados():
    return {"estados": ESTADOS_PRODUCCION}

@api_router.get("/registros")
async def get_registros(
    limit: int = 50,
    offset: int = 0,
    search: str = "",
    estados: str = "",
    excluir_estados: str = "Tienda",
    modelo_id: str = "",
    operativo: str = "",
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Build WHERE clause dynamically
        conditions = []
        params = []
        param_idx = 1

        if search:
            conditions.append(f"(r.n_corte ILIKE ${param_idx} OR m.nombre ILIKE ${param_idx})")
            params.append(f"%{search}%")
            param_idx += 1

        if estados:
            estado_list = [e.strip() for e in estados.split(",") if e.strip()]
            if estado_list:
                placeholders = ", ".join(f"${param_idx + i}" for i in range(len(estado_list)))
                conditions.append(f"r.estado IN ({placeholders})")
                params.extend(estado_list)
                param_idx += len(estado_list)

        if excluir_estados:
            excl_list = [e.strip() for e in excluir_estados.split(",") if e.strip()]
            if excl_list:
                placeholders = ", ".join(f"${param_idx + i}" for i in range(len(excl_list)))
                conditions.append(f"(r.estado NOT IN ({placeholders}) OR r.estado IS NULL)")
                params.extend(excl_list)
                param_idx += len(excl_list)

        if modelo_id:
            conditions.append(f"r.modelo_id = ${param_idx}")
            params.append(modelo_id)
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        # Count total
        count_row = await conn.fetchrow(f"""
            SELECT COUNT(*) as total
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            WHERE {where_clause}
        """, *params)
        total = count_row['total']

        # Get paginated data
        rows = await conn.fetch(f"""
            SELECT r.*,
                m.nombre as modelo_nombre,
                ma.nombre as marca_nombre,
                t.nombre as tipo_nombre,
                e.nombre as entalle_nombre,
                te.nombre as tela_nombre,
                h.nombre as hilo_nombre,
                he.nombre as hilo_especifico_nombre,
                rp.n_corte as padre_n_corte,
                (SELECT COUNT(*) FROM prod_incidencia i WHERE i.registro_id = r.id AND i.estado = 'ABIERTA') as incidencias_abiertas,
                (SELECT row_to_json(p.*) FROM prod_paralizacion p WHERE p.registro_id = r.id AND p.activa = TRUE LIMIT 1) as paralizacion_json,
                (SELECT COUNT(*) FROM prod_movimientos_produccion mp WHERE mp.registro_id = r.id AND mp.fecha_esperada_movimiento < CURRENT_DATE) as movs_vencidos,
                (SELECT COUNT(*) FROM prod_registros rh WHERE rh.dividido_desde_registro_id = r.id) as cantidad_divisiones
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            LEFT JOIN prod_tipos t ON m.tipo_id = t.id
            LEFT JOIN prod_entalles e ON m.entalle_id = e.id
            LEFT JOIN prod_telas te ON m.tela_id = te.id
            LEFT JOIN prod_hilos h ON m.hilo_id = h.id
            LEFT JOIN prod_hilos_especificos he ON COALESCE(r.hilo_especifico_id, m.hilo_especifico_id) = he.id
            LEFT JOIN prod_registros rp ON r.dividido_desde_registro_id = rp.id
            WHERE {where_clause}
            ORDER BY r.fecha_creacion DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """, *params, limit, offset)

        result = []
        from datetime import date as date_type
        for r in rows:
            d = row_to_dict(r)
            d['tallas'] = parse_jsonb(d.get('tallas'))
            d['distribucion_colores'] = parse_jsonb(d.get('distribucion_colores'))
            if d.get('fecha_entrega_final'):
                d['fecha_entrega_final'] = str(d['fecha_entrega_final'])
            # Paralización activa
            par_json = d.pop('paralizacion_json', None)
            if par_json and isinstance(par_json, str):
                import json as json_mod
                par_json = json_mod.loads(par_json)
            d['paralizacion_activa'] = par_json
            # Estado operativo
            movs_vencidos = d.pop('movs_vencidos', 0) or 0
            if par_json:
                d['estado_operativo'] = 'PARALIZADA'
            elif d['estado'] != 'Almacén PT':
                if movs_vencidos > 0:
                    d['estado_operativo'] = 'EN_RIESGO'
                elif d.get('fecha_entrega_final'):
                    try:
                        fecha = date_type.fromisoformat(str(d['fecha_entrega_final']))
                        d['estado_operativo'] = 'EN_RIESGO' if fecha < date_type.today() else 'NORMAL'
                    except:
                        d['estado_operativo'] = 'NORMAL'
                else:
                    d['estado_operativo'] = 'NORMAL'
            result.append(d)
        return {"items": result, "total": total, "limit": limit, "offset": offset}

# Endpoint para obtener estados únicos (para filtros)
@api_router.get("/registros-estados")
async def get_registros_estados():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT DISTINCT estado FROM prod_registros WHERE estado IS NOT NULL AND estado != '' ORDER BY estado")
        return [r['estado'] for r in rows]

@api_router.get("/registros/{registro_id}")
async def get_registro(registro_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not row:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        d = row_to_dict(row)
        tallas_raw = parse_jsonb(d.get('tallas'))
        d['distribucion_colores'] = parse_jsonb(d.get('distribucion_colores'))
        
        # Obtener tallas de la tabla prod_registro_tallas (si existen)
        tallas_tabla = await conn.fetch("""
            SELECT rt.talla_id, rt.cantidad_real, tc.nombre as talla_nombre
            FROM prod_registro_tallas rt
            LEFT JOIN prod_tallas_catalogo tc ON rt.talla_id = tc.id
            WHERE rt.registro_id = $1
            ORDER BY tc.orden
        """, registro_id)
        
        if tallas_tabla:
            # Usar datos de la tabla (más actualizados)
            tallas_enriquecidas = [{
                'talla_id': str(t['talla_id']),
                'talla_nombre': t['talla_nombre'] or '',
                'cantidad': int(t['cantidad_real']) if t['cantidad_real'] else 0
            } for t in tallas_tabla]
        else:
            # Fallback al campo JSONB
            tallas_enriquecidas = []
            for t in tallas_raw:
                talla_id = t.get('talla_id')
                if talla_id:
                    talla_info = await conn.fetchrow("SELECT nombre FROM prod_tallas_catalogo WHERE id = $1", talla_id)
                    tallas_enriquecidas.append({
                        'talla_id': talla_id,
                        'talla_nombre': talla_info['nombre'] if talla_info else '',
                        'cantidad': t.get('cantidad', 0)
                    })
        d['tallas'] = tallas_enriquecidas
        
        modelo = await conn.fetchrow("SELECT * FROM prod_modelos WHERE id = $1", d.get('modelo_id'))
        if modelo:
            d['modelo_nombre'] = modelo['nombre']
            marca = await conn.fetchrow("SELECT nombre FROM prod_marcas WHERE id = $1", modelo['marca_id'])
            tipo = await conn.fetchrow("SELECT nombre FROM prod_tipos WHERE id = $1", modelo['tipo_id'])
            entalle = await conn.fetchrow("SELECT nombre FROM prod_entalles WHERE id = $1", modelo['entalle_id'])
            tela = await conn.fetchrow("SELECT nombre FROM prod_telas WHERE id = $1", modelo['tela_id'])
            hilo = await conn.fetchrow("SELECT nombre FROM prod_hilos WHERE id = $1", modelo['hilo_id'])
            d['marca_nombre'] = marca['nombre'] if marca else None
            d['tipo_nombre'] = tipo['nombre'] if tipo else None
            d['entalle_nombre'] = entalle['nombre'] if entalle else None
            d['tela_nombre'] = tela['nombre'] if tela else None
            d['hilo_nombre'] = hilo['nombre'] if hilo else None
        # Enriquecer hilo específico
        if d.get('hilo_especifico_id'):
            hilo_esp = await conn.fetchrow("SELECT nombre FROM prod_hilos_especificos WHERE id = $1", d.get('hilo_especifico_id'))
            d['hilo_especifico_nombre'] = hilo_esp['nombre'] if hilo_esp else None
        # Enriquecer PT item
        if d.get('pt_item_id'):
            pt_item = await conn.fetchrow("SELECT id, codigo, nombre FROM prod_inventario WHERE id = $1", d['pt_item_id'])
            d['pt_item_nombre'] = pt_item['nombre'] if pt_item else None
            d['pt_item_codigo'] = pt_item['codigo'] if pt_item else None
        return d

@api_router.post("/registros")
async def create_registro(input: RegistroCreate):
    registro = Registro(**input.model_dump())
    # Sanitizar FKs opcionales: string vacío → None
    registro.pt_item_id = registro.pt_item_id or None
    registro.hilo_especifico_id = registro.hilo_especifico_id or None
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Heredar linea_negocio_id del modelo si no viene explícito
        if not registro.linea_negocio_id and registro.modelo_id:
            modelo = await conn.fetchrow("SELECT linea_negocio_id FROM prod_modelos WHERE id = $1", registro.modelo_id)
            if modelo and modelo['linea_negocio_id']:
                registro.linea_negocio_id = modelo['linea_negocio_id']
        tallas_json = json.dumps([t.model_dump() for t in registro.tallas])
        dist_json = json.dumps([d.model_dump() for d in registro.distribucion_colores])
        await conn.execute(
            """INSERT INTO prod_registros (id, n_corte, modelo_id, curva, estado, urgente, hilo_especifico_id, tallas, distribucion_colores, fecha_creacion, pt_item_id, empresa_id, id_odoo, observaciones, linea_negocio_id) 
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)""",
            registro.id, registro.n_corte, registro.modelo_id, registro.curva, registro.estado, registro.urgente,
            registro.hilo_especifico_id, tallas_json, dist_json, registro.fecha_creacion.replace(tzinfo=None),
            registro.pt_item_id, registro.empresa_id, registro.id_odoo, registro.observaciones, registro.linea_negocio_id
        )
    return registro

@api_router.put("/registros/{registro_id}/skip-validacion")
async def toggle_skip_validacion(registro_id: str, body: dict):
    """Activa o desactiva la validación de estados para un registro."""
    skip = body.get("skip_validacion_estado", False)
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE prod_registros SET skip_validacion_estado = $1 WHERE id = $2",
            skip, registro_id
        )
        return {"ok": True, "skip_validacion_estado": skip}


@api_router.put("/registros/{registro_id}")
async def update_registro(registro_id: str, input: RegistroCreate):
    # Sanitizar FKs opcionales: string vacío → None
    input.pt_item_id = input.pt_item_id or None
    input.hilo_especifico_id = input.hilo_especifico_id or None
    input.lq_odoo_id = input.lq_odoo_id or None
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not result:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Validar cambio de línea de negocio si hay consumos/movimientos
        old_linea = result.get('linea_negocio_id')
        new_linea = input.linea_negocio_id
        if old_linea and new_linea != old_linea:
            tiene_consumos = await conn.fetchval(
                "SELECT COUNT(*) FROM prod_inventario_salidas WHERE registro_id = $1", registro_id
            )
            tiene_movimientos = await conn.fetchval(
                "SELECT COUNT(*) FROM prod_movimientos_produccion WHERE registro_id = $1", registro_id
            )
            if tiene_consumos > 0 or tiene_movimientos > 0:
                raise HTTPException(
                    status_code=400,
                    detail="No se puede cambiar la línea de negocio: el registro ya tiene consumos o movimientos asociados."
                )
        
        tallas_json = json.dumps([t.model_dump() for t in input.tallas])
        dist_json = json.dumps([d.model_dump() for d in input.distribucion_colores])
        fecha_ef = None
        if input.fecha_entrega_final:
            try:
                fecha_ef = date.fromisoformat(input.fecha_entrega_final)
            except Exception:
                fecha_ef = None
        await conn.execute(
            """UPDATE prod_registros SET n_corte=$1, modelo_id=$2, curva=$3, estado=$4, urgente=$5, hilo_especifico_id=$6, tallas=$7, distribucion_colores=$8, pt_item_id=$9, id_odoo=$10, observaciones=$11, lq_odoo_id=$12, linea_negocio_id=$13, fecha_entrega_final=$15 WHERE id=$14""",
            input.n_corte, input.modelo_id, input.curva, input.estado, input.urgente, input.hilo_especifico_id, tallas_json, dist_json, input.pt_item_id, input.id_odoo, input.observaciones, input.lq_odoo_id, input.linea_negocio_id, registro_id, fecha_ef
        )
        
        # Sincronizar prod_registro_tallas con las cantidades del JSON
        await conn.execute("DELETE FROM prod_registro_tallas WHERE registro_id = $1", registro_id)
        empresa_id = 7  # FK válido para cont_empresa
        for t in input.tallas:
            td = t.model_dump()
            cant = td.get('cantidad', 0)
            if cant > 0:
                await conn.execute(
                    """INSERT INTO prod_registro_tallas (id, registro_id, talla_id, cantidad_real, empresa_id, created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                    str(uuid.uuid4()), registro_id, td['talla_id'], cant, empresa_id
                )
        
        return {**row_to_dict(result), **input.model_dump()}

@api_router.delete("/registros/{registro_id}")
async def delete_registro(registro_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_registros WHERE id = $1", registro_id)
        return {"message": "Registro eliminado"}

@api_router.get("/registros/{registro_id}/estados-disponibles")
async def get_estados_disponibles_registro(registro_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Obtener ruta del modelo
        modelo = await conn.fetchrow("SELECT ruta_produccion_id FROM prod_modelos WHERE id = $1", registro['modelo_id']) if registro['modelo_id'] else None
        ruta_id = modelo['ruta_produccion_id'] if modelo and modelo['ruta_produccion_id'] else None
        
        if ruta_id:
            ruta = await conn.fetchrow("SELECT etapas, nombre FROM prod_rutas_produccion WHERE id = $1", ruta_id)
            if ruta and ruta['etapas']:
                etapas = ruta['etapas'] if isinstance(ruta['etapas'], list) else json.loads(ruta['etapas'])
                etapas_sorted = sorted(etapas, key=lambda e: e.get('orden', 0))
                # Solo mostrar etapas con aparece_en_estado=true (default true para compatibilidad)
                estados = [e['nombre'] for e in etapas_sorted if e.get('nombre') and e.get('aparece_en_estado', True)]
                return {
                    "estados": estados,
                    "usa_ruta": True,
                    "ruta_nombre": ruta['nombre'],
                    "estado_actual": registro['estado'],
                    "etapas_completas": etapas_sorted
                }
        
        # Fallback: lista genérica si no hay ruta
        return {"estados": ESTADOS_PRODUCCION, "usa_ruta": False, "estado_actual": registro['estado']}


@api_router.get("/registros/{registro_id}/analisis-estado")
async def analisis_estado_registro(registro_id: str):
    """Analiza la coherencia entre estado del registro y sus movimientos."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        estado_actual = registro['estado']
        
        # Obtener ruta del modelo
        modelo = await conn.fetchrow("SELECT ruta_produccion_id FROM prod_modelos WHERE id = $1", registro['modelo_id']) if registro['modelo_id'] else None
        ruta_id = modelo['ruta_produccion_id'] if modelo and modelo['ruta_produccion_id'] else None
        
        if not ruta_id:
            return {
                "usa_ruta": False,
                "estado_actual": estado_actual,
                "estado_sugerido": None,
                "siguiente_estado_sugerido": None,
                "movimiento_faltante_por_estado": None,
                "inconsistencias": [],
                "bloqueos": []
            }
        
        ruta = await conn.fetchrow("SELECT etapas, nombre FROM prod_rutas_produccion WHERE id = $1", ruta_id)
        if not ruta or not ruta['etapas']:
            return {
                "usa_ruta": False,
                "estado_actual": estado_actual,
                "estado_sugerido": None,
                "siguiente_estado_sugerido": None,
                "movimiento_faltante_por_estado": None,
                "inconsistencias": [],
                "bloqueos": []
            }
        
        etapas = ruta['etapas'] if isinstance(ruta['etapas'], list) else json.loads(ruta['etapas'])
        etapas_sorted = sorted(etapas, key=lambda e: e.get('orden', 0))
        
        # Obtener movimientos del registro
        movimientos = await conn.fetch(
            "SELECT mp.*, sp.nombre as servicio_nombre FROM prod_movimientos_produccion mp LEFT JOIN prod_servicios_produccion sp ON mp.servicio_id = sp.id WHERE mp.registro_id = $1",
            registro_id
        )
        
        # Mapear movimientos por servicio_id
        movs_por_servicio = {}
        for m in movimientos:
            sid = m['servicio_id']
            if sid not in movs_por_servicio:
                movs_por_servicio[sid] = []
            movs_por_servicio[sid].append(dict(m))
        
        # Encontrar la etapa actual en la ruta
        etapa_actual_idx = None
        for i, et in enumerate(etapas_sorted):
            if et.get('nombre') == estado_actual:
                etapa_actual_idx = i
                break
        
        # Determinar etapas visibles (aparece_en_estado=true)
        etapas_visibles = [e for e in etapas_sorted if e.get('aparece_en_estado', True)]
        
        # --- Calcular estado sugerido basado en movimientos ---
        estado_sugerido = None
        # Recorrer etapas de atrás hacia adelante: la última etapa con movimiento iniciado es la sugerida
        for et in reversed(etapas_sorted):
            sid = et.get('servicio_id')
            if sid and sid in movs_por_servicio:
                movs = movs_por_servicio[sid]
                alguno_iniciado = any(m.get('fecha_inicio') for m in movs)
                if alguno_iniciado and et.get('aparece_en_estado', True):
                    estado_sugerido = et['nombre']
                    break
        
        # --- Calcular siguiente estado sugerido ---
        siguiente_estado_sugerido = None
        if etapa_actual_idx is not None and etapa_actual_idx < len(etapas_sorted) - 1:
            for et in etapas_sorted[etapa_actual_idx + 1:]:
                if et.get('aparece_en_estado', True):
                    siguiente_estado_sugerido = et['nombre']
                    break
        
        # --- Verificar si falta movimiento para el estado actual ---
        movimiento_faltante_por_estado = None
        if etapa_actual_idx is not None:
            etapa_act = etapas_sorted[etapa_actual_idx]
            sid = etapa_act.get('servicio_id')
            if sid and sid not in movs_por_servicio:
                srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", sid)
                movimiento_faltante_por_estado = {
                    "servicio_id": sid,
                    "servicio_nombre": srv['nombre'] if srv else etapa_act['nombre'],
                    "etapa_nombre": etapa_act['nombre']
                }
        
        # --- Inconsistencias ---
        inconsistencias = []
        
        # 1. Estado actual no está en la ruta
        nombres_ruta = [e['nombre'] for e in etapas_sorted]
        if estado_actual not in nombres_ruta:
            inconsistencias.append({
                "tipo": "estado_fuera_ruta",
                "mensaje": f"El estado '{estado_actual}' no existe en la ruta de producción.",
                "severidad": "error"
            })
        
        # 2. Estado avanzado pero etapa anterior tiene problemas
        if etapa_actual_idx is not None:
            for i, et in enumerate(etapas_sorted[:etapa_actual_idx]):
                sid = et.get('servicio_id')
                if not sid:
                    continue
                es_obligatoria = et.get('obligatorio', True)
                if sid in movs_por_servicio:
                    movs = movs_por_servicio[sid]
                    alguno_sin_cerrar = any(m.get('fecha_inicio') and not m.get('fecha_fin') for m in movs)
                    if alguno_sin_cerrar:
                        sev = "warning" if es_obligatoria else "info"
                        inconsistencias.append({
                            "tipo": "etapa_previa_abierta",
                            "mensaje": f"La etapa '{et['nombre']}' tiene movimiento(s) sin cerrar (sin fecha_fin).",
                            "severidad": sev
                        })
                elif es_obligatoria:
                    # Etapa obligatoria previa sin movimiento
                    inconsistencias.append({
                        "tipo": "etapa_obligatoria_sin_movimiento",
                        "mensaje": f"La etapa obligatoria '{et['nombre']}' no tiene movimiento registrado.",
                        "severidad": "warning"
                    })
        
        # 3. Estado sugiere que estamos en etapa X pero ya hay movimientos de etapas posteriores
        if etapa_actual_idx is not None:
            for et in etapas_sorted[etapa_actual_idx + 1:]:
                sid = et.get('servicio_id')
                if sid and sid in movs_por_servicio:
                    movs = movs_por_servicio[sid]
                    alguno_iniciado = any(m.get('fecha_inicio') for m in movs)
                    if alguno_iniciado and et.get('aparece_en_estado', True):
                        inconsistencias.append({
                            "tipo": "movimiento_adelantado",
                            "mensaje": f"Ya existe movimiento de '{et['nombre']}' pero el estado sigue en '{estado_actual}'.",
                            "severidad": "info"
                        })
        
        # --- Bloqueos (solo graves) ---
        bloqueos = []
        
        return {
            "usa_ruta": True,
            "ruta_nombre": ruta['nombre'],
            "estado_actual": estado_actual,
            "estado_sugerido": estado_sugerido,
            "siguiente_estado_sugerido": siguiente_estado_sugerido,
            "movimiento_faltante_por_estado": movimiento_faltante_por_estado,
            "inconsistencias": inconsistencias,
            "bloqueos": bloqueos,
            "etapas": etapas_sorted,
            "movimientos_resumen": [
                {
                    "servicio_id": m['servicio_id'],
                    "servicio_nombre": m['servicio_nombre'],
                    "fecha_inicio": str(m['fecha_inicio']) if m.get('fecha_inicio') else None,
                    "fecha_fin": str(m['fecha_fin']) if m.get('fecha_fin') else None
                } for m in movimientos
            ]
        }

@api_router.post("/registros/{registro_id}/validar-cambio-estado")
async def validar_cambio_estado(registro_id: str, body: dict):
    """Valida si un cambio de estado es permitido. Retorna bloqueos si los hay.
    Si body incluye forzar=true, se saltan las validaciones de movimientos."""
    nuevo_estado = body.get("nuevo_estado")
    forzar = body.get("forzar", False)
    if not nuevo_estado:
        raise HTTPException(status_code=400, detail="nuevo_estado requerido")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Bloqueo por paralización activa
        par_activa = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_paralizacion WHERE registro_id = $1 AND activa = TRUE", registro_id
        )
        if par_activa and par_activa > 0:
            return {
                "permitido": False,
                "bloqueos": [{"mensaje": "El registro esta PARALIZADO. Resuelve la incidencia que paraliza antes de cambiar de estado.", "servicio_id": None, "movimiento_id": None, "etapa": None}],
                "sugerencia_movimiento": None,
                "paralizado": True
            }
        
        modelo = await conn.fetchrow("SELECT ruta_produccion_id FROM prod_modelos WHERE id = $1", registro['modelo_id']) if registro['modelo_id'] else None
        ruta_id = modelo['ruta_produccion_id'] if modelo and modelo['ruta_produccion_id'] else None
        
        if not ruta_id:
            return {"permitido": True, "bloqueos": [], "sugerencia_movimiento": None}
        
        ruta = await conn.fetchrow("SELECT etapas FROM prod_rutas_produccion WHERE id = $1", ruta_id)
        if not ruta or not ruta['etapas']:
            return {"permitido": True, "bloqueos": [], "sugerencia_movimiento": None}
        
        etapas = ruta['etapas'] if isinstance(ruta['etapas'], list) else json.loads(ruta['etapas'])
        etapas_sorted = sorted(etapas, key=lambda e: e.get('orden', 0))
        nombres_ruta = [e['nombre'] for e in etapas_sorted]
        
        # Si se fuerza el cambio O el registro tiene skip_validacion_estado, permitir sin validaciones
        if forzar or registro.get('skip_validacion_estado'):
            return {"permitido": True, "bloqueos": [], "forzado": True, "sugerencia_movimiento": None}
        
        bloqueos = []
        
        # Bloqueo 1: estado fuera de ruta
        if nuevo_estado not in nombres_ruta:
            bloqueos.append({"mensaje": f"El estado '{nuevo_estado}' no pertenece a la ruta de producción asignada.", "servicio_id": None, "movimiento_id": None, "etapa": None})
        
        # Bloqueo 2: saltar etapa obligatoria previa sin movimiento completado
        nuevo_idx = None
        for i, e in enumerate(etapas_sorted):
            if e['nombre'] == nuevo_estado:
                nuevo_idx = i
                break
        
        movimientos = await conn.fetch(
            "SELECT id, servicio_id, fecha_inicio, fecha_fin FROM prod_movimientos_produccion WHERE registro_id = $1",
            registro_id
        )
        movs_por_servicio = {}
        for m in movimientos:
            sid = m['servicio_id']
            if sid not in movs_por_servicio:
                movs_por_servicio[sid] = []
            movs_por_servicio[sid].append(dict(m))
        
        if nuevo_idx is not None:
            # Si es un registro dividido, verificar movimientos del padre para etapas previas
            es_division = bool(registro.get('dividido_desde_registro_id'))
            movs_padre = {}
            if es_division and registro['dividido_desde_registro_id']:
                movs_padre_rows = await conn.fetch(
                    "SELECT servicio_id, fecha_inicio, fecha_fin FROM prod_movimientos_produccion WHERE registro_id = $1",
                    registro['dividido_desde_registro_id']
                )
                for m in movs_padre_rows:
                    sid = m['servicio_id']
                    if sid not in movs_padre:
                        movs_padre[sid] = []
                    movs_padre[sid].append(dict(m))
            
            for et in etapas_sorted[:nuevo_idx]:
                sid = et.get('servicio_id')
                if not sid:
                    continue
                es_obligatoria = et.get('obligatorio', True)
                
                tiene_mov_propio = sid in movs_por_servicio
                tiene_mov_padre = sid in movs_padre
                
                if es_obligatoria and not tiene_mov_propio and not tiene_mov_padre:
                    bloqueos.append({"mensaje": f"La etapa obligatoria '{et['nombre']}' no tiene movimiento registrado.", "servicio_id": sid, "movimiento_id": None, "etapa": et['nombre']})
                elif tiene_mov_propio:
                    alguno_abierto = any(m.get('fecha_inicio') and not m.get('fecha_fin') for m in movs_por_servicio[sid])
                    if alguno_abierto:
                        mov_abierto = next((m for m in movs_por_servicio[sid] if m.get('fecha_inicio') and not m.get('fecha_fin')), None)
                        mov_id = mov_abierto.get('id') if mov_abierto else None
                        if es_obligatoria:
                            bloqueos.append({"mensaje": f"La etapa obligatoria '{et['nombre']}' tiene movimiento iniciado sin cerrar.", "servicio_id": sid, "movimiento_id": mov_id, "etapa": et['nombre']})
                        else:
                            bloqueos.append({"mensaje": f"La etapa '{et['nombre']}' tiene movimiento activo sin cerrar.", "servicio_id": sid, "movimiento_id": mov_id, "etapa": et['nombre']})
        
        # Sugerencia: si el nuevo estado tiene servicio vinculado y no hay movimiento
        sugerencia_movimiento = None
        if nuevo_idx is not None and not bloqueos:
            etapa_nueva = etapas_sorted[nuevo_idx]
            sid = etapa_nueva.get('servicio_id')
            if sid and sid not in movs_por_servicio:
                srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", sid)
                sugerencia_movimiento = {
                    "servicio_id": sid,
                    "servicio_nombre": srv['nombre'] if srv else etapa_nueva['nombre'],
                    "etapa_nombre": etapa_nueva['nombre']
                }
        
        return {
            "permitido": len(bloqueos) == 0,
            "bloqueos": bloqueos,
            "sugerencia_movimiento": sugerencia_movimiento
        }



# ==================== FASE 2: ENDPOINTS TALLAS POR REGISTRO ====================

@api_router.get("/registros/{registro_id}/tallas")
async def get_registro_tallas(registro_id: str):
    """Obtiene las cantidades reales por talla de un registro"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        modelo_id = registro['modelo_id']
        
        # Obtener tallas del modelo (prod_modelo_tallas)
        modelo_tallas = await conn.fetch("""
            SELECT mt.talla_id, tc.nombre as talla_nombre, tc.orden
            FROM prod_modelo_tallas mt
            JOIN prod_tallas_catalogo tc ON mt.talla_id = tc.id
            WHERE mt.modelo_id = $1 AND mt.activo = true
            ORDER BY tc.orden, tc.nombre
        """, modelo_id)
        
        # Obtener cantidades reales ya registradas
        registro_tallas = await conn.fetch(
            "SELECT * FROM prod_registro_tallas WHERE registro_id = $1", registro_id
        )
        tallas_map = {rt['talla_id']: rt for rt in registro_tallas}
        
        result = []
        total_prendas = 0
        for mt in modelo_tallas:
            talla_id = mt['talla_id']
            rt = tallas_map.get(talla_id)
            cantidad_real = int(rt['cantidad_real']) if rt else 0
            total_prendas += cantidad_real
            result.append({
                "talla_id": talla_id,
                "talla_nombre": mt['talla_nombre'],
                "talla_orden": mt['orden'],
                "cantidad_real": cantidad_real,
                "id": rt['id'] if rt else None
            })
        
        return {
            "registro_id": registro_id,
            "modelo_id": modelo_id,
            "tallas": result,
            "total_prendas": total_prendas
        }


@api_router.post("/registros/{registro_id}/tallas")
async def upsert_registro_tallas(registro_id: str, input: RegistroTallaBulkUpdate):
    """Actualiza (upsert) las cantidades reales por talla de un registro"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        modelo_id = registro['modelo_id']
        
        # Validar que todas las tallas pertenecen al modelo
        modelo_tallas = await conn.fetch(
            "SELECT talla_id FROM prod_modelo_tallas WHERE modelo_id = $1 AND activo = true", modelo_id
        )
        valid_tallas = {mt['talla_id'] for mt in modelo_tallas}
        
        updated = []
        for t in input.tallas:
            if t.talla_id not in valid_tallas:
                raise HTTPException(status_code=400, detail=f"Talla {t.talla_id} no pertenece al modelo")
            
            # Upsert: buscar si existe, si no crear
            existing = await conn.fetchrow(
                "SELECT id FROM prod_registro_tallas WHERE registro_id = $1 AND talla_id = $2",
                registro_id, t.talla_id
            )
            
            if existing:
                await conn.execute(
                    "UPDATE prod_registro_tallas SET cantidad_real = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    t.cantidad_real, existing['id']
                )
                updated.append({"id": existing['id'], "talla_id": t.talla_id, "cantidad_real": t.cantidad_real})
            else:
                new_id = str(uuid.uuid4())
                await conn.execute(
                    """INSERT INTO prod_registro_tallas (id, registro_id, talla_id, cantidad_real)
                       VALUES ($1, $2, $3, $4)""",
                    new_id, registro_id, t.talla_id, t.cantidad_real
                )
                updated.append({"id": new_id, "talla_id": t.talla_id, "cantidad_real": t.cantidad_real})
        
        return {"message": "Tallas actualizadas", "updated": updated}


@api_router.put("/registros/{registro_id}/tallas/{talla_id}")
async def update_single_registro_talla(registro_id: str, talla_id: str, input: RegistroTallaUpdate):
    """Actualiza una sola talla de un registro (para autosave)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        modelo_id = registro['modelo_id']
        
        # Validar talla pertenece al modelo
        modelo_talla = await conn.fetchrow(
            "SELECT talla_id FROM prod_modelo_tallas WHERE modelo_id = $1 AND talla_id = $2 AND activo = true",
            modelo_id, talla_id
        )
        if not modelo_talla:
            raise HTTPException(status_code=400, detail="Talla no pertenece al modelo")
        
        # Upsert
        existing = await conn.fetchrow(
            "SELECT id FROM prod_registro_tallas WHERE registro_id = $1 AND talla_id = $2",
            registro_id, talla_id
        )
        
        if existing:
            await conn.execute(
                "UPDATE prod_registro_tallas SET cantidad_real = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                input.cantidad_real, existing['id']
            )
            return {"id": existing['id'], "talla_id": talla_id, "cantidad_real": input.cantidad_real}
        else:
            new_id = str(uuid.uuid4())
            await conn.execute(
                """INSERT INTO prod_registro_tallas (id, registro_id, talla_id, cantidad_real)
                   VALUES ($1, $2, $3, $4)""",
                new_id, registro_id, talla_id, input.cantidad_real
            )
            return {"id": new_id, "talla_id": talla_id, "cantidad_real": input.cantidad_real}


# ==================== FASE 2: ENDPOINTS REQUERIMIENTO MP (EXPLOSIÓN BOM) ====================

def calcular_estado_requerimiento(cantidad_requerida: float, cantidad_reservada: float, cantidad_consumida: float) -> str:
    """Calcula el estado de una línea de requerimiento"""
    if cantidad_requerida <= 0:
        return 'PENDIENTE'
    if cantidad_consumida >= cantidad_requerida:
        return 'COMPLETO'
    if cantidad_reservada > 0 or cantidad_consumida > 0:
        return 'PARCIAL'
    return 'PENDIENTE'


@api_router.post("/registros/{registro_id}/generar-requerimiento")
async def generar_requerimiento_mp(registro_id: str, bom_id: str = Query(None)):
    """Genera el requerimiento de MP a partir de la explosión del BOM.
    Si bom_id se proporciona, usa ese BOM específico.
    Si no, auto-selecciona el mejor BOM (APROBADO > BORRADOR, versión más reciente)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Obtener registro
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        modelo_id = registro['modelo_id']
        
        # Obtener cantidades reales por talla
        tallas_registro = await conn.fetch(
            "SELECT talla_id, cantidad_real FROM prod_registro_tallas WHERE registro_id = $1",
            registro_id
        )
        tallas_map = {t['talla_id']: int(t['cantidad_real']) for t in tallas_registro}
        total_prendas = sum(tallas_map.values())
        
        if total_prendas <= 0:
            raise HTTPException(status_code=400, detail="Ingresa cantidades reales por talla antes de generar el requerimiento")
        
        # Determinar qué BOM usar
        if bom_id:
            bom_cab = await conn.fetchrow("SELECT * FROM prod_bom_cabecera WHERE id = $1", bom_id)
            if not bom_cab:
                raise HTTPException(status_code=404, detail="BOM no encontrado")
        else:
            # Auto-seleccionar mejor BOM: APROBADO primero, luego BORRADOR, versión más reciente
            bom_cab = await conn.fetchrow("""
                SELECT * FROM prod_bom_cabecera
                WHERE modelo_id = $1 AND estado != 'INACTIVO'
                ORDER BY CASE estado WHEN 'APROBADO' THEN 1 WHEN 'BORRADOR' THEN 2 ELSE 3 END, version DESC
                LIMIT 1
            """, modelo_id)
        
        # Obtener BOM activo del modelo, filtrando por bom_id si existe
        if bom_cab:
            bom_lineas = await conn.fetch("""
                SELECT bl.*, i.nombre as item_nombre, i.codigo as item_codigo, i.unidad_medida
                FROM prod_modelo_bom_linea bl
                JOIN prod_inventario i ON bl.inventario_id = i.id
                WHERE bl.bom_id = $1 AND bl.activo = true
                  AND COALESCE(bl.tipo_componente, 'TELA') IN ('TELA', 'AVIO', 'EMPAQUE', 'OTRO')
            """, bom_cab['id'])
        else:
            # Fallback: líneas sin bom_id asignado (datos legacy)
            bom_lineas = await conn.fetch("""
                SELECT bl.*, i.nombre as item_nombre, i.codigo as item_codigo, i.unidad_medida
                FROM prod_modelo_bom_linea bl
                JOIN prod_inventario i ON bl.inventario_id = i.id
                WHERE bl.modelo_id = $1 AND bl.activo = true AND bl.bom_id IS NULL
            """, modelo_id)
        
        if not bom_lineas:
            raise HTTPException(status_code=400, detail="El modelo no tiene BOM definido")
        
        created = 0
        updated = 0
        empresa_id = registro.get('empresa_id') or 8
        
        for bom in bom_lineas:
            item_id = bom['inventario_id']
            cantidad_base = float(bom['cantidad_base'])
            talla_id = bom['talla_id']  # Puede ser NULL
            
            # Calcular cantidad requerida
            if talla_id is None:
                # Línea general: aplica a todas las prendas
                cantidad_requerida = total_prendas * cantidad_base
            else:
                # Línea específica por talla
                qty_talla = tallas_map.get(talla_id, 0)
                cantidad_requerida = qty_talla * cantidad_base
            
            # Buscar si ya existe requerimiento para este (registro, item, talla)
            if talla_id:
                existing = await conn.fetchrow("""
                    SELECT * FROM prod_registro_requerimiento_mp
                    WHERE registro_id = $1 AND item_id = $2 AND talla_id = $3
                """, registro_id, item_id, talla_id)
            else:
                existing = await conn.fetchrow("""
                    SELECT * FROM prod_registro_requerimiento_mp
                    WHERE registro_id = $1 AND item_id = $2 AND talla_id IS NULL
                """, registro_id, item_id)
            
            if existing:
                # Actualizar solo cantidad_requerida, NO resetear reservada/consumida
                cantidad_reservada = float(existing['cantidad_reservada'])
                cantidad_consumida = float(existing['cantidad_consumida'])
                nuevo_estado = calcular_estado_requerimiento(cantidad_requerida, cantidad_reservada, cantidad_consumida)
                
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_requerida = $1, estado = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3
                """, cantidad_requerida, nuevo_estado, existing['id'])
                updated += 1
            else:
                # Crear nuevo requerimiento
                new_id = str(uuid.uuid4())
                estado = 'PENDIENTE' if cantidad_requerida > 0 else 'COMPLETO'
                await conn.execute("""
                    INSERT INTO prod_registro_requerimiento_mp
                    (id, registro_id, item_id, talla_id, cantidad_requerida, cantidad_reservada, cantidad_consumida, estado, empresa_id)
                    VALUES ($1, $2, $3, $4, $5, 0, 0, $6, $7)
                """, new_id, registro_id, item_id, talla_id, cantidad_requerida, estado, empresa_id)
                created += 1
        
        return {
            "message": "Requerimiento generado",
            "total_prendas": total_prendas,
            "lineas_creadas": created,
            "lineas_actualizadas": updated,
            "bom_usado": {
                "id": bom_cab['id'],
                "codigo": bom_cab['codigo'],
                "version": bom_cab['version'],
                "estado": bom_cab['estado'],
            } if bom_cab else None
        }


@api_router.get("/registros/{registro_id}/requerimiento")
async def get_requerimiento_mp(registro_id: str):
    """Obtiene el requerimiento de MP de un registro"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        rows = await conn.fetch("""
            SELECT r.*, i.codigo as item_codigo, i.nombre as item_nombre, 
                   i.unidad_medida as item_unidad, i.control_por_rollos,
                   tc.nombre as talla_nombre
            FROM prod_registro_requerimiento_mp r
            JOIN prod_inventario i ON r.item_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON r.talla_id = tc.id
            WHERE r.registro_id = $1
            ORDER BY i.nombre, tc.orden NULLS FIRST
        """, registro_id)
        
        result = []
        for r in rows:
            d = row_to_dict(r)
            cantidad_requerida = float(d['cantidad_requerida'])
            cantidad_reservada = float(d['cantidad_reservada'])
            cantidad_consumida = float(d['cantidad_consumida'])
            d['pendiente_reservar'] = max(0, cantidad_requerida - cantidad_reservada)
            d['pendiente_consumir'] = max(0, cantidad_reservada - cantidad_consumida)
            result.append(d)
        
        # Calcular totales
        total_requerido = sum(float(r['cantidad_requerida']) for r in result)
        total_reservado = sum(float(r['cantidad_reservada']) for r in result)
        total_consumido = sum(float(r['cantidad_consumida']) for r in result)
        
        return {
            "registro_id": registro_id,
            "lineas": result,
            "resumen": {
                "total_lineas": len(result),
                "total_requerido": total_requerido,
                "total_reservado": total_reservado,
                "total_consumido": total_consumido,
                "pendiente_reservar": max(0, total_requerido - total_reservado),
                "pendiente_consumir": max(0, total_reservado - total_consumido)
            }
        }


@api_router.get("/registros/{registro_id}/materiales")
async def get_materiales_consolidado(registro_id: str):
    """Vista consolidada: requerimiento + reservas + salidas de un registro en una sola respuesta."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # 1) Requerimiento
        req_rows = await conn.fetch("""
            SELECT r.*, i.codigo as item_codigo, i.nombre as item_nombre,
                   i.unidad_medida as item_unidad, i.stock_actual, i.control_por_rollos,
                   tc.nombre as talla_nombre
            FROM prod_registro_requerimiento_mp r
            JOIN prod_inventario i ON r.item_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON r.talla_id = tc.id
            WHERE r.registro_id = $1
            ORDER BY i.nombre, tc.orden NULLS FIRST
        """, registro_id)
        
        # 2) Reservas activas con detalle de líneas
        reservas = await conn.fetch("""
            SELECT r.id, r.estado, r.created_at as fecha
            FROM prod_inventario_reservas r
            WHERE r.registro_id = $1
            ORDER BY r.created_at DESC
        """, registro_id)
        
        reservas_list = []
        for res in reservas:
            lineas_r = await conn.fetch("""
                SELECT rl.*, i.codigo as item_codigo, i.nombre as item_nombre, i.unidad_medida as item_unidad,
                       tc.nombre as talla_nombre
                FROM prod_inventario_reservas_linea rl
                JOIN prod_inventario i ON rl.item_id = i.id
                LEFT JOIN prod_tallas_catalogo tc ON rl.talla_id = tc.id
                WHERE rl.reserva_id = $1
            """, res['id'])
            reservas_list.append({
                "id": res['id'],
                "estado": res['estado'],
                "fecha": str(res['fecha']) if res['fecha'] else None,
                "lineas": [{
                    **row_to_dict(l),
                    "cantidad_activa": max(0, float(l['cantidad_reservada']) - float(l['cantidad_liberada']))
                } for l in lineas_r]
            })
        
        # 3) Salidas relacionadas
        salidas = await conn.fetch("""
            SELECT s.*, i.codigo as item_codigo, i.nombre as item_nombre, i.unidad_medida as item_unidad
            FROM prod_inventario_salidas s
            JOIN prod_inventario i ON s.item_id = i.id
            WHERE s.registro_id = $1
            ORDER BY s.fecha DESC
        """, registro_id)
        
        # 4) Disponibilidad por item (con reservas globales)
        item_ids = list(set(r['item_id'] for r in req_rows))
        disponibilidad = {}
        for iid in item_ids:
            disp = await get_disponibilidad_item(conn, iid)
            if disp:
                disponibilidad[iid] = disp
        
        # Armar resultado
        lineas = []
        for r in req_rows:
            d = row_to_dict(r)
            req = float(d['cantidad_requerida'])
            res_qty = float(d['cantidad_reservada'])
            con = float(d['cantidad_consumida'])
            item_disp = disponibilidad.get(d['item_id'], {})
            d['pendiente'] = max(0, req - con)
            d['disponible'] = item_disp.get('disponible', 0)
            d['stock_actual'] = item_disp.get('stock_actual', float(d.get('stock_actual') or 0))
            # Para items con control_por_rollos, incluir rollos disponibles
            if d.get('control_por_rollos'):
                rollos = await conn.fetch("""
                    SELECT r.id, r.numero_rollo, r.metraje_disponible, r.tono, r.ancho,
                           ing.fecha as fecha_ingreso
                    FROM prod_inventario_rollos r
                    JOIN prod_inventario_ingresos ing ON r.ingreso_id = ing.id
                    WHERE r.item_id = $1 AND r.metraje_disponible > 0
                    ORDER BY ing.fecha ASC
                """, d['item_id'])
                d['rollos_disponibles'] = [dict(ro) for ro in rollos]
                for ro in d['rollos_disponibles']:
                    ro['metraje_disponible'] = float(ro['metraje_disponible'])
                    ro['fecha_ingreso'] = str(ro['fecha_ingreso']) if ro.get('fecha_ingreso') else None
                    ro['ancho'] = float(ro['ancho']) if ro.get('ancho') else None
            lineas.append(d)
        
        total_req = sum(float(l['cantidad_requerida']) for l in lineas)
        total_res = sum(float(l['cantidad_reservada']) for l in lineas)
        total_con = sum(float(l['cantidad_consumida']) for l in lineas)
        
        return {
            "registro_id": registro_id,
            "tiene_requerimiento": len(lineas) > 0,
            "lineas": lineas,
            "resumen": {
                "total_lineas": len(lineas),
                "total_requerido": total_req,
                "total_reservado": total_res,
                "total_consumido": total_con,
                "total_pendiente": max(0, total_req - total_con),
            },
            "reservas": reservas_list,
            "salidas": [row_to_dict(s) for s in salidas],
        }



# ==================== FASE 2: ENDPOINTS RESERVAS ====================

async def get_disponibilidad_item(conn, item_id: str) -> dict:
    """Calcula la disponibilidad real de un item (stock - reservas activas)"""
    item = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", item_id)
    if not item:
        return None
    
    stock_actual = float(item['stock_actual'])
    
    # Sumar reservas activas (cantidad_reservada - cantidad_liberada)
    total_reservado = await conn.fetchval("""
        SELECT COALESCE(SUM(rl.cantidad_reservada - rl.cantidad_liberada), 0)
        FROM prod_inventario_reservas_linea rl
        JOIN prod_inventario_reservas r ON rl.reserva_id = r.id
        WHERE rl.item_id = $1 AND r.estado = 'ACTIVA'
    """, item_id)
    
    total_reservado = float(total_reservado or 0)
    disponible = max(0, stock_actual - total_reservado)
    
    return {
        "item_id": item_id,
        "item_codigo": item['codigo'],
        "item_nombre": item['nombre'],
        "stock_actual": stock_actual,
        "total_reservado": total_reservado,
        "disponible": disponible,
        "control_por_rollos": item['control_por_rollos']
    }


@api_router.get("/inventario/{item_id}/disponibilidad")
async def get_disponibilidad_inventario(item_id: str):
    """Obtiene la disponibilidad real de un item (stock - reservas activas)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await get_disponibilidad_item(conn, item_id)
        if not result:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        return result


@api_router.post("/registros/{registro_id}/reservas")
async def crear_reserva(registro_id: str, input: ReservaCreateInput):
    """Crea una reserva para un registro"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Validar registro
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # FASE 2C: Validar que OP no esté cerrada/anulada
        if registro['estado'] in ('CERRADA', 'ANULADA'):
            raise HTTPException(
                status_code=400, 
                detail=f"OP {registro['estado'].lower()}: no se puede crear reservas en una orden {registro['estado'].lower()}"
            )
        
        if not input.lineas:
            raise HTTPException(status_code=400, detail="Debe incluir al menos una línea de reserva")
        
        # Validar cada línea
        errores = []
        for idx, linea in enumerate(input.lineas):
            # Buscar requerimiento
            if linea.talla_id:
                req = await conn.fetchrow("""
                    SELECT * FROM prod_registro_requerimiento_mp
                    WHERE registro_id = $1 AND item_id = $2 AND talla_id = $3
                """, registro_id, linea.item_id, linea.talla_id)
            else:
                req = await conn.fetchrow("""
                    SELECT * FROM prod_registro_requerimiento_mp
                    WHERE registro_id = $1 AND item_id = $2 AND talla_id IS NULL
                """, registro_id, linea.item_id)
            
            if not req:
                errores.append(f"Línea {idx+1}: No existe requerimiento para item_id={linea.item_id}, talla_id={linea.talla_id}")
                continue
            
            # OPCIÓN 1: Ya NO limitamos al pendiente_reservar - se puede reservar más si hay stock disponible
            # Solo validamos disponibilidad global
            disp = await get_disponibilidad_item(conn, linea.item_id)
            if not disp:
                errores.append(f"Línea {idx+1}: Item no encontrado")
                continue
            
            if linea.cantidad > disp['disponible']:
                errores.append(f"Línea {idx+1}: Cantidad ({linea.cantidad}) excede disponible ({disp['disponible']})")
        
        if errores:
            raise HTTPException(status_code=400, detail={"errores": errores})
        
        # Crear cabecera de reserva
        reserva_id = str(uuid.uuid4())
        await conn.execute("""
            INSERT INTO prod_inventario_reservas (id, registro_id, estado, empresa_id)
            VALUES ($1, $2, 'ACTIVA', $3)
        """, reserva_id, registro_id, registro['empresa_id'])
        
        # Crear líneas y actualizar requerimiento
        lineas_creadas = []
        for linea in input.lineas:
            linea_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO prod_inventario_reservas_linea
                (id, reserva_id, item_id, talla_id, cantidad_reservada, cantidad_liberada, empresa_id)
                VALUES ($1, $2, $3, $4, $5, 0, $6)
            """, linea_id, reserva_id, linea.item_id, linea.talla_id, linea.cantidad, registro['empresa_id'])
            
            # Actualizar cantidad_reservada en requerimiento
            if linea.talla_id:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_reservada = cantidad_reservada + $1, updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id = $4
                """, linea.cantidad, registro_id, linea.item_id, linea.talla_id)
            else:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_reservada = cantidad_reservada + $1, updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id IS NULL
                """, linea.cantidad, registro_id, linea.item_id)
            
            lineas_creadas.append({
                "id": linea_id,
                "item_id": linea.item_id,
                "talla_id": linea.talla_id,
                "cantidad_reservada": linea.cantidad
            })
        
        # Recalcular estados de requerimiento
        await conn.execute("""
            UPDATE prod_registro_requerimiento_mp
            SET estado = CASE
                WHEN cantidad_consumida >= cantidad_requerida THEN 'COMPLETO'
                WHEN cantidad_reservada > 0 OR cantidad_consumida > 0 THEN 'PARCIAL'
                ELSE 'PENDIENTE'
            END
            WHERE registro_id = $1
        """, registro_id)
        
        return {
            "message": "Reserva creada",
            "reserva_id": reserva_id,
            "lineas": lineas_creadas
        }


@api_router.get("/registros/{registro_id}/reservas")
async def get_reservas_registro(registro_id: str):
    """Lista las reservas de un registro"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Obtener cabeceras de reserva
        reservas = await conn.fetch("""
            SELECT * FROM prod_inventario_reservas
            WHERE registro_id = $1
            ORDER BY fecha DESC
        """, registro_id)
        
        result = []
        for res in reservas:
            d = row_to_dict(res)
            
            # Obtener líneas de la reserva
            lineas = await conn.fetch("""
                SELECT rl.*, i.codigo as item_codigo, i.nombre as item_nombre,
                       i.unidad_medida as item_unidad, tc.nombre as talla_nombre
                FROM prod_inventario_reservas_linea rl
                JOIN prod_inventario i ON rl.item_id = i.id
                LEFT JOIN prod_tallas_catalogo tc ON rl.talla_id = tc.id
                WHERE rl.reserva_id = $1
            """, res['id'])
            
            d['lineas'] = []
            for lin in lineas:
                ld = row_to_dict(lin)
                ld['cantidad_activa'] = float(ld['cantidad_reservada']) - float(ld['cantidad_liberada'])
                d['lineas'].append(ld)
            
            result.append(d)
        
        return {"registro_id": registro_id, "reservas": result}


@api_router.delete("/reservas/{reserva_id}")
async def anular_reserva(reserva_id: str):
    """Anula una reserva completa, liberando todo el stock reservado."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        reserva = await conn.fetchrow("SELECT * FROM prod_inventario_reservas WHERE id = $1", reserva_id)
        if not reserva:
            raise HTTPException(status_code=404, detail="Reserva no encontrada")
        if reserva['estado'] != 'ACTIVA':
            raise HTTPException(status_code=400, detail=f"La reserva ya está {reserva['estado']}")
        
        registro_id = reserva['registro_id']
        
        # Obtener líneas activas de la reserva
        lineas = await conn.fetch("""
            SELECT * FROM prod_inventario_reservas_linea WHERE reserva_id = $1
        """, reserva_id)
        
        # Liberar cada línea y actualizar requerimiento
        for lin in lineas:
            cantidad_activa = float(lin['cantidad_reservada']) - float(lin['cantidad_liberada'])
            if cantidad_activa > 0:
                # Marcar como liberada
                await conn.execute("""
                    UPDATE prod_inventario_reservas_linea
                    SET cantidad_liberada = cantidad_reservada, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                """, lin['id'])
                
                # Devolver al requerimiento
                if lin['talla_id']:
                    await conn.execute("""
                        UPDATE prod_registro_requerimiento_mp
                        SET cantidad_reservada = GREATEST(0, cantidad_reservada - $1), updated_at = CURRENT_TIMESTAMP
                        WHERE registro_id = $2 AND item_id = $3 AND talla_id = $4
                    """, cantidad_activa, registro_id, lin['item_id'], lin['talla_id'])
                else:
                    await conn.execute("""
                        UPDATE prod_registro_requerimiento_mp
                        SET cantidad_reservada = GREATEST(0, cantidad_reservada - $1), updated_at = CURRENT_TIMESTAMP
                        WHERE registro_id = $2 AND item_id = $3 AND talla_id IS NULL
                    """, cantidad_activa, registro_id, lin['item_id'])
        
        # Marcar reserva como anulada
        await conn.execute("""
            UPDATE prod_inventario_reservas SET estado = 'ANULADA', updated_at = CURRENT_TIMESTAMP WHERE id = $1
        """, reserva_id)
        
        return {"message": "Reserva anulada", "reserva_id": reserva_id, "lineas_liberadas": len(lineas)}



@api_router.post("/registros/{registro_id}/liberar-reservas")
async def liberar_reservas(registro_id: str, input: LiberarReservaInput):
    """Libera parcial o totalmente reservas de un registro"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # FASE 2C: Validar que OP no esté cerrada/anulada (la liberación manual es bloqueada, la automática usa otra función)
        if registro['estado'] in ('CERRADA', 'ANULADA'):
            raise HTTPException(
                status_code=400, 
                detail=f"OP {registro['estado'].lower()}: las reservas ya fueron liberadas automáticamente al cerrar/anular"
            )
        
        if not input.lineas:
            raise HTTPException(status_code=400, detail="Debe incluir al menos una línea a liberar")
        
        liberadas = []
        for linea in input.lineas:
            # Buscar líneas de reserva activas para este item/talla
            if linea.talla_id:
                reserva_lineas = await conn.fetch("""
                    SELECT rl.* FROM prod_inventario_reservas_linea rl
                    JOIN prod_inventario_reservas r ON rl.reserva_id = r.id
                    WHERE r.registro_id = $1 AND r.estado = 'ACTIVA'
                      AND rl.item_id = $2 AND rl.talla_id = $3
                      AND (rl.cantidad_reservada - rl.cantidad_liberada) > 0
                """, registro_id, linea.item_id, linea.talla_id)
            else:
                reserva_lineas = await conn.fetch("""
                    SELECT rl.* FROM prod_inventario_reservas_linea rl
                    JOIN prod_inventario_reservas r ON rl.reserva_id = r.id
                    WHERE r.registro_id = $1 AND r.estado = 'ACTIVA'
                      AND rl.item_id = $2 AND rl.talla_id IS NULL
                      AND (rl.cantidad_reservada - rl.cantidad_liberada) > 0
                """, registro_id, linea.item_id)
            
            cantidad_a_liberar = linea.cantidad
            for rl in reserva_lineas:
                if cantidad_a_liberar <= 0:
                    break
                
                activa = float(rl['cantidad_reservada']) - float(rl['cantidad_liberada'])
                liberar = min(activa, cantidad_a_liberar)
                
                await conn.execute("""
                    UPDATE prod_inventario_reservas_linea
                    SET cantidad_liberada = cantidad_liberada + $1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                """, liberar, rl['id'])
                
                cantidad_a_liberar -= liberar
            
            # Actualizar requerimiento: bajar cantidad_reservada
            if linea.talla_id:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_reservada = GREATEST(0, cantidad_reservada - $1), updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id = $4
                """, linea.cantidad, registro_id, linea.item_id, linea.talla_id)
            else:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_reservada = GREATEST(0, cantidad_reservada - $1), updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id IS NULL
                """, linea.cantidad, registro_id, linea.item_id)
            
            liberadas.append({
                "item_id": linea.item_id,
                "talla_id": linea.talla_id,
                "cantidad_liberada": linea.cantidad
            })
        
        # Recalcular estados
        await conn.execute("""
            UPDATE prod_registro_requerimiento_mp
            SET estado = CASE
                WHEN cantidad_consumida >= cantidad_requerida THEN 'COMPLETO'
                WHEN cantidad_reservada > 0 OR cantidad_consumida > 0 THEN 'PARCIAL'
                ELSE 'PENDIENTE'
            END
            WHERE registro_id = $1
        """, registro_id)
        
        return {"message": "Reservas liberadas", "liberadas": liberadas}


# ==================== FASE 2C: CIERRE/ANULACIÓN OP ====================

async def liberar_reservas_pendientes_auto(conn, registro_id: str):
    """
    Libera automáticamente todas las reservas pendientes de un registro.
    Usado al cerrar o anular una OP.
    Retorna resumen de liberaciones.
    """
    items_liberados = []
    total_liberado = 0.0
    
    # Obtener todas las reservas activas del registro
    reservas = await conn.fetch("""
        SELECT id FROM prod_inventario_reservas
        WHERE registro_id = $1 AND estado = 'ACTIVA'
    """, registro_id)
    
    for reserva in reservas:
        # Obtener líneas con cantidad pendiente
        lineas = await conn.fetch("""
            SELECT rl.*, i.nombre as item_nombre
            FROM prod_inventario_reservas_linea rl
            JOIN prod_inventario i ON rl.item_id = i.id
            WHERE rl.reserva_id = $1 
              AND (rl.cantidad_reservada - rl.cantidad_liberada) > 0
        """, reserva['id'])
        
        for linea in lineas:
            liberable = float(linea['cantidad_reservada']) - float(linea['cantidad_liberada'])
            if liberable <= 0:
                continue
            
            # Actualizar línea de reserva: marcar como liberada
            await conn.execute("""
                UPDATE prod_inventario_reservas_linea
                SET cantidad_liberada = cantidad_reservada, updated_at = CURRENT_TIMESTAMP
                WHERE id = $1
            """, linea['id'])
            
            # Actualizar requerimiento: bajar cantidad_reservada
            if linea['talla_id']:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_reservada = GREATEST(0, cantidad_reservada - $1), updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id = $4
                """, liberable, registro_id, linea['item_id'], linea['talla_id'])
            else:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_reservada = GREATEST(0, cantidad_reservada - $1), updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id IS NULL
                """, liberable, registro_id, linea['item_id'])
            
            items_liberados.append({
                "item_id": linea['item_id'],
                "item_nombre": linea['item_nombre'],
                "talla_id": linea['talla_id'],
                "cantidad": liberable
            })
            total_liberado += liberable
        
        # Marcar cabecera de reserva como CERRADA
        await conn.execute("""
            UPDATE prod_inventario_reservas
            SET estado = 'CERRADA', updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """, reserva['id'])
    
    # Recalcular estados de requerimiento
    await conn.execute("""
        UPDATE prod_registro_requerimiento_mp
        SET estado = CASE
            WHEN cantidad_consumida >= cantidad_requerida AND cantidad_requerida > 0 THEN 'COMPLETO'
            WHEN cantidad_reservada > 0 OR cantidad_consumida > 0 THEN 'PARCIAL'
            ELSE 'PENDIENTE'
        END
        WHERE registro_id = $1
    """, registro_id)
    
    return {
        "total_liberado": total_liberado,
        "items_liberados": items_liberados
    }


@api_router.post("/registros/{registro_id}/cerrar")
async def cerrar_registro(registro_id: str):
    """
    Cierra una OP (Orden de Producción).
    - Cambia estado a CERRADA
    - Libera automáticamente todas las reservas pendientes
    - No revierte salidas ya realizadas
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Validar registro
            registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
            if not registro:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            
            estado_actual = registro['estado']
            if estado_actual == 'ANULADA':
                raise HTTPException(status_code=400, detail="No se puede cerrar una OP que ya está ANULADA")
            
            if estado_actual == 'CERRADA':
                raise HTTPException(status_code=400, detail="La OP ya está CERRADA")
            
            # Cambiar estado a CERRADA
            await conn.execute("""
                UPDATE prod_registros 
                SET estado = 'CERRADA'
                WHERE id = $1
            """, registro_id)
            
            # Liberar reservas pendientes automáticamente
            liberacion = await liberar_reservas_pendientes_auto(conn, registro_id)
            
            return {
                "message": "OP cerrada correctamente",
                "estado_nuevo": "CERRADA",
                "estado_anterior": estado_actual,
                "reservas_liberadas_total": liberacion["total_liberado"],
                "items_liberados": liberacion["items_liberados"]
            }


@api_router.post("/registros/{registro_id}/anular")
async def anular_registro(registro_id: str):
    """
    Anula una OP (Orden de Producción).
    - Cambia estado a ANULADA
    - Libera automáticamente TODAS las reservas pendientes
    - NO revierte salidas ya realizadas (mantiene trazabilidad FIFO)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            # Validar registro
            registro = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
            if not registro:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            
            estado_actual = registro['estado']
            if estado_actual == 'ANULADA':
                raise HTTPException(status_code=400, detail="La OP ya está ANULADA")
            
            # Cambiar estado a ANULADA
            await conn.execute("""
                UPDATE prod_registros 
                SET estado = 'ANULADA'
                WHERE id = $1
            """, registro_id)
            
            # Liberar reservas pendientes automáticamente
            liberacion = await liberar_reservas_pendientes_auto(conn, registro_id)
            
            # Obtener info de salidas ya realizadas (para trazabilidad)
            salidas_realizadas = await conn.fetchval("""
                SELECT COUNT(*) FROM prod_inventario_salidas WHERE registro_id = $1
            """, registro_id)
            
            return {
                "message": "OP anulada correctamente",
                "estado_nuevo": "ANULADA",
                "estado_anterior": estado_actual,
                "reservas_liberadas_total": liberacion["total_liberado"],
                "items_liberados": liberacion["items_liberados"],
                "salidas_no_revertidas": salidas_realizadas,
                "nota": "Las salidas de inventario ya realizadas NO se revierten para mantener trazabilidad FIFO"
            }


@api_router.get("/registros/{registro_id}/resumen")
async def get_resumen_registro(registro_id: str):
    """
    Devuelve un resumen completo de la OP:
    - Total de prendas (sum tallas)
    - Requerimiento: requerida/reservada/consumida/pendiente por item/talla
    - Reservas: estado y detalle
    - Salidas: total consumido por item/talla, detalle por rollo si aplica
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Validar registro
        registro = await conn.fetchrow("""
            SELECT r.*, m.nombre as modelo_nombre
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            WHERE r.id = $1
        """, registro_id)
        if not registro:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Total de prendas (sum de tallas)
        total_prendas = await conn.fetchval("""
            SELECT COALESCE(SUM(cantidad_real), 0) FROM prod_registro_tallas WHERE registro_id = $1
        """, registro_id)
        
        # Detalle de tallas
        tallas = await conn.fetch("""
            SELECT rt.*, tc.nombre as talla_nombre
            FROM prod_registro_tallas rt
            LEFT JOIN prod_tallas_catalogo tc ON rt.talla_id = tc.id
            WHERE rt.registro_id = $1
            ORDER BY tc.orden
        """, registro_id)
        
        # Requerimiento de MP
        requerimiento = await conn.fetch("""
            SELECT req.*, 
                   i.codigo as item_codigo, i.nombre as item_nombre, i.unidad_medida,
                   tc.nombre as talla_nombre,
                   GREATEST(0, req.cantidad_requerida - req.cantidad_consumida) as pendiente_consumir,
                   GREATEST(0, req.cantidad_reservada - req.cantidad_consumida) as reserva_disponible
            FROM prod_registro_requerimiento_mp req
            JOIN prod_inventario i ON req.item_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON req.talla_id = tc.id
            WHERE req.registro_id = $1
            ORDER BY i.nombre, tc.orden
        """, registro_id)
        
        # Reservas
        reservas_raw = await conn.fetch("""
            SELECT res.id, res.estado as reserva_estado, res.fecha as reserva_fecha,
                   rl.item_id, rl.talla_id, rl.cantidad_reservada, rl.cantidad_liberada,
                   i.nombre as item_nombre, tc.nombre as talla_nombre
            FROM prod_inventario_reservas res
            JOIN prod_inventario_reservas_linea rl ON rl.reserva_id = res.id
            JOIN prod_inventario i ON rl.item_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON rl.talla_id = tc.id
            WHERE res.registro_id = $1
            ORDER BY res.fecha DESC
        """, registro_id)
        
        # Agrupar reservas
        reservas_totales = {
            "total_reservado": 0,
            "total_liberado": 0,
            "activas": 0,
            "cerradas": 0,
            "detalle": []
        }
        for r in reservas_raw:
            reservas_totales["total_reservado"] += float(r['cantidad_reservada'])
            reservas_totales["total_liberado"] += float(r['cantidad_liberada'])
            if r['reserva_estado'] == 'ACTIVA':
                reservas_totales["activas"] += 1
            else:
                reservas_totales["cerradas"] += 1
            reservas_totales["detalle"].append({
                "item_id": r['item_id'],
                "item_nombre": r['item_nombre'],
                "talla_id": r['talla_id'],
                "talla_nombre": r['talla_nombre'],
                "cantidad_reservada": float(r['cantidad_reservada']),
                "cantidad_liberada": float(r['cantidad_liberada']),
                "pendiente": float(r['cantidad_reservada']) - float(r['cantidad_liberada']),
                "reserva_estado": r['reserva_estado']
            })
        
        # Salidas
        salidas = await conn.fetch("""
            SELECT s.*, 
                   i.codigo as item_codigo, i.nombre as item_nombre, i.control_por_rollos,
                   tc.nombre as talla_nombre,
                   ro.numero_rollo, ro.tono
            FROM prod_inventario_salidas s
            JOIN prod_inventario i ON s.item_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON s.talla_id = tc.id
            LEFT JOIN prod_inventario_rollos ro ON s.rollo_id = ro.id
            WHERE s.registro_id = $1
            ORDER BY s.fecha DESC
        """, registro_id)
        
        # Agrupar salidas por item/talla
        salidas_por_item = {}
        for s in salidas:
            key = f"{s['item_id']}_{s['talla_id'] or 'null'}"
            if key not in salidas_por_item:
                salidas_por_item[key] = {
                    "item_id": s['item_id'],
                    "item_nombre": s['item_nombre'],
                    "talla_id": s['talla_id'],
                    "talla_nombre": s['talla_nombre'],
                    "total_consumido": 0,
                    "costo_total": 0,
                    "detalle_salidas": []
                }
            salidas_por_item[key]["total_consumido"] += float(s['cantidad'])
            salidas_por_item[key]["costo_total"] += float(s['costo_total']) if s['costo_total'] else 0
            salidas_por_item[key]["detalle_salidas"].append({
                "id": s['id'],
                "cantidad": float(s['cantidad']),
                "costo_total": float(s['costo_total']) if s['costo_total'] else 0,
                "fecha": s['fecha'].isoformat() if s['fecha'] else None,
                "rollo_id": s['rollo_id'],
                "numero_rollo": s['numero_rollo'],
                "tono": s['tono']
            })
        
        return {
            "registro": {
                "id": registro['id'],
                "n_corte": registro['n_corte'],
                "estado": registro['estado'],
                "modelo_nombre": registro['modelo_nombre'],
                "fecha_creacion": registro['fecha_creacion'].isoformat() if registro['fecha_creacion'] else None,
                "urgente": registro['urgente']
            },
            "total_prendas": int(total_prendas or 0),
            "tallas": [
                {
                    "talla_id": t['talla_id'],
                    "talla_nombre": t['talla_nombre'],
                    "cantidad": int(t['cantidad_real']) if t['cantidad_real'] else 0
                }
                for t in tallas
            ],
            "requerimiento": [
                {
                    "id": r['id'],
                    "item_id": r['item_id'],
                    "item_codigo": r['item_codigo'],
                    "item_nombre": r['item_nombre'],
                    "unidad_medida": r['unidad_medida'],
                    "talla_id": r['talla_id'],
                    "talla_nombre": r['talla_nombre'],
                    "cantidad_requerida": float(r['cantidad_requerida']),
                    "cantidad_reservada": float(r['cantidad_reservada']),
                    "cantidad_consumida": float(r['cantidad_consumida']),
                    "pendiente_consumir": float(r['pendiente_consumir']),
                    "reserva_disponible": float(r['reserva_disponible']),
                    "estado": r['estado']
                }
                for r in requerimiento
            ],
            "reservas": reservas_totales,
            "salidas": {
                "total_salidas": len(salidas),
                "costo_total": sum(float(s['costo_total'] or 0) for s in salidas),
                "por_item": list(salidas_por_item.values())
            }
        }


# ==================== ENDPOINTS INVENTARIO ====================

CATEGORIAS_INVENTARIO = ["Telas", "Avios", "Otros"]

# ==================== ENDPOINTS MOVIMIENTOS PRODUCCION ====================

@api_router.get("/movimientos-produccion")
async def get_movimientos(
    registro_id: str = None,
    servicio_id: str = None,
    persona_id: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    search: str = "",
    limit: int = 50,
    offset: int = 0,
    all: str = "",
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        conditions = []
        params = []
        param_idx = 1

        if registro_id:
            conditions.append(f"mp.registro_id = ${param_idx}")
            params.append(registro_id)
            param_idx += 1
        if servicio_id:
            conditions.append(f"mp.servicio_id = ${param_idx}")
            params.append(servicio_id)
            param_idx += 1
        if persona_id:
            conditions.append(f"mp.persona_id = ${param_idx}")
            params.append(persona_id)
            param_idx += 1
        if fecha_desde:
            conditions.append(f"mp.fecha_inicio >= ${param_idx}::date")
            params.append(fecha_desde)
            param_idx += 1
        if fecha_hasta:
            conditions.append(f"mp.fecha_inicio <= ${param_idx}::date")
            params.append(fecha_hasta)
            param_idx += 1
        if search:
            conditions.append(f"(r.n_corte ILIKE ${param_idx} OR s.nombre ILIKE ${param_idx} OR p.nombre ILIKE ${param_idx})")
            params.append(f"%{search}%")
            param_idx += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        base_from = """
            FROM prod_movimientos_produccion mp
            LEFT JOIN prod_servicios_produccion s ON mp.servicio_id = s.id
            LEFT JOIN prod_personas_produccion p ON mp.persona_id = p.id
            LEFT JOIN prod_registros r ON mp.registro_id = r.id
        """

        # Count total
        count_row = await conn.fetchrow(f"SELECT COUNT(*) as total {base_from} WHERE {where_clause}", *params)
        total = count_row['total']

        # Build query with JOINs (eliminates N+1)
        query = f"""
            SELECT mp.*,
                s.nombre as servicio_nombre,
                p.nombre as persona_nombre,
                p.tipo_persona as persona_tipo,
                p.unidad_interna_id as persona_unidad_interna_id,
                r.n_corte as registro_n_corte
            {base_from}
            WHERE {where_clause}
            ORDER BY mp.created_at DESC
        """

        if all != "true":
            query += f" LIMIT ${param_idx} OFFSET ${param_idx + 1}"
            params.extend([limit, offset])

        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            d = row_to_dict(r)
            if d.get('fecha_inicio'):
                d['fecha_inicio'] = str(d['fecha_inicio'])
            if d.get('fecha_fin'):
                d['fecha_fin'] = str(d['fecha_fin'])
            if d.get('fecha_esperada_movimiento'):
                d['fecha_esperada_movimiento'] = str(d['fecha_esperada_movimiento'])
            result.append(d)

        if all == "true":
            return result
        return {"items": result, "total": total, "limit": limit, "offset": offset}

@api_router.post("/movimientos-produccion")
async def create_movimiento(input: MovimientoCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("SELECT id FROM prod_registros WHERE id = $1", input.registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        # Bloqueo por paralización activa
        par_activa = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_paralizacion WHERE registro_id = $1 AND activa = TRUE", input.registro_id
        )
        if par_activa and par_activa > 0:
            raise HTTPException(status_code=400, detail="Registro PARALIZADO. Resuelve la incidencia antes de crear movimientos.")
        srv = await conn.fetchrow("SELECT id FROM prod_servicios_produccion WHERE id = $1", input.servicio_id)
        if not srv:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        per = await conn.fetchrow("SELECT servicios FROM prod_personas_produccion WHERE id = $1", input.persona_id)
        if not per:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        
        # Usar tarifa_aplicada del frontend si viene, sino calcular desde persona-servicio
        tarifa = input.tarifa_aplicada or 0
        if not tarifa:
            servicios = parse_jsonb(per['servicios'])
            for s in servicios:
                sid = s if isinstance(s, str) else s.get('servicio_id')
                if sid == input.servicio_id:
                    tarifa = s.get('tarifa', 0) if isinstance(s, dict) else 0
                    break
        
        diferencia = input.cantidad_enviada - input.cantidad_recibida
        costo_calculado = input.cantidad_recibida * tarifa
        
        movimiento = Movimiento(**input.model_dump())
        movimiento.diferencia = diferencia
        movimiento.costo_calculado = costo_calculado
        
        fecha_inicio = None
        fecha_fin = None
        if input.fecha_inicio:
            try:
                fecha_inicio = datetime.strptime(input.fecha_inicio, '%Y-%m-%d').date()
            except:
                pass
        if input.fecha_fin:
            try:
                fecha_fin = datetime.strptime(input.fecha_fin, '%Y-%m-%d').date()
            except:
                pass
        
        fecha_esperada = None
        if input.fecha_esperada_movimiento:
            try:
                fecha_esperada = datetime.strptime(input.fecha_esperada_movimiento, '%Y-%m-%d').date()
            except:
                pass
        
        await conn.execute(
            """INSERT INTO prod_movimientos_produccion (id, registro_id, servicio_id, persona_id, cantidad_enviada, cantidad_recibida, diferencia, costo_calculado, tarifa_aplicada, fecha_inicio, fecha_fin, fecha_esperada_movimiento, responsable_movimiento, observaciones, avance_porcentaje, avance_updated_at, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)""",
            movimiento.id, movimiento.registro_id, movimiento.servicio_id, movimiento.persona_id,
            movimiento.cantidad_enviada, movimiento.cantidad_recibida, diferencia, costo_calculado,
            tarifa, fecha_inicio, fecha_fin, fecha_esperada, input.responsable_movimiento or None,
            movimiento.observaciones, input.avance_porcentaje,
            datetime.now() if input.avance_porcentaje is not None else None,
            movimiento.created_at.replace(tzinfo=None)
        )
        
        # Crear merma si hay diferencia
        if diferencia > 0:
            merma_id = str(uuid.uuid4())
            await conn.execute(
                """INSERT INTO prod_mermas (id, registro_id, movimiento_id, servicio_id, persona_id, cantidad, motivo, fecha)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
                merma_id, input.registro_id, movimiento.id, input.servicio_id, input.persona_id,
                diferencia, "Diferencia automática", datetime.now()
            )
        
        return movimiento

@api_router.put("/movimientos-produccion/{movimiento_id}")
async def update_movimiento(movimiento_id: str, input: MovimientoCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_movimientos_produccion WHERE id = $1", movimiento_id)
        if not result:
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        # Bloqueo por paralización activa
        par_activa = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_paralizacion WHERE registro_id = $1 AND activa = TRUE", input.registro_id
        )
        if par_activa and par_activa > 0:
            raise HTTPException(status_code=400, detail="Registro PARALIZADO. Resuelve la incidencia antes de editar movimientos.")
        
        # Usar tarifa_aplicada del frontend si viene, sino calcular desde persona-servicio
        tarifa = input.tarifa_aplicada or 0
        if not tarifa:
            per = await conn.fetchrow("SELECT servicios FROM prod_personas_produccion WHERE id = $1", input.persona_id)
            servicios = parse_jsonb(per['servicios']) if per else []
            for s in servicios:
                sid = s if isinstance(s, str) else s.get('servicio_id')
                if sid == input.servicio_id:
                    tarifa = s.get('tarifa', 0) if isinstance(s, dict) else 0
                    break
        
        diferencia = input.cantidad_enviada - input.cantidad_recibida
        costo_calculado = input.cantidad_recibida * tarifa
        
        # Eliminar mermas anteriores
        await conn.execute("DELETE FROM prod_mermas WHERE movimiento_id = $1", movimiento_id)
        
        fecha_inicio = None
        fecha_fin = None
        if input.fecha_inicio:
            try:
                fecha_inicio = datetime.strptime(input.fecha_inicio, '%Y-%m-%d').date()
            except:
                pass
        if input.fecha_fin:
            try:
                fecha_fin = datetime.strptime(input.fecha_fin, '%Y-%m-%d').date()
            except:
                pass
        
        fecha_esperada = None
        if input.fecha_esperada_movimiento:
            try:
                fecha_esperada = datetime.strptime(input.fecha_esperada_movimiento, '%Y-%m-%d').date()
            except:
                pass
        
        await conn.execute(
            """UPDATE prod_movimientos_produccion SET registro_id=$1, servicio_id=$2, persona_id=$3, cantidad_enviada=$4, cantidad_recibida=$5, diferencia=$6, costo_calculado=$7, tarifa_aplicada=$8, fecha_inicio=$9, fecha_fin=$10, fecha_esperada_movimiento=$11, responsable_movimiento=$12, observaciones=$13, avance_porcentaje=$14, avance_updated_at=CASE WHEN $14 IS DISTINCT FROM avance_porcentaje THEN NOW() ELSE avance_updated_at END WHERE id=$15""",
            input.registro_id, input.servicio_id, input.persona_id, input.cantidad_enviada, input.cantidad_recibida,
            diferencia, costo_calculado, tarifa, fecha_inicio, fecha_fin, fecha_esperada, input.responsable_movimiento or None, input.observaciones, input.avance_porcentaje, movimiento_id
        )
        
        # Crear nueva merma si hay diferencia
        if diferencia > 0:
            merma_id = str(uuid.uuid4())
            await conn.execute(
                """INSERT INTO prod_mermas (id, registro_id, movimiento_id, servicio_id, persona_id, cantidad, motivo, fecha)
                   VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
                merma_id, input.registro_id, movimiento_id, input.servicio_id, input.persona_id,
                diferencia, "Diferencia automática", datetime.now()
            )
        
        return {**row_to_dict(result), **input.model_dump(), "diferencia": diferencia, "costo_calculado": costo_calculado, "tarifa_aplicada": tarifa}

@api_router.delete("/movimientos-produccion/{movimiento_id}")
async def delete_movimiento(movimiento_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_mermas WHERE movimiento_id = $1", movimiento_id)
        await conn.execute("DELETE FROM prod_movimientos_produccion WHERE id = $1", movimiento_id)
        return {"message": "Movimiento eliminado"}

# ==================== ENDPOINTS MERMAS ====================

@api_router.get("/mermas")
async def get_mermas(registro_id: str = None, servicio_id: str = None, persona_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM prod_mermas WHERE 1=1"
        params = []
        if registro_id:
            params.append(registro_id)
            query += f" AND registro_id = ${len(params)}"
        if servicio_id:
            params.append(servicio_id)
            query += f" AND servicio_id = ${len(params)}"
        if persona_id:
            params.append(persona_id)
            query += f" AND persona_id = ${len(params)}"
        query += " ORDER BY fecha DESC"
        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            d = row_to_dict(r)
            srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", d.get('servicio_id'))
            per = await conn.fetchrow("SELECT nombre FROM prod_personas_produccion WHERE id = $1", d.get('persona_id'))
            reg = await conn.fetchrow("SELECT n_corte FROM prod_registros WHERE id = $1", d.get('registro_id'))
            d['servicio_nombre'] = srv['nombre'] if srv else None
            d['persona_nombre'] = per['nombre'] if per else None
            d['registro_n_corte'] = reg['n_corte'] if reg else None
            result.append(d)
        return result

@api_router.post("/mermas")
async def create_merma(input: MermaCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        merma = Merma(**input.model_dump())
        await conn.execute(
            """INSERT INTO prod_mermas (id, registro_id, movimiento_id, servicio_id, persona_id, cantidad, motivo, fecha)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8)""",
            merma.id, merma.registro_id, merma.movimiento_id, merma.servicio_id, merma.persona_id,
            merma.cantidad, merma.motivo, merma.fecha.replace(tzinfo=None)
        )
        return merma

@api_router.put("/mermas/{merma_id}")
async def update_merma(merma_id: str, input: MermaCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_mermas WHERE id = $1", merma_id)
        if not result:
            raise HTTPException(status_code=404, detail="Merma no encontrada")
        await conn.execute(
            """UPDATE prod_mermas SET registro_id=$1, movimiento_id=$2, servicio_id=$3, persona_id=$4, cantidad=$5, motivo=$6 WHERE id=$7""",
            input.registro_id, input.movimiento_id, input.servicio_id, input.persona_id, input.cantidad, input.motivo, merma_id
        )
        return {**row_to_dict(result), **input.model_dump()}

@api_router.delete("/mermas/{merma_id}")
async def delete_merma(merma_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_mermas WHERE id = $1", merma_id)
        return {"message": "Merma eliminada"}

# ==================== ENDPOINTS GUIAS REMISION ====================

@api_router.get("/guias-remision")
async def get_guias_remision(registro_id: str = None, persona_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM prod_guias_remision WHERE 1=1"
        params = []
        if registro_id:
            params.append(registro_id)
            query += f" AND registro_id = ${len(params)}"
        if persona_id:
            params.append(persona_id)
            query += f" AND persona_id = ${len(params)}"
        query += " ORDER BY fecha DESC"
        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            d = row_to_dict(r)
            srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", d.get('servicio_id'))
            per = await conn.fetchrow("SELECT nombre, telefono, direccion FROM prod_personas_produccion WHERE id = $1", d.get('persona_id'))
            reg = await conn.fetchrow("SELECT n_corte, modelo_id FROM prod_registros WHERE id = $1", d.get('registro_id'))
            d['servicio_nombre'] = srv['nombre'] if srv else None
            d['persona_nombre'] = per['nombre'] if per else None
            d['persona_telefono'] = per['telefono'] if per else None
            d['persona_direccion'] = per['direccion'] if per else None
            d['registro_n_corte'] = reg['n_corte'] if reg else None
            if reg and reg['modelo_id']:
                modelo = await conn.fetchrow("SELECT nombre FROM prod_modelos WHERE id = $1", reg['modelo_id'])
                d['modelo_nombre'] = modelo['nombre'] if modelo else None
            result.append(d)
        return result

@api_router.get("/guias-remision/{guia_id}")
async def get_guia_remision(guia_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        guia = await conn.fetchrow("SELECT * FROM prod_guias_remision WHERE id = $1", guia_id)
        if not guia:
            raise HTTPException(status_code=404, detail="Guía no encontrada")
        d = row_to_dict(guia)
        srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", d.get('servicio_id'))
        per = await conn.fetchrow("SELECT * FROM prod_personas_produccion WHERE id = $1", d.get('persona_id'))
        reg = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", d.get('registro_id'))
        d['servicio_nombre'] = srv['nombre'] if srv else None
        if per:
            d['persona_nombre'] = per['nombre']
            d['persona_telefono'] = per['telefono']
            d['persona_direccion'] = per['direccion']
        if reg:
            d['registro_n_corte'] = reg['n_corte']
            d['tallas'] = parse_jsonb(reg['tallas'])
            d['distribucion_colores'] = parse_jsonb(reg['distribucion_colores'])
            if reg['modelo_id']:
                modelo = await conn.fetchrow("SELECT nombre FROM prod_modelos WHERE id = $1", reg['modelo_id'])
                d['modelo_nombre'] = modelo['nombre'] if modelo else None
        return d

@api_router.post("/guias-remision")
async def create_guia_remision(input: GuiaRemisionCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        guia = GuiaRemision(**input.model_dump())
        # Generar número de guía
        ultima = await conn.fetchrow("SELECT numero_guia FROM prod_guias_remision WHERE numero_guia != '' ORDER BY numero_guia DESC LIMIT 1")
        if ultima and ultima['numero_guia']:
            try:
                num = int(ultima['numero_guia'].replace('GR-', '')) + 1
            except:
                num = 1
        else:
            num = 1
        guia.numero_guia = f"GR-{num:06d}"
        
        await conn.execute(
            """INSERT INTO prod_guias_remision (id, numero_guia, movimiento_id, registro_id, servicio_id, persona_id, cantidad, observaciones, fecha)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
            guia.id, guia.numero_guia, guia.movimiento_id, guia.registro_id, guia.servicio_id,
            guia.persona_id, guia.cantidad, guia.observaciones, guia.fecha.replace(tzinfo=None)
        )
        return guia

@api_router.post("/guias-remision/from-movimiento/{movimiento_id}")
async def create_guia_from_movimiento(movimiento_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        mov = await conn.fetchrow("SELECT * FROM prod_movimientos_produccion WHERE id = $1", movimiento_id)
        if not mov:
            raise HTTPException(status_code=404, detail="Movimiento no encontrado")
        
        # Ver si ya existe guía para este movimiento
        guia_existente = await conn.fetchrow("SELECT * FROM prod_guias_remision WHERE movimiento_id = $1", movimiento_id)
        
        if guia_existente:
            # Actualizar guía existente
            await conn.execute(
                """UPDATE prod_guias_remision SET servicio_id=$1, persona_id=$2, cantidad=$3, fecha=$4 WHERE id=$5""",
                mov['servicio_id'], mov['persona_id'], mov['cantidad_enviada'], datetime.now(), guia_existente['id']
            )
            updated = await conn.fetchrow("SELECT * FROM prod_guias_remision WHERE id = $1", guia_existente['id'])
            updated_dict = row_to_dict(updated)
            # Enriquecer con nombres
            srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", updated_dict.get('servicio_id'))
            per = await conn.fetchrow("SELECT nombre, telefono, direccion FROM prod_personas_produccion WHERE id = $1", updated_dict.get('persona_id'))
            reg = await conn.fetchrow("SELECT n_corte, modelo_id FROM prod_registros WHERE id = $1", updated_dict.get('registro_id'))
            updated_dict['servicio_nombre'] = srv['nombre'] if srv else None
            updated_dict['persona_nombre'] = per['nombre'] if per else None
            updated_dict['persona_telefono'] = per['telefono'] if per else None
            updated_dict['persona_direccion'] = per['direccion'] if per else None
            updated_dict['registro_n_corte'] = reg['n_corte'] if reg else None
            if reg and reg['modelo_id']:
                modelo = await conn.fetchrow("SELECT nombre FROM prod_modelos WHERE id = $1", reg['modelo_id'])
                updated_dict['modelo_nombre'] = modelo['nombre'] if modelo else None
            return {"message": "Guía actualizada", "guia": updated_dict, "updated": True}
        
        # Crear nueva guía
        guia_id = str(uuid.uuid4())
        ultima = await conn.fetchrow("SELECT numero_guia FROM prod_guias_remision WHERE numero_guia != '' ORDER BY numero_guia DESC LIMIT 1")
        if ultima and ultima['numero_guia']:
            try:
                num = int(ultima['numero_guia'].replace('GR-', '')) + 1
            except:
                num = 1
        else:
            num = 1
        numero_guia = f"GR-{num:06d}"
        
        await conn.execute(
            """INSERT INTO prod_guias_remision (id, numero_guia, movimiento_id, registro_id, servicio_id, persona_id, cantidad, observaciones, fecha)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
            guia_id, numero_guia, movimiento_id, mov['registro_id'], mov['servicio_id'],
            mov['persona_id'], mov['cantidad_enviada'], "", datetime.now()
        )
        guia = await conn.fetchrow("SELECT * FROM prod_guias_remision WHERE id = $1", guia_id)
        guia_dict = row_to_dict(guia)
        # Enriquecer con nombres
        srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", guia_dict.get('servicio_id'))
        per = await conn.fetchrow("SELECT nombre, telefono, direccion FROM prod_personas_produccion WHERE id = $1", guia_dict.get('persona_id'))
        reg = await conn.fetchrow("SELECT n_corte, modelo_id FROM prod_registros WHERE id = $1", guia_dict.get('registro_id'))
        guia_dict['servicio_nombre'] = srv['nombre'] if srv else None
        guia_dict['persona_nombre'] = per['nombre'] if per else None
        guia_dict['persona_telefono'] = per['telefono'] if per else None
        guia_dict['persona_direccion'] = per['direccion'] if per else None
        guia_dict['registro_n_corte'] = reg['n_corte'] if reg else None
        if reg and reg['modelo_id']:
            modelo = await conn.fetchrow("SELECT nombre FROM prod_modelos WHERE id = $1", reg['modelo_id'])
            guia_dict['modelo_nombre'] = modelo['nombre'] if modelo else None
        return {"message": "Guía creada", "guia": guia_dict, "updated": False}

@api_router.delete("/guias-remision/{guia_id}")
async def delete_guia_remision(guia_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_guias_remision WHERE id = $1", guia_id)
        return {"message": "Guía eliminada"}

# ==================== ENDPOINTS ESTADISTICAS ====================

@api_router.get("/stats")
async def get_stats():
    pool = await get_pool()
    async with pool.acquire() as conn:
        marcas = await conn.fetchval("SELECT COUNT(*) FROM prod_marcas")
        tipos = await conn.fetchval("SELECT COUNT(*) FROM prod_tipos")
        entalles = await conn.fetchval("SELECT COUNT(*) FROM prod_entalles")
        telas = await conn.fetchval("SELECT COUNT(*) FROM prod_telas")
        hilos = await conn.fetchval("SELECT COUNT(*) FROM prod_hilos")
        modelos = await conn.fetchval("SELECT COUNT(*) FROM prod_modelos")
        registros = await conn.fetchval("SELECT COUNT(*) FROM prod_registros")
        registros_urgentes = await conn.fetchval("SELECT COUNT(*) FROM prod_registros WHERE urgente = true")
        tallas = await conn.fetchval("SELECT COUNT(*) FROM prod_tallas_catalogo")
        colores = await conn.fetchval("SELECT COUNT(*) FROM prod_colores_catalogo")
        inventario = await conn.fetchval("SELECT COUNT(*) FROM prod_inventario")
        ingresos = await conn.fetchval("SELECT COUNT(*) FROM prod_inventario_ingresos")
        salidas = await conn.fetchval("SELECT COUNT(*) FROM prod_inventario_salidas")
        ajustes = await conn.fetchval("SELECT COUNT(*) FROM prod_inventario_ajustes")
        
        # Alertas de stock: items con stock_minimo > 0 y stock por debajo
        stock_bajo_count = await conn.fetchval("""
            SELECT COUNT(*) FROM prod_inventario 
            WHERE stock_minimo > 0 
              AND stock_actual > 0 
              AND stock_actual <= stock_minimo 
              AND COALESCE(ignorar_alerta_stock, false) = false
        """)
        sin_stock_count = await conn.fetchval("""
            SELECT COUNT(*) FROM prod_inventario 
            WHERE stock_minimo > 0 
              AND stock_actual <= 0 
              AND COALESCE(ignorar_alerta_stock, false) = false
        """)
        
        estados_count = {}
        for estado in ESTADOS_PRODUCCION:
            count = await conn.fetchval("SELECT COUNT(*) FROM prod_registros WHERE estado = $1", estado)
            estados_count[estado] = count
        
        return {
            "marcas": marcas, "tipos": tipos, "entalles": entalles, "telas": telas, "hilos": hilos,
            "modelos": modelos, "registros": registros, "registros_urgentes": registros_urgentes,
            "tallas": tallas, "colores": colores, "inventario": inventario,
            "ingresos_count": ingresos, "salidas_count": salidas, "ajustes_count": ajustes,
            "estados_count": estados_count,
            "stock_bajo": stock_bajo_count or 0,
            "sin_stock": sin_stock_count or 0,
            "alertas_stock_total": (stock_bajo_count or 0) + (sin_stock_count or 0),
        }

@api_router.get("/stats/charts")
async def get_stats_charts():
    """Datos para gráficos del dashboard"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Registros por marca
        marcas_query = """
            SELECT COALESCE(ma.nombre, 'Sin Marca') as name, COUNT(*) as value
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            GROUP BY ma.nombre
            ORDER BY value DESC
            LIMIT 8
        """
        marcas_rows = await conn.fetch(marcas_query)
        registros_por_marca = [{"name": r["name"], "value": r["value"]} for r in marcas_rows]
        
        # Producción mensual (últimos 6 meses)
        mensual_query = """
            SELECT 
                TO_CHAR(fecha_creacion, 'Mon') as mes,
                EXTRACT(MONTH FROM fecha_creacion) as mes_num,
                COUNT(*) as registros
            FROM prod_registros
            WHERE fecha_creacion >= CURRENT_DATE - INTERVAL '6 months'
            GROUP BY TO_CHAR(fecha_creacion, 'Mon'), EXTRACT(MONTH FROM fecha_creacion)
            ORDER BY mes_num
        """
        mensual_rows = await conn.fetch(mensual_query)
        produccion_mensual = [{"mes": r["mes"], "registros": r["registros"]} for r in mensual_rows]
        
        # Registros por tipo
        tipos_query = """
            SELECT COALESCE(t.nombre, 'Sin Tipo') as name, COUNT(*) as value
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_tipos t ON m.tipo_id = t.id
            GROUP BY t.nombre
            ORDER BY value DESC
            LIMIT 8
        """
        tipos_rows = await conn.fetch(tipos_query)
        registros_por_tipo = [{"name": r["name"], "value": r["value"]} for r in tipos_rows]
        
        return {
            "registros_por_marca": registros_por_marca,
            "registros_por_tipo": registros_por_tipo,
            "produccion_mensual": produccion_mensual
        }

# ==================== REPORTE MERMAS ====================

@api_router.get("/reportes/mermas")
async def get_reporte_mermas(fecha_inicio: str = None, fecha_fin: str = None, persona_id: str = None, servicio_id: str = None):
    """Reporte de mermas por período con totales y estadísticas"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Query base con filtros
        query = """
            SELECT m.*, 
                   r.n_corte,
                   p.nombre as persona_nombre,
                   s.nombre as servicio_nombre
            FROM prod_mermas m
            LEFT JOIN prod_registros r ON m.registro_id = r.id
            LEFT JOIN prod_personas_produccion p ON m.persona_id = p.id
            LEFT JOIN prod_servicios_produccion s ON m.servicio_id = s.id
            WHERE 1=1
        """
        params = []
        
        if fecha_inicio:
            params.append(fecha_inicio)
            query += f" AND m.fecha >= ${len(params)}::date"
        if fecha_fin:
            params.append(fecha_fin)
            query += f" AND m.fecha <= ${len(params)}::date"
        if persona_id:
            params.append(persona_id)
            query += f" AND m.persona_id = ${len(params)}"
        if servicio_id:
            params.append(servicio_id)
            query += f" AND m.servicio_id = ${len(params)}"
        
        query += " ORDER BY m.fecha DESC"
        
        rows = await conn.fetch(query, *params)
        mermas = [row_to_dict(r) for r in rows]
        
        # Totales
        total_cantidad = sum(m.get('cantidad', 0) or 0 for m in mermas)
        
        # Mermas por persona
        mermas_por_persona = {}
        for m in mermas:
            persona = m.get('persona_nombre') or 'Sin asignar'
            if persona not in mermas_por_persona:
                mermas_por_persona[persona] = 0
            mermas_por_persona[persona] += m.get('cantidad', 0) or 0
        
        # Mermas por servicio
        mermas_por_servicio = {}
        for m in mermas:
            servicio = m.get('servicio_nombre') or 'Sin servicio'
            if servicio not in mermas_por_servicio:
                mermas_por_servicio[servicio] = 0
            mermas_por_servicio[servicio] += m.get('cantidad', 0) or 0
        
        # Mermas por mes
        mermas_por_mes = {}
        for m in mermas:
            if m.get('fecha'):
                mes = m['fecha'].strftime('%Y-%m') if hasattr(m['fecha'], 'strftime') else str(m['fecha'])[:7]
                if mes not in mermas_por_mes:
                    mermas_por_mes[mes] = 0
                mermas_por_mes[mes] += m.get('cantidad', 0) or 0
        
        return {
            "mermas": mermas,
            "total_registros": len(mermas),
            "total_cantidad": total_cantidad,
            "por_persona": [{"name": k, "value": v} for k, v in mermas_por_persona.items()],
            "por_servicio": [{"name": k, "value": v} for k, v in mermas_por_servicio.items()],
            "por_mes": [{"mes": k, "cantidad": v} for k, v in sorted(mermas_por_mes.items())]
        }

# ==================== REPORTE PRODUCTIVIDAD ====================

@api_router.get("/reportes/productividad")
async def get_reporte_productividad(fecha_inicio: str = None, fecha_fin: str = None, servicio_id: str = None, persona_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM prod_movimientos_produccion WHERE fecha_fin IS NOT NULL"
        params = []
        if fecha_inicio:
            params.append(fecha_inicio)
            query += f" AND fecha_fin >= ${len(params)}::date"
        if fecha_fin:
            params.append(fecha_fin)
            query += f" AND fecha_fin <= ${len(params)}::date"
        if servicio_id:
            params.append(servicio_id)
            query += f" AND servicio_id = ${len(params)}"
        if persona_id:
            params.append(persona_id)
            query += f" AND persona_id = ${len(params)}"


        
        rows = await conn.fetch(query, *params)
        
        por_servicio = {}
        por_persona = {}
        
        for m in rows:
            srv_id = m['servicio_id']
            per_id = m['persona_id']
            cantidad = m['cantidad_recibida'] or 0
            costo = float(m['costo_calculado'] or 0)
            
            srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", srv_id)
            srv_nombre = srv['nombre'] if srv else 'Desconocido'
            
            if srv_id not in por_servicio:
                por_servicio[srv_id] = {"servicio_id": srv_id, "servicio_nombre": srv_nombre, "total_cantidad": 0, "total_costo": 0, "movimientos": 0}
            por_servicio[srv_id]['total_cantidad'] += cantidad
            por_servicio[srv_id]['total_costo'] += costo
            por_servicio[srv_id]['movimientos'] += 1
            
            per = await conn.fetchrow("SELECT nombre FROM prod_personas_produccion WHERE id = $1", per_id)
            per_nombre = per['nombre'] if per else 'Desconocido'
            
            if per_id not in por_persona:
                por_persona[per_id] = {"persona_id": per_id, "persona_nombre": per_nombre, "total_cantidad": 0, "total_costo": 0, "movimientos": 0}
            por_persona[per_id]['total_cantidad'] += cantidad
            por_persona[per_id]['total_costo'] += costo
            por_persona[per_id]['movimientos'] += 1
        
        return {
            "por_servicio": list(por_servicio.values()),
            "por_persona": list(por_persona.values()),
            "total_movimientos": len(rows)
        }

# ==================== ENDPOINTS KARDEX E INVENTARIO MOVIMIENTOS ====================

@api_router.get("/inventario-movimientos")
async def get_inventario_movimientos(
    item_id: str = None,
    tipo: str = None,
    fecha_inicio: str = None, fecha_fin: str = None,
    fecha_desde: str = None, fecha_hasta: str = None,
    limit: int = 100, offset: int = 0,
):
    # Compatibilidad de nombres de params
    f_inicio = fecha_inicio or fecha_desde
    f_fin = fecha_fin or fecha_hasta
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Construir queries con JOINs (eliminando N+1)
        unions = []
        params = []
        param_idx = 0
        
        # --- INGRESOS ---
        if not tipo or tipo == 'ingreso':
            ing_where = []
            if item_id:
                param_idx += 1; params.append(item_id)
                ing_where.append(f"i.item_id = ${param_idx}")
            if f_inicio:
                param_idx += 1; params.append(f_inicio)
                ing_where.append(f"i.fecha >= ${param_idx}::timestamp")
            if f_fin:
                param_idx += 1; params.append(f_fin)
                ing_where.append(f"i.fecha <= ${param_idx}::timestamp")
            where_clause = (" AND " + " AND ".join(ing_where)) if ing_where else ""
            unions.append(f"""
                SELECT i.id, 'ingreso' as tipo, i.item_id, inv.nombre as item_nombre, inv.codigo as item_codigo,
                       i.cantidad::float, i.costo_unitario::float, (i.cantidad * i.costo_unitario)::float as costo_total,
                       i.fecha, i.proveedor, i.numero_documento, i.observaciones,
                       NULL as registro_id, NULL as registro_n_corte, NULL as motivo
                FROM prod_inventario_ingresos i
                LEFT JOIN prod_inventario inv ON inv.id = i.item_id
                WHERE 1=1 {where_clause}
            """)
        
        # --- SALIDAS ---
        if not tipo or tipo == 'salida':
            sal_where = []
            if item_id:
                param_idx += 1; params.append(item_id)
                sal_where.append(f"s.item_id = ${param_idx}")
            if f_inicio:
                param_idx += 1; params.append(f_inicio)
                sal_where.append(f"s.fecha >= ${param_idx}::timestamp")
            if f_fin:
                param_idx += 1; params.append(f_fin)
                sal_where.append(f"s.fecha <= ${param_idx}::timestamp")
            where_clause = (" AND " + " AND ".join(sal_where)) if sal_where else ""
            unions.append(f"""
                SELECT s.id, 'salida' as tipo, s.item_id, inv.nombre as item_nombre, inv.codigo as item_codigo,
                       s.cantidad::float, 0::float as costo_unitario, s.costo_total::float,
                       s.fecha, NULL as proveedor, NULL as numero_documento, s.observaciones,
                       s.registro_id, r.n_corte as registro_n_corte, NULL as motivo
                FROM prod_inventario_salidas s
                LEFT JOIN prod_inventario inv ON inv.id = s.item_id
                LEFT JOIN prod_registros r ON r.id = s.registro_id
                WHERE 1=1 {where_clause}
            """)
        
        # --- AJUSTES ---
        if not tipo or tipo.startswith('ajuste'):
            aj_where = []
            if item_id:
                param_idx += 1; params.append(item_id)
                aj_where.append(f"a.item_id = ${param_idx}")
            if f_inicio:
                param_idx += 1; params.append(f_inicio)
                aj_where.append(f"a.fecha >= ${param_idx}::timestamp")
            if f_fin:
                param_idx += 1; params.append(f_fin)
                aj_where.append(f"a.fecha <= ${param_idx}::timestamp")
            where_clause = (" AND " + " AND ".join(aj_where)) if aj_where else ""
            unions.append(f"""
                SELECT a.id, ('ajuste_' || a.tipo) as tipo, a.item_id, inv.nombre as item_nombre, inv.codigo as item_codigo,
                       a.cantidad::float, 0::float as costo_unitario, 0::float as costo_total,
                       a.fecha, NULL as proveedor, NULL as numero_documento, a.observaciones,
                       NULL as registro_id, NULL as registro_n_corte, a.motivo
                FROM prod_inventario_ajustes a
                LEFT JOIN prod_inventario inv ON inv.id = a.item_id
                WHERE 1=1 {where_clause}
            """)
        
        if not unions:
            return []
        
        full_query = " UNION ALL ".join(unions)
        
        # Count total
        count_query = f"SELECT COUNT(*) FROM ({full_query}) sub"
        total = await conn.fetchval(count_query, *params)
        
        # Paginated results
        param_idx += 1; params.append(limit)
        param_idx += 1; params.append(offset)
        data_query = f"SELECT * FROM ({full_query}) sub ORDER BY fecha DESC NULLS LAST LIMIT ${param_idx - 1} OFFSET ${param_idx}"
        rows = await conn.fetch(data_query, *params)
        
        movimientos = [row_to_dict(r) for r in rows]
        return {"items": movimientos, "total": total}

@api_router.get("/inventario-kardex/{item_id}")
async def get_inventario_kardex_by_path(item_id: str):
    return await _get_kardex(item_id)

@api_router.get("/inventario-kardex")
async def get_inventario_kardex(item_id: str):
    return await _get_kardex(item_id)

async def _get_kardex(item_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        item = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        
        movimientos = []
        
        # Ingresos
        ingresos = await conn.fetch("SELECT * FROM prod_inventario_ingresos WHERE item_id = $1", item_id)
        for ing in ingresos:
            movimientos.append({
                "id": ing['id'],
                "tipo": "ingreso",
                "fecha": ing['fecha'],
                "cantidad": float(ing['cantidad']),
                "costo_unitario": float(ing['costo_unitario']),
                "costo_total": float(ing['cantidad']) * float(ing['costo_unitario']),
                "proveedor": ing['proveedor'],
                "numero_documento": ing['numero_documento'],
                "observaciones": ing['observaciones']
            })
        
        # Salidas
        salidas = await conn.fetch("SELECT * FROM prod_inventario_salidas WHERE item_id = $1", item_id)
        for sal in salidas:
            registro = None
            modelo_nombre = None
            if sal['registro_id']:
                registro = await conn.fetchrow("""
                    SELECT r.n_corte, m.nombre as modelo_nombre 
                    FROM prod_registros r 
                    LEFT JOIN prod_modelos m ON r.modelo_id = m.id
                    WHERE r.id = $1
                """, sal['registro_id'])
                if registro:
                    modelo_nombre = registro['modelo_nombre']
            movimientos.append({
                "id": sal['id'],
                "tipo": "salida",
                "fecha": sal['fecha'],
                "cantidad": -float(sal['cantidad']),
                "costo_unitario": 0,
                "costo_total": float(sal['costo_total']),
                "registro_id": sal['registro_id'],
                "registro_n_corte": registro['n_corte'] if registro else None,
                "modelo_nombre": modelo_nombre,
                "rollo_id": sal.get('rollo_id'),
            })
        
        # Ajustes
        ajustes = await conn.fetch("SELECT * FROM prod_inventario_ajustes WHERE item_id = $1", item_id)
        for aj in ajustes:
            cantidad = float(aj['cantidad']) if aj['tipo'] == 'entrada' else -float(aj['cantidad'])
            movimientos.append({
                "id": aj['id'],
                "tipo": f"ajuste_{aj['tipo']}",
                "fecha": aj['fecha'],
                "cantidad": cantidad,
                "costo_unitario": 0,
                "costo_total": 0,
                "motivo": aj['motivo'],
                "observaciones": aj['observaciones']
            })
        
        # Ordenar por fecha
        movimientos.sort(key=lambda x: x['fecha'] if x['fecha'] else datetime.min)
        
        # Calcular saldo acumulado
        saldo = 0
        for mov in movimientos:
            if mov['tipo'] == 'ingreso':
                saldo += mov['cantidad']
            elif mov['tipo'] == 'salida':
                saldo += mov['cantidad']  # ya es negativo
            elif mov['tipo'] == 'ajuste_entrada':
                saldo += abs(mov['cantidad'])
            elif mov['tipo'] == 'ajuste_salida':
                saldo -= abs(mov['cantidad'])
            mov['saldo'] = saldo
        
        return {
            "item": row_to_dict(item),
            "movimientos": movimientos,
            "saldo_actual": float(item['stock_actual'])
        }

# ==================== REPORTE ITEM - ESTADOS (PIVOT) ====================

@api_router.get("/reportes/estados-item")
async def get_reporte_estados_item(
    search: str = None,
    marca_id: str = None,
    tipo_id: str = None,
    entalle_id: str = None,
    tela_id: str = None,
    hilo_especifico_id: str = None,
    prioridad: str = None,  # urgente|normal
    include_tienda: bool = False,
):
    """Reporte tipo Power BI: ITEM (marca+tipo+entalle+tela) + HILO, columnas por estado = COUNT(registros)."""

    # Nota: en algunos entornos este estado aparece como "Para Atraque" (en DB/código) o "Para Atanque" (en reportes).
    # Ambos se consolidan en la misma columna (para_atanque).
    estados_map = {
        "Para Corte": "para_corte",
        "Para Costura": "para_costura",
        "Para Atraque": "para_atanque",
        "Para Atanque": "para_atanque",
        "Para Lavandería": "para_lavanderia",
        "Acabado": "acabado",
        "Almacén PT": "almacen_pt",
        "Tienda": "tienda",
    }

    estados_incluidos = [
        "Para Corte",
        "Para Costura",
        "Para Atraque",
        "Para Atanque",
        "Para Lavandería",
        "Acabado",
        "Almacén PT",
    ]
    if include_tienda:
        estados_incluidos.append("Tienda")

    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT r.estado, r.urgente, he.nombre as hilo_nombre,
                   ma.nombre as marca_nombre,
                   t.nombre as tipo_nombre,
                   e.nombre as entalle_nombre,
                   te.nombre as tela_nombre
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            LEFT JOIN prod_tipos t ON m.tipo_id = t.id
            LEFT JOIN prod_entalles e ON m.entalle_id = e.id
            LEFT JOIN prod_telas te ON m.tela_id = te.id
            LEFT JOIN prod_hilos_especificos he ON r.hilo_especifico_id = he.id
            WHERE 1=1
        """
        params = []

        if marca_id:
            params.append(marca_id)
            query += f" AND m.marca_id = ${len(params)}"
        if tipo_id:
            params.append(tipo_id)
            query += f" AND m.tipo_id = ${len(params)}"
        if entalle_id:
            params.append(entalle_id)
            query += f" AND m.entalle_id = ${len(params)}"
        if tela_id:
            params.append(tela_id)
            query += f" AND m.tela_id = ${len(params)}"
        if hilo_especifico_id:
            params.append(hilo_especifico_id)
            query += f" AND r.hilo_especifico_id = ${len(params)}"

        if prioridad == "urgente":
            query += " AND r.urgente = true"
        elif prioridad == "normal":
            query += " AND (r.urgente = false OR r.urgente IS NULL)"

        rows = await conn.fetch(query, *params)

    data = {}

    def safe(x):
        return (x or '').strip()

    for row in rows:
        estado = row.get('estado')
        if estado not in estados_incluidos:
            continue

        marca = safe(row.get('marca_nombre')) or 'Sin Marca'
        tipo = safe(row.get('tipo_nombre')) or 'Sin Tipo'
        entalle = safe(row.get('entalle_nombre')) or 'Sin Entalle'
        tela = safe(row.get('tela_nombre')) or 'Sin Tela'
        hilo = safe(row.get('hilo_nombre')) or 'Sin Hilo'

        item = f"{marca} - {tipo} - {entalle} - {tela}"

        if search and search.strip().lower() not in item.lower():
            continue

        key = (item, hilo)
        if key not in data:
            data[key] = {
                "item": item,
                "hilo": hilo,
                "total": 0,
            }
            for est in estados_incluidos:
                data[key][estados_map[est]] = 0

        col = estados_map.get(estado)
        if not col:
            continue

        data[key][col] += 1
        data[key]["total"] += 1

    result_rows = list(data.values())
    result_rows.sort(key=lambda r: (r.get('item') or '', r.get('hilo') or ''))

    updated_at = datetime.now().strftime('%d/%m/%Y %H:%M')
    return {
        "updated_at": updated_at,
        "include_tienda": include_tienda,
        "rows": result_rows,
    }



@api_router.get("/reportes/estados-item/detalle")
async def get_reporte_estados_item_detalle(
    item: str,
    hilo: str,
    estado: str,
    include_tienda: bool = False,
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
):
    """Detalle (drill-down) del reporte por Item+Hilo y Estado.

    - item: string exacto como se muestra ("Marca - Tipo - Entalle - Tela")
    - hilo: nombre del hilo específico (o "Sin Hilo")
    - estado: estado a filtrar (ej: "Para Costura")
    - include_tienda: si es False, no permite estado="Tienda"
    """

    if (not include_tienda) and estado == "Tienda":
        raise HTTPException(status_code=400, detail="Estado 'Tienda' no permitido cuando include_tienda=false")

    # Mapeo compatible: aceptar Para Atanque como sinónimo de Para Atraque
    if estado == "Para Atanque":
        estado = "Para Atraque"

    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT r.id, r.n_corte, r.estado, r.urgente, r.fecha_creacion,
                   m.nombre as modelo_nombre,
                   ma.nombre as marca_nombre,
                   t.nombre as tipo_nombre,
                   e.nombre as entalle_nombre,
                   te.nombre as tela_nombre,
                   he.nombre as hilo_nombre
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            LEFT JOIN prod_tipos t ON m.tipo_id = t.id
            LEFT JOIN prod_entalles e ON m.entalle_id = e.id
            LEFT JOIN prod_telas te ON m.tela_id = te.id
            LEFT JOIN prod_hilos_especificos he ON r.hilo_especifico_id = he.id
            WHERE 1=1
        """
        params = []

        # Reconstruir item igual que el reporte
        params.append(item)
        query += f" AND (COALESCE(ma.nombre,'Sin Marca') || ' - ' || COALESCE(t.nombre,'Sin Tipo') || ' - ' || COALESCE(e.nombre,'Sin Entalle') || ' - ' || COALESCE(te.nombre,'Sin Tela')) = ${len(params)}"

        params.append(estado)
        query += f" AND r.estado = ${len(params)}"

        if hilo == "Sin Hilo":
            query += " AND (r.hilo_especifico_id IS NULL)"
        else:
            params.append(hilo)
            query += f" AND he.nombre = ${len(params)}"

        # Paginación
        params.append(limit)
        query += f" ORDER BY r.fecha_creacion DESC NULLS LAST LIMIT ${len(params)}"
        params.append(offset)
        query += f" OFFSET ${len(params)}"

        rows = await conn.fetch(query, *params)

        # total
        count_query = """
            SELECT COUNT(*)
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            LEFT JOIN prod_tipos t ON m.tipo_id = t.id
            LEFT JOIN prod_entalles e ON m.entalle_id = e.id
            LEFT JOIN prod_telas te ON m.tela_id = te.id
            LEFT JOIN prod_hilos_especificos he ON r.hilo_especifico_id = he.id
            WHERE 1=1
        """
        count_params = []
        count_params.append(item)
        count_query += f" AND (COALESCE(ma.nombre,'Sin Marca') || ' - ' || COALESCE(t.nombre,'Sin Tipo') || ' - ' || COALESCE(e.nombre,'Sin Entalle') || ' - ' || COALESCE(te.nombre,'Sin Tela')) = ${len(count_params)}"
        count_params.append(estado)
        count_query += f" AND r.estado = ${len(count_params)}"
        if hilo == "Sin Hilo":
            count_query += " AND (r.hilo_especifico_id IS NULL)"
        else:
            count_params.append(hilo)
            count_query += f" AND he.nombre = ${len(count_params)}"

        total = await conn.fetchval(count_query, *count_params)

    result = []
    for r in rows:
        d = row_to_dict(r)
        # normalizar datetime
        if isinstance(d.get('fecha_creacion'), datetime):
            d['fecha_creacion'] = d['fecha_creacion'].strftime('%d/%m/%Y %H:%M')
        result.append(d)

    return {
        "item": item,
        "hilo": hilo,
        "estado": estado,
        "total": int(total or 0),
        "limit": limit,
        "offset": offset,
        "rows": result,
    }

@api_router.get("/reportes/estados-item/export")
async def export_reporte_estados_item(
    search: str = None,
    marca_id: str = None,
    tipo_id: str = None,
    entalle_id: str = None,
    tela_id: str = None,
    hilo_especifico_id: str = None,
    prioridad: str = None,
    include_tienda: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Export CSV (Excel) del reporte ITEM - ESTADOS."""

    reporte = await get_reporte_estados_item(
        search=search,
        marca_id=marca_id,
        tipo_id=tipo_id,
        entalle_id=entalle_id,
        tela_id=tela_id,
        hilo_especifico_id=hilo_especifico_id,
        prioridad=prioridad,
        include_tienda=include_tienda,
    )

    cols = [
        ('Item', 'item'),
        ('Hilo', 'hilo'),
        ('Para Corte', 'para_corte'),
        ('Para Costura', 'para_costura'),
        ('Para Atraque', 'para_atanque'),
        ('Para Lavandería', 'para_lavanderia'),
        ('Acabado', 'acabado'),
        ('Almacén PT', 'almacen_pt'),
    ]
    if include_tienda:
        cols.append(('Tienda', 'tienda'))
    cols.append(('Total', 'total'))

    output = io.StringIO()
    output.write('\ufeff')
    output.write(','.join([c[0] for c in cols]) + '\n')

    for row in reporte.get('rows', []):
        values = []
        for _, key in cols:
            val = row.get(key)
            if val is None:
                values.append('')
            else:
                s = str(val).replace('"', '""')
                if ',' in s or '"' in s or '\n' in s:
                    s = f'"{s}"'
                values.append(s)
        output.write(','.join(values) + '\n')

    output.seek(0)
    filename = f"reporte_estados_item_{datetime.now().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

# ==================== ENDPOINTS BACKUP ====================

BACKUP_TABLES = [
    'prod_marcas', 'prod_tipos', 'prod_entalles', 'prod_telas', 'prod_hilos',
    'prod_hilos_especificos', 'prod_tallas_catalogo', 'prod_colores_generales',
    'prod_colores_catalogo', 'prod_modelos', 'prod_registros', 'prod_inventario',
    'prod_inventario_ingresos', 'prod_inventario_salidas', 'prod_inventario_ajustes',
    'prod_inventario_rollos', 'prod_servicios_produccion', 'prod_personas_produccion',
    'prod_rutas_produccion', 'prod_movimientos_produccion', 'prod_mermas',
    'prod_guias_remision', 'prod_usuarios'
]

@api_router.get("/backup/create")
async def create_backup(current_user: dict = Depends(get_current_user)):
    """Crea un backup completo de todas las tablas"""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear backups")
    
    pool = await get_pool()
    backup_data = {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_by": current_user['username'],
        "tables": {}
    }
    
    async with pool.acquire() as conn:
        for table in BACKUP_TABLES:
            try:
                rows = await conn.fetch(f"SELECT * FROM {table}")
                table_data = []
                for row in rows:
                    row_dict = dict(row)
                    # Convertir tipos no serializables
                    for key, value in row_dict.items():
                        if isinstance(value, datetime):
                            row_dict[key] = value.isoformat()
                        elif isinstance(value, date):
                            row_dict[key] = value.isoformat()
                        elif isinstance(value, uuid.UUID):
                            row_dict[key] = str(value)
                        elif isinstance(value, Decimal):
                            row_dict[key] = float(value)
                    table_data.append(row_dict)
                backup_data["tables"][table] = table_data
            except Exception as e:
                backup_data["tables"][table] = {"error": str(e)}
    
    # Registrar actividad
    await registrar_actividad(
        pool,
        usuario_id=current_user['id'],
        usuario_nombre=current_user['username'],
        tipo_accion="crear",
        tabla_afectada="backup",
        descripcion="Creó backup completo de la base de datos"
    )
    
    # Generar archivo JSON
    json_content = json.dumps(backup_data, ensure_ascii=False, indent=2)
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    
    return StreamingResponse(
        io.BytesIO(json_content.encode('utf-8')),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@api_router.get("/backup/info")
async def backup_info(current_user: dict = Depends(get_current_user)):
    """Retorna información sobre las tablas para backup"""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    pool = await get_pool()
    info = {"tables": []}
    
    async with pool.acquire() as conn:
        for table in BACKUP_TABLES:
            try:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                info["tables"].append({"name": table, "count": count})
            except:
                info["tables"].append({"name": table, "count": 0, "error": True})
    
    return info

@api_router.post("/backup/restore")
async def restore_backup(file: UploadFile = File(...), current_user: dict = Depends(get_current_user)):
    """Restaura un backup desde archivo JSON"""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden restaurar backups")
    
    try:
        content = await file.read()
        backup_data = json.loads(content.decode('utf-8'))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al leer archivo: {str(e)}")
    
    if "tables" not in backup_data:
        raise HTTPException(status_code=400, detail="Formato de backup inválido")
    
    pool = await get_pool()
    restored = []
    errors = []
    
    async with pool.acquire() as conn:
        for table, rows in backup_data["tables"].items():
            if table not in BACKUP_TABLES:
                continue
            if isinstance(rows, dict) and "error" in rows:
                continue
            if not rows:
                continue
            
            try:
                # Eliminar datos existentes
                await conn.execute(f"DELETE FROM {table}")
                
                # Insertar nuevos datos
                for row in rows:
                    columns = list(row.keys())
                    values = list(row.values())
                    placeholders = [f"${i+1}" for i in range(len(columns))]
                    
                    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    try:
                        await conn.execute(query, *values)
                    except Exception as row_error:
                        errors.append(f"{table}: {str(row_error)[:50]}")
                
                restored.append(table)
            except Exception as table_error:
                errors.append(f"{table}: {str(table_error)}")
    
    # Registrar actividad
    await registrar_actividad(
        pool,
        usuario_id=current_user['id'],
        usuario_nombre=current_user['username'],
        tipo_accion="editar",
        tabla_afectada="backup",
        descripcion=f"Restauró backup: {len(restored)} tablas restauradas",
        datos_nuevos={"tablas_restauradas": restored, "errores": errors}
    )
    
    return {
        "message": "Backup restaurado",
        "restored_tables": restored,
        "errors": errors
    }

# ==================== ENDPOINTS EXPORTAR EXCEL ====================

@api_router.get("/export/{tabla}")
async def export_to_csv(tabla: str, current_user: dict = Depends(get_current_user)):
    """Exporta una tabla a formato CSV (compatible con Excel)"""
    
    # Mapeo de tabla a query
    EXPORT_CONFIG = {
        "registros": {
            "query": """
                SELECT r.n_corte, r.fecha_creacion, r.estado, r.urgente,
                       m.nombre as modelo, ma.nombre as marca, t.nombre as tipo,
                       en.nombre as entalle, te.nombre as tela,
                       h.nombre as hilo, he.nombre as hilo_especifico,
                       r.curva
                FROM prod_registros r
                LEFT JOIN prod_modelos m ON r.modelo_id = m.id
                LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
                LEFT JOIN prod_tipos t ON m.tipo_id = t.id
                LEFT JOIN prod_entalles en ON m.entalle_id = en.id
                LEFT JOIN prod_telas te ON m.tela_id = te.id
                LEFT JOIN prod_hilos h ON m.hilo_id = h.id
                LEFT JOIN prod_hilos_especificos he ON m.hilo_especifico_id = he.id
                ORDER BY r.fecha_creacion DESC
            """,
            "headers": ["N° Corte", "Fecha", "Estado", "Urgente", "Modelo", "Marca", "Tipo", "Entalle", "Tela", "Hilo", "Hilo Específico", "Curva"]
        },
        "inventario": {
            "query": """
                SELECT codigo, nombre, descripcion, unidad_medida, stock_actual, stock_minimo,
                       control_por_rollos
                FROM prod_inventario ORDER BY codigo
            """,
            "headers": ["Código", "Nombre", "Descripción", "Unidad", "Stock Actual", "Stock Mínimo", "Control Rollos"]
        },
        "movimientos": {
            "query": """
                SELECT i.codigo, i.nombre, 
                       COALESCE(ing.fecha, sal.fecha, aj.fecha) as fecha,
                       CASE 
                           WHEN ing.id IS NOT NULL THEN 'Ingreso'
                           WHEN sal.id IS NOT NULL THEN 'Salida'
                           WHEN aj.id IS NOT NULL THEN 'Ajuste'
                       END as tipo,
                       COALESCE(ing.cantidad, -sal.cantidad, aj.cantidad) as cantidad,
                       COALESCE(ing.costo_unitario, 0) as costo
                FROM prod_inventario i
                LEFT JOIN prod_inventario_ingresos ing ON i.id = ing.inventario_id
                LEFT JOIN prod_inventario_salidas sal ON i.id = sal.inventario_id
                LEFT JOIN prod_inventario_ajustes aj ON i.id = aj.inventario_id
                WHERE ing.id IS NOT NULL OR sal.id IS NOT NULL OR aj.id IS NOT NULL
                ORDER BY COALESCE(ing.fecha, sal.fecha, aj.fecha) DESC
            """,
            "headers": ["Código", "Item", "Fecha", "Tipo", "Cantidad", "Costo"]
        },
        "productividad": {
            "query": """
                SELECT p.nombre as persona, s.nombre as servicio, 
                       mp.cantidad_enviada as cantidad, mp.costo_calculado as monto,
                       mp.fecha_inicio as fecha, r.n_corte, mp.observaciones
                FROM prod_movimientos_produccion mp
                LEFT JOIN prod_personas_produccion p ON mp.persona_id = p.id
                LEFT JOIN prod_servicios_produccion s ON mp.servicio_id = s.id
                LEFT JOIN prod_registros r ON mp.registro_id = r.id
                ORDER BY mp.created_at DESC
            """,
            "headers": ["Persona", "Servicio", "Cantidad", "Monto", "Fecha", "N° Corte", "Observaciones"]
        },
        "personas": {
            "query": "SELECT nombre, telefono, activo FROM prod_personas_produccion ORDER BY nombre",
            "headers": ["Nombre", "Teléfono", "Activo"]
        },
        "modelos": {
            "query": """
                SELECT m.nombre, ma.nombre as marca, t.nombre as tipo,
                       e.nombre as entalle, te.nombre as tela
                FROM prod_modelos m
                LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
                LEFT JOIN prod_tipos t ON m.tipo_id = t.id
                LEFT JOIN prod_entalles e ON m.entalle_id = e.id
                LEFT JOIN prod_telas te ON m.tela_id = te.id
                ORDER BY m.nombre
            """,
            "headers": ["Nombre", "Marca", "Tipo", "Entalle", "Tela"]
        }
    }
    
    if tabla not in EXPORT_CONFIG:
        raise HTTPException(status_code=400, detail=f"Tabla '{tabla}' no exportable")
    
    config = EXPORT_CONFIG[tabla]
    pool = await get_pool()
    
    async with pool.acquire() as conn:
        rows = await conn.fetch(config["query"])
    
    # Crear CSV
    output = io.StringIO()
    # BOM para Excel
    output.write('\ufeff')
    # Headers
    output.write(','.join(config["headers"]) + '\n')
    
    for row in rows:
        values = []
        for val in row.values():
            if val is None:
                values.append('')
            elif isinstance(val, (datetime, date)):
                values.append(val.strftime('%d/%m/%Y'))
            elif isinstance(val, bool):
                values.append('Sí' if val else 'No')
            else:
                # Escapar comas y comillas
                str_val = str(val).replace('"', '""')
                if ',' in str_val or '"' in str_val or '\n' in str_val:
                    str_val = f'"{str_val}"'
                values.append(str_val)
        output.write(','.join(values) + '\n')
    
    output.seek(0)
    filename = f"{tabla}_{datetime.now().strftime('%Y%m%d')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# ==================== NUEVOS ROUTERS (Valorización/Costos/Cierre) ====================
from routes.costos import router as costos_router
from routes.cierre import router as cierre_legacy_router
# reportes_valorizacion deprecado - lógica unificada en routes/reportes.py

# ==================== ROUTERS REFACTORIZADOS (v2) ====================
from routes.inventario import router as inventario_router
from routes.rollos import router as rollos_router
from routes.ordenes import router as ordenes_router
from routes.consumo import router as consumo_router
from routes.servicios import router as servicios_router
from routes.cierre_v2 import router as cierre_v2_router
from routes.reportes import router as reportes_router
from routes.integracion_finanzas import router as integracion_finanzas_router
from routes.control_produccion import router as control_produccion_router
from routes.reportes_produccion import router as reportes_produccion_router
from routes.conversacion import router as conversacion_router
from routes.catalogos import router as catalogos_router
from routes.auth import router as auth_router
from routes.inventario_main import router as inventario_main_router


# ==================== DIVISIÓN DE LOTE ====================

class DivisionLoteRequest(BaseModel):
    tallas_hijo: list  # [{talla_id, talla_nombre, cantidad}, ...]
    estado_hijo: Optional[str] = None  # Si no se pasa, hereda del padre

@api_router.post("/registros/{registro_id}/dividir")
async def dividir_lote(registro_id: str, body: DivisionLoteRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        padre = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not padre:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        tallas_padre = padre['tallas'] if isinstance(padre['tallas'], list) else json.loads(padre['tallas']) if padre['tallas'] else []
        tallas_hijo_req = body.tallas_hijo
        
        # Validar que las cantidades del hijo no excedan las del padre
        padre_map = {t['talla_id']: t for t in tallas_padre}
        nuevas_tallas_padre = []
        tallas_hijo_final = []
        
        for tp in tallas_padre:
            hijo_t = next((h for h in tallas_hijo_req if h.get('talla_id') == tp['talla_id']), None)
            cant_hijo = hijo_t.get('cantidad', 0) if hijo_t else 0
            if cant_hijo < 0:
                raise HTTPException(status_code=400, detail=f"Cantidad negativa para talla {tp.get('talla_nombre')}")
            if cant_hijo > tp['cantidad']:
                raise HTTPException(status_code=400, detail=f"Cantidad para talla {tp.get('talla_nombre')} ({cant_hijo}) excede disponible ({tp['cantidad']})")
            nuevas_tallas_padre.append({**tp, 'cantidad': tp['cantidad'] - cant_hijo})
            if cant_hijo > 0:
                tallas_hijo_final.append({**tp, 'cantidad': cant_hijo})
        
        if not tallas_hijo_final:
            raise HTTPException(status_code=400, detail="Debe asignar al menos una talla al nuevo lote")
        
        # Determinar número de división
        max_div = await conn.fetchval(
            "SELECT COALESCE(MAX(division_numero), 0) FROM prod_registros WHERE dividido_desde_registro_id = $1",
            registro_id
        )
        # También considerar divisiones del padre original
        padre_original_id = padre.get('dividido_desde_registro_id') or registro_id
        if padre_original_id != registro_id:
            max_div2 = await conn.fetchval(
                "SELECT COALESCE(MAX(division_numero), 0) FROM prod_registros WHERE dividido_desde_registro_id = $1",
                padre_original_id
            )
            max_div = max(max_div, max_div2)
        
        division_num = max_div + 1
        n_corte_base = padre['n_corte'].split('-')[0]
        n_corte_hijo = f"{n_corte_base}-{division_num}"
        
        import uuid
        hijo_id = str(uuid.uuid4())
        estado_hijo = body.estado_hijo or padre['estado']
        
        await conn.execute("""
            INSERT INTO prod_registros (id, n_corte, modelo_id, curva, estado, urgente, tallas, distribucion_colores,
                fecha_creacion, hilo_especifico_id, empresa_id, pt_item_id, fecha_entrega_final,
                dividido_desde_registro_id, division_numero)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, CURRENT_TIMESTAMP, $9, $10, $11, $12, $13, $14)
        """,
            hijo_id, n_corte_hijo, padre['modelo_id'], padre.get('curva'), estado_hijo,
            padre.get('urgente', False),
            json.dumps(tallas_hijo_final), json.dumps(padre['distribucion_colores'] if isinstance(padre['distribucion_colores'], list) else []),
            padre.get('hilo_especifico_id'), padre.get('empresa_id'), padre.get('pt_item_id'),
            padre.get('fecha_entrega_final'),
            registro_id, division_num
        )
        
        await conn.execute(
            "UPDATE prod_registros SET tallas = $1::jsonb WHERE id = $2",
            json.dumps(nuevas_tallas_padre), registro_id
        )
        
        # Sincronizar prod_registro_tallas del padre (actualizar cantidades)
        for tp in nuevas_tallas_padre:
            await conn.execute(
                "UPDATE prod_registro_tallas SET cantidad_real = $1, updated_at = CURRENT_TIMESTAMP WHERE registro_id = $2 AND talla_id = $3",
                tp['cantidad'], registro_id, tp['talla_id']
            )
        
        # Crear prod_registro_tallas del hijo
        # Obtener empresa_id real desde los registros existentes
        empresa_id_real = await conn.fetchval(
            "SELECT empresa_id FROM prod_registro_tallas WHERE registro_id = $1 LIMIT 1", registro_id
        ) or 7
        for th in tallas_hijo_final:
            await conn.execute(
                """INSERT INTO prod_registro_tallas (id, registro_id, talla_id, cantidad_real, empresa_id, created_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                str(uuid.uuid4()), hijo_id, th['talla_id'], th['cantidad'], empresa_id_real
            )
        
        return {
            "mensaje": f"Lote dividido exitosamente. Nuevo registro: {n_corte_hijo}",
            "registro_hijo_id": hijo_id,
            "n_corte_hijo": n_corte_hijo,
            "tallas_padre": nuevas_tallas_padre,
            "tallas_hijo": tallas_hijo_final,
        }

@api_router.get("/registros/{registro_id}/divisiones")
async def get_divisiones_registro(registro_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        padre = await conn.fetchrow("SELECT id, n_corte, dividido_desde_registro_id FROM prod_registros WHERE id = $1", registro_id)
        if not padre:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Hijos directos
        hijos = await conn.fetch(
            "SELECT id, n_corte, estado, tallas, division_numero FROM prod_registros WHERE dividido_desde_registro_id = $1 ORDER BY division_numero",
            registro_id
        )
        
        # Si este registro es un hijo, obtener info del padre
        padre_info = None
        if padre['dividido_desde_registro_id']:
            p = await conn.fetchrow(
                "SELECT id, n_corte, estado FROM prod_registros WHERE id = $1",
                padre['dividido_desde_registro_id']
            )
            if p:
                padre_info = {"id": p['id'], "n_corte": p['n_corte'], "estado": p['estado']}
        
        # Hermanos (otros hijos del mismo padre)
        hermanos = []
        if padre['dividido_desde_registro_id']:
            hermanos_rows = await conn.fetch(
                "SELECT id, n_corte, estado FROM prod_registros WHERE dividido_desde_registro_id = $1 AND id != $2 ORDER BY division_numero",
                padre['dividido_desde_registro_id'], registro_id
            )
            hermanos = [{"id": h['id'], "n_corte": h['n_corte'], "estado": h['estado']} for h in hermanos_rows]
        
        return {
            "registro_id": registro_id,
            "n_corte": padre['n_corte'],
            "es_hijo": padre['dividido_desde_registro_id'] is not None,
            "padre": padre_info,
            "hijos": [
                {
                    "id": h['id'],
                    "n_corte": h['n_corte'],
                    "estado": h['estado'],
                    "tallas": h['tallas'] if isinstance(h['tallas'], list) else json.loads(h['tallas']) if h['tallas'] else [],
                    "division_numero": h['division_numero'],
                }
                for h in hijos
            ],
            "hermanos": hermanos,
        }

@api_router.post("/registros/{registro_id}/reunificar")
async def reunificar_lote(registro_id: str):
    """Reunifica un registro hijo con su padre. Solo si el hijo no tiene movimientos propios."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        hijo = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not hijo:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        if not hijo.get('dividido_desde_registro_id'):
            raise HTTPException(status_code=400, detail="Este registro no es una división. No se puede reunificar.")
        
        padre_id = hijo['dividido_desde_registro_id']
        
        # Verificar que el hijo no tenga movimientos
        mov_count = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_movimientos_produccion WHERE registro_id = $1", registro_id
        )
        if mov_count and mov_count > 0:
            raise HTTPException(status_code=400, detail="Este lote ya tiene movimientos registrados. No se puede reunificar.")
        
        # Verificar que el hijo no tenga salidas de inventario
        sal_count = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_inventario_salidas WHERE registro_id = $1", registro_id
        )
        if sal_count and sal_count > 0:
            raise HTTPException(status_code=400, detail="Este lote ya tiene salidas de inventario. No se puede reunificar.")
        
        # Sumar tallas del hijo al padre
        padre = await conn.fetchrow("SELECT tallas FROM prod_registros WHERE id = $1", padre_id)
        tallas_padre = padre['tallas'] if isinstance(padre['tallas'], list) else json.loads(padre['tallas']) if padre['tallas'] else []
        tallas_hijo = hijo['tallas'] if isinstance(hijo['tallas'], list) else json.loads(hijo['tallas']) if hijo['tallas'] else []
        
        padre_map = {t['talla_id']: t for t in tallas_padre}
        for th in tallas_hijo:
            tid = th['talla_id']
            if tid in padre_map:
                padre_map[tid]['cantidad'] = padre_map[tid]['cantidad'] + th['cantidad']
            else:
                padre_map[tid] = th
        
        nuevas_tallas = list(padre_map.values())
        
        await conn.execute(
            "UPDATE prod_registros SET tallas = $1::jsonb WHERE id = $2",
            json.dumps(nuevas_tallas), padre_id
        )
        
        # Sincronizar prod_registro_tallas del padre
        for tp in nuevas_tallas:
            existing = await conn.fetchval(
                "SELECT id FROM prod_registro_tallas WHERE registro_id = $1 AND talla_id = $2", padre_id, tp['talla_id']
            )
            if existing:
                await conn.execute(
                    "UPDATE prod_registro_tallas SET cantidad_real = $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                    tp['cantidad'], existing
                )
            else:
                await conn.execute(
                    """INSERT INTO prod_registro_tallas (id, registro_id, talla_id, cantidad_real, empresa_id, created_at, updated_at)
                       VALUES ($1, $2, $3, $4, $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)""",
                    str(uuid.uuid4()), padre_id, tp['talla_id'], tp['cantidad'], 7
                )
        
        # Eliminar prod_registro_tallas del hijo
        await conn.execute("DELETE FROM prod_registro_tallas WHERE registro_id = $1", registro_id)
        
        # Eliminar incidencias y paralizaciones del hijo
        await conn.execute("DELETE FROM prod_incidencia WHERE registro_id = $1", registro_id)
        await conn.execute("DELETE FROM prod_paralizacion WHERE registro_id = $1", registro_id)
        
        # Eliminar el registro hijo
        await conn.execute("DELETE FROM prod_registros WHERE id = $1", registro_id)
        
        return {
            "mensaje": f"Lote reunificado exitosamente con {padre['tallas']}",
            "padre_id": padre_id,
            "tallas_reunificadas": nuevas_tallas,
        }


# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup():
    await get_pool()
    await ensure_bom_tables()
    await ensure_fase2_tables()
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE prod_modelos DROP COLUMN IF EXISTS materiales")
        # Columnas para división de lote
        await conn.execute("ALTER TABLE prod_registros ADD COLUMN IF NOT EXISTS dividido_desde_registro_id VARCHAR NULL")
        await conn.execute("ALTER TABLE prod_registros ADD COLUMN IF NOT EXISTS division_numero INT DEFAULT 0")
        # Campo para vincular producto de liquidación en Odoo
        await conn.execute("ALTER TABLE prod_registros ADD COLUMN IF NOT EXISTS lq_odoo_id VARCHAR NULL")
        # Fix: corregir items con empresa_id inválido (1 no es válido)
        await conn.execute("""
            UPDATE prod_inventario SET empresa_id = 8
            WHERE empresa_id = 1
        """)
    # Tablas de trazabilidad unificada (fallados, arreglos)
    await init_trazabilidad_tables()

@app.on_event("shutdown")
async def shutdown():
    await close_pool()

# ==================== CORS & ROUTER ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(inventario_main_router)
app.include_router(catalogos_router)
app.include_router(auth_router)
app.include_router(api_router)
app.include_router(costos_router)
app.include_router(cierre_legacy_router)

# Include refactored routers
app.include_router(inventario_router)
app.include_router(rollos_router)
app.include_router(ordenes_router)
app.include_router(consumo_router)
app.include_router(servicios_router)
app.include_router(cierre_v2_router)
app.include_router(reportes_router)
app.include_router(integracion_finanzas_router)

# BOM router
from routes.bom import router as bom_router
app.include_router(bom_router)

app.include_router(control_produccion_router)
app.include_router(reportes_produccion_router)

# Trazabilidad unificada router
from routes.trazabilidad import router as trazabilidad_router, init_trazabilidad_tables
app.include_router(trazabilidad_router)
app.include_router(conversacion_router)