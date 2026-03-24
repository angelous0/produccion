"""
Router: Reportes de Producción P0
Dashboard KPIs, En Proceso, WIP por Etapa, Atrasados, Trazabilidad,
Cumplimiento de Ruta, Balance Terceros, Lotes Fraccionados.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import date, datetime, timezone
import json

router = APIRouter(prefix="/api/reportes-produccion", tags=["reportes-produccion"])

import sys
sys.path.insert(0, '/app/backend')
from db import get_pool
from auth import get_current_user
from helpers import row_to_dict


def parse_jsonb(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except:
            return []
    return val


def safe_float(v):
    try:
        return float(v or 0)
    except:
        return 0.0


def safe_int(v):
    try:
        return int(v or 0)
    except:
        return 0


# ==================== 1. DASHBOARD KPIs ====================

@router.get("/dashboard")
async def dashboard_kpis(
    empresa_id: int = Query(6),
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    ruta_id: Optional[str] = None,
    modelo_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # KPI 1: Registros por estado_op
        rows_estado_op = await conn.fetch("""
            SELECT r.estado_op, COUNT(*) as cnt,
                   COALESCE(SUM((SELECT COALESCE(SUM(rt.cantidad_real),0) FROM prod_registro_tallas rt WHERE rt.registro_id = r.id)),0) as prendas
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            WHERE r.empresa_id = $1
              AND r.dividido_desde_registro_id IS NULL
            GROUP BY r.estado_op
        """, empresa_id)

        total_en_proceso = 0
        total_prendas_proceso = 0
        dist_estado_op = []
        for r in rows_estado_op:
            d = {"estado_op": r["estado_op"], "cantidad": int(r["cnt"]), "prendas": int(r["prendas"])}
            dist_estado_op.append(d)
            if r["estado_op"] in ("ABIERTA", "EN_PROCESO"):
                total_en_proceso += int(r["cnt"])
                total_prendas_proceso += int(r["prendas"])

        # KPI 2: Distribución por estado (etapa visible)
        rows_estado = await conn.fetch("""
            SELECT r.estado, COUNT(*) as cnt
            FROM prod_registros r
            WHERE r.empresa_id = $1
              AND r.estado_op IN ('ABIERTA', 'EN_PROCESO')
              AND r.dividido_desde_registro_id IS NULL
            GROUP BY r.estado
            ORDER BY cnt DESC
        """, empresa_id)
        dist_estado = [{"estado": r["estado"], "cantidad": int(r["cnt"])} for r in rows_estado]

        # KPI 3: Lotes atrasados
        atrasados_count = await conn.fetchval("""
            SELECT COUNT(DISTINCT r.id)
            FROM prod_registros r
            WHERE r.empresa_id = $1
              AND r.estado_op IN ('ABIERTA', 'EN_PROCESO')
              AND (
                r.fecha_entrega_final < CURRENT_DATE
                OR EXISTS (
                    SELECT 1 FROM prod_movimientos_produccion mp
                    WHERE mp.registro_id = r.id
                      AND mp.fecha_esperada_movimiento < CURRENT_DATE
                      AND mp.fecha_fin IS NULL
                )
              )
        """, empresa_id)

        # KPI 4: Movimientos abiertos (sin fecha_fin)
        movs_abiertos = await conn.fetchval("""
            SELECT COUNT(*)
            FROM prod_movimientos_produccion mp
            JOIN prod_registros r ON mp.registro_id = r.id
            WHERE r.empresa_id = $1
              AND r.estado_op IN ('ABIERTA', 'EN_PROCESO')
              AND mp.fecha_fin IS NULL
        """, empresa_id)

        # KPI 5: Prendas por servicio (top 10)
        rows_srv = await conn.fetch("""
            SELECT sp.nombre as servicio, 
                   COUNT(DISTINCT mp.registro_id) as lotes,
                   COALESCE(SUM(mp.cantidad_enviada),0) as enviadas,
                   COALESCE(SUM(mp.cantidad_recibida),0) as recibidas
            FROM prod_movimientos_produccion mp
            JOIN prod_registros r ON mp.registro_id = r.id
            JOIN prod_servicios_produccion sp ON mp.servicio_id = sp.id
            WHERE r.empresa_id = $1
              AND r.estado_op IN ('ABIERTA', 'EN_PROCESO')
            GROUP BY sp.nombre
            ORDER BY lotes DESC
            LIMIT 10
        """, empresa_id)
        por_servicio = [
            {"servicio": r["servicio"], "lotes": int(r["lotes"]),
             "enviadas": safe_int(r["enviadas"]), "recibidas": safe_int(r["recibidas"])}
            for r in rows_srv
        ]

        # KPI 6: Lotes fraccionados count
        fraccionados = await conn.fetchval("""
            SELECT COUNT(*) FROM prod_registros
            WHERE empresa_id = $1 AND dividido_desde_registro_id IS NOT NULL
        """, empresa_id)

        return {
            "total_en_proceso": total_en_proceso,
            "total_prendas_proceso": total_prendas_proceso,
            "atrasados": safe_int(atrasados_count),
            "movimientos_abiertos": safe_int(movs_abiertos),
            "lotes_fraccionados": safe_int(fraccionados),
            "distribucion_estado_op": dist_estado_op,
            "distribucion_estado": dist_estado,
            "por_servicio": por_servicio,
        }


# ==================== 2. PRODUCCIÓN EN PROCESO ====================

@router.get("/en-proceso")
async def produccion_en_proceso(
    empresa_id: int = Query(6),
    estado: Optional[str] = None,
    ruta_id: Optional[str] = None,
    modelo_id: Optional[str] = None,
    servicio_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT r.id, r.n_corte, r.estado, r.estado_op, r.urgente,
                   r.fecha_creacion, r.fecha_entrega_final,
                   m.nombre as modelo_nombre,
                   ma.nombre as marca_nombre,
                   rp.nombre as ruta_nombre,
                   COALESCE((SELECT SUM(rt.cantidad_real) FROM prod_registro_tallas rt WHERE rt.registro_id = r.id),0) as total_prendas,
                   (CURRENT_DATE - r.fecha_creacion::date) as dias_proceso,
                   (SELECT COUNT(*) FROM prod_movimientos_produccion mp WHERE mp.registro_id = r.id) as total_movimientos,
                   (SELECT COUNT(*) FROM prod_movimientos_produccion mp WHERE mp.registro_id = r.id AND mp.fecha_fin IS NOT NULL) as movimientos_cerrados,
                   (SELECT COUNT(*) FROM prod_movimientos_produccion mp WHERE mp.registro_id = r.id AND mp.fecha_esperada_movimiento < CURRENT_DATE AND mp.fecha_fin IS NULL) as movs_vencidos,
                   r.dividido_desde_registro_id,
                   r.division_numero
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            LEFT JOIN prod_rutas_produccion rp ON m.ruta_produccion_id = rp.id
            WHERE r.empresa_id = $1
              AND r.estado_op IN ('ABIERTA', 'EN_PROCESO')
        """
        params = [empresa_id]

        if estado:
            params.append(estado)
            query += f" AND r.estado = ${len(params)}"
        if modelo_id:
            params.append(modelo_id)
            query += f" AND r.modelo_id = ${len(params)}"
        if ruta_id:
            params.append(ruta_id)
            query += f" AND m.ruta_produccion_id = ${len(params)}"
        if servicio_id:
            params.append(servicio_id)
            query += f" AND EXISTS (SELECT 1 FROM prod_movimientos_produccion mp2 WHERE mp2.registro_id = r.id AND mp2.servicio_id = ${len(params)})"

        query += " ORDER BY r.urgente DESC, r.fecha_creacion ASC"
        rows = await conn.fetch(query, *params)

        registros = []
        for r in rows:
            d = row_to_dict(r)
            d["total_prendas"] = safe_int(d.get("total_prendas"))
            d["dias_proceso"] = safe_int(d.get("dias_proceso"))
            d["total_movimientos"] = safe_int(d.get("total_movimientos"))
            d["movimientos_cerrados"] = safe_int(d.get("movimientos_cerrados"))
            d["movs_vencidos"] = safe_int(d.get("movs_vencidos"))
            if d.get("fecha_entrega_final"):
                d["fecha_entrega_final"] = str(d["fecha_entrega_final"])
            if d.get("fecha_creacion"):
                d["fecha_creacion"] = str(d["fecha_creacion"])
            registros.append(d)

        return {"registros": registros, "total": len(registros)}


