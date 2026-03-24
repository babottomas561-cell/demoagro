"""
Cliente para la Bolsa de Comercio de Rosario (BCR).

NOTA IMPORTANTE:
La BCR no tiene una API REST pública estable con datos de precios en tiempo real.
Esta implementación usa fuentes alternativas ordenadas por prioridad:

1. API de INDEC (datos de comercio exterior de granos) - pública y gratuita
2. Datos del Ministerio de Agricultura (MAGYP) si disponibles
3. Precios de referencia actualizados manualmente como fallback

Para acceso a datos en tiempo real de precios pizarra:
- Suscripción comercial a BCR: https://www.bcr.com.ar/es/mercados/precios-pizarra
- Acceso institucional vía convenio
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# APIs alternativas reales
INDEC_BASE_URL = "https://apis.datos.gob.ar/series/api/series/"
MAGYP_BASE_URL = "https://datosestimaciones.magyp.gob.ar/reportes.php"

DEFAULT_TIMEOUT = 15.0

# ──────────────────────────────────────────────────────────────────────────────
# Precios de referencia (actualización manual periódica)
# Fuente base: BCR Precios Pizarra Rosario, Cámara Arbitral Cereales
# Unidad: USD/tonelada, mercado disponible Rosario
# Actualizado: 2024-Q4 (valores orientativos para demo)
# ──────────────────────────────────────────────────────────────────────────────
PRECIOS_REFERENCIA: dict[str, dict] = {
    "soja": {
        "cultivo": "Soja",
        "precio_usd_ton": 285.0,
        "precio_ars_ton": None,  # Se calcula en runtime con TC del BCRA
        "posicion": "Disponible",
        "mercado": "Rosario",
        "calidad": "Soja Campaña (base 13% humedad, 1% impurezas)",
        "fecha_referencia": "2024-11-01",
        "fuente": "BCR Precios Pizarra (referencia manual)",
        "variacion_semanal_pct": -0.5,
        "variacion_mensual_pct": 2.1,
    },
    "maiz": {
        "cultivo": "Maíz",
        "precio_usd_ton": 158.0,
        "precio_ars_ton": None,
        "posicion": "Disponible",
        "mercado": "Rosario",
        "calidad": "Maíz Grado 2 (base 14.5% humedad, 3% impurezas)",
        "fecha_referencia": "2024-11-01",
        "fuente": "BCR Precios Pizarra (referencia manual)",
        "variacion_semanal_pct": 1.2,
        "variacion_mensual_pct": -0.8,
    },
    "trigo": {
        "cultivo": "Trigo",
        "precio_usd_ton": 195.0,
        "precio_ars_ton": None,
        "posicion": "Disponible",
        "mercado": "Rosario",
        "calidad": "Trigo Pan Grado 1 (11% proteína mínima, 14% humedad)",
        "fecha_referencia": "2024-11-01",
        "fuente": "BCR Precios Pizarra (referencia manual)",
        "variacion_semanal_pct": -1.0,
        "variacion_mensual_pct": 3.5,
    },
    "girasol": {
        "cultivo": "Girasol",
        "precio_usd_ton": 310.0,
        "precio_ars_ton": None,
        "posicion": "Disponible",
        "mercado": "Rosario",
        "calidad": "Girasol Campaña (base 10.5% humedad, 2% impurezas, 45% contenido graso mínimo)",
        "fecha_referencia": "2024-11-01",
        "fuente": "BCR Precios Pizarra (referencia manual)",
        "variacion_semanal_pct": 0.3,
        "variacion_mensual_pct": 1.8,
    },
    "sorgo": {
        "cultivo": "Sorgo",
        "precio_usd_ton": 142.0,
        "precio_ars_ton": None,
        "posicion": "Disponible",
        "mercado": "Rosario",
        "calidad": "Sorgo Grado 2",
        "fecha_referencia": "2024-11-01",
        "fuente": "BCR Precios Pizarra (referencia manual)",
        "variacion_semanal_pct": 0.7,
        "variacion_mensual_pct": -1.2,
    },
}

# Series de tiempo de INDEC via datos.gob.ar como alternativa
INDEC_SERIES = {
    "exportaciones_granos": "22.8_GOCXBTD_2017_M_39",  # Exportaciones de cereales y oleaginosas
}


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_metadata(
    status: str = "ok",
    error_message: Optional[str] = None,
    is_fallback: bool = False,
    source_name: str = "BCR - Bolsa de Comercio de Rosario (Fallback)",
) -> dict:
    return {
        "source_name": source_name,
        "source_url": "https://www.bcr.com.ar/es/mercados/precios-pizarra",
        "fetched_at": _now_utc(),
        "frequency": "diaria (mercado disponible)",
        "status": status,
        "error_message": error_message,
        "is_fallback": is_fallback,
        "nota": (
            "La BCR no expone API REST pública. Estos precios son de referencia "
            "actualizados manualmente. Para precios en tiempo real, se requiere "
            "suscripción comercial a BCR o acceso institucional."
            if is_fallback else None
        ),
    }


class BCRClient:
    """
    Cliente para datos de la Bolsa de Comercio de Rosario.

    LIMITACIONES:
    La BCR no tiene API REST pública con datos de precios en tiempo real.
    Esta implementación usa fuentes alternativas:
    1. API de INDEC (datos.gob.ar) para series de comercio exterior
    2. Precios de referencia actualizados manualmente como último recurso

    Para datos reales en tiempo real:
    - Suscripción BCR: https://www.bcr.com.ar
    - MATBA-ROFEX (mercado de futuros): https://www.rofex.com.ar
    """

    def __init__(self, timeout: float = DEFAULT_TIMEOUT):
        self.timeout = timeout

    async def is_available(self) -> bool:
        """
        La BCR no tiene API REST pública.
        Siempre retorna False para indicar que se usa modo degradado.
        """
        return False

    async def _try_indec_series(self, serie_id: str, limit: int = 12) -> Optional[dict]:
        """Intenta obtener datos de series de tiempo del INDEC vía datos.gob.ar."""
        params = {
            "ids": serie_id,
            "limit": limit,
            "format": "json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                headers={"Accept": "application/json", "User-Agent": "DemoAgro/1.0"},
            ) as client:
                resp = await client.get(INDEC_BASE_URL, params=params)
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            logger.warning("No se pudo obtener serie INDEC %s: %s", serie_id, exc)
            return None

    async def get_precios_pizarra(self) -> dict:
        """
        Retorna precios pizarra de todos los cultivos disponibles.
        Usa datos de referencia actualizados manualmente.

        Para datos reales, se requiere suscripción a BCR.
        """
        logger.info(
            "BCR: retornando precios de referencia (sin API pública disponible). "
            "Fuente: datos actualizados manualmente."
        )
        return {
            "data": {
                "cultivos": PRECIOS_REFERENCIA,
                "mercado": "Rosario - Mercado Disponible",
                "advertencia": (
                    "Precios de referencia aproximados. "
                    "Para precios oficiales en tiempo real, consultar www.bcr.com.ar"
                ),
            },
            "metadata": _build_metadata(status="ok", is_fallback=True),
        }

    async def get_disponible_soja(self) -> dict:
        """
        Retorna el precio disponible de soja en Rosario.
        Intenta INDEC como fuente alternativa, fallback a referencia manual.
        """
        # Intentar obtener datos de series de INDEC
        indec_data = await self._try_indec_series(
            INDEC_SERIES.get("exportaciones_granos", ""), limit=6
        )

        precio_base = PRECIOS_REFERENCIA["soja"].copy()

        extra_info = {}
        if indec_data and indec_data.get("data"):
            # Usar la última observación como referencia de actividad exportadora
            ultima = indec_data["data"][-1] if indec_data["data"] else None
            if ultima:
                extra_info["exportaciones_referencia"] = {
                    "valor": ultima[1] if len(ultima) > 1 else None,
                    "fecha": ultima[0] if ultima else None,
                    "descripcion": "Exportaciones FOB de cereales y oleaginosas (millones USD)",
                    "fuente": "INDEC via datos.gob.ar",
                }

        return {
            "data": {
                **precio_base,
                **extra_info,
            },
            "metadata": _build_metadata(
                status="ok",
                is_fallback=True,
                source_name="BCR Precios Pizarra Rosario (referencia manual) + INDEC",
            ),
        }

    async def get_disponible_maiz(self) -> dict:
        """
        Retorna el precio disponible de maíz en Rosario.
        """
        precio_base = PRECIOS_REFERENCIA["maiz"].copy()
        return {
            "data": precio_base,
            "metadata": _build_metadata(status="ok", is_fallback=True),
        }

    async def get_disponible_trigo(self) -> dict:
        """
        Retorna el precio disponible de trigo en Rosario.
        """
        precio_base = PRECIOS_REFERENCIA["trigo"].copy()
        return {
            "data": precio_base,
            "metadata": _build_metadata(status="ok", is_fallback=True),
        }

    async def get_exportaciones_cereales_indec(self, limit: int = 24) -> dict:
        """
        Retorna la serie de exportaciones de cereales y oleaginosas del INDEC.
        Esta sí es una fuente pública real disponible vía datos.gob.ar.
        """
        serie_id = INDEC_SERIES["exportaciones_granos"]
        indec_raw = await self._try_indec_series(serie_id, limit=limit)

        if not indec_raw or not indec_raw.get("data"):
            return {
                "data": [],
                "metadata": _build_metadata(
                    status="error",
                    error_message="No se pudo obtener serie de exportaciones del INDEC",
                    source_name="INDEC - Exportaciones de Cereales y Oleaginosas",
                ),
            }

        raw_data = indec_raw.get("data", [])
        normalized = [
            {"fecha": row[0], "exportaciones_fob_millones_usd": row[1] if len(row) > 1 else None}
            for row in raw_data
        ]

        return {
            "data": normalized,
            "descripcion": "Exportaciones FOB de cereales y oleaginosas (millones USD)",
            "fuente_serie": serie_id,
            "metadata": _build_metadata(
                status="ok",
                is_fallback=False,
                source_name="INDEC via datos.gob.ar - Series de Tiempo",
            ),
        }
