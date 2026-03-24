import math
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.integrations.argentina_series_client import ArgentinaSeriesClient
from app.services.campaign_scope import resolve_campaign_id
from app.services.decision_data import load_position_rows
from app.services.external_data_service import ExternalDataService

router = APIRouter()
service = ExternalDataService()
arg_series = ArgentinaSeriesClient()

COMMODITY_COST_MODEL_USD_TN = {
    "soja": 318.0,
    "maiz": 162.0,
    "trigo": 194.0,
    "girasol": 402.0,
}

COMMODITY_FALLBACK_VARIATIONS = {
    "soja": {"var_7d": 1.8, "var_30d": 4.3, "volatility": 0.018, "phase": 0.2},
    "maiz": {"var_7d": -0.9, "var_30d": 1.6, "volatility": 0.014, "phase": 1.4},
    "trigo": {"var_7d": 0.7, "var_30d": 2.5, "volatility": 0.016, "phase": 0.8},
    "girasol": {"var_7d": 1.5, "var_30d": 4.9, "volatility": 0.02, "phase": 0.5},
}

COMMODITY_ORDER = ("soja", "maiz", "trigo", "girasol")
COMMODITY_LABELS = {
    "soja": "Soja",
    "maiz": "Maíz",
    "trigo": "Trigo",
    "girasol": "Girasol",
}


def _map_external_severity(value: str) -> str:
    return {
        "alta": "critical",
        "media": "warning",
        "baja": "info",
        "positivo": "success",
    }.get(value, "info")


def _weather_label(code: int) -> str:
    if code == 0:
        return "Cielo despejado"
    if code <= 2:
        return "Parcialmente nublado"
    if code == 3:
        return "Nublado"
    if code <= 48:
        return "Neblina"
    if code <= 67:
        return "Lluvia"
    if code <= 77:
        return "Nieve"
    if code <= 86:
        return "Chaparrones"
    if code <= 99:
        return "Tormenta"
    return "Variable"


def _normalize_crop_key(value: str) -> str:
    normalized = (value or "").strip().lower()
    return {
        "soja": "soja",
        "maiz": "maiz",
        "maíz": "maiz",
        "trigo": "trigo",
        "girasol": "girasol",
    }.get(normalized, normalized)


def _safe_pct(current: float, base: float, fallback: float = 0.0) -> float:
    if not base:
        return round(fallback, 2)
    return round(((current - base) / base) * 100, 2)


def _avg(values: list[float]) -> float:
    valid = [value for value in values if value is not None]
    if not valid:
        return 0.0
    return round(sum(valid) / len(valid), 2)


def _extract_first_numeric_value(row: dict | None) -> float | None:
    if not row:
        return None
    for key, value in row.items():
        if key == "fecha":
            continue
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _severity_to_action_tag(severity: str) -> str:
    return {
        "critical": "riesgo",
        "warning": "atención",
        "success": "oportunidad",
        "info": "neutral",
    }.get(severity, "neutral")


def _macro_recommendation_tone(
    tasa_real_pct: float,
    inflacion_delta_vs_3m: float,
    tc_oficial_var_30d_pct: float,
    inflacion_mensual: float,
) -> tuple[str, str, str]:
    if tasa_real_pct > 6:
        return (
            "riesgo",
            "critical",
            "Costo financiero real alto: conviene acortar financiamiento en pesos y revisar capital de trabajo comprometido.",
        )
    if inflacion_delta_vs_3m < -0.5 and tc_oficial_var_30d_pct <= inflacion_mensual:
        return (
            "favorable",
            "success",
            "La desaceleración inflacionaria mejora previsibilidad, pero el tipo de cambio sigue corriendo por debajo del costo local.",
        )
    return (
        "neutral",
        "warning",
        "Contexto mixto: conviene sostener cobertura de costos dolarizados y evitar financiar campaña sin revisar tasa efectiva.",
    )


def _climate_window_assessment(
    precip_48h_mm: float,
    humidity_avg_pct: float,
    wind_avg_kmh: float,
) -> tuple[str, str, str]:
    if precip_48h_mm <= 5 and humidity_avg_pct <= 82 and wind_avg_kmh <= 22:
        return (
            "favorable",
            "success",
            "Hay ventana operativa para siembra, pulverización o movimiento de equipos en las próximas 48 hs.",
        )
    if precip_48h_mm <= 18 and wind_avg_kmh <= 28:
        return (
            "mixta",
            "warning",
            "La ventana es utilizable, pero conviene priorizar lotes livianos y revisar humedad antes de entrar.",
        )
    return (
        "adversa",
        "critical",
        "El pronóstico complica la ejecución: conviene reprogramar labores sensibles y cuidar transitabilidad.",
    )


def _climate_risk_assessment(
    lluvia_72h_mm: float,
    lluvia_30d_mm: float,
    humedad_avg_pct: float,
) -> tuple[str, str, str]:
    if lluvia_72h_mm >= 30 or humedad_avg_pct >= 88:
        return (
            "adverso",
            "critical",
            "Exceso hídrico y humedad alta elevan el riesgo operativo y la posibilidad de atraso en labores.",
        )
    if lluvia_30d_mm <= 20 and lluvia_72h_mm <= 8:
        return (
            "déficit hídrico",
            "warning",
            "La lluvia acumulada sigue corta: conviene monitorear estrés y ajustar expectativas de rinde en lotes más restrictivos.",
        )
    return (
        "neutral",
        "success",
        "Las condiciones son estables y no muestran un riesgo climático dominante para la operación inmediata.",
    )


def _build_fallback_history(crop: str, current_price: float, days: int = 730) -> list[dict]:
    profile = COMMODITY_FALLBACK_VARIATIONS.get(crop, COMMODITY_FALLBACK_VARIATIONS["soja"])
    target_30d = profile["var_30d"]
    start_price = current_price / (1 + (target_30d / 100)) if current_price else COMMODITY_COST_MODEL_USD_TN[crop] * 1.05
    start_date = datetime.utcnow().date() - timedelta(days=days - 1)
    history = []

    for idx in range(days):
        progress = idx / max(days - 1, 1)
        trend_value = start_price + ((current_price - start_price) * progress)
        wave = current_price * profile["volatility"] * math.sin((idx / 3.2) + profile["phase"])
        price = round(max(trend_value + wave, current_price * 0.72 if current_price else 1), 2)
        history.append(
            {
                "fecha": (start_date + timedelta(days=idx)).isoformat(),
                "precio_usd_tn": price,
                "high_usd_tn": round(price * 1.008, 2),
                "low_usd_tn": round(price * 0.992, 2),
                "source": "fallback",
            }
        )

    if history:
        history[-1]["precio_usd_tn"] = round(current_price or history[-1]["precio_usd_tn"], 2)
        history[-1]["high_usd_tn"] = round(history[-1]["precio_usd_tn"] * 1.008, 2)
        history[-1]["low_usd_tn"] = round(history[-1]["precio_usd_tn"] * 0.992, 2)

    return history


