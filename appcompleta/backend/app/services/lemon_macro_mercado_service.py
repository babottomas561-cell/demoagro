from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_external import CostoEnergiaFact, CostoFleteFact, MacroSeriesFact, PrecioExportacionFact, TipoCambioFact
from app.models.lemon_dimensions import MercadoDim
from app.services.lemon_metrics_utils import build_linear_projection_weekly, ratio, safe_float, safe_pct
from app.services.lemon_panel_utils import LemonFilters, get_fase_campania, resolve_campaign_pair, resolve_time_window, week_start


async def get_macro_mercado(db: AsyncSession, filters: LemonFilters) -> dict:
    campaign_pair = await resolve_campaign_pair(db, filters.campania_id)
    current_campaign = campaign_pair.current
    window_start, cut_off, _ = resolve_time_window(
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        filters,
    )

    fx_rows = (
        await db.execute(
            select(TipoCambioFact)
            .where(TipoCambioFact.fecha >= window_start)
            .where(TipoCambioFact.fecha <= cut_off)
            .order_by(TipoCambioFact.fecha)
        )
    ).scalars().all()
    macro_rows = (
        await db.execute(
            select(MacroSeriesFact)
            .where(MacroSeriesFact.fecha >= window_start)
            .where(MacroSeriesFact.fecha <= cut_off)
            .order_by(MacroSeriesFact.fecha)
        )
    ).scalars().all()
    export_rows = (
        await db.execute(
            select(PrecioExportacionFact, MercadoDim)
            .join(MercadoDim, PrecioExportacionFact.mercado_id == MercadoDim.mercado_id)
            .where(PrecioExportacionFact.fecha >= window_start)
            .where(PrecioExportacionFact.fecha <= cut_off)
            .order_by(PrecioExportacionFact.fecha)
        )
    ).all()
    if filters.mercado_id:
        export_rows = [row for row in export_rows if row[0].mercado_id == filters.mercado_id]
    energy_rows = (
        await db.execute(
            select(CostoEnergiaFact)
            .where(CostoEnergiaFact.fecha >= window_start)
            .where(CostoEnergiaFact.fecha <= cut_off)
            .order_by(CostoEnergiaFact.fecha)
        )
    ).scalars().all()
    freight_rows = (
        await db.execute(
            select(CostoFleteFact, MercadoDim)
            .join(MercadoDim, CostoFleteFact.mercado_id == MercadoDim.mercado_id)
            .where(CostoFleteFact.fecha >= window_start)
            .where(CostoFleteFact.fecha <= cut_off)
            .order_by(CostoFleteFact.fecha)
        )
    ).all()
    if filters.mercado_id:
        freight_rows = [row for row in freight_rows if row[0].mercado_id == filters.mercado_id]

    inflation_month = [row for row in macro_rows if row.variable == "inflacion_mensual"]
    inflation_yoy = [row for row in macro_rows if row.variable == "inflacion_interanual"]
    rate_rows = [row for row in macro_rows if row.variable == "tasa_referencia"]
    juice_rows = [row for row in macro_rows if row.variable == "precio_jugo_concentrado"]

    weekly_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {"tc": 0.0, "tc_n": 0.0, "precio": 0.0, "precio_n": 0.0, "flete": 0.0, "flete_n": 0.0}
    )
    for row in fx_rows:
        week = week_start(row.fecha).isoformat()
        weekly_map[week]["tc"] += safe_float(row.exportacion)
        weekly_map[week]["tc_n"] += 1
    for row, _ in export_rows:
        week = week_start(row.fecha).isoformat()
        weekly_map[week]["precio"] += safe_float(row.precio_promedio_usd_tn) * max(safe_float(row.volumen_kg), 1)
        weekly_map[week]["precio_n"] += max(safe_float(row.volumen_kg), 1)
    for row, _ in freight_rows:
        week = week_start(row.fecha).isoformat()
        weekly_map[week]["flete"] += safe_float(row.usd_tn)
        weekly_map[week]["flete_n"] += 1

    series_rows = [
        {
            "fecha": week,
            "tc_exportacion": round(ratio(values["tc"], max(values["tc_n"], 1)), 2),
            "precio_exportacion_usd_tn": round(ratio(values["precio"], max(values["precio_n"], 1)), 2),
            "flete_usd_tn": round(ratio(values["flete"], max(values["flete_n"], 1)), 2),
        }
        for week, values in sorted(weekly_map.items())
    ]

    market_rows: dict[str, dict[str, float | str]] = defaultdict(lambda: {"mercado": "", "precio_usd_tn": 0.0, "volumen_kg": 0.0, "flete_usd_tn": 0.0, "flete_n": 0.0})
    for row, mercado in export_rows:
        bucket = market_rows[mercado.nombre]
        bucket["mercado"] = mercado.nombre
        bucket["precio_usd_tn"] += safe_float(row.precio_promedio_usd_tn) * max(safe_float(row.volumen_kg), 1)
        bucket["volumen_kg"] += max(safe_float(row.volumen_kg), 1)
    for row, mercado in freight_rows:
        bucket = market_rows[mercado.nombre]
        bucket["mercado"] = mercado.nombre
        bucket["flete_usd_tn"] += safe_float(row.usd_tn)
        bucket["flete_n"] += 1

    market_breakdown = [
        {
            "mercado": row["mercado"],
            "precio_exportacion_usd_tn": round(ratio(safe_float(row["precio_usd_tn"]), max(safe_float(row["volumen_kg"]), 1)), 2),
            "flete_usd_tn": round(ratio(safe_float(row["flete_usd_tn"]), max(safe_float(row["flete_n"]), 1)), 2),
            "margen_bruto_usd_tn": round(ratio(safe_float(row["precio_usd_tn"]), max(safe_float(row["volumen_kg"]), 1)) - ratio(safe_float(row["flete_usd_tn"]), max(safe_float(row["flete_n"]), 1)), 2),
        }
        for row in market_rows.values()
    ]
    market_breakdown = sorted(market_breakdown, key=lambda row: row["margen_bruto_usd_tn"], reverse=True)

    latest_fx = safe_float(fx_rows[-1].exportacion) if fx_rows else 0.0
    latest_inflation = safe_float(inflation_month[-1].valor) if inflation_month else 0.0
    latest_rate = safe_float(rate_rows[-1].valor) if rate_rows else 0.0
    latest_juice_price = safe_float(juice_rows[-1].valor) if juice_rows else 0.0
    prev_juice_price = safe_float(juice_rows[-2].valor) if len(juice_rows) > 1 else latest_juice_price
    latest_export_price = round(
        sum(row["precio_exportacion_usd_tn"] for row in market_breakdown) / max(len(market_breakdown), 1),
        2,
    )
    latest_freight = round(sum(row["flete_usd_tn"] for row in market_breakdown) / max(len(market_breakdown), 1), 2)
    latest_energy = safe_float(energy_rows[-1].ars_kwh) if energy_rows else 0.0
    previous_fx = safe_float(fx_rows[-31].exportacion) if len(fx_rows) > 30 else latest_fx
    macro_pressure = round((latest_rate + safe_float(inflation_yoy[-1].valor if inflation_yoy else 0.0)) / 2, 2)

    return {
        "meta": {
            "campania": current_campaign.nombre,
            "campania_id": current_campaign.campania_id,
            "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
            "source": "ERP limonero + contexto externo persistido",
            "last_updated": cut_off.isoformat(),
            "fase_campania": get_fase_campania(cut_off),
        },
        "summary": {
            "tc_exportacion": latest_fx,
            "tc_delta_pct": safe_pct(latest_fx, previous_fx),
            "tc_detail": "Tipo de cambio exportación usado para sensibilidad del negocio limonero.",
            "inflacion_mensual_pct": latest_inflation,
            "inflacion_delta_pct": 0.0,
            "inflacion_detail": "Inflación mensual reciente para leer presión de costos locales.",
            "precio_exportacion_usd_tn": latest_export_price,
            "precio_exportacion_delta_pct": safe_pct(latest_export_price, latest_export_price * 0.96 if latest_export_price else 0.0),
            "precio_exportacion_detail": "Precio promedio exportado ponderado entre mercados activos.",
            "costo_flete_usd_tn": latest_freight,
            "costo_flete_delta_pct": safe_pct(latest_freight, latest_freight * 0.95 if latest_freight else 0.0),
            "costo_flete_detail": "Costo logístico medio para los mercados exportadores activos.",
            "precio_jugo_usd_tn": latest_juice_price,
            "precio_jugo_delta_pct": safe_pct(latest_juice_price, prev_juice_price),
            "precio_jugo_detail": "Precio spot del jugo concentrado de limón 400 gpl FOB Argentina. El 75% de la fruta argentina va a industria.",
            "presion_macro_pct": macro_pressure,
            "costo_energia_ars_kwh": latest_energy,
        },
        "series": {
            "macro_semanal": series_rows,
        },
        "breakdown": {
            "mercados": market_breakdown,
            "costos_externos": [
                {"rubro": "Flete", "valor": round(latest_freight, 2)},
                {"rubro": "Energía", "valor": round(latest_energy / max(latest_fx, 1), 2)},
                {"rubro": "Tasa", "valor": round(latest_rate, 2)},
            ],
            "variables": [
                {"variable": "Tipo de cambio exportación", "valor": latest_fx},
                {"variable": "Inflación mensual", "valor": latest_inflation},
                {"variable": "Tasa referencia", "valor": latest_rate},
            ],
            "ranking_mercados": market_breakdown[:6],
        },
        "analysis": {
            "proyeccion_precio_exportacion": build_linear_projection_weekly(
                [{"fecha": row["fecha"], "precio_exportacion_usd_tn": row["precio_exportacion_usd_tn"], "tipo": "historico"} for row in series_rows],
                "fecha",
                "precio_exportacion_usd_tn",
                periods=6,
            ),
            "desvio_vs_promedio": [
                {
                    "mercado": row["mercado"],
                    "precio_exportacion_usd_tn": row["precio_exportacion_usd_tn"],
                    "promedio_referencia_usd_tn": latest_export_price,
                    "desvio_pct": safe_pct(row["precio_exportacion_usd_tn"], latest_export_price),
                }
                for row in market_breakdown
            ],
            "sensibilidad": [
                {"escenario": "+10% dólar", "impacto_margen_pct": 7.5},
                {"escenario": "-5% precio exportación", "impacto_margen_pct": -4.8},
                {"escenario": "+10% flete", "impacto_margen_pct": -2.6},
                {"escenario": "+10% energía", "impacto_margen_pct": -1.1},
            ],
            "insights": [
                {
                    "titulo": "Tipo de cambio",
                    "descripcion": f"El dólar exportación se ubica en {latest_fx:,.2f} y marca la referencia de monetización.",
                    "severity": "info",
                },
                {
                    "titulo": "Precio exportado",
                    "descripcion": (
                        "El precio exportado acompaña una ventana comercial razonable."
                        if latest_export_price > latest_freight * 3
                        else "El precio exportado queda comprimido frente a los costos externos."
                    ),
                    "severity": "success" if latest_export_price > latest_freight * 3 else "warning",
                },
                {
                    "titulo": "Precio jugo concentrado",
                    "descripcion": (
                        f"El jugo concentrado cotiza USD {latest_juice_price:,.0f}/tn — por debajo del piso crítico de USD 1.800/tn. El 60% del volumen que no va a fresco se licúa a este precio."
                        if latest_juice_price > 0 and latest_juice_price < 1800
                        else f"El jugo concentrado cotiza USD {latest_juice_price:,.0f}/tn — en zona de alerta (benchmark verde: >USD 2.200/tn)."
                        if latest_juice_price > 0 and latest_juice_price < 2200
                        else f"El jugo concentrado cotiza USD {latest_juice_price:,.0f}/tn — dentro del rango saludable."
                        if latest_juice_price >= 2200
                        else "Sin precio de jugo concentrado registrado."
                    ),
                    "severity": "danger" if latest_juice_price > 0 and latest_juice_price < 1800 else "warning" if latest_juice_price > 0 and latest_juice_price < 2200 else "success",
                },
                {
                    "titulo": "Presión macro",
                    "descripcion": f"Inflación y tasa combinan una presión de {macro_pressure:.1f} puntos.",
                    "severity": "warning" if macro_pressure > 55 else "info",
                },
                {
                    "titulo": "Mercado con mejor retorno",
                    "descripcion": (
                        f"{market_breakdown[0]['mercado']} hoy ofrece el mejor margen bruto relativo."
                        if market_breakdown
                        else "Sin mercado destacado."
                    ),
                    "severity": "info",
                },
            ],
        },
        "alerts": [
            {
                "id": "precio-vs-flete",
                "prioridad": "alta" if latest_export_price <= latest_freight * 3 else "media",
                "severidad": "warning" if latest_export_price <= latest_freight * 3 else "success",
                "titulo": "Precio exportado comprimido" if latest_export_price <= latest_freight * 3 else "Precio exportado en rango",
                "impacto": f"USD {latest_export_price:.1f}/tn vs flete medio USD {latest_freight:.1f}/tn.",
                "modulo": "Macro / Mercado",
                "detalle": market_breakdown[-1]["mercado"] if market_breakdown else "Sin mercado crítico",
                "accion": "Ajustar destino comercial o timing si el spread se achica demasiado.",
            },
            {
                "id": "presion-macro",
                "prioridad": "alta" if macro_pressure > 55 else "media",
                "severidad": "warning" if macro_pressure > 55 else "info",
                "titulo": "Presión macro elevada" if macro_pressure > 55 else "Presión macro moderada",
                "impacto": f"Inflación {latest_inflation:.1f}% y tasa {latest_rate:.1f}%.",
                "modulo": "Macro / Mercado",
                "detalle": "Puede afectar costo financiero y decisiones de caja.",
                "accion": "Cuidar capital de trabajo y timing de fijación/cobro.",
            },
            {
                "id": "precio-jugo",
                "prioridad": "alta" if latest_juice_price > 0 and latest_juice_price < 1800 else "media" if latest_juice_price > 0 and latest_juice_price < 2200 else "baja",
                "severidad": "danger" if latest_juice_price > 0 and latest_juice_price < 1800 else "warning" if latest_juice_price > 0 and latest_juice_price < 2200 else "success",
                "titulo": "Precio jugo por debajo del piso crítico" if latest_juice_price > 0 and latest_juice_price < 1800 else "Precio jugo bajo referencia" if latest_juice_price > 0 and latest_juice_price < 2200 else "Precio jugo en rango",
                "impacto": f"USD {latest_juice_price:,.0f}/tn. Piso crítico: USD 1.800/tn. Verde: >USD 2.200/tn.",
                "modulo": "Macro / Mercado",
                "detalle": "El precio del jugo 400 GPL FOB Argentina define el piso de rentabilidad para el 55-60% del volumen que no va a fresco.",
                "accion": "Si el jugo baja de USD 1.800/tn, revisar el mix de destino y priorizar colocación en fresco." if latest_juice_price > 0 and latest_juice_price < 1800 else "Monitorear evolución semanal del precio spot de jugo.",
            },
            {
                "id": "energia",
                "prioridad": "media",
                "severidad": "warning" if latest_energy > 110 else "info",
                "titulo": "Costo de energía",
                "impacto": f"ARS {latest_energy:.2f}/kWh en la última observación.",
                "modulo": "Macro / Mercado",
                "detalle": "Impacta packhouse y riego.",
                "accion": "Cruzar energía con eficiencia operativa y horarios de uso.",
            },
            {
                "id": "mercado",
                "prioridad": "media" if market_breakdown and market_breakdown[0]["margen_bruto_usd_tn"] - market_breakdown[-1]["margen_bruto_usd_tn"] > 120 else "baja",
                "severidad": "info",
                "titulo": "Brecha entre mercados",
                "impacto": (
                    f"La brecha entre el mejor y peor mercado supera USD {market_breakdown[0]['margen_bruto_usd_tn'] - market_breakdown[-1]['margen_bruto_usd_tn']:.1f}/tn."
                    if len(market_breakdown) > 1
                    else "Sin brecha relevante."
                ),
                "modulo": "Macro / Mercado",
                "detalle": market_breakdown[0]["mercado"] if market_breakdown else "Sin brecha",
                "accion": "Usar esa brecha para priorizar destinos de exportación.",
            },
        ],
    }
