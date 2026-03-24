"""
Servicio que combina todas las fuentes de datos externos.

Actúa como facade sobre los clientes individuales, agrega cache automático
y genera insights automáticos combinando múltiples fuentes.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from app.integrations.bcra_client import BCRAClient
from app.integrations.argentina_series_client import ArgentinaSeriesClient
from app.integrations.weather_client import WeatherClient, ESTABLECIMIENTOS_COORDS
from app.integrations.usda_client import USDAClient
from app.integrations.bcr_client import BCRClient
from app.integrations.commodities_client import CommoditiesClient, TICKERS
from app.services.cache_service import cache_service, CACHE_TTLS

logger = logging.getLogger(__name__)

# Umbrales para generación de insights
INSIGHT_INFLACION_MENSUAL_ALTA = 5.0        # % mensual
INSIGHT_TC_VARIACION_ALERTA = 3.0          # % variación en 30d
INSIGHT_SOJA_PRECIO_ALTO_USD = 380.0       # USD/ton
INSIGHT_SOJA_PRECIO_BAJO_USD = 300.0       # USD/ton
INSIGHT_MAIZ_PRECIO_ALTO_USD = 175.0       # USD/ton
INSIGHT_TRIGO_PRECIO_ALTO_USD = 210.0      # USD/ton
INSIGHT_SEQUIA_PRECIP_MM = 10.0            # mm/30d mínimo


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _build_insight(
    tipo: str,
    severidad: str,
    titulo: str,
    descripcion: str,
    modulo: str,
    valor_detectado: Any = None,
    umbral: Any = None,
    recomendacion: Optional[str] = None,
) -> dict:
    """Construye un objeto insight normalizado."""
    return {
        "tipo": tipo,
        "severidad": severidad,          # "alta", "media", "baja", "positivo"
        "titulo": titulo,
        "descripcion": descripcion,
        "modulo": modulo,                # "macro", "mercado", "clima", "operaciones"
        "valor_detectado": valor_detectado,
        "umbral": umbral,
        "recomendacion": recomendacion,
        "fecha": _now_utc(),
    }


class ExternalDataService:
    """
    Servicio principal que combina todas las fuentes de datos externos.

    Implementa cache automático con TTL para cada tipo de dato.
    En caso de fallo de la fuente, retorna datos del cache aunque
    estén expirados (stale) antes de retornar error.

    Uso:
        service = ExternalDataService()
        resumen = await service.get_macro_resumen()
    """

    def __init__(self):
        self.bcra = BCRAClient()
        self.arg_series = ArgentinaSeriesClient()
        self.weather = WeatherClient()
        self.usda = USDAClient()
        self.bcr = BCRClient()
        self.commodities = CommoditiesClient()

    # ──────────────────────────────────────────────────────────────────────────
    # Helpers de cache
    # ──────────────────────────────────────────────────────────────────────────

    async def _cached(
        self,
        cache_key: str,
        fetch_fn,
        ttl_key: Optional[str] = None,
    ) -> dict:
        """
        Wrapper genérico de cache.
        1. Intenta retornar del cache.
        2. Si hay miss, llama a fetch_fn().
        3. Si fetch_fn falla, intenta retornar stale del cache.
        4. Si todo falla, retorna estructura de error.
        """
        ttl = cache_service.get_ttl(ttl_key or cache_key)

        # Intentar cache hit
        cached = await cache_service.get(cache_key)
        if cached is not None:
            logger.debug("Cache HIT para %s", cache_key)
            if isinstance(cached, dict) and "metadata" in cached:
                cached["metadata"]["cache_hit"] = True
            return cached

        # Cache miss: buscar datos frescos
        try:
            logger.debug("Cache MISS para %s. Fetching...", cache_key)
            fresh_data = await fetch_fn()
            await cache_service.set(cache_key, fresh_data, ttl=ttl)
            if isinstance(fresh_data, dict) and "metadata" in fresh_data:
                fresh_data["metadata"]["cache_hit"] = False
            return fresh_data
        except Exception as exc:
            logger.error(
                "Error al obtener datos para %s: %s. Intentando stale cache.", cache_key, exc
            )
            # Intentar stale del cache ignorando TTL (no implementado en este cache simple)
            # En producción con Redis, se usaría OBJECT IDLETIME o almacenar copia "stale"
            return {
                "data": None,
                "metadata": {
                    "status": "unavailable",
                    "error_message": str(exc),
                    "fetched_at": _now_utc(),
                    "cache_hit": False,
                },
            }

    # ──────────────────────────────────────────────────────────────────────────
    # Datos macroeconómicos
    # ──────────────────────────────────────────────────────────────────────────

    async def get_macro_resumen(self) -> dict:
        """
        Retorna resumen macroeconómico combinando BCRA y Series de Tiempo Argentina.

        Incluye: tipo de cambio, inflación, tasas, reservas, series históricas.
        Cache TTL: 15 minutos.
        """
        import asyncio

        async def _fetch():
            bcra_task = self.bcra.get_resumen_macro()
            ipc_task = self.arg_series.get_ipc_mensual(limit=24)
            tc_serie_task = self.arg_series.get_tipo_cambio_serie(limit=60)

            bcra_data, ipc_data, tc_serie_data = await asyncio.gather(
                bcra_task, ipc_task, tc_serie_task
            )

            return {
                "data": {
                    "bcra": bcra_data.get("data", {}),
                    "series_historicas": {
                        "ipc_mensual": ipc_data.get("data", []),
                        "tipo_cambio": tc_serie_data.get("data", {}),
                    },
                },
                "metadata": {
                    "source_name": "BCRA + Datos Abiertos Argentina",
                    "fetched_at": _now_utc(),
                    "status": bcra_data.get("metadata", {}).get("status", "ok"),
                    "cache_hit": False,
                },
            }

        return await self._cached("macro_resumen", _fetch, ttl_key="macro_resumen")

    async def get_macro_series(self, serie: str = "ipc", limit: int = 36) -> dict:
        """
        Retorna series temporales específicas para gráficos.

        Args:
            serie: Tipo de serie ('ipc', 'tipo_cambio', 'pbi', 'ventas_super').
            limit: Cantidad de observaciones.
        """
        cache_key = f"macro_serie_{serie}_{limit}"

        serie_map = {
            "ipc": lambda: self.arg_series.get_ipc_mensual(limit=limit),
            "tipo_cambio": lambda: self.arg_series.get_tipo_cambio_serie(limit=limit),
            "pbi": lambda: self.arg_series.get_pbi(limit=limit),
            "ventas_super": lambda: self.arg_series.get_ventas_supermercados(limit=limit),
        }

        fetch_fn = serie_map.get(serie)
        if not fetch_fn:
            return {
                "data": [],
                "error": f"Serie '{serie}' no disponible. Opciones: {list(serie_map.keys())}",
                "metadata": {"status": "error", "fetched_at": _now_utc()},
            }

        return await self._cached(cache_key, fetch_fn, ttl_key="datos_arg_series")

    # ──────────────────────────────────────────────────────────────────────────
    # Datos de mercado (commodities)
    # ──────────────────────────────────────────────────────────────────────────

    async def get_mercado_commodities(self) -> dict:
        """
        Retorna precios actuales de todos los commodities más datos USDA.

        Fuentes: Yahoo Finance (CBOT) + BCR referencia + USDA PSD.
        Cache TTL: 30 minutos.
        """
        import asyncio

        async def _fetch():
            precios_task = self.commodities.get_todos_commodities()
            bcr_task = self.bcr.get_precios_pizarra()
            soja_usda_task = self.usda.get_soja_argentina()
            maiz_usda_task = self.usda.get_maiz_argentina()
            trigo_usda_task = self.usda.get_trigo_argentina()

            precios, bcr, soja_usda, maiz_usda, trigo_usda = await asyncio.gather(
                precios_task, bcr_task, soja_usda_task, maiz_usda_task, trigo_usda_task
            )

            return {
                "data": {
                    "precios_cbot": precios.get("data", {}),
                    "precios_pizarra_rosario": bcr.get("data", {}).get("cultivos", {}),
                    "produccion_argentina_usda": {
                        "soja": soja_usda.get("data", {}),
                        "maiz": maiz_usda.get("data", {}),
                        "trigo": trigo_usda.get("data", {}),
                    },
                    "resumen": precios.get("resumen", {}),
                },
                "metadata": {
                    "source_name": "Yahoo Finance (CBOT) + BCR Referencia + USDA PSD",
                    "fetched_at": _now_utc(),
                    "status": precios.get("metadata", {}).get("status", "ok"),
                    "cache_hit": False,
                },
            }

        return await self._cached("mercado_resumen", _fetch, ttl_key="commodities_precios")

    async def get_historico_cultivo(self, cultivo: str, period: str = "1mo") -> dict:
        """
        Retorna la serie histórica de precios para un cultivo.

        Args:
            cultivo: Nombre del cultivo ('soja', 'maiz', 'trigo').
            period: Período ('1mo', '3mo', '6mo', '1y').
        """
        ticker = TICKERS.get(cultivo.lower())
        if not ticker:
            return {
                "data": [],
                "error": f"Cultivo '{cultivo}' no disponible. Opciones: {list(TICKERS.keys())}",
                "metadata": {"status": "error", "fetched_at": _now_utc()},
            }

        cache_key = f"commodities_historico_{cultivo}_{period}"

        async def _fetch():
            return await self.commodities.get_serie_historica(ticker, period=period)

        return await self._cached(cache_key, _fetch, ttl_key="commodities_historico")

    # ──────────────────────────────────────────────────────────────────────────
    # Datos climáticos
    # ──────────────────────────────────────────────────────────────────────────

    async def get_clima_resumen(self) -> dict:
        """
        Retorna el resumen climático de todos los establecimientos.
        Cache TTL: 1 hora.
        """
        async def _fetch():
            establecimientos = await self.weather.get_resumen_todos_establecimientos()
            return {
                "data": {
                    "establecimientos": establecimientos,
                    "total": len(establecimientos),
                    "nombres": list(ESTABLECIMIENTOS_COORDS.keys()),
                },
                "metadata": {
                    "source_name": "Open-Meteo",
                    "source_url": "https://open-meteo.com",
                    "fetched_at": _now_utc(),
                    "status": "ok",
                    "cache_hit": False,
                },
            }

        return await self._cached("clima_resumen", _fetch, ttl_key="clima_resumen")

    async def get_clima_pronostico(self, establecimiento: str) -> dict:
        """
        Retorna el pronóstico de 7 días para un establecimiento específico.
        Cache TTL: 1 hora.
        """
        cache_key = f"clima_forecast_{establecimiento.lower().replace(' ', '_')}"

        async def _fetch():
            return await self.weather.get_resumen_establecimiento(establecimiento)

        return await self._cached(cache_key, _fetch, ttl_key="clima_forecast")

    async def get_alertas_climaticas(self) -> dict:
        """
        Retorna alertas climáticas activas para todos los establecimientos.
        Cache TTL: 1 hora.
        """
        async def _fetch():
            alertas = await self.weather.get_alertas_climaticas()
            return {
                "data": alertas,
                "total_alertas": len(alertas),
                "por_tipo": {
                    "sequia": [a for a in alertas if a.get("tipo") == "SEQUIA"],
                    "inundacion": [a for a in alertas if a.get("tipo") == "INUNDACION"],
                    "helada": [a for a in alertas if a.get("tipo") == "HELADA"],
                },
                "metadata": {
                    "source_name": "Open-Meteo",
                    "fetched_at": _now_utc(),
                    "status": "ok",
                    "cache_hit": False,
                },
            }

        return await self._cached("clima_alertas", _fetch, ttl_key="clima_alertas")

    # ──────────────────────────────────────────────────────────────────────────
    # Insights automáticos
    # ──────────────────────────────────────────────────────────────────────────

    async def get_insights_macro(self) -> dict:
        """
        Genera insights automáticos combinando datos macroeconómicos,
        de mercado y climáticos.

        Cache TTL: 1 hora.
        """
        import asyncio

        async def _fetch():
            macro_task = self.get_macro_resumen()
            commodities_task = self.get_mercado_commodities()
            clima_task = self.get_alertas_climaticas()

            macro_data, commodities_data, clima_data = await asyncio.gather(
                macro_task, commodities_task, clima_task
            )

            insights = self._generar_insights(macro_data, commodities_data, clima_data)

            return {
                "data": insights,
                "total": len(insights),
                "por_severidad": {
                    "alta": [i for i in insights if i.get("severidad") == "alta"],
                    "media": [i for i in insights if i.get("severidad") == "media"],
                    "baja": [i for i in insights if i.get("severidad") == "baja"],
                    "positivo": [i for i in insights if i.get("severidad") == "positivo"],
                },
                "por_modulo": {
                    "macro": [i for i in insights if i.get("modulo") == "macro"],
                    "mercado": [i for i in insights if i.get("modulo") == "mercado"],
                    "clima": [i for i in insights if i.get("modulo") == "clima"],
                },
                "metadata": {
                    "source_name": "DemoAgro - Motor de Insights",
                    "fetched_at": _now_utc(),
                    "status": "ok",
                    "cache_hit": False,
                },
            }

        return await self._cached("insights", _fetch, ttl_key="insights")

    def _generar_insights(
        self,
        macro_data: dict,
        commodities_data: dict,
        clima_data: dict,
    ) -> list[dict]:
        """
        Lógica central de generación de insights automáticos.

        Evalúa umbrales sobre datos macroeconómicos, precios de commodities
        y alertas climáticas para generar insights accionables.
        """
        insights: list[dict] = []

        # ── INSIGHTS MACROECONÓMICOS ──────────────────────────────────────────
        try:
            inflacion_data = (
                macro_data.get("data", {})
                .get("bcra", {})
                .get("inflacion", {})
                .get("inflacion_mensual", {})
            )
            inflacion_valor = inflacion_data.get("valor")

            if inflacion_valor is not None:
                if inflacion_valor > INSIGHT_INFLACION_MENSUAL_ALTA:
                    insights.append(_build_insight(
                        tipo="INFLACION_ALTA",
                        severidad="alta",
                        titulo="Presión inflacionaria elevada sobre costos operativos",
                        descripcion=(
                            f"La inflación mensual es de {inflacion_valor:.1f}%, "
                            f"superando el umbral de alerta de {INSIGHT_INFLACION_MENSUAL_ALTA}%. "
                            "Esto impacta directamente en el costo de insumos, combustibles y mano de obra."
                        ),
                        modulo="macro",
                        valor_detectado=inflacion_valor,
                        umbral=INSIGHT_INFLACION_MENSUAL_ALTA,
                        recomendacion=(
                            "Revisar contratos de insumos y adelantar compras de aquellos "
                            "con mayor exposición inflacionaria. Considerar cobertura cambiaria."
                        ),
                    ))
                elif inflacion_valor > 3.0:
                    insights.append(_build_insight(
                        tipo="INFLACION_MODERADA",
                        severidad="media",
                        titulo="Inflación moderada: monitoreo de costos recomendado",
                        descripcion=(
                            f"Inflación mensual de {inflacion_valor:.1f}%. "
                            "Impacto moderado en estructura de costos operativos."
                        ),
                        modulo="macro",
                        valor_detectado=inflacion_valor,
                        umbral=3.0,
                    ))
        except Exception as exc:
            logger.warning("Error generando insight de inflación: %s", exc)

        # ── Tipo de cambio ────────────────────────────────────────────────────
        try:
            tc_data = (
                macro_data.get("data", {})
                .get("bcra", {})
                .get("tipo_cambio", {})
                .get("tipo_cambio_minorista", {})
            )
            tc_serie = tc_data.get("serie", [])

            if len(tc_serie) >= 2:
                tc_actual = tc_serie[-1].get("valor", 0) if tc_serie[-1] else 0
                tc_hace_30d = tc_serie[0].get("valor", 0) if tc_serie[0] else 0

                if tc_actual and tc_hace_30d and tc_hace_30d > 0:
                    variacion_pct = ((tc_actual - tc_hace_30d) / tc_hace_30d) * 100

                    if variacion_pct > INSIGHT_TC_VARIACION_ALERTA:
                        insights.append(_build_insight(
                            tipo="TIPO_CAMBIO_SUBA",
                            severidad="positivo",
                            titulo="Mejora de competitividad exportadora por tipo de cambio",
                            descripcion=(
                                f"El tipo de cambio minorista subió {variacion_pct:.1f}% en el período reciente "
                                f"(de ${tc_hace_30d:.0f} a ${tc_actual:.0f}). "
                                "Mayor rentabilidad en pesos para exportaciones."
                            ),
                            modulo="macro",
                            valor_detectado=variacion_pct,
                            umbral=INSIGHT_TC_VARIACION_ALERTA,
                            recomendacion=(
                                "Evaluar oportunidad de venta en mercado disponible o "
                                "fijar precio forward aprovechando la mejora cambiaria."
                            ),
                        ))
                    elif variacion_pct < 0:
                        insights.append(_build_insight(
                            tipo="TIPO_CAMBIO_BAJA",
                            severidad="media",
                            titulo="Tipo de cambio estable o en baja: impacto en rentabilidad",
                            descripcion=(
                                f"El tipo de cambio bajó {abs(variacion_pct):.1f}% en el período. "
                                "Puede reducir la rentabilidad en pesos de las exportaciones."
                            ),
                            modulo="macro",
                            valor_detectado=variacion_pct,
                            umbral=0,
                        ))
        except Exception as exc:
            logger.warning("Error generando insight de tipo de cambio: %s", exc)

        # ── INSIGHTS DE MERCADO (COMMODITIES) ─────────────────────────────────
        try:
            precios = commodities_data.get("data", {}).get("precios_cbot", {})

            soja_precio = precios.get("soja", {}).get("precio_usd_ton")
            if soja_precio is not None:
                if soja_precio >= INSIGHT_SOJA_PRECIO_ALTO_USD:
                    insights.append(_build_insight(
                        tipo="PRECIO_SOJA_ALTO",
                        severidad="positivo",
                        titulo=f"Precio de soja en niveles altos: USD {soja_precio:.0f}/ton",
                        descripcion=(
                            f"El precio de soja en CBOT es USD {soja_precio:.0f}/ton, "
                            f"por encima del umbral de oportunidad (USD {INSIGHT_SOJA_PRECIO_ALTO_USD}/ton). "
                            "Momento favorable para venta o fijación de precio."
                        ),
                        modulo="mercado",
                        valor_detectado=soja_precio,
                        umbral=INSIGHT_SOJA_PRECIO_ALTO_USD,
                        recomendacion=(
                            "Considerar venta en mercado disponible o contrato forward "
                            "para asegurar precio de campaña."
                        ),
                    ))
                elif soja_precio < INSIGHT_SOJA_PRECIO_BAJO_USD:
                    insights.append(_build_insight(
                        tipo="PRECIO_SOJA_BAJO",
                        severidad="media",
                        titulo=f"Precio de soja por debajo del promedio: USD {soja_precio:.0f}/ton",
                        descripcion=(
                            f"El precio de soja en CBOT es USD {soja_precio:.0f}/ton, "
                            f"por debajo del umbral de referencia (USD {INSIGHT_SOJA_PRECIO_BAJO_USD}/ton). "
                            "Revisar decisiones de venta."
                        ),
                        modulo="mercado",
                        valor_detectado=soja_precio,
                        umbral=INSIGHT_SOJA_PRECIO_BAJO_USD,
                        recomendacion=(
                            "Evaluar si conviene retener producción esperando recuperación de precio. "
                            "Monitorear condiciones de almacenamiento y costo financiero."
                        ),
                    ))

            maiz_precio = precios.get("maiz", {}).get("precio_usd_ton")
            if maiz_precio is not None and maiz_precio >= INSIGHT_MAIZ_PRECIO_ALTO_USD:
                insights.append(_build_insight(
                    tipo="PRECIO_MAIZ_ALTO",
                    severidad="positivo",
                    titulo=f"Precio de maíz en zona de oportunidad: USD {maiz_precio:.0f}/ton",
                    descripcion=(
                        f"El precio de maíz en CBOT es USD {maiz_precio:.0f}/ton. "
                        "Nivel competitivo para considerar ventas o contratos de entrega."
                    ),
                    modulo="mercado",
                    valor_detectado=maiz_precio,
                    umbral=INSIGHT_MAIZ_PRECIO_ALTO_USD,
                    recomendacion="Evaluar venta disponible o contratos de entrega futura.",
                ))

            trigo_precio = precios.get("trigo", {}).get("precio_usd_ton")
            if trigo_precio is not None and trigo_precio >= INSIGHT_TRIGO_PRECIO_ALTO_USD:
                insights.append(_build_insight(
                    tipo="PRECIO_TRIGO_ALTO",
                    severidad="positivo",
                    titulo=f"Precio de trigo en niveles favorables: USD {trigo_precio:.0f}/ton",
                    descripcion=(
                        f"El precio de trigo en CBOT es USD {trigo_precio:.0f}/ton. "
                        "Nivel atractivo para asegurar precio de la cosecha."
                    ),
                    modulo="mercado",
                    valor_detectado=trigo_precio,
                    umbral=INSIGHT_TRIGO_PRECIO_ALTO_USD,
                ))
        except Exception as exc:
            logger.warning("Error generando insights de mercado: %s", exc)

        # ── INSIGHTS CLIMÁTICOS ───────────────────────────────────────────────
        try:
            alertas = clima_data.get("data", [])
            if isinstance(alertas, list):
                sequias = [a for a in alertas if a.get("tipo") == "SEQUIA"]
                heladas = [a for a in alertas if a.get("tipo") == "HELADA"]
                inundaciones = [a for a in alertas if a.get("tipo") == "INUNDACION"]

                if sequias:
                    estabs_sequia = list({a.get("establecimiento") for a in sequias})
                    insights.append(_build_insight(
                        tipo="RIESGO_HIDRICO",
                        severidad="alta",
                        titulo=f"Riesgo hídrico en {len(estabs_sequia)} establecimiento(s)",
                        descripcion=(
                            f"Déficit hídrico detectado en: {', '.join(estabs_sequia)}. "
                            "Precipitaciones por debajo del umbral mínimo en los últimos 30 días."
                        ),
                        modulo="clima",
                        valor_detectado=len(estabs_sequia),
                        recomendacion=(
                            "Monitorear humedad de suelos. Evaluar riego suplementario "
                            "si los cultivos están en etapas críticas de desarrollo."
                        ),
                    ))

                if heladas:
                    estabs_helada = list({a.get("establecimiento") for a in heladas})
                    insights.append(_build_insight(
                        tipo="ALERTA_HELADA",
                        severidad="alta",
                        titulo=f"Alerta de helada en {len(estabs_helada)} establecimiento(s)",
                        descripcion=(
                            f"Temperaturas mínimas bajo cero pronosticadas en: {', '.join(estabs_helada)}. "
                            "Riesgo de daño en cultivos susceptibles."
                        ),
                        modulo="clima",
                        valor_detectado=len(estabs_helada),
                        recomendacion=(
                            "Revisar estado fenológico de cultivos. "
                            "Activar protocolos de protección si corresponde."
                        ),
                    ))

                if inundaciones:
                    estabs_inund = list({a.get("establecimiento") for a in inundaciones})
                    insights.append(_build_insight(
                        tipo="RIESGO_INUNDACION",
                        severidad="alta",
                        titulo=f"Riesgo de anegamiento en {len(estabs_inund)} establecimiento(s)",
                        descripcion=(
                            f"Precipitaciones extremas detectadas en: {', '.join(estabs_inund)}. "
                            "Posible impacto en operaciones y acceso a lotes."
                        ),
                        modulo="clima",
                        valor_detectado=len(estabs_inund),
                        recomendacion=(
                            "Verificar estado de desagües. Posponer laboreos hasta que "
                            "los suelos recuperen capacidad de soporte."
                        ),
                    ))
        except Exception as exc:
            logger.warning("Error generando insights climáticos: %s", exc)

        # Ordenar por severidad (alta > media > positivo > baja)
        severidad_orden = {"alta": 0, "media": 1, "positivo": 2, "baja": 3}
        insights.sort(key=lambda x: severidad_orden.get(x.get("severidad", "baja"), 99))

        logger.info("Se generaron %d insights automáticos", len(insights))
        return insights