def _prepare_history_series(crop: str, current_price: float, payload: dict | None) -> tuple[list[dict], bool]:
    rows = payload.get("data", []) if payload else []
    series = []

    for row in rows[-520:]:
        price = row.get("precio_usd_ton")
        fecha = row.get("fecha")
        if not fecha or price is None:
            continue
        series.append(
            {
                "fecha": fecha,
                "precio_usd_tn": round(price, 2),
                "high_usd_tn": round(row.get("high_usd_ton") or price, 2),
                "low_usd_tn": round(row.get("low_usd_ton") or price, 2),
                "source": "real",
            }
        )

    is_fallback = len(series) < 10
    if is_fallback:
        return _build_fallback_history(crop, current_price), True

    series[-1]["precio_usd_tn"] = round(current_price or series[-1]["precio_usd_tn"], 2)
    series[-1]["high_usd_tn"] = round(max(series[-1]["high_usd_tn"], series[-1]["precio_usd_tn"]), 2)
    series[-1]["low_usd_tn"] = round(min(series[-1]["low_usd_tn"], series[-1]["precio_usd_tn"]), 2)
    return series, False


def _compute_market_recommendation(
    margin_pct: float,
    variation_7d: float,
    variation_30d: float,
    uncovered_pct: float,
) -> tuple[str, str, str]:
    if margin_pct <= 4 or variation_30d <= -4:
        return (
            "riesgo",
            "critical",
            "Precio cerca del break-even: conviene cubrir exposición y evitar esperar una corrección adicional.",
        )
    if margin_pct >= 12 and uncovered_pct >= 20:
        return (
            "favorable venta",
            "success",
            "Hay margen positivo y exposición abierta: vender o fijar una parte mejora la captura del resultado actual.",
        )
    if margin_pct >= 8 and variation_7d > 1.5:
        return (
            "favorable venta",
            "success",
            "El precio sostiene tendencia positiva y margen cómodo: buena ventana para ventas escalonadas.",
        )
    return (
        "neutral",
        "warning" if uncovered_pct > 30 else "info",
        "El mercado no está en zona crítica, pero conviene monitorear cobertura y tendencia antes de tomar posición.",
    )


