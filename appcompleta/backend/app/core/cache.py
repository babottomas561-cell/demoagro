"""
Cache en memoria con TTL para DemoAgro.

Modulo liviano que complementa al CacheService existente en app/services/cache_service.py.
Provee la funcion `cached()` para uso simple en factories de datos.
"""
import time
import logging
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)

# Almacen global: key -> (value, expires_at)
_cache: dict[str, tuple[Any, float]] = {}


async def cached(key: str, ttl: int, factory: Callable[[], Awaitable[Any]]) -> Any:
    """
    Cache en memoria con TTL. Ideal para APIs externas y calculos costosos.

    Args:
        key:     Clave unica del cache.
        ttl:     Tiempo de vida en segundos.
        factory: Coroutine callable que genera el valor si no esta en cache.

    Returns:
        Valor cacheado o nuevo valor generado por factory().

    Example::
        data = await cached(
            key="bcra_tipo_cambio",
            ttl=900,
            factory=lambda: fetch_tipo_cambio(),
        )
    """
    if key in _cache:
        value, expires_at = _cache[key]
        if time.time() < expires_at:
            logger.debug("Cache HIT: %s", key)
            return value
        else:
            del _cache[key]
            logger.debug("Cache EXPIRED: %s", key)

    logger.debug("Cache MISS: %s - llamando factory", key)
    value = await factory()
    _cache[key] = (value, time.time() + ttl)
    return value


def invalidate(key: str) -> bool:
    """
    Invalida una entrada del cache.

    Returns:
        True si existia y fue eliminada, False si no existia.
    """
    if key in _cache:
        del _cache[key]
        logger.debug("Cache INVALIDATED: %s", key)
        return True
    return False


def invalidate_prefix(prefix: str) -> int:
    """
    Invalida todas las entradas cuya clave comience con el prefijo dado.

    Returns:
        Cantidad de entradas eliminadas.
    """
    keys = [k for k in _cache if k.startswith(prefix)]
    for k in keys:
        del _cache[k]
    if keys:
        logger.debug("Cache INVALIDATED PREFIX '%s': %d entradas", prefix, len(keys))
    return len(keys)


def cache_size() -> int:
    """Retorna la cantidad de entradas activas (no expiradas) en el cache."""
    now = time.time()
    active = sum(1 for _, expires_at in _cache.values() if expires_at > now)
    return active


def clear_all() -> int:
    """Limpia completamente el cache. Util para tests."""
    count = len(_cache)
    _cache.clear()
    return count
