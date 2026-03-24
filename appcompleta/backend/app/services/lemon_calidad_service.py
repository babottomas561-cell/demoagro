from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_dimensions import CalibreDim, DefectoDim, DestinoFrutaDim
from app.models.lemon_field import LoteCampaniaFact, RendimientoLoteFact
from app.models.lemon_quality import ClasificacionCalidadFact, PackoutFact, RecepcionFrutaFact, RechazoFact
from app.services.lemon_metrics_utils import (
    build_linear_projection_daily,
    ratio,
    safe_float,
    safe_pct,
)
from app.services.lemon_panel_utils import (
    LemonFilters,
    get_fase_campania,
    load_scope_rows,
    resolve_campaign_pair,
    resolve_previous_window,
    resolve_time_window,
)


@dataclass
class QualityLotMeta:
    lote_campania_id: int
    lote: str
    codigo_lote: str
    campo: str
    establecimiento: str
    variedad: str
    superficie_ha: float
    objetivo_packout_pct: float


def _severity_from_packout(actual: float, target: float) -> str:
    if actual >= target:
        return "success"
    if actual >= target - 4:
        return "warning"
    return "danger"


async def _load_quality_meta(db: AsyncSession, filters: LemonFilters, campania_id: int) -> list[QualityLotMeta]:
    rows = await load_scope_rows(db, filters, campania_id)
    meta: list[QualityLotMeta] = []
    for lot_campaign, lote, campo, establecimiento, variedad in rows:
        meta.append(
            QualityLotMeta(
                lote_campania_id=lot_campaign.lote_campania_id,
                lote=lote.nombre,
                codigo_lote=lote.codigo,
                campo=campo.nombre,
                establecimiento=establecimiento.nombre,
                variedad=variedad.nombre,
                superficie_ha=safe_float(lot_campaign.superficie_ha),
                objetivo_packout_pct=safe_float(lot_campaign.objetivo_packout_pct),
            )
        )
    return meta