async def _build_commodity_market_panel(db: AsyncSession) -> dict:
    mercado = await service.get_mercado_commodities()

    import asyncio

    soja_hist, maiz_hist, trigo_hist = await asyncio.gather(
        service.get_historico_cultivo("soja", period="2y"),
        service.get_historico_cultivo("maiz", period="2y"),
        service.get_historico_cultivo("trigo", period="2y"),
    )
    history_payloads = {
        "soja": soja_hist,
        "maiz": maiz_hist,
        "trigo": trigo_hist,
        "girasol": {"data": []},
    }

    active_campaign_id = await resolve_campaign_id(db=db)
    position_rows = await load_position_rows(db=db, campania_id=active_campaign_id)
    aggregated_exposure: dict[str, dict] = {}
    for posicion, cultivo in position_rows:
        crop_key = _normalize_crop_key(cultivo.nombre)
        if crop_key not in COMMODITY_ORDER:
            continue
        bucket = aggregated_exposure.setdefault(
            crop_key,
            {
                "cultivo": COMMODITY_LABELS[crop_key],
                "toneladas_producidas": 0.0,
                "toneladas_vendidas": 0.0,
                "toneladas_fijadas": 0.0,
                "toneladas_entregadas": 0.0,
            },
        )
        bucket["toneladas_producidas"] += posicion.toneladas_producidas or 0
        bucket["toneladas_vendidas"] += posicion.toneladas_comprometidas or 0
        bucket["toneladas_fijadas"] += posicion.toneladas_fijadas or 0
        bucket["toneladas_entregadas"] += posicion.toneladas_entregadas or 0

    precios_cbot = mercado.get("data", {}).get("precios_cbot", {})
    price_items = []
    comparison = []
    series_by_crop: dict[str, list[dict]] = {}
    fallback_crops: list[str] = []

    for crop_key in COMMODITY_ORDER:
        market_row = precios_cbot.get(crop_key, {})
        current_price = round(market_row.get("precio_usd_ton") or 0, 2)
        if current_price <= 0 and crop_key == "girasol":
            current_price = 455.0

        series, history_is_fallback = _prepare_history_series(
            crop_key,
            current_price,
            history_payloads.get(crop_key),
        )
        series_by_crop[crop_key] = [
            {
                "fecha": point["fecha"],
                "precio_usd_tn": point["precio_usd_tn"],
                "break_even_usd_tn": COMMODITY_COST_MODEL_USD_TN[crop_key],
                "margen_usd_tn": round(point["precio_usd_tn"] - COMMODITY_COST_MODEL_USD_TN[crop_key], 2),
                "rentable": point["precio_usd_tn"] >= COMMODITY_COST_MODEL_USD_TN[crop_key],
                "source": point["source"],
            }
            for point in series
        ]
        if history_is_fallback:
            fallback_crops.append(COMMODITY_LABELS[crop_key])

        recent_prices = [point["precio_usd_tn"] for point in series if point.get("precio_usd_tn") is not None]
        profile = COMMODITY_FALLBACK_VARIATIONS[crop_key]
        latest_price = round(current_price or (recent_prices[-1] if recent_prices else 0), 2)
        base_7d = recent_prices[-8] if len(recent_prices) >= 8 else (recent_prices[0] if recent_prices else 0)
        base_30d = recent_prices[0] if recent_prices else 0
        variation_7d = _safe_pct(latest_price, base_7d, profile["var_7d"])
        variation_30d = _safe_pct(latest_price, base_30d, profile["var_30d"])
        min_recent = round(min(recent_prices), 2) if recent_prices else round(latest_price * 0.95, 2)
        max_recent = round(max(recent_prices), 2) if recent_prices else round(latest_price * 1.05, 2)

        cost_estimate = COMMODITY_COST_MODEL_USD_TN[crop_key]
        margin_usd = round(latest_price - cost_estimate, 2)
        margin_pct = round((margin_usd / cost_estimate) * 100, 1) if cost_estimate else 0

        exposure = aggregated_exposure.get(
            crop_key,
            {
                "cultivo": COMMODITY_LABELS[crop_key],
                "toneladas_producidas": 0.0,
                "toneladas_vendidas": 0.0,
                "toneladas_fijadas": 0.0,
                "toneladas_entregadas": 0.0,
            },
        )
        toneladas_sin_precio = round(
            max(exposure["toneladas_producidas"] - exposure["toneladas_fijadas"], 0),
            2,
        )
        sin_cobertura_pct = round(
            (toneladas_sin_precio / exposure["toneladas_producidas"]) * 100,
            1,
        ) if exposure["toneladas_producidas"] else 0
        risk_price_drop = round(toneladas_sin_precio * latest_price * 0.05, 2)

        recommendation, severity, action = _compute_market_recommendation(
            margin_pct,
            variation_7d,
            variation_30d,
            sin_cobertura_pct,
        )

        price_items.append(
            {
                "nombre": COMMODITY_LABELS[crop_key],
                "simbolo": crop_key,
                "precio_usd_tn": latest_price,
                "variacion_7d_pct": variation_7d,
                "variacion_30d_pct": variation_30d,
                "variacion_semanal": variation_7d,
                "variacion_pct": variation_7d,
                "precio_min_reciente_usd_tn": min_recent,
                "precio_max_reciente_usd_tn": max_recent,
                "costo_estimado_usd_tn": cost_estimate,
                "breakeven_usd_tn": cost_estimate,
                "margen_usd_tn": margin_usd,
                "margen_pct": margin_pct,
                "recomendacion": recommendation,
                "severidad": severity,
                "accion_sugerida": action,
                "historico_fallback": history_is_fallback,
                "toneladas_producidas": round(exposure["toneladas_producidas"], 2),
                "toneladas_vendidas": round(exposure["toneladas_vendidas"], 2),
                "toneladas_sin_precio": toneladas_sin_precio,
                "sin_cobertura_pct": sin_cobertura_pct,
                "riesgo_caida_5pct_usd": risk_price_drop,
            }
        )

        comparison.append(
            {
                "cultivo": COMMODITY_LABELS[crop_key],
                "simbolo": crop_key,
                "precio_usd_tn": latest_price,
                "costo_estimado_usd_tn": cost_estimate,
                "margen_usd_tn": margin_usd,
                "margen_pct": margin_pct,
                "recomendacion": recommendation,
                "severidad": severity,
            }
        )

    comparison.sort(key=lambda item: item["margen_usd_tn"], reverse=True)
    for index, item in enumerate(comparison, start=1):
        item["ranking"] = index

    exposure_rows = []
    total_produced = 0.0
    total_unpriced = 0.0
    for item in price_items:
        total_produced += item["toneladas_producidas"]
        total_unpriced += item["toneladas_sin_precio"]
        exposure_rows.append(
            {
                "cultivo": item["nombre"],
                "simbolo": item["simbolo"],
                "toneladas_producidas": item["toneladas_producidas"],
                "toneladas_vendidas": item["toneladas_vendidas"],
                "toneladas_sin_precio": item["toneladas_sin_precio"],
                "sin_cobertura_pct": item["sin_cobertura_pct"],
                "riesgo_caida_5pct_usd": item["riesgo_caida_5pct_usd"],
                "recomendacion": item["recomendacion"],
                "severidad": item["severidad"],
            }
        )

    exposure_rows.sort(key=lambda item: item["sin_cobertura_pct"], reverse=True)
    best_margin = comparison[0] if comparison else None
    riskiest_crop = exposure_rows[0] if exposure_rows else None

    insights = []
    now_iso = datetime.utcnow().isoformat()
    if best_margin:
        insights.append(
            {
                "id": f"commod-best-{best_margin['simbolo']}",
                "titulo": f"{best_margin['cultivo']} tiene el mejor margen actual",
                "descripcion": (
                    f"Deja {best_margin['margen_usd_tn']:.0f} USD/tn ({best_margin['margen_pct']:.1f}%) "
                    "sobre el costo estimado."
                ),
                "severidad": "success",
                "tab": "commodities",
                "timestamp": now_iso,
            }
        )

    near_break_even = min(price_items, key=lambda item: abs(item["margen_pct"])) if price_items else None
    if near_break_even and near_break_even["margen_pct"] <= 5:
        insights.append(
            {
                "id": f"commod-break-{near_break_even['simbolo']}",
                "titulo": f"{near_break_even['nombre']} está cerca del break-even",
                "descripcion": (
                    f"El margen estimado es {near_break_even['margen_usd_tn']:.0f} USD/tn "
                    f"({near_break_even['margen_pct']:.1f}%). Conviene cubrir exposición antes de esperar más precio."
                ),
                "severidad": "warning" if near_break_even["margen_pct"] > 0 else "critical",
                "tab": "commodities",
                "timestamp": now_iso,
            }
        )

    strongest_trend = max(price_items, key=lambda item: item["variacion_7d_pct"]) if price_items else None
    if strongest_trend and strongest_trend["variacion_7d_pct"] >= 1:
        insights.append(
            {
                "id": f"commod-trend-{strongest_trend['simbolo']}",
                "titulo": f"{strongest_trend['nombre']} muestra la mejor inercia reciente",
                "descripcion": (
                    f"Sube {strongest_trend['variacion_7d_pct']:.1f}% en 7 días y "
                    f"{strongest_trend['variacion_30d_pct']:.1f}% en 30 días."
                ),
                "severidad": "info",
                "tab": "commodities",
                "timestamp": now_iso,
            }
        )

    if riskiest_crop and riskiest_crop["sin_cobertura_pct"] >= 25:
        insights.append(
            {
                "id": f"commod-risk-{riskiest_crop['simbolo']}",
                "titulo": f"{riskiest_crop['cultivo']} concentra el mayor riesgo de precio",
                "descripcion": (
                    f"Tiene {riskiest_crop['sin_cobertura_pct']:.1f}% sin cobertura. "
                    f"Una baja de 5% impactaría unos {riskiest_crop['riesgo_caida_5pct_usd']:.0f} USD."
                ),
                "severidad": "warning" if riskiest_crop["sin_cobertura_pct"] < 45 else "critical",
                "tab": "commodities",
                "timestamp": now_iso,
            }
        )

    aggregated_history: dict[str, dict] = {}
    for crop_key, series in series_by_crop.items():
        for point in series:
            aggregated_history.setdefault(
                point["fecha"],
                {
                    "fecha": point["fecha"],
                    "soja": None,
                    "maiz": None,
                    "trigo": None,
                    "girasol": None,
                },
            )
            aggregated_history[point["fecha"]][crop_key] = point["precio_usd_tn"]

    return {
        "precios": price_items,
        "historico_30d": [aggregated_history[key] for key in sorted(aggregated_history.keys())[-30:]],
        "series_by_crop": series_by_crop,
        "comparador": comparison,
        "exposicion_comercial": exposure_rows,
        "insights": insights,
        "summary": {
            "mejor_margen_cultivo": best_margin["cultivo"] if best_margin else None,
            "mejor_margen_pct": best_margin["margen_pct"] if best_margin else 0,
            "mejor_margen_usd_tn": best_margin["margen_usd_tn"] if best_margin else 0,
            "sin_cobertura_pct_total": round((total_unpriced / total_produced) * 100, 1) if total_produced else 0,
            "toneladas_sin_precio_total": round(total_unpriced, 2),
            "cultivo_mayor_riesgo": riskiest_crop["cultivo"] if riskiest_crop else None,
        },
        "historico_nota": (
            "Histórico sintetizado sobre precio actual cuando el proveedor no entregó serie completa."
            if fallback_crops
            else None
        ),
        "historico_cultivos_fallback": fallback_crops,
        "fuente": mercado.get("metadata", {}).get("source_name", "Yahoo Finance"),
        "ultima_actualizacion": mercado.get("metadata", {}).get(
            "fetched_at",
            datetime.now().isoformat(),
        ),
    }


