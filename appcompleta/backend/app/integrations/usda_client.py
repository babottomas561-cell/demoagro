"""
Cliente para USDA PSD (Production, Supply and Distribution) API.

API real: https://apps.fas.usda.gov/psdonline/app/api/

NOTA: Si USDA_API_KEY no está configurada en las variables de entorno,
esta implementación retorna datos de referencia estáticos actualizados (2024)
claramente documentados como fallback.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

USDA_API_BASE = "https://apps.fas.usda.gov/psdonline/app/api"

# Commodity codes del USDA PSD
COMMODITY_CODES = {
    "soja": "2222000",
    "maiz": "0440100",
    "trigo": "0410100",
    "soja_harina": "2221000",
    "girasol": "4232000",
}

# Country codes
COUNTRY_CODES = {
    "argentina": "AR",
    "brasil": "BR",
    "usa": "US",
    "mundial": "00",  # Aggregate world
}

DEFAULT_TIMEOUT = 15.0


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_metadata(
    status: str = "ok",
    error_message: Optional[str] = None,
    is_fallback: bool = False,
) -> dict:
    return {
        "source_name": "USDA FAS - Production, Supply and Distribution" + (" (FALLBACK)" if is_fallback else ""),
        "source_url": "https://apps.fas.usda.gov/psdonline/",
        "fetched_at": _now_utc(),
        "frequency": "anual",
        "status": status,
        "error_message": error_message,
        "is_fallback": is_fallback,
    }


# ──────────────────────────────────────────────────────────────────────────────
# Datos de referencia estáticos (actualización manual, campaña 2023/2024)
# Fuente: USDA WASDE Reports 2024 / informes sectoriales MAGYP Argentina
# ──────────────────────────────────────────────────────────────────────────────
STATIC_FALLBACK_DATA: dict[str, dict] = {
    "soja_argentina": {
        "commodity": "Soja (Soybeans)",
        "commodity_code": COMMODITY_CODES["soja"],
        "country": "Argentina",
        "country_code": "AR",
        "market_year": 2024,
        "attributes": [
            {"attribute": "Area Harvested", "value": 17200, "unit": "1000 HA"},
            {"attribute": "Beginning Stocks", "value": 2700, "unit": "1000 MT"},
            {"attribute": "Production", "value": 50500, "unit": "1000 MT"},
            {"attribute": "MY Imports", "value": 100, "unit": "1000 MT"},
            {"attribute": "Total Supply", "value": 53300, "unit": "1000 MT"},
            {"attribute": "Crush", "value": 38000, "unit": "1000 MT"},
            {"attribute": "Exports", "value": 7500, "unit": "1000 MT"},
            {"attribute": "Total Distribution", "value": 52200, "unit": "1000 MT"},
            {"attribute": "Ending Stocks", "value": 1100, "unit": "1000 MT"},
        ],
        "nota": "Datos estimados campaña 2023/24 - Fuente: USDA WASDE",
    },
    "maiz_argentina": {
        "commodity": "Maíz (Corn)",
        "commodity_code": COMMODITY_CODES["maiz"],
        "country": "Argentina",
        "country_code": "AR",
        "market_year": 2024,
        "attributes": [
            {"attribute": "Area Harvested", "value": 7800, "unit": "1000 HA"},
            {"attribute": "Beginning Stocks", "value": 1500, "unit": "1000 MT"},
            {"attribute": "Production", "value": 50000, "unit": "1000 MT"},
            {"attribute": "MY Imports", "value": 0, "unit": "1000 MT"},
            {"attribute": "Total Supply", "value": 51500, "unit": "1000 MT"},
            {"attribute": "Domestic Consumption", "value": 11500, "unit": "1000 MT"},
            {"attribute": "Exports", "value": 38000, "unit": "1000 MT"},
            {"attribute": "Total Distribution", "value": 50000, "unit": "1000 MT"},
            {"attribute": "Ending Stocks", "value": 1500, "unit": "1000 MT"},
        ],
        "nota": "Datos estimados campaña 2023/24 - Fuente: USDA WASDE",
    },
    "trigo_argentina": {
        "commodity": "Trigo (Wheat)",
        "commodity_code": COMMODITY_CODES["trigo"],
        "country": "Argentina",
        "country_code": "AR",
        "market_year": 2024,
        "attributes": [
            {"attribute": "Area Harvested", "value": 6200, "unit": "1000 HA"},
            {"attribute": "Beginning Stocks", "value": 1800, "unit": "1000 MT"},
            {"attribute": "Production", "value": 15500, "unit": "1000 MT"},
            {"attribute": "MY Imports", "value": 0, "unit": "1000 MT"},
            {"attribute": "Total Supply", "value": 17300, "unit": "1000 MT"},
            {"attribute": "Domestic Consumption", "value": 6200, "unit": "1000 MT"},
            {"attribute": "Exports", "value": 9000, "unit": "1000 MT"},
            {"attribute": "Total Distribution", "value": 16200, "unit": "1000 MT"},
            {"attribute": "Ending Stocks", "value": 1100, "unit": "1000 MT"},
        ],
        "nota": "Datos estimados campaña 2023/24 - Fuente: USDA WASDE",
    },
}

STATIC_WORLD_PRODUCTION: dict[str, dict] = {
    COMMODITY_CODES["soja"]: {
        "commodity": "Soja (Soybeans)",
        "market_year": 2024,
        "top_producers": [
            {"country": "Brasil", "country_code": "BR", "production_mt": 153000},
            {"country": "USA", "country_code": "US", "production_mt": 113000},
            {"country": "Argentina", "country_code": "AR", "production_mt": 50500},
            {"country": "China", "country_code": "CH", "production_mt": 20300},
            {"country": "Paraguay", "country_code": "PY", "production_mt": 10500},
        ],
        "world_total_mt": 390000,
        "nota": "Producción mundial estimada campaña 2023/24 - Fuente: USDA WASDE",
    },
    COMMODITY_CODES["maiz"]: {
        "commodity": "Maíz (Corn)",
        "market_year": 2024,
        "top_producers": [
            {"country": "USA", "country_code": "US", "production_mt": 384000},
            {"country": "China", "country_code": "CH", "production_mt": 288000},
            {"country": "Brasil", "country_code": "BR", "production_mt": 127000},
            {"country": "Argentina", "country_code": "AR", "production_mt": 50000},
            {"country": "Ucrania", "country_code": "UP", "production_mt": 23500},
        ],
        "world_total_mt": 1226000,
        "nota": "Producción mundial estimada campaña 2023/24 - Fuente: USDA WASDE",
    },
    COMMODITY_CODES["trigo"]: {
        "commodity": "Trigo (Wheat)",
        "market_year": 2024,
        "top_producers": [
            {"country": "China", "country_code": "CH", "production_mt": 137000},
            {"country": "India", "country_code": "IN", "production_mt": 113000},
            {"country": "Rusia", "country_code": "RS", "production_mt": 85000},
            {"country": "USA", "country_code": "US", "production_mt": 47800},
            {"country": "Australia", "country_code": "AS", "production_mt": 25000},
            {"country": "Argentina", "country_code": "AR", "production_mt": 15500},
        ],
        "world_total_mt": 785000,
        "nota": "Producción mundial estimada campaña 2023/24 - Fuente: USDA WASDE",
    },
}


class USDAClient:
    """
    Cliente asíncrono para la API USDA FAS PSD.

    Si USDA_API_KEY no está configurada en el entorno, usa datos de referencia
    estáticos actualizados (campaña 2023/24).

    Uso:
        client = USDAClient()
        if await client.is_available():
            data = await client.get_soja_argentina()
        else:
            data = await client.get_soja_argentina()  # usa fallback automáticamente
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.api_key = os.environ.get("USDA_API_KEY", "").strip()
        self._use_fallback = not bool(self.api_key)

        if self._use_fallback:
            logger.warning(
                "USDA_API_KEY no configurada. Se usarán datos de referencia estáticos (2024). "
                "Para datos reales, registrarse en: https://apps.fas.usda.gov/psdonline/"
            )

    async def is_available(self) -> bool:
        """Retorna True si la API key está configurada y el servicio es accesible."""
        if self._use_fallback:
            return False
        try:
            url = f"{USDA_API_BASE}/worldComodityData"
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(
                    url,
                    params={"commodityCode": COMMODITY_CODES["soja"], "countryCode": "US"},
                    headers={"API_KEY": self.api_key},
                )
                return resp.status_code < 400
        except Exception:
            return False

    async def _get(self, endpoint: str, params: dict) -> Any:
        url = f"{USDA_API_BASE}/{endpoint}"
        headers = {}
        if self.api_key:
            headers["API_KEY"] = self.api_key

        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Accept": "application/json", "User-Agent": "DemoAgro/1.0", **headers},
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_commodity_data(
        self,
        commodity_code: str,
        country_code: str = "AR",
        market_year: int = 2024,
    ) -> dict:
        """
        Retorna datos de producción, oferta y distribución para un commodity/país/año.

        Si no hay API key, usa el fallback estático.
        """
        if self._use_fallback:
            return self._get_static_commodity(commodity_code, country_code, market_year)

        params = {
            "commodityCode": commodity_code,
            "countryCode": country_code,
            "marketYear": market_year,
        }
        try:
            raw = await self._get("worldComodityData", params)
            return {
                "data": raw if isinstance(raw, list) else [raw],
                "commodity_code": commodity_code,
                "country_code": country_code,
                "market_year": market_year,
                "metadata": _build_metadata(status="ok"),
            }
        except httpx.TimeoutException:
            logger.error("Timeout USDA API para commodity %s", commodity_code)
            return self._get_static_commodity(commodity_code, country_code, market_year)
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error %s en USDA API: %s", exc.response.status_code, exc)
            return self._get_static_commodity(commodity_code, country_code, market_year)
        except Exception as exc:
            logger.exception("Error inesperado en USDA API: %s", exc)
            return self._get_static_commodity(commodity_code, country_code, market_year)

    def _get_static_commodity(
        self,
        commodity_code: str,
        country_code: str,
        market_year: int,
    ) -> dict:
        """Retorna datos estáticos de referencia cuando la API no está disponible."""
        # Buscar en datos estáticos por código de commodity
        static_key_map = {
            (COMMODITY_CODES["soja"], "AR"): "soja_argentina",
            (COMMODITY_CODES["maiz"], "AR"): "maiz_argentina",
            (COMMODITY_CODES["trigo"], "AR"): "trigo_argentina",
        }
        key = static_key_map.get((commodity_code, country_code))
        if key and key in STATIC_FALLBACK_DATA:
            data = STATIC_FALLBACK_DATA[key].copy()
        else:
            data = {
                "commodity_code": commodity_code,
                "country_code": country_code,
                "market_year": market_year,
                "nota": "Sin datos estáticos de referencia para esta combinación",
                "attributes": [],
            }
        return {
            "data": data,
            "commodity_code": commodity_code,
            "country_code": country_code,
            "market_year": market_year,
            "metadata": _build_metadata(
                status="ok",
                is_fallback=True,
                error_message="USDA_API_KEY no configurada. Datos de referencia 2023/24.",
            ),
        }

    async def get_soja_argentina(self, market_year: int = 2024) -> dict:
        """Retorna datos de soja para Argentina."""
        result = await self.get_commodity_data(COMMODITY_CODES["soja"], "AR", market_year)
        result["cultivo"] = "Soja"
        return result

    async def get_maiz_argentina(self, market_year: int = 2024) -> dict:
        """Retorna datos de maíz para Argentina."""
        result = await self.get_commodity_data(COMMODITY_CODES["maiz"], "AR", market_year)
        result["cultivo"] = "Maíz"
        return result

    async def get_trigo_argentina(self, market_year: int = 2024) -> dict:
        """Retorna datos de trigo para Argentina."""
        result = await self.get_commodity_data(COMMODITY_CODES["trigo"], "AR", market_year)
        result["cultivo"] = "Trigo"
        return result

    async def get_produccion_mundial(self, commodity_code: str) -> dict:
        """
        Retorna datos de producción mundial para un commodity.
        Usa datos estáticos si no hay API key.
        """
        if self._use_fallback or commodity_code not in STATIC_WORLD_PRODUCTION:
            static = STATIC_WORLD_PRODUCTION.get(commodity_code, {})
            return {
                "data": static,
                "commodity_code": commodity_code,
                "metadata": _build_metadata(
                    status="ok" if static else "unavailable",
                    is_fallback=True,
                    error_message="USDA_API_KEY no configurada. Datos de referencia 2023/24." if static else
                                  f"Sin datos estáticos para commodity {commodity_code}",
                ),
            }

        # Con API key, consultar todos los países para armar ranking
        params = {
            "commodityCode": commodity_code,
            "countryCode": COUNTRY_CODES["mundial"],
        }
        try:
            raw = await self._get("worldComodityData", params)
            return {
                "data": raw,
                "commodity_code": commodity_code,
                "metadata": _build_metadata(status="ok"),
            }
        except Exception as exc:
            logger.warning("Fallback a datos estáticos para producción mundial: %s", exc)
            static = STATIC_WORLD_PRODUCTION.get(commodity_code, {})
            return {
                "data": static,
                "commodity_code": commodity_code,
                "metadata": _build_metadata(
                    status="stale",
                    is_fallback=True,
                    error_message=f"Error API USDA, usando datos de referencia: {exc}",
                ),
            }
