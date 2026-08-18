import asyncpg
from .config import get_settings

_pool: asyncpg.Pool | None = None


async def init_pool() -> asyncpg.Pool | None:
    # MODE=local iken pool hiç kurulmaz; DB'ye tek satır bile yazılmaz.
    # MODE=prod iken bağlantı hatası bilerek yukarı fırlar — fail-fast korunur.
    global _pool
    if get_settings().MODE == "local":
        return None
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=get_settings().DATABASE_URL,
            min_size=1,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def persistence_enabled() -> bool:
    return _pool is not None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized")
    return _pool
