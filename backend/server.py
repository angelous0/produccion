from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header, UploadFile, File
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# PostgreSQL connection
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgres://admin:admin@72.60.241.216:9091/datos?sslmode=disable')

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'tu-clave-secreta-muy-segura-cambiar-en-produccion-2024')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer(auto_error=False)

# Connection pool
pool = None

async def get_pool():
    global pool
    if pool is None:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            server_settings={"search_path": "produccion,public"},
        )
    return pool


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

        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bom_inventario_id ON prod_modelo_bom_linea(inventario_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_bom_talla_id ON prod_modelo_bom_linea(talla_id)"
        )
        await conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_bom_linea_activo
            ON prod_modelo_bom_linea(modelo_id, inventario_id, talla_id)
            WHERE activo = TRUE
            """
        )


    return pool


# ==================== FASE 2: Tablas de Reservas y Requerimiento ====================
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


app = FastAPI()
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
    servicio_id: str
    orden: int = 0

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

class ModeloCreate(ModeloBase):
    pass

class Modelo(ModeloBase):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class TallaCantidadItem(BaseModel):
    talla_id: str


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
    fecha_inicio: Optional[str] = None
    fecha_fin: Optional[str] = None
    observaciones: str = ""

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
    pass

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

@api_router.post("/auth/login")
async def login(credentials: UserLogin):
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM prod_usuarios WHERE username = $1 AND activo = true",
            credentials.username
        )
        if not user or not verify_password(credentials.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
        
        # Crear token
        access_token = create_access_token(data={"sub": user['id']})
        
        user_dict = row_to_dict(user)
        user_dict.pop('password_hash', None)
        user_dict['permisos'] = parse_jsonb(user_dict.get('permisos'))
        
        # Registrar actividad de login
        await registrar_actividad(
            pool,
            usuario_id=user['id'],
            usuario_nombre=user['username'],
            tipo_accion="login",
            descripcion="Inicio de sesión exitoso"
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_dict
        }

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    user = dict(current_user)
    user.pop('password_hash', None)
    user['permisos'] = parse_jsonb(user.get('permisos'))
    return user

@api_router.put("/auth/change-password")
async def change_password(data: UserChangePassword, current_user: dict = Depends(get_current_user)):
    if not verify_password(data.current_password, current_user['password_hash']):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        new_hash = get_password_hash(data.new_password)
        await conn.execute(
            "UPDATE prod_usuarios SET password_hash = $1, updated_at = NOW() WHERE id = $2",
            new_hash, current_user['id']
        )
    
    # Registrar actividad
    await registrar_actividad(
        pool,
        usuario_id=current_user['id'],
        usuario_nombre=current_user['username'],
        tipo_accion="cambio_password",
        tabla_afectada="usuarios",
        registro_id=current_user['id'],
        registro_nombre=current_user['username'],
        descripcion="Cambió su propia contraseña"
    )
    
    return {"message": "Contraseña actualizada correctamente"}

# ==================== ENDPOINTS USUARIOS (ADMIN) ====================

@api_router.get("/usuarios")
async def get_usuarios(current_user: dict = Depends(get_current_user)):
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver usuarios")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_usuarios ORDER BY created_at DESC")
        result = []
        for r in rows:
            user = row_to_dict(r)
            user.pop('password_hash', None)
            user['permisos'] = parse_jsonb(user.get('permisos'))
            result.append(user)
        return result

@api_router.post("/usuarios")
async def create_usuario(input: UserCreate, current_user: dict = Depends(get_current_user)):
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden crear usuarios")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verificar que no exista
        existing = await conn.fetchrow("SELECT id FROM prod_usuarios WHERE username = $1", input.username)
        if existing:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
        
        if input.email:
            existing_email = await conn.fetchrow("SELECT id FROM prod_usuarios WHERE email = $1", input.email)
            if existing_email:
                raise HTTPException(status_code=400, detail="El email ya está registrado")
        
        user_id = str(uuid.uuid4())
        password_hash = get_password_hash(input.password)
        
        await conn.execute(
            """INSERT INTO prod_usuarios (id, username, email, password_hash, nombre_completo, rol, permisos, activo, created_at, updated_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, true, NOW(), NOW())""",
            user_id, input.username, input.email, password_hash, input.nombre_completo, 
            input.rol, json.dumps(input.permisos)
        )
        
        # Registrar actividad
        await registrar_actividad(
            pool,
            usuario_id=current_user['id'],
            usuario_nombre=current_user['username'],
            tipo_accion="crear",
            tabla_afectada="usuarios",
            registro_id=user_id,
            registro_nombre=input.username,
            descripcion=f"Creó usuario '{input.username}' con rol '{input.rol}'",
            datos_nuevos=limpiar_datos_sensibles({"username": input.username, "email": input.email, "nombre_completo": input.nombre_completo, "rol": input.rol})
        )
        
        return {"id": user_id, "username": input.username, "message": "Usuario creado correctamente"}

@api_router.put("/usuarios/{user_id}")
async def update_usuario(user_id: str, input: UserUpdate, current_user: dict = Depends(get_current_user)):
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden editar usuarios")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM prod_usuarios WHERE id = $1", user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Guardar datos anteriores
        datos_anteriores = limpiar_datos_sensibles({
            "email": user['email'],
            "nombre_completo": user['nombre_completo'],
            "rol": user['rol'],
            "activo": user['activo'],
            "permisos": parse_jsonb(user.get('permisos'))
        })
        
        # Construir actualización dinámica
        updates = []
        params = []
        param_count = 0
        cambios = {}
        
        if input.email is not None:
            param_count += 1
            updates.append(f"email = ${param_count}")
            params.append(input.email)
            cambios['email'] = input.email
        if input.nombre_completo is not None:
            param_count += 1
            updates.append(f"nombre_completo = ${param_count}")
            params.append(input.nombre_completo)
            cambios['nombre_completo'] = input.nombre_completo
        if input.rol is not None:
            param_count += 1
            updates.append(f"rol = ${param_count}")
            params.append(input.rol)
            cambios['rol'] = input.rol
        if input.permisos is not None:
            param_count += 1
            updates.append(f"permisos = ${param_count}")
            params.append(json.dumps(input.permisos))
            cambios['permisos'] = input.permisos
        if input.activo is not None:
            param_count += 1
            updates.append(f"activo = ${param_count}")
            params.append(input.activo)
            cambios['activo'] = input.activo
        
        if updates:
            param_count += 1
            updates.append("updated_at = NOW()")
            params.append(user_id)
            query = f"UPDATE prod_usuarios SET {', '.join(updates)} WHERE id = ${param_count}"
            await conn.execute(query, *params)
            
            # Registrar actividad
            descripcion = f"Editó usuario '{user['username']}'"
            if 'activo' in cambios:
                descripcion = f"{'Activó' if cambios['activo'] else 'Desactivó'} usuario '{user['username']}'"
            elif 'permisos' in cambios:
                descripcion = f"Modificó permisos de '{user['username']}'"
            elif 'rol' in cambios:
                descripcion = f"Cambió rol de '{user['username']}' a '{cambios['rol']}'"
            
            await registrar_actividad(
                pool,
                usuario_id=current_user['id'],
                usuario_nombre=current_user['username'],
                tipo_accion="editar",
                tabla_afectada="usuarios",
                registro_id=user_id,
                registro_nombre=user['username'],
                descripcion=descripcion,
                datos_anteriores=datos_anteriores,
                datos_nuevos=limpiar_datos_sensibles(cambios)
            )
        
        return {"message": "Usuario actualizado correctamente"}

@api_router.delete("/usuarios/{user_id}")
async def delete_usuario(user_id: str, current_user: dict = Depends(get_current_user)):
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden eliminar usuarios")
    
    if user_id == current_user['id']:
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Obtener datos del usuario antes de eliminar
        user = await conn.fetchrow("SELECT * FROM prod_usuarios WHERE id = $1", user_id)
        if user:
            datos_anteriores = limpiar_datos_sensibles({
                "username": user['username'],
                "email": user['email'],
                "nombre_completo": user['nombre_completo'],
                "rol": user['rol']
            })
            
            await conn.execute("DELETE FROM prod_usuarios WHERE id = $1", user_id)
            
            # Registrar actividad
            await registrar_actividad(
                pool,
                usuario_id=current_user['id'],
                usuario_nombre=current_user['username'],
                tipo_accion="eliminar",
                tabla_afectada="usuarios",
                registro_id=user_id,
                registro_nombre=user['username'],
                descripcion=f"Eliminó usuario '{user['username']}'",
                datos_anteriores=datos_anteriores
            )
    return {"message": "Usuario eliminado"}

class AdminSetPassword(BaseModel):
    new_password: str

@api_router.put("/usuarios/{user_id}/set-password")
async def set_password_usuario(user_id: str, data: AdminSetPassword, current_user: dict = Depends(get_current_user)):
    """Admin establece una contraseña específica para un usuario"""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden cambiar contraseñas")
    
    if len(data.new_password) < 4:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 4 caracteres")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT username FROM prod_usuarios WHERE id = $1", user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        new_hash = get_password_hash(data.new_password)
        await conn.execute("UPDATE prod_usuarios SET password_hash = $1, updated_at = NOW() WHERE id = $2", new_hash, user_id)
        
        # Registrar actividad
        await registrar_actividad(
            pool,
            usuario_id=current_user['id'],
            usuario_nombre=current_user['username'],
            tipo_accion="cambio_password_admin",
            tabla_afectada="usuarios",
            registro_id=user_id,
            registro_nombre=user['username'],
            descripcion=f"Cambió contraseña de '{user['username']}'"
        )
        
        return {"message": "Contraseña actualizada correctamente"}

@api_router.put("/usuarios/{user_id}/reset-password")
async def reset_password_usuario(user_id: str, current_user: dict = Depends(get_current_user)):
    """Resetea la contraseña a username + '123'"""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden resetear contraseñas")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT username FROM prod_usuarios WHERE id = $1", user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Nueva contraseña = username + "123"
        new_password = user['username'] + "123"
        new_hash = get_password_hash(new_password)
        await conn.execute("UPDATE prod_usuarios SET password_hash = $1, updated_at = NOW() WHERE id = $2", new_hash, user_id)
        
        return {"message": f"Contraseña reseteada. Nueva contraseña: {new_password}"}

@api_router.get("/permisos/estructura")
async def get_estructura_permisos():
    """Retorna la estructura de permisos disponibles agrupados por categoría"""
    return {
        "categorias": [
            {
                "nombre": "Producción",
                "icono": "Play",
                "tablas": [
                    {"key": "registros", "nombre": "Registros", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "movimientos_produccion", "nombre": "Movimientos de Producción", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "guias_remision", "nombre": "Guías de Remisión", "acciones": ["ver", "crear", "editar", "eliminar"]},
                ]
            },
            {
                "nombre": "Inventario",
                "icono": "Package",
                "tablas": [
                    {"key": "inventario", "nombre": "Items de Inventario", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "inventario_ingresos", "nombre": "Ingresos", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "inventario_salidas", "nombre": "Salidas", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "inventario_ajustes", "nombre": "Ajustes", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "inventario_rollos", "nombre": "Rollos de Tela", "acciones": ["ver", "crear", "editar"]},
                ]
            },
            {
                "nombre": "Maestros",
                "icono": "Database",
                "tablas": [
                    {"key": "marcas", "nombre": "Marcas", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "tipos", "nombre": "Tipos", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "entalles", "nombre": "Entalles", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "telas", "nombre": "Telas", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "hilos", "nombre": "Hilos", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "hilos_especificos", "nombre": "Hilos Específicos", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "tallas", "nombre": "Tallas", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "colores", "nombre": "Colores", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "colores_generales", "nombre": "Colores Generales", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "modelos", "nombre": "Modelos", "acciones": ["ver", "crear", "editar", "eliminar"]},
                ]
            },
            {
                "nombre": "Configuración",
                "icono": "Settings",
                "tablas": [
                    {"key": "servicios_produccion", "nombre": "Servicios", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "personas_produccion", "nombre": "Personas", "acciones": ["ver", "crear", "editar", "eliminar"]},
                    {"key": "rutas_produccion", "nombre": "Rutas de Producción", "acciones": ["ver", "crear", "editar", "eliminar"]},
                ]
            },
            {
                "nombre": "Calidad",
                "icono": "AlertTriangle",
                "tablas": [
                    {"key": "merma", "nombre": "Merma", "acciones": ["ver", "crear", "editar", "eliminar"]},
                ]
            },
            {
                "nombre": "Reportes",
                "icono": "BarChart",
                "tablas": [
                    {"key": "kardex", "nombre": "Kardex", "acciones": ["ver"]},
                    {"key": "reporte_productividad", "nombre": "Productividad", "acciones": ["ver"]},
                    {"key": "reporte_movimientos", "nombre": "Reporte Movimientos", "acciones": ["ver"]},
                ]
            },
        ]
    }

# ==================== ENDPOINTS HISTORIAL DE ACTIVIDAD ====================

@api_router.get("/actividad")
async def get_actividad(
    usuario_id: str = None,
    tipo_accion: str = None,
    tabla_afectada: str = None,
    fecha_desde: str = None,
    fecha_hasta: str = None,
    limit: int = 100,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Obtiene el historial de actividad con filtros"""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores pueden ver el historial")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM prod_actividad_historial WHERE 1=1"
        params = []
        param_count = 0
        
        if usuario_id:
            param_count += 1
            query += f" AND usuario_id = ${param_count}"
            params.append(usuario_id)
        
        if tipo_accion:
            param_count += 1
            query += f" AND tipo_accion = ${param_count}"
            params.append(tipo_accion)
        
        if tabla_afectada:
            param_count += 1
            query += f" AND tabla_afectada = ${param_count}"
            params.append(tabla_afectada)
        
        if fecha_desde:
            param_count += 1
            query += f" AND created_at >= ${param_count}::timestamp"
            params.append(fecha_desde)
        
        if fecha_hasta:
            param_count += 1
            query += f" AND created_at <= ${param_count}::timestamp + interval '1 day'"
            params.append(fecha_hasta)
        
        # Contar total
        count_query = query.replace("SELECT *", "SELECT COUNT(*)")
        total = await conn.fetchval(count_query, *params)
        
        # Obtener registros con paginación
        query += f" ORDER BY created_at DESC LIMIT {limit} OFFSET {offset}"
        rows = await conn.fetch(query, *params)
        
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['datos_anteriores'] = parse_jsonb(d.get('datos_anteriores'))
            d['datos_nuevos'] = parse_jsonb(d.get('datos_nuevos'))
            result.append(d)
        
        return {
            "total": total,
            "items": result,
            "limit": limit,
            "offset": offset
        }