# ==================== 3. WIP POR ETAPA ====================

@router.get("/wip-etapa")
async def wip_por_etapa(
    empresa_id: int = Query(6),
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT r.estado,
                   COUNT(*) as lotes,
                   COALESCE(SUM((SELECT COALESCE(SUM(rt.cantidad_real),0) FROM prod_registro_tallas rt WHERE rt.registro_id = r.id)),0) as prendas,
                   MIN(r.fecha_creacion) as lote_mas_antiguo,
                   COUNT(*) FILTER (WHERE r.urgente = true) as urgentes
            FROM prod_registros r
            WHERE r.empresa_id = $1
              AND r.estado_op IN ('ABIERTA', 'EN_PROCESO')
              AND r.dividido_desde_registro_id IS NULL
            GROUP BY r.estado
            ORDER BY lotes DESC
        """, empresa_id)

        etapas = []
        for r in rows:
            d = {
                "etapa": r["estado"],
                "lotes": int(r["lotes"]),
                "prendas": safe_int(r["prendas"]),
                "urgentes": int(r["urgentes"]),
                "lote_mas_antiguo": str(r["lote_mas_antiguo"]) if r["lote_mas_antiguo"] else None,
            }
            etapas.append(d)

        return {"etapas": etapas, "total_etapas": len(etapas)}


# ==================== 4. LOTES ATRASADOS ====================

@router.get("/atrasados")
async def lotes_atrasados(
    empresa_id: int = Query(6),
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT r.id, r.n_corte, r.estado, r.estado_op, r.urgente,
                   r.fecha_creacion, r.fecha_entrega_final,
                   m.nombre as modelo_nombre,
                   ma.nombre as marca_nombre,
                   COALESCE((SELECT SUM(rt.cantidad_real) FROM prod_registro_tallas rt WHERE rt.registro_id = r.id),0) as total_prendas,
                   (CURRENT_DATE - r.fecha_creacion::date) as dias_proceso,
                   -- Motivos de atraso
                   CASE WHEN r.fecha_entrega_final < CURRENT_DATE THEN true ELSE false END as entrega_vencida,
                   (SELECT COUNT(*) FROM prod_movimientos_produccion mp
                    WHERE mp.registro_id = r.id AND mp.fecha_esperada_movimiento < CURRENT_DATE AND mp.fecha_fin IS NULL) as movs_vencidos,
                   -- Días de atraso
                   CASE WHEN r.fecha_entrega_final < CURRENT_DATE 
                        THEN (CURRENT_DATE - r.fecha_entrega_final) 
                        ELSE 0 END as dias_atraso_entrega
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            WHERE r.empresa_id = $1
              AND r.estado_op IN ('ABIERTA', 'EN_PROCESO')
              AND (
                r.fecha_entrega_final < CURRENT_DATE
                OR EXISTS (
                    SELECT 1 FROM prod_movimientos_produccion mp
                    WHERE mp.registro_id = r.id
                      AND mp.fecha_esperada_movimiento < CURRENT_DATE
                      AND mp.fecha_fin IS NULL
                )
              )
            ORDER BY dias_atraso_entrega DESC NULLS LAST, r.urgente DESC
        """, empresa_id)

        registros = []
        for r in rows:
            d = row_to_dict(r)
            d["total_prendas"] = safe_int(d.get("total_prendas"))
            d["dias_proceso"] = safe_int(d.get("dias_proceso"))
            d["movs_vencidos"] = safe_int(d.get("movs_vencidos"))
            d["dias_atraso_entrega"] = safe_int(d.get("dias_atraso_entrega"))
            if d.get("fecha_entrega_final"):
                d["fecha_entrega_final"] = str(d["fecha_entrega_final"])
            if d.get("fecha_creacion"):
                d["fecha_creacion"] = str(d["fecha_creacion"])
            registros.append(d)

        return {"registros": registros, "total": len(registros)}


