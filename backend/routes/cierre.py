"""
Router: Cierre de Registro → Ingreso PT
Calcula costo MP (FIFO) + costos servicio → genera ingreso PT
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import date
from decimal import Decimal
import uuid
from db import get_pool
from auth import get_current_user
from helpers import row_to_dict

router = APIRouter(prefix="/api", tags=["cierre"])


class CierreRegistroInput(BaseModel):
    empresa_id: int
    fecha: Optional[date] = None
    qty_terminada: Optional[float] = None  # If None, uses total prendas from tallas


class PtItemUpdate(BaseModel):
    pt_item_id: Optional[str] = None


@router.put("/registros/{registro_id}/pt-item")
async def update_pt_item(registro_id: str, data: PtItemUpdate, current_user: dict = Depends(get_current_user)):
    """Asignar o cambiar el artículo PT de un registro"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("SELECT id, estado FROM prod_registros WHERE id = $1", registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        if reg['estado'] in ('CERRADA', 'ANULADA'):
            raise HTTPException(status_code=400, detail="No se puede modificar una OP cerrada/anulada")
        
        if data.pt_item_id:
            item = await conn.fetchrow("SELECT id, codigo, nombre FROM prod_inventario WHERE id = $1", data.pt_item_id)
            if not item:
                raise HTTPException(status_code=404, detail="Item PT no encontrado en inventario")
        
        await conn.execute(
            "UPDATE prod_registros SET pt_item_id = $1 WHERE id = $2",
            data.pt_item_id, registro_id
        )
        return {"message": "PT item actualizado", "pt_item_id": data.pt_item_id}


