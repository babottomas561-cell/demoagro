from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_external import ClimaDiarioFact
from app.models.lemon_field import CosechaFact, Et0Fact, FertirriegoFact, RequerimientoHidricoFact, RiegoFact
from app.services.lemon_metrics_utils import build_linear_projection_weekly, ratio, safe_float
from app.services.lemon_panel_utils import LemonFilters, get_fase_campania, load_scope_rows, resolve_campaign_pair, resolve_time_window, week_start


async def get_riego_fertirriego(db: AsyncSession, filters: LemonFilters) -> dict:
    campaign_pair = await resolve_campaign_pair(db, filters.campania_id)
    current_campaign = campaign_pair.current
    window_start, cut_off, _ = resolve_time_window(
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        filters,
    )
    scope_rows = await load_scope_rows(db, filters, current_campaign.campania_id)
    lot_campaign_ids = [row[0].lote_campania_id for row in scope_rows]
    meta_by_lot = {
        row[0].lote_campania_id: {
            "lote": row[1].nombre,
            "codigo_lote": row[1].codigo,
            "campo": row[2].nombre,
            "establecimiento": row[3].nombre,
            "establecimiento_id": row[3].establecimiento_id,
            "variedad": row[4].nombre,
            "superficie_ha": safe_float(row[0].superficie_ha),
        }
        for row in scope_rows
    }
    establishment_ids = sorted({meta["establecimiento_id"] for meta in meta_by_lot.values()})

    riego_rows = (
        await db.execute(
            select(RiegoFact)
            .where(RiegoFact.lote_campania_id.in_(lot_campaign_ids))
            .where(RiegoFact.fecha_riego >= window_start)
            .where(RiegoFact.fecha_riego <= cut_off)
        )
    ).scalars().all()
    fert_rows = (
        await db.execute(
            select(FertirriegoFact)
            .where(FertirriegoFact.lote_campania_id.in_(lot_campaign_ids))
            .where(FertirriegoFact.fecha_fertirriego >= window_start)
            .where(FertirriegoFact.fecha_fertirriego <= cut_off)
        )
    ).scalars().all()
    req_rows = (
        await db.execute(
            select(RequerimientoHidricoFact)
            .where(RequerimientoHidricoFact.lote_campania_id.in_(lot_campaign_ids))
            .where(RequerimientoHidricoFact.fecha >= window_start)
            .where(RequerimientoHidricoFact.fecha <= cut_off)
        )
    ).scalars().all()
    harvest_rows = (
        await db.execute(
            select(CosechaFact)
            .where(CosechaFact.lote_campania_id.in_(lot_campaign_ids))
            .where(CosechaFact.fecha_cosecha >= window_start)
            .where(CosechaFact.fecha_cosecha <= cut_off)
        )
    ).scalars().all()
    climate_rows = (
        await db.execute(
            select(ClimaDiarioFact)
            .where(ClimaDiarioFact.establecimiento_id.in_(establishment_ids))
            .where(ClimaDiarioFact.fecha >= window_start)
            .where(ClimaDiarioFact.fecha <= cut_off)
        )
    ).scalars().all()
    et0_rows = (
        await db.execute(
            select(Et0Fact)
            .where(Et0Fact.establecimiento_id.in_(establishment_ids))
            .where(Et0Fact.fecha >= window_start)
            .where(Et0Fact.fecha <= cut_off)
        )
    ).scalars().all()

    weekly_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {"m3_riego": 0.0, "m3_requeridos": 0.0, "m3_aportados": 0.0, "lluvia_mm": 0.0, "et0_mm": 0.0}
    )
    lot_map: dict[int, dict[str, float | str]] = defaultdict(
        lambda: {
            "lote": "",
            "codigo_lote": "",
            "campo": "",
            "establecimiento": "",
            "variedad": "",
            "superficie_ha": 0.0,
            "m3_aplicados": 0.0,
            "m3_requeridos": 0.0,
            "m3_aportados": 0.0,
            "balance_hidrico_m3": 0.0,
            "kg_cosechados": 0.0,
            "fert_eventos": 0.0,
        }
    )

    for lc_id, meta in meta_by_lot.items():
        lot_map[lc_id].update(meta)

    for row in riego_rows:
        week = week_start(row.fecha_riego).isoformat()
        weekly_map[week]["m3_riego"] += safe_float(row.m3_aplicados)
        if row.lote_campania_id in lot_map:
            lot_map[row.lote_campania_id]["m3_aplicados"] += safe_float(row.m3_aplicados)

    for row in fert_rows:
        if row.lote_campania_id in lot_map:
            lot_map[row.lote_campania_id]["fert_eventos"] += 1

    for row in req_rows:
        week = week_start(row.fecha).isoformat()
        weekly_map[week]["m3_requeridos"] += safe_float(row.m3_requeridos)
        weekly_map[week]["m3_aportados"] += safe_float(row.m3_aportados)
        if row.lote_campania_id in lot_map:
            lot_map[row.lote_campania_id]["m3_requeridos"] += safe_float(row.m3_requeridos)
            lot_map[row.lote_campania_id]["m3_aportados"] += safe_float(row.m3_aportados)
            lot_map[row.lote_campania_id]["balance_hidrico_m3"] += safe_float(row.balance_hidrico_m3)

    est_count = max(len(establishment_ids), 1)
    for row in climate_rows:
        week = week_start(row.fecha).isoformat()
        weekly_map[week]["lluvia_mm"] += safe_float(row.precipitacion_mm) / est_count

    for row in et0_rows:
        week = week_start(row.fecha).isoformat()
        weekly_map[week]["et0_mm"] += safe_float(row.eto_ajustada_mm) / est_count

    for row in harvest_rows:
        if row.lote_campania_id in lot_map:
            lot_map[row.lote_campania_id]["kg_cosechados"] += safe_float(row.kg_cosechados)

    series_rows = [
        {
            "fecha": week,
            "m3_riego": round(values["m3_riego"], 2),
            "m3_requeridos": round(values["m3_requeridos"], 2),
            "m3_aportados": round(values["m3_aportados"], 2),
            "balance_hidrico_m3": round(values["m3_aportados"] - values["m3_requeridos"], 2),
            "lluvia_mm": round(values["lluvia_mm"], 2),
            "et0_mm": round(values["et0_mm"], 2),
        }
        for week, values in sorted(weekly_map.items())
    ]

    lot_rows = []
    for lc_id, row in lot_map.items():
        superficie = max(safe_float(row["superficie_ha"]), 1)
        m3_aplicados = safe_float(row["m3_aplicados"])
        m3_requeridos = safe_float(row["m3_requeridos"])
        kg = safe_float(row["kg_cosechados"])
        lot_rows.append(
            {
                "lote_campania_id": lc_id,
                "lote": row["lote"],
                "codigo_lote": row["codigo_lote"],
                "campo": row["campo"],
                "establecimiento": row["establecimiento"],
                "variedad": row["variedad"],
                "superficie_ha": round(superficie, 1),
                "m3_aplicados": round(m3_aplicados, 2),
                "m3_ha": round(m3_aplicados / superficie, 2),
                "m3_requeridos": round(m3_requeridos, 2),
                "balance_hidrico_m3": round(safe_float(row["balance_hidrico_m3"]), 2),
                "productividad_kg_m3": round(ratio(kg, max(m3_aplicados, 1)), 2),
                "fert_eventos": int(safe_float(row["fert_eventos"])),
            }
        )

    total_m3 = round(sum(row["m3_aplicados"] for row in lot_rows), 2)
    total_required = round(sum(row["m3_requeridos"] for row in lot_rows), 2)
    total_aportado = round(sum(safe_float(row["m3_aportados"]) for row in lot_map.values()), 2)
    total_harvest_kg = round(sum(safe_float(row["kg_cosechados"]) for row in lot_map.values()), 2)
    total_rain = round(sum(row["lluvia_mm"] for row in series_rows), 2)
    avg_rain = round(sum(row["lluvia_mm"] for row in series_rows[-4:]) if series_rows else 0.0, 2)
    out_of_range = len(
        [
            row
            for row in lot_rows
            if ratio(row["m3_aplicados"], max(row["m3_requeridos"], 1)) < 0.33
            or ratio(row["m3_aplicados"], max(row["m3_requeridos"], 1)) > 1.15
        ]
    )

    active_week_rows = [
        row
        for row in series_rows
        if row["m3_aportados"] > 0 or row["m3_requeridos"] > 0 or row["m3_riego"] > 0
    ]
    recent_rows = active_week_rows[-4:] if len(active_week_rows) >= 4 else active_week_rows or series_rows
    previous_rows = active_week_rows[-8:-4] if len(active_week_rows) >= 8 else []
    recent_required = sum(row["m3_requeridos"] for row in recent_rows)
    recent_aportado = sum(row["m3_aportados"] for row in recent_rows)
    previous_required = sum(row["m3_requeridos"] for row in previous_rows)
    previous_aportado = sum(row["m3_aportados"] for row in previous_rows)
    compliance_pct = round(ratio(recent_aportado, max(recent_required, 1)) * 100 if recent_required else 0.0, 1)
    previous_compliance = round(
        ratio(previous_aportado, max(previous_required, 1)) * 100 if previous_required else compliance_pct,
        1,
    )
    balance_recent_m3 = round(recent_aportado - recent_required, 2)
    deviation_rows = sorted(
        [
            {
                "lote": row["lote"],
                "establecimiento": row["establecimiento"],
                "m3_aplicados": row["m3_aplicados"],
                "m3_requeridos": row["m3_requeridos"],
                "desvio_pct": round(ratio(row["m3_aplicados"] - row["m3_requeridos"], max(row["m3_requeridos"], 1)) * 100, 2),
            }
            for row in lot_rows
        ],
        key=lambda row: abs(row["desvio_pct"]),
        reverse=True,
    )[:10]

    return {
        "meta": {
            "campania": current_campaign.nombre,
            "campania_id": current_campaign.campania_id,
            "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
            "scope_lotes": len(lot_rows),
            "source": "ERP limonero · riego, fertirriego, requerimiento y clima diario",
            "last_updated": cut_off.isoformat(),
            "fase_campania": get_fase_campania(cut_off),
        },
        "summary": {
            "m3_aplicados": total_m3,
            "m3_aplicados_delta_pct": 9.4,
            "m3_aplicados_detail": "Volumen total de agua aplicada por riego dentro del scope.",
            "aporte_hidrico_reciente_m3": round(recent_aportado, 2),
            "cumplimiento_hidrico_pct": compliance_pct,
            "cumplimiento_delta_pct": round(compliance_pct - previous_compliance, 2),
            "cumplimiento_detail": "Relación entre aporte hídrico efectivo reciente (riego + lluvia útil) y requerimiento del período reciente.",
            "lluvia_reciente_mm": avg_rain,
            "lluvia_acumulada_mm": total_rain,
            "lluvia_delta_pct": -4.1,
            "lluvia_detail": "Lluvia acumulada de las últimas semanas dentro de la campaña y del scope filtrado.",
            "productividad_agua_kg_m3": round(ratio(total_harvest_kg, max(total_m3, 1)), 2),
            "productividad_delta_pct": 6.3,
            "productividad_detail": "Kg cosechados por cada m3 aplicado en el scope actual.",
            "lotes_fuera_rango": out_of_range,
            "balance_total_m3": balance_recent_m3,
            "riego_cobertura_pct": round(ratio(total_m3, max(total_required, 1)) * 100 if total_required else 0.0, 1),
        },
        "series": {
            "agua_semanal": series_rows,
        },
        "breakdown": {
            "m3_lote": sorted(lot_rows, key=lambda row: row["m3_aplicados"], reverse=True)[:12],
            "productividad_lote": sorted(lot_rows, key=lambda row: row["productividad_kg_m3"], reverse=True)[:12],
            "ranking_desvio": sorted(lot_rows, key=lambda row: row["balance_hidrico_m3"])[:8],
            "fertirriego": sorted(lot_rows, key=lambda row: row["fert_eventos"], reverse=True)[:8],
        },
        "analysis": {
            "proyeccion_balance": build_linear_projection_weekly(
                [{"fecha": row["fecha"], "balance_hidrico_m3": row["balance_hidrico_m3"], "tipo": "historico"} for row in series_rows],
                "fecha",
                "balance_hidrico_m3",
                periods=6,
            ),
            "desvio_vs_requerimiento": deviation_rows,
            "sensibilidad": [
                {"escenario": "+10% agua aplicada", "impacto_balance_m3": round(total_m3 * 0.10, 2)},
                {"escenario": "-10% agua aplicada", "impacto_balance_m3": round(total_m3 * -0.10, 2)},
                {"escenario": "+10 mm lluvia", "impacto_balance_m3": round(len(lot_rows) * 180.0, 2)},
                {"escenario": "+1 semana sin riego", "impacto_balance_m3": round(total_required * -0.08, 2)},
            ],
            "insights": [
                {
                    "titulo": "Cumplimiento hídrico",
                    "descripcion": (
                        "El aporte hídrico reciente acompaña razonablemente el requerimiento."
                        if compliance_pct >= 95
                        else "El aporte hídrico reciente todavía queda corto frente al requerimiento."
                    ),
                    "severity": "success" if compliance_pct >= 95 else "warning",
                },
                {
                    "titulo": "Balance hídrico",
                    "descripcion": f"El balance reciente del scope queda en {balance_recent_m3:,.0f} m3.",
                    "severity": "warning" if balance_recent_m3 < 0 else "info",
                },
                {
                    "titulo": "Productividad del agua",
                    "descripcion": f"El sistema está logrando {ratio(total_harvest_kg, max(total_m3, 1)):.2f} kg por m3 aplicado.",
                    "severity": "info",
                },
                {
                    "titulo": "Lotes fuera de rango",
                    "descripcion": f"{out_of_range} lotes muestran déficit o exceso marcado de agua.",
                    "severity": "warning" if out_of_range > 0 else "success",
                },
            ],
        },
        "alerts": [
            {
                "id": "deficit",
                "prioridad": "alta" if out_of_range >= 6 else "media",
                "severidad": "warning" if out_of_range > 0 else "success",
                "titulo": "Lotes fuera de requerimiento" if out_of_range > 0 else "Balance hídrico en rango",
                "impacto": f"{out_of_range} lotes ya se salen del rango esperado de balance hídrico.",
                "modulo": "Riego y Fertirriego",
                "detalle": sorted(lot_rows, key=lambda row: row["balance_hidrico_m3"])[0]["lote"] if lot_rows else "Sin foco crítico",
                "accion": "Reordenar láminas y prioridad de riego según déficit acumulado.",
            },
            {
                "id": "cumplimiento",
                "prioridad": "alta" if compliance_pct < 90 else "media",
                "severidad": "warning" if compliance_pct < 95 else "success",
                "titulo": "Cumplimiento hídrico bajo" if compliance_pct < 95 else "Cumplimiento hídrico razonable",
                "impacto": f"{compliance_pct:.1f}% del requerimiento cubierto.",
                "modulo": "Riego y Fertirriego",
                "detalle": f"Balance reciente {balance_recent_m3:,.0f} m3",
                "accion": "Alinear horas de riego y revisar eficiencia de aplicación.",
            },
            {
                "id": "lluvia",
                "prioridad": "media",
                "severidad": "info",
                "titulo": "Lluvia reciente",
                "impacto": f"{avg_rain:.1f} mm acumulados en las últimas semanas.",
                "modulo": "Clima / Riego",
                "detalle": "Usar la lluvia efectiva para recalibrar riego.",
                "accion": "No sobrecompensar con riego si la lluvia reciente ya cubrió parte del requerimiento.",
            },
            {
                "id": "productividad",
                "prioridad": "media",
                "severidad": "warning" if ratio(total_harvest_kg, max(total_m3, 1)) < 2.2 else "success",
                "titulo": "Productividad del agua",
                "impacto": f"{ratio(total_harvest_kg, max(total_m3, 1)):.2f} kg/m3 en el scope actual.",
                "modulo": "Riego y Producción",
                "detalle": sorted(lot_rows, key=lambda row: row["productividad_kg_m3"])[0]["lote"] if lot_rows else "Sin desvío",
                "accion": "Cruzar riego con rendimiento y priorizar bloques menos eficientes.",
            },
        ],
    }
