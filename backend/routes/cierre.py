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
import json
from db import get_pool
from auth import get_current_user
from helpers import row_to_dict

router = APIRouter(prefix="/api", tags=["cierre"])


class CierreRegistroInput(BaseModel):
    empresa_id: Optional[int] = None
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
        
        # Costo servicios (desde movimientos de producción - fuente única)
        costo_servicios = await conn.fetchval("""
            SELECT COALESCE(SUM(costo_calculado), 0) FROM prod_movimientos_produccion
            WHERE registro_id = $1
        """, registro_id)
        
        # Otros costos adicionales (no servicios de producción)
        otros_costos = await conn.fetchval("""
            SELECT COALESCE(SUM(monto), 0) FROM prod_registro_costos_servicio
            WHERE registro_id = $1
        """, registro_id)
        
        costo_mp = float(costo_mp or 0)
        costo_servicios = float(costo_servicios or 0)
        otros_costos = float(otros_costos or 0)
        costo_total = costo_mp + costo_servicios + otros_costos
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
        
        # Detalle de movimientos de producción (servicios)
        movimientos_detalle = await conn.fetch("""
            SELECT mp.servicio_id, sp.nombre as servicio_nombre,
                   SUM(mp.cantidad_recibida) as cantidad_total,
                   SUM(mp.costo_calculado) as costo_total
            FROM prod_movimientos_produccion mp
            LEFT JOIN prod_servicios_produccion sp ON mp.servicio_id = sp.id
            WHERE mp.registro_id = $1
            GROUP BY mp.servicio_id, sp.nombre
            ORDER BY sp.nombre
        """, registro_id)
        
        return {
            "registro_id": registro_id,
            "n_corte": reg['n_corte'],
            "estado": reg['estado'],
            "pt_item": pt_item,
            "qty_terminada": qty,
            "costo_mp": round(costo_mp, 2),
            "costo_servicios": round(costo_servicios, 2),
            "otros_costos": round(otros_costos, 2),
            "costo_total": round(costo_total, 2),
            "costo_unit_pt": round(costo_unit, 6),
            "salidas_mp_detalle": [row_to_dict(r) for r in salidas_detalle],
            "movimientos_detalle": [row_to_dict(r) for r in movimientos_detalle],
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
            
            # Costo servicios (desde movimientos de producción - fuente única)
            costo_servicios = float(await conn.fetchval("""
                SELECT COALESCE(SUM(costo_calculado), 0) FROM prod_movimientos_produccion
                WHERE registro_id = $1
            """, registro_id) or 0)
            
            # Otros costos adicionales
            otros_costos = float(await conn.fetchval("""
                SELECT COALESCE(SUM(monto), 0) FROM prod_registro_costos_servicio
                WHERE registro_id = $1
            """, registro_id) or 0)
            
            costo_total = costo_mp + costo_servicios + otros_costos
            costo_unit_pt = costo_total / qty_terminada
            
            fecha_cierre = data.fecha or date.today()
            # Use empresa_id from data, or from registro, or default valid FK
            empresa_id = data.empresa_id or reg.get('empresa_id') or 7
            # Ensure empresa_id is valid for finanzas2.cont_empresa FK
            valid_empresa = await conn.fetchval("SELECT id FROM finanzas2.cont_empresa WHERE id = $1", empresa_id)
            if not valid_empresa:
                empresa_id = await conn.fetchval("SELECT id FROM finanzas2.cont_empresa ORDER BY id LIMIT 1") or 7
            
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
                empresa_id, 'PROD_CIERRE', registro_id, f'OP-{reg["n_corte"]}'
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
                cierre_id, empresa_id, registro_id, fecha_cierre,
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
            
            # Update registro estado (both estado and estado_op)
            await conn.execute("""
                UPDATE prod_registros SET estado = 'CERRADA', estado_op = 'CERRADA' WHERE id = $1
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


@router.get("/registros/{registro_id}/balance-pdf")
async def get_balance_pdf(registro_id: str, current_user: dict = Depends(get_current_user)):
    """Genera PDF detallado del balance del lote"""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from fastapi.responses import StreamingResponse
    import io
    from datetime import datetime

    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")

        modelo = await conn.fetchrow("SELECT m.nombre, ma.nombre as marca_nombre FROM prod_modelos m LEFT JOIN prod_marcas ma ON m.marca_id = ma.id WHERE m.id = $1", reg['modelo_id']) if reg['modelo_id'] else None
        tallas = await conn.fetch("SELECT talla_id, cantidad_real FROM prod_registro_tallas WHERE registro_id = $1", registro_id)
        total_prendas = sum(int(t['cantidad_real']) for t in tallas)

        # Obtener nombres de tallas
        tallas_info = json.loads(reg['tallas']) if reg.get('tallas') else []
        tallas_map_nombre = {t.get('id', t.get('talla_id', '')): t.get('nombre', t.get('talla', '')) for t in tallas_info}

        # Movimientos
        movs = await conn.fetch("""
            SELECT m.*, s.nombre as servicio_nombre
            FROM prod_movimientos_produccion m
            LEFT JOIN prod_servicios_produccion s ON m.servicio_id = s.id
            WHERE m.registro_id = $1 ORDER BY m.fecha_inicio
        """, registro_id)

        # Mermas
        mermas = await conn.fetch("SELECT * FROM prod_mermas WHERE registro_id = $1", registro_id)
        total_mermas = sum(float(m.get('cantidad', 0) or 0) for m in mermas)

        # Cierre
        cierre = await conn.fetchrow("SELECT * FROM prod_registro_cierre WHERE registro_id = $1", registro_id)

        # Materiales consumidos
        salidas = await conn.fetch("""
            SELECT s.*, i.nombre as item_nombre, i.codigo as item_codigo
            FROM prod_inventario_salidas s
            JOIN prod_inventario i ON s.item_id = i.id
            WHERE s.registro_id = $1
        """, registro_id)
        total_costo_mp = sum(float(s.get('costo_total', 0) or 0) for s in salidas)

        # Generar PDF
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5*cm, bottomMargin=1.5*cm, leftMargin=2*cm, rightMargin=2*cm)
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, spaceAfter=6)
        subtitle_style = ParagraphStyle('Subtitle', parent=styles['Heading2'], fontSize=12, spaceAfter=4)
        normal = styles['Normal']

        elements = []

        # Header
        elements.append(Paragraph(f"Balance del Lote — {reg['n_corte']}", title_style))
        elements.append(Paragraph(f"Modelo: {modelo['nombre'] if modelo else 'N/A'} | Marca: {modelo['marca_nombre'] if modelo and modelo.get('marca_nombre') else 'N/A'}", normal))
        elements.append(Paragraph(f"Estado: {reg['estado']} | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", normal))
        if reg.get('id_odoo'):
            elements.append(Paragraph(f"ID Odoo: {reg['id_odoo']}", normal))
        if reg.get('lq_odoo_id'):
            elements.append(Paragraph(f"ID Odoo Liquidación: {reg['lq_odoo_id']}", normal))
        elements.append(Spacer(1, 0.5*cm))

        # Tallas
        elements.append(Paragraph("Distribución por Tallas", subtitle_style))
        talla_data = [['Talla', 'Cantidad']]
        for t in tallas:
            nombre = tallas_map_nombre.get(t['talla_id'], t['talla_id'])
            talla_data.append([nombre, str(int(t['cantidad_real']))])
        talla_data.append(['TOTAL', str(total_prendas)])
        t_table = Table(talla_data, colWidths=[8*cm, 4*cm])
        t_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f9ff')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(t_table)
        elements.append(Spacer(1, 0.5*cm))

        # Balance de cantidades
        elements.append(Paragraph("Balance de Cantidades", subtitle_style))
        en_produccion = total_prendas - int(total_mermas)
        bal_data = [
            ['Concepto', 'Cantidad'],
            ['Cantidad Inicial', str(total_prendas)],
            ['En Producción', str(en_produccion)],
            ['Mermas / Faltantes', str(int(total_mermas))],
        ]
        bal_table = Table(bal_data, colWidths=[8*cm, 4*cm])
        bal_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(bal_table)
        elements.append(Spacer(1, 0.5*cm))

        # Movimientos de producción
        if movs:
            elements.append(Paragraph("Movimientos de Producción", subtitle_style))
            mov_data = [['Servicio', 'Enviado', 'Recibido', 'Fecha Envío', 'Estado']]
            for m in movs:
                fecha = str(m['fecha_inicio'])[:10] if m.get('fecha_inicio') else '-'
                estado = 'Completado' if m.get('fecha_fin') else 'En proceso'
                mov_data.append([
                    m.get('servicio_nombre', '-'),
                    str(int(m.get('cantidad_enviada', 0) or 0)),
                    str(int(m.get('cantidad_recibida', 0) or 0)),
                    fecha,
                    estado,
                ])
            mov_table = Table(mov_data, colWidths=[4*cm, 2.5*cm, 2.5*cm, 2.5*cm, 2.5*cm])
            mov_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(mov_table)
            elements.append(Spacer(1, 0.5*cm))

        # Materiales consumidos
        if salidas:
            elements.append(Paragraph("Materiales Consumidos", subtitle_style))
            sal_data = [['Material', 'Cantidad', 'Costo']]
            for s in salidas:
                sal_data.append([
                    s.get('item_nombre', '-'),
                    f"{float(s.get('cantidad', 0)):.1f}",
                    f"S/ {float(s.get('costo_total', 0) or 0):.2f}",
                ])
            sal_data.append(['TOTAL MATERIALES', '', f"S/ {total_costo_mp:.2f}"])
            sal_table = Table(sal_data, colWidths=[6*cm, 3*cm, 3*cm])
            sal_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0f9ff')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
                ('TOPPADDING', (0, 0), (-1, -1), 3),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ]))
            elements.append(sal_table)
            elements.append(Spacer(1, 0.5*cm))

        # Resumen de costos (si hay cierre)
        if cierre:
            elements.append(Paragraph("Resumen de Costos", subtitle_style))
            cost_data = [
                ['Concepto', 'Monto'],
                ['Costo MP (FIFO)', f"S/ {float(cierre.get('costo_mp', 0) or 0):.2f}"],
                ['Costo Servicios', f"S/ {float(cierre.get('costo_servicios', 0) or 0):.2f}"],
                ['COSTO TOTAL', f"S/ {float(cierre.get('costo_total', 0) or 0):.2f}"],
            ]
            if total_prendas > 0:
                costo_unit = float(cierre.get('costo_total', 0) or 0) / total_prendas
                cost_data.append(['Costo Unitario', f"S/ {costo_unit:.2f}"])
            cost_table = Table(cost_data, colWidths=[8*cm, 4*cm])
            cost_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#dcfce7')),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ]))
            elements.append(cost_table)

        doc.build(elements)
        buffer.seek(0)

        filename = f"Balance_{reg['n_corte'].replace(' ', '_')}.pdf"
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
