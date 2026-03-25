# Database connection pool management
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Conexión única - NO usar fallbacks
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL no configurado en .env")

pool = None

async def get_pool():
    global pool
    if pool is None or pool._closed:
        pool = await asyncpg.create_pool(
            DATABASE_URL,
            min_size=2,
            max_size=10,
            command_timeout=30,
            max_inactive_connection_lifetime=60,
            server_settings={"search_path": "produccion,public"},
        )
    return pool

async def close_pool():
    global pool
    if pool:
        await pool.close()
        pool = None