async def _build_macro_decision_panel() -> dict:
    import asyncio

    macro, ipc_variacion, ventas_super = await asyncio.gather(
        service.get_macro_resumen(),
        arg_series.get_ipc_variacion_mensual(limit=48),
        arg_series.get_ventas_supermercados(limit=48),
    )

    bcra = macro.get("data", {}).get("bcra", {})
    tipo_cambio = bcra.get("tipo_cambio", {})
    inflacion = bcra.get("inflacion", {})
    tasas = bcra.get("tasas", {})
    series_historicas = macro.get("data", {}).get("series_historicas", {})

    oficial = tipo_cambio.get("tipo_cambio_minorista", {})
    mayorista = tipo_cambio.get("tipo_cambio_mayorista", {})
    oficial_serie = [
        {
            "fecha": item.get("fecha"),
            "valor": round(item.get("valor") or 0, 2),
        }
        for item in oficial.get("serie", [])
        if item.get("fecha")
    ]
    if not oficial_serie:
        oficial_serie = [
            {
                "fecha": item.get("fecha"),
                "valor": round(item.get("168.1_T_CAMBIOR_D_0_0_26") or 0, 2),
            }
            for item in series_historicas.get("tipo_cambio", {}).get("tipo_cambio_bna_vendedor", [])
            if item.get("fecha")
        ]

    mayorista_serie = [
        {
            "fecha": item.get("fecha"),
            "valor": round(item.get("valor") or 0, 2),
        }
        for item in mayorista.get("serie", [])
        if item.get("fecha")
    ]

    fx_index: dict[str, dict] = {}
    for item in oficial_serie:
        fx_index.setdefault(
            item["fecha"],
            {
                "fecha": item["fecha"],
                "tipo_cambio_oficial": None,
                "tipo_cambio_mayorista": None,
                "spread_cambiario_pct": None,
            },
        )["tipo_cambio_oficial"] = item["valor"]
    for item in mayorista_serie:
        fx_index.setdefault(
            item["fecha"],
            {
                "fecha": item["fecha"],
                "tipo_cambio_oficial": None,
                "tipo_cambio_mayorista": None,
                "spread_cambiario_pct": None,
            },
        )["tipo_cambio_mayorista"] = item["valor"]

    fx_series = []
    for fecha in sorted(fx_index.keys()):
        row = fx_index[fecha]
        oficial_val = row["tipo_cambio_oficial"]
        mayorista_val = row["tipo_cambio_mayorista"]
        row["spread_cambiario_pct"] = round(
            ((oficial_val - mayorista_val) / mayorista_val) * 100,
            2,
        ) if oficial_val and mayorista_val else None
        fx_series.append(row)

    oficial_values = [item["valor"] for item in oficial_serie if item.get("valor") is not None]
    mayorista_values = [item["valor"] for item in mayorista_serie if item.get("valor") is not None]
    current_official = round(oficial.get("valor") or (oficial_values[-1] if oficial_values else 0), 2)
    current_mayorista = round(mayorista.get("valor") or (mayorista_values[-1] if mayorista_values else 0), 2)
    spread_cambiario = round(
        ((current_official - current_mayorista) / current_mayorista) * 100,
        2,
    ) if current_official and current_mayorista else 0

    official_base_7d = oficial_values[-8] if len(oficial_values) >= 8 else (oficial_values[0] if oficial_values else 0)
    official_base_30d = oficial_values[0] if oficial_values else 0
    mayorista_base_7d = mayorista_values[-8] if len(mayorista_values) >= 8 else (mayorista_values[0] if mayorista_values else 0)
    mayorista_base_30d = mayorista_values[0] if mayorista_values else 0

    ipc_variacion_rows = ipc_variacion.get("data", [])
    inflacion_mensual = inflacion.get("inflacion_mensual", {}).get("valor")
    if inflacion_mensual is None and ipc_variacion_rows:
        inflacion_mensual = (_extract_first_numeric_value(ipc_variacion_rows[-1]) or 0) * 100

    inflacion_interanual = inflacion.get("inflacion_interanual", {}).get("valor")
    inflacion_mensual_series = []
    for row in ipc_variacion_rows:
        fecha = row.get("fecha")
        valor = _extract_first_numeric_value(row)
        if not fecha or valor is None:
            continue
        inflacion_mensual_series.append(
            {
                "fecha": fecha,
                "inflacion_mensual": round(valor * 100, 2),
            }
        )

    inflacion_3m = _avg([item["inflacion_mensual"] for item in inflacion_mensual_series[-3:]])
    inflacion_delta_vs_3m = round((inflacion_mensual or 0) - inflacion_3m, 2)

    tasa_serie = [
        {
            "fecha": item.get("fecha"),
            "valor": round(item.get("valor") or 0, 2),
        }
        for item in tasas.get("tasa_politica_monetaria", {}).get("serie", [])
        if item.get("fecha")
    ]
    tasa_politica = round(
        tasas.get("tasa_politica_monetaria", {}).get("valor") or (tasa_serie[-1]["valor"] if tasa_serie else 0),
        2,
    )
    tasa_real = round(tasa_politica - (inflacion_interanual or 0), 2)
    costo_financiero_90d_pct = round(tasa_politica * (90 / 365), 2)

    ventas_rows = ventas_super.get("data", [])
    activity_series = []
    ventas_values = []
    for row in ventas_rows:
        fecha = row.get("fecha")
        valor = _extract_first_numeric_value(row)
        if not fecha or valor is None:
            continue
        ventas_values.append(valor)
        activity_series.append(
            {
                "fecha": fecha,
                "ventas_supermercados": round(valor, 2),
            }
        )

    actividad_proxi_var_pct = 0.0
    if len(ventas_values) >= 13:
        actividad_proxi_var_pct = _safe_pct(ventas_values[-1], ventas_values[-13], 0)
    elif len(ventas_values) >= 2:
        actividad_proxi_var_pct = _safe_pct(ventas_values[-1], ventas_values[-2], 0)

    recommendation_tag, recommendation_severity, recommendation_text = _macro_recommendation_tone(
        tasa_real,
        inflacion_delta_vs_3m,
        _safe_pct(current_official, official_base_30d, 0),
        inflacion_mensual or 0,
    )

    capital_reference_rows = []
    for capital in (50_000_000, 100_000_000, 250_000_000):
        capital_reference_rows.append(
            {
                "escenario": f"Capital de trabajo ${capital / 1_000_000:.0f}M",
                "capital_trabajo_ars": capital,
                "costo_financiero_90d_ars": round(capital * (costo_financiero_90d_pct / 100), 2),
                "costo_financiero_90d_pct": costo_financiero_90d_pct,
            }
        )

    alerts = []
    if tasa_real > 6:
        alerts.append(
            {
                "id": "macro-fin-1",
                "titulo": "Costo financiero real elevado",
                "descripcion": (
                    f"La tasa de referencia ({tasa_politica:.1f}%) supera a la inflación interanual "
                    f"por {tasa_real:.1f} p.p. y encarece capital de trabajo."
                ),
                "severidad": "critical",
                "recommendation": "Acortar plazos de financiación y priorizar cobros o ventas con mayor liquidez.",
                "impacto": "Presiona el costo financiero de campaña.",
            }
        )
    elif tasa_real > 0:
        alerts.append(
            {
                "id": "macro-fin-2",
                "titulo": "Financiamiento todavía caro en términos reales",
                "descripcion": (
                    f"La tasa real estimada sigue positiva ({tasa_real:.1f} p.p.), "
                    "por lo que conviene revisar deuda operativa y anticipar compras críticas."
                ),
                "severidad": "warning",
                "recommendation": "Revisar estructura de capital de trabajo antes de financiar insumos.",
                "impacto": "Reduce flexibilidad financiera.",
            }
        )
    else:
        alerts.append(
            {
                "id": "macro-fin-3",
                "titulo": "Tasa real negativa mejora el carry operativo",
                "descripcion": (
                    f"La tasa real estimada es {tasa_real:.1f} p.p., lo que da más aire "
                    "para financiar necesidades puntuales en pesos."
                ),
                "severidad": "success",
                "recommendation": "Aprovechar para ordenar compras y presupuesto de campaña sin sobrefinanciarse.",
                "impacto": "Mejora previsibilidad del capital de trabajo.",
            }
        )

    if current_official and inflacion_mensual and _safe_pct(current_official, official_base_30d, 0) < inflacion_mensual:
        alerts.append(
            {
                "id": "macro-fx-1",
                "titulo": "El tipo de cambio corre por debajo de la inflación mensual",
                "descripcion": (
                    f"El oficial varía {_safe_pct(current_official, official_base_30d, 0):.1f}% en 30 días "
                    f"vs una inflación mensual de {inflacion_mensual:.1f}%."
                ),
                "severidad": "warning",
                "recommendation": "Revisar cobertura de costos dolarizados y supuestos de margen en pesos.",
                "impacto": "Puede erosionar margen real si los costos locales siguen subiendo.",
            }
        )

    if inflacion_delta_vs_3m < -0.5:
        alerts.append(
            {
                "id": "macro-inf-1",
                "titulo": "Desaceleración inflacionaria reciente",
                "descripcion": (
                    f"La inflación mensual ({inflacion_mensual or 0:.1f}%) se ubica "
                    f"{abs(inflacion_delta_vs_3m):.1f} p.p. por debajo del promedio de 3 meses."
                ),
                "severidad": "success",
                "recommendation": "Usar la mejora de previsibilidad para recalibrar presupuesto y política comercial.",
                "impacto": "Mejora la lectura de costos de campaña.",
            }
        )

    if actividad_proxi_var_pct < -5:
        alerts.append(
            {
                "id": "macro-act-1",
                "titulo": "La actividad proxy muestra desaceleración",
                "descripcion": (
                    f"El indicador de ventas se retrae {abs(actividad_proxi_var_pct):.1f}% en la comparación de referencia."
                ),
                "severidad": "warning",
                "recommendation": "Conservar liquidez y revisar timing de inversiones no críticas.",
                "impacto": "Aumenta prudencia financiera y comercial.",
            }
        )

    now_iso = datetime.utcnow().isoformat()
    insights = [
        {
            "id": "macro-insight-rate",
            "titulo": (
                "El costo financiero sigue elevado en términos reales"
                if tasa_real > 0
                else "La tasa real negativa mejora el carry operativo"
            ),
            "descripcion": (
                f"Tasa política {tasa_politica:.1f}% vs inflación interanual {inflacion_interanual or 0:.1f}% "
                f"deja una tasa real estimada de {tasa_real:.1f} p.p."
            ),
            "severidad": "critical" if tasa_real > 6 else "warning" if tasa_real > 0 else "success",
            "tab": "macro",
            "timestamp": now_iso,
        },
        {
            "id": "macro-insight-fx",
            "titulo": (
                "El tipo de cambio se mantiene estable vs la inflación"
                if _safe_pct(current_official, official_base_30d, 0) <= (inflacion_mensual or 0) + 0.5
                else "El tipo de cambio acelera por encima del costo local"
            ),
            "descripcion": (
                f"El oficial se mueve {_safe_pct(current_official, official_base_30d, 0):.1f}% en 30 días "
                f"con un spread de {spread_cambiario:.1f}% frente al mayorista."
            ),
            "severidad": "info" if spread_cambiario < 3 else "warning",
            "tab": "macro",
            "timestamp": now_iso,
        },
        {
            "id": "macro-insight-inf",
            "titulo": (
                "La desaceleración inflacionaria mejora previsibilidad"
                if inflacion_delta_vs_3m < 0
                else "La inflación vuelve a presionar el presupuesto"
            ),
            "descripcion": (
                f"La inflación mensual es {inflacion_mensual or 0:.1f}% vs promedio 3M de {inflacion_3m:.1f}%."
            ),
            "severidad": "success" if inflacion_delta_vs_3m < -0.5 else "warning" if inflacion_delta_vs_3m > 0.5 else "info",
            "tab": "macro",
            "timestamp": now_iso,
        },
    ]

    recommendations = [
        {
            "titulo": "Revisar financiamiento de campaña",
            "descripcion": "Calcular el costo efectivo a 90 días antes de tomar deuda corta para capital de trabajo.",
            "owner": "Finanzas",
            "impacto": f"{costo_financiero_90d_pct:.1f}% sobre capital financiado",
            "severity": "critical" if tasa_real > 6 else "warning",
        },
        {
            "titulo": "Recalibrar supuestos de presupuesto",
            "descripcion": "Actualizar costos en pesos y referencia cambiaria para no subestimar presión sobre margen.",
            "owner": "Planeamiento",
            "impacto": "Mejora lectura de margen y cash flow",
            "severity": "success" if inflacion_delta_vs_3m < -0.5 else "warning",
        },
        {
            "titulo": "Definir cobertura de costos dolarizados",
            "descripcion": "Validar exposición de insumos, fletes y servicios atados a dólar frente a un tipo de cambio más estable.",
            "owner": "Gerencia",
            "impacto": "Protege margen operativo",
            "severity": "warning",
        },
    ]

    return {
        "summary": {
            "tipo_cambio_oficial": current_official,
            "tipo_cambio_mayorista": current_mayorista,
            "spread_cambiario_pct": spread_cambiario,
            "tc_oficial_var_7d_pct": _safe_pct(current_official, official_base_7d, 0),
            "tc_oficial_var_30d_pct": _safe_pct(current_official, official_base_30d, 0),
            "tc_mayorista_var_7d_pct": _safe_pct(current_mayorista, mayorista_base_7d, 0),
            "tc_mayorista_var_30d_pct": _safe_pct(current_mayorista, mayorista_base_30d, 0),
            "tc_oficial_min_30d": round(min(oficial_values), 2) if oficial_values else 0,
            "tc_oficial_max_30d": round(max(oficial_values), 2) if oficial_values else 0,
            "tc_mayorista_min_30d": round(min(mayorista_values), 2) if mayorista_values else 0,
            "tc_mayorista_max_30d": round(max(mayorista_values), 2) if mayorista_values else 0,
            "inflacion_mensual": round(inflacion_mensual or 0, 2),
            "inflacion_interanual": round(inflacion_interanual or 0, 2),
            "inflacion_promedio_3m": inflacion_3m,
            "inflacion_delta_vs_3m": inflacion_delta_vs_3m,
            "tasa_politica_monetaria": tasa_politica,
            "tasa_real_pct": tasa_real,
            "costo_financiero_90d_pct": costo_financiero_90d_pct,
            "actividad_proxi_var_pct": round(actividad_proxi_var_pct, 2),
            "reservas_internacionales": round(
                bcra.get("reservas_internacionales", {}).get("valor") or 0,
                2,
            ),
            "recommendation": recommendation_text,
            "recommendation_tag": recommendation_tag,
            "recommendation_severity": recommendation_severity,
        },
        "series": {
            "fx": fx_series,
            "inflacion": inflacion_mensual_series,
            "tasa": tasa_serie,
            "actividad": activity_series,
            "impacto_capital_trabajo": capital_reference_rows,
        },
        "alerts": alerts,
        "recommendations": recommendations,
        "insights": insights,
        "tipo_cambio_oficial": current_official,
        "tipo_cambio_mayorista": current_mayorista,
        "tipo_cambio_historico": [
            {
                "fecha": item["fecha"],
                "valor": item["tipo_cambio_oficial"] or 0,
            }
            for item in fx_series
            if item.get("fecha")
        ],
        "inflacion_mensual": round(inflacion_mensual or 0, 2),
        "inflacion_interanual": round(inflacion_interanual or 0, 2),
        "tasa_politica_monetaria": tasa_politica,
        "reservas_internacionales": round(
            bcra.get("reservas_internacionales", {}).get("valor") or 0,
            2,
        ),
        "fuente": macro.get("metadata", {}).get("source_name", "BCRA"),
        "ultima_actualizacion": macro.get("metadata", {}).get(
            "fetched_at",
            datetime.now().isoformat(),
        ),
    }


