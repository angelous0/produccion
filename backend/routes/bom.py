"""
Router BOM (Bill of Materials) - Cabecera + Detalle
Propósito: definir materiales estándar por modelo, estimar consumo, generar requerimiento MP.
El BOM NO reemplaza el consumo real ni el costo real de cierre.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from uuid import uuid4
from db import get_pool

router = APIRouter(prefix="/api/bom", tags=["BOM"])


# ==================== PYDANTIC MODELS ====================

class BomCabeceraCreate(BaseModel):
    modelo_id: str
    codigo: Optional[str] = None
    version: int = 1
    observaciones: Optional[str] = None

class BomCabeceraUpdate(BaseModel):
    estado: Optional[str] = None  # BORRADOR, APROBADO, INACTIVO
    observaciones: Optional[str] = None
    vigente_desde: Optional[str] = None
    vigente_hasta: Optional[str] = None

class BomLineaCreate(BaseModel):
    inventario_id: str
    tipo_componente: str = "TELA"  # TELA, AVIO, SERVICIO, EMPAQUE, OTRO
    talla_id: Optional[str] = None
    etapa_id: Optional[str] = None
    cantidad_base: float
    merma_pct: float = 0.0
    es_opcional: bool = False
    observaciones: Optional[str] = None

class BomLineaUpdate(BaseModel):
    inventario_id: Optional[str] = None
    tipo_componente: Optional[str] = None
    talla_id: Optional[str] = None
    etapa_id: Optional[str] = None
    cantidad_base: Optional[float] = None
    merma_pct: Optional[float] = None
    es_opcional: Optional[bool] = None
    observaciones: Optional[str] = None
    activo: Optional[bool] = None


# ==================== HELPERS ====================

def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    from datetime import datetime
    from decimal import Decimal
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
        elif isinstance(v, Decimal):
            d[k] = float(v)
    return d

TIPOS_COMPONENTE = ["TELA", "AVIO", "SERVICIO", "EMPAQUE", "OTRO"]
ESTADOS_BOM = ["BORRADOR", "APROBADO", "INACTIVO"]


# ==================== CABECERA ====================

@router.get("")
async def list_bom_cabeceras(modelo_id: str = Query(...), estado: Optional[str] = None):
    """Lista BOMs de un modelo."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        q = """
            SELECT bc.*, m.nombre as modelo_nombre,
                   (SELECT COUNT(*) FROM prod_modelo_bom_linea bl WHERE bl.bom_id = bc.id AND bl.activo = true) as total_lineas
            FROM prod_bom_cabecera bc
            LEFT JOIN prod_modelos m ON bc.modelo_id = m.id
            WHERE bc.modelo_id = $1
        """
        params = [modelo_id]
        if estado:
            q += " AND bc.estado = $2"
            params.append(estado)
        q += " ORDER BY bc.version DESC"
        rows = await conn.fetch(q, *params)
    return [row_to_dict(r) for r in rows]


@router.post("")
async def create_bom_cabecera(data: BomCabeceraCreate):
    """Crea una nueva cabecera BOM para un modelo."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verificar modelo existe
        modelo = await conn.fetchrow("SELECT id, nombre FROM prod_modelos WHERE id = $1", data.modelo_id)
        if not modelo:
            raise HTTPException(status_code=404, detail="Modelo no encontrado")

        # Auto-calcular version
        max_ver = await conn.fetchval(
            "SELECT COALESCE(MAX(version), 0) FROM prod_bom_cabecera WHERE modelo_id = $1",
            data.modelo_id
        )
        version = (max_ver or 0) + 1

        codigo = data.codigo or f"BOM-{modelo['nombre'][:10].upper().replace(' ','-')}-V{version}"
        new_id = str(uuid4())

        await conn.execute("""
            INSERT INTO prod_bom_cabecera (id, modelo_id, codigo, version, estado, observaciones, created_at, updated_at)
            VALUES ($1, $2, $3, $4, 'BORRADOR', $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, new_id, data.modelo_id, codigo, version, data.observaciones)

        row = await conn.fetchrow("""
            SELECT bc.*, m.nombre as modelo_nombre
            FROM prod_bom_cabecera bc
            LEFT JOIN prod_modelos m ON bc.modelo_id = m.id
            WHERE bc.id = $1
        """, new_id)

    return row_to_dict(row)


@router.get("/{bom_id}")
async def get_bom_detalle(bom_id: str):
    """Obtiene cabecera BOM con todas sus líneas."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        cab = await conn.fetchrow("""
            SELECT bc.*, m.nombre as modelo_nombre
            FROM prod_bom_cabecera bc
            LEFT JOIN prod_modelos m ON bc.modelo_id = m.id
            WHERE bc.id = $1
        """, bom_id)
        if not cab:
            raise HTTPException(status_code=404, detail="BOM no encontrado")

        lineas = await conn.fetch("""
            SELECT bl.*, i.nombre as inventario_nombre, i.codigo as inventario_codigo,
                   i.tipo_item as inventario_tipo, i.unidad_medida as inventario_unidad,
                   tc.nombre as talla_nombre,
                   et.nombre as etapa_nombre
            FROM prod_modelo_bom_linea bl
            LEFT JOIN prod_inventario i ON bl.inventario_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON bl.talla_id = tc.id
            LEFT JOIN prod_orden_etapa et ON bl.etapa_id = et.id
            WHERE bl.bom_id = $1
            ORDER BY bl.orden ASC, bl.created_at ASC
        """, bom_id)

    cab_dict = row_to_dict(cab)
    cab_dict["lineas"] = [row_to_dict(l) for l in lineas]
    return cab_dict


@router.put("/{bom_id}")
async def update_bom_cabecera(bom_id: str, data: BomCabeceraUpdate):
    """Actualiza estado/observaciones de la cabecera BOM."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        cab = await conn.fetchrow("SELECT * FROM prod_bom_cabecera WHERE id = $1", bom_id)
        if not cab:
            raise HTTPException(status_code=404, detail="BOM no encontrado")

        estado = data.estado if data.estado else cab['estado']
        if estado not in ESTADOS_BOM:
            raise HTTPException(status_code=400, detail=f"Estado inválido. Permitidos: {ESTADOS_BOM}")

        obs = data.observaciones if data.observaciones is not None else cab['observaciones']
        vigente_desde = data.vigente_desde or (cab['vigente_desde'].isoformat() if cab['vigente_desde'] else None)
        vigente_hasta = data.vigente_hasta or (cab['vigente_hasta'].isoformat() if cab['vigente_hasta'] else None)

        await conn.execute("""
            UPDATE prod_bom_cabecera
            SET estado = $1, observaciones = $2,
                vigente_desde = $3::timestamp, vigente_hasta = $4::timestamp,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $5
        """, estado, obs, vigente_desde, vigente_hasta, bom_id)

        row = await conn.fetchrow("""
            SELECT bc.*, m.nombre as modelo_nombre
            FROM prod_bom_cabecera bc
            LEFT JOIN prod_modelos m ON bc.modelo_id = m.id
            WHERE bc.id = $1
        """, bom_id)
    return row_to_dict(row)


# ==================== LÍNEAS ====================

@router.post("/{bom_id}/lineas")
async def add_bom_linea(bom_id: str, data: BomLineaCreate):
    """Agrega una línea al BOM."""
    if data.cantidad_base <= 0:
        raise HTTPException(status_code=400, detail="cantidad_base debe ser mayor a 0")
    if data.tipo_componente not in TIPOS_COMPONENTE:
        raise HTTPException(status_code=400, detail=f"tipo_componente inválido. Permitidos: {TIPOS_COMPONENTE}")
    if data.merma_pct < 0 or data.merma_pct > 100:
        raise HTTPException(status_code=400, detail="merma_pct debe estar entre 0 y 100")

    pool = await get_pool()
    async with pool.acquire() as conn:
        # Verificar BOM existe
        cab = await conn.fetchrow("SELECT * FROM prod_bom_cabecera WHERE id = $1", bom_id)
        if not cab:
            raise HTTPException(status_code=404, detail="BOM no encontrado")

        # Verificar inventario existe
        inv = await conn.fetchrow("SELECT * FROM prod_inventario WHERE id = $1", data.inventario_id)
        if not inv:
            raise HTTPException(status_code=404, detail="Item de inventario no encontrado")

        # Calcular cantidad_total
        cantidad_total = round(data.cantidad_base * (1 + data.merma_pct / 100), 4)

        new_id = str(uuid4())
        await conn.execute("""
            INSERT INTO prod_modelo_bom_linea
                (id, bom_id, modelo_id, inventario_id, tipo_componente, talla_id, etapa_id,
                 unidad_base, cantidad_base, merma_pct, cantidad_total, es_opcional,
                 observaciones, orden, activo, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7,
                    'PRENDA', $8, $9, $10, $11,
                    $12, 10, true, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, new_id, bom_id, cab['modelo_id'], data.inventario_id, data.tipo_componente,
            data.talla_id, data.etapa_id,
            float(data.cantidad_base), float(data.merma_pct), cantidad_total, data.es_opcional,
            data.observaciones)

        row = await conn.fetchrow("""
            SELECT bl.*, i.nombre as inventario_nombre, i.codigo as inventario_codigo,
                   i.tipo_item as inventario_tipo, i.unidad_medida as inventario_unidad,
                   tc.nombre as talla_nombre, et.nombre as etapa_nombre
            FROM prod_modelo_bom_linea bl
            LEFT JOIN prod_inventario i ON bl.inventario_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON bl.talla_id = tc.id
            LEFT JOIN prod_orden_etapa et ON bl.etapa_id = et.id
            WHERE bl.id = $1
        """, new_id)

    return row_to_dict(row)


@router.put("/{bom_id}/lineas/{linea_id}")
async def update_bom_linea(bom_id: str, linea_id: str, data: BomLineaUpdate):
    """Actualiza una línea del BOM."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        bl = await conn.fetchrow(
            "SELECT * FROM prod_modelo_bom_linea WHERE id = $1 AND bom_id = $2",
            linea_id, bom_id
        )
        if not bl:
            raise HTTPException(status_code=404, detail="Línea BOM no encontrada")

        inv_id = data.inventario_id if data.inventario_id is not None else bl['inventario_id']
        tipo = data.tipo_componente if data.tipo_componente is not None else (bl.get('tipo_componente') or 'TELA')
        talla_id = data.talla_id if data.talla_id is not None else bl.get('talla_id')
        etapa_id = data.etapa_id if data.etapa_id is not None else bl.get('etapa_id')
        cant_base = float(data.cantidad_base) if data.cantidad_base is not None else float(bl['cantidad_base'])
        merma = float(data.merma_pct) if data.merma_pct is not None else float(bl.get('merma_pct') or 0)
        es_opc = data.es_opcional if data.es_opcional is not None else bool(bl.get('es_opcional') or False)
        obs = data.observaciones if data.observaciones is not None else bl.get('observaciones')
        activo = data.activo if data.activo is not None else bl['activo']

        if tipo not in TIPOS_COMPONENTE:
            raise HTTPException(status_code=400, detail=f"tipo_componente inválido. Permitidos: {TIPOS_COMPONENTE}")
        if cant_base <= 0:
            raise HTTPException(status_code=400, detail="cantidad_base debe ser mayor a 0")
        if merma < 0 or merma > 100:
            raise HTTPException(status_code=400, detail="merma_pct debe estar entre 0 y 100")

        cantidad_total = round(cant_base * (1 + merma / 100), 4)

        await conn.execute("""
            UPDATE prod_modelo_bom_linea
            SET inventario_id = $1, tipo_componente = $2, talla_id = $3, etapa_id = $4,
                cantidad_base = $5, merma_pct = $6, cantidad_total = $7, es_opcional = $8,
                observaciones = $9, activo = $10, updated_at = CURRENT_TIMESTAMP
            WHERE id = $11
        """, inv_id, tipo, talla_id, etapa_id, cant_base, merma, cantidad_total,
            es_opc, obs, activo, linea_id)

        row = await conn.fetchrow("""
            SELECT bl.*, i.nombre as inventario_nombre, i.codigo as inventario_codigo,
                   i.tipo_item as inventario_tipo, i.unidad_medida as inventario_unidad,
                   tc.nombre as talla_nombre, et.nombre as etapa_nombre
            FROM prod_modelo_bom_linea bl
            LEFT JOIN prod_inventario i ON bl.inventario_id = i.id
            LEFT JOIN prod_tallas_catalogo tc ON bl.talla_id = tc.id
            LEFT JOIN prod_orden_etapa et ON bl.etapa_id = et.id
            WHERE bl.id = $1
        """, linea_id)

    return row_to_dict(row)


@router.delete("/{bom_id}/lineas/{linea_id}")
async def delete_bom_linea(bom_id: str, linea_id: str):
    """Elimina o desactiva una línea del BOM."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        bl = await conn.fetchrow(
            "SELECT * FROM prod_modelo_bom_linea WHERE id = $1 AND bom_id = $2",
            linea_id, bom_id
        )
        if not bl:
            raise HTTPException(status_code=404, detail="Línea BOM no encontrada")

        await conn.execute("DELETE FROM prod_modelo_bom_linea WHERE id = $1", linea_id)
    return {"action": "deleted", "message": "Línea eliminada"}


# ==================== COSTO ESTÁNDAR ====================

@router.get("/{bom_id}/costo-estandar")
async def get_bom_costo_estandar(bom_id: str, cantidad_prendas: int = Query(1, ge=1)):
    """Calcula el costo estándar de un BOM basado en precios actuales de inventario.
    El costo estándar es REFERENCIAL, no reemplaza el costo real de producción."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        cab = await conn.fetchrow("SELECT * FROM prod_bom_cabecera WHERE id = $1", bom_id)
        if not cab:
            raise HTTPException(status_code=404, detail="BOM no encontrado")

        lineas = await conn.fetch("""
            SELECT bl.*, i.nombre as inventario_nombre, i.codigo as inventario_codigo,
                   i.costo_promedio as precio_unitario, i.unidad_medida as inventario_unidad,
                   i.tipo_item as inventario_tipo
            FROM prod_modelo_bom_linea bl
            LEFT JOIN prod_inventario i ON bl.inventario_id = i.id
            WHERE bl.bom_id = $1 AND bl.activo = true
            ORDER BY bl.tipo_componente, bl.orden
        """, bom_id)

    detalle = []
    total_por_tipo = {}
    total_general = 0.0

    for l in lineas:
        ld = row_to_dict(l)
        precio = float(ld.get('precio_unitario') or 0)
        cant_total = float(ld.get('cantidad_total') or ld.get('cantidad_base', 0))
        costo_unitario = round(cant_total * precio, 4)
        costo_lote = round(costo_unitario * cantidad_prendas, 2)
        tipo = ld.get('tipo_componente') or 'OTRO'

        item = {
            "linea_id": ld['id'],
            "inventario_codigo": ld.get('inventario_codigo'),
            "inventario_nombre": ld.get('inventario_nombre'),
            "tipo_componente": tipo,
            "cantidad_base": float(ld.get('cantidad_base', 0)),
            "merma_pct": float(ld.get('merma_pct') or 0),
            "cantidad_total": cant_total,
            "precio_unitario": precio,
            "costo_por_prenda": costo_unitario,
            "costo_lote": costo_lote,
            "es_opcional": ld.get('es_opcional', False),
        }
        detalle.append(item)

        if tipo not in total_por_tipo:
            total_por_tipo[tipo] = 0.0
        total_por_tipo[tipo] += costo_unitario
        if not item['es_opcional']:
            total_general += costo_unitario

    return {
        "bom_id": bom_id,
        "modelo_id": row_to_dict(cab)['modelo_id'],
        "version": row_to_dict(cab)['version'],
        "estado": row_to_dict(cab)['estado'],
        "cantidad_prendas": cantidad_prendas,
        "costo_estandar_unitario": round(total_general, 4),
        "costo_estandar_lote": round(total_general * cantidad_prendas, 2),
        "costo_por_tipo": {k: round(v, 4) for k, v in total_por_tipo.items()},
        "detalle": detalle,
    }


# ==================== DUPLICAR BOM ====================

@router.post("/{bom_id}/duplicar")
async def duplicar_bom(bom_id: str):
    """Crea una nueva versión del BOM copiando todas las líneas activas."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        cab = await conn.fetchrow("SELECT * FROM prod_bom_cabecera WHERE id = $1", bom_id)
        if not cab:
            raise HTTPException(status_code=404, detail="BOM no encontrado")

        modelo_id = cab['modelo_id']
        max_ver = await conn.fetchval(
            "SELECT COALESCE(MAX(version), 0) FROM prod_bom_cabecera WHERE modelo_id = $1", modelo_id
        )
        new_ver = (max_ver or 0) + 1
        new_cab_id = str(uuid4())
        new_codigo = f"{cab['codigo'].rsplit('-V', 1)[0]}-V{new_ver}" if '-V' in (cab['codigo'] or '') else f"BOM-V{new_ver}"

        await conn.execute("""
            INSERT INTO prod_bom_cabecera (id, modelo_id, codigo, version, estado, observaciones, created_at, updated_at)
            VALUES ($1, $2, $3, $4, 'BORRADOR', $5, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, new_cab_id, modelo_id, new_codigo, new_ver,
            f"Duplicado de v{cab['version']}")

        # Copiar líneas activas
        lineas = await conn.fetch(
            "SELECT * FROM prod_modelo_bom_linea WHERE bom_id = $1 AND activo = true", bom_id
        )
        for l in lineas:
            new_linea_id = str(uuid4())
            await conn.execute("""
                INSERT INTO prod_modelo_bom_linea
                    (id, bom_id, modelo_id, inventario_id, tipo_componente, talla_id, etapa_id,
                     unidad_base, cantidad_base, merma_pct, cantidad_total, es_opcional,
                     observaciones, orden, activo, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7,
                        $8, $9, $10, $11, $12, $13, $14, true,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, new_linea_id, new_cab_id, modelo_id, l['inventario_id'],
                l.get('tipo_componente') or 'TELA', l.get('talla_id'), l.get('etapa_id'),
                l.get('unidad_base') or 'PRENDA', float(l['cantidad_base']),
                float(l.get('merma_pct') or 0), float(l.get('cantidad_total') or l['cantidad_base']),
                bool(l.get('es_opcional') or False), l.get('observaciones'),
                l.get('orden') or 10)

        row = await conn.fetchrow("""
            SELECT bc.*, m.nombre as modelo_nombre,
                   (SELECT COUNT(*) FROM prod_modelo_bom_linea bl WHERE bl.bom_id = bc.id AND bl.activo = true) as total_lineas
            FROM prod_bom_cabecera bc
            LEFT JOIN prod_modelos m ON bc.modelo_id = m.id
            WHERE bc.id = $1
        """, new_cab_id)

    return row_to_dict(row)
