from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone, date
import uuid

router = APIRouter(prefix="/api", tags=["Control Producción"])

# ========== MODELS ==========

class IncidenciaCreate(BaseModel):
    registro_id: str
    tipo: str
    comentario: str = ""
    usuario: str = ""

class IncidenciaUpdate(BaseModel):
    estado: str  # ABIERTA | RESUELTA

class ParalizacionCreate(BaseModel):
    registro_id: str
    motivo: str
    comentario: str = ""

# ========== HELPERS ==========

def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
    return d

# ========== INCIDENCIAS ==========

@router.get("/incidencias/{registro_id}")
async def get_incidencias(registro_id: str):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM prod_incidencia WHERE registro_id = $1 ORDER BY fecha_hora DESC",
            registro_id
        )
        return [row_to_dict(r) for r in rows]

@router.post("/incidencias")
async def create_incidencia(input: IncidenciaCreate):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("SELECT id FROM prod_registros WHERE id = $1", input.registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        inc_id = str(uuid.uuid4())
        now = datetime.now()
        await conn.execute(
            """INSERT INTO prod_incidencia (id, registro_id, fecha_hora, usuario, tipo, comentario, estado, created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,$6,'ABIERTA',$7,$7)""",
            inc_id, input.registro_id, now, input.usuario, input.tipo, input.comentario, now
        )
        row = await conn.fetchrow("SELECT * FROM prod_incidencia WHERE id = $1", inc_id)
        return row_to_dict(row)

@router.put("/incidencias/{incidencia_id}")
async def update_incidencia(incidencia_id: str, input: IncidenciaUpdate):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM prod_incidencia WHERE id = $1", incidencia_id)
        if not row:
            raise HTTPException(status_code=404, detail="Incidencia no encontrada")
        
        await conn.execute(
            "UPDATE prod_incidencia SET estado = $1, updated_at = $2 WHERE id = $3",
            input.estado, datetime.now(), incidencia_id
        )
        updated = await conn.fetchrow("SELECT * FROM prod_incidencia WHERE id = $1", incidencia_id)
        return row_to_dict(updated)

@router.delete("/incidencias/{incidencia_id}")
async def delete_incidencia(incidencia_id: str):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_incidencia WHERE id = $1", incidencia_id)
        return {"message": "Incidencia eliminada"}

# ========== PARALIZACIONES ==========

@router.get("/paralizaciones/{registro_id}")
async def get_paralizaciones(registro_id: str):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM prod_paralizacion WHERE registro_id = $1 ORDER BY fecha_inicio DESC",
            registro_id
        )
        return [row_to_dict(r) for r in rows]

@router.post("/paralizaciones")
async def create_paralizacion(input: ParalizacionCreate):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("SELECT id FROM prod_registros WHERE id = $1", input.registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        # Check no active paralizacion
        active = await conn.fetchrow(
            "SELECT id FROM prod_paralizacion WHERE registro_id = $1 AND activa = TRUE",
            input.registro_id
        )
        if active:
            raise HTTPException(status_code=400, detail="Ya existe una paralización activa para este registro")
        
        par_id = str(uuid.uuid4())
        now = datetime.now()
        await conn.execute(
            """INSERT INTO prod_paralizacion (id, registro_id, fecha_inicio, motivo, comentario, activa, created_at, updated_at)
               VALUES ($1,$2,$3,$4,$5,TRUE,$6,$6)""",
            par_id, input.registro_id, now, input.motivo, input.comentario, now
        )
        
        # Update estado_operativo
        await conn.execute(
            "UPDATE prod_registros SET estado_operativo = 'PARALIZADA' WHERE id = $1",
            input.registro_id
        )
        
        row = await conn.fetchrow("SELECT * FROM prod_paralizacion WHERE id = $1", par_id)
        return row_to_dict(row)

@router.put("/paralizaciones/{paralizacion_id}/levantar")
async def levantar_paralizacion(paralizacion_id: str):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM prod_paralizacion WHERE id = $1", paralizacion_id)
        if not row:
            raise HTTPException(status_code=404, detail="Paralización no encontrada")
        if not row['activa']:
            raise HTTPException(status_code=400, detail="Esta paralización ya fue levantada")
        
        now = datetime.now()
        await conn.execute(
            "UPDATE prod_paralizacion SET activa = FALSE, fecha_fin = $1, updated_at = $1 WHERE id = $2",
            now, paralizacion_id
        )
        
        # Recalculate estado_operativo
        registro_id = row['registro_id']
        reg = await conn.fetchrow("SELECT fecha_entrega_esperada, estado FROM prod_registros WHERE id = $1", registro_id)
        
        new_estado = 'NORMAL'
        if reg and reg['fecha_entrega_esperada']:
            if reg['fecha_entrega_esperada'] < date.today() and reg['estado'] != 'Almacén PT':
                new_estado = 'EN_RIESGO'
        
        await conn.execute(
            "UPDATE prod_registros SET estado_operativo = $1 WHERE id = $2",
            new_estado, registro_id
        )
        
        updated = await conn.fetchrow("SELECT * FROM prod_paralizacion WHERE id = $1", paralizacion_id)
        return row_to_dict(updated)

# ========== UPDATE REGISTRO FIELDS ==========

@router.put("/registros/{registro_id}/control")
async def update_registro_control(registro_id: str, data: dict):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        reg = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        if not reg:
            raise HTTPException(status_code=404, detail="Registro no encontrado")
        
        sets = []
        params = []
        idx = 1
        
        if 'fecha_entrega_esperada' in data:
            val = data['fecha_entrega_esperada']
            if val:
                from datetime import datetime as dt
                try:
                    parsed = dt.strptime(val, '%Y-%m-%d').date()
                    params.append(parsed)
                except:
                    params.append(None)
            else:
                params.append(None)
            sets.append(f"fecha_entrega_esperada = ${idx}")
            idx += 1
        
        if 'responsable_actual' in data:
            params.append(data['responsable_actual'] or None)
            sets.append(f"responsable_actual = ${idx}")
            idx += 1
        
        if not sets:
            return {"message": "Nada que actualizar"}
        
        params.append(registro_id)
        query = f"UPDATE prod_registros SET {', '.join(sets)} WHERE id = ${idx}"
        await conn.execute(query, *params)
        
        # Recalculate estado_operativo
        active_par = await conn.fetchrow(
            "SELECT id FROM prod_paralizacion WHERE registro_id = $1 AND activa = TRUE", registro_id
        )
        updated_reg = await conn.fetchrow("SELECT * FROM prod_registros WHERE id = $1", registro_id)
        
        new_estado = 'NORMAL'
        if active_par:
            new_estado = 'PARALIZADA'
        elif updated_reg['fecha_entrega_esperada'] and updated_reg['fecha_entrega_esperada'] < date.today() and updated_reg['estado'] != 'Almacén PT':
            new_estado = 'EN_RIESGO'
        
        await conn.execute("UPDATE prod_registros SET estado_operativo = $1 WHERE id = $2", new_estado, registro_id)
        
        return {"message": "Actualizado", "estado_operativo": new_estado}