@router.get("/registros/{registro_id}/preview-cierre")
async def preview_cierre(registro_id: str, current_user: dict = Depends(get_current_user)):
    """Preview del cierre: calcula costos sin ejecutar"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Check if already closed via prod_registro_cierre
        existing_cierre = await conn.fetchrow(
            "SELECT id FROM prod_registro_cierre WHERE registro_id = $1", registro_id
        )
        if existing_cierre:
            raise HTTPException(status_code=400, detail="Este registro ya tiene un cierre registrado")
        
        # qty_terminada from tallas
        total_prendas = await conn.fetchval(
            "SELECT COALESCE(SUM(cantidad_real), 0) FROM prod_registro_tallas WHERE registro_id = $1",
            registro_id
        )
        
        # Costo MP from salidas (FIFO already calculated)
        costo_mp = await conn.fetchval("""
            SELECT COALESCE(SUM(costo_total), 0) FROM prod_inventario_salidas
            WHERE registro_id = $1
        """, registro_id)
        
        # Costo servicios
        costo_servicios = await conn.fetchval("""
            SELECT COALESCE(SUM(monto), 0) FROM prod_registro_costos_servicio
            WHERE registro_id = $1
        """, registro_id)
        
        costo_mp = float(costo_mp or 0)
        costo_servicios = float(costo_servicios or 0)
        costo_total = costo_mp + costo_servicios
        qty = float(total_prendas) if total_prendas else 0
        costo_unit = costo_total / qty if qty > 0 else 0
        
        # PT item info
        pt_item = None
        if reg['pt_item_id']:
            pt_row = await conn.fetchrow(
                "SELECT id, codigo, nombre FROM prod_inventario WHERE id = $1",
                reg['pt_item_id']
            )
            if pt_row:
                pt_item = row_to_dict(pt_row)
        
        # Detalle de salidas MP por item
        salidas_detalle = await conn.fetch("""
            SELECT s.item_id, i.codigo, i.nombre, SUM(s.cantidad) as cantidad_total, 
                   SUM(s.costo_total) as costo_total
            FROM prod_inventario_salidas s
            JOIN prod_inventario i ON s.item_id = i.id
            WHERE s.registro_id = $1
            GROUP BY s.item_id, i.codigo, i.nombre
            ORDER BY i.nombre
        """, registro_id)
        
        return {
            "registro_id": registro_id,
            "n_corte": reg['n_corte'],
            "estado": reg['estado'],
            "pt_item": pt_item,
            "qty_terminada": qty,
            "costo_mp": round(costo_mp, 2),
            "costo_servicios": round(costo_servicios, 2),
            "costo_total": round(costo_total, 2),
            "costo_unit_pt": round(costo_unit, 6),
            "salidas_mp_detalle": [row_to_dict(r) for r in salidas_detalle],
            "puede_cerrar": qty > 0 and reg.get('pt_item_id') is not None
        }


@router.post("/registros/{registro_id}/cierre-produccion")
async def ejecutar_cierre(registro_id: str, data: CierreRegistroInput, current_user: dict = Depends(get_current_user)):
    """Ejecuta el cierre: calcula costos, crea ingreso PT, marca estado"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        async with conn.transaction():
            reg = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
            if not reg:
                raise HTTPException(status_code=404, detail="Registro no encontrado")
            
            if reg['estado'] in ('CERRADA', 'ANULADA'):
                raise HTTPException(status_code=400, detail=f"OP ya está {reg['estado']}")
            
            if not reg['pt_item_id']:
                raise HTTPException(status_code=400, detail="Debe asignar un artículo PT antes de cerrar")
            
            # Check no existing cierre
            existing = await conn.fetchrow("SELECT id FROM prod_registro_cierre WHERE registro_id = $1", registro_id)
            if existing:
                raise HTTPException(status_code=400, detail="Ya existe un cierre para este registro")
            
            # Calculate qty_terminada
            if data.qty_terminada and data.qty_terminada > 0:
                qty_terminada = data.qty_terminada
            else:
                qty_terminada = float(await conn.fetchval(
                    "SELECT COALESCE(SUM(cantidad_real), 0) FROM prod_registro_tallas WHERE registro_id = $1",
                    registro_id
                ) or 0)
            
            if qty_terminada <= 0:
                raise HTTPException(status_code=400, detail="qty_terminada debe ser > 0")
            
            # Costo MP (from FIFO salidas)
            costo_mp = float(await conn.fetchval("""
                SELECT COALESCE(SUM(costo_total), 0) FROM prod_inventario_salidas
                WHERE registro_id = $1
            """, registro_id) or 0)
            
            # Costo servicios
            costo_servicios = float(await conn.fetchval("""
                SELECT COALESCE(SUM(monto), 0) FROM prod_registro_costos_servicio
                WHERE registro_id = $1
            """, registro_id) or 0)
            
            costo_total = costo_mp + costo_servicios
            costo_unit_pt = costo_total / qty_terminada
            
            fecha_cierre = data.fecha or date.today()
            
            # Create PT ingreso
            ingreso_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO prod_inventario_ingresos 
                (id, item_id, cantidad, cantidad_disponible, costo_unitario, 
                 proveedor, numero_documento, observaciones, fecha, empresa_id,
                 fin_origen_tipo, fin_origen_id, fin_numero_doc)
                VALUES ($1, $2, $3, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
                ingreso_id, reg['pt_item_id'], qty_terminada, costo_unit_pt,
                'PRODUCCIÓN', f'CIERRE-{reg["n_corte"]}',
                f'Cierre producción OP {reg["n_corte"]}', fecha_cierre,
                data.empresa_id, 'PROD_CIERRE', registro_id, f'OP-{reg["n_corte"]}'
            )
            
            # Update PT item stock
            await conn.execute("""
                UPDATE prod_inventario 
                SET stock_actual = COALESCE(stock_actual, 0) + $1
                WHERE id = $2
            """, qty_terminada, reg['pt_item_id'])
            
            # Create cierre record
            cierre_id = str(uuid.uuid4())
            await conn.execute("""
                INSERT INTO prod_registro_cierre 
                (id, empresa_id, registro_id, fecha, qty_terminada, costo_mp, 
                 costo_servicios, costo_total, costo_unit_pt, pt_ingreso_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                cierre_id, data.empresa_id, registro_id, fecha_cierre,
                qty_terminada, costo_mp, costo_servicios, costo_total,
                costo_unit_pt, ingreso_id
            )
            
            # Liberar reservas pendientes (reuse existing logic pattern)
            reservas = await conn.fetch("""
                SELECT rl.id, rl.item_id, rl.talla_id, 
                       rl.cantidad_reservada - rl.cantidad_liberada as pendiente
                FROM prod_inventario_reservas_linea rl
                JOIN prod_inventario_reservas r ON rl.reserva_id = r.id
                WHERE r.registro_id = $1 AND r.estado = 'ACTIVA'
                AND rl.cantidad_reservada > rl.cantidad_liberada
            """, registro_id)
            
            for rl in reservas:
                pendiente = float(rl['pendiente'])
                if pendiente > 0:
                    await conn.execute("""
                        UPDATE prod_inventario_reservas_linea 
                        SET cantidad_liberada = cantidad_reservada, updated_at = NOW()
                        WHERE id = $1
                    """, rl['id'])
                    
                    # Update requerimiento
                    await conn.execute("""
                        UPDATE prod_registro_requerimiento_mp 
                        SET cantidad_reservada = cantidad_reservada - $1, updated_at = NOW()
                        WHERE registro_id = $2 AND item_id = $3 
                        AND ($4::varchar IS NULL OR talla_id = $4)
                    """, pendiente, registro_id, rl['item_id'], rl['talla_id'])
            
            # Mark all reservas as CERRADA
            await conn.execute("""
                UPDATE prod_inventario_reservas SET estado = 'CERRADA', updated_at = NOW()
                WHERE registro_id = $1 AND estado = 'ACTIVA'
            """, registro_id)
            
            # Update registro estado
            await conn.execute("""
                UPDATE prod_registros SET estado = 'CERRADA' WHERE id = $1
            """, registro_id)
            
            return {
                "message": f"Cierre completado para OP {reg['n_corte']}",
                "cierre_id": cierre_id,
                "ingreso_pt_id": ingreso_id,
                "qty_terminada": qty_terminada,
                "costo_mp": round(costo_mp, 2),
                "costo_servicios": round(costo_servicios, 2),
                "costo_total": round(costo_total, 2),
                "costo_unit_pt": round(costo_unit_pt, 6)
            }


@router.get("/registros/{registro_id}/cierre-produccion")
async def get_cierre(registro_id: str, current_user: dict = Depends(get_current_user)):
    """Obtiene datos del cierre si existe"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        cierre = await conn.fetchrow("""
            SELECT c.*, i.codigo as pt_codigo, i.nombre as pt_nombre
            FROM prod_registro_cierre c
            LEFT JOIN prod_inventario_ingresos ing ON c.pt_ingreso_id = ing.id
            LEFT JOIN prod_inventario i ON ing.item_id = i.id
            WHERE c.registro_id = $1
        """, registro_id)
        if not cierre:
            return None
        return row_to_dict(cierre)
