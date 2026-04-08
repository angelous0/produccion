"""
Kardex de Producto Terminado (PT).
Consume datos del schema odoo (stock_move, stock_location, product_template)
y cruza con produccion.prod_registro_pt_odoo_vinculo para clasificar ingresos de produccion.
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional
from datetime import datetime
from db import get_pool
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["kardex-pt"])


CLASIFICACION_CASE = """
    CASE
        WHEN EXISTS(
            SELECT 1 FROM produccion.prod_registro_pt_odoo_vinculo v
            WHERE v.stock_inventory_odoo_id = sm.inventory_id
        ) THEN 'INGRESO_PRODUCCION'
        WHEN sm.inventory_id IS NOT NULL AND ld.usage = 'internal'
            THEN 'AJUSTE_POSITIVO'
        WHEN sm.inventory_id IS NOT NULL AND lo.usage = 'internal'
            THEN 'AJUSTE_NEGATIVO'
        WHEN sm.inventory_id IS NULL AND lo.usage = 'internal' AND ld.usage = 'customer'
            THEN 'SALIDA_VENTA'
        WHEN sm.inventory_id IS NULL AND lo.usage = 'internal' AND ld.usage = 'internal'
            THEN 'TRANSFERENCIA'
        ELSE 'OTRO'
    END
"""

ENTRADA_EXPR = """
    CASE
        WHEN EXISTS(
            SELECT 1 FROM produccion.prod_registro_pt_odoo_vinculo v
            WHERE v.stock_inventory_odoo_id = sm.inventory_id
        ) THEN sm.product_qty
        WHEN sm.inventory_id IS NOT NULL AND ld.usage = 'internal'
            THEN sm.product_qty
        ELSE 0
    END
"""

SALIDA_EXPR = """
    CASE
        WHEN sm.inventory_id IS NOT NULL AND lo.usage = 'internal' AND ld.usage != 'internal'
            THEN sm.product_qty
        WHEN sm.inventory_id IS NULL AND lo.usage = 'internal' AND ld.usage = 'customer'
            THEN sm.product_qty
        ELSE 0
    END
