"""
Router: Trazabilidad Unificada de Lotes
- Fallados (detección, clasificación, destino no reparables)
- Arreglos (envío, retorno, resultado)
- Resumen de cantidades por lote
- Trazabilidad completa (timeline unificado)
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
import json, uuid

router = APIRouter(prefix="/api", tags=["trazabilidad"])

import sys
sys.path.insert(0, '/app/backend')
from db import get_pool
from auth import get_current_user
from helpers import row_to_dict


def safe_int(v):
    try: return int(v or 0)
    except (ValueError, TypeError): return 0

def safe_float(v):
    try: return float(v or 0)
    except (ValueError, TypeError): return 0.0

def parse_jsonb(val):
    if val is None: return []
    if isinstance(val, list): return val
    if isinstance(val, str):
        try: return json.loads(val)
        except (ValueError, json.JSONDecodeError): return []
    return val

DIAS_LIMITE_ARREGLO = 3


# ==================== INIT TABLES ====================

async def init_trazabilidad_tables():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_fallados (
                id VARCHAR PRIMARY KEY,
                registro_id VARCHAR NOT NULL,
                movimiento_id VARCHAR,
                servicio_detectado_id VARCHAR,
                cantidad_detectada INT NOT NULL DEFAULT 0,
                cantidad_reparable INT NOT NULL DEFAULT 0,
                cantidad_no_reparable INT NOT NULL DEFAULT 0,
                destino_no_reparable VARCHAR DEFAULT 'PENDIENTE',
                motivo TEXT,
                fecha_deteccion DATE,
                estado VARCHAR DEFAULT 'ABIERTO',
                observaciones TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS prod_arreglos (
                id VARCHAR PRIMARY KEY,
                fallado_id VARCHAR NOT NULL,
                registro_id VARCHAR NOT NULL,
                cantidad_enviada INT NOT NULL DEFAULT 0,
                cantidad_resuelta INT NOT NULL DEFAULT 0,
                cantidad_no_resuelta INT NOT NULL DEFAULT 0,
                tipo VARCHAR NOT NULL DEFAULT 'ARREGLO_INTERNO',
                servicio_destino_id VARCHAR,
                persona_destino_id VARCHAR,
                fecha_envio DATE,
                fecha_limite DATE,
                fecha_retorno DATE,
                resultado_final VARCHAR DEFAULT 'PENDIENTE',
                estado VARCHAR DEFAULT 'PENDIENTE',
                observaciones TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            )
        """)
        await conn.execute("ALTER TABLE prod_mermas ADD COLUMN IF NOT EXISTS tipo VARCHAR DEFAULT 'FALTANTE'")
        await conn.execute("ALTER TABLE prod_arreglos ADD COLUMN IF NOT EXISTS motivo TEXT")
        await conn.execute("ALTER TABLE prod_arreglos ADD COLUMN IF NOT EXISTS motivo_no_resuelta TEXT")


# ==================== MODELS ====================

class FalladoCreate(BaseModel):
    registro_id: str
    movimiento_id: Optional[str] = None
    servicio_detectado_id: Optional[str] = None
    cantidad_detectada: int
    cantidad_reparable: int = 0
    cantidad_no_reparable: int = 0
    destino_no_reparable: str = "PENDIENTE"
    motivo: str = ""
    fecha_deteccion: Optional[str] = None
    observaciones: str = ""

class FalladoUpdate(BaseModel):
    cantidad_detectada: Optional[int] = None
    cantidad_reparable: Optional[int] = None
    cantidad_no_reparable: Optional[int] = None
    destino_no_reparable: Optional[str] = None
    motivo: Optional[str] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None
    fecha_deteccion: Optional[str] = None
    servicio_detectado_id: Optional[str] = None

class ArregloCreate(BaseModel):
    fallado_id: str
    registro_id: str
    cantidad_enviada: int
    tipo: str = "ARREGLO_INTERNO"
    servicio_destino_id: Optional[str] = None
    persona_destino_id: Optional[str] = None
    fecha_envio: Optional[str] = None
    motivo: str = ""
    observaciones: str = ""

class ArregloCierre(BaseModel):
    fecha_retorno: Optional[str] = None
    cantidad_resuelta: int = 0
    cantidad_no_resuelta: int = 0
    resultado_final: str = "BUENO"
    motivo_no_resuelta: Optional[str] = None
    observaciones: Optional[str] = None

class ArregloUpdate(BaseModel):
    cantidad_enviada: Optional[int] = None
    tipo: Optional[str] = None
    servicio_destino_id: Optional[str] = None
    persona_destino_id: Optional[str] = None
    fecha_envio: Optional[str] = None
    motivo: Optional[str] = None
    observaciones: Optional[str] = None

