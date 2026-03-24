"""
Cliente para Open-Meteo (API meteorológica gratuita sin API key).

Endpoints:
- Pronóstico: https://api.open-meteo.com/v1/forecast
- Histórico: https://archive-api.open-meteo.com/v1/archive

Cobertura: zonas pampeanas de Argentina.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

TIMEZONE_AR = "America/Argentina/Buenos_Aires"

# Coordenadas de establecimientos ficticios en zonas pampeanas reales
ESTABLECIMIENTOS_COORDS: dict[str, dict] = {
    "La Pampa Grande": {"lat": -36.6167, "lon": -63.7667, "provincia": "La Pampa"},
    "El Progreso": {"lat": -34.5, "lon": -60.5, "provincia": "Buenos Aires"},
    "San Martín": {"lat": -33.0, "lon": -62.5, "provincia": "Córdoba"},
    "La Esperanza": {"lat": -32.0, "lon": -61.0, "provincia": "Santa Fe"},
}

# Variables diarias a solicitar
DAILY_VARS = [
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "windspeed_10m_max",
    "weathercode",
]

# Variables horarias a solicitar
HOURLY_VARS = [
    "temperature_2m",
    "precipitation",
    "relativehumidity_2m",
]

DEFAULT_TIMEOUT = 15.0

# Umbrales de alerta
UMBRAL_INUNDACION_MM = 50.0    # mm/día
UMBRAL_SEQUIA_MM_30D = 2.0     # mm acumulados en 30 días
UMBRAL_HELADA_C = 2.0          # °C temperatura mínima


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_metadata(
    status: str = "ok",
    error_message: Optional[str] = None,
) -> dict:
    return {
        "source_name": "Open-Meteo",
        "source_url": "https://open-meteo.com",
        "fetched_at": _now_utc(),
        "frequency": "horaria/diaria",
        "status": status,
        "error_message": error_message,
    }


class WeatherClient:
    """
    Cliente asíncrono para la API Open-Meteo.
    No requiere API key. Gratuita para uso no comercial.

    Uso:
        client = WeatherClient()
        forecast = await client.get_forecast(lat=-34.5, lon=-60.5)
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout

    async def _get(self, url: str, params: dict) -> Any:
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Accept": "application/json", "User-Agent": "DemoAgro/1.0"},
        ) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_forecast(
        self,
        lat: float,
        lon: float,
        days: int = 7,
    ) -> dict:
        """
        Retorna el pronóstico para los próximos N días.

        Args:
            lat: Latitud en grados decimales.
            lon: Longitud en grados decimales.
            days: Días de pronóstico (1-16).
        """
        days = max(1, min(days, 16))
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": ",".join(DAILY_VARS),
            "hourly": ",".join(HOURLY_VARS),
            "timezone": TIMEZONE_AR,
            "forecast_days": days,
        }

        try:
            raw = await self._get(FORECAST_URL, params)
            return {
                "data": {
                    "daily": raw.get("daily", {}),
                    "hourly": raw.get("hourly", {}),
                    "daily_units": raw.get("daily_units", {}),
                    "hourly_units": raw.get("hourly_units", {}),
                    "latitude": raw.get("latitude"),
                    "longitude": raw.get("longitude"),
                    "elevation": raw.get("elevation"),
                    "timezone": raw.get("timezone"),
                    "forecast_days": days,
                },
                "metadata": _build_metadata(status="ok"),
            }
        except httpx.TimeoutException:
            logger.error("Timeout al obtener pronóstico para lat=%s lon=%s", lat, lon)
            return {
                "data": {},
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"Timeout al obtener pronóstico para ({lat}, {lon})",
                ),
            }
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error %s en pronóstico: %s", exc.response.status_code, exc)
            return {
                "data": {},
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"HTTP {exc.response.status_code} desde Open-Meteo",
                ),
            }
        except Exception as exc:
            logger.exception("Error inesperado al obtener pronóstico: %s", exc)
            return {
                "data": {},
                "metadata": _build_metadata(status="error", error_message=str(exc)),
            }

    async def get_historical(
        self,
        lat: float,
        lon: float,
        start: str,
        end: str,
    ) -> dict:
        """
        Retorna datos históricos para un rango de fechas.

        Args:
            lat: Latitud en grados decimales.
            lon: Longitud en grados decimales.
            start: Fecha inicio YYYY-MM-DD.
            end: Fecha fin YYYY-MM-DD.
        """
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start,
            "end_date": end,
            "daily": ",".join(DAILY_VARS),
            "hourly": ",".join(HOURLY_VARS),
            "timezone": TIMEZONE_AR,
        }

        try:
            raw = await self._get(ARCHIVE_URL, params)
            return {
                "data": {
                    "daily": raw.get("daily", {}),
                    "hourly": raw.get("hourly", {}),
                    "daily_units": raw.get("daily_units", {}),
                    "hourly_units": raw.get("hourly_units", {}),
                    "latitude": raw.get("latitude"),
                    "longitude": raw.get("longitude"),
                    "elevation": raw.get("elevation"),
                    "timezone": raw.get("timezone"),
                    "start_date": start,
                    "end_date": end,
                },
                "metadata": _build_metadata(status="ok"),
            }
        except httpx.TimeoutException:
            logger.error("Timeout al obtener histórico para lat=%s lon=%s", lat, lon)
            return {
                "data": {},
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"Timeout al obtener histórico para ({lat}, {lon})",
                ),
            }
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error %s en histórico: %s", exc.response.status_code, exc)
            return {
                "data": {},
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"HTTP {exc.response.status_code} desde Open-Meteo archive",
                ),
            }
        except Exception as exc:
            logger.exception("Error inesperado al obtener histórico: %s", exc)
            return {
                "data": {},
                "metadata": _build_metadata(status="error", error_message=str(exc)),
            }

    async def get_resumen_establecimiento(
        self,
        establecimiento_nombre: str,
    ) -> dict:
        """
        Retorna un resumen climático completo para un establecimiento.
        Incluye pronóstico 7 días e histórico 30 días.

        Args:
            establecimiento_nombre: Nombre del establecimiento (debe existir en ESTABLECIMIENTOS_COORDS).
        """
        coords = ESTABLECIMIENTOS_COORDS.get(establecimiento_nombre)
        if not coords:
            return {
                "establecimiento": establecimiento_nombre,
                "error": f"Establecimiento '{establecimiento_nombre}' no encontrado. "
                         f"Disponibles: {list(ESTABLECIMIENTOS_COORDS.keys())}",
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"Establecimiento '{establecimiento_nombre}' no encontrado",
                ),
            }

        lat, lon = coords["lat"], coords["lon"]
        provincia = coords.get("provincia", "")

        now = datetime.now()
        hist_end = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        hist_start = (now - timedelta(days=30)).strftime("%Y-%m-%d")

        import asyncio
        forecast_task = self.get_forecast(lat, lon, days=7)
        historical_task = self.get_historical(lat, lon, start=hist_start, end=hist_end)
        forecast, historical = await asyncio.gather(forecast_task, historical_task)

        # Calcular estadísticas del histórico
        hist_daily = historical.get("data", {}).get("daily", {})
        precip_hist = hist_daily.get("precipitation_sum", [])
        temp_max_hist = hist_daily.get("temperature_2m_max", [])
        temp_min_hist = hist_daily.get("temperature_2m_min", [])

        precip_validos = [p for p in precip_hist if p is not None]
        temp_max_validos = [t for t in temp_max_hist if t is not None]
        temp_min_validos = [t for t in temp_min_hist if t is not None]

        historico_stats = {
            "precipitacion_total_30d_mm": round(sum(precip_validos), 1) if precip_validos else None,
            "precipitacion_promedio_diaria_mm": round(
                sum(precip_validos) / len(precip_validos), 1
            ) if precip_validos else None,
            "temperatura_max_promedio_c": round(
                sum(temp_max_validos) / len(temp_max_validos), 1
            ) if temp_max_validos else None,
            "temperatura_min_promedio_c": round(
                sum(temp_min_validos) / len(temp_min_validos), 1
            ) if temp_min_validos else None,
            "temperatura_min_absoluta_c": round(min(temp_min_validos), 1) if temp_min_validos else None,
            "dias_con_helada": sum(1 for t in temp_min_validos if t <= UMBRAL_HELADA_C),
            "dias_con_lluvia": sum(1 for p in precip_validos if p > 0),
        }

        # Próximo pronóstico resumido
        fore_daily = forecast.get("data", {}).get("daily", {})
        precip_fore = fore_daily.get("precipitation_sum", [])
        temp_max_fore = fore_daily.get("temperature_2m_max", [])
        temp_min_fore = fore_daily.get("temperature_2m_min", [])
        fechas_fore = fore_daily.get("time", [])

        pronostico_resumen = []
        for i in range(min(len(fechas_fore), 7)):
            pronostico_resumen.append({
                "fecha": fechas_fore[i] if i < len(fechas_fore) else None,
                "temp_max_c": temp_max_fore[i] if i < len(temp_max_fore) else None,
                "temp_min_c": temp_min_fore[i] if i < len(temp_min_fore) else None,
                "precipitacion_mm": precip_fore[i] if i < len(precip_fore) else None,
            })

        return {
            "establecimiento": establecimiento_nombre,
            "provincia": provincia,
            "coordenadas": {"lat": lat, "lon": lon},
            "historico_30d": {
                "periodo": f"{hist_start} al {hist_end}",
                "estadisticas": historico_stats,
                "serie_diaria": {
                    "fechas": hist_daily.get("time", []),
                    "precipitacion_mm": precip_hist,
                    "temp_max_c": temp_max_hist,
                    "temp_min_c": temp_min_hist,
                },
            },
            "pronostico_7d": {
                "resumen": pronostico_resumen,
                "detalle": forecast.get("data", {}),
            },
            "metadata": _build_metadata(
                status=(
                    "ok"
                    if forecast.get("metadata", {}).get("status") == "ok"
                    else "stale"
                )
            ),
        }

    async def get_resumen_todos_establecimientos(self) -> list[dict]:
        """
        Retorna un resumen climático para todos los establecimientos configurados.
        Las llamadas se ejecutan en paralelo.
        """
        import asyncio

        tasks = [
            self.get_resumen_establecimiento(nombre)
            for nombre in ESTABLECIMIENTOS_COORDS
        ]
        resultados = await asyncio.gather(*tasks, return_exceptions=True)

        output = []
        for nombre, resultado in zip(ESTABLECIMIENTOS_COORDS.keys(), resultados):
            if isinstance(resultado, Exception):
                logger.error("Error al obtener clima para '%s': %s", nombre, resultado)
                output.append({
                    "establecimiento": nombre,
                    "error": str(resultado),
                    "metadata": _build_metadata(
                        status="error", error_message=str(resultado)
                    ),
                })
            else:
                output.append(resultado)

        return output

    async def get_alertas_climaticas(self) -> list[dict]:
        """
        Genera alertas climáticas basadas en datos de todos los establecimientos.

        Criterios de alerta:
        - Precipitación > 50 mm/día: ALERTA INUNDACIÓN
        - Precipitación acumulada 30d < 2 mm: ALERTA SEQUÍA
        - Temperatura mínima < 2°C (próximos 7d): ALERTA HELADA
        """
        establecimientos = await self.get_resumen_todos_establecimientos()
        alertas = []

        for estab in establecimientos:
            nombre = estab.get("establecimiento", "Desconocido")
            if "error" in estab and not estab.get("historico_30d"):
                continue

            # --- ALERTA SEQUÍA ---
            hist_stats = estab.get("historico_30d", {}).get("estadisticas", {})
            precip_30d = hist_stats.get("precipitacion_total_30d_mm")
            if precip_30d is not None and precip_30d < UMBRAL_SEQUIA_MM_30D:
                alertas.append({
                    "tipo": "SEQUIA",
                    "severidad": "alta" if precip_30d == 0 else "media",
                    "establecimiento": nombre,
                    "titulo": "Alerta de Sequía",
                    "descripcion": (
                        f"Precipitación acumulada en 30 días: {precip_30d} mm "
                        f"(umbral: {UMBRAL_SEQUIA_MM_30D} mm). Riesgo hídrico elevado."
                    ),
                    "valor_detectado": precip_30d,
                    "umbral": UMBRAL_SEQUIA_MM_30D,
                    "unidad": "mm/30 días",
                    "fecha_deteccion": _now_utc(),
                })

            # --- ALERTA INUNDACIÓN (histórico 30d) ---
            serie_precip = estab.get("historico_30d", {}).get("serie_diaria", {}).get("precipitacion_mm", [])
            serie_fechas = estab.get("historico_30d", {}).get("serie_diaria", {}).get("fechas", [])
            for i, p in enumerate(serie_precip):
                if p is not None and p > UMBRAL_INUNDACION_MM:
                    fecha_evento = serie_fechas[i] if i < len(serie_fechas) else "desconocida"
                    alertas.append({
                        "tipo": "INUNDACION",
                        "severidad": "alta" if p > 100 else "media",
                        "establecimiento": nombre,
                        "titulo": "Alerta de Inundación",
                        "descripcion": (
                            f"Precipitación de {p} mm el {fecha_evento} "
                            f"(umbral: {UMBRAL_INUNDACION_MM} mm/día)."
                        ),
                        "valor_detectado": p,
                        "umbral": UMBRAL_INUNDACION_MM,
                        "unidad": "mm/día",
                        "fecha_evento": fecha_evento,
                        "fecha_deteccion": _now_utc(),
                    })

            # --- ALERTA HELADA (pronóstico 7d) ---
            pronostico = estab.get("pronostico_7d", {}).get("resumen", [])
            for dia in pronostico:
                temp_min = dia.get("temp_min_c")
                if temp_min is not None and temp_min < UMBRAL_HELADA_C:
                    alertas.append({
                        "tipo": "HELADA",
                        "severidad": "alta" if temp_min < 0 else "media",
                        "establecimiento": nombre,
                        "titulo": "Alerta de Helada",
                        "descripcion": (
                            f"Temperatura mínima pronosticada de {temp_min}°C "
                            f"el {dia.get('fecha', 'desconocida')} "
                            f"(umbral: {UMBRAL_HELADA_C}°C)."
                        ),
                        "valor_detectado": temp_min,
                        "umbral": UMBRAL_HELADA_C,
                        "unidad": "°C",
                        "fecha_pronostico": dia.get("fecha"),
                        "fecha_deteccion": _now_utc(),
                    })

        logger.info("Se generaron %d alertas climáticas", len(alertas))
        return alertas
