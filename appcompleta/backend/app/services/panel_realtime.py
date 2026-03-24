"""
Capa de realtime para paneles operativos.

Cada endpoint de panel pasa por aquí antes de tocar el ERP.
- El resultado se cachea N segundos (configurable por panel).
- Si el ERP no responde, el último valor en cache se sirve con flag stale=True.
- La clave de cache incluye los filtros activos para que distintos scopes
  no colisionen entre sí.

USO en un router:
    from app.services.panel_realtime import cached_panel

    @router.get("/produccion/campo")
    async def produccion_campo(..., db: AsyncSession = Depends(get_db)):
        return await cached_panel(
            "produccion", filters,
            lambda: get_produccion_campo(db, filters),
        )
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Awaitable, Callable

from app.services.cache_service import cache_service
from app.services.lemon_panel_utils import LemonFilters

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# TTL por panel (segundos).
# Paneles operativos en tiempo real: 3s.
# Paneles de campo (riego, sanidad) cambian menos seguido: 5s.
# Macro usa fuentes externas que no cambian cada 3s: 15s.
# ─────────────────────────────────────────────────────────────
PANEL_TTL: dict[str, int] = {
    "produccion": 3,
    "calidad":    3,
    "packhouse":  3,
    "comercial":  3,
    "gerencia":   3,
    "sanidad":    5,
    "riego":      5,
    "macro":     15,
}

_DEFAULT_TTL = 3


def _cache_key(panel: str, filters: LemonFilters) -> str:
    """Clave única por panel + combinación de filtros activos."""
    raw = json.dumps(filters.__dict__, sort_keys=True, default=str)
    digest = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"panel_rt:{panel}:{digest}"


async def cached_panel(
    panel: str,
    filters: LemonFilters,
    compute: Callable[[], Awaitable[Any]],
) -> Any:
    """
    Devuelve el resultado del panel desde cache si está fresco.
    Si el cache expiró o no existe, llama a compute() — que va al ERP —
    y guarda el resultado con el TTL correspondiente.

    Args:
        panel:   Nombre del panel (clave en PANEL_TTL).
        filters: Filtros activos del request.
        compute: Corrutina que ejecuta la consulta al ERP / servicio.

    Returns:
        Dict con los datos del panel, tal como lo retorna el servicio.
    """
    key = _cache_key(panel, filters)
    ttl = PANEL_TTL.get(panel, _DEFAULT_TTL)

    cached = await cache_service.get(key)
    if cached is not None:
        return cached

    try:
        result = await compute()
        await cache_service.set(key, result, ttl=ttl)
        return result
    except Exception as exc:
        logger.error("Panel %s — error consultando ERP: %s", panel, exc)
        raise
