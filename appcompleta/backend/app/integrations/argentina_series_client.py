"""
Cliente para la API de Series de Tiempo del gobierno argentino.

Base URL: https://apis.datos.gob.ar/series/api/series/

Documentación oficial: https://datosgobar.github.io/series-tiempo-ar-api/
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)

ARG_SERIES_BASE_URL = "https://apis.datos.gob.ar/series/api/series/"

# Series de tiempo disponibles y sus IDs oficiales
SERIES_IDS = {
    "ipc_nivel_general": "148.3_INIVELNAL_DICI_M_26",
    "ipc_variacion_mensual": "145.3_INGNACUAL_DICI_M_38",
    "tipo_cambio_bna_vendedor": "168.1_T_CAMBIOR_D_0_0_26",
    "pbi_precios_constantes": "9.1_PP2_2004_A_16",
    "ventas_supermercados": "455.1_VENTAS_PRETES_0_M_25_98",
    "tipo_cambio_referencia_bcra": "168.1_T_CAMBIOR_D_0_0_26",
}

DEFAULT_TIMEOUT = 15.0


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_metadata(
    status: str = "ok",
    error_message: Optional[str] = None,
    frequency: str = "mensual",
) -> dict:
    return {
        "source_name": "Datos Abiertos Argentina - Series de Tiempo",
        "source_url": "https://apis.datos.gob.ar/series/api/",
        "fetched_at": _now_utc(),
        "frequency": frequency,
        "status": status,
        "error_message": error_message,
    }


class ArgentinaSeriesClient:
    """
    Cliente asíncrono para la API de Series de Tiempo de datos.gob.ar.

    No requiere API key. Los datos son abiertos y públicos.

    Uso:
        client = ArgentinaSeriesClient()
        data = await client.get_ipc_mensual()
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.base_url = ARG_SERIES_BASE_URL

    async def _get(self, params: dict) -> Any:
        """Realiza un GET contra la API de series de tiempo."""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            headers={"Accept": "application/json", "User-Agent": "DemoAgro/1.0"},
        ) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()

    async def get_series(
        self,
        series_ids: list[str],
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        collapse: Optional[str] = None,
        collapse_aggregation: Optional[str] = None,
        representation_mode: Optional[str] = None,
    ) -> dict:
        """
        Consulta una o más series de tiempo por ID.

        Args:
            series_ids: Lista de IDs de series (pueden combinarse con ':' para transformaciones).
            limit: Cantidad máxima de registros (max 1000).
            start_date: Fecha de inicio en formato YYYY-MM-DD o YYYY-MM.
            end_date: Fecha de fin en formato YYYY-MM-DD o YYYY-MM.
            collapse: Frecuencia de agrupamiento ('day', 'month', 'quarter', 'year').
            collapse_aggregation: Función de agregación ('avg', 'sum', 'end_of_period', 'min', 'max').
            representation_mode: Modo de representación ('value', 'change', 'pct_change', 'pct_change_a_year_ago').
        """
        ids_str = ",".join(series_ids)
        params: dict = {"ids": ids_str, "limit": limit, "format": "json"}

        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        if collapse:
            params["collapse"] = collapse
        if collapse_aggregation:
            params["collapse_aggregation"] = collapse_aggregation
        if representation_mode:
            params["representation_mode"] = representation_mode

        try:
            raw = await self._get(params)
            data_rows = raw.get("data", [])

            # Normalizar: convertir lista de listas en lista de dicts
            normalized = []
            if data_rows:
                headers = ["fecha", *series_ids]
                for row in data_rows:
                    record = {}
                    for i, header in enumerate(headers):
                        record[header] = row[i] if i < len(row) else None
                    normalized.append(record)

            return {
                "data": normalized,
                "raw_meta": raw.get("meta", []),
                "series_ids": series_ids,
                "count": len(normalized),
                "metadata": _build_metadata(status="ok"),
            }
        except httpx.TimeoutException:
            logger.error("Timeout al consultar series de tiempo Argentina: %s", ids_str)
            return {
                "data": [],
                "series_ids": series_ids,
                "metadata": _build_metadata(
                    status="error",
                    error_message="Timeout al conectar con API de series de tiempo",
                ),
            }
        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP error %s al consultar series %s: %s",
                exc.response.status_code,
                ids_str,
                exc,
            )
            return {
                "data": [],
                "series_ids": series_ids,
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"HTTP {exc.response.status_code} desde API de series de tiempo",
                ),
            }
        except Exception as exc:
            logger.exception("Error inesperado al consultar series de tiempo: %s", exc)
            return {
                "data": [],
                "series_ids": series_ids,
                "metadata": _build_metadata(status="error", error_message=str(exc)),
            }

    async def get_ipc_mensual(
        self,
        limit: int = 24,
        start_date: Optional[str] = None,
    ) -> dict:
        """
        Retorna la serie mensual del IPC (Índice de Precios al Consumidor).

        Serie: 148.3_INIVELGENER_DICI_M_26
        Fuente: INDEC - Dirección de Estadísticas de Condiciones de Vida
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m")

        result = await self.get_series(
            series_ids=[SERIES_IDS["ipc_nivel_general"]],
            limit=limit,
            start_date=start_date,
            collapse="month",
        )
        result["descripcion"] = "IPC Nivel General mensual (base diciembre 2016=100)"
        result["unidad"] = "Índice"
        return result

    async def get_tipo_cambio_serie(
        self,
        limit: int = 60,
        start_date: Optional[str] = None,
    ) -> dict:
        """
        Retorna la serie del tipo de cambio de referencia del BCRA y BNA.

        Series:
        - 168.1_T_CAMBIOR_D_0_0_26: TC referencia BCRA (diario)
        - 101.1_I2N_2016_M_15: TC BNA vendedor (mensual)
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")

        result_bna = await self.get_series(
            series_ids=[SERIES_IDS["tipo_cambio_bna_vendedor"]],
            limit=limit,
            start_date=start_date,
            collapse="month",
            collapse_aggregation="end_of_period",
        )

        status = result_bna.get("metadata", {}).get("status", "error")

        return {
            "data": {
                "tipo_cambio_referencia_bcra": result_bna.get("data", []),
                "tipo_cambio_bna_vendedor": result_bna.get("data", []),
            },
            "metadata": {
                "source_name": "Datos Abiertos Argentina - Series de Tiempo",
                "source_url": "https://apis.datos.gob.ar/series/api/",
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "frequency": "mensual",
                "status": status,
            },
        }

    async def search_series(self, q: str, limit: int = 20) -> dict:
        """
        Busca series de tiempo por nombre o descripción.

        Args:
            q: Texto a buscar.
            limit: Cantidad máxima de resultados.
        """
        search_url = "https://apis.datos.gob.ar/series/api/search/"
        params = {"q": q, "limit": limit}

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Accept": "application/json", "User-Agent": "DemoAgro/1.0"},
            ) as client:
                response = await client.get(search_url, params=params)
                response.raise_for_status()
                raw = response.json()

            return {
                "data": raw.get("data", []),
                "count": raw.get("count", 0),
                "query": q,
                "metadata": _build_metadata(status="ok"),
            }
        except httpx.TimeoutException:
            logger.error("Timeout al buscar series con query '%s'", q)
            return {
                "data": [],
                "query": q,
                "metadata": _build_metadata(
                    status="error",
                    error_message="Timeout al buscar series de tiempo",
                ),
            }
        except httpx.HTTPStatusError as exc:
            logger.error("HTTP error %s al buscar series '%s': %s", exc.response.status_code, q, exc)
            return {
                "data": [],
                "query": q,
                "metadata": _build_metadata(
                    status="error",
                    error_message=f"HTTP {exc.response.status_code} al buscar series",
                ),
            }
        except Exception as exc:
            logger.exception("Error inesperado al buscar series de tiempo: %s", exc)
            return {
                "data": [],
                "query": q,
                "metadata": _build_metadata(status="error", error_message=str(exc)),
            }

    async def get_pbi(self, limit: int = 10) -> dict:
        """
        Retorna la serie anual del PBI a precios constantes.

        Serie: 63.1_MT2P_2016_A_21
        """
        result = await self.get_series(
            series_ids=[SERIES_IDS["pbi_precios_constantes"]],
            limit=limit,
        )
        result["descripcion"] = "PBI a precios constantes de 2004 (millones de pesos)"
        result["unidad"] = "Millones de pesos (base 2004)"
        result["frecuencia"] = "anual"
        return result

    async def get_ventas_supermercados(self, limit: int = 24) -> dict:
        """
        Retorna la serie mensual de ventas en supermercados (proxy de consumo).

        Serie: 11.3_VMATBAEP_2016_M_15
        """
        result = await self.get_series(
            series_ids=[SERIES_IDS["ventas_supermercados"]],
            limit=limit,
        )
        result["descripcion"] = "Ventas en supermercados (millones de pesos corrientes)"
        result["unidad"] = "Millones de pesos"
        return result

    async def get_ipc_variacion_mensual(
        self,
        limit: int = 24,
        start_date: Optional[str] = None,
    ) -> dict:
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=365 * 2)).strftime("%Y-%m")

        result = await self.get_series(
            series_ids=[SERIES_IDS["ipc_variacion_mensual"]],
            limit=limit,
            start_date=start_date,
            collapse="month",
        )
        result["descripcion"] = "IPC variacion mensual nacional"
        result["unidad"] = "Variacion intermensual"
        return result
