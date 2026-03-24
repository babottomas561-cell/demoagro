"""
Servicio de cache con TTL.

Implementa cache usando Redis con fallback automático a dict en memoria
cuando Redis no está disponible.

Orden de prioridad:
1. Redis (si REDIS_URL está configurada y Redis responde)
2. Dict en memoria (proceso local, se pierde al reiniciar)
"""

import json
import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# TTLs por tipo de dato (en segundos)
CACHE_TTLS: dict[str, int] = {
    "bcra_tipo_cambio": 900,        # 15 min
    "bcra_tasas": 3600,             # 1 hora
    "bcra_inflacion": 86400,        # 24 hs
    "bcra_variables": 3600,         # 1 hora
    "bcra_resumen_macro": 900,      # 15 min
    "datos_arg_series": 86400,      # 24 hs
    "arg_ipc": 86400,               # 24 hs
    "arg_tipo_cambio": 86400,       # 24 hs
    "clima_forecast": 3600,         # 1 hora
    "clima_historico": 7200,        # 2 horas
    "clima_alertas": 3600,          # 1 hora
    "clima_resumen": 3600,          # 1 hora
    "commodities_precios": 1800,    # 30 min
    "commodities_historico": 3600,  # 1 hora
    "usda_data": 86400,             # 24 hs
    "bcr_precios": 3600,            # 1 hora
    "insights": 3600,               # 1 hora
    "mercado_resumen": 1800,        # 30 min
    "macro_resumen": 900,           # 15 min
}

DEFAULT_TTL = 1800  # 30 min


class _InMemoryCache:
    """Implementación de cache en memoria con TTL."""

    def __init__(self):
        self._store: dict[str, tuple[Any, float]] = {}  # key → (value, expires_at)

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def get_with_age(self, key: str) -> tuple[Optional[Any], Optional[int]]:
        """Retorna (valor, edad_en_segundos) o (None, None) si no existe."""
        entry = self._store.get(key)
        if entry is None:
            return None, None
        value, expires_at = entry
        now = time.time()
        if now > expires_at:
            del self._store[key]
            return None, None
        ttl_remaining = int(expires_at - now)
        return value, ttl_remaining

    def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        self._store[key] = (value, time.time() + ttl)
        return True

    def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    def delete_pattern(self, pattern: str) -> int:
        import fnmatch
        keys_to_delete = [k for k in self._store if fnmatch.fnmatch(k, pattern)]
        for k in keys_to_delete:
            del self._store[k]
        return len(keys_to_delete)

    def size(self) -> int:
        # Limpiar entradas expiradas
        now = time.time()
        self._store = {k: v for k, v in self._store.items() if v[1] > now}
        return len(self._store)


# Instancia compartida del cache en memoria
_memory_cache = _InMemoryCache()

# Flag de Redis disponibilidad (se detecta en el primer intento)
_redis_available: Optional[bool] = None
_redis_client: Any = None


async def _get_redis_client() -> Optional[Any]:
    """Intenta obtener un cliente Redis. Retorna None si no disponible."""
    global _redis_available, _redis_client

    if _redis_available is False:
        return None

    if _redis_client is not None:
        return _redis_client

    redis_url = os.environ.get("REDIS_URL", "").strip()
    if not redis_url:
        logger.info("REDIS_URL no configurada. Usando cache en memoria.")
        _redis_available = False
        return None

    try:
        import redis.asyncio as aioredis  # type: ignore
        client = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("Redis disponible en %s. Usando Redis como cache.", redis_url)
        return client
    except ImportError:
        logger.warning("Librería redis no instalada. Usando cache en memoria.")
        _redis_available = False
        return None
    except Exception as exc:
        logger.warning("Redis no disponible (%s). Usando cache en memoria.", exc)
        _redis_available = False
        return None