async def _build_climate_operation_panel() -> dict:
    clima = await service.get_clima_resumen()
    alertas_payload = await service.get_alertas_climaticas()
    alertas = alertas_payload.get("data", [])

    establecimientos_raw = clima.get("data", {}).get("establecimientos", [])
    establecimientos = []

    selected = next(
        (
            item
            for item in establecimientos_raw
            if item.get("establecimiento") == "El Progreso"
            and item.get("metadata", {}).get("status") == "ok"
        ),
        next(
            (
                item
                for item in establecimientos_raw
                if item.get("metadata", {}).get("status") == "ok"
            ),
            establecimientos_raw[0] if establecimientos_raw else {},
        ),
    )

    for establecimiento in establecimientos_raw:
        detalle = establecimiento.get("pronostico_7d", {}).get("detalle", {})
        daily = detalle.get("daily", {})
        hourly = detalle.get("hourly", {})
        temperatura = (hourly.get("temperature_2m") or [None])[0]
        humedad = (hourly.get("relativehumidity_2m") or [None])[0]
        precipitacion = (hourly.get("precipitation") or [None])[0]
        viento = (daily.get("windspeed_10m_max") or [None])[0]
        codigo = (daily.get("weathercode") or [0])[0]
        forecast_resumen = establecimiento.get("pronostico_7d", {}).get("resumen", [])
        forecast_7d_mm = round(
            sum(row.get("precipitacion_mm") or 0 for row in forecast_resumen),
            1,
        )
        forecast_72h_mm = round(
            sum((forecast_resumen[index].get("precipitacion_mm") or 0) for index in range(min(3, len(forecast_resumen)))),
            1,
        )
        historico_stats = establecimiento.get("historico_30d", {}).get("estadisticas", {})
        lluvia_30d = round(historico_stats.get("precipitacion_total_30d_mm") or 0, 1)
        humidity_value = round(humedad, 0) if humedad is not None else None
        wind_value = round(viento, 1) if viento is not None else None
        ventana_label, ventana_severity, _ = _climate_window_assessment(
            round(sum((forecast_resumen[index].get("precipitacion_mm") or 0) for index in range(min(2, len(forecast_resumen)))), 1),
            humidity_value or 0,
            wind_value or 0,
        )
        riesgo_label, riesgo_severity, riesgo_detail = _climate_risk_assessment(
            forecast_72h_mm,
            lluvia_30d,
            humidity_value or 0,
        )

        alertas_establecimiento = [
            alerta.get("titulo")
            for alerta in alertas
            if alerta.get("establecimiento") == establecimiento.get("establecimiento")
        ]

        establecimientos.append(
            {
                "nombre": establecimiento.get("establecimiento"),
                "provincia": establecimiento.get("provincia"),
                "temperatura": round(temperatura, 1) if temperatura is not None else None,
                "sensacion_termica": round(temperatura, 1) if temperatura is not None else None,
                "humedad": humidity_value,
                "precipitacion_mm": round(precipitacion, 1) if precipitacion is not None else None,
                "condicion": _weather_label(codigo),
                "condicion_codigo": codigo,
                "viento_kmh": wind_value,
                "alertas": alertas_establecimiento,
                "lluvia_30d_mm": lluvia_30d,
                "lluvia_7d_forecast_mm": forecast_7d_mm,
                "riesgo_operativo": riesgo_label,
                "riesgo_operativo_detalle": riesgo_detail,
                "ventana_operativa": ventana_label,
                "status": establecimiento.get("metadata", {}).get("status", "ok"),
            }
        )

    selected_daily = selected.get("pronostico_7d", {}).get("detalle", {}).get("daily", {})
    selected_hourly = selected.get("pronostico_7d", {}).get("detalle", {}).get("hourly", {})
    selected_resumen = selected.get("pronostico_7d", {}).get("resumen", [])
    hourly_times = selected_hourly.get("time", []) or []
    hourly_humidity = selected_hourly.get("relativehumidity_2m", []) or []

    humidity_by_day: dict[str, list[float]] = {}
    for index, timestamp in enumerate(hourly_times):
        date_key = (timestamp or "").split("T")[0]
        if not date_key:
            continue
        value = hourly_humidity[index] if index < len(hourly_humidity) else None
        if value is None:
            continue
        humidity_by_day.setdefault(date_key, []).append(value)

    selected_codes = selected_daily.get("weathercode", []) or []
    selected_wind = selected_daily.get("windspeed_10m_max", []) or []
    pronostico_7d = []
    precip_accum = 0.0
    for index, row in enumerate(selected_resumen):
        fecha = row.get("fecha")
        precip = round(row.get("precipitacion_mm") or 0, 1)
        precip_accum += precip
        humidity_avg = _avg(humidity_by_day.get(fecha, []))
        wind = round(selected_wind[index], 1) if index < len(selected_wind) and selected_wind[index] is not None else 0
        window_label, window_severity, _ = _climate_window_assessment(
            precip,
            humidity_avg,
            wind,
        )
        risk_label, risk_severity, risk_detail = _climate_risk_assessment(
            precip,
            round(selected.get("historico_30d", {}).get("estadisticas", {}).get("precipitacion_total_30d_mm") or 0, 1),
            humidity_avg,
        )
        pronostico_7d.append(
            {
                "fecha": fecha,
                "temp_max": round(row.get("temp_max_c") or 0, 1),
                "temp_min": round(row.get("temp_min_c") or 0, 1),
                "temp_media": round(((row.get("temp_max_c") or 0) + (row.get("temp_min_c") or 0)) / 2, 1),
                "precipitacion_mm": precip,
                "precipitacion_acumulada_mm": round(precip_accum, 1),
                "humedad_promedio": round(humidity_avg, 0),
                "condicion": _weather_label(
                    selected_codes[index] if index < len(selected_codes) else 0
                ),
                "condicion_codigo": selected_codes[index] if index < len(selected_codes) else 0,
                "viento_kmh": wind,
                "ventana_operativa": window_label,
                "ventana_severidad": window_severity,
                "riesgo_operativo": risk_label,
                "riesgo_detalle": risk_detail,
            }
        )

    historico_diario = selected.get("historico_30d", {}).get("serie_diaria", {})
    historico_30d = []
    for index, fecha in enumerate(historico_diario.get("fechas", []) or []):
        precip = historico_diario.get("precipitacion_mm", [])[index] if index < len(historico_diario.get("precipitacion_mm", [])) else None
        temp_max = historico_diario.get("temp_max_c", [])[index] if index < len(historico_diario.get("temp_max_c", [])) else None
        temp_min = historico_diario.get("temp_min_c", [])[index] if index < len(historico_diario.get("temp_min_c", [])) else None
        historico_30d.append(
            {
                "fecha": fecha,
                "precipitacion_mm": round(precip or 0, 1),
                "temp_max": round(temp_max or 0, 1),
                "temp_min": round(temp_min or 0, 1),
                "temp_media": round((((temp_max or 0) + (temp_min or 0)) / 2), 1),
            }
        )

    lluvia_72h = round(sum(item.get("precipitacion_mm") or 0 for item in pronostico_7d[:3]), 1)
    lluvia_7d = round(sum(item.get("precipitacion_mm") or 0 for item in pronostico_7d), 1)
    lluvia_30d = round(selected.get("historico_30d", {}).get("estadisticas", {}).get("precipitacion_total_30d_mm") or 0, 1)
    humedad_promedio = _avg([item.get("humedad") or 0 for item in establecimientos if item.get("humedad") is not None])
    temperatura_promedio_7d = _avg([item.get("temp_media") or 0 for item in pronostico_7d])
    lluvia_normal_7d = round((lluvia_30d / 30) * 7, 1) if lluvia_30d else 0
    anomalia_lluvia_pct = _safe_pct(lluvia_7d, lluvia_normal_7d, 0) if lluvia_normal_7d else 0
    ventana_label, ventana_severity, ventana_detail = _climate_window_assessment(
        round(sum(item.get("precipitacion_mm") or 0 for item in pronostico_7d[:2]), 1),
        humedad_promedio,
        _avg([item.get("viento_kmh") or 0 for item in pronostico_7d[:2]]),
    )
    riesgo_label, riesgo_severity, riesgo_detail = _climate_risk_assessment(
        lluvia_72h,
        lluvia_30d,
        humedad_promedio,
    )

    derived_alerts = []
    if lluvia_72h >= 30:
        derived_alerts.append(
            {
                "tipo": "OPERATIVO",
                "mensaje": f"Se esperan {lluvia_72h:.1f} mm en 72 hs sobre {selected.get('establecimiento')}: alto riesgo de atraso operativo.",
                "severidad": "critical",
            }
        )
    if humedad_promedio >= 85:
        derived_alerts.append(
            {
                "tipo": "HUMEDAD",
                "mensaje": "La humedad ambiente sigue alta y puede complicar pulverización o tránsito en lotes pesados.",
                "severidad": "warning",
            }
        )
    if lluvia_30d <= 20 and lluvia_7d <= 10:
        derived_alerts.append(
            {
                "tipo": "AGRONOMÍA",
                "mensaje": "La lluvia acumulada sigue baja y eleva el riesgo de estrés hídrico en lotes más restrictivos.",
                "severidad": "warning",
            }
        )

    alertas_activas = [
        {
            "tipo": alerta.get("tipo"),
            "mensaje": alerta.get("descripcion"),
            "severidad": _map_external_severity(alerta.get("severidad", "")),
        }
        for alerta in alertas
    ] + derived_alerts

    now_iso = datetime.utcnow().isoformat()
    insights = []
    if lluvia_30d <= 20 and lluvia_7d <= 10:
        insights.append(
            {
                "id": "clima-insight-hidrico",
                "titulo": "Lluvias insuficientes elevan el riesgo agronómico",
                "descripcion": (
                    f"El establecimiento de referencia acumula {lluvia_30d:.1f} mm en 30 días "
                    f"y sólo {lluvia_7d:.1f} mm proyectados en 7 días."
                ),
                "severidad": "warning",
                "tab": "clima",
                "timestamp": now_iso,
            }
        )
    if ventana_label == "favorable":
        insights.append(
            {
                "id": "clima-insight-ventana",
                "titulo": "Ventana favorable para labores en las próximas 48 hs",
                "descripcion": ventana_detail,
                "severidad": "success",
                "tab": "clima",
                "timestamp": now_iso,
            }
        )
    else:
        insights.append(
            {
                "id": "clima-insight-ventana-mixta",
                "titulo": "La ventana operativa requiere priorización fina",
                "descripcion": ventana_detail,
                "severidad": "warning" if ventana_severity == "warning" else "critical",
                "tab": "clima",
                "timestamp": now_iso,
            }
        )

    insights.append(
        {
            "id": "clima-insight-riesgo",
            "titulo": (
                "Condiciones climáticas favorables"
                if riesgo_severity == "success"
                else "El clima complica la ejecución"
            ),
            "descripcion": riesgo_detail,
            "severidad": riesgo_severity,
            "tab": "clima",
            "timestamp": now_iso,
        }
    )

    recommendations = [
        {
            "titulo": "Priorizar labores por ventana operativa",
            "descripcion": ventana_detail,
            "owner": "Operaciones",
            "impacto": "Protege cumplimiento y transitabilidad",
            "severity": "success" if ventana_severity == "success" else "warning",
        },
        {
            "titulo": "Monitorear lotes con mayor sensibilidad hídrica",
            "descripcion": riesgo_detail,
            "owner": "Agronomía",
            "impacto": "Reduce pérdida potencial de rinde",
            "severity": "critical" if riesgo_severity == "critical" else "warning",
        },
        {
            "titulo": "Alinear equipos y pulverización con pronóstico",
            "descripcion": "Revisar humedad, lluvia y viento antes de definir el frente operativo del próximo bloque de trabajo.",
            "owner": "Jefe de campo",
            "impacto": "Evita reprocesos y paradas improductivas",
            "severity": "warning",
        },
    ]

    return {
        "summary": {
            "lluvia_72h_mm": lluvia_72h,
            "lluvia_7d_mm": lluvia_7d,
            "lluvia_30d_mm": lluvia_30d,
            "lluvia_normal_7d_mm": lluvia_normal_7d,
            "anomalia_lluvia_7d_pct": anomalia_lluvia_pct,
            "humedad_promedio_pct": round(humedad_promedio, 1),
            "temperatura_promedio_7d_c": round(temperatura_promedio_7d, 1),
            "ventana_operativa": ventana_label,
            "ventana_detalle": ventana_detail,
            "riesgo_operativo": riesgo_label,
            "riesgo_operativo_detalle": riesgo_detail,
            "establecimientos_con_alerta": len(
                [
                    item
                    for item in establecimientos
                    if item.get("alertas")
                    or item.get("riesgo_operativo") != "neutral"
                ]
            ),
            "establecimiento_referencia": selected.get("establecimiento"),
            "recommendation": ventana_detail if ventana_severity != "success" else riesgo_detail,
            "recommendation_severity": ventana_severity if ventana_severity != "success" else riesgo_severity,
        },
        "series": {
            "forecast_daily": pronostico_7d,
            "historico_30d": historico_30d,
            "establecimientos": establecimientos,
        },
        "alerts": alertas_activas,
        "recommendations": recommendations,
        "insights": insights,
        "establecimientos": establecimientos,
        "pronostico_7d": pronostico_7d,
        "historico_30d": historico_30d,
        "alertas_activas": alertas_activas,
        "selected_establecimiento": {
            "nombre": selected.get("establecimiento"),
            "provincia": selected.get("provincia"),
        },
        "fuente": clima.get("metadata", {}).get("source_name", "Open-Meteo"),
        "ultima_actualizacion": clima.get("metadata", {}).get(
            "fetched_at",
            datetime.now().isoformat(),
        ),
    }


