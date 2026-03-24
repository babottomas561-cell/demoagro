# Macro router - indicadores macroeconomicos argentinos
# Incluye endpoints simulados (compatibilidad) y endpoints reales (BCRA + datos.gob.ar)
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from datetime import date

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/macro")
async def get_macro_data():
    """Indicadores macroeconomicos simulados para demo agro."""
    today = date.today()
    return {
        "tipo_cambio": {
            "oficial": 865.0,
            "blue": 1050.0,
            "mep": 1020.0,
            "ccl": 1035.0,
            "soja": 900.0,
            "fecha": today.isoformat(),
        },
        "precios_granos_usd": [
            {"cultivo": "Soja", "precio_mat": 295.0, "precio_disponible": 292.0, "precio_ars": 252980.0, "variacion_dia": -0.8, "variacion_semana": 1.2},
            {"cultivo": "Maiz", "precio_mat": 175.0, "precio_disponible": 173.0, "precio_ars": 149645.0, "variacion_dia": 0.5, "variacion_semana": -0.3},
            {"cultivo": "Trigo", "precio_mat": 220.0, "precio_disponible": 218.0, "precio_ars": 188570.0, "variacion_dia": 0.2, "variacion_semana": 2.1},
            {"cultivo": "Girasol", "precio_mat": 395.0, "precio_disponible": 390.0, "precio_ars": 337350.0, "variacion_dia": 1.1, "variacion_semana": 3.5},
            {"cultivo": "Sorgo", "precio_mat": 145.0, "precio_disponible": 143.0, "precio_ars": 123695.0, "variacion_dia": -0.2, "variacion_semana": 0.8},
        ],
        "indicadores": [
            {"nombre": "IPC Mensual", "valor": 8.8, "variacion": -1.2, "unidad": "%", "fecha": today.isoformat()},
            {"nombre": "IPC Interanual", "valor": 143.5, "variacion": -25.3, "unidad": "%", "fecha": today.isoformat()},
            {"nombre": "Reservas BCRA", "valor": 28500, "variacion": 1200, "unidad": "M USD", "fecha": today.isoformat()},
            {"nombre": "Tasa Politica Monetaria", "valor": 40.0, "variacion": -10.0, "unidad": "% TNA", "fecha": today.isoformat()},
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints reales con datos del BCRA y datos.gob.ar
# ─────────────────────────────────────────────────────────────────────────────

from app.services.external_data_service import ExternalDataService  # noqa: E402
from app.services.cache_service import cache_service  # noqa: E402

_ext_service = ExternalDataService()


@router.get("/macro/resumen")
async def get_macro_resumen():
    """
    Resumen macroeconomico completo con datos reales del BCRA y datos.gob.ar.

    Incluye tipo de cambio, inflacion, tasas, reservas y series historicas.
    Fuente: https://api.bcra.gob.ar + https://apis.datos.gob.ar
    Cache TTL: 15 minutos
    """
    try:
        return await _ext_service.get_macro_resumen()
    except Exception as exc:
        logger.exception("Error en /macro/resumen: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/macro/series")
async def get_macro_series(
    serie: Literal["ipc", "tipo_cambio", "pbi", "ventas_super"] = Query(
        "ipc",
        description="Tipo de serie: ipc, tipo_cambio, pbi, ventas_super",
    ),
    limit: int = Query(36, ge=1, le=200, description="Cantidad maxima de observaciones"),
):
    """
    Series temporales para graficos macroeconomicos.
    Fuente: API de Series de Tiempo datos.gob.ar. Cache TTL: 24 horas.
    """
    try:
        return await _ext_service.get_macro_series(serie=serie, limit=limit)
    except Exception as exc:
        logger.exception("Error en /macro/series: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/macro/tipo-cambio")
async def get_tipo_cambio_real():
    """
    Tipo de cambio minorista y mayorista vigente del BCRA.
    Variables ID 4 y ID 5. Cache TTL: 15 minutos.
    """
    from app.integrations.bcra_client import BCRAClient

    cache_key = "bcra_tipo_cambio"
    cached = await cache_service.get(cache_key)
    if cached:
        if isinstance(cached, dict) and "metadata" in cached:
            cached["metadata"]["cache_hit"] = True
        return cached
    try:
        data = await BCRAClient().get_tipo_cambio()
        await cache_service.set(cache_key, data, ttl=900)
        return data
    except Exception as exc:
        logger.exception("Error en /macro/tipo-cambio: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/macro/inflacion")
async def get_inflacion_real():
    """
    IPC mensual, interanual e inflacion esperada del BCRA.
    Variables ID 27, 28, 29. Cache TTL: 24 horas.
    """
    from app.integrations.bcra_client import BCRAClient

    cache_key = "bcra_inflacion"
    cached = await cache_service.get(cache_key)
    if cached:
        if isinstance(cached, dict) and "metadata" in cached:
            cached["metadata"]["cache_hit"] = True
        return cached
    try:
        data = await BCRAClient().get_inflacion()
        await cache_service.set(cache_key, data, ttl=86400)
        return data
    except Exception as exc:
        logger.exception("Error en /macro/inflacion: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/macro/tasas")
async def get_tasas_real():
    """
    Tasa de politica monetaria del BCRA. Variable ID 7. Cache TTL: 1 hora.
    """
    from app.integrations.bcra_client import BCRAClient

    cache_key = "bcra_tasas"
    cached = await cache_service.get(cache_key)
    if cached:
        if isinstance(cached, dict) and "metadata" in cached:
            cached["metadata"]["cache_hit"] = True
        return cached
    try:
        data = await BCRAClient().get_tasas()
        await cache_service.set(cache_key, data, ttl=3600)
        return data
    except Exception as exc:
        logger.exception("Error en /macro/tasas: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
