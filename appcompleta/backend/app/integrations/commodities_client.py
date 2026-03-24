"""
Cliente para precios de commodities agrícolas.

Fuentes:
- Yahoo Finance (endpoint JSON público, sin API key)
  * ZS=F → Soja futuros (CBOT, USD/bushel)
  * ZC=F → Maíz futuros (CBOT, USD/bushel)
  * ZW=F → Trigo futuros (CBOT, USD/bushel)
  * SB=F → Azúcar futuros
  * KO=F → Girasol (referencia: no existe ticker directo, se usa dato estático)

Conversiones bushel → tonelada:
- Soja: 1 bushel = 27.2155 kg → 1 MT = 36.744 bushels
- Maíz: 1 bushel = 25.4012 kg → 1 MT = 39.368 bushels
- Trigo: 1 bushel = 27.2155 kg → 1 MT = 36.744 bushels
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

YAHOO_FINANCE_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

# Conversión: bushels por tonelada métrica
BUSHELS_POR_TONELADA = {
    "soja": 36.744,   # 1000 / 27.2155
    "maiz": 39.368,   # 1000 / 25.4012
    "trigo": 36.744,  # 1000 / 27.2155
}

# Tickers de futuros en Yahoo Finance
TICKERS = {
    "soja": "ZS=F",   # CBOT Soybean Futures
    "maiz": "ZC=F",   # CBOT Corn Futures
    "trigo": "ZW=F",  # CBOT Wheat Futures
}

DEFAULT_TIMEOUT = 15.0

# Headers necesarios para Yahoo Finance (simula un navegador)
YAHOO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Referer": "https://finance.yahoo.com/",
}

# ──────────────────────────────────────────────────────────────────────────────
# Precios de referencia estáticos (fallback si Yahoo Finance no responde)
# Precios CBOT aproximados en USD/bushel → se convierten a USD/ton
# Actualizado: 2024-Q4
# ──────────────────────────────────────────────────────────────────────────────
PRECIOS_FALLBACK_USD_BUSHEL = {
    "soja": 9.80,   # ~360 USD/ton
    "maiz": 4.20,   # ~165 USD/ton
    "trigo": 5.50,  # ~202 USD/ton
}

# Datos estáticos de girasol (no tiene ticker Yahoo Finance activo)
GIRASOL_REFERENCIA = {
    "cultivo": "Girasol",
    "ticker": "N/A",
    "exchange": "N/A",
    "precio_usd_ton": 455.0,
    "precio_usd_bushel": None,
    "variacion_diaria_pct": 0.0,
    "variacion_semanal_pct": 1.5,
    "volumen": None,
    "fecha_actualizacion": "2024-11-01",
    "fuente": "Referencia: Bolsa de Comercio de Rosario / USDA",
    "nota": "El girasol no tiene contrato de futuros líquido en CBOT. Precio de referencia FOB Rosario.",
    "is_fallback": True,
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_metadata(
    status: str = "ok",
    error_message: Optional[str] = None,
    is_fallback: bool = False,
) -> dict:
    return {
        "source_name": "Yahoo Finance" + (" (FALLBACK)" if is_fallback else ""),
        "source_url": "https://finance.yahoo.com",
        "fetched_at": _now_utc(),
        "frequency": "tiempo real / diferida 15 min",
        "status": status,
        "error_message": error_message,
        "is_fallback": is_fallback,
    }


def _bushel_to_ton(precio_bushel: float, cultivo: str) -> float:
    """Convierte precio en USD/bushel a USD/tonelada métrica."""
    factor = BUSHELS_POR_TONELADA.get(cultivo, 36.744)
    return round(precio_bushel * factor, 2)


def _parse_yahoo_response(raw: dict, cultivo: str, ticker: str) -> dict:
    """
    Extrae y normaliza el precio spot del JSON de Yahoo Finance v8.
    """
    try:
        chart = raw["chart"]["result"][0]
        meta = chart["meta"]

        precio_bushel = meta.get("regularMarketPrice") or meta.get("previousClose", 0)
        precio_cierre_anterior = meta.get("chartPreviousClose") or meta.get("previousClose", 0)

        variacion_diaria = 0.0
        if precio_cierre_anterior and precio_cierre_anterior > 0:
            variacion_diaria = round(
                ((precio_bushel - precio_cierre_anterior) / precio_cierre_anterior) * 100, 2
            )

        precio_ton = _bushel_to_ton(precio_bushel, cultivo)
        precio_cierre_ton = _bushel_to_ton(precio_cierre_anterior, cultivo) if precio_cierre_anterior else None

        return {
            "cultivo": cultivo.capitalize(),
            "ticker": ticker,
            "exchange": meta.get("exchangeName", "CBOT"),
            "precio_usd_ton": precio_ton,
            "precio_usd_bushel": round(precio_bushel, 4),
            "precio_cierre_anterior_usd_ton": precio_cierre_ton,
            "variacion_diaria_pct": variacion_diaria,
            "variacion_diaria_usd_ton": round(precio_ton - precio_cierre_ton, 2) if precio_cierre_ton else None,
            "currency": meta.get("currency", "USD"),
            "market_state": meta.get("marketState", "unknown"),
            "fifty_two_week_high": _bushel_to_ton(
                meta.get("fiftyTwoWeekHigh", 0), cultivo
            ) if meta.get("fiftyTwoWeekHigh") else None,
            "fifty_two_week_low": _bushel_to_ton(
                meta.get("fiftyTwoWeekLow", 0), cultivo
            ) if meta.get("fiftyTwoWeekLow") else None,
            "timestamp": meta.get("regularMarketTime"),
            "is_fallback": False,
        }
    except (KeyError, IndexError, TypeError) as exc:
        logger.warning("Error parseando respuesta Yahoo Finance para %s: %s", ticker, exc)
        return _get_fallback_data(cultivo, ticker)


def _get_fallback_data(cultivo: str, ticker: str) -> dict:
    """Genera datos de fallback cuando Yahoo Finance no responde."""
    precio_bushel = PRECIOS_FALLBACK_USD_BUSHEL.get(cultivo, 0)
    precio_ton = _bushel_to_ton(precio_bushel, cultivo) if precio_bushel else 0
    return {
        "cultivo": cultivo.capitalize(),
        "ticker": ticker,
        "exchange": "CBOT",
        "precio_usd_ton": precio_ton,
        "precio_usd_bushel": precio_bushel,
        "precio_cierre_anterior_usd_ton": None,
        "variacion_diaria_pct": None,
        "variacion_diaria_usd_ton": None,
        "currency": "USD",
        "market_state": "unknown",
        "fifty_two_week_high": None,
        "fifty_two_week_low": None,
        "timestamp": None,
        "is_fallback": True,
        "nota": "Precio de referencia estático. Yahoo Finance no disponible.",
    }


class CommoditiesClient:
    """
    Cliente asíncrono para precios de commodities agrícolas.

    Usa Yahoo Finance como fuente principal (sin API key).
    Convierte precios de USD/bushel a USD/tonelada métrica.

    Uso:
        client = CommoditiesClient()
        data = await client.get_precio_soja()
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout

    async def _get_yahoo(self, ticker: str, params: Optional[dict] = None) -> Any:
        """Realiza GET al endpoint de Yahoo Finance."""
        url = f"{YAHOO_FINANCE_BASE}/{ticker}"
        default_params = {
            "interval": "1d",
            "range": "1d",
        }
        if params:
            default_params.update(params)

        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers=YAHOO_HEADERS,
            follow_redirects=True,
        ) as client:
            response = await client.get(url, params=default_params)
            response.raise_for_status()
            return response.json()

    async def _get_precio_cultivo(self, cultivo: str) -> dict:
        """Obtiene el precio spot de un cultivo."""
        ticker = TICKERS.get(cultivo)
        if not ticker:
            return {
                "data": {"error": f"Ticker no configurado para cultivo '{cultivo}'"},
                "metadata": _build_metadata(status="error", error_message=f"Ticker no configurado para '{cultivo}'"),
            }

        try:
            raw = await self._get_yahoo(ticker)
            error = raw.get("chart", {}).get("error")
            if error:
                logger.warning("Yahoo Finance error para %s: %s", ticker, error)
                data = _get_fallback_data(cultivo, ticker)
                return {
                    "data": data,
                    "metadata": _build_metadata(
                        status="stale",
                        is_fallback=True,
                        error_message=str(error),
                    ),
                }

            data = _parse_yahoo_response(raw, cultivo, ticker)
            status = "stale" if data.get("is_fallback") else "ok"
            return {
                "data": data,
                "metadata": _build_metadata(
                    status=status,
                    is_fallback=data.get("is_fallback", False),
                ),
            }
        except httpx.TimeoutException:
            logger.error("Timeout al obtener precio %s de Yahoo Finance", ticker)
            return {
                "data": _get_fallback_data(cultivo, ticker),
                "metadata": _build_metadata(
                    status="stale",
                    is_fallback=True,
                    error_message=f"Timeout Yahoo Finance para {ticker}",
                ),
            }
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error %s Yahoo Finance %s: %s", exc.response.status_code, ticker, exc)
            return {
                "data": _get_fallback_data(cultivo, ticker),
                "metadata": _build_metadata(
                    status="stale",
                    is_fallback=True,
                    error_message=f"HTTP {exc.response.status_code} Yahoo Finance",
                ),
            }
        except Exception as exc:
            logger.exception("Error inesperado al obtener precio %s: %s", ticker, exc)
            return {
                "data": _get_fallback_data(cultivo, ticker),
                "metadata": _build_metadata(
                    status="stale",
                    is_fallback=True,
                    error_message=str(exc),
                ),
            }

    async def get_precio_soja(self) -> dict:
        """Retorna el precio spot de soja (ZS=F) en USD/tonelada."""
        return await self._get_precio_cultivo("soja")

    async def get_precio_maiz(self) -> dict:
        """Retorna el precio spot de maíz (ZC=F) en USD/tonelada."""
        return await self._get_precio_cultivo("maiz")

    async def get_precio_trigo(self) -> dict:
        """Retorna el precio spot de trigo (ZW=F) en USD/tonelada."""
        return await self._get_precio_cultivo("trigo")

    async def get_precio_girasol(self) -> dict:
        """
        Retorna el precio de referencia del girasol.
        El girasol no tiene contrato de futuros líquido en CBOT.
        Se retorna precio de referencia FOB Rosario.
        """
        return {
            "data": GIRASOL_REFERENCIA,
            "metadata": _build_metadata(
                status="ok",
                is_fallback=True,
                error_message="Girasol sin ticker CBOT activo. Precio de referencia BCR.",
            ),
        }

    async def get_todos_commodities(self) -> dict:
        """
        Retorna precios actuales de todos los commodities en paralelo.
        """
        import asyncio

        soja_task = self.get_precio_soja()
        maiz_task = self.get_precio_maiz()
        trigo_task = self.get_precio_trigo()
        girasol_task = self.get_precio_girasol()

        soja, maiz, trigo, girasol = await asyncio.gather(
            soja_task, maiz_task, trigo_task, girasol_task
        )

        statuses = [
            soja.get("metadata", {}).get("status", "error"),
            maiz.get("metadata", {}).get("status", "error"),
            trigo.get("metadata", {}).get("status", "error"),
        ]
        overall = "ok" if all(s == "ok" for s in statuses) else (
            "stale" if any(s in ("ok", "stale") for s in statuses) else "error"
        )

        return {
            "data": {
                "soja": soja.get("data", {}),
                "maiz": maiz.get("data", {}),
                "trigo": trigo.get("data", {}),
                "girasol": girasol.get("data", {}),
            },
            "resumen": {
                "actualizacion": _now_utc(),
                "moneda": "USD",
                "unidad_precio": "USD/tonelada métrica",
                "fuente": "Yahoo Finance (CBOT Futures) + Referencias BCR",
                "nota_conversion": (
                    "Precios convertidos de USD/bushel: "
                    "soja y trigo × 36.744, maíz × 39.368"
                ),
            },
            "metadata": _build_metadata(status=overall),
        }

    async def get_serie_historica(
        self,
        symbol: str,
        period: str = "1mo",
    ) -> dict:
        """
        Retorna la serie histórica de precios para un ticker dado.

        Args:
            symbol: Ticker de Yahoo Finance (ej: 'ZS=F', 'ZC=F', 'ZW=F').
            period: Período ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y').
        """
        # Determinar cultivo por ticker
        ticker_to_cultivo = {v: k for k, v in TICKERS.items()}
        cultivo = ticker_to_cultivo.get(symbol.upper(), "desconocido")

        PERIOD_INTERVALS = {
            "1d": "5m",
            "5d": "15m",
            "1mo": "1d",
            "3mo": "1d",
            "6mo": "1wk",
            "1y": "1wk",
            "2y": "1wk",
        }
        interval = PERIOD_INTERVALS.get(period, "1d")

        try:
            raw = await self._get_yahoo(symbol, params={"range": period, "interval": interval})
            error = raw.get("chart", {}).get("error")
            if error:
                return {
                    "data": [],
                    "symbol": symbol,
                    "cultivo": cultivo,
                    "metadata": _build_metadata(
                        status="error", error_message=str(error), is_fallback=True
                    ),
                }

            chart = raw["chart"]["result"][0]
            timestamps = chart.get("timestamp", [])
            closes = chart.get("indicators", {}).get("quote", [{}])[0].get("close", [])
            highs = chart.get("indicators", {}).get("quote", [{}])[0].get("high", [])
            lows = chart.get("indicators", {}).get("quote", [{}])[0].get("low", [])
            volumes = chart.get("indicators", {}).get("quote", [{}])[0].get("volume", [])

            serie = []
            for i, ts in enumerate(timestamps):
                precio_bushel = closes[i] if i < len(closes) and closes[i] is not None else None
                precio_ton = _bushel_to_ton(precio_bushel, cultivo) if precio_bushel else None

                serie.append({
                    "timestamp": ts,
                    "fecha": datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"),
                    "precio_usd_bushel": round(precio_bushel, 4) if precio_bushel else None,
                    "precio_usd_ton": precio_ton,
                    "high_usd_ton": _bushel_to_ton(highs[i], cultivo) if i < len(highs) and highs[i] else None,
                    "low_usd_ton": _bushel_to_ton(lows[i], cultivo) if i < len(lows) and lows[i] else None,
                    "volumen": volumes[i] if i < len(volumes) else None,
                })

            return {
                "data": serie,
                "symbol": symbol,
                "cultivo": cultivo,
                "period": period,
                "interval": interval,
                "count": len(serie),
                "metadata": _build_metadata(status="ok"),
            }

        except httpx.TimeoutException:
            logger.error("Timeout al obtener histórico %s", symbol)
            return {
                "data": [],
                "symbol": symbol,
                "cultivo": cultivo,
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"Timeout al obtener histórico para {symbol}",
                    is_fallback=True,
                ),
            }
        except (KeyError, IndexError, httpx.HTTPStatusError) as exc:
            logger.error("Error al obtener histórico %s: %s", symbol, exc)
            return {
                "data": [],
                "symbol": symbol,
                "cultivo": cultivo,
                "metadata": _build_metadata(
                    status="error",
                    error_message=str(exc),
                    is_fallback=True,
                ),
            }
        except Exception as exc:
            logger.exception("Error inesperado al obtener histórico %s: %s", symbol, exc)
            return {
                "data": [],
                "symbol": symbol,
                "cultivo": cultivo,
                "metadata": _build_metadata(
                    status="error",
                    error_message=str(exc),
                    is_fallback=True,
                ),
            }