"""


@router.get("/kardex-pt")
async def get_kardex_pt(
    product_tmpl_id: Optional[int] = Query(None),
    tipo_movimiento: Optional[str] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    company_key: Optional[str] = Query(None),
    location_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(get_current_user),
):
    pool = await get_pool()
    async with pool.acquire() as conn:

        # Construir WHERE dinamico
        conditions = ["sm.state = 'done'"]
        params = []
        idx = 1

        # Excluir transferencias del kardex global (salvo filtro por ubicacion)
        if not location_id:
            conditions.append("""
                NOT (sm.inventory_id IS NULL AND lo.usage = 'internal' AND ld.usage = 'internal')
            """)

        if product_tmpl_id:
            conditions.append(f"sm.product_tmpl_id = ${idx}")
            params.append(product_tmpl_id)
            idx += 1

        if fecha_desde:
            conditions.append(f"sm.date >= ${idx}::timestamp")
            params.append(datetime.fromisoformat(fecha_desde))
            idx += 1

        if fecha_hasta:
            conditions.append(f"sm.date <= (${idx}::timestamp + interval '1 day')")
            params.append(datetime.fromisoformat(fecha_hasta))
            idx += 1

        if company_key:
            conditions.append(f"sm.company_key = ${idx}")
            params.append(company_key)
            idx += 1

        if location_id:
            conditions.append(f"(sm.location_id = ${idx} OR sm.location_dest_id = ${idx})")
            params.append(location_id)
            idx += 1

        if tipo_movimiento:
            conditions.append(f"{CLASIFICACION_CASE} = ${idx}")
            params.append(tipo_movimiento)
            idx += 1

        where = " AND ".join(conditions)
        offset = (page - 1) * page_size

        # Count
        count_sql = f"""
            SELECT COUNT(*)
            FROM odoo.stock_move sm
            JOIN odoo.stock_location lo ON lo.odoo_id = sm.location_id
            JOIN odoo.stock_location ld ON ld.odoo_id = sm.location_dest_id
            WHERE {where}
        """
        total = await conn.fetchval(count_sql, *params)

        # Data con saldo acumulado por producto
        data_sql = f"""
            SELECT
                sm.odoo_id,
                sm.date,
                sm.product_tmpl_id,
                pt.name as producto_nombre,
                pt.marca as producto_marca,
                sm.product_qty,
                sm.origin as referencia,
                sm.company_key,
                lo.odoo_id as location_from_id,
                lo.complete_name as location_from,
                ld.odoo_id as location_to_id,
                ld.complete_name as location_to,
                {CLASIFICACION_CASE} as tipo_movimiento,
                ({ENTRADA_EXPR})::numeric as entrada,
                ({SALIDA_EXPR})::numeric as salida,
                SUM({ENTRADA_EXPR} - {SALIDA_EXPR}) OVER (
                    PARTITION BY sm.product_tmpl_id
                    ORDER BY sm.date, sm.odoo_id
                ) as saldo_acumulado
            FROM odoo.stock_move sm
            JOIN odoo.stock_location lo ON lo.odoo_id = sm.location_id
            JOIN odoo.stock_location ld ON ld.odoo_id = sm.location_dest_id
            JOIN odoo.product_template pt ON pt.odoo_id = sm.product_tmpl_id
            WHERE {where}
            ORDER BY sm.date DESC, sm.odoo_id DESC
            LIMIT {page_size} OFFSET {offset}
        """
        rows = await conn.fetch(data_sql, *params)

        items = []
        for r in rows:
            items.append({
                "odoo_id": r["odoo_id"],
                "fecha": r["date"].isoformat() if r["date"] else None,
                "product_tmpl_id": r["product_tmpl_id"],
                "producto_nombre": r["producto_nombre"],
                "producto_marca": r["producto_marca"],
                "tipo_movimiento": r["tipo_movimiento"],
                "entrada": float(r["entrada"]),
                "salida": float(r["salida"]),
                "saldo_acumulado": float(r["saldo_acumulado"]),
                "referencia": r["referencia"],
                "company_key": r["company_key"],
                "location_from": r["location_from"],
                "location_to": r["location_to"],
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }


@router.get("/kardex-pt/resumen")
async def get_kardex_pt_resumen(
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    company_key: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """Resumen agrupado por producto: total entradas, salidas, saldo."""
    pool = await get_pool()
    async with pool.acquire() as conn:

        conditions = ["sm.state = 'done'"]
        # Excluir transferencias internas del resumen global
        conditions.append("NOT (sm.inventory_id IS NULL AND lo.usage = 'internal' AND ld.usage = 'internal')")
        params = []
        idx = 1

        if fecha_desde:
            conditions.append(f"sm.date >= ${idx}::timestamp")
            params.append(datetime.fromisoformat(fecha_desde))
            idx += 1

        if fecha_hasta:
            conditions.append(f"sm.date <= (${idx}::timestamp + interval '1 day')")
            params.append(datetime.fromisoformat(fecha_hasta))
            idx += 1

        if company_key:
            conditions.append(f"sm.company_key = ${idx}")
            params.append(company_key)
            idx += 1

        where = " AND ".join(conditions)

        sql = f"""
            SELECT
                sm.product_tmpl_id,
                pt.name as producto_nombre,
                pt.marca as producto_marca,
                SUM({ENTRADA_EXPR}) as total_entradas,
                SUM({SALIDA_EXPR}) as total_salidas,
                SUM({ENTRADA_EXPR} - {SALIDA_EXPR}) as saldo
            FROM odoo.stock_move sm
            JOIN odoo.stock_location lo ON lo.odoo_id = sm.location_id
            JOIN odoo.stock_location ld ON ld.odoo_id = sm.location_dest_id
            JOIN odoo.product_template pt ON pt.odoo_id = sm.product_tmpl_id
            WHERE {where}
            GROUP BY sm.product_tmpl_id, pt.name, pt.marca
            HAVING SUM({ENTRADA_EXPR}) > 0 OR SUM({SALIDA_EXPR}) > 0
            ORDER BY pt.name
        """
        rows = await conn.fetch(sql, *params)

        productos = []
        for r in rows:
            productos.append({
                "product_tmpl_id": r["product_tmpl_id"],
                "producto_nombre": r["producto_nombre"],
                "producto_marca": r["producto_marca"],
                "total_entradas": float(r["total_entradas"]),
                "total_salidas": float(r["total_salidas"]),
                "saldo": float(r["saldo"]),
            })

        return {
            "productos": productos,
            "totales": {
                "entradas": sum(p["total_entradas"] for p in productos),
                "salidas": sum(p["total_salidas"] for p in productos),
                "saldo": sum(p["saldo"] for p in productos),
            }
        }


@router.get("/kardex-pt/filtros")
async def get_kardex_pt_filtros(current_user: dict = Depends(get_current_user)):
    """Retorna opciones de filtro disponibles."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        # Company keys
        companies = await conn.fetch(
            "SELECT DISTINCT company_key FROM odoo.stock_move WHERE state='done' ORDER BY company_key"
        )
        # Ubicaciones internas
        locations = await conn.fetch(
            "SELECT odoo_id, name, complete_name FROM odoo.stock_location WHERE usage='internal' ORDER BY name"
        )
        return {
            "company_keys": [c["company_key"] for c in companies],
            "ubicaciones": [
                {"id": l["odoo_id"], "name": l["name"], "complete_name": l["complete_name"]}
                for l in locations
            ],
            "tipos_movimiento": [
                {"value": "INGRESO_PRODUCCION", "label": "Ingreso Produccion"},
                {"value": "SALIDA_VENTA", "label": "Salida Venta"},
                {"value": "AJUSTE_POSITIVO", "label": "Ajuste Positivo"},
                {"value": "AJUSTE_NEGATIVO", "label": "Ajuste Negativo"},
                {"value": "TRANSFERENCIA", "label": "Transferencia"},
            ]
        }
