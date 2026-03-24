"""
Cliente para la API pública del BCRA (Banco Central de la República Argentina).

Endpoints base: https://api.bcra.gob.ar/estadisticas/v4.0/

NOTA: El BCRA presenta problemas intermitentes con sus certificados SSL.
Se utiliza verify=False con advertencia explícita en los logs.
"""

import logging
import ssl
import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

BCRA_BASE_URL = "https://api.bcra.gob.ar/estadisticas/v4.0"

# IDs de variables clave en la API del BCRA
BCRA_VARIABLES = {
    "reservas_internacionales": 1,
    "tipo_cambio_minorista": 4,   # TC minorista ($ por USD, com. 3500)
    "tipo_cambio_mayorista": 5,   # TC mayorista ($ por USD, com. 3500)
    "tasa_politica_monetaria": 7,
    "inflacion_mensual": 27,      # IPC mensual
    "inflacion_interanual": 28,   # IPC interanual
    "inflacion_esperada": 29,
}

DEFAULT_TIMEOUT = 15.0


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_metadata(
    status: str = "ok",
    error_message: Optional[str] = None,
    frequency: str = "diaria",
) -> dict:
    return {
        "source_name": "BCRA - Banco Central de la República Argentina",
        "source_url": "https://api.bcra.gob.ar",
        "fetched_at": _now_utc(),
        "frequency": frequency,
        "status": status,
        "error_message": error_message,
    }


