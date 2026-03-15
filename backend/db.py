# Database connection pool management
import asyncpg
import os
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgres://admin:admin@72.60.241.216:9091/datos?sslmode=disable')

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

async def close_pool():
    global pool
    if pool:
        await pool.close()