@api_router.get("/actividad/tipos")
async def get_tipos_actividad(current_user: dict = Depends(get_current_user)):
    """Retorna los tipos de actividad disponibles"""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    return [
        {"value": "login", "label": "Inicio de Sesión", "icon": "LogIn", "color": "text-green-500"},
        {"value": "crear", "label": "Crear", "icon": "Plus", "color": "text-blue-500"},
        {"value": "editar", "label": "Editar", "icon": "Pencil", "color": "text-yellow-500"},
        {"value": "eliminar", "label": "Eliminar", "icon": "Trash2", "color": "text-red-500"},
        {"value": "cambio_password", "label": "Cambio de Contraseña", "icon": "Key", "color": "text-purple-500"},
        {"value": "cambio_password_admin", "label": "Cambio Contraseña (Admin)", "icon": "Shield", "color": "text-orange-500"},
    ]

@api_router.get("/actividad/tablas")
async def get_tablas_actividad(current_user: dict = Depends(get_current_user)):
    """Retorna las tablas que tienen actividad registrada"""
    if current_user['rol'] != 'admin':
        raise HTTPException(status_code=403, detail="Solo administradores")
    
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT DISTINCT tabla_afectada FROM prod_actividad_historial WHERE tabla_afectada IS NOT NULL ORDER BY tabla_afectada"
        )
        return [r['tabla_afectada'] for r in rows]

# ==================== ENDPOINTS MARCA ====================

@api_router.get("/marcas")
async def get_marcas():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_marcas ORDER BY orden ASC, created_at DESC")
        return [row_to_dict(r) for r in rows]