def _build_ssl_context() -> ssl.SSLContext:
    """
    Crea un contexto SSL con verificación deshabilitada.
    El BCRA tiene problemas frecuentes con su cadena de certificados.
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _build_client() -> httpx.AsyncClient:
    warnings.warn(
        "BCRA SSL verification is disabled due to known certificate issues with api.bcra.gob.ar",
        UserWarning,
        stacklevel=2,
    )
    return httpx.AsyncClient(
        verify=False,
        timeout=DEFAULT_TIMEOUT,
        headers={"Accept": "application/json", "User-Agent": "DemoAgro/1.0"},
    )


class BCRAClient:
    """
    Cliente asíncrono para la API pública del BCRA.

    Uso:
        client = BCRAClient()
        data = await client.get_tipo_cambio()
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = BCRA_BASE_URL

    async def _get(self, path: str, params: Optional[dict] = None) -> Any:
        """Realiza un GET autenticado contra la API del BCRA."""
        url = f"{self.base_url}{path}"
        async with _build_client() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_variables_list(self) -> dict:
        """
        Retorna la lista completa de variables monetarias disponibles.

        Endpoint: GET /monetarias
        """
        try:
            raw = await self._get("/monetarias")
            results = raw.get("results", raw) if isinstance(raw, dict) else raw
            return {
                "data": results,
                "metadata": _build_metadata(status="ok"),
            }
        except httpx.TimeoutException:
            logger.error("BCRA API timeout al obtener lista de variables")
            return {
                "data": [],
                "metadata": _build_metadata(
                    status="error", error_message="Timeout al conectar con BCRA"
                ),
            }
        except httpx.HTTPStatusError as exc:
            logger.error("BCRA HTTP error %s: %s", exc.response.status_code, exc)
            return {
                "data": [],
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"HTTP {exc.response.status_code} desde BCRA",
                ),
            }
        except Exception as exc:
            logger.exception("Error inesperado al consultar variables BCRA: %s", exc)
            return {
                "data": [],
                "metadata": _build_metadata(status="error", error_message=str(exc)),
            }

    async def get_variable_serie(
        self,
        id_variable: int,
        desde: Optional[str] = None,
        hasta: Optional[str] = None,
    ) -> dict:
        """
        Retorna la serie histórica de una variable monetaria.

        Args:
            id_variable: ID de la variable (ver BCRA_VARIABLES).
            desde: Fecha de inicio en formato YYYY-MM-DD. Default: 30 días atrás.
            hasta: Fecha de fin en formato YYYY-MM-DD. Default: hoy.

        Endpoint: GET /monetarias/{idVariable}
        """
        if hasta is None:
            hasta = datetime.now().strftime("%Y-%m-%d")
        if desde is None:
            desde = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")

        delta = max((datetime.fromisoformat(hasta) - datetime.fromisoformat(desde)).days, 1)
        params = {"limit": min(max(delta + 5, 30), 365)}
        try:
            raw = await self._get(f"/monetarias/{id_variable}", params=params)
            results = raw.get("results", []) if isinstance(raw, dict) else []
            detalle = []
            if results and isinstance(results[0], dict):
                detalle = results[0].get("detalle", []) or []
            detalle = sorted(detalle, key=lambda item: item.get("fecha", ""))
            return {
                "data": detalle,
                "id_variable": id_variable,
                "desde": desde,
                "hasta": hasta,
                "metadata": _build_metadata(status="ok"),
            }
        except httpx.TimeoutException:
            logger.error("BCRA API timeout al obtener serie variable %s", id_variable)
            return {
                "data": [],
                "id_variable": id_variable,
                "metadata": _build_metadata(
                    status="error", error_message="Timeout al conectar con BCRA"
                ),
            }
        except httpx.HTTPStatusError as exc:
            logger.error(
                "BCRA HTTP error %s al obtener variable %s: %s",
                exc.response.status_code,
                id_variable,
                exc,
            )
            return {
                "data": [],
                "id_variable": id_variable,
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"HTTP {exc.response.status_code} desde BCRA",
                ),
            }
        except Exception as exc:
            logger.exception(
                "Error inesperado al consultar serie BCRA variable %s: %s",
                id_variable,
                exc,
            )
            return {
                "data": [],
                "id_variable": id_variable,
                "metadata": _build_metadata(status="error", error_message=str(exc)),
            }

    async def get_tipo_cambio(self) -> dict:
        """
        Retorna el tipo de cambio minorista y mayorista vigente.

        Variables consultadas:
        - 4: TC minorista ($ por USD, com. 3500)
        - 5: TC mayorista ($ por USD, com. 3500)
        """
        minorista_task = self.get_variable_serie(BCRA_VARIABLES["tipo_cambio_minorista"])
        mayorista_task = self.get_variable_serie(BCRA_VARIABLES["tipo_cambio_mayorista"])

        import asyncio
        minorista_raw, mayorista_raw = await asyncio.gather(
            minorista_task, mayorista_task
        )

        def _last_value(serie_response: dict) -> Optional[dict]:
            data = serie_response.get("data", [])
            if data and isinstance(data, list):
                return data[-1]
            return None

        minorista_last = _last_value(minorista_raw)
        mayorista_last = _last_value(mayorista_raw)

        status = "ok"
        if minorista_raw["metadata"]["status"] == "error" and mayorista_raw["metadata"]["status"] == "error":
            status = "error"
        elif minorista_raw["metadata"]["status"] == "error" or mayorista_raw["metadata"]["status"] == "error":
            status = "stale"

        return {
            "data": {
                "tipo_cambio_minorista": {
                    "valor": minorista_last.get("valor") if minorista_last else None,
                    "fecha": minorista_last.get("fecha") if minorista_last else None,
                    "descripcion": "TC minorista ($ por USD, com. 3500)",
                    "id_variable": BCRA_VARIABLES["tipo_cambio_minorista"],
                    "serie": minorista_raw.get("data", []),
                },
                "tipo_cambio_mayorista": {
                    "valor": mayorista_last.get("valor") if mayorista_last else None,
                    "fecha": mayorista_last.get("fecha") if mayorista_last else None,
                    "descripcion": "TC mayorista ($ por USD, com. 3500)",
                    "id_variable": BCRA_VARIABLES["tipo_cambio_mayorista"],
                    "serie": mayorista_raw.get("data", []),
                },
            },
            "metadata": _build_metadata(status=status),
        }

    async def get_tasas(self) -> dict:
        """
        Retorna la tasa de política monetaria y variables relacionadas.

        Variable consultada:
        - 7: Tasa de política monetaria
        """
        serie = await self.get_variable_serie(BCRA_VARIABLES["tasa_politica_monetaria"])
        data = serie.get("data", [])
        last = data[-1] if data else None

        return {
            "data": {
                "tasa_politica_monetaria": {
                    "valor": last.get("valor") if last else None,
                    "fecha": last.get("fecha") if last else None,
                    "descripcion": "Tasa de política monetaria (% anual)",
                    "id_variable": BCRA_VARIABLES["tasa_politica_monetaria"],
                    "serie": data,
                }
            },
            "metadata": serie.get("metadata", _build_metadata()),
        }

    async def get_inflacion(self) -> dict:
        """
        Retorna IPC mensual, interanual e inflación esperada.

        Variables consultadas:
        - 27: Inflación mensual (IPC)
        - 28: Inflación interanual
        - 29: Inflación esperada
        """
        import asyncio

        mensual_task = self.get_variable_serie(BCRA_VARIABLES["inflacion_mensual"])
        interanual_task = self.get_variable_serie(BCRA_VARIABLES["inflacion_interanual"])
        esperada_task = self.get_variable_serie(BCRA_VARIABLES["inflacion_esperada"])

        mensual_raw, interanual_raw, esperada_raw = await asyncio.gather(
            mensual_task, interanual_task, esperada_task
        )

        def _last(r: dict) -> Optional[dict]:
            d = r.get("data", [])
            return d[-1] if d else None

        mensual_last = _last(mensual_raw)
        interanual_last = _last(interanual_raw)
        esperada_last = _last(esperada_raw)

        errors = [
            r["metadata"]["status"] == "error"
            for r in [mensual_raw, interanual_raw, esperada_raw]
        ]
        status = "error" if all(errors) else ("stale" if any(errors) else "ok")

        return {
            "data": {
                "inflacion_mensual": {
                    "valor": mensual_last.get("valor") if mensual_last else None,
                    "fecha": mensual_last.get("fecha") if mensual_last else None,
                    "descripcion": "Inflación mensual IPC (%)",
                    "id_variable": BCRA_VARIABLES["inflacion_mensual"],
                    "serie": mensual_raw.get("data", []),
                },
                "inflacion_interanual": {
                    "valor": interanual_last.get("valor") if interanual_last else None,
                    "fecha": interanual_last.get("fecha") if interanual_last else None,
                    "descripcion": "Inflación interanual IPC (%)",
                    "id_variable": BCRA_VARIABLES["inflacion_interanual"],
                    "serie": interanual_raw.get("data", []),
                },
                "inflacion_esperada": {
                    "valor": esperada_last.get("valor") if esperada_last else None,
                    "fecha": esperada_last.get("fecha") if esperada_last else None,
                    "descripcion": "Inflación esperada próximos 12 meses (%)",
                    "id_variable": BCRA_VARIABLES["inflacion_esperada"],
                    "serie": esperada_raw.get("data", []),
                },
            },
            "metadata": _build_metadata(status=status),
        }

    async def get_resumen_macro(self) -> dict:
        """
        Combina tipo de cambio, tasas e inflación en un único resumen macroeconómico.
        """
        import asyncio

        tc_task = self.get_tipo_cambio()
        tasas_task = self.get_tasas()
        inflacion_task = self.get_inflacion()
        reservas_task = self.get_variable_serie(BCRA_VARIABLES["reservas_internacionales"])

        tc, tasas, inflacion, reservas_raw = await asyncio.gather(
            tc_task, tasas_task, inflacion_task, reservas_task
        )

        reservas_data = reservas_raw.get("data", [])
        reservas_last = reservas_data[-1] if reservas_data else None

        statuses = [
            tc.get("metadata", {}).get("status", "error"),
            tasas.get("metadata", {}).get("status", "error"),
            inflacion.get("metadata", {}).get("status", "error"),
        ]
        if all(s == "error" for s in statuses):
            overall_status = "error"
        elif any(s == "error" for s in statuses):
            overall_status = "stale"
        else:
            overall_status = "ok"

        return {
            "data": {
                "tipo_cambio": tc.get("data", {}),
                "tasas": tasas.get("data", {}),
                "inflacion": inflacion.get("data", {}),
                "reservas_internacionales": {
                    "valor": reservas_last.get("valor") if reservas_last else None,
                    "fecha": reservas_last.get("fecha") if reservas_last else None,
                    "descripcion": "Reservas internacionales del BCRA (millones de USD)",
                    "id_variable": BCRA_VARIABLES["reservas_internacionales"],
                },
            },
            "metadata": _build_metadata(status=overall_status),
        }