class CacheService:
    """
    Servicio de cache con TTL.

    Usa Redis si está disponible (REDIS_URL configurada), sino usa
    un dict en memoria como fallback transparente.

    Ejemplo:
        cache = CacheService()
        await cache.set("my_key", {"data": 123}, ttl=300)
        value = await cache.get("my_key")
    """

    async def is_available(self) -> bool:
        """Retorna True si Redis está disponible."""
        client = await _get_redis_client()
        return client is not None

    async def get(self, key: str) -> Optional[Any]:
        """
        Obtiene un valor del cache.

        Args:
            key: Clave del cache.

        Returns:
            El valor almacenado, o None si no existe o expiró.
        """
        client = await _get_redis_client()

        if client is not None:
            try:
                raw = await client.get(key)
                if raw is None:
                    return None
                return json.loads(raw)
            except Exception as exc:
                logger.warning("Error leyendo de Redis (key=%s): %s. Fallback a memoria.", key, exc)

        # Fallback a memoria
        return _memory_cache.get(key)

    async def get_with_metadata(self, key: str) -> dict:
        """
        Obtiene un valor junto con metadata del cache (hit, age, backend).

        Returns:
            dict con keys: value, hit, backend, ttl_remaining
        """
        client = await _get_redis_client()

        if client is not None:
            try:
                raw = await client.get(key)
                if raw is not None:
                    ttl_remaining = await client.ttl(key)
                    return {
                        "value": json.loads(raw),
                        "hit": True,
                        "backend": "redis",
                        "ttl_remaining": ttl_remaining,
                    }
            except Exception as exc:
                logger.warning("Error en Redis get_with_metadata (key=%s): %s", key, exc)

        # Fallback a memoria
        value, ttl_remaining = _memory_cache.get_with_age(key)
        return {
            "value": value,
            "hit": value is not None,
            "backend": "memory",
            "ttl_remaining": ttl_remaining,
        }

    async def set(self, key: str, value: Any, ttl: int = DEFAULT_TTL) -> bool:
        """
        Almacena un valor en el cache.

        Args:
            key: Clave del cache.
            value: Valor a almacenar (debe ser serializable a JSON).
            ttl: Tiempo de vida en segundos.

        Returns:
            True si se almacenó correctamente.
        """
        client = await _get_redis_client()
        serialized = json.dumps(value, ensure_ascii=False, default=str)

        if client is not None:
            try:
                await client.setex(key, ttl, serialized)
                return True
            except Exception as exc:
                logger.warning("Error escribiendo en Redis (key=%s): %s. Fallback a memoria.", key, exc)

        # Fallback a memoria
        return _memory_cache.set(key, value, ttl)

    async def invalidate(self, key: str) -> bool:
        """
        Elimina una clave del cache.

        Args:
            key: Clave a eliminar.

        Returns:
            True si se eliminó, False si no existía.
        """
        client = await _get_redis_client()
        deleted = False

        if client is not None:
            try:
                result = await client.delete(key)
                deleted = result > 0
            except Exception as exc:
                logger.warning("Error eliminando de Redis (key=%s): %s", key, exc)

        # También eliminar de memoria por si acaso
        _memory_cache.delete(key)
        return deleted

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Elimina todas las claves que coincidan con el patrón (glob).

        Args:
            pattern: Patrón glob (ej: 'bcra_*', 'clima_*').

        Returns:
            Número de claves eliminadas.
        """
        client = await _get_redis_client()
        count = 0

        if client is not None:
            try:
                keys = await client.keys(pattern)
                if keys:
                    count = await client.delete(*keys)
            except Exception as exc:
                logger.warning("Error en invalidate_pattern Redis (pattern=%s): %s", pattern, exc)

        # También limpiar en memoria
        count += _memory_cache.delete_pattern(pattern)
        return count

    def get_ttl(self, cache_key_prefix: str) -> int:
        """
        Retorna el TTL recomendado para un tipo de dato.

        Args:
            cache_key_prefix: Prefijo del tipo de dato (ver CACHE_TTLS).

        Returns:
            TTL en segundos.
        """
        return CACHE_TTLS.get(cache_key_prefix, DEFAULT_TTL)

    async def cache_status(self) -> dict:
        """Retorna el estado del sistema de cache."""
        redis_available = await self.is_available()
        return {
            "backend": "redis" if redis_available else "memory",
            "redis_available": redis_available,
            "redis_url_configured": bool(os.environ.get("REDIS_URL", "").strip()),
            "memory_cache_size": _memory_cache.size(),
            "ttls_configured": CACHE_TTLS,
        }


# Instancia singleton del servicio
cache_service = CacheService()
