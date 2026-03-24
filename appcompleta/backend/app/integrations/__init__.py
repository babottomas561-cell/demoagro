"""
Integrations package for external API clients.

Available clients:
- BCRAClient: Banco Central de la República Argentina
- ArgentinaSeriesClient: API de Series de Tiempo del gobierno argentino
- WeatherClient: Open-Meteo (sin API key)
- USDAClient: USDA Production, Supply and Distribution
- BCRClient: Bolsa de Comercio de Rosario (modo stub)
- CommoditiesClient: Precios de commodities vía Yahoo Finance
"""

from app.integrations.bcra_client import BCRAClient
from app.integrations.argentina_series_client import ArgentinaSeriesClient
from app.integrations.weather_client import WeatherClient
from app.integrations.usda_client import USDAClient
from app.integrations.bcr_client import BCRClient
from app.integrations.commodities_client import CommoditiesClient

__all__ = [
    "BCRAClient",
    "ArgentinaSeriesClient",
    "WeatherClient",
    "USDAClient",
    "BCRClient",
    "CommoditiesClient",
]
