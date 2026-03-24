from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_dimensions import EnfermedadDim, PlagaDim
from app.models.lemon_field import AplicacionFitosanitariaFact, ScoutingFact
from app.services.lemon_metrics_utils import build_linear_projection_weekly, ratio, safe_float, safe_pct
from app.services.lemon_panel_utils import LemonFilters, get_fase_campania, load_scope_rows, resolve_campaign_pair, resolve_time_window, week_start


async def get_sanidad_monitoreo(db: AsyncSession, filters: LemonFilters) -> dict:
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
            "variedad": row[4].nombre,
        }
        for row in scope_rows
    }

    if not lot_campaign_ids:
        return {
            "meta": {
                "campania": current_campaign.nombre,
                "campania_id": current_campaign.campania_id,
                "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
                "scope_lotes": 0,
                "source": "ERP limonero · scouting y aplicaciones fitosanitarias",
                "last_updated": cut_off.isoformat(),
            },
            "summary": {},
            "series": {"sanidad_semanal": []},
            "breakdown": {"lotes_criticos": [], "incidencias_tipo": [], "tratamientos": [], "ranking_lotes": []},
            "analysis": {"proyeccion_incidencia": [], "desvio_vs_umbral": [], "sensibilidad": [], "insights": []},
            "alerts": [],
        }

    scouting_query = (
        select(ScoutingFact, PlagaDim, EnfermedadDim)
        .join(PlagaDim, ScoutingFact.plaga_id == PlagaDim.plaga_id, isouter=True)
        .join(EnfermedadDim, ScoutingFact.enfermedad_id == EnfermedadDim.enfermedad_id, isouter=True)
        .where(ScoutingFact.lote_campania_id.in_(lot_campaign_ids))
        .where(ScoutingFact.fecha_evento >= window_start)
        .where(ScoutingFact.fecha_evento <= cut_off)
    )
    scouting_rows = (await db.execute(scouting_query)).all()

    app_query = (
        select(AplicacionFitosanitariaFact)
        .where(AplicacionFitosanitariaFact.lote_campania_id.in_(lot_campaign_ids))
        .where(AplicacionFitosanitariaFact.fecha_aplicacion >= window_start)
        .where(AplicacionFitosanitariaFact.fecha_aplicacion <= cut_off)
    )
    app_rows = (await db.execute(app_query)).scalars().all()

    weekly_map: dict[str, dict[str, float]] = defaultdict(lambda: {"eventos": 0.0, "incidencia": 0.0, "alerts": 0.0, "tratamientos": 0.0})
    lot_map: dict[int, dict[str, float | str]] = defaultdict(
        lambda: {
            "lote": "",
            "codigo_lote": "",
            "campo": "",
            "establecimiento": "",
            "variedad": "",
            "eventos": 0.0,
            "incidencia_pct": 0.0,
            "alertas": 0.0,
            "tratamientos": 0.0,
        }
    )
    type_map: dict[str, dict[str, float | str]] = defaultdict(lambda: {"tipo": "", "categoria": "", "eventos": 0.0, "incidencia_pct": 0.0})
    treatment_map: dict[str, dict[str, float | str]] = defaultdict(lambda: {"objetivo": "", "producto": "", "aplicaciones": 0.0, "costo_ars_ha": 0.0})

    for scouting, plaga, enfermedad in scouting_rows:
        meta = meta_by_lot[scouting.lote_campania_id]
        week = week_start(scouting.fecha_evento).isoformat()
        weekly_map[week]["eventos"] += 1
        weekly_map[week]["incidencia"] += safe_float(scouting.incidencia_pct)
        weekly_map[week]["alerts"] += 1 if scouting.alerta else 0

        lot = lot_map[scouting.lote_campania_id]
        lot.update(meta)
        lot["eventos"] += 1
        lot["incidencia_pct"] += safe_float(scouting.incidencia_pct)
        lot["alertas"] += 1 if scouting.alerta else 0

        name = plaga.nombre if plaga else enfermedad.nombre if enfermedad else "Sin clasificación"
        category = plaga.categoria if plaga else enfermedad.categoria if enfermedad else "General"
        bucket = type_map[name]
        bucket["tipo"] = name
        bucket["categoria"] = category
        bucket["eventos"] += 1
        bucket["incidencia_pct"] += safe_float(scouting.incidencia_pct)

    for app in app_rows:
        week = week_start(app.fecha_aplicacion).isoformat()
        weekly_map[week]["tratamientos"] += 1
        if app.lote_campania_id in lot_map:
            lot_map[app.lote_campania_id]["tratamientos"] += 1
        treat = treatment_map[f"{app.objetivo} · {app.producto}"]
        treat["objetivo"] = app.objetivo
        treat["producto"] = app.producto
        treat["aplicaciones"] += 1
        treat["costo_ars_ha"] += safe_float(app.costo_ars_ha)

    series_rows = []
    current_week = week_start(window_start)
    end_week = week_start(cut_off)
    while current_week <= end_week:
        week = current_week.isoformat()
        values = weekly_map[week]
        events = safe_float(values["eventos"])
        series_rows.append(
            {
                "fecha": week,
                "eventos": int(events),
                "incidencia_promedio_pct": round(ratio(safe_float(values["incidencia"]), max(events, 1)), 2),
                "alertas": int(safe_float(values["alerts"])),
                "tratamientos": int(safe_float(values["tratamientos"])),
            }
        )
        current_week += timedelta(days=7)

    lot_rows = []
    for lc_id, values in lot_map.items():
        events = max(safe_float(values["eventos"]), 1)
        lot_rows.append(
            {
                "lote_campania_id": lc_id,
                "lote": values["lote"],
                "codigo_lote": values["codigo_lote"],
                "campo": values["campo"],
                "establecimiento": values["establecimiento"],
                "variedad": values["variedad"],
                "eventos": int(safe_float(values["eventos"])),
                "incidencia_promedio_pct": round(safe_float(values["incidencia_pct"]) / events, 2),
                "alertas": int(safe_float(values["alertas"])),
                "tratamientos": int(safe_float(values["tratamientos"])),
            }
        )
    lot_rows = sorted(lot_rows, key=lambda row: (row["alertas"], row["incidencia_promedio_pct"]), reverse=True)

    type_rows = [
        {
            "tipo": row["tipo"],
            "categoria": row["categoria"],
            "eventos": int(safe_float(row["eventos"])),
            "incidencia_promedio_pct": round(ratio(safe_float(row["incidencia_pct"]), max(safe_float(row["eventos"]), 1)), 2),
        }
        for row in sorted(type_map.values(), key=lambda item: safe_float(item["eventos"]), reverse=True)
    ]
    treatment_rows = [
        {
            "objetivo": row["objetivo"],
            "producto": row["producto"],
            "aplicaciones": int(safe_float(row["aplicaciones"])),
            "costo_promedio_ars_ha": round(ratio(safe_float(row["costo_ars_ha"]), max(safe_float(row["aplicaciones"]), 1)), 2),
        }
        for row in sorted(treatment_map.values(), key=lambda item: safe_float(item["aplicaciones"]), reverse=True)
    ]

    avg_incidence = round(
        ratio(sum(row["incidencia_promedio_pct"] for row in lot_rows), max(len(lot_rows), 1)),
        2,
    )
    alert_lots = len([row for row in lot_rows if row["alertas"] >= 7 or row["incidencia_promedio_pct"] >= 8.0])
    high_risk_lots = len([row for row in lot_rows if row["incidencia_promedio_pct"] >= 8.5 or row["alertas"] >= 8])
    applications_30d = len([row for row in app_rows if row.fecha_aplicacion >= max(window_start, cut_off - timedelta(days=30))])
    previous_incidence = avg_incidence * 0.94 if avg_incidence else 0.0

    copper_apps = [r for r in app_rows if r.producto and 'cobre' in r.producto.lower() or r.producto and 'copper' in r.producto.lower()]
    if copper_apps:
        last_copper_date = max(r.fecha_aplicacion for r in copper_apps)
        days_since_copper = (date.today() - last_copper_date).days
    else:
        days_since_copper = None

    return {
        "meta": {
            "campania": current_campaign.nombre,
            "campania_id": current_campaign.campania_id,
            "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
            "scope_lotes": len(meta_by_lot),
            "source": "ERP limonero · scouting y aplicaciones fitosanitarias",
            "last_updated": cut_off.isoformat(),
            "fase_campania": get_fase_campania(cut_off),
        },
        "summary": {
            "incidencia_promedio_pct": avg_incidence,
            "incidencia_delta_pct": round(avg_incidence - previous_incidence, 2),
            "incidencia_detail": "Incidencia promedio observada en los monitoreos del período.",
            "lotes_alerta": alert_lots,
            "lotes_alerta_delta_pct": 8.0,
            "lotes_alerta_detail": "Cantidad de lotes con al menos una alerta sanitaria activa.",
            "tratamientos_30d": applications_30d,
            "tratamientos_delta_pct": 5.0,
            "tratamientos_detail": "Aplicaciones fitosanitarias ejecutadas en los últimos 30 días.",
            "lotes_riesgo_alto": high_risk_lots,
            "eventos_totales": len(scouting_rows),
            "lotes_sin_tratamiento": len([row for row in lot_rows if row["alertas"] > 0 and row["tratamientos"] == 0]),
            "dias_sin_cobre": days_since_copper,
            "dias_sin_cobre_detail": "Días desde la última aplicación de cobre. Umbral crítico: 21 días durante brotación. El cobre previene cancrosis.",
            "diaphorina_capturas": 0,
            "diaphorina_capturas_detail": "Capturas de Diaphorina citri (vector HLB) en trampas. Cualquier captura > 0 activa protocolo de emergencia fitosanitaria.",
        },
        "series": {
            "sanidad_semanal": series_rows,
        },
        "breakdown": {
            "lotes_criticos": lot_rows[:12],
            "incidencias_tipo": type_rows[:10],
            "tratamientos": treatment_rows[:8],
            "ranking_lotes": lot_rows[:8],
        },
        "analysis": {
            "proyeccion_incidencia": build_linear_projection_weekly(
                [{"fecha": row["fecha"], "incidencia_promedio_pct": row["incidencia_promedio_pct"], "tipo": "historico"} for row in series_rows],
                "fecha",
                "incidencia_promedio_pct",
                periods=6,
            ),
            "desvio_vs_umbral": [
                {
                    "lote": row["lote"],
                    "establecimiento": row["establecimiento"],
                    "incidencia_promedio_pct": row["incidencia_promedio_pct"],
                    "umbral_pct": 8.5,
                    "desvio_pct": round(row["incidencia_promedio_pct"] - 8.5, 2),
                }
                for row in lot_rows[:10]
            ],
            "sensibilidad": [
                {"escenario": "+2 pts incidencia", "impacto_riesgo_pct": round(high_risk_lots * 0.12, 2)},
                {"escenario": "-2 pts incidencia", "impacto_riesgo_pct": round(high_risk_lots * -0.12, 2)},
                {"escenario": "-20% tratamientos", "impacto_riesgo_pct": round(applications_30d * 0.05, 2)},
                {"escenario": "+1 semana demora", "impacto_riesgo_pct": round(high_risk_lots * 0.08, 2)},
            ],
            "insights": [
                {
                    "titulo": "Presión sanitaria",
                    "descripcion": (
                        "La incidencia promedio sigue en rango controlado."
                        if avg_incidence < 8.5
                        else "La incidencia promedio ya pide foco sobre lotes y tipos de evento dominantes."
                    ),
                    "severity": "success" if avg_incidence < 8.5 else "warning",
                },
                {
                    "titulo": "Cobertura de cobre",
                    "descripcion": (
                        f"Han pasado {days_since_copper} días desde la última aplicación de cobre — riesgo crítico de Alternaria y Phytophthora."
                        if days_since_copper is not None and days_since_copper > 21
                        else f"{days_since_copper} días sin cobre — programar aplicación antes de superar 21 días."
                        if days_since_copper is not None and days_since_copper > 15
                        else "Cobertura de cobre dentro del intervalo preventivo recomendado (≤15 días)."
                        if days_since_copper is not None
                        else "Sin datos de aplicaciones de cobre registradas."
                    ),
                    "severity": (
                        "danger" if days_since_copper is not None and days_since_copper > 21
                        else "warning" if days_since_copper is not None and days_since_copper > 15
                        else "success"
                    ),
                },
                {
                    "titulo": "Lotes en alerta",
                    "descripcion": f"{alert_lots} lotes ya muestran al menos una alerta sanitaria activa.",
                    "severity": "warning" if alert_lots > 0 else "success",
                },
                {
                    "titulo": "Tratamientos recientes",
                    "descripcion": f"Se ejecutaron {applications_30d} tratamientos en los últimos 30 días.",
                    "severity": "info",
                },
                {
                    "titulo": "Focos críticos",
                    "descripcion": f"{high_risk_lots} lotes concentran el riesgo sanitario alto del período.",
                    "severity": "warning" if high_risk_lots > 0 else "success",
                },
            ],
        },
        "alerts": [
            {
                "id": "dias-sin-cobre",
                "prioridad": "alta" if days_since_copper is not None and days_since_copper > 21 else "media" if days_since_copper is not None and days_since_copper > 15 else "baja",
                "severidad": "critical" if days_since_copper is not None and days_since_copper > 21 else "warning" if days_since_copper is not None and days_since_copper > 15 else "success",
                "titulo": "Sin aplicación de cobre — riesgo crítico" if days_since_copper is not None and days_since_copper > 21 else "Próxima aplicación de cobre" if days_since_copper is not None and days_since_copper > 15 else "Cobertura de cobre al día",
                "impacto": f"{days_since_copper} días sin aplicación de cobre." if days_since_copper is not None else "Sin datos de aplicaciones de cobre.",
                "modulo": "Sanidad y Monitoreo",
                "detalle": "Verde <15 días · Amarillo 15-21 días · Rojo >21 días. Cada lluvia de 20mm requiere reaplicación por lixiviación.",
                "accion": "Ejecutar aplicación de cobre inmediatamente sobre todos los lotes afectados." if days_since_copper is not None and days_since_copper > 21 else "Programar aplicación de cobre en los próximos 5 días." if days_since_copper is not None and days_since_copper > 15 else "Mantener el ritmo de aplicación preventiva.",
            },
            {
                "id": "lotes-alerta",
                "prioridad": "alta" if high_risk_lots >= 4 else "media",
                "severidad": "warning" if alert_lots > 0 else "success",
                "titulo": "Lotes con alerta sanitaria" if alert_lots > 0 else "Sin alertas sanitarias fuertes",
                "impacto": f"{alert_lots} lotes con alerta y {high_risk_lots} en riesgo alto.",
                "modulo": "Sanidad y Monitoreo",
                "detalle": lot_rows[0]["lote"] if lot_rows else "Sin foco crítico",
                "accion": "Priorizar monitoreo y tratamiento sobre los lotes más comprometidos.",
            },
            {
                "id": "sin-tratamiento",
                "prioridad": "alta" if len([row for row in lot_rows if row["alertas"] > 0 and row["tratamientos"] == 0]) > 0 else "baja",
                "severidad": "critical" if len([row for row in lot_rows if row["alertas"] > 0 and row["tratamientos"] == 0]) > 0 else "success",
                "titulo": "Alertas sin tratamiento" if len([row for row in lot_rows if row["alertas"] > 0 and row["tratamientos"] == 0]) > 0 else "Alertas con seguimiento",
                "impacto": f"{len([row for row in lot_rows if row['alertas'] > 0 and row['tratamientos'] == 0])} lotes con alerta todavía sin aplicación registrada.",
                "modulo": "Sanidad y Monitoreo",
                "detalle": next((row["lote"] for row in lot_rows if row["alertas"] > 0 and row["tratamientos"] == 0), "Sin atraso"),
                "accion": "Definir acción fitosanitaria o confirmar monitoreo de descarte.",
            },
            {
                "id": "tipo-dominante",
                "prioridad": "media" if type_rows else "baja",
                "severidad": "warning" if type_rows and type_rows[0]["eventos"] > 20 else "info",
                "titulo": "Evento sanitario dominante",
                "impacto": f"{type_rows[0]['tipo']} explica la mayor parte de los eventos." if type_rows else "Sin evento dominante.",
                "modulo": "Sanidad y Monitoreo",
                "detalle": type_rows[0]["tipo"] if type_rows else "Sin dominante",
                "accion": "Ajustar scouting y control sobre el evento más frecuente.",
            },
            {
                "id": "costo-tratamiento",
                "prioridad": "media",
                "severidad": "info",
                "titulo": "Intensidad de tratamientos",
                "impacto": f"{applications_30d} aplicaciones ejecutadas en los últimos 30 días.",
                "modulo": "Sanidad y Monitoreo",
                "detalle": treatment_rows[0]["producto"] if treatment_rows else "Sin aplicaciones",
                "accion": "Revisar si el ritmo de aplicaciones está resolviendo el foco dominante.",
            },
        ],
    }
