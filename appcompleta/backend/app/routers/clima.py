# Clima router - datos climaticos simulados para zonas pampeanas
from fastapi import APIRouter, Query
from datetime import date, timedelta

router = APIRouter()


@router.get("/clima/actual")
async def get_clima_actual(
    lat: float = Query(-34.6),
    lon: float = Query(-60.5),
):
    """Datos climaticos actuales simulados para zona pampeana."""
    return {
        "lat": lat, "lon": lon,
        "fecha": date.today().isoformat(),
        "temperatura_actual": 22.4,
        "temperatura_max": 27.8,
        "temperatura_min": 14.2,
        "sensacion_termica": 21.0,
        "humedad_pct": 68,
        "presion_hpa": 1013,
        "viento_kmh": 18,
        "viento_direccion": "SE",
        "precipitaciones_mm": 0,
        "condicion": "Parcialmente nublado",
    }


@router.get("/clima/pronostico")
async def get_pronostico(
    lat: float = Query(-34.6),
    lon: float = Query(-60.5),
    dias: int = Query(7, ge=1, le=14),
):
    """Pronostico simulado para zona pampeana."""
    today = date.today()
    conds = [
        ("Soleado", 0, 32, 17), ("Parcialmente nublado", 0, 28, 14),
        ("Lluvia leve", 12, 20, 11), ("Nublado", 2, 22, 12),
        ("Soleado", 0, 30, 15), ("Tormenta", 45, 17, 10),
        ("Soleado", 0, 31, 17), ("Parcialmente nublado", 0, 29, 16),
        ("Lluvia moderada", 28, 18, 10), ("Soleado", 0, 33, 18),
        ("Nublado", 5, 24, 13), ("Lluvia leve", 15, 21, 12),
        ("Soleado", 0, 31, 17), ("Parcialmente nublado", 0, 28, 15),
    ]
    pronostico = []
    for i in range(dias):
        c = conds[i % len(conds)]
        pronostico.append({
            "fecha": (today + timedelta(days=i)).isoformat(),
            "condicion": c[0], "precipitaciones_mm": c[1],
            "temperatura_max": c[2], "temperatura_min": c[3],
            "humedad_pct": 60 + c[1] * 2, "viento_kmh": 15 + (i % 5) * 3,
            "probabilidad_lluvia_pct": min(c[1] * 3, 95),
        })
    return {
        "lat": lat, "lon": lon, "dias": dias, "pronostico": pronostico,
        "acumulado_precipitaciones": sum(p["precipitaciones_mm"] for p in pronostico),
    }


@router.get("/clima/precipitaciones-historicas")
async def get_precipitaciones(establecimiento_id: int = Query(...)):
    """Precipitaciones historicas mensuales simuladas."""
    meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    normales = [80, 85, 110, 95, 60, 40, 35, 45, 65, 100, 115, 90]
    actuales = [75, 92, 105, 88, 72, 38, 42, 50, 58, 112, 98, 0]
    return {
        "establecimiento_id": establecimiento_id,
        "anio": date.today().year,
        "meses": meses,
        "normal_mm": normales,
        "actual_mm": actuales,
        "acumulado_anual": sum(a for a in actuales if a > 0),
        "normal_anual": sum(normales),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints reales con datos de Open-Meteo
# ─────────────────────────────────────────────────────────────────────────────

import logging  # noqa: E402
from app.services.external_data_service import ExternalDataService  # noqa: E402
from app.integrations.weather_client import ESTABLECIMIENTOS_COORDS, WeatherClient  # noqa: E402
from app.services.cache_service import cache_service  # noqa: E402
from fastapi import HTTPException  # noqa: E402

_clima_logger = logging.getLogger(__name__)
_ext_service = ExternalDataService()


@router.get("/clima/resumen")
async def get_clima_resumen():
    """
    Resumen climatico de todos los establecimientos (Open-Meteo, real, sin API key).

    Historico 30 dias + pronostico 7 dias por establecimiento.
    Cache TTL: 1 hora.
    """
    try:
        return await _ext_service.get_clima_resumen()
    except Exception as exc:
        _clima_logger.exception("Error en /clima/resumen: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/clima/pronostico-real")
async def get_pronostico_real(
    establecimiento: str = Query(
        "El Progreso",
        description="Opciones: 'La Pampa Grande', 'El Progreso', 'San Martin', 'La Esperanza'",
    ),
):
    """
    Pronostico 7 dias para un establecimiento especifico (Open-Meteo real).

    Cache TTL: 1 hora.
    """
    try:
        return await _ext_service.get_clima_pronostico(establecimiento=establecimiento)
    except Exception as exc:
        _clima_logger.exception("Error en /clima/pronostico-real '%s': %s", establecimiento, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/clima/alertas")
async def get_alertas_climaticas():
    """
    Alertas climaticas activas (Open-Meteo real).

    Sequia: < 2mm/30d | Inundacion: > 50mm/dia | Helada: < 2C pronosticado.
    Cache TTL: 1 hora.
    """
    try:
        return await _ext_service.get_alertas_climaticas()
    except Exception as exc:
        _clima_logger.exception("Error en /clima/alertas: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/clima/establecimientos")
async def get_establecimientos():
    """Lista los establecimientos disponibles con coordenadas geograficas."""
    return {
        "data": [
            {
                "nombre": nombre,
                "provincia": coords.get("provincia", ""),
                "lat": coords["lat"],
                "lon": coords["lon"],
            }
            for nombre, coords in ESTABLECIMIENTOS_COORDS.items()
        ],
        "total": len(ESTABLECIMIENTOS_COORDS),
    }


@router.get("/clima/historico-real")
async def get_historico_real(
    lat: float = Query(-34.5, description="Latitud decimal"),
    lon: float = Query(-60.5, description="Longitud decimal"),
    start: str = Query(None, description="Fecha inicio YYYY-MM-DD (default: 30d atras)"),
    end: str = Query(None, description="Fecha fin YYYY-MM-DD (default: ayer)"),
):
    """
    Datos meteorologicos historicos para cualquier coordenada (Open-Meteo Archive).

    Cache TTL: 2 horas.
    """
    from datetime import datetime

    now = datetime.now()
    if end is None:
        end = (now - timedelta(days=1)).strftime("%Y-%m-%d")
    if start is None:
        start = (now - timedelta(days=30)).strftime("%Y-%m-%d")

    cache_key = f"clima_historico_{lat}_{lon}_{start}_{end}"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    try:
        data = await WeatherClient().get_historical(lat=lat, lon=lon, start=start, end=end)
        await cache_service.set(cache_key, data, ttl=7200)
        return data
    except Exception as exc:
        _clima_logger.exception("Error en /clima/historico-real: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