class LiquidacionDirecta(BaseModel):
    fallado_id: str
    registro_id: str
    cantidad: int
    destino: str = "LIQUIDACION"
    motivo: str = ""


# ==================== FALLADOS CRUD ====================

@router.get("/fallados")
async def get_fallados(
    registro_id: Optional[str] = None,
    estado: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT f.*,
                   sp.nombre as servicio_detectado_nombre,
                   r.n_corte as registro_n_corte
            FROM prod_fallados f
            LEFT JOIN prod_servicios_produccion sp ON f.servicio_detectado_id = sp.id
            LEFT JOIN prod_registros r ON f.registro_id = r.id
            WHERE 1=1
        """
        params = []
        if registro_id:
            params.append(registro_id)
            query += f" AND f.registro_id = ${len(params)}"
        if estado:
            params.append(estado)
            query += f" AND f.estado = ${len(params)}"
        query += " ORDER BY f.created_at DESC"
        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            d = row_to_dict(r)
            for f in ("fecha_deteccion", "created_at"):
                if d.get(f): d[f] = str(d[f])
            result.append(d)
        return result


@router.post("/fallados")
async def create_fallado(
    input: FalladoCreate,
    current_user: dict = Depends(get_current_user),
):
    if input.cantidad_reparable + input.cantidad_no_reparable > input.cantidad_detectada:
        raise HTTPException(status_code=400, detail="Reparable + No reparable no puede exceder cantidad detectada")

    pool = await get_pool()
    async with pool.acquire() as conn:
        fid = str(uuid.uuid4())
        # Convert fecha_deteccion string to date object for asyncpg
        fecha_str = input.fecha_deteccion or str(date.today())
        fecha = date.fromisoformat(fecha_str[:10]) if fecha_str else date.today()
        await conn.execute("""
            INSERT INTO prod_fallados (id, registro_id, movimiento_id, servicio_detectado_id,
                cantidad_detectada, cantidad_reparable, cantidad_no_reparable, destino_no_reparable,
                motivo, fecha_deteccion, estado, observaciones)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        """, fid, input.registro_id, input.movimiento_id, input.servicio_detectado_id,
            input.cantidad_detectada, input.cantidad_reparable, input.cantidad_no_reparable,
            input.destino_no_reparable, input.motivo, fecha, 'ABIERTO', input.observaciones)
        return {"id": fid, "message": "Fallado registrado"}


@router.put("/fallados/{fallado_id}")
async def update_fallado(
    fallado_id: str,
    input: FalladoUpdate,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM prod_fallados WHERE id = $1", fallado_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Fallado no encontrado")

        det = input.cantidad_detectada if input.cantidad_detectada is not None else existing["cantidad_detectada"]
        rep = input.cantidad_reparable if input.cantidad_reparable is not None else existing["cantidad_reparable"]
        norep = input.cantidad_no_reparable if input.cantidad_no_reparable is not None else existing["cantidad_no_reparable"]
        if rep + norep > det:
            raise HTTPException(status_code=400, detail="Reparable + No reparable no puede exceder cantidad detectada")

        sets = []
        params = []
        for field, val in [
            ("cantidad_detectada", input.cantidad_detectada),
            ("cantidad_reparable", input.cantidad_reparable),
            ("cantidad_no_reparable", input.cantidad_no_reparable),
            ("destino_no_reparable", input.destino_no_reparable),
            ("motivo", input.motivo),
            ("estado", input.estado),
            ("observaciones", input.observaciones),
            ("servicio_detectado_id", input.servicio_detectado_id),
        ]:
            if val is not None:
                params.append(val)
                sets.append(f"{field} = ${len(params)}")

        if input.fecha_deteccion is not None:
            from datetime import date as date_type
            params.append(date_type.fromisoformat(input.fecha_deteccion))
            sets.append(f"fecha_deteccion = ${len(params)}")

        if sets:
            params.append(fallado_id)
            await conn.execute(f"UPDATE prod_fallados SET {', '.join(sets)} WHERE id = ${len(params)}", *params)

        return {"message": "Fallado actualizado"}


@router.delete("/fallados/{fallado_id}")
async def delete_fallado(
    fallado_id: str,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_arreglos WHERE fallado_id = $1", fallado_id)
        await conn.execute("DELETE FROM prod_fallados WHERE id = $1", fallado_id)
        return {"message": "Fallado eliminado"}


# ==================== ARREGLOS CRUD ====================

@router.get("/arreglos")
async def get_arreglos(
    registro_id: Optional[str] = None,
    fallado_id: Optional[str] = None,
    estado: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT a.*,
                   sp.nombre as servicio_destino_nombre,
                   pp.nombre as persona_destino_nombre
            FROM prod_arreglos a
            LEFT JOIN prod_servicios_produccion sp ON a.servicio_destino_id = sp.id
            LEFT JOIN prod_personas_produccion pp ON a.persona_destino_id = pp.id
            WHERE 1=1
        """
        params = []
        if registro_id:
            params.append(registro_id)
            query += f" AND a.registro_id = ${len(params)}"
        if fallado_id:
            params.append(fallado_id)
            query += f" AND a.fallado_id = ${len(params)}"
        if estado:
            params.append(estado)
            query += f" AND a.estado = ${len(params)}"
        query += " ORDER BY a.created_at DESC"
        rows = await conn.fetch(query, *params)
        result = []
        for r in rows:
            d = row_to_dict(r)
            for f in ("fecha_envio", "fecha_limite", "fecha_retorno", "created_at"):
                if d.get(f): d[f] = str(d[f])
            # Mark as vencido if past limit
            if d.get("estado") == "PENDIENTE" and d.get("fecha_limite"):
                try:
                    lim = date.fromisoformat(str(d["fecha_limite"])[:10])
                    if lim < date.today() and not d.get("fecha_retorno"):
                        d["vencido"] = True
                except (ValueError, TypeError):
                    pass
            result.append(d)
        return result


@router.post("/arreglos")
async def create_arreglo(
    input: ArregloCreate,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        fallado = await conn.fetchrow("SELECT * FROM prod_fallados WHERE id = $1", input.fallado_id)
        if not fallado:
            raise HTTPException(status_code=404, detail="Fallado no encontrado")

        # Validate: sum of arreglos.cantidad_enviada <= fallado.cantidad_detectada
        existing_sum = await conn.fetchval(
            "SELECT COALESCE(SUM(cantidad_enviada),0) FROM prod_arreglos WHERE fallado_id = $1",
            input.fallado_id
        )
        disponible = fallado["cantidad_detectada"] - safe_int(existing_sum)
        if input.cantidad_enviada > disponible:
            raise HTTPException(status_code=400, detail=f"Cantidad excede disponible ({disponible} de {fallado['cantidad_detectada']})")

        aid = str(uuid.uuid4())
        # Convert fecha_envio string to date object for asyncpg
        fecha_envio_str = input.fecha_envio or str(date.today())
        fecha_envio = date.fromisoformat(fecha_envio_str[:10]) if fecha_envio_str else date.today()
        fecha_limite = fecha_envio + timedelta(days=DIAS_LIMITE_ARREGLO)

        await conn.execute("""
            INSERT INTO prod_arreglos (id, fallado_id, registro_id, cantidad_enviada,
                tipo, servicio_destino_id, persona_destino_id,
                fecha_envio, fecha_limite, estado, motivo, observaciones)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)
        """, aid, input.fallado_id, input.registro_id, input.cantidad_enviada,
            input.tipo, input.servicio_destino_id, input.persona_destino_id,
            fecha_envio, fecha_limite, 'PENDIENTE', input.motivo, input.observaciones)

        # Update fallado estado
        await conn.execute("UPDATE prod_fallados SET estado = 'EN_PROCESO' WHERE id = $1", input.fallado_id)

        return {"id": aid, "message": "Arreglo creado", "fecha_limite": str(fecha_limite)}


@router.put("/arreglos/{arreglo_id}/cerrar")
async def cerrar_arreglo(
    arreglo_id: str,
    input: ArregloCierre,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        arreglo = await conn.fetchrow("SELECT * FROM prod_arreglos WHERE id = $1", arreglo_id)
        if not arreglo:
            raise HTTPException(status_code=404, detail="Arreglo no encontrado")

        if input.cantidad_resuelta + input.cantidad_no_resuelta > arreglo["cantidad_enviada"]:
            raise HTTPException(status_code=400, detail="Resuelta + No resuelta excede cantidad enviada")

        # Convert fecha_retorno string to date object for asyncpg
        fecha_retorno_str = input.fecha_retorno or str(date.today())
        fecha_retorno = date.fromisoformat(fecha_retorno_str[:10]) if fecha_retorno_str else date.today()
        estado = "RESUELTO"

        await conn.execute("""
            UPDATE prod_arreglos SET
                fecha_retorno = $1, cantidad_resuelta = $2, cantidad_no_resuelta = $3,
                resultado_final = $4, estado = $5, observaciones = COALESCE($6, observaciones),
                motivo_no_resuelta = $7
            WHERE id = $8
        """, fecha_retorno, input.cantidad_resuelta, input.cantidad_no_resuelta,
            input.resultado_final, estado, input.observaciones, input.motivo_no_resuelta, arreglo_id)

        # Check if all arreglos for this fallado are resolved
        fallado_id = arreglo["fallado_id"]
        pending = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_arreglos WHERE fallado_id = $1 AND estado IN ('PENDIENTE','EN_PROCESO')",
            fallado_id
        )
        if safe_int(pending) == 0:
            await conn.execute("UPDATE prod_fallados SET estado = 'CERRADO' WHERE id = $1", fallado_id)

        return {"message": "Arreglo cerrado"}


@router.put("/arreglos/{arreglo_id}")
async def update_arreglo(
    arreglo_id: str,
    input: ArregloUpdate,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        existing = await conn.fetchrow("SELECT * FROM prod_arreglos WHERE id = $1", arreglo_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Arreglo no encontrado")
        if existing["estado"] == "RESUELTO":
            raise HTTPException(status_code=400, detail="No se puede editar un arreglo ya cerrado")

        sets = []
        params = []
        for field, val in [
            ("cantidad_enviada", input.cantidad_enviada),
            ("tipo", input.tipo),
            ("servicio_destino_id", input.servicio_destino_id),
            ("persona_destino_id", input.persona_destino_id),
            ("motivo", input.motivo),
            ("observaciones", input.observaciones),
        ]:
            if val is not None:
                params.append(val)
                sets.append(f"{field} = ${len(params)}")

        if input.fecha_envio is not None:
            params.append(date.fromisoformat(input.fecha_envio[:10]))
            sets.append(f"fecha_envio = ${len(params)}")
            fecha_limite = date.fromisoformat(input.fecha_envio[:10]) + timedelta(days=3)
            params.append(fecha_limite)
            sets.append(f"fecha_limite = ${len(params)}")

        if sets:
            params.append(arreglo_id)
            await conn.execute(f"UPDATE prod_arreglos SET {', '.join(sets)} WHERE id = ${len(params)}", *params)

        return {"message": "Arreglo actualizado"}


@router.post("/liquidacion-directa")
async def liquidacion_directa(
    input: LiquidacionDirecta,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        fallado = await conn.fetchrow("SELECT * FROM prod_fallados WHERE id = $1", input.fallado_id)
        if not fallado:
            raise HTTPException(status_code=404, detail="Fallado no encontrado")

        if input.cantidad < 1:
            raise HTTPException(status_code=400, detail="Cantidad debe ser mayor a 0")

        existing_sum = await conn.fetchval(
            "SELECT COALESCE(SUM(cantidad_enviada),0) FROM prod_arreglos WHERE fallado_id = $1",
            input.fallado_id
        )
        disponible = fallado["cantidad_detectada"] - safe_int(existing_sum)
        if input.cantidad > disponible:
            raise HTTPException(status_code=400, detail=f"Cantidad excede disponible ({disponible} de {fallado['cantidad_detectada']})")

        aid = str(uuid.uuid4())
        today = date.today()

        await conn.execute("""
            INSERT INTO prod_arreglos (id, fallado_id, registro_id, cantidad_enviada,
                cantidad_resuelta, cantidad_no_resuelta,
                tipo, fecha_envio, fecha_retorno, resultado_final, estado,
                motivo, motivo_no_resuelta)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
        """, aid, input.fallado_id, input.registro_id, input.cantidad,
            0, input.cantidad,
            'LIQUIDACION_DIRECTA', today, today, input.destino, 'RESUELTO',
            input.motivo, input.motivo)

        await conn.execute("UPDATE prod_fallados SET estado = 'EN_PROCESO' WHERE id = $1", input.fallado_id)

        pending = await conn.fetchval(
            "SELECT COUNT(*) FROM prod_arreglos WHERE fallado_id = $1 AND estado IN ('PENDIENTE','EN_PROCESO')",
            input.fallado_id
        )
        if safe_int(pending) == 0:
            total_nr = await conn.fetchval(
                "SELECT COALESCE(SUM(cantidad_no_resuelta),0) FROM prod_arreglos WHERE fallado_id = $1 AND estado = 'RESUELTO'",
                input.fallado_id
            )
            if safe_int(total_nr) >= fallado["cantidad_reparable"]:
                await conn.execute("UPDATE prod_fallados SET estado = 'CERRADO' WHERE id = $1", input.fallado_id)

        return {"id": aid, "message": "Liquidacion directa registrada"}


@router.delete("/arreglos/{arreglo_id}")
async def delete_arreglo(
    arreglo_id: str,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_arreglos WHERE id = $1", arreglo_id)
        return {"message": "Arreglo eliminado"}


# ==================== RESUMEN DE CANTIDADES ====================

@router.get("/registros/{registro_id}/resumen-cantidades")
async def resumen_cantidades(
    registro_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Resumen de cantidades del lote calculado en tiempo real.
    Regla prendas: SUM(prod_registro_tallas.cantidad_real), fallback JSONB tallas.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:

        reg = await conn.fetchrow("""
            SELECT r.id, r.n_corte, r.estado, r.estado_op, r.tallas,
                   r.dividido_desde_registro_id,
                   COALESCE((SELECT SUM(rt.cantidad_real) FROM prod_registro_tallas rt WHERE rt.registro_id = r.id), 0) as cantidad_tallas
            FROM prod_registros r WHERE r.id = $1
        """, registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")

        # Cantidad inicial: tallas actuales + prendas en hijos (para reflejar el total original)
        cantidad_base = safe_int(reg["cantidad_tallas"])
        if cantidad_base == 0:
            tallas_jsonb = parse_jsonb(reg["tallas"])
            cantidad_base = sum(safe_int(t.get("cantidad", 0)) for t in tallas_jsonb)

        # Merma / faltantes
        merma_total = await conn.fetchval(
            "SELECT COALESCE(SUM(cantidad), 0) FROM prod_mermas WHERE registro_id = $1", registro_id
        )

        # Fallados
        fallados_rows = await conn.fetch("SELECT * FROM prod_fallados WHERE registro_id = $1", registro_id)
        fallados_detectados = sum(safe_int(f["cantidad_detectada"]) for f in fallados_rows)
        total_reparable = sum(safe_int(f["cantidad_reparable"]) for f in fallados_rows)
        total_no_reparable = sum(safe_int(f["cantidad_no_reparable"]) for f in fallados_rows)
        no_rep_liquidacion = sum(safe_int(f["cantidad_no_reparable"]) for f in fallados_rows if f["destino_no_reparable"] == "LIQUIDACION")
        no_rep_segunda = sum(safe_int(f["cantidad_no_reparable"]) for f in fallados_rows if f["destino_no_reparable"] == "SEGUNDA")
        no_rep_descarte = sum(safe_int(f["cantidad_no_reparable"]) for f in fallados_rows if f["destino_no_reparable"] == "DESCARTE")
        no_rep_pendiente = sum(safe_int(f["cantidad_no_reparable"]) for f in fallados_rows if f["destino_no_reparable"] == "PENDIENTE")

        # Arreglos
        arreglos_rows = await conn.fetch("SELECT * FROM prod_arreglos WHERE registro_id = $1", registro_id)
        arreglos_enviados = sum(safe_int(a["cantidad_enviada"]) for a in arreglos_rows)
        arreglos_resueltos = sum(safe_int(a["cantidad_resuelta"]) for a in arreglos_rows if a["estado"] == "RESUELTO")
        arreglos_no_resueltos = sum(safe_int(a["cantidad_no_resuelta"]) for a in arreglos_rows if a["estado"] == "RESUELTO")
        arreglos_pendientes = sum(safe_int(a["cantidad_enviada"]) for a in arreglos_rows if a["estado"] in ("PENDIENTE", "EN_PROCESO"))
        arreglos_vencidos = 0
        for a in arreglos_rows:
            if a["estado"] in ("PENDIENTE", "EN_PROCESO") and a.get("fecha_limite"):
                try:
                    lim = a["fecha_limite"] if isinstance(a["fecha_limite"], date) else date.fromisoformat(str(a["fecha_limite"])[:10])
                    if lim < date.today():
                        arreglos_vencidos += safe_int(a["cantidad_enviada"])
                except (ValueError, TypeError):
                    pass

        # Liquidación from arreglos resultado_final
        liq_arreglos = sum(safe_int(a["cantidad_no_resuelta"]) for a in arreglos_rows if a.get("resultado_final") in ("LIQUIDACION", "SEGUNDA", "DESCARTE"))

        total_liquidacion = no_rep_liquidacion + sum(safe_int(a["cantidad_no_resuelta"]) for a in arreglos_rows if a.get("resultado_final") == "LIQUIDACION")
        total_segunda = no_rep_segunda + sum(safe_int(a["cantidad_no_resuelta"]) for a in arreglos_rows if a.get("resultado_final") == "SEGUNDA")
        total_descarte = no_rep_descarte + sum(safe_int(a["cantidad_no_resuelta"]) for a in arreglos_rows if a.get("resultado_final") == "DESCARTE")

        # Balance padre-hijos
        hijos = await conn.fetch(
            "SELECT id, n_corte, estado FROM prod_registros WHERE dividido_desde_registro_id = $1", registro_id
        )
        padre = None
        if reg["dividido_desde_registro_id"]:
            padre_row = await conn.fetchrow(
                "SELECT id, n_corte FROM prod_registros WHERE id = $1", reg["dividido_desde_registro_id"]
            )
            if padre_row:
                padre = {"id": padre_row["id"], "n_corte": padre_row["n_corte"]}

        hijos_data = []
        total_hijos_prendas = 0
        for h in hijos:
            hp = await conn.fetchval(
                "SELECT COALESCE(SUM(cantidad_real),0) FROM prod_registro_tallas WHERE registro_id = $1", h["id"]
            )
            hp_int = safe_int(hp)
            total_hijos_prendas += hp_int
            hijos_data.append({"id": h["id"], "n_corte": h["n_corte"], "estado": h["estado"], "prendas": hp_int})

        # cantidad_inicial = tallas actuales + hijos divididos (= total original antes de dividir)
        cantidad_inicial = cantidad_base + total_hijos_prendas

        # Alertas
        alertas = []
        if arreglos_vencidos > 0:
            alertas.append({"tipo": "VENCIDO", "mensaje": f"{arreglos_vencidos} prendas en arreglos vencidos"})
        if safe_int(merma_total) > 0:
            alertas.append({"tipo": "MERMA", "mensaje": f"{safe_int(merma_total)} prendas extraviadas/faltantes"})
        if no_rep_pendiente > 0:
            alertas.append({"tipo": "PENDIENTE", "mensaje": f"{no_rep_pendiente} no reparables sin destino definido"})

        # ---- Distribución que suma al total ----
        fallados_en_arreglo_pendiente = arreglos_pendientes
        fallados_en_arreglo_resuelto_buenos = arreglos_resueltos
        fallados_liquidados = total_liquidacion + total_segunda + total_descarte
        fallados_sin_asignar = fallados_detectados - sum(safe_int(a["cantidad_enviada"]) for a in arreglos_rows)

        # En producción = inicial - mermas - fallados + reparados - divididos
        en_produccion = cantidad_inicial - safe_int(merma_total) - fallados_detectados + fallados_en_arreglo_resuelto_buenos - total_hijos_prendas

        return {
            "registro_id": registro_id,
            "n_corte": reg["n_corte"],
            "estado": reg["estado"],
            "cantidad_inicial": cantidad_inicial,
            # Distribución (suma = cantidad_inicial)
            "en_produccion": max(en_produccion, 0),
            "mermas": safe_int(merma_total),
            "fallados_total": fallados_detectados,
            "fallados_en_arreglo": fallados_en_arreglo_pendiente,
            "fallados_reparados": fallados_en_arreglo_resuelto_buenos,
            "fallados_liquidados": fallados_liquidados,
            "fallados_sin_asignar": max(fallados_sin_asignar, 0),
            "divididos": total_hijos_prendas,
            # Desglose liquidación
            "liquidacion": total_liquidacion,
            "segunda": total_segunda,
            "descarte": total_descarte,
            # Desglose fallados
            "reparables": total_reparable,
            "no_reparables": total_no_reparable,
            "no_reparables_pendiente": no_rep_pendiente,
            # Arreglos detalle
            "arreglos_vencidos": arreglos_vencidos,
            # Padre/hijos
            "padre": padre,
            "hijos": hijos_data,
            "alertas": alertas,
        }


# ==================== REPORTE TRAZABILIDAD GENERAL ====================

@router.get("/reporte-trazabilidad")
async def reporte_trazabilidad(
    current_user: dict = Depends(get_current_user),
):
    """Resumen de trazabilidad de todos los registros activos."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        registros = await conn.fetch("""
            SELECT r.id, r.n_corte, r.estado, r.estado_op,
                   m.nombre as modelo_nombre, ma.nombre as marca,
                   COALESCE((SELECT SUM(rt.cantidad_real) FROM prod_registro_tallas rt WHERE rt.registro_id = r.id), 0) as cantidad_inicial
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            ORDER BY r.n_corte
        """)

        resultado = []
        for reg in registros:
            rid = reg["id"]
            ci = safe_int(reg["cantidad_inicial"])

            merma = safe_int(await conn.fetchval(
                "SELECT COALESCE(SUM(cantidad),0) FROM prod_mermas WHERE registro_id = $1", rid))

            fallados_total = safe_int(await conn.fetchval(
                "SELECT COALESCE(SUM(cantidad_detectada),0) FROM prod_fallados WHERE registro_id = $1", rid))

            arreglos_rows = await conn.fetch("SELECT * FROM prod_arreglos WHERE registro_id = $1", rid)
            en_arreglo = sum(safe_int(a["cantidad_enviada"]) for a in arreglos_rows if a["estado"] in ("PENDIENTE", "EN_PROCESO"))
            reparados = sum(safe_int(a["cantidad_resuelta"]) for a in arreglos_rows if a["estado"] == "RESUELTO")
            liquidados = sum(safe_int(a["cantidad_no_resuelta"]) for a in arreglos_rows if a["estado"] == "RESUELTO")
            sin_asignar = fallados_total - sum(safe_int(a["cantidad_enviada"]) for a in arreglos_rows)
            en_produccion = max(ci - merma - fallados_total + reparados, 0)

            vencidos = 0
            for a in arreglos_rows:
                if a["estado"] in ("PENDIENTE", "EN_PROCESO") and a.get("fecha_limite"):
                    try:
                        lim = a["fecha_limite"] if isinstance(a["fecha_limite"], date) else date.fromisoformat(str(a["fecha_limite"])[:10])
                        if lim < date.today():
                            vencidos += safe_int(a["cantidad_enviada"])
                    except (ValueError, TypeError):
                        pass

            divididos = safe_int(await conn.fetchval(
                "SELECT COALESCE(SUM(rt.cantidad_real),0) FROM prod_registro_tallas rt JOIN prod_registros r ON rt.registro_id = r.id WHERE r.dividido_desde_registro_id = $1", rid))

            tiene_novedades = fallados_total > 0 or merma > 0 or divididos > 0

            resultado.append({
                "id": rid,
                "n_corte": reg["n_corte"],
                "estado": reg["estado"],
                "modelo": reg["modelo_nombre"] or "",
                "marca": reg["marca"] or "",
                "cantidad_inicial": ci,
                "en_produccion": en_produccion,
                "fallados_total": fallados_total,
                "en_arreglo": en_arreglo,
                "reparados": reparados,
                "liquidados": liquidados,
                "sin_asignar": max(sin_asignar, 0),
                "mermas": merma,
                "divididos": divididos,
                "vencidos": vencidos,
                "tiene_novedades": tiene_novedades,
            })

        # Totales generales
        totales = {
            "registros": len(resultado),
            "cantidad_inicial": sum(r["cantidad_inicial"] for r in resultado),
            "en_produccion": sum(r["en_produccion"] for r in resultado),
            "fallados_total": sum(r["fallados_total"] for r in resultado),
            "en_arreglo": sum(r["en_arreglo"] for r in resultado),
            "reparados": sum(r["reparados"] for r in resultado),
            "liquidados": sum(r["liquidados"] for r in resultado),
            "sin_asignar": sum(r["sin_asignar"] for r in resultado),
            "mermas": sum(r["mermas"] for r in resultado),
            "divididos": sum(r["divididos"] for r in resultado),
            "vencidos": sum(r["vencidos"] for r in resultado),
        }

        return {"registros": resultado, "totales": totales}


# ==================== TRAZABILIDAD COMPLETA ====================

@router.get("/registros/{registro_id}/trazabilidad-completa")
async def trazabilidad_completa(
    registro_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Timeline unificado: movimientos + mermas + fallados + arreglos + divisiones.
    Todo cronológico en un solo array de eventos.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:

        # Registro info
        reg = await conn.fetchrow("""
            SELECT r.id, r.n_corte, r.estado, r.estado_op, r.fecha_creacion,
                   r.fecha_entrega_final, r.urgente, r.dividido_desde_registro_id,
                   m.nombre as modelo_nombre, rp.nombre as ruta_nombre
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_rutas_produccion rp ON m.ruta_produccion_id = rp.id
            WHERE r.id = $1
        """, registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")

        reg_d = row_to_dict(reg)
        for f in ("fecha_creacion", "fecha_entrega_final"):
            if reg_d.get(f): reg_d[f] = str(reg_d[f])

        eventos = []

        # 1. Movimientos
        movs = await conn.fetch("""
            SELECT mp.*, sp.nombre as servicio_nombre, pp.nombre as persona_nombre
            FROM prod_movimientos_produccion mp
            LEFT JOIN prod_servicios_produccion sp ON mp.servicio_id = sp.id
            LEFT JOIN prod_personas_produccion pp ON mp.persona_id = pp.id
            WHERE mp.registro_id = $1
            ORDER BY mp.fecha_inicio ASC NULLS LAST, mp.created_at ASC
        """, registro_id)
        for mv in movs:
            d = row_to_dict(mv)
            eventos.append({
                "tipo_evento": "MOVIMIENTO",
                "fecha": str(d.get("fecha_inicio") or d.get("created_at") or ""),
                "servicio": d.get("servicio_nombre", ""),
                "persona": d.get("persona_nombre", ""),
                "cantidad_enviada": safe_int(d.get("cantidad_enviada")),
                "cantidad_recibida": safe_int(d.get("cantidad_recibida")),
                "diferencia": safe_int(d.get("diferencia")),
                "fecha_fin": str(d["fecha_fin"]) if d.get("fecha_fin") else None,
                "id": d["id"],
            })

        # 2. Mermas
        mermas = await conn.fetch("""
            SELECT m.*, sp.nombre as servicio_nombre, pp.nombre as persona_nombre
            FROM prod_mermas m
            LEFT JOIN prod_servicios_produccion sp ON m.servicio_id = sp.id
            LEFT JOIN prod_personas_produccion pp ON m.persona_id = pp.id
            WHERE m.registro_id = $1
        """, registro_id)
        for mr in mermas:
            d = row_to_dict(mr)
            eventos.append({
                "tipo_evento": "MERMA",
                "fecha": str(d.get("fecha") or d.get("created_at") or ""),
                "cantidad": safe_int(d.get("cantidad")),
                "motivo": d.get("motivo", ""),
                "tipo": d.get("tipo", "FALTANTE"),
                "servicio": d.get("servicio_nombre", ""),
                "id": d["id"],
            })

        # 3. Fallados
        fallados = await conn.fetch("""
            SELECT f.*, sp.nombre as servicio_nombre
            FROM prod_fallados f
            LEFT JOIN prod_servicios_produccion sp ON f.servicio_detectado_id = sp.id
            WHERE f.registro_id = $1
        """, registro_id)
        for fl in fallados:
            d = row_to_dict(fl)
            eventos.append({
                "tipo_evento": "FALLADO",
                "fecha": str(d.get("fecha_deteccion") or d.get("created_at") or ""),
                "cantidad_detectada": safe_int(d.get("cantidad_detectada")),
                "cantidad_reparable": safe_int(d.get("cantidad_reparable")),
                "cantidad_no_reparable": safe_int(d.get("cantidad_no_reparable")),
                "destino_no_reparable": d.get("destino_no_reparable", "PENDIENTE"),
                "motivo": d.get("motivo", ""),
                "estado": d.get("estado", "ABIERTO"),
                "servicio": d.get("servicio_nombre", ""),
                "id": d["id"],
            })

        # 4. Arreglos
        arreglos = await conn.fetch("""
            SELECT a.*, sp.nombre as servicio_nombre, pp.nombre as persona_nombre
            FROM prod_arreglos a
            LEFT JOIN prod_servicios_produccion sp ON a.servicio_destino_id = sp.id
            LEFT JOIN prod_personas_produccion pp ON a.persona_destino_id = pp.id
            WHERE a.registro_id = $1
        """, registro_id)
        for ar in arreglos:
            d = row_to_dict(ar)
            vencido = False
            if d.get("estado") in ("PENDIENTE", "EN_PROCESO") and d.get("fecha_limite"):
                try:
                    lim = d["fecha_limite"] if isinstance(d["fecha_limite"], date) else date.fromisoformat(str(d["fecha_limite"])[:10])
                    vencido = lim < date.today() and not d.get("fecha_retorno")
                except (ValueError, TypeError):
                    pass
            eventos.append({
                "tipo_evento": "ARREGLO",
                "fecha": str(d.get("fecha_envio") or d.get("created_at") or ""),
                "tipo": d.get("tipo", ""),
                "cantidad_enviada": safe_int(d.get("cantidad_enviada")),
                "cantidad_resuelta": safe_int(d.get("cantidad_resuelta")),
                "cantidad_no_resuelta": safe_int(d.get("cantidad_no_resuelta")),
                "servicio": d.get("servicio_nombre", ""),
                "persona": d.get("persona_nombre", ""),
                "fecha_limite": str(d["fecha_limite"]) if d.get("fecha_limite") else None,
                "fecha_retorno": str(d["fecha_retorno"]) if d.get("fecha_retorno") else None,
                "estado": d.get("estado", "PENDIENTE"),
                "resultado_final": d.get("resultado_final", "PENDIENTE"),
                "vencido": vencido,
                "id": d["id"],
            })

        # 5. Divisiones
        hijos = await conn.fetch("""
            SELECT id, n_corte, estado, division_numero, fecha_creacion,
                   COALESCE((SELECT SUM(rt.cantidad_real) FROM prod_registro_tallas rt WHERE rt.registro_id = h.id),0) as prendas
            FROM prod_registros h
            WHERE h.dividido_desde_registro_id = $1
            ORDER BY h.division_numero
        """, registro_id)
        for h in hijos:
            d = row_to_dict(h)
            eventos.append({
                "tipo_evento": "DIVISION",
                "fecha": str(d.get("fecha_creacion") or ""),
                "hijo_id": d["id"],
                "hijo_n_corte": d["n_corte"],
                "hijo_estado": d["estado"],
                "hijo_prendas": safe_int(d.get("prendas")),
            })

        # Sort by date
        eventos.sort(key=lambda e: e.get("fecha", ""))

        return {
            "registro": reg_d,
            "eventos": eventos,
            "total_eventos": len(eventos),
        }