@api_router.post("/marcas")
async def create_marca(input: MarcaCreate):
    marca = Marca(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Auto-asignar orden si es 0
        if marca.orden == 0:
            max_orden = await conn.fetchval("SELECT COALESCE(MAX(orden), 0) FROM prod_marcas")
            marca.orden = max_orden + 1
        await conn.execute(
            "INSERT INTO prod_marcas (id, nombre, orden, created_at) VALUES ($1, $2, $3, $4)",
            marca.id, marca.nombre, marca.orden, marca.created_at.replace(tzinfo=None)
        )
    return marca

@api_router.put("/marcas/{marca_id}")
async def update_marca(marca_id: str, input: MarcaCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_marcas WHERE id = $1", marca_id)
        if not result:
            raise HTTPException(status_code=404, detail="Marca no encontrada")
        await conn.execute("UPDATE prod_marcas SET nombre = $1, orden = $2 WHERE id = $3", input.nombre, input.orden, marca_id)
        return {**row_to_dict(result), "nombre": input.nombre, "orden": input.orden}

@api_router.delete("/marcas/{marca_id}")
async def delete_marca(marca_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM prod_marcas WHERE id = $1", marca_id)
        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Marca no encontrada")
        return {"message": "Marca eliminada"}

# ==================== ENDPOINTS TIPO ====================

@api_router.get("/tipos")
async def get_tipos(marca_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if marca_id:
            rows = await conn.fetch("SELECT * FROM prod_tipos WHERE marca_ids ? $1 ORDER BY orden ASC, created_at DESC", marca_id)
        else:
            rows = await conn.fetch("SELECT * FROM prod_tipos ORDER BY orden ASC, created_at DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['marca_ids'] = parse_jsonb(d.get('marca_ids'))
            result.append(d)
        return result

@api_router.post("/tipos")
async def create_tipo(input: TipoCreate):
    tipo = Tipo(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        if tipo.orden == 0:
            max_orden = await conn.fetchval("SELECT COALESCE(MAX(orden), 0) FROM prod_tipos")
            tipo.orden = max_orden + 1
        await conn.execute(
            "INSERT INTO prod_tipos (id, nombre, marca_ids, orden, created_at) VALUES ($1, $2, $3, $4, $5)",
            tipo.id, tipo.nombre, json.dumps(tipo.marca_ids), tipo.orden, tipo.created_at.replace(tzinfo=None)
        )
    return tipo

@api_router.put("/tipos/{tipo_id}")
async def update_tipo(tipo_id: str, input: TipoCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_tipos WHERE id = $1", tipo_id)
        if not result:
            raise HTTPException(status_code=404, detail="Tipo no encontrado")
        await conn.execute("UPDATE prod_tipos SET nombre = $1, marca_ids = $2, orden = $3 WHERE id = $4", 
                          input.nombre, json.dumps(input.marca_ids), input.orden, tipo_id)
        return {**row_to_dict(result), "nombre": input.nombre, "marca_ids": input.marca_ids, "orden": input.orden}

@api_router.delete("/tipos/{tipo_id}")
async def delete_tipo(tipo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_tipos WHERE id = $1", tipo_id)
        return {"message": "Tipo eliminado"}

# ==================== ENDPOINTS ENTALLE ====================

@api_router.get("/entalles")
async def get_entalles(tipo_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if tipo_id:
            rows = await conn.fetch("SELECT * FROM prod_entalles WHERE tipo_ids ? $1 ORDER BY orden ASC, created_at DESC", tipo_id)
        else:
            rows = await conn.fetch("SELECT * FROM prod_entalles ORDER BY orden ASC, created_at DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['tipo_ids'] = parse_jsonb(d.get('tipo_ids'))
            result.append(d)
        return result

@api_router.post("/entalles")
async def create_entalle(input: EntalleCreate):
    entalle = Entalle(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        if entalle.orden == 0:
            max_orden = await conn.fetchval("SELECT COALESCE(MAX(orden), 0) FROM prod_entalles")
            entalle.orden = max_orden + 1
        await conn.execute(
            "INSERT INTO prod_entalles (id, nombre, tipo_ids, orden, created_at) VALUES ($1, $2, $3, $4, $5)",
            entalle.id, entalle.nombre, json.dumps(entalle.tipo_ids), entalle.orden, entalle.created_at.replace(tzinfo=None)
        )
    return entalle

@api_router.put("/entalles/{entalle_id}")
async def update_entalle(entalle_id: str, input: EntalleCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_entalles WHERE id = $1", entalle_id)
        if not result:
            raise HTTPException(status_code=404, detail="Entalle no encontrado")
        await conn.execute("UPDATE prod_entalles SET nombre = $1, tipo_ids = $2, orden = $3 WHERE id = $4",
                          input.nombre, json.dumps(input.tipo_ids), input.orden, entalle_id)
        return {**row_to_dict(result), "nombre": input.nombre, "tipo_ids": input.tipo_ids, "orden": input.orden}

@api_router.delete("/entalles/{entalle_id}")
async def delete_entalle(entalle_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_entalles WHERE id = $1", entalle_id)
        return {"message": "Entalle eliminado"}

# ==================== ENDPOINTS TELA ====================

@api_router.get("/telas")
async def get_telas(entalle_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if entalle_id:
            rows = await conn.fetch("SELECT * FROM prod_telas WHERE entalle_ids ? $1 ORDER BY orden ASC, created_at DESC", entalle_id)
        else:
            rows = await conn.fetch("SELECT * FROM prod_telas ORDER BY orden ASC, created_at DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['entalle_ids'] = parse_jsonb(d.get('entalle_ids'))
            result.append(d)
        return result

@api_router.post("/telas")
async def create_tela(input: TelaCreate):
    tela = Tela(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        if tela.orden == 0:
            max_orden = await conn.fetchval("SELECT COALESCE(MAX(orden), 0) FROM prod_telas")
            tela.orden = max_orden + 1
        await conn.execute(
            "INSERT INTO prod_telas (id, nombre, entalle_ids, orden, created_at) VALUES ($1, $2, $3, $4, $5)",
            tela.id, tela.nombre, json.dumps(tela.entalle_ids), tela.orden, tela.created_at.replace(tzinfo=None)
        )
    return tela

@api_router.put("/telas/{tela_id}")
async def update_tela(tela_id: str, input: TelaCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_telas WHERE id = $1", tela_id)
        if not result:
            raise HTTPException(status_code=404, detail="Tela no encontrada")
        await conn.execute("UPDATE prod_telas SET nombre = $1, entalle_ids = $2, orden = $3 WHERE id = $4",
                          input.nombre, json.dumps(input.entalle_ids), input.orden, tela_id)
        return {**row_to_dict(result), "nombre": input.nombre, "entalle_ids": input.entalle_ids, "orden": input.orden}

@api_router.delete("/telas/{tela_id}")
async def delete_tela(tela_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_telas WHERE id = $1", tela_id)
        return {"message": "Tela eliminada"}

# ==================== ENDPOINTS HILO ====================

@api_router.get("/hilos")
async def get_hilos(tela_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if tela_id:
            rows = await conn.fetch("SELECT * FROM prod_hilos WHERE tela_ids ? $1 ORDER BY orden ASC, created_at DESC", tela_id)
        else:
            rows = await conn.fetch("SELECT * FROM prod_hilos ORDER BY orden ASC, created_at DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['tela_ids'] = parse_jsonb(d.get('tela_ids'))
            result.append(d)
        return result

@api_router.post("/hilos")
async def create_hilo(input: HiloCreate):
    hilo = Hilo(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        if hilo.orden == 0:
            max_orden = await conn.fetchval("SELECT COALESCE(MAX(orden), 0) FROM prod_hilos")
            hilo.orden = max_orden + 1
        await conn.execute(
            "INSERT INTO prod_hilos (id, nombre, tela_ids, orden, created_at) VALUES ($1, $2, $3, $4, $5)",
            hilo.id, hilo.nombre, json.dumps(hilo.tela_ids), hilo.orden, hilo.created_at.replace(tzinfo=None)
        )
    return hilo

@api_router.put("/hilos/{hilo_id}")
async def update_hilo(hilo_id: str, input: HiloCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_hilos WHERE id = $1", hilo_id)
        if not result:
            raise HTTPException(status_code=404, detail="Hilo no encontrado")
        await conn.execute("UPDATE prod_hilos SET nombre = $1, tela_ids = $2, orden = $3 WHERE id = $4",
                          input.nombre, json.dumps(input.tela_ids), input.orden, hilo_id)
        return {**row_to_dict(result), "nombre": input.nombre, "tela_ids": input.tela_ids, "orden": input.orden}

@api_router.delete("/hilos/{hilo_id}")
async def delete_hilo(hilo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_hilos WHERE id = $1", hilo_id)
        return {"message": "Hilo eliminado"}

# ==================== ENDPOINTS TALLA CATALOGO ====================

@api_router.get("/tallas-catalogo")
async def get_tallas_catalogo():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_tallas_catalogo ORDER BY orden ASC")
        return [row_to_dict(r) for r in rows]

@api_router.post("/tallas-catalogo")
async def create_talla_catalogo(input: TallaCreate):
    talla = Talla(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO prod_tallas_catalogo (id, nombre, orden, created_at) VALUES ($1, $2, $3, $4)",
            talla.id, talla.nombre, talla.orden, talla.created_at.replace(tzinfo=None)
        )
    return talla

@api_router.put("/tallas-catalogo/{talla_id}")
async def update_talla_catalogo(talla_id: str, input: TallaCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_tallas_catalogo WHERE id = $1", talla_id)
        if not result:
            raise HTTPException(status_code=404, detail="Talla no encontrada")
        await conn.execute("UPDATE prod_tallas_catalogo SET nombre = $1, orden = $2 WHERE id = $3",
                          input.nombre, input.orden, talla_id)
        return {**row_to_dict(result), "nombre": input.nombre, "orden": input.orden}

@api_router.delete("/tallas-catalogo/{talla_id}")
async def delete_talla_catalogo(talla_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_tallas_catalogo WHERE id = $1", talla_id)
        return {"message": "Talla eliminada"}

# ==================== ENDPOINTS COLORES GENERALES ====================

@api_router.get("/colores-generales")
async def get_colores_generales():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_colores_generales ORDER BY orden ASC, nombre ASC")
        return [row_to_dict(r) for r in rows]

@api_router.post("/colores-generales")
async def create_color_general(input: ColorGeneralCreate):
    color_general = ColorGeneral(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verificar que no exista
        existing = await conn.fetchrow("SELECT id FROM prod_colores_generales WHERE LOWER(nombre) = LOWER($1)", input.nombre)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un color general con ese nombre")
        if color_general.orden == 0:
            max_orden = await conn.fetchval("SELECT COALESCE(MAX(orden), 0) FROM prod_colores_generales")
            color_general.orden = max_orden + 1
        await conn.execute(
            "INSERT INTO prod_colores_generales (id, nombre, orden, created_at) VALUES ($1, $2, $3, $4)",
            color_general.id, color_general.nombre, color_general.orden, color_general.created_at.replace(tzinfo=None)
        )
    return color_general

@api_router.put("/colores-generales/{color_general_id}")
async def update_color_general(color_general_id: str, input: ColorGeneralCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_colores_generales WHERE id = $1", color_general_id)
        if not result:
            raise HTTPException(status_code=404, detail="Color general no encontrado")
        # Verificar que no exista otro con el mismo nombre
        existing = await conn.fetchrow("SELECT id FROM prod_colores_generales WHERE LOWER(nombre) = LOWER($1) AND id != $2", input.nombre, color_general_id)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un color general con ese nombre")
        await conn.execute("UPDATE prod_colores_generales SET nombre = $1, orden = $2 WHERE id = $3", input.nombre, input.orden, color_general_id)
        return {**row_to_dict(result), "nombre": input.nombre, "orden": input.orden}

@api_router.delete("/colores-generales/{color_general_id}")
async def delete_color_general(color_general_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verificar si hay colores usando este color general
        count = await conn.fetchval("SELECT COUNT(*) FROM prod_colores_catalogo WHERE color_general_id = $1", color_general_id)
        if count > 0:
            raise HTTPException(status_code=400, detail=f"No se puede eliminar: {count} color(es) usan este color general")
        await conn.execute("DELETE FROM prod_colores_generales WHERE id = $1", color_general_id)
        return {"message": "Color general eliminado"}

# ==================== ENDPOINTS COLOR CATALOGO ====================

@api_router.get("/colores-catalogo")
async def get_colores_catalogo():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_colores_catalogo ORDER BY orden ASC, nombre ASC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            # Obtener nombre del color general
            if d.get('color_general_id'):
                cg = await conn.fetchrow("SELECT nombre FROM prod_colores_generales WHERE id = $1", d['color_general_id'])
                d['color_general_nombre'] = cg['nombre'] if cg else None
            else:
                d['color_general_nombre'] = None
            result.append(d)
        return result

@api_router.post("/colores-catalogo")
async def create_color_catalogo(input: ColorCreate):
    color = Color(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        if color.orden == 0:
            max_orden = await conn.fetchval("SELECT COALESCE(MAX(orden), 0) FROM prod_colores_catalogo")
            color.orden = max_orden + 1
        await conn.execute(
            "INSERT INTO prod_colores_catalogo (id, nombre, codigo_hex, color_general_id, orden, created_at) VALUES ($1, $2, $3, $4, $5, $6)",
            color.id, color.nombre, color.codigo_hex, color.color_general_id, color.orden, color.created_at.replace(tzinfo=None)
        )
    return color

@api_router.put("/colores-catalogo/{color_id}")
async def update_color_catalogo(color_id: str, input: ColorCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_colores_catalogo WHERE id = $1", color_id)
        if not result:
            raise HTTPException(status_code=404, detail="Color no encontrado")
        await conn.execute("UPDATE prod_colores_catalogo SET nombre = $1, codigo_hex = $2, color_general_id = $3, orden = $4 WHERE id = $5",
                          input.nombre, input.codigo_hex, input.color_general_id, input.orden, color_id)
        return {**row_to_dict(result), "nombre": input.nombre, "codigo_hex": input.codigo_hex, "color_general_id": input.color_general_id, "orden": input.orden}

@api_router.delete("/colores-catalogo/{color_id}")
async def delete_color_catalogo(color_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_colores_catalogo WHERE id = $1", color_id)
        return {"message": "Color eliminado"}

# ==================== ENDPOINT REORDENAMIENTO BATCH ====================

class ReorderItem(BaseModel):
    id: str
    orden: int

class ReorderRequest(BaseModel):
    items: List[ReorderItem]


# ==================== REORDENAMIENTO MODELO ↔ TALLAS ====================

@api_router.put("/modelos/{modelo_id}/tallas/reorder")
async def reorder_modelo_tallas(modelo_id: str, request: ReorderRequest, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    """Reordena tallas de un modelo. Se valida que cada id pertenezca al modelo."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # validar pertenencia
        ids = [it.id for it in request.items]
        if not ids:
            return {"message": "Sin cambios", "items_updated": 0}

        rows = await conn.fetch(
            "SELECT id FROM prod_modelo_tallas WHERE modelo_id=$1 AND id = ANY($2::varchar[])",
            modelo_id,
            ids,
        )
        found = {r['id'] for r in rows}
        missing = [i for i in ids if i not in found]
        if missing:
            raise HTTPException(status_code=400, detail="Hay tallas que no pertenecen a este modelo")

        for item in request.items:
            await conn.execute(
                "UPDATE prod_modelo_tallas SET orden=$1, updated_at=CURRENT_TIMESTAMP WHERE id=$2",
                int(item.orden),
                item.id,
            )

    return {"message": "Orden actualizado", "items_updated": len(request.items)}


@api_router.delete("/modelos/{modelo_id}/tallas/{rel_id}/hard")
async def hard_delete_modelo_talla(modelo_id: str, rel_id: str, current_user: dict = Depends(require_permission('modelos', 'editar'))):
    """Elimina físicamente la relación modelo-talla SOLO si no tiene vinculaciones (por ahora: BOM)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rel = await conn.fetchrow("SELECT * FROM prod_modelo_tallas WHERE id=$1 AND modelo_id=$2", rel_id, modelo_id)
        if not rel:
            raise HTTPException(status_code=404, detail="Relación modelo-talla no encontrada")

        # Vinculación: BOM por talla
        used = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_modelo_bom_linea WHERE modelo_id=$1 AND talla_id=$2",
            modelo_id,
            rel.get('talla_id'),
        )
        if used and int(used) > 0:
            raise HTTPException(status_code=400, detail="No se puede borrar: hay líneas BOM vinculadas a esta talla")

        await conn.execute("DELETE FROM prod_modelo_tallas WHERE id=$1", rel_id)

    return {"message": "Talla eliminada"}

 

@api_router.put("/reorder/{tabla}")
async def reorder_items(tabla: str, request: ReorderRequest):
    """Endpoint genérico para reordenar items de cualquier tabla"""
    tablas_permitidas = {
        "marcas": "prod_marcas",
        "tipos": "prod_tipos",
        "entalles": "prod_entalles",
        "telas": "prod_telas",
        "hilos": "prod_hilos",
        "tallas-catalogo": "prod_tallas_catalogo",
        "colores-generales": "prod_colores_generales",
        "colores-catalogo": "prod_colores_catalogo",
        "hilos-especificos": "prod_hilos_especificos"
    }
    
    if tabla not in tablas_permitidas:
        raise HTTPException(status_code=400, detail=f"Tabla '{tabla}' no permitida para reordenamiento")
    
    table_name = tablas_permitidas[tabla]
    pool = await get_pool()
    async with pool.acquire() as conn:
        for item in request.items:
            await conn.execute(f"UPDATE {table_name} SET orden = $1 WHERE id = $2", item.orden, item.id)
    
    return {"message": f"Reordenamiento de {tabla} completado", "items_updated": len(request.items)}

# ==================== ENDPOINTS HILOS ESPECÍFICOS ====================

@api_router.get("/hilos-especificos")
async def get_hilos_especificos():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_hilos_especificos ORDER BY orden ASC, nombre ASC")
        return [row_to_dict(r) for r in rows]

@api_router.post("/hilos-especificos")
async def create_hilo_especifico(input: HiloEspecificoCreate):
    hilo = HiloEspecifico(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        if hilo.orden == 0:
            max_orden = await conn.fetchval("SELECT COALESCE(MAX(orden), 0) FROM prod_hilos_especificos")
            hilo.orden = max_orden + 1
        await conn.execute(
            "INSERT INTO prod_hilos_especificos (id, nombre, codigo, color, descripcion, orden, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7)",
            hilo.id, hilo.nombre, hilo.codigo, hilo.color, hilo.descripcion, hilo.orden, hilo.created_at.replace(tzinfo=None)
        )
    return hilo

@api_router.put("/hilos-especificos/{hilo_id}")
async def update_hilo_especifico(hilo_id: str, input: HiloEspecificoCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_hilos_especificos WHERE id = $1", hilo_id)
        if not result:
            raise HTTPException(status_code=404, detail="Hilo específico no encontrado")
        await conn.execute(
            "UPDATE prod_hilos_especificos SET nombre = $1, codigo = $2, color = $3, descripcion = $4, orden = $5 WHERE id = $6",
            input.nombre, input.codigo, input.color, input.descripcion, input.orden, hilo_id
        )
        return {**row_to_dict(result), **input.model_dump()}

@api_router.delete("/hilos-especificos/{hilo_id}")
async def delete_hilo_especifico(hilo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_hilos_especificos WHERE id = $1", hilo_id)
        return {"message": "Hilo específico eliminado"}

# ==================== ENDPOINTS RUTAS PRODUCCION ====================

@api_router.get("/rutas-produccion")
async def get_rutas_produccion():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_rutas_produccion ORDER BY created_at DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['etapas'] = parse_jsonb(d.get('etapas'))
            # Enriquecer con nombres de servicios
            for etapa in d['etapas']:
                srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", etapa.get('servicio_id'))
                etapa['servicio_nombre'] = srv['nombre'] if srv else None
            result.append(d)
        return result

@api_router.get("/rutas-produccion/{ruta_id}")
async def get_ruta_produccion(ruta_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM prod_rutas_produccion WHERE id = $1", ruta_id)
        if not row:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")
        d = row_to_dict(row)
        d['etapas'] = parse_jsonb(d.get('etapas'))
        for etapa in d['etapas']:
            srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", etapa.get('servicio_id'))
            etapa['servicio_nombre'] = srv['nombre'] if srv else None
        return d

@api_router.post("/rutas-produccion")
async def create_ruta_produccion(input: RutaProduccionCreate):
    ruta = RutaProduccion(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        etapas_json = json.dumps([e.model_dump() for e in ruta.etapas])
        await conn.execute(
            "INSERT INTO prod_rutas_produccion (id, nombre, descripcion, etapas, created_at) VALUES ($1, $2, $3, $4, $5)",
            ruta.id, ruta.nombre, ruta.descripcion, etapas_json, ruta.created_at.replace(tzinfo=None)
        )
    return ruta

@api_router.put("/rutas-produccion/{ruta_id}")
async def update_ruta_produccion(ruta_id: str, input: RutaProduccionCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_rutas_produccion WHERE id = $1", ruta_id)
        if not result:
            raise HTTPException(status_code=404, detail="Ruta no encontrada")
        etapas_json = json.dumps([e.model_dump() for e in input.etapas])
        await conn.execute("UPDATE prod_rutas_produccion SET nombre = $1, descripcion = $2, etapas = $3 WHERE id = $4",
                          input.nombre, input.descripcion, etapas_json, ruta_id)
        return {**row_to_dict(result), "nombre": input.nombre, "descripcion": input.descripcion, "etapas": [e.model_dump() for e in input.etapas]}

@api_router.delete("/rutas-produccion/{ruta_id}")
async def delete_ruta_produccion(ruta_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        count = await conn.fetchval("SELECT COUNT(*) FROM prod_modelos WHERE ruta_produccion_id = $1", ruta_id)
        if count > 0:
            raise HTTPException(status_code=400, detail=f"No se puede eliminar: {count} modelo(s) usan esta ruta")
        await conn.execute("DELETE FROM prod_rutas_produccion WHERE id = $1", ruta_id)
        return {"message": "Ruta eliminada"}

# ==================== ENDPOINTS SERVICIOS PRODUCCION ====================

@api_router.get("/servicios-produccion")
async def get_servicios_produccion():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_servicios_produccion ORDER BY nombre ASC")
        return [row_to_dict(r) for r in rows]

@api_router.post("/servicios-produccion")
async def create_servicio_produccion(input: ServicioCreate):
    servicio = Servicio(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO prod_servicios_produccion (id, nombre, descripcion, tarifa, created_at) VALUES ($1, $2, $3, $4, $5)",
            servicio.id, servicio.nombre, servicio.descripcion, servicio.tarifa, servicio.created_at.replace(tzinfo=None)
        )
    return servicio

@api_router.put("/servicios-produccion/{servicio_id}")
async def update_servicio_produccion(servicio_id: str, input: ServicioCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_servicios_produccion WHERE id = $1", servicio_id)
        if not result:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        await conn.execute("UPDATE prod_servicios_produccion SET nombre = $1, descripcion = $2, tarifa = $3 WHERE id = $4",
                          input.nombre, input.descripcion, input.tarifa, servicio_id)
        return {**row_to_dict(result), **input.model_dump()}

@api_router.delete("/servicios-produccion/{servicio_id}")
async def delete_servicio_produccion(servicio_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        mov_count = await conn.fetchval("SELECT COUNT(*) FROM prod_movimientos_produccion WHERE servicio_id = $1", servicio_id)
        if mov_count > 0:
            raise HTTPException(status_code=400, detail=f"No se puede eliminar: {mov_count} movimiento(s) usan este servicio")
        await conn.execute("DELETE FROM prod_servicios_produccion WHERE id = $1", servicio_id)
        return {"message": "Servicio eliminado"}

# ==================== ENDPOINTS PERSONAS PRODUCCION ====================

@api_router.get("/personas-produccion")
async def get_personas_produccion(servicio_id: str = None, activo: bool = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM prod_personas_produccion WHERE 1=1"
        params = []
        if activo is not None:
            params.append(activo)
            query += f" AND activo = ${len(params)}"
        query += " ORDER BY orden ASC, nombre ASC"
        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['servicios'] = parse_jsonb(d.get('servicios'))
            # Enriquecer con nombre del servicio
            servicios_detalle = []
            for s in d['servicios']:
                srv = await conn.fetchrow("SELECT nombre FROM prod_servicios_produccion WHERE id = $1", s.get('servicio_id'))
                servicios_detalle.append({
                    "servicio_id": s.get('servicio_id'),
                    "servicio_nombre": srv['nombre'] if srv else None,
                    "tarifa": s.get('tarifa', 0)
                })
            d['servicios_detalle'] = servicios_detalle
            if servicio_id:
                if any(s.get('servicio_id') == servicio_id for s in d['servicios']):
                    result.append(d)
            else:
                result.append(d)
        return result

@api_router.post("/personas-produccion")
async def create_persona_produccion(input: PersonaCreate):
    persona = Persona(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        servicios_json = json.dumps([s.model_dump() for s in persona.servicios])
        await conn.execute(
            "INSERT INTO prod_personas_produccion (id, nombre, tipo, telefono, email, direccion, servicios, activo, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            persona.id, persona.nombre, persona.tipo, persona.telefono, persona.email, persona.direccion, servicios_json, persona.activo, persona.created_at.replace(tzinfo=None)
        )
    return persona

@api_router.put("/personas-produccion/{persona_id}")
async def update_persona_produccion(persona_id: str, input: PersonaCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_personas_produccion WHERE id = $1", persona_id)
        if not result:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        servicios_json = json.dumps([s.model_dump() for s in input.servicios])
        await conn.execute(
            "UPDATE prod_personas_produccion SET nombre=$1, tipo=$2, telefono=$3, email=$4, direccion=$5, servicios=$6, activo=$7 WHERE id=$8",
            input.nombre, input.tipo, input.telefono, input.email, input.direccion, servicios_json, input.activo, persona_id
        )
        return {**row_to_dict(result), **input.model_dump()}

@api_router.delete("/personas-produccion/{persona_id}")
async def delete_persona_produccion(persona_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        mov_count = await conn.fetchval("SELECT COUNT(*) FROM prod_movimientos_produccion WHERE persona_id = $1", persona_id)
        if mov_count > 0:
            raise HTTPException(status_code=400, detail=f"No se puede eliminar: {mov_count} movimiento(s) asignados")
        await conn.execute("DELETE FROM prod_personas_produccion WHERE id = $1", persona_id)
        return {"message": "Persona eliminada"}

# ==================== ENDPOINTS MODELOS ====================

@api_router.get("/modelos")
async def get_modelos():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_modelos ORDER BY created_at DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['servicios_ids'] = parse_jsonb(d.get('servicios_ids'))
            # Enriquecer con nombres
            marca = await conn.fetchrow("SELECT nombre FROM prod_marcas WHERE id = $1", d.get('marca_id'))
            tipo = await conn.fetchrow("SELECT nombre FROM prod_tipos WHERE id = $1", d.get('tipo_id'))
            entalle = await conn.fetchrow("SELECT nombre FROM prod_entalles WHERE id = $1", d.get('entalle_id'))
            tela = await conn.fetchrow("SELECT nombre FROM prod_telas WHERE id = $1", d.get('tela_id'))
            hilo = await conn.fetchrow("SELECT nombre FROM prod_hilos WHERE id = $1", d.get('hilo_id'))
            ruta = await conn.fetchrow("SELECT nombre FROM prod_rutas_produccion WHERE id = $1", d.get('ruta_produccion_id')) if d.get('ruta_produccion_id') else None
            d['marca_nombre'] = marca['nombre'] if marca else None
            d['tipo_nombre'] = tipo['nombre'] if tipo else None
            d['entalle_nombre'] = entalle['nombre'] if entalle else None
            d['tela_nombre'] = tela['nombre'] if tela else None
            d['hilo_nombre'] = hilo['nombre'] if hilo else None
            d['ruta_nombre'] = ruta['nombre'] if ruta else None
            result.append(d)
        return result

@api_router.get("/modelos/{modelo_id}")
async def get_modelo_detalle(modelo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM prod_modelos WHERE id = $1", modelo_id)
        if not row:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")

        d = row_to_dict(row)
        return d


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
        await conn.execute(
            """INSERT INTO prod_modelos (id, nombre, marca_id, tipo_id, entalle_id, tela_id, hilo_id, 
               ruta_produccion_id, servicios_ids, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            modelo.id, modelo.nombre, modelo.marca_id, modelo.tipo_id, modelo.entalle_id, modelo.tela_id,
            modelo.hilo_id, modelo.ruta_produccion_id, servicios_json, modelo.created_at.replace(tzinfo=None)
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
        await conn.execute(
            """UPDATE prod_modelos SET nombre=$1, marca_id=$2, tipo_id=$3, entalle_id=$4, tela_id=$5, hilo_id=$6,
               ruta_produccion_id=$7, servicios_ids=$8 WHERE id=$9""",
            input.nombre, input.marca_id, input.tipo_id, input.entalle_id, input.tela_id, input.hilo_id,
            input.ruta_produccion_id, servicios_json, modelo_id
        )
        return {**row_to_dict(result), **input.model_dump()}

@api_router.delete("/modelos/{modelo_id}")
async def delete_modelo(modelo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_modelos WHERE id = $1", modelo_id)
        return {"message": "Modelo eliminado"}

# ==================== ENDPOINTS REGISTROS ====================

@api_router.get("/estados")
async def get_estados():
    return {"estados": ESTADOS_PRODUCCION}

@api_router.get("/registros")
async def get_registros():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_registros ORDER BY fecha_creacion DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['tallas'] = parse_jsonb(d.get('tallas'))
            d['distribucion_colores'] = parse_jsonb(d.get('distribucion_colores'))
            # Enriquecer modelo
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
            result.append(d)
        return result

@api_router.get("/registros/{registro_id}")
async def get_registro(registro_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not row:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        d = row_to_dict(row)
        d['tallas'] = parse_jsonb(d.get('tallas'))
        d['distribucion_colores'] = parse_jsonb(d.get('distribucion_colores'))
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
        return d

@api_router.post("/registros")
async def create_registro(input: RegistroCreate):
    registro = Registro(**input.model_dump())
    pool = await get_pool()
    async with pool.acquire() as conn:
        tallas_json = json.dumps([t.model_dump() for t in registro.tallas])
        dist_json = json.dumps([d.model_dump() for d in registro.distribucion_colores])
        await conn.execute(
            """INSERT INTO prod_registros (id, n_corte, modelo_id, curva, estado, urgente, hilo_especifico_id, tallas, distribucion_colores, fecha_creacion) 
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            registro.id, registro.n_corte, registro.modelo_id, registro.curva, registro.estado, registro.urgente,
            registro.hilo_especifico_id, tallas_json, dist_json, registro.fecha_creacion.replace(tzinfo=None)
        )
    return registro

@api_router.put("/registros/{registro_id}")
async def update_registro(registro_id: str, input: RegistroCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not result:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        tallas_json = json.dumps([t.model_dump() for t in input.tallas])
        dist_json = json.dumps([d.model_dump() for d in input.distribucion_colores])
        await conn.execute(
            """UPDATE prod_registros SET n_corte=$1, modelo_id=$2, curva=$3, estado=$4, urgente=$5, hilo_especifico_id=$6, tallas=$7, distribucion_colores=$8 WHERE id=$9""",
            input.n_corte, input.modelo_id, input.curva, input.estado, input.urgente, input.hilo_especifico_id, tallas_json, dist_json, registro_id
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
        return {"estados": ESTADOS_PRODUCCION, "usa_ruta": False, "estado_actual": registro['estado']}


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
async def generar_requerimiento_mp(registro_id: str):
    """Genera el requerimiento de MP a partir de la explosión del BOM"""
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
        
        # Obtener BOM activo del modelo
        bom_lineas = await conn.fetch("""
            SELECT bl.*, i.nombre as item_nombre, i.codigo as item_codigo, i.unidad_medida
            FROM prod_modelo_bom_linea bl
            JOIN prod_inventario i ON bl.inventario_id = i.id
            WHERE bl.modelo_id = $1 AND bl.activo = true
        """, modelo_id)
        
        if not bom_lineas:
            raise HTTPException(status_code=400, detail="El modelo no tiene BOM definido")
        
        created = 0
        updated = 0
        
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
                    (id, registro_id, item_id, talla_id, cantidad_requerida, cantidad_reservada, cantidad_consumida, estado)
                    VALUES ($1, $2, $3, $4, $5, 0, 0, $6)
                """, new_id, registro_id, item_id, talla_id, cantidad_requerida, estado)
                created += 1
        
        return {
            "message": "Requerimiento generado",
            "total_prendas": total_prendas,
            "lineas_creadas": created,
            "lineas_actualizadas": updated
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
            INSERT INTO prod_inventario_reservas (id, registro_id, estado)
            VALUES ($1, $2, 'ACTIVA')
        """, reserva_id, registro_id)
        
        # Crear líneas y actualizar requerimiento
        lineas_creadas = []
        for linea in input.lineas:
            linea_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO prod_inventario_reservas_linea
                (id, reserva_id, item_id, talla_id, cantidad_reservada, cantidad_liberada)
                VALUES ($1, $2, $3, $4, $5, 0)
            """, linea_id, reserva_id, linea.item_id, linea.talla_id, linea.cantidad)
            
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

@api_router.get("/inventario-categorias")
async def get_categorias():
    return {"categorias": CATEGORIAS_INVENTARIO}

@api_router.get("/inventario")
async def get_inventario():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_inventario ORDER BY nombre ASC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            # Calcular total reservado para este item
            total_reservado = await conn.fetchval("""
                SELECT COALESCE(SUM(rl.cantidad_reservada - rl.cantidad_liberada), 0)
                FROM prod_inventario_reservas_linea rl
                JOIN prod_inventario_reservas res ON rl.reserva_id = res.id
                WHERE rl.item_id = $1 AND res.estado = 'ACTIVA'
            """, d['id'])
            d['total_reservado'] = float(total_reservado or 0)
            d['stock_disponible'] = max(0, float(d['stock_actual']) - d['total_reservado'])
            result.append(d)
        return result

@api_router.get("/inventario/{item_id}")
async def get_item_inventario(item_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        item = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        d = row_to_dict(item)
        # Lotes disponibles
        ingresos = await conn.fetch(
            "SELECT * FROM prod_inventario_ingresos WHERE item_id = $1 AND cantidad_disponible > 0 ORDER BY fecha ASC", item_id
        )
        d['lotes'] = [row_to_dict(i) for i in ingresos]
        # Rollos si aplica
        if d.get('control_por_rollos'):
            rollos = await conn.fetch(
                "SELECT * FROM prod_inventario_rollos WHERE item_id = $1 AND activo = true AND metraje_disponible > 0", item_id
            )
            d['rollos'] = [row_to_dict(r) for r in rollos]
        return d


@api_router.get("/inventario/{item_id}/reservas-detalle")
async def get_reservas_detalle_item(item_id: str):
    """
    Obtiene el detalle de reservas activas para un item,
    agrupado por registro (para ver qué registros tienen reservas)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        item = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        
        # Obtener todas las líneas de reserva activas para este item
        rows = await conn.fetch("""
            SELECT 
                rl.id,
                rl.item_id,
                rl.talla_id,
                rl.cantidad_reservada,
                rl.cantidad_liberada,
                (rl.cantidad_reservada - rl.cantidad_liberada) as cantidad_activa,
                res.id as reserva_id,
                res.registro_id,
                res.estado as reserva_estado,
                res.fecha as reserva_fecha,
                reg.n_corte,
                reg.estado as registro_estado,
                m.nombre as modelo_nombre,
                tc.nombre as talla_nombre
            FROM prod_inventario_reservas_linea rl
            JOIN prod_inventario_reservas res ON rl.reserva_id = res.id
            JOIN prod_registros reg ON res.registro_id = reg.id
            LEFT JOIN prod_modelos m ON reg.modelo_id = m.id
            LEFT JOIN prod_tallas_catalogo tc ON rl.talla_id = tc.id
            WHERE rl.item_id = $1 AND res.estado = 'ACTIVA' AND (rl.cantidad_reservada - rl.cantidad_liberada) > 0
            ORDER BY res.fecha DESC
        """, item_id)
        
        # Agrupar por registro
        registros_map = {}
        for r in rows:
            reg_id = r['registro_id']
            if reg_id not in registros_map:
                registros_map[reg_id] = {
                    'registro_id': reg_id,
                    'n_corte': r['n_corte'],
                    'registro_estado': r['registro_estado'],
                    'modelo_nombre': r['modelo_nombre'],
                    'total_reservado': 0,
                    'lineas': []
                }
            registros_map[reg_id]['total_reservado'] += float(r['cantidad_activa'])
            registros_map[reg_id]['lineas'].append({
                'id': r['id'],
                'talla_nombre': r['talla_nombre'],
                'cantidad_reservada': float(r['cantidad_reservada']),
                'cantidad_liberada': float(r['cantidad_liberada']),
                'cantidad_activa': float(r['cantidad_activa']),
                'reserva_fecha': r['reserva_fecha'].isoformat() if r['reserva_fecha'] else None
            })
        
        total_reservado = sum(reg['total_reservado'] for reg in registros_map.values())
        
        return {
            'item_id': item_id,
            'item_codigo': item['codigo'],
            'item_nombre': item['nombre'],
            'stock_actual': float(item['stock_actual']),
            'total_reservado': total_reservado,
            'stock_disponible': max(0, float(item['stock_actual']) - total_reservado),
            'registros': list(registros_map.values())
        }


@api_router.post("/inventario")
async def create_item_inventario(input: ItemInventarioCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT id FROM prod_inventario WHERE codigo = $1", input.codigo)
        if existing:
            raise HTTPException(status_code=400, detail="El código ya existe")
        item = ItemInventario(**input.model_dump())
        await conn.execute(
            """INSERT INTO prod_inventario (id, codigo, nombre, descripcion, categoria, unidad_medida, stock_minimo, stock_actual, control_por_rollos, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            item.id, item.codigo, item.nombre, item.descripcion, item.categoria, item.unidad_medida,
            item.stock_minimo, item.stock_actual, item.control_por_rollos, item.created_at.replace(tzinfo=None)
        )
        return item

@api_router.put("/inventario/{item_id}")
async def update_item_inventario(item_id: str, input: ItemInventarioCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", item_id)
        if not result:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        if input.codigo != result['codigo']:
            existing = await conn.fetchrow("SELECT id FROM prod_inventario WHERE codigo = $1 AND id != $2", input.codigo, item_id)
            if existing:
                raise HTTPException(status_code=400, detail="El código ya existe")
        await conn.execute(
            """UPDATE prod_inventario SET codigo=$1, nombre=$2, descripcion=$3, categoria=$4, unidad_medida=$5, stock_minimo=$6, control_por_rollos=$7 WHERE id=$8""",
            input.codigo, input.nombre, input.descripcion, input.categoria, input.unidad_medida, input.stock_minimo, input.control_por_rollos, item_id
        )
        return {**row_to_dict(result), **input.model_dump()}

@api_router.delete("/inventario/{item_id}")
async def delete_item_inventario(item_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_inventario_ingresos WHERE item_id = $1", item_id)
        await conn.execute("DELETE FROM prod_inventario_salidas WHERE item_id = $1", item_id)
        await conn.execute("DELETE FROM prod_inventario_ajustes WHERE item_id = $1", item_id)
        await conn.execute("DELETE FROM prod_inventario_rollos WHERE item_id = $1", item_id)
        await conn.execute("DELETE FROM prod_inventario WHERE id = $1", item_id)
        return {"message": "Item eliminado"}

# ==================== ENDPOINTS INGRESOS INVENTARIO ====================

@api_router.get("/inventario-ingresos")
async def get_ingresos():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_inventario_ingresos ORDER BY fecha DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            item = await conn.fetchrow("SELECT nombre, codigo FROM prod_inventario WHERE id = $1", d.get('item_id'))
            d['item_nombre'] = item['nombre'] if item else ""
            d['item_codigo'] = item['codigo'] if item else ""
            rollos_count = await conn.fetchval("SELECT COUNT(*) FROM prod_inventario_rollos WHERE ingreso_id = $1", d['id'])
            d['rollos_count'] = rollos_count
            result.append(d)
        return result

@api_router.post("/inventario-ingresos")
async def create_ingreso(input: IngresoInventarioCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        item = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", input.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
        
        rollos_data = input.rollos if hasattr(input, 'rollos') else []
        cantidad = input.cantidad
        
        if item['control_por_rollos'] and rollos_data:
            cantidad = sum(r.get('metraje', 0) for r in rollos_data)
        
        ingreso = IngresoInventario(
            item_id=input.item_id, cantidad=cantidad, costo_unitario=input.costo_unitario,
            proveedor=input.proveedor, numero_documento=input.numero_documento, observaciones=input.observaciones
        )
        ingreso.cantidad_disponible = cantidad
        
        await conn.execute(
            """INSERT INTO prod_inventario_ingresos (id, item_id, cantidad, cantidad_disponible, costo_unitario, proveedor, numero_documento, observaciones, fecha)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""",
            ingreso.id, ingreso.item_id, ingreso.cantidad, ingreso.cantidad_disponible, ingreso.costo_unitario,
            ingreso.proveedor, ingreso.numero_documento, ingreso.observaciones, ingreso.fecha.replace(tzinfo=None)
        )
        
        # Crear rollos si aplica
        if item['control_por_rollos'] and rollos_data:
            for rollo_data in rollos_data:
                rollo_id = str(uuid.uuid4())
                await conn.execute(
                    """INSERT INTO prod_inventario_rollos (id, item_id, ingreso_id, numero_rollo, metraje, metraje_disponible, ancho, tono, observaciones, activo, created_at)
                       VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
                    rollo_id, input.item_id, ingreso.id, rollo_data.get('numero_rollo', ''), rollo_data.get('metraje', 0),
                    rollo_data.get('metraje', 0), rollo_data.get('ancho', 0), rollo_data.get('tono', ''),
                    rollo_data.get('observaciones', ''), True, datetime.now()
                )
        
        # Actualizar stock
        await conn.execute("UPDATE prod_inventario SET stock_actual = stock_actual + $1 WHERE id = $2", cantidad, input.item_id)
        return ingreso

class IngresoUpdateData(BaseModel):
    proveedor: str = ""
    numero_documento: str = ""
    observaciones: str = ""
    costo_unitario: float = 0

@api_router.put("/inventario-ingresos/{ingreso_id}")
async def update_ingreso(ingreso_id: str, input: IngresoUpdateData):
    pool = await get_pool()
    async with pool.acquire() as conn:
        ingreso = await conn.fetchrow("SELECT * FROM prod_inventario_ingresos WHERE id = $1", ingreso_id)
        if not ingreso:
            raise HTTPException(status_code=404, detail="Ingreso no encontrado")
        await conn.execute(
            """UPDATE prod_inventario_ingresos SET proveedor=$1, numero_documento=$2, observaciones=$3, costo_unitario=$4 WHERE id=$5""",
            input.proveedor, input.numero_documento, input.observaciones, input.costo_unitario, ingreso_id
        )
        return {"message": "Ingreso actualizado", **input.model_dump()}

@api_router.delete("/inventario-ingresos/{ingreso_id}")
async def delete_ingreso(ingreso_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        ingreso = await conn.fetchrow("SELECT * FROM prod_inventario_ingresos WHERE id = $1", ingreso_id)
        if not ingreso:
            raise HTTPException(status_code=404, detail="Ingreso no encontrado")
        if ingreso['cantidad_disponible'] != ingreso['cantidad']:
            raise HTTPException(status_code=400, detail="No se puede eliminar un ingreso que ya tiene salidas")
        await conn.execute("DELETE FROM prod_inventario_rollos WHERE ingreso_id = $1", ingreso_id)
        await conn.execute("DELETE FROM prod_inventario_ingresos WHERE id = $1", ingreso_id)
        await conn.execute("UPDATE prod_inventario SET stock_actual = stock_actual - $1 WHERE id = $2", ingreso['cantidad'], ingreso['item_id'])
        return {"message": "Ingreso eliminado"}

# ==================== ENDPOINTS SALIDAS INVENTARIO ====================

@api_router.get("/inventario-salidas")
async def get_salidas(registro_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        if registro_id:
            rows = await conn.fetch("SELECT * FROM prod_inventario_salidas WHERE registro_id = $1 ORDER BY fecha DESC", registro_id)
        else:
            rows = await conn.fetch("SELECT * FROM prod_inventario_salidas ORDER BY fecha DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            d['detalle_fifo'] = parse_jsonb(d.get('detalle_fifo'))
            item = await conn.fetchrow("SELECT nombre, codigo FROM prod_inventario WHERE id = $1", d.get('item_id'))
            d['item_nombre'] = item['nombre'] if item else ""
            d['item_codigo'] = item['codigo'] if item else ""
            if d.get('registro_id'):
                reg = await conn.fetchrow("SELECT n_corte FROM prod_registros WHERE id = $1", d['registro_id'])
                d['registro_n_corte'] = reg['n_corte'] if reg else None
            if d.get('rollo_id'):
                rollo = await conn.fetchrow("SELECT numero_rollo FROM prod_inventario_rollos WHERE id = $1", d['rollo_id'])
                d['rollo_numero'] = rollo['numero_rollo'] if rollo else None
            # Fase 2: incluir talla_nombre
            if d.get('talla_id'):
                talla = await conn.fetchrow("SELECT nombre FROM prod_tallas_catalogo WHERE id = $1", d['talla_id'])
                d['talla_nombre'] = talla['nombre'] if talla else None
            else:
                d['talla_nombre'] = None
            result.append(d)
        return result

@api_router.post("/inventario-salidas")
async def create_salida(input: SalidaInventarioCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        item = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", input.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
        
        control_por_rollos = item['control_por_rollos']
        
        # === FASE 2: Validaciones de reserva y rollo ===
        
        # Validar regla de rollo según control_por_rollos
        if control_por_rollos:
            # TELA: rollo_id OBLIGATORIO
            if not input.rollo_id:
                raise HTTPException(status_code=400, detail="Este item requiere seleccionar un rollo (control por rollos activo)")
            # Validar que el rollo pertenece al item
            rollo = await conn.fetchrow("SELECT * FROM prod_inventario_rollos WHERE id = $1", input.rollo_id)
            if not rollo:
                raise HTTPException(status_code=404, detail="Rollo no encontrado")
            if rollo['item_id'] != input.item_id:
                raise HTTPException(status_code=400, detail="El rollo no pertenece a este item")
            if float(rollo['metraje_disponible']) < input.cantidad:
                raise HTTPException(status_code=400, detail=f"Metraje insuficiente en rollo. Disponible: {rollo['metraje_disponible']}")
        else:
            # NO TELA: rollo_id debe ser NULL
            if input.rollo_id:
                raise HTTPException(status_code=400, detail="Este item no usa control por rollos, rollo_id debe ser vacío")
            # Validar stock suficiente
            if float(item['stock_actual']) < input.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {item['stock_actual']}")
        
        # Validar registro si se proporciona
        if input.registro_id:
            reg = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", input.registro_id)
            if not reg:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            
            # FASE 2C: Validar que OP no esté cerrada/anulada
            if reg['estado'] in ('CERRADA', 'ANULADA'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"OP {reg['estado'].lower()}: no se puede crear salidas en una orden {reg['estado'].lower()}"
                )
            
            # Buscar requerimiento para validar reserva
            if input.talla_id:
                req = await conn.fetchrow("""
                    SELECT * FROM prod_registro_requerimiento_mp
                    WHERE registro_id = $1 AND item_id = $2 AND talla_id = $3
                """, input.registro_id, input.item_id, input.talla_id)
            else:
                req = await conn.fetchrow("""
                    SELECT * FROM prod_registro_requerimiento_mp
                    WHERE registro_id = $1 AND item_id = $2 AND talla_id IS NULL
                """, input.registro_id, input.item_id)
            
            if not req:
                raise HTTPException(status_code=400, detail="No existe requerimiento para este item/talla. Genera el requerimiento y reserva primero.")
            
            # Validar que hay reserva suficiente
            reserva_pendiente = float(req['cantidad_reservada']) - float(req['cantidad_consumida'])
            if input.cantidad > reserva_pendiente:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Reserva insuficiente. Reservado pendiente: {reserva_pendiente}, Solicitado: {input.cantidad}. Reserva más antes de consumir."
                )
        
        # === FIN Validaciones Fase 2 ===
        
        costo_total = 0.0
        detalle_fifo = []
        
        if input.rollo_id:
            # Ya validamos el rollo arriba, lo obtenemos de nuevo para el ingreso
            rollo = await conn.fetchrow("SELECT * FROM prod_inventario_rollos WHERE id = $1", input.rollo_id)
            ingreso = await conn.fetchrow("SELECT costo_unitario FROM prod_inventario_ingresos WHERE id = $1", rollo['ingreso_id'])
            costo_unitario = float(ingreso['costo_unitario']) if ingreso else 0
            costo_total = input.cantidad * costo_unitario
            detalle_fifo = [{"rollo_id": input.rollo_id, "cantidad": input.cantidad, "costo_unitario": costo_unitario}]
            await conn.execute("UPDATE prod_inventario_rollos SET metraje_disponible = metraje_disponible - $1 WHERE id = $2", input.cantidad, input.rollo_id)
            await conn.execute("UPDATE prod_inventario_ingresos SET cantidad_disponible = cantidad_disponible - $1 WHERE id = $2", input.cantidad, rollo['ingreso_id'])
        else:
            ingresos = await conn.fetch(
                "SELECT * FROM prod_inventario_ingresos WHERE item_id = $1 AND cantidad_disponible > 0 ORDER BY fecha ASC", input.item_id
            )
            cantidad_restante = input.cantidad
            for ing in ingresos:
                if cantidad_restante <= 0:
                    break
                disponible = float(ing['cantidad_disponible'])
                consumir = min(disponible, cantidad_restante)
                costo_unitario = float(ing['costo_unitario'])
                costo_total += consumir * costo_unitario
                detalle_fifo.append({"ingreso_id": ing['id'], "cantidad": consumir, "costo_unitario": costo_unitario})
                await conn.execute("UPDATE prod_inventario_ingresos SET cantidad_disponible = cantidad_disponible - $1 WHERE id = $2", consumir, ing['id'])
                cantidad_restante -= consumir
        
        salida = SalidaInventario(**input.model_dump())
        salida.costo_total = costo_total
        salida.detalle_fifo = detalle_fifo
        
        # Insertar salida con talla_id
        await conn.execute(
            """INSERT INTO prod_inventario_salidas (id, item_id, cantidad, registro_id, talla_id, observaciones, rollo_id, costo_total, detalle_fifo, fecha)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            salida.id, salida.item_id, salida.cantidad, salida.registro_id, salida.talla_id, salida.observaciones,
            salida.rollo_id, salida.costo_total, json.dumps(salida.detalle_fifo), salida.fecha.replace(tzinfo=None)
        )
        await conn.execute("UPDATE prod_inventario SET stock_actual = stock_actual - $1 WHERE id = $2", input.cantidad, input.item_id)
        
        # === FASE 2: Actualizar cantidad_consumida en requerimiento ===
        if input.registro_id:
            if input.talla_id:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_consumida = cantidad_consumida + $1,
                        estado = CASE
                            WHEN cantidad_consumida + $1 >= cantidad_requerida THEN 'COMPLETO'
                            ELSE 'PARCIAL'
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id = $4
                """, input.cantidad, input.registro_id, input.item_id, input.talla_id)
            else:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_consumida = cantidad_consumida + $1,
                        estado = CASE
                            WHEN cantidad_consumida + $1 >= cantidad_requerida THEN 'COMPLETO'
                            ELSE 'PARCIAL'
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id IS NULL
                """, input.cantidad, input.registro_id, input.item_id)
        
        return salida


# OPCIÓN 2: Endpoint para Salida Extra (sin validación de reserva)
class SalidaExtraCreate(BaseModel):
    item_id: str
    cantidad: float
    registro_id: str
    talla_id: Optional[str] = None
    observaciones: str = ""
    rollo_id: Optional[str] = None
    motivo: str = "Consumo adicional"

@api_router.post("/inventario-salidas/extra")
async def create_salida_extra(input: SalidaExtraCreate):
    """
    Crea una salida SIN validar reserva previa.
    Útil para excedentes, reposiciones o ajustes.
    Solo valida stock/rollo disponible.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        item = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", input.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
        
        control_por_rollos = item['control_por_rollos']
        
        # Validar regla de rollo según control_por_rollos
        if control_por_rollos:
            if not input.rollo_id:
                raise HTTPException(status_code=400, detail="Este item requiere seleccionar un rollo")
            rollo = await conn.fetchrow("SELECT * FROM prod_inventario_rollos WHERE id = $1", input.rollo_id)
            if not rollo:
                raise HTTPException(status_code=404, detail="Rollo no encontrado")
            if rollo['item_id'] != input.item_id:
                raise HTTPException(status_code=400, detail="El rollo no pertenece a este item")
            if float(rollo['metraje_disponible']) < input.cantidad:
                raise HTTPException(status_code=400, detail=f"Metraje insuficiente en rollo. Disponible: {rollo['metraje_disponible']}")
        else:
            if input.rollo_id:
                raise HTTPException(status_code=400, detail="Este item no usa control por rollos")
            if float(item['stock_actual']) < input.cantidad:
                raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {item['stock_actual']}")
        
        # Validar registro
        if input.registro_id:
            reg = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", input.registro_id)
            if not reg:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            
            # FASE 2C: Validar que OP no esté cerrada/anulada (incluso para salidas extra)
            if reg['estado'] in ('CERRADA', 'ANULADA'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"OP {reg['estado'].lower()}: no se puede crear salidas en una orden {reg['estado'].lower()}"
                )
        
        # NO validamos reserva - es salida extra
        
        costo_total = 0.0
        detalle_fifo = []
        
        if input.rollo_id:
            rollo = await conn.fetchrow("SELECT * FROM prod_inventario_rollos WHERE id = $1", input.rollo_id)
            ingreso = await conn.fetchrow("SELECT costo_unitario FROM prod_inventario_ingresos WHERE id = $1", rollo['ingreso_id'])
            costo_unitario = float(ingreso['costo_unitario']) if ingreso else 0
            costo_total = input.cantidad * costo_unitario
            detalle_fifo = [{"rollo_id": input.rollo_id, "cantidad": input.cantidad, "costo_unitario": costo_unitario}]
            await conn.execute("UPDATE prod_inventario_rollos SET metraje_disponible = metraje_disponible - $1 WHERE id = $2", input.cantidad, input.rollo_id)
            await conn.execute("UPDATE prod_inventario_ingresos SET cantidad_disponible = cantidad_disponible - $1 WHERE id = $2", input.cantidad, rollo['ingreso_id'])
        else:
            ingresos = await conn.fetch(
                "SELECT * FROM prod_inventario_ingresos WHERE item_id = $1 AND cantidad_disponible > 0 ORDER BY fecha ASC", input.item_id
            )
            cantidad_restante = input.cantidad
            for ing in ingresos:
                if cantidad_restante <= 0:
                    break
                disponible = float(ing['cantidad_disponible'])
                consumir = min(disponible, cantidad_restante)
                costo_unitario = float(ing['costo_unitario'])
                costo_total += consumir * costo_unitario
                detalle_fifo.append({"ingreso_id": ing['id'], "cantidad": consumir, "costo_unitario": costo_unitario})
                await conn.execute("UPDATE prod_inventario_ingresos SET cantidad_disponible = cantidad_disponible - $1 WHERE id = $2", consumir, ing['id'])
                cantidad_restante -= consumir
        
        salida_id = str(uuid.uuid4())
        fecha = datetime.now(timezone.utc)
        observaciones = f"[EXTRA] {input.motivo}. {input.observaciones}".strip()
        
        await conn.execute(
            """INSERT INTO prod_inventario_salidas (id, item_id, cantidad, registro_id, talla_id, observaciones, rollo_id, costo_total, detalle_fifo, fecha)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
            salida_id, input.item_id, input.cantidad, input.registro_id, input.talla_id, observaciones,
            input.rollo_id, costo_total, json.dumps(detalle_fifo), fecha.replace(tzinfo=None)
        )
        await conn.execute("UPDATE prod_inventario SET stock_actual = stock_actual - $1 WHERE id = $2", input.cantidad, input.item_id)
        
        # Actualizar requerimiento si existe (suma al consumido aunque no tenga reserva)
        if input.registro_id:
            if input.talla_id:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_consumida = cantidad_consumida + $1,
                        estado = CASE
                            WHEN cantidad_consumida + $1 >= cantidad_requerida THEN 'COMPLETO'
                            ELSE 'PARCIAL'
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id = $4
                """, input.cantidad, input.registro_id, input.item_id, input.talla_id)
            else:
                await conn.execute("""
                    UPDATE prod_registro_requerimiento_mp
                    SET cantidad_consumida = cantidad_consumida + $1,
                        estado = CASE
                            WHEN cantidad_consumida + $1 >= cantidad_requerida THEN 'COMPLETO'
                            ELSE 'PARCIAL'
                        END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE registro_id = $2 AND item_id = $3 AND talla_id IS NULL
                """, input.cantidad, input.registro_id, input.item_id)
        
        return {
            "id": salida_id,
            "item_id": input.item_id,
            "cantidad": input.cantidad,
            "costo_total": costo_total,
            "tipo": "EXTRA",
            "message": "Salida extra registrada"
        }


class SalidaUpdateData(BaseModel):
    observaciones: str = ""

@api_router.put("/inventario-salidas/{salida_id}")
async def update_salida(salida_id: str, input: SalidaUpdateData):
    pool = await get_pool()
    async with pool.acquire() as conn:
        salida = await conn.fetchrow("SELECT * FROM prod_inventario_salidas WHERE id = $1", salida_id)
        if not salida:
            raise HTTPException(status_code=404, detail="Salida no encontrada")
        await conn.execute("UPDATE prod_inventario_salidas SET observaciones=$1 WHERE id=$2", input.observaciones, salida_id)
        return {"message": "Salida actualizada"}

@api_router.delete("/inventario-salidas/{salida_id}")
async def delete_salida(salida_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        salida = await conn.fetchrow("SELECT * FROM prod_inventario_salidas WHERE id = $1", salida_id)
        if not salida:
            raise HTTPException(status_code=404, detail="Salida no encontrada")
        detalle_fifo = parse_jsonb(salida['detalle_fifo'])
        for detalle in detalle_fifo:
            if detalle.get('rollo_id'):
                await conn.execute("UPDATE prod_inventario_rollos SET metraje_disponible = metraje_disponible + $1 WHERE id = $2", detalle['cantidad'], detalle['rollo_id'])
                rollo = await conn.fetchrow("SELECT ingreso_id FROM prod_inventario_rollos WHERE id = $1", detalle['rollo_id'])
                if rollo:
                    await conn.execute("UPDATE prod_inventario_ingresos SET cantidad_disponible = cantidad_disponible + $1 WHERE id = $2", detalle['cantidad'], rollo['ingreso_id'])
            elif detalle.get('ingreso_id'):
                await conn.execute("UPDATE prod_inventario_ingresos SET cantidad_disponible = cantidad_disponible + $1 WHERE id = $2", detalle['cantidad'], detalle['ingreso_id'])
        await conn.execute("DELETE FROM prod_inventario_salidas WHERE id = $1", salida_id)
        await conn.execute("UPDATE prod_inventario SET stock_actual = stock_actual + $1 WHERE id = $2", float(salida['cantidad']), salida['item_id'])
        return {"message": "Salida eliminada y stock restaurado"}

# ==================== ENDPOINTS ROLLOS ====================

@api_router.get("/inventario-rollos")
async def get_rollos(item_id: str = None, activo: bool = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM prod_inventario_rollos WHERE 1=1"
        params = []
        if item_id:
            params.append(item_id)
            query += f" AND item_id = ${len(params)}"
        if activo is not None:
            params.append(activo)
            query += f" AND activo = ${len(params)}"
            if activo:
                query += " AND metraje_disponible > 0"
        query += " ORDER BY created_at DESC"
        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            d = row_to_dict(r)
            item = await conn.fetchrow("SELECT nombre, codigo FROM prod_inventario WHERE id = $1", d.get('item_id'))
            d['item_nombre'] = item['nombre'] if item else ""
            d['item_codigo'] = item['codigo'] if item else ""
            result.append(d)
        return result

@api_router.get("/inventario-rollos/{rollo_id}")
async def get_rollo(rollo_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rollo = await conn.fetchrow("SELECT * FROM prod_inventario_rollos WHERE id = $1", rollo_id)
        if not rollo:
            raise HTTPException(status_code=404, detail="Rollo no encontrado")
        d = row_to_dict(rollo)
        item = await conn.fetchrow("SELECT nombre, codigo FROM prod_inventario WHERE id = $1", d.get('item_id'))
        d['item_nombre'] = item['nombre'] if item else ""
        d['item_codigo'] = item['codigo'] if item else ""
        return d

# ==================== ENDPOINTS AJUSTES INVENTARIO ====================

@api_router.get("/inventario-ajustes")
async def get_ajustes():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM prod_inventario_ajustes ORDER BY fecha DESC")
        result = []
        for r in rows:
            d = row_to_dict(r)
            item = await conn.fetchrow("SELECT nombre, codigo FROM prod_inventario WHERE id = $1", d.get('item_id'))
            d['item_nombre'] = item['nombre'] if item else ""
            d['item_codigo'] = item['codigo'] if item else ""
            result.append(d)
        return result

@api_router.post("/inventario-ajustes")
async def create_ajuste(input: AjusteInventarioCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        item = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", input.item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")
        if input.tipo not in ["entrada", "salida"]:
            raise HTTPException(status_code=400, detail="Tipo debe ser 'entrada' o 'salida'")
        if input.tipo == "salida" and float(item['stock_actual']) < input.cantidad:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente. Disponible: {item['stock_actual']}")
        
        ajuste = AjusteInventario(**input.model_dump())
        await conn.execute(
            """INSERT INTO prod_inventario_ajustes (id, item_id, tipo, cantidad, motivo, observaciones, fecha)
               VALUES ($1,$2,$3,$4,$5,$6,$7)""",
            ajuste.id, ajuste.item_id, ajuste.tipo, ajuste.cantidad, ajuste.motivo, ajuste.observaciones, ajuste.fecha.replace(tzinfo=None)
        )
        incremento = input.cantidad if input.tipo == "entrada" else -input.cantidad
        await conn.execute("UPDATE prod_inventario SET stock_actual = stock_actual + $1 WHERE id = $2", incremento, input.item_id)
        return ajuste

class AjusteUpdateData(BaseModel):
    motivo: str = ""
    observaciones: str = ""

@api_router.put("/inventario-ajustes/{ajuste_id}")
async def update_ajuste(ajuste_id: str, input: AjusteUpdateData):
    pool = await get_pool()
    async with pool.acquire() as conn:
        ajuste = await conn.fetchrow("SELECT * FROM prod_inventario_ajustes WHERE id = $1", ajuste_id)
        if not ajuste:
            raise HTTPException(status_code=404, detail="Ajuste no encontrado")
        await conn.execute("UPDATE prod_inventario_ajustes SET motivo=$1, observaciones=$2 WHERE id=$3", 
                          input.motivo, input.observaciones, ajuste_id)
        return {"message": "Ajuste actualizado"}

@api_router.delete("/inventario-ajustes/{ajuste_id}")
async def delete_ajuste(ajuste_id: str):
    pool = await get_pool()
    async with pool.acquire() as conn:
        ajuste = await conn.fetchrow("SELECT * FROM prod_inventario_ajustes WHERE id = $1", ajuste_id)
        if not ajuste:
            raise HTTPException(status_code=404, detail="Ajuste no encontrado")
        incremento = -float(ajuste['cantidad']) if ajuste['tipo'] == "entrada" else float(ajuste['cantidad'])
        if ajuste['tipo'] == "entrada":
            item = await conn.fetchrow("SELECT stock_actual FROM prod_inventario WHERE id = $1", ajuste['item_id'])
            if item and float(item['stock_actual']) < float(ajuste['cantidad']):
                raise HTTPException(status_code=400, detail="No se puede eliminar: dejaría el stock negativo")
        await conn.execute("DELETE FROM prod_inventario_ajustes WHERE id = $1", ajuste_id)
        await conn.execute("UPDATE prod_inventario SET stock_actual = stock_actual + $1 WHERE id = $2", incremento, ajuste['item_id'])
        return {"message": "Ajuste eliminado"}

# ==================== ENDPOINTS MOVIMIENTOS PRODUCCION ====================

@api_router.get("/movimientos-produccion")
async def get_movimientos(registro_id: str = None, servicio_id: str = None, persona_id: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM prod_movimientos_produccion WHERE 1=1"
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
        query += " ORDER BY created_at DESC"
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
            # Convertir fechas a string
            if d.get('fecha_inicio'):
                d['fecha_inicio'] = str(d['fecha_inicio'])
            if d.get('fecha_fin'):
                d['fecha_fin'] = str(d['fecha_fin'])
            result.append(d)
        return result

@api_router.post("/movimientos-produccion")
async def create_movimiento(input: MovimientoCreate):
    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("SELECT id FROM prod_registros WHERE id = $1", input.registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        srv = await conn.fetchrow("SELECT id FROM prod_servicios_produccion WHERE id = $1", input.servicio_id)
        if not srv:
            raise HTTPException(status_code=404, detail="Servicio no encontrado")
        per = await conn.fetchrow("SELECT servicios FROM prod_personas_produccion WHERE id = $1", input.persona_id)
        if not per:
            raise HTTPException(status_code=404, detail="Persona no encontrada")
        
        # Calcular tarifa
        servicios = parse_jsonb(per['servicios'])
        tarifa = 0
        for s in servicios:
            if s.get('servicio_id') == input.servicio_id:
                tarifa = s.get('tarifa', 0)
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
        
        await conn.execute(
            """INSERT INTO prod_movimientos_produccion (id, registro_id, servicio_id, persona_id, cantidad_enviada, cantidad_recibida, diferencia, costo_calculado, fecha_inicio, fecha_fin, observaciones, created_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)""",
            movimiento.id, movimiento.registro_id, movimiento.servicio_id, movimiento.persona_id,
            movimiento.cantidad_enviada, movimiento.cantidad_recibida, diferencia, costo_calculado,
            fecha_inicio, fecha_fin, movimiento.observaciones, movimiento.created_at.replace(tzinfo=None)
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
        
        per = await conn.fetchrow("SELECT servicios FROM prod_personas_produccion WHERE id = $1", input.persona_id)
        servicios = parse_jsonb(per['servicios']) if per else []
        tarifa = 0
        for s in servicios:
            if s.get('servicio_id') == input.servicio_id:
                tarifa = s.get('tarifa', 0)
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
        
        await conn.execute(
            """UPDATE prod_movimientos_produccion SET registro_id=$1, servicio_id=$2, persona_id=$3, cantidad_enviada=$4, cantidad_recibida=$5, diferencia=$6, costo_calculado=$7, fecha_inicio=$8, fecha_fin=$9, observaciones=$10 WHERE id=$11""",
            input.registro_id, input.servicio_id, input.persona_id, input.cantidad_enviada, input.cantidad_recibida,
            diferencia, costo_calculado, fecha_inicio, fecha_fin, input.observaciones, movimiento_id
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
        
        return {**row_to_dict(result), **input.model_dump(), "diferencia": diferencia, "costo_calculado": costo_calculado}

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
            return {"message": "Guía actualizada", "guia": row_to_dict(updated), "updated": True}
        
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
        return {"message": "Guía creada", "guia": row_to_dict(guia), "updated": False}

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
        
        estados_count = {}
        for estado in ESTADOS_PRODUCCION:
            count = await conn.fetchval("SELECT COUNT(*) FROM prod_registros WHERE estado = $1", estado)
            estados_count[estado] = count
        
        return {
            "marcas": marcas, "tipos": tipos, "entalles": entalles, "telas": telas, "hilos": hilos,
            "modelos": modelos, "registros": registros, "registros_urgentes": registros_urgentes,
            "tallas": tallas, "colores": colores, "inventario": inventario,
            "ingresos_count": ingresos, "salidas_count": salidas, "ajustes_count": ajustes,
            "estados_count": estados_count
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
async def get_inventario_movimientos(item_id: str = None, fecha_inicio: str = None, fecha_fin: str = None):
    pool = await get_pool()
    async with pool.acquire() as conn:
        movimientos = []
        
        # Obtener ingresos
        query_ing = "SELECT * FROM prod_inventario_ingresos WHERE 1=1"
        params_ing = []
        if item_id:
            params_ing.append(item_id)
            query_ing += f" AND item_id = ${len(params_ing)}"
        if fecha_inicio:
            params_ing.append(fecha_inicio)
            query_ing += f" AND fecha >= ${len(params_ing)}::timestamp"
        if fecha_fin:
            params_ing.append(fecha_fin)
            query_ing += f" AND fecha <= ${len(params_ing)}::timestamp"
        
        ingresos = await conn.fetch(query_ing, *params_ing)
        for ing in ingresos:
            item = await conn.fetchrow("SELECT nombre, codigo FROM prod_inventario WHERE id = $1", ing['item_id'])
            movimientos.append({
                "id": ing['id'],
                "tipo": "ingreso",
                "item_id": ing['item_id'],
                "item_nombre": item['nombre'] if item else "",
                "item_codigo": item['codigo'] if item else "",
                "cantidad": float(ing['cantidad']),
                "costo_unitario": float(ing['costo_unitario']),
                "costo_total": float(ing['cantidad']) * float(ing['costo_unitario']),
                "fecha": ing['fecha'],
                "proveedor": ing['proveedor'],
                "numero_documento": ing['numero_documento'],
                "observaciones": ing['observaciones']
            })
        
        # Obtener salidas
        query_sal = "SELECT * FROM prod_inventario_salidas WHERE 1=1"
        params_sal = []
        if item_id:
            params_sal.append(item_id)
            query_sal += f" AND item_id = ${len(params_sal)}"
        if fecha_inicio:
            params_sal.append(fecha_inicio)
            query_sal += f" AND fecha >= ${len(params_sal)}::timestamp"
        if fecha_fin:
            params_sal.append(fecha_fin)
            query_sal += f" AND fecha <= ${len(params_sal)}::timestamp"
        
        salidas = await conn.fetch(query_sal, *params_sal)
        for sal in salidas:
            item = await conn.fetchrow("SELECT nombre, codigo FROM prod_inventario WHERE id = $1", sal['item_id'])
            registro = None
            if sal['registro_id']:
                registro = await conn.fetchrow("SELECT n_corte FROM prod_registros WHERE id = $1", sal['registro_id'])
            movimientos.append({
                "id": sal['id'],
                "tipo": "salida",
                "item_id": sal['item_id'],
                "item_nombre": item['nombre'] if item else "",
                "item_codigo": item['codigo'] if item else "",
                "cantidad": float(sal['cantidad']),
                "costo_unitario": 0,
                "costo_total": float(sal['costo_total']),
                "fecha": sal['fecha'],
                "registro_id": sal['registro_id'],
                "registro_n_corte": registro['n_corte'] if registro else None,
                "observaciones": sal['observaciones']
            })
        
        # Obtener ajustes
        query_aj = "SELECT * FROM prod_inventario_ajustes WHERE 1=1"
        params_aj = []
        if item_id:
            params_aj.append(item_id)
            query_aj += f" AND item_id = ${len(params_aj)}"
        if fecha_inicio:
            params_aj.append(fecha_inicio)
            query_aj += f" AND fecha >= ${len(params_aj)}::timestamp"
        if fecha_fin:
            params_aj.append(fecha_fin)
            query_aj += f" AND fecha <= ${len(params_aj)}::timestamp"
        
        ajustes = await conn.fetch(query_aj, *params_aj)
        for aj in ajustes:
            item = await conn.fetchrow("SELECT nombre, codigo FROM prod_inventario WHERE id = $1", aj['item_id'])
            movimientos.append({
                "id": aj['id'],
                "tipo": f"ajuste_{aj['tipo']}",
                "item_id": aj['item_id'],
                "item_nombre": item['nombre'] if item else "",
                "item_codigo": item['codigo'] if item else "",
                "cantidad": float(aj['cantidad']),
                "costo_unitario": 0,
                "costo_total": 0,
                "fecha": aj['fecha'],
                "motivo": aj['motivo'],
                "observaciones": aj['observaciones']
            })
        
        # Ordenar por fecha
        movimientos.sort(key=lambda x: x['fecha'] if x['fecha'] else datetime.min, reverse=True)
        return movimientos

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
            if sal['registro_id']:
                registro = await conn.fetchrow("SELECT n_corte FROM prod_registros WHERE id = $1", sal['registro_id'])
            movimientos.append({
                "id": sal['id'],
                "tipo": "salida",
                "fecha": sal['fecha'],
                "cantidad": -float(sal['cantidad']),
                "costo_unitario": 0,
                "costo_total": float(sal['costo_total']),
                "registro_id": sal['registro_id'],
                "registro_n_corte": registro['n_corte'] if registro else None,
                "observaciones": sal['observaciones']
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
                       r.curva
                FROM prod_registros r
                LEFT JOIN prod_modelos m ON r.modelo_id = m.id
                LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
                LEFT JOIN prod_tipos t ON m.tipo_id = t.id
                ORDER BY r.fecha_creacion DESC
            """,
            "headers": ["N° Corte", "Fecha", "Estado", "Urgente", "Modelo", "Marca", "Tipo", "Curva"]
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

# ==================== STARTUP/SHUTDOWN ====================

@app.on_event("startup")
async def startup():
    await get_pool()
    await ensure_bom_tables()
    await ensure_fase2_tables()
    # Eliminar columna materiales obsoleta
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("ALTER TABLE prod_modelos DROP COLUMN IF EXISTS materiales")

@app.on_event("shutdown")
async def shutdown():
    global pool
    if pool:
        await pool.close()

# ==================== CORS & ROUTER ====================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)