@router.get("/contexto/macro")
async def contexto_macro():
    return await _build_macro_decision_panel()


@router.get("/contexto/commodities")
async def contexto_commodities(db: AsyncSession = Depends(get_db)):
    return await _build_commodity_market_panel(db)


@router.get("/contexto/clima")
async def contexto_clima():
    return await _build_climate_operation_panel()


@router.get("/contexto/insights")
async def contexto_insights(db: AsyncSession = Depends(get_db)):
    import asyncio

    insights = await service.get_insights_macro()
    items = []
    for index, insight in enumerate(insights.get("data", []), start=1):
        tab = insight.get("modulo", "macro")
        if tab == "mercado":
            tab = "commodities"

        items.append(
            {
                "id": f"contexto-{index}",
                "titulo": insight.get("titulo"),
                "descripcion": insight.get("descripcion"),
                "severidad": _map_external_severity(insight.get("severidad", "")),
                "tab": tab,
                "timestamp": insight.get("fecha", datetime.now().isoformat()),
            }
        )

    macro_panel, commodity_panel, climate_panel = await asyncio.gather(
        _build_macro_decision_panel(),
        _build_commodity_market_panel(db),
        _build_climate_operation_panel(),
    )
    for panel in (macro_panel, commodity_panel, climate_panel):
        for insight in panel.get("insights", []):
            items.append(insight)

    return items
