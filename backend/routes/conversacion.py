from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date
import uuid

router = APIRouter(prefix="/api", tags=["Conversacion"])


class MensajeCreate(BaseModel):
    autor: str
    mensaje: str
    mensaje_padre_id: Optional[str] = None


def row_to_dict(row):
    if row is None:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, (datetime, date)):
            d[k] = v.isoformat()
    return d


@router.get("/registros/{registro_id}/conversacion")
async def get_conversacion(registro_id: str):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT * FROM prod_conversacion WHERE registro_id = $1 ORDER BY created_at ASC",
            registro_id
        )
        return [row_to_dict(r) for r in rows]


@router.post("/registros/{registro_id}/conversacion")
async def create_mensaje(registro_id: str, input: MensajeCreate):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        if not input.mensaje.strip():
            raise HTTPException(status_code=400, detail="El mensaje no puede estar vacio")
        if input.mensaje_padre_id:
            parent = await conn.fetchval(
                "SELECT id FROM prod_conversacion WHERE id = $1 AND registro_id = $2",
                input.mensaje_padre_id, registro_id
            )
            if not parent:
                raise HTTPException(status_code=404, detail="Mensaje padre no encontrado")
        msg_id = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO prod_conversacion (id, registro_id, mensaje_padre_id, autor, mensaje, created_at)
               VALUES ($1, $2, $3, $4, $5, NOW())""",
            msg_id, registro_id, input.mensaje_padre_id, input.autor.strip(), input.mensaje.strip()
        )
        row = await conn.fetchrow("SELECT * FROM prod_conversacion WHERE id = $1", msg_id)
        return row_to_dict(row)


@router.delete("/conversacion/{mensaje_id}")
async def delete_mensaje(mensaje_id: str):
    from server import get_pool
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM prod_conversacion WHERE mensaje_padre_id = $1", mensaje_id)
        await conn.execute("DELETE FROM prod_conversacion WHERE id = $1", mensaje_id)
        return {"ok": True}