# ==================== 5. TRAZABILIDAD ====================

@router.get("/trazabilidad/{registro_id}")
async def trazabilidad_registro(
    registro_id: str,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("""
            SELECT r.id, r.n_corte, r.estado, r.estado_op, r.fecha_creacion, r.fecha_entrega_final,
                   r.urgente, r.dividido_desde_registro_id, r.division_numero,
                   m.nombre as modelo_nombre, ma.nombre as marca_nombre,
                   rp.nombre as ruta_nombre, rp.etapas as ruta_etapas,
                   m.ruta_produccion_id
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_marcas ma ON m.marca_id = ma.id
            LEFT JOIN prod_rutas_produccion rp ON m.ruta_produccion_id = rp.id
            WHERE r.id = $1
        """, registro_id)

        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")

        reg_d = row_to_dict(reg)
        if reg_d.get("fecha_creacion"):
            reg_d["fecha_creacion"] = str(reg_d["fecha_creacion"])
        if reg_d.get("fecha_entrega_final"):
            reg_d["fecha_entrega_final"] = str(reg_d["fecha_entrega_final"])
        reg_d["ruta_etapas"] = parse_jsonb(reg_d.get("ruta_etapas"))

        # Tallas
        tallas = await conn.fetch("""
            SELECT rt.talla_id, rt.cantidad_real, tc.nombre as talla_nombre
            FROM prod_registro_tallas rt
            LEFT JOIN prod_tallas_catalogo tc ON rt.talla_id = tc.id
            WHERE rt.registro_id = $1
            ORDER BY tc.nombre
        """, registro_id)
        reg_d["tallas"] = [{"talla_id": t["talla_id"], "talla_nombre": t["talla_nombre"], "cantidad": safe_int(t["cantidad_real"])} for t in tallas]
        reg_d["total_prendas"] = sum(safe_int(t["cantidad_real"]) for t in tallas)

        # Movimientos cronológicos
        movs = await conn.fetch("""
            SELECT mp.id, mp.servicio_id, mp.persona_id,
                   sp.nombre as servicio_nombre,
                   pp.nombre as persona_nombre,
                   pp.tipo_persona,
                   mp.cantidad_enviada, mp.cantidad_recibida, mp.diferencia,
                   mp.costo_calculado, mp.tarifa_aplicada,
                   mp.fecha_inicio, mp.fecha_fin, mp.fecha_esperada_movimiento,
                   mp.observaciones, mp.created_at,
                   CASE WHEN mp.fecha_fin IS NOT NULL AND mp.fecha_inicio IS NOT NULL
                        THEN mp.fecha_fin - mp.fecha_inicio
                        ELSE NULL END as dias_servicio
            FROM prod_movimientos_produccion mp
            LEFT JOIN prod_servicios_produccion sp ON mp.servicio_id = sp.id
            LEFT JOIN prod_personas_produccion pp ON mp.persona_id = pp.id
            WHERE mp.registro_id = $1
            ORDER BY mp.fecha_inicio ASC NULLS LAST, mp.created_at ASC
        """, registro_id)

        movimientos = []
        for mv in movs:
            d = row_to_dict(mv)
            d["cantidad_enviada"] = safe_int(d.get("cantidad_enviada"))
            d["cantidad_recibida"] = safe_int(d.get("cantidad_recibida"))
            d["diferencia"] = safe_int(d.get("diferencia"))
            d["costo_calculado"] = safe_float(d.get("costo_calculado"))
            d["tarifa_aplicada"] = safe_float(d.get("tarifa_aplicada"))
            d["dias_servicio"] = safe_int(d.get("dias_servicio"))
            for f in ("fecha_inicio", "fecha_fin", "fecha_esperada_movimiento", "created_at"):
                if d.get(f):
                    d[f] = str(d[f])
            movimientos.append(d)

        # Divisiones (hijos)
        hijos = await conn.fetch("""
            SELECT id, n_corte, estado, estado_op, division_numero
            FROM prod_registros WHERE dividido_desde_registro_id = $1
            ORDER BY division_numero
        """, registro_id)
        divisiones = [row_to_dict(h) for h in hijos]

        return {
            "registro": reg_d,
            "movimientos": movimientos,
            "divisiones": divisiones,
            "total_movimientos": len(movimientos),
        }


# ==================== 6. CUMPLIMIENTO DE RUTA ====================

@router.get("/cumplimiento-ruta")
async def cumplimiento_ruta(
    empresa_id: int = Query(6),
    ruta_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT r.id, r.n_corte, r.estado, r.estado_op, r.urgente,
                   r.fecha_creacion, r.fecha_entrega_final,
                   m.nombre as modelo_nombre,
                   rp.id as ruta_id, rp.nombre as ruta_nombre, rp.etapas as ruta_etapas,
                   COALESCE((SELECT SUM(rt.cantidad_real) FROM prod_registro_tallas rt WHERE rt.registro_id = r.id),0) as total_prendas
            FROM prod_registros r
            LEFT JOIN prod_modelos m ON r.modelo_id = m.id
            LEFT JOIN prod_rutas_produccion rp ON m.ruta_produccion_id = rp.id
            WHERE r.empresa_id = $1
              AND r.estado_op IN ('ABIERTA', 'EN_PROCESO')
              AND r.dividido_desde_registro_id IS NULL
              AND rp.id IS NOT NULL
        """
        params = [empresa_id]
        if ruta_id:
            params.append(ruta_id)
            query += f" AND rp.id = ${len(params)}"

        query += " ORDER BY r.fecha_creacion ASC"
        rows = await conn.fetch(query, *params)

        # Get all movimientos for these registros in batch
        reg_ids = [r["id"] for r in rows]
        if reg_ids:
            movs = await conn.fetch("""
                SELECT mp.registro_id, mp.servicio_id,
                       mp.fecha_inicio, mp.fecha_fin
                FROM prod_movimientos_produccion mp
                WHERE mp.registro_id = ANY($1::text[])
            """, reg_ids)
        else:
            movs = []

        # Index: registro_id -> list of {servicio_id, fecha_inicio, fecha_fin}
        mov_map = {}
        for mv in movs:
            rid = mv["registro_id"]
            if rid not in mov_map:
                mov_map[rid] = []
            mov_map[rid].append({
                "servicio_id": mv["servicio_id"],
                "inicio": mv["fecha_inicio"] is not None,
                "fin": mv["fecha_fin"] is not None,
            })

        registros = []
        for r in rows:
            d = row_to_dict(r)
            etapas = parse_jsonb(d.pop("ruta_etapas", None))
            d["total_prendas"] = safe_int(d.get("total_prendas"))
            if d.get("fecha_creacion"):
                d["fecha_creacion"] = str(d["fecha_creacion"])
            if d.get("fecha_entrega_final"):
                d["fecha_entrega_final"] = str(d["fecha_entrega_final"])

            reg_movs = mov_map.get(r["id"], [])
            total_etapas = len(etapas)
            completadas = 0
            en_curso = 0
            pendientes = 0
            detalle_etapas = []

            for etapa in etapas:
                sid = etapa.get("servicio_id")
                nombre_etapa = etapa.get("nombre", "")
                obligatorio = etapa.get("obligatorio", False)

                # Check if any movement matches this service
                movs_etapa = [m for m in reg_movs if m["servicio_id"] == sid]
                tiene_inicio = any(m["inicio"] for m in movs_etapa)
                tiene_fin = any(m["fin"] for m in movs_etapa)

                if tiene_fin:
                    estado_etapa = "COMPLETADA"
                    completadas += 1
                elif tiene_inicio:
                    estado_etapa = "EN_CURSO"
                    en_curso += 1
                else:
                    estado_etapa = "PENDIENTE"
                    pendientes += 1

                detalle_etapas.append({
                    "nombre": nombre_etapa,
                    "obligatorio": obligatorio,
                    "estado": estado_etapa,
                })

            pct = round((completadas / total_etapas * 100), 1) if total_etapas > 0 else 0
            d["total_etapas"] = total_etapas
            d["completadas"] = completadas
            d["en_curso"] = en_curso
            d["pendientes"] = pendientes
            d["pct_cumplimiento"] = pct
            d["detalle_etapas"] = detalle_etapas
            registros.append(d)

        return {"registros": registros, "total": len(registros)}


# ==================== 7. BALANCE POR TERCEROS ====================

@router.get("/balance-terceros")
async def balance_terceros(
    empresa_id: int = Query(6),
    servicio_id: Optional[str] = None,
    persona_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # By service
        query_srv = """
            SELECT sp.id as servicio_id, sp.nombre as servicio,
                   pp.id as persona_id, pp.nombre as persona, pp.tipo_persona,
                   COUNT(DISTINCT mp.registro_id) as lotes,
                   COUNT(mp.id) as movimientos,
                   COALESCE(SUM(mp.cantidad_enviada),0) as total_enviadas,
                   COALESCE(SUM(mp.cantidad_recibida),0) as total_recibidas,
                   COALESCE(SUM(mp.diferencia),0) as total_diferencia,
                   COALESCE(SUM(mp.costo_calculado),0) as costo_total,
                   COUNT(mp.id) FILTER (WHERE mp.fecha_fin IS NULL) as movs_abiertos,
                   COALESCE(SUM(mp.cantidad_enviada) FILTER (WHERE mp.fecha_fin IS NULL),0) as prendas_en_poder
            FROM prod_movimientos_produccion mp
            JOIN prod_registros r ON mp.registro_id = r.id
            JOIN prod_servicios_produccion sp ON mp.servicio_id = sp.id
            LEFT JOIN prod_personas_produccion pp ON mp.persona_id = pp.id
            WHERE r.empresa_id = $1
        """
        params = [empresa_id]
        if servicio_id:
            params.append(servicio_id)
            query_srv += f" AND mp.servicio_id = ${len(params)}"
        if persona_id:
            params.append(persona_id)
            query_srv += f" AND mp.persona_id = ${len(params)}"

        query_srv += " GROUP BY sp.id, sp.nombre, pp.id, pp.nombre, pp.tipo_persona ORDER BY costo_total DESC"
        rows = await conn.fetch(query_srv, *params)

        balance = []
        for r in rows:
            balance.append({
                "servicio_id": r["servicio_id"],
                "servicio": r["servicio"],
                "persona_id": r["persona_id"],
                "persona": r["persona"],
                "tipo_persona": r["tipo_persona"],
                "lotes": int(r["lotes"]),
                "movimientos": int(r["movimientos"]),
                "total_enviadas": safe_int(r["total_enviadas"]),
                "total_recibidas": safe_int(r["total_recibidas"]),
                "total_diferencia": safe_int(r["total_diferencia"]),
                "costo_total": safe_float(r["costo_total"]),
                "movs_abiertos": int(r["movs_abiertos"]),
                "prendas_en_poder": safe_int(r["prendas_en_poder"]),
            })

        # Summary by service only
        resumen_servicio = {}
        for b in balance:
            sid = b["servicio"]
            if sid not in resumen_servicio:
                resumen_servicio[sid] = {"lotes": 0, "enviadas": 0, "recibidas": 0, "costo": 0, "en_poder": 0}
            resumen_servicio[sid]["lotes"] += b["lotes"]
            resumen_servicio[sid]["enviadas"] += b["total_enviadas"]
            resumen_servicio[sid]["recibidas"] += b["total_recibidas"]
            resumen_servicio[sid]["costo"] += b["costo_total"]
            resumen_servicio[sid]["en_poder"] += b["prendas_en_poder"]

        return {"balance": balance, "resumen_servicio": resumen_servicio, "total": len(balance)}


# ==================== 8. LOTES FRACCIONADOS ====================

@router.get("/lotes-fraccionados")
async def lotes_fraccionados(
    empresa_id: int = Query(6),
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Get parents that have children
        rows = await conn.fetch("""
            SELECT p.id as padre_id, p.n_corte as padre_corte, p.estado as padre_estado,
                   p.estado_op as padre_estado_op,
                   mo.nombre as modelo_nombre,
                   COALESCE((SELECT SUM(rt.cantidad_real) FROM prod_registro_tallas rt WHERE rt.registro_id = p.id),0) as padre_prendas,
                   (SELECT json_agg(json_build_object(
                       'id', h.id,
                       'n_corte', h.n_corte,
                       'estado', h.estado,
                       'estado_op', h.estado_op,
                       'division_numero', h.division_numero,
                       'prendas', COALESCE((SELECT SUM(rt2.cantidad_real) FROM prod_registro_tallas rt2 WHERE rt2.registro_id = h.id),0)
                   ) ORDER BY h.division_numero)
                   FROM prod_registros h WHERE h.dividido_desde_registro_id = p.id) as hijos
            FROM prod_registros p
            LEFT JOIN prod_modelos mo ON p.modelo_id = mo.id
            WHERE p.empresa_id = $1
              AND EXISTS (SELECT 1 FROM prod_registros h WHERE h.dividido_desde_registro_id = p.id)
            ORDER BY p.fecha_creacion DESC
        """, empresa_id)

        familias = []
        for r in rows:
            hijos_raw = r["hijos"]
            if isinstance(hijos_raw, str):
                hijos_raw = json.loads(hijos_raw)
            hijos = hijos_raw or []
            total_hijos_prendas = sum(safe_int(h.get("prendas")) for h in hijos)

            familias.append({
                "padre_id": r["padre_id"],
                "padre_corte": r["padre_corte"],
                "padre_estado": r["padre_estado"],
                "padre_estado_op": r["padre_estado_op"],
                "modelo_nombre": r["modelo_nombre"],
                "padre_prendas": safe_int(r["padre_prendas"]),
                "hijos": hijos,
                "total_hijos": len(hijos),
                "total_hijos_prendas": total_hijos_prendas,
                "total_familia_prendas": safe_int(r["padre_prendas"]) + total_hijos_prendas,
            })

        return {"familias": familias, "total": len(familias)}


# ==================== FILTROS: Servicios y Rutas para combos ====================

@router.get("/filtros")
async def get_filtros_reportes(
    empresa_id: int = Query(6),
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:
        servicios = await conn.fetch("SELECT id, nombre FROM prod_servicios_produccion ORDER BY orden ASC, nombre")
        rutas = await conn.fetch("SELECT id, nombre FROM prod_rutas_produccion ORDER BY nombre")
        modelos = await conn.fetch("SELECT id, nombre FROM prod_modelos ORDER BY nombre")
        estados = await conn.fetch("""
            SELECT DISTINCT estado FROM prod_registros WHERE empresa_id = $1 AND estado_op IN ('ABIERTA','EN_PROCESO') ORDER BY estado
        """, empresa_id)

        return {
            "servicios": [{"id": r["id"], "nombre": r["nombre"]} for r in servicios],
            "rutas": [{"id": r["id"], "nombre": r["nombre"]} for r in rutas],
            "modelos": [{"id": r["id"], "nombre": r["nombre"]} for r in modelos],
            "estados": [r["estado"] for r in estados],
        }