async def _build_snapshot(
    db: AsyncSession,
    filters: LemonFilters,
    campania_id: int,
    window_start: date,
    cut_off: date,
) -> dict:
    meta = await _load_quality_meta(db, filters, campania_id)
    if not meta:
        return {
            "summary": {
                "received_kg": 0.0,
                "commercial_kg": 0.0,
                "packout_pct": 0.0,
                "rejection_pct": 0.0,
                "export_share_pct": 0.0,
                "industry_share_pct": 0.0,
                "discard_share_pct": 0.0,
                "critical_lots": 0,
                "target_packout_pct": 0.0,
                "latest_daily": {
                    "fecha": cut_off.isoformat(),
                    "packout_pct": 0.0,
                    "rechazo_pct": 0.0,
                    "industry_pct": 0.0,
                    "discard_pct": 0.0,
                },
            },
            "series": [],
            "lot_rows": [],
            "destination_rows": [],
            "defect_rows": [],
            "ranking_rows": [],
            "deviation_rows": [],
            "alerts_source": {"critical": [], "defects": []},
            "last_date": cut_off,
        }

    lot_campaign_ids = [item.lote_campania_id for item in meta]
    meta_by_lot = {item.lote_campania_id: item for item in meta}

    reception_rows = (
        await db.execute(
            select(RecepcionFrutaFact)
            .where(RecepcionFrutaFact.lote_campania_id.in_(lot_campaign_ids))
            .where(RecepcionFrutaFact.fecha_recepcion >= window_start)
            .where(RecepcionFrutaFact.fecha_recepcion <= cut_off)
            .order_by(RecepcionFrutaFact.fecha_recepcion)
        )
    ).scalars().all()
    packout_query = (
        select(PackoutFact, RecepcionFrutaFact)
        .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
        .where(RecepcionFrutaFact.lote_campania_id.in_(lot_campaign_ids))
        .where(PackoutFact.fecha_proceso >= window_start)
        .where(PackoutFact.fecha_proceso <= cut_off)
    )
    if filters.destino_id:
        packout_query = packout_query.where(PackoutFact.destino_id == filters.destino_id)
    if filters.calibre_id:
        packout_query = packout_query.where(PackoutFact.calibre_id == filters.calibre_id)
    packout_rows = (await db.execute(packout_query)).all()

    classification_query = (
        select(ClasificacionCalidadFact, RecepcionFrutaFact, DestinoFrutaDim, CalibreDim)
        .join(RecepcionFrutaFact, ClasificacionCalidadFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
        .join(DestinoFrutaDim, ClasificacionCalidadFact.destino_id == DestinoFrutaDim.destino_id)
        .join(CalibreDim, ClasificacionCalidadFact.calibre_id == CalibreDim.calibre_id, isouter=True)
        .where(RecepcionFrutaFact.lote_campania_id.in_(lot_campaign_ids))
        .where(ClasificacionCalidadFact.fecha_clasificacion >= window_start)
        .where(ClasificacionCalidadFact.fecha_clasificacion <= cut_off)
    )
    if filters.destino_id:
        classification_query = classification_query.where(ClasificacionCalidadFact.destino_id == filters.destino_id)
    if filters.calibre_id:
        classification_query = classification_query.where(ClasificacionCalidadFact.calibre_id == filters.calibre_id)
    classification_rows = (await db.execute(classification_query)).all()

    rejection_rows = (
        await db.execute(
            select(RechazoFact, RecepcionFrutaFact, DefectoDim)
            .join(RecepcionFrutaFact, RechazoFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .join(DefectoDim, RechazoFact.defecto_id == DefectoDim.defecto_id)
            .where(RecepcionFrutaFact.lote_campania_id.in_(lot_campaign_ids))
            .where(RechazoFact.fecha_rechazo >= window_start)
            .where(RechazoFact.fecha_rechazo <= cut_off)
        )
    ).all()
    yield_rows = (
        await db.execute(
            select(RendimientoLoteFact).where(RendimientoLoteFact.lote_campania_id.in_(lot_campaign_ids))
        )
    ).scalars().all()

    lot_state: dict[int, dict[str, float | str]] = {}
    for item in meta:
        lot_state[item.lote_campania_id] = {
            "lote_campania_id": item.lote_campania_id,
            "lote": item.lote,
            "codigo_lote": item.codigo_lote,
            "campo": item.campo,
            "establecimiento": item.establecimiento,
            "variedad": item.variedad,
            "superficie_ha": item.superficie_ha,
            "kg_recibidos": 0.0,
            "kg_comerciales": 0.0,
            "kg_rechazo": 0.0,
            "kg_exportacion": 0.0,
            "kg_industria": 0.0,
            "kg_descarte": 0.0,
            "packout_pct": 0.0,
            "rechazo_pct": 0.0,
            "objetivo_packout_pct": item.objetivo_packout_pct,
            "principal_defecto": "",
            "principal_defecto_kg": 0.0,
        }

    daily: dict[date, dict[str, float]] = defaultdict(
        lambda: {
            "recibidos": 0.0,
            "comerciales": 0.0,
            "rechazo": 0.0,
            "industria": 0.0,
            "descarte": 0.0,
        }
    )
    destination_totals: dict[str, float] = defaultdict(float)
    defect_totals: dict[str, dict[str, float | str]] = defaultdict(lambda: {"defecto": "", "categoria": "", "kg_rechazo": 0.0})
    calibre_totals: dict[str, dict[str, float | str | bool]] = defaultdict(
        lambda: {"calibre": "", "kg": 0.0, "apto_exportacion": False, "banda_mm": ""}
    )
    rejection_by_lot_defect: dict[tuple[int, str], float] = defaultdict(float)
    sanitary_rejection_kg = 0.0
    last_dates = [window_start]

    for row in reception_rows:
        lot_state[row.lote_campania_id]["kg_recibidos"] += safe_float(row.kg_recibidos)
        daily[row.fecha_recepcion]["recibidos"] += safe_float(row.kg_recibidos)
        last_dates.append(row.fecha_recepcion)

    for packout, reception in packout_rows:
        lot_state[reception.lote_campania_id]["kg_comerciales"] += safe_float(packout.kg_salida)
        daily[packout.fecha_proceso]["comerciales"] += safe_float(packout.kg_salida)
        last_dates.append(packout.fecha_proceso)

    for classification, reception, destino, calibre in classification_rows:
        kg = safe_float(classification.kg_clasificados)
        destination_totals[destino.nombre] += kg
        calibre_name = calibre.nombre if calibre else "Sin calibre"
        calibre_bucket = calibre_totals[calibre_name]
        calibre_bucket["calibre"] = calibre_name
        calibre_bucket["kg"] += kg
        calibre_bucket["apto_exportacion"] = bool(calibre.apto_exportacion) if calibre else False
        if calibre and calibre.diametro_min_mm and calibre.diametro_max_mm:
            calibre_bucket["banda_mm"] = f"{safe_float(calibre.diametro_min_mm):.0f}-{safe_float(calibre.diametro_max_mm):.0f} mm"
        if destino.codigo == "EXP":
            lot_state[reception.lote_campania_id]["kg_exportacion"] += kg
        elif destino.codigo == "IND":
            lot_state[reception.lote_campania_id]["kg_industria"] += kg
            daily[classification.fecha_clasificacion]["industria"] += kg
        elif destino.codigo == "DSC":
            lot_state[reception.lote_campania_id]["kg_descarte"] += kg
            daily[classification.fecha_clasificacion]["descarte"] += kg
        last_dates.append(classification.fecha_clasificacion)

    for rejection, reception, defect in rejection_rows:
        kg = safe_float(rejection.kg_rechazo)
        lot_state[reception.lote_campania_id]["kg_rechazo"] += kg
        daily[rejection.fecha_rechazo]["rechazo"] += kg
        bucket = defect_totals[defect.nombre]
        bucket["defecto"] = defect.nombre
        bucket["categoria"] = defect.categoria
        bucket["kg_rechazo"] += kg
        if str(defect.categoria).lower() == "sanitario":
            sanitary_rejection_kg += kg
        rejection_by_lot_defect[(reception.lote_campania_id, defect.nombre)] += kg
        last_dates.append(rejection.fecha_rechazo)

    for row in yield_rows:
        if row.lote_campania_id not in lot_state:
            continue
        state = lot_state[row.lote_campania_id]
        if safe_float(state["kg_exportacion"]) <= 0:
            base = safe_float(state["kg_recibidos"])
            state["kg_exportacion"] = base * safe_float(row.fruta_exportable_pct) / 100.0
            state["kg_industria"] = base * safe_float(row.fruta_industria_pct) / 100.0
            state["kg_descarte"] = base * safe_float(row.fruta_descarte_pct) / 100.0

    lot_rows = []
    for item in meta:
        state = lot_state[item.lote_campania_id]
        received = safe_float(state["kg_recibidos"])
        commercial = safe_float(state["kg_comerciales"])
        rejected = safe_float(state["kg_rechazo"])
        packout_pct = ratio(commercial, received) * 100 if received else 0.0
        rejection_pct = ratio(rejected, received) * 100 if received else 0.0
        state["packout_pct"] = round(packout_pct, 1)
        state["rechazo_pct"] = round(rejection_pct, 1)
        defect_candidates = [
            (defecto, kg)
            for (lc_id, defecto), kg in rejection_by_lot_defect.items()
            if lc_id == item.lote_campania_id
        ]
        if defect_candidates:
            top_defect, top_kg = max(defect_candidates, key=lambda row: row[1])
            state["principal_defecto"] = top_defect
            state["principal_defecto_kg"] = round(top_kg, 2)
        lot_rows.append(
            {
                "lote_campania_id": item.lote_campania_id,
                "lote": item.lote,
                "codigo_lote": item.codigo_lote,
                "campo": item.campo,
                "establecimiento": item.establecimiento,
                "variedad": item.variedad,
                "superficie_ha": round(item.superficie_ha, 1),
                "kg_recibidos": round(received, 2),
                "kg_comerciales": round(commercial, 2),
                "packout_pct": round(packout_pct, 1),
                "rechazo_pct": round(rejection_pct, 1),
                "objetivo_packout_pct": round(item.objetivo_packout_pct, 1),
                "kg_exportacion": round(safe_float(state["kg_exportacion"]), 2),
                "kg_industria": round(safe_float(state["kg_industria"]), 2),
                "kg_descarte": round(safe_float(state["kg_descarte"]), 2),
                "principal_defecto": str(state["principal_defecto"]),
                "principal_defecto_kg": round(safe_float(state["principal_defecto_kg"]), 2),
            }
        )

    received_kg = round(sum(safe_float(row["kg_recibidos"]) for row in lot_rows), 2)
    commercial_kg = round(sum(safe_float(row["kg_comerciales"]) for row in lot_rows), 2)
    rejection_kg = round(sum(safe_float(row["kg_rechazo"]) for row in lot_state.values()), 2)
    export_kg = round(sum(safe_float(row["kg_exportacion"]) for row in lot_rows), 2)
    industry_kg = round(sum(safe_float(row["kg_industria"]) for row in lot_rows), 2)
    discard_kg = round(sum(safe_float(row["kg_descarte"]) for row in lot_rows), 2)

    daily_rows = []
    for current_day, values in sorted(daily.items()):
        rec = safe_float(values["recibidos"])
        useful = safe_float(values["comerciales"])
        rej = safe_float(values["rechazo"])
        daily_rows.append(
            {
                "fecha": current_day.isoformat(),
                "kg_recibidos": round(rec, 2),
                "kg_comerciales": round(useful, 2),
                "packout_pct": round(ratio(useful, rec) * 100 if rec else 0.0, 1),
                "rechazo_pct": round(ratio(rej, rec) * 100 if rec else 0.0, 1),
                "industria_pct": round(ratio(safe_float(values["industria"]), rec) * 100 if rec else 0.0, 1),
                "descarte_pct": round(ratio(safe_float(values["descarte"]), rec) * 100 if rec else 0.0, 1),
            }
        )

    defect_rows = [
        {
            "defecto": key,
            "categoria": str(value["categoria"]),
            "kg_rechazo": round(safe_float(value["kg_rechazo"]), 2),
            "participacion_pct": round(ratio(safe_float(value["kg_rechazo"]), max(rejection_kg, 1)) * 100, 1),
        }
        for key, value in sorted(defect_totals.items(), key=lambda item: safe_float(item[1]["kg_rechazo"]), reverse=True)
    ]
    destination_rows = [
        {
            "destino": destino,
            "kg": round(kg, 2),
            "participacion_pct": round(ratio(kg, max(export_kg + industry_kg + discard_kg, 1)) * 100, 1),
        }
        for destino, kg in sorted(destination_totals.items(), key=lambda item: item[1], reverse=True)
    ]
    classified_kg = export_kg + industry_kg + discard_kg
    exportable_calibre_kg = round(
        sum(safe_float(item["kg"]) for item in calibre_totals.values() if bool(item["apto_exportacion"])),
        2,
    )
    calibre_rows = [
        {
            "calibre": calibre,
            "kg": round(safe_float(values["kg"]), 2),
            "participacion_pct": round(ratio(safe_float(values["kg"]), max(classified_kg, 1)) * 100, 1),
            "apto_exportacion": bool(values["apto_exportacion"]),
            "banda_mm": str(values["banda_mm"]),
        }
        for calibre, values in sorted(calibre_totals.items(), key=lambda item: safe_float(item[1]["kg"]), reverse=True)
    ]

    ranking_rows = sorted(lot_rows, key=lambda row: (row["rechazo_pct"], -row["packout_pct"]), reverse=True)[:8]
    deviation_rows = sorted(
        [
            {
                "lote": row["lote"],
                "establecimiento": row["establecimiento"],
                "packout_pct": row["packout_pct"],
                "objetivo_packout_pct": row["objetivo_packout_pct"],
                "desvio_pct": round(row["packout_pct"] - row["objetivo_packout_pct"], 2),
            }
            for row in lot_rows
        ],
        key=lambda row: row["desvio_pct"],
    )[:10]

    target_packout = round(mean([item.objetivo_packout_pct for item in meta if item.objetivo_packout_pct > 0]) if meta else 0.0, 1)
    critical_rows = [row for row in lot_rows if row["packout_pct"] < row["objetivo_packout_pct"] - 5 or row["rechazo_pct"] >= 10]
    latest_daily = (
        daily_rows[-1]
        if daily_rows
        else {
            "fecha": cut_off.isoformat(),
            "packout_pct": 0.0,
            "rechazo_pct": 0.0,
            "industria_pct": 0.0,
            "descarte_pct": 0.0,
        }
    )

    return {
        "summary": {
            "received_kg": received_kg,
            "commercial_kg": commercial_kg,
            "packout_pct": round(ratio(commercial_kg, received_kg) * 100 if received_kg else 0.0, 1),
            "rejection_pct": round(ratio(rejection_kg, received_kg) * 100 if received_kg else 0.0, 1),
            "sanitary_rejection_pct": round(ratio(sanitary_rejection_kg, max(rejection_kg, 1)) * 100, 1),
            "export_share_pct": round(ratio(export_kg, max(export_kg + industry_kg + discard_kg, 1)) * 100, 1),
            "industry_share_pct": round(ratio(industry_kg, max(export_kg + industry_kg + discard_kg, 1)) * 100, 1),
            "discard_share_pct": round(ratio(discard_kg, max(export_kg + industry_kg + discard_kg, 1)) * 100, 1),
            "exportable_calibre_pct": round(ratio(exportable_calibre_kg, max(classified_kg, 1)) * 100, 1),
            "traceability_pct": round(
                ratio(
                    sum(
                        1
                        for row in lot_rows
                        if row["lote"] and row["campo"] and row["establecimiento"] and row["variedad"]
                    ),
                    max(len(lot_rows), 1),
                ) * 100,
                1,
            ),
            "critical_lots": len(critical_rows),
            "target_packout_pct": target_packout,
            "latest_daily": latest_daily,
        },
        "series": daily_rows,
        "lot_rows": sorted(lot_rows, key=lambda row: row["packout_pct"], reverse=True),
        "destination_rows": destination_rows,
        "calibre_rows": calibre_rows,
        "defect_rows": defect_rows,
        "ranking_rows": ranking_rows,
        "deviation_rows": deviation_rows,
        "alerts_source": {
            "critical": critical_rows,
            "defects": defect_rows[:3],
        },
        "last_date": max(last_dates),
    }


async def get_calidad_fruta(db: AsyncSession, filters: LemonFilters) -> dict:
    campaign_pair = await resolve_campaign_pair(db, filters.campania_id)
    current_campaign = campaign_pair.current
    current_window_start, cut_off, _ = resolve_time_window(
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        filters,
    )
    scope_meta = await _load_quality_meta(db, filters, current_campaign.campania_id)

    current = await _build_snapshot(db, filters, current_campaign.campania_id, current_window_start, cut_off)
    previous_summary = None
    if campaign_pair.previous:
        previous_window_start, previous_cut_off = resolve_previous_window(
            current_window_start,
            cut_off,
            current_campaign,
            campaign_pair.previous,
        )
        previous = await _build_snapshot(
            db,
            filters,
            campaign_pair.previous.campania_id,
            previous_window_start,
            previous_cut_off,
        )
        previous_summary = previous["summary"]

    previous = previous_summary or {
        "packout_pct": 0.0,
        "rejection_pct": 0.0,
        "export_share_pct": 0.0,
        "critical_lots": 0,
    }
    summary = current["summary"]

    projection_base = [{"fecha": row["fecha"], "packout_pct": row["packout_pct"], "tipo": "historico"} for row in current["series"]]

    return {
        "meta": {
            "campania": current_campaign.nombre,
            "campania_id": current_campaign.campania_id,
            "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
            "scope_lotes": len(scope_meta),
            "scope_superficie_ha": round(sum(item.superficie_ha for item in scope_meta), 2),
            "source": "ERP limonero · recepción, clasificación, rechazo y packout",
            "last_updated": current["last_date"].isoformat(),
            "fase_campania": get_fase_campania(current["last_date"]),
        },
        "summary": {
            "packout_hoy_pct": summary["latest_daily"]["packout_pct"],
            "rechazo_hoy_pct": summary["latest_daily"]["rechazo_pct"],
            "industria_hoy_pct": summary["latest_daily"]["industria_pct"],
            "descarte_hoy_pct": summary["latest_daily"]["descarte_pct"],
            "packout_promedio_pct": summary["packout_pct"],
            "packout_promedio_delta_pct": round(summary["packout_pct"] - previous["packout_pct"], 2),
            "packout_promedio_status": _severity_from_packout(summary["packout_pct"], summary["target_packout_pct"]),
            "packout_promedio_detail": "Porcentaje útil sobre fruta recibida luego de clasificación y proceso.",
            "rechazo_pct": summary["rejection_pct"],
            "rechazo_delta_pct": round(summary["rejection_pct"] - previous["rejection_pct"], 2),
            "rechazo_detail": "Proporción de fruta perdida por defecto o descarte operativo.",
            "riesgo_sanitario_pct": summary["sanitary_rejection_pct"],
            "riesgo_sanitario_detail": "Peso de defectos sanitarios dentro del rechazo total del período.",
            "exportacion_share_pct": summary["export_share_pct"],
            "exportacion_delta_pct": round(summary["export_share_pct"] - previous["export_share_pct"], 2),
            "exportacion_detail": "Parte del volumen clasificado que sostiene el canal exportador.",
            "industria_share_pct": summary["industry_share_pct"],
            "descarte_share_pct": summary["discard_share_pct"],
            "calibre_exportable_pct": summary["exportable_calibre_pct"],
            "calibre_exportable_detail": "Participación de calibres aptos para exportación sobre el volumen clasificado.",
            "trazabilidad_pct": summary["traceability_pct"],
            "trazabilidad_detail": "Cobertura de lote, campo, establecimiento y variedad en fruta procesada.",
            "lotes_criticos": summary["critical_lots"],
            "lotes_fuera_tolerancia": summary["critical_lots"],
            "lotes_criticos_delta_pct": round(summary["critical_lots"] - previous["critical_lots"], 2),
            "packout_objetivo_pct": summary["target_packout_pct"],
        },
        "series": {
            "calidad_diaria": current["series"],
        },
        "breakdown": {
            "packout_lotes": current["lot_rows"],
            "destino_fruta": current["destination_rows"],
            "calibres_exportacion": current["calibre_rows"],
            "defectos_tipo": current["defect_rows"],
            "ranking_rechazo": current["ranking_rows"],
        },
        "analysis": {
            "proyeccion_packout": build_linear_projection_daily(projection_base, "fecha", "packout_pct", periods=14),
            "desvio_vs_objetivo": current["deviation_rows"],
            "sensibilidad": [
                {"escenario": "+2 pts packout", "impacto_tn_utiles": round(summary["received_kg"] * 0.02 / 1000.0, 2)},
                {"escenario": "-2 pts packout", "impacto_tn_utiles": round(summary["received_kg"] * -0.02 / 1000.0, 2)},
                {"escenario": "-2 pts rechazo", "impacto_tn_utiles": round(summary["received_kg"] * 0.02 / 1000.0, 2)},
                {"escenario": "+5 pts exportación", "impacto_tn_exportables": round(summary["received_kg"] * 0.05 / 1000.0, 2)},
            ],
            "insights": [
                {
                    "titulo": "Lectura de packout",
                    "descripcion": (
                        "La calidad útil viene sosteniendo el objetivo de campaña."
                        if summary["packout_pct"] >= summary["target_packout_pct"]
                        else "El packout útil sigue abajo del objetivo y conviene priorizar lotes más sanos."
                    ),
                    "severity": "success" if summary["packout_pct"] >= summary["target_packout_pct"] else "warning",
                },
                {
                    "titulo": "Presión de rechazo",
                    "descripcion": f"El rechazo acumula {summary['rejection_pct']:.1f}% del volumen recibido.",
                    "severity": "warning" if summary["rejection_pct"] >= 12 else "info",
                },
                {
                    "titulo": "Mix de destino",
                    "descripcion": f"Exportación concentra {summary['export_share_pct']:.1f}% y la industria {summary['industry_share_pct']:.1f}% del volumen clasificado.",
                    "severity": "info",
                },
                {
                    "titulo": "Focos críticos",
                    "descripcion": f"{summary['critical_lots']} lotes concentran la mayor parte del deterioro de calidad.",
                    "severity": "warning" if summary["critical_lots"] > 0 else "success",
                },
            ],
        },
        "alerts": [
            {
                "id": "packout-bajo",
                "prioridad": "alta" if summary["packout_pct"] < summary["target_packout_pct"] - 4 else "media",
                "severidad": "warning" if summary["packout_pct"] < summary["target_packout_pct"] else "success",
                "titulo": "Packout útil bajo objetivo" if summary["packout_pct"] < summary["target_packout_pct"] else "Packout útil dentro de rango",
                "impacto": f"{summary['packout_pct']:.1f}% vs meta {summary['target_packout_pct']:.1f}%.",
                "modulo": "Calidad de Fruta",
                "detalle": current["ranking_rows"][0]["lote"] if current["ranking_rows"] else "Seguimiento semanal",
                "accion": "Priorizar lotes con mejor condición y revisar defectos dominantes.",
            },
            {
                "id": "rechazo-alto",
                "prioridad": "alta" if summary["rejection_pct"] >= 18 else "media" if summary["rejection_pct"] >= 12 else "baja",
                "severidad": "warning" if summary["rejection_pct"] >= 12 else "info",
                "titulo": "Rechazo crítico" if summary["rejection_pct"] >= 18 else "Rechazo por encima de referencia" if summary["rejection_pct"] >= 12 else "Rechazo controlado",
                "impacto": f"{summary['rejection_pct']:.1f}% del volumen recibido ya quedó rechazado.",
                "modulo": "Calidad de Fruta",
                "detalle": current["alerts_source"]["defects"][0]["defecto"] if current["alerts_source"]["defects"] else "Sin defecto dominante",
                "accion": "Corregir el defecto dominante y revisar manejo de cosecha.",
            },
            {
                "id": "mix-industria",
                "prioridad": "media" if summary["industry_share_pct"] >= 60 else "baja",
                "severidad": "warning" if summary["industry_share_pct"] >= 60 else "info",
                "titulo": "Mayor derivación a industria" if summary["industry_share_pct"] >= 60 else "Mix de industria en rango",
                "impacto": f"{summary['industry_share_pct']:.1f}% del volumen clasificado va a industria.",
                "modulo": "Comercial / Exportación",
                "detalle": "Revisar si el mix responde a mercado o a calidad.",
                "accion": "Separar problemas de mercado de problemas reales de calidad.",
            },
            {
                "id": "lotes-criticos",
                "prioridad": "alta" if summary["critical_lots"] >= 4 else "media",
                "severidad": "critical" if summary["critical_lots"] >= 4 else "warning",
                "titulo": "Lotes críticos por calidad",
                "impacto": f"{summary['critical_lots']} lotes quedan fuera de rango por packout o rechazo.",
                "modulo": "Producción / Calidad",
                "detalle": current["alerts_source"]["critical"][0]["lote"] if current["alerts_source"]["critical"] else "Sin foco crítico",
                "accion": "Definir secuencia de corte y destino lote por lote.",
            },
        ],
    }
