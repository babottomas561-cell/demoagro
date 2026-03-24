# Mercado router - precios de commodities agricolas
# Incluye endpoints simulados (compatibilidad) y endpoints reales (Yahoo Finance CBOT + USDA + BCR)
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Path, Query
from datetime import date, timedelta

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/mercado/precios")
async def get_precios_mercado():
    """Precios de mercado simulados (MATBA-ROFEX / Chicago)."""
    today = date.today()
    cultivos = [
        ("Soja", 295, 8), ("Maiz", 175, 5),
        ("Trigo", 220, 6), ("Girasol", 395, 10), ("Sorgo", 145, 4),
    ]
    historico = {}
    for nombre, base, volatilidad in cultivos:
        serie = []
        precio = float(base)
        for i in range(30, -1, -1):
            dia = today - timedelta(days=i)
            delta = (hash(f"{nombre}{dia}") % (volatilidad * 2 + 1) - volatilidad) / 10.0
            precio = max(precio + delta, base * 0.8)
            serie.append({"fecha": dia.isoformat(), "precio_usd": round(precio, 2)})
        historico[nombre] = serie

    return {
        "fecha": today.isoformat(),
        "fuente": "Simulado - MATBA ROFEX",
        "precios_actuales": [
            {
                "cultivo": nombre,
                "precio_usd_tn": historico[nombre][-1]["precio_usd"],
                "precio_ars_tn": round(historico[nombre][-1]["precio_usd"] * 865, 2),
                "variacion_dia": round(historico[nombre][-1]["precio_usd"] - historico[nombre][-2]["precio_usd"], 2),
                "variacion_semana": round(historico[nombre][-1]["precio_usd"] - historico[nombre][-8]["precio_usd"], 2),
            }
            for nombre, _, _ in cultivos
        ],
        "serie_historica_30d": historico,
    }


@router.get("/mercado/chicago")
async def get_chicago():
    """Precios de referencia Chicago simulados."""
    return {
        "fecha": date.today().isoformat(),
        "soja_usd_bushel": 11.45, "soja_usd_tn": 420.5,
        "maiz_usd_bushel": 4.35, "maiz_usd_tn": 171.3,
        "trigo_usd_bushel": 5.85, "trigo_usd_tn": 214.8,
        "spread_arg_chicago_soja": -125.5,
        "spread_arg_chicago_maiz": 3.7,
        "fuente": "Simulado - CBOT",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Endpoints reales con datos de Yahoo Finance CBOT + USDA + BCR
# ─────────────────────────────────────────────────────────────────────────────

from app.services.external_data_service import ExternalDataService  # noqa: E402
from app.services.cache_service import cache_service  # noqa: E402
from fastapi import HTTPException  # noqa: E402

_ext_service = ExternalDataService()


@router.get("/mercado/commodities")
async def get_commodities_real():
    """
    Precios reales de soja, maiz, trigo y girasol via Yahoo Finance CBOT.

    Conversion: USD/bushel a USD/tonelada metrica.
    Soja/Trigo x 36.744 (1 bushel = 27.2155 kg).
    Maiz x 39.368 (1 bushel = 25.4012 kg).
    Cache TTL: 30 minutos.
    """
    try:
        return await _ext_service.get_mercado_commodities()
    except Exception as exc:
        logger.exception("Error en /mercado/commodities: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/mercado/historico/{cultivo}")
async def get_historico_cultivo(
    cultivo: str = Path(description="Cultivo: soja, maiz o trigo"),
    period: str = Query("1mo", description="Periodo: 1mo, 3mo, 6mo, 1y"),
):
    """
    Serie historica de precios CBOT para un cultivo.

    Retorna OHLCV convertidos a USD/tonelada metrica.
    Fuente: Yahoo Finance (ZS=F, ZC=F, ZW=F).
    Cache TTL: 1 hora.
    """
    valid_cultivos = {"soja", "maiz", "trigo"}
    if cultivo.lower() not in valid_cultivos:
        raise HTTPException(
            status_code=400,
            detail=f"Cultivo '{cultivo}' no valido. Opciones: {sorted(valid_cultivos)}",
        )
    valid_periods = {"1mo", "3mo", "6mo", "1y"}
    if period not in valid_periods:
        raise HTTPException(
            status_code=400,
            detail=f"Periodo '{period}' no valido. Opciones: {sorted(valid_periods)}",
        )
    try:
        return await _ext_service.get_historico_cultivo(cultivo=cultivo.lower(), period=period)
    except Exception as exc:
        logger.exception("Error en /mercado/historico/%s: %s", cultivo, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/mercado/precios-pizarra")
async def get_precios_pizarra_real():
    """
    Precios pizarra de referencia Rosario.

    NOTA: BCR no tiene API REST publica. Se retornan precios de
    referencia actualizados manualmente. Cache TTL: 1 hora.
    """
    from app.integrations.bcr_client import BCRClient

    cache_key = "bcr_precios"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached
    try:
        data = await BCRClient().get_precios_pizarra()
        await cache_service.set(cache_key, data, ttl=3600)
        return data
    except Exception as exc:
        logger.exception("Error en /mercado/precios-pizarra: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/mercado/produccion-usda/{cultivo}")
async def get_produccion_usda(
    cultivo: str = Path(description="Cultivo: soja, maiz o trigo"),
    pais: str = Query("argentina", description="Ambito: argentina o mundial"),
    market_year: int = Query(2024, ge=2020, le=2030),
):
    """
    Datos USDA PSD de produccion, oferta y demanda.

    Sin USDA_API_KEY retorna datos de referencia 2023/24.
    Cache TTL: 24 horas.
    """
    from app.integrations.usda_client import USDAClient, COMMODITY_CODES

    valid_cultivos = {"soja", "maiz", "trigo"}
    if cultivo.lower() not in valid_cultivos:
        raise HTTPException(
            status_code=400,
            detail=f"Cultivo '{cultivo}' no valido. Opciones: {sorted(valid_cultivos)}",
        )

    cache_key = f"usda_{cultivo}_{pais}_{market_year}"
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    try:
        client = USDAClient()
        commodity_code = COMMODITY_CODES.get(cultivo.lower(), "")
        if pais == "mundial":
            data = await client.get_produccion_mundial(commodity_code)
        elif cultivo.lower() == "soja":
            data = await client.get_soja_argentina(market_year)
        elif cultivo.lower() == "maiz":
            data = await client.get_maiz_argentina(market_year)
        else:
            data = await client.get_trigo_argentina(market_year)
        await cache_service.set(cache_key, data, ttl=86400)
        return data
    except Exception as exc:
        logger.exception("Error en /mercado/produccion-usda/%s: %s", cultivo, exc)
        raise HTTPException(status_code=500, detail=str(exc))
