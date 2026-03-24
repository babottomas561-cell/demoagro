from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_commercial import PresupuestoLoteFact, PrecioVentaFact
from app.models.lemon_external import TipoCambioFact
from app.models.lemon_field import (
    CosechaFact,
    LoteCampaniaFact,
    RequerimientoHidricoFact,
    RendimientoLoteFact,
    ScoutingFact,
)
from app.models.lemon_quality import PackoutFact, RecepcionFrutaFact
from app.services.lemon_panel_utils import (
    LemonFilters,
    get_fase_campania,
    load_scope_rows,
    recent_window_start,
    resolve_campaign_pair,
    resolve_previous_window,
    resolve_time_window,
    week_start,
)


@dataclass
class ProductionLotMeta:
    lote_campania_id: int
    lote: str
    codigo_lote: str
    campo: str
    establecimiento: str
    variedad: str
    superficie_ha: float
    fecha_inicio_estimada: date | None
    fecha_fin_estimada: date | None
    objetivo_kg_ha: float
    objetivo_packout_pct: float


def _safe_float(value: float | None) -> float:
    return float(value or 0)


def _safe_pct(current: float, base: float) -> float:
    if not base:
        return 0.0
    return round(((current - base) / base) * 100, 2)


def _ratio(value: float, base: float) -> float:
    if not base:
        return 0.0
    return value / base


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _daterange(start: date, end: date) -> Iterable[date]:
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def _month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def _weighted_price_lookup(rows: list[PrecioVentaFact]) -> dict[date, float]:
    grouped: dict[date, dict[str, float]] = defaultdict(lambda: {"importe": 0.0, "volumen": 0.0})
    for row in rows:
        key = week_start(row.fecha)
        volume = max(_safe_float(row.volumen_kg), 1)
        grouped[key]["importe"] += _safe_float(row.precio_promedio_usd_tn) * volume
        grouped[key]["volumen"] += volume
    return {
        key: values["importe"] / values["volumen"]
        for key, values in grouped.items()
        if values["volumen"] > 0
    }


def _fx_lookup(rows: list[TipoCambioFact]) -> dict[date, float]:
    return {week_start(row.fecha): _safe_float(row.exportacion or row.mayorista or row.oficial) for row in rows}


def _nearest_week_value(lookup: dict[date, float], value_date: date) -> float:
    probe = week_start(value_date)
    for _ in range(0, 12):
        value = lookup.get(probe)
        if value is not None:
            return value
        probe -= timedelta(days=7)
    candidates = [value for row_date, value in lookup.items() if row_date <= value_date]
    return candidates[-1] if candidates else 0.0


async def _load_production_meta(
    db: AsyncSession,
    filters: LemonFilters,
    campania_id: int,
) -> list[ProductionLotMeta]:
    rows = await load_scope_rows(db, filters, campania_id)
    result: list[ProductionLotMeta] = []
    for lot_campaign, lote, campo, establecimiento, variedad in rows:
        result.append(
            ProductionLotMeta(
                lote_campania_id=lot_campaign.lote_campania_id,
                lote=lote.nombre,
                codigo_lote=lote.codigo,
                campo=campo.nombre,
                establecimiento=establecimiento.nombre,
                variedad=variedad.nombre,
                superficie_ha=_safe_float(lot_campaign.superficie_ha),
                fecha_inicio_estimada=lot_campaign.fecha_inicio_cosecha_estimada,
                fecha_fin_estimada=lot_campaign.fecha_fin_cosecha_estimada,
                objetivo_kg_ha=_safe_float(lot_campaign.objetivo_kg_ha),
                objetivo_packout_pct=_safe_float(lot_campaign.objetivo_packout_pct),
            )
        )
    return result


def _expected_share(meta: ProductionLotMeta, current_date: date, campaign_start: date, campaign_end: date) -> float:
    start = meta.fecha_inicio_estimada or campaign_start
    end = meta.fecha_fin_estimada or campaign_end
    if current_date < start:
        return 0.0
    if current_date >= end:
        return 1.0
    total_days = max((end - start).days + 1, 1)
    elapsed_days = max((current_date - start).days + 1, 0)
    return _clamp(elapsed_days / total_days, 0.0, 1.0)


async def _build_snapshot(
    db: AsyncSession,
    filters: LemonFilters,
    campania_id: int,
    campaign_start: date,
    campaign_end: date,
    window_start: date,
    cut_off: date,
) -> dict:
    lot_meta = await _load_production_meta(db, filters, campania_id)
    if not lot_meta:
        return {
            "meta": [],
            "summary": {
                "harvested_kg": 0.0,
                "plan_kg": 0.0,
                "progress_pct": 0.0,
                "projected_kg_ha": 0.0,
                "packout_pct": 0.0,
                "under_target_lots": 0,
                "hydric_risk_lots": 0,
                "surface_ha": 0.0,
                "total_jornales": 0.0,
                "total_costo": 0.0,
            },
            "series": [],
            "lots": [],
            "bottom_lots": [],
            "variety_establishment": [],
            "heatmap": [],
            "deviation_rows": [],
            "alerts_source": {"water": [], "scouting": [], "delay": []},
            "last_date": cut_off,
        }

    lot_campaign_ids = [item.lote_campania_id for item in lot_meta]
    meta_by_lot = {item.lote_campania_id: item for item in lot_meta}

    harvest_rows = (
        await db.execute(
            select(CosechaFact)
            .where(CosechaFact.lote_campania_id.in_(lot_campaign_ids))
            .where(CosechaFact.fecha_cosecha >= window_start)
            .where(CosechaFact.fecha_cosecha <= cut_off)
            .order_by(CosechaFact.fecha_cosecha)
        )
    ).scalars().all()
    yield_rows = (
        await db.execute(
            select(RendimientoLoteFact)
            .where(RendimientoLoteFact.lote_campania_id.in_(lot_campaign_ids))
        )
    ).scalars().all()
    budget_rows = (
        await db.execute(
            select(PresupuestoLoteFact)
            .where(PresupuestoLoteFact.lote_campania_id.in_(lot_campaign_ids))
        )
    ).scalars().all()
    water_rows = (
        await db.execute(
            select(RequerimientoHidricoFact)
            .where(RequerimientoHidricoFact.lote_campania_id.in_(lot_campaign_ids))
            .where(RequerimientoHidricoFact.fecha >= window_start)
            .where(RequerimientoHidricoFact.fecha <= cut_off)
            .order_by(RequerimientoHidricoFact.fecha.desc())
        )
    ).scalars().all()
    scouting_rows = (
        await db.execute(
            select(ScoutingFact)
            .where(ScoutingFact.lote_campania_id.in_(lot_campaign_ids))
            .where(ScoutingFact.fecha_evento <= cut_off)
            .where(ScoutingFact.fecha_evento >= recent_window_start(window_start, cut_off, 45))
            .order_by(ScoutingFact.fecha_evento.desc())
        )
    ).scalars().all()
    packout_rows = (
        await db.execute(
            select(PackoutFact, RecepcionFrutaFact)
            .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .where(RecepcionFrutaFact.lote_campania_id.in_(lot_campaign_ids))
            .where(PackoutFact.fecha_proceso >= window_start)
            .where(PackoutFact.fecha_proceso <= cut_off)
        )
    ).all()
    price_rows = (await db.execute(select(PrecioVentaFact).where(PrecioVentaFact.fecha <= cut_off))).scalars().all()
    fx_rows = (await db.execute(select(TipoCambioFact).where(TipoCambioFact.fecha <= cut_off))).scalars().all()

    lot_state: dict[int, dict[str, float | str]] = {}
    for meta in lot_meta:
        lot_state[meta.lote_campania_id] = {
            "lote_campania_id": meta.lote_campania_id,
            "lote": meta.lote,
            "codigo_lote": meta.codigo_lote,
            "campo": meta.campo,
            "establecimiento": meta.establecimiento,
            "variedad": meta.variedad,
            "superficie_ha": meta.superficie_ha,
            "objetivo_kg_ha": meta.objetivo_kg_ha,
            "objetivo_packout_pct": meta.objetivo_packout_pct,
            "harvested_kg": 0.0,
            "projected_kg": 0.0,
            "plan_kg": 0.0,
            "packout_pct": 0.0,
            "exportable_pct": 0.0,
            "margin_impact_ars": 0.0,
        }

    budget_by_lot = {row.lote_campania_id: row for row in budget_rows}
    yield_by_lot = {row.lote_campania_id: row for row in yield_rows}
    price_lookup = _weighted_price_lookup(price_rows)
    fx_lookup = _fx_lookup(fx_rows)

    daily_harvest: dict[date, float] = defaultdict(float)
    total_jornales: float = 0.0
    total_costo: float = 0.0
    last_dates = [campaign_start]
    for row in harvest_rows:
        lot_state[row.lote_campania_id]["harvested_kg"] += _safe_float(row.kg_cosechados)
        daily_harvest[row.fecha_cosecha] += _safe_float(row.kg_cosechados)
        total_jornales += _safe_float(row.jornales)
        total_costo += _safe_float(row.costo_cosecha_ars)
        last_dates.append(row.fecha_cosecha)

    packout_by_lot: dict[int, dict[str, float]] = defaultdict(lambda: {"entrada": 0.0, "salida": 0.0})
    for packout, recepcion in packout_rows:
        packout_by_lot[recepcion.lote_campania_id]["entrada"] += _safe_float(packout.kg_entrada)
        packout_by_lot[recepcion.lote_campania_id]["salida"] += _safe_float(packout.kg_salida)
        last_dates.append(packout.fecha_proceso)

    latest_water_by_lot: dict[int, RequerimientoHidricoFact] = {}
    for row in water_rows:
        latest_water_by_lot.setdefault(row.lote_campania_id, row)

    latest_scout_by_lot: dict[int, ScoutingFact] = {}
    for row in scouting_rows:
        latest_scout_by_lot.setdefault(row.lote_campania_id, row)

    for meta in lot_meta:
        budget = budget_by_lot.get(meta.lote_campania_id)
        campaign_plan_kg = _safe_float(budget.kg_plan) if budget else meta.objetivo_kg_ha * meta.superficie_ha
        base_share = _expected_share(meta, window_start - timedelta(days=1), campaign_start, campaign_end)
        progress_share = _expected_share(meta, cut_off, campaign_start, campaign_end)
        window_progress_share = max(progress_share - base_share, 0.0)
        window_plan_kg = campaign_plan_kg * window_progress_share
        lot_state[meta.lote_campania_id]["plan_kg"] = window_plan_kg
        harvested_kg = _safe_float(lot_state[meta.lote_campania_id]["harvested_kg"])
        if harvested_kg > 0 and window_progress_share > 0.08:
            projected_kg = min(
                harvested_kg / window_progress_share,
                campaign_plan_kg * 1.2 if campaign_plan_kg else harvested_kg * 1.2,
            )
        else:
            projected_kg = campaign_plan_kg * max(window_progress_share, 0.2) if window_progress_share > 0 else 0.0
        lot_state[meta.lote_campania_id]["projected_kg"] = projected_kg

        yield_fact = yield_by_lot.get(meta.lote_campania_id)
        if yield_fact:
            lot_state[meta.lote_campania_id]["exportable_pct"] = round(_safe_float(yield_fact.fruta_exportable_pct), 1)
            lot_state[meta.lote_campania_id]["packout_pct"] = round(_safe_float(yield_fact.fruta_exportable_pct), 1)
        else:
            packout = packout_by_lot.get(meta.lote_campania_id)
            if packout and packout["entrada"] > 0:
                lot_state[meta.lote_campania_id]["packout_pct"] = round(packout["salida"] / packout["entrada"] * 100, 1)

        average_price = _nearest_week_value(price_lookup, cut_off)
        average_fx = _nearest_week_value(fx_lookup, cut_off)
        value_ars = (projected_kg / 1000.0) * average_price * average_fx
        lot_state[meta.lote_campania_id]["margin_impact_ars"] = round(value_ars * 0.18, 2)

    total_surface = round(sum(meta.superficie_ha for meta in lot_meta), 2)
    total_harvest = round(sum(_safe_float(row["harvested_kg"]) for row in lot_state.values()), 2)
    total_plan = round(sum(_safe_float(row["plan_kg"]) for row in lot_state.values()), 2)
    total_projected = round(sum(_safe_float(row["projected_kg"]) for row in lot_state.values()), 2)
    average_packout_target = round(mean([meta.objetivo_packout_pct for meta in lot_meta if meta.objetivo_packout_pct > 0]) if lot_meta else 0.0, 1)
    weighted_packout = sum(
        _safe_float(state["packout_pct"]) * max(_safe_float(state["harvested_kg"]), _safe_float(state["projected_kg"]))
        for state in lot_state.values()
    )
    weighted_base = sum(max(_safe_float(state["harvested_kg"]), _safe_float(state["projected_kg"])) for state in lot_state.values())
    packout_pct = round(weighted_packout / weighted_base, 1) if weighted_base else 0.0

    cumulative_harvest = 0.0
    series = []
    baseline_date = window_start - timedelta(days=1)
    for current_date in _daterange(window_start, max(last_dates)):
        cumulative_harvest += daily_harvest.get(current_date, 0.0)
        plan_cumulative = 0.0
        for meta in lot_meta:
            plan_total = _safe_float(lot_state[meta.lote_campania_id]["plan_kg"])
            end_share = _expected_share(meta, current_date, campaign_start, campaign_end)
            start_share = _expected_share(meta, baseline_date, campaign_start, campaign_end)
            delta_share = max(end_share - start_share, 0.0)
            planned_window_total = _safe_float(budget_by_lot.get(meta.lote_campania_id).kg_plan) if budget_by_lot.get(meta.lote_campania_id) else meta.objetivo_kg_ha * meta.superficie_ha
            plan_cumulative += planned_window_total * delta_share
        series.append(
            {
                "fecha": current_date.isoformat(),
                "kg_cosechados": round(daily_harvest.get(current_date, 0.0), 2),
                "kg_acumulados": round(cumulative_harvest, 2),
                "kg_plan_acumulado": round(plan_cumulative, 2),
                "desvio_acumulado_kg": round(cumulative_harvest - plan_cumulative, 2),
            }
        )

    lot_rows = []
    for meta in lot_meta:
        state = lot_state[meta.lote_campania_id]
        projected_kg_ha = _safe_float(state["projected_kg"]) / max(meta.superficie_ha, 1)
        harvested_kg_ha = _safe_float(state["harvested_kg"]) / max(meta.superficie_ha, 1)
        deviation_pct = _safe_pct(projected_kg_ha, meta.objetivo_kg_ha) if meta.objetivo_kg_ha else 0.0
        lot_rows.append(
            {
                "lote_campania_id": meta.lote_campania_id,
                "lote": meta.lote,
                "codigo_lote": meta.codigo_lote,
                "campo": meta.campo,
                "establecimiento": meta.establecimiento,
                "variedad": meta.variedad,
                "superficie_ha": round(meta.superficie_ha, 1),
                "kg_cosechados": round(_safe_float(state["harvested_kg"]), 2),
                "kg_cosechados_tn": round(_safe_float(state["harvested_kg"]) / 1000.0, 2),
                "kg_ha_actual": round(harvested_kg_ha, 1),
                "kg_ha_proyectado": round(projected_kg_ha, 1),
                "objetivo_kg_ha": round(meta.objetivo_kg_ha, 1),
                "desvio_pct": round(deviation_pct, 2),
                "packout_pct": round(_safe_float(state["packout_pct"]), 1),
                "impacto_margen_ars": round(_safe_float(state["margin_impact_ars"]), 2),
            }
        )

    variety_establishment_map: dict[tuple[str, str], dict[str, float | str]] = defaultdict(
        lambda: {"establecimiento": "", "variedad": "", "kg_cosechados_tn": 0.0, "kg_plan_tn": 0.0}
    )
    for row in lot_rows:
        key = (row["establecimiento"], row["variedad"])
        bucket = variety_establishment_map[key]
        bucket["establecimiento"] = row["establecimiento"]
        bucket["variedad"] = row["variedad"]
        bucket["kg_cosechados_tn"] += row["kg_cosechados_tn"]
        bucket["kg_plan_tn"] += round(_safe_float(lot_state[row["lote_campania_id"]]["plan_kg"]) / 1000.0, 2)

    water_risk = []
    for lc_id, row in latest_water_by_lot.items():
        meta = meta_by_lot[lc_id]
        water_risk.append(
            {
                "lote": meta.lote,
                "establecimiento": meta.establecimiento,
                "estado": row.estado,
                "balance_hidrico_m3": round(_safe_float(row.balance_hidrico_m3), 2),
                "fecha": row.fecha.isoformat(),
            }
        )
    scouting_risk = []
    for lc_id, row in latest_scout_by_lot.items():
        meta = meta_by_lot[lc_id]
        scouting_risk.append(
            {
                "lote": meta.lote,
                "establecimiento": meta.establecimiento,
                "severidad": row.severidad,
                "incidencia_pct": round(_safe_float(row.incidencia_pct), 2),
                "fecha": row.fecha_evento.isoformat(),
                "alerta": bool(row.alerta),
            }
        )

    delayed_lots = []
    for meta in lot_meta:
        harvested = _safe_float(lot_state[meta.lote_campania_id]["harvested_kg"])
        if meta.fecha_inicio_estimada and cut_off > meta.fecha_inicio_estimada + timedelta(days=10) and harvested <= 0:
            delayed_lots.append(
                {
                    "lote": meta.lote,
                    "establecimiento": meta.establecimiento,
                    "fecha_inicio_estimada": meta.fecha_inicio_estimada.isoformat(),
                    "dias_atraso": (cut_off - meta.fecha_inicio_estimada).days,
                }
            )

    under_target_lots = [row for row in lot_rows if row["desvio_pct"] <= -10]
    hydric_risk_lots = [row for row in water_risk if row["estado"] != "normal" and row["balance_hidrico_m3"] <= -6000]
    return {
        "meta": lot_meta,
        "summary": {
            "harvested_kg": total_harvest,
            "plan_kg": total_plan,
            "progress_pct": round(_ratio(total_harvest, total_plan) * 100, 1) if total_plan else 0.0,
            "projected_kg_ha": round(total_projected / max(total_surface, 1), 1),
            "packout_pct": packout_pct,
            "packout_target_pct": average_packout_target,
            "under_target_lots": len(under_target_lots),
            "hydric_risk_lots": len(hydric_risk_lots),
            "surface_ha": total_surface,
            "total_jornales": total_jornales,
            "total_costo": total_costo,
        },
        "series": series,
        "lots": sorted(lot_rows, key=lambda item: item["kg_ha_proyectado"], reverse=True),
        "bottom_lots": sorted(lot_rows, key=lambda item: item["desvio_pct"])[:8],
        "variety_establishment": sorted(variety_establishment_map.values(), key=lambda item: (_safe_float(item["kg_cosechados_tn"]), item["establecimiento"]), reverse=True),
        "heatmap": sorted(lot_rows, key=lambda item: item["kg_ha_proyectado"], reverse=True),
        "deviation_rows": sorted(lot_rows, key=lambda item: item["desvio_pct"]),
        "alerts_source": {
            "water": hydric_risk_lots,
            "scouting": [row for row in scouting_risk if row["severidad"] in {"alta", "media"}],
            "delay": delayed_lots,
        },
        "last_date": max(last_dates),
    }


def _build_projection(series_rows: list[dict]) -> list[dict]:
    if not series_rows:
        return []
    historical = [
        {"fecha": row["fecha"], "kg_acumulados": row["kg_acumulados"], "tipo": "historico"}
        for row in series_rows
    ]
    recent = series_rows[-14:] if len(series_rows) >= 14 else series_rows
    if len(recent) < 3:
        return historical
    pace = (recent[-1]["kg_acumulados"] - recent[0]["kg_acumulados"]) / max(len(recent) - 1, 1)
    base_date = date.fromisoformat(series_rows[-1]["fecha"])
    base_value = series_rows[-1]["kg_acumulados"]
    for step in range(1, 22):
        future_date = base_date + timedelta(days=step)
        historical.append(
            {
                "fecha": future_date.isoformat(),
                "kg_acumulados": round(base_value + pace * step, 2),
                "tipo": "proyeccion",
            }
        )
    return historical


async def get_produccion_campo(
    db: AsyncSession,
    filters: LemonFilters,
) -> dict:
    campaign_pair = await resolve_campaign_pair(db, filters.campania_id)
    current_campaign = campaign_pair.current
    current_window_start, cut_off, _ = resolve_time_window(
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        filters,
    )
    current_snapshot = await _build_snapshot(
        db,
        filters,
        current_campaign.campania_id,
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        current_window_start,
        cut_off,
    )

    previous_summary = None
    if campaign_pair.previous:
        previous_window_start, previous_cut_off = resolve_previous_window(
            current_window_start,
            cut_off,
            current_campaign,
            campaign_pair.previous,
        )
        previous_snapshot = await _build_snapshot(
            db,
            filters,
            campaign_pair.previous.campania_id,
            campaign_pair.previous.fecha_inicio,
            campaign_pair.previous.fecha_fin,
            previous_window_start,
            previous_cut_off,
        )
        previous_summary = previous_snapshot["summary"]

    previous = previous_summary or {
        "harvested_kg": 0.0,
        "progress_pct": 0.0,
        "projected_kg_ha": 0.0,
        "packout_pct": 0.0,
        "under_target_lots": 0,
        "total_jornales": 0.0,
        "total_costo": 0.0,
    }
    summary = current_snapshot["summary"]

    deviation_rows = [
        {
            "lote": row["lote"],
            "establecimiento": row["establecimiento"],
            "kg_ha_proyectado": row["kg_ha_proyectado"],
            "objetivo_kg_ha": row["objetivo_kg_ha"],
            "desvio_pct": row["desvio_pct"],
        }
        for row in current_snapshot["deviation_rows"][:10]
    ]

    sensitivity_base = sum(item["impacto_margen_ars"] for item in current_snapshot["lots"])

    return {
        "meta": {
            "campania": current_campaign.nombre,
            "campania_id": current_campaign.campania_id,
            "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
            "scope_lotes": len(current_snapshot["meta"]),
            "scope_superficie_ha": summary["surface_ha"],
            "source": "ERP limonero · cosecha, calidad y rinde proyectado",
            "last_updated": current_snapshot["last_date"].isoformat(),
            "fase_campania": get_fase_campania(current_snapshot["last_date"]),
        },
        "summary": {
            "kg_cosechados": round(summary["harvested_kg"], 2),
            "kg_cosechados_delta_pct": _safe_pct(summary["harvested_kg"], previous["harvested_kg"]),
            "kg_cosechados_detail": "Volumen ya levantado en finca dentro de la campaña filtrada.",
            "avance_cosecha_pct": round(summary["progress_pct"], 1),
            "avance_cosecha_delta_pct": round(summary["progress_pct"] - previous["progress_pct"], 2),
            "avance_cosecha_detail": "Mide cuánto de la cosecha planificada ya pasó por finca.",
            "rendimiento_proyectado_kg_ha": round(summary["projected_kg_ha"], 1),
            "rendimiento_proyectado_delta_pct": _safe_pct(summary["projected_kg_ha"], previous["projected_kg_ha"]),
            "rendimiento_proyectado_detail": "Proyección de kg/ha al cierre según avance real y ventana de cosecha.",
            "packout_promedio_pct": round(summary["packout_pct"], 1),
            "packout_objetivo_pct": round(summary["packout_target_pct"], 1),
            "packout_promedio_delta_pct": round(summary["packout_pct"] - previous["packout_pct"], 2),
            "packout_promedio_detail": "Porcentaje exportable ponderado del volumen proyectado en el scope filtrado.",
            "lotes_bajo_objetivo": summary["under_target_lots"],
            "lotes_bajo_objetivo_delta_pct": round(summary["under_target_lots"] - previous["under_target_lots"], 2),
            "lotes_bajo_objetivo_detail": "Cantidad de lotes proyectados al menos 10% debajo del objetivo.",
            "lotes_atrasados": len(current_snapshot["alerts_source"]["delay"]),
            "lotes_riesgo_hidrico": summary["hydric_risk_lots"],
            "plan_kg": round(summary["plan_kg"], 2),
            "kg_jornalero": round(summary["harvested_kg"] / max(summary["total_jornales"], 1), 1),
            "kg_jornalero_delta_pct": _safe_pct(
                summary["harvested_kg"] / max(summary["total_jornales"], 1),
                previous["harvested_kg"] / max(previous["total_jornales"], 1) if previous.get("total_jornales") else 0.0,
            ),
            "kg_jornalero_detail": "Productividad laboral de cosecha. Referencia industria: 2.000–2.500 kg/jornalero/día.",
            "costo_kg_ars": round(summary["total_costo"] / max(summary["harvested_kg"], 1), 2),
            "costo_kg_ars_delta_pct": _safe_pct(
                summary["total_costo"] / max(summary["harvested_kg"], 1),
                previous["total_costo"] / max(previous["harvested_kg"], 1) if previous.get("harvested_kg") else 0.0,
            ),
            "costo_kg_ars_detail": "Costo directo de cosecha por kg. Clave para controlar el margen operativo.",
        },
        "series": {
            "cosecha_diaria": current_snapshot["series"],
        },
        "breakdown": {
            "rendimiento_lotes": current_snapshot["lots"][:12],
            "produccion_variedad_establecimiento": current_snapshot["variety_establishment"],
            "ranking_bajo_rendimiento": current_snapshot["bottom_lots"],
            "heatmap_rendimiento": current_snapshot["heatmap"],
        },
        "analysis": {
            "proyeccion_cosecha": _build_projection(current_snapshot["series"]),
            "desvio_vs_objetivo": deviation_rows,
            "sensibilidad": [
                {"escenario": "-5% rinde", "impacto_margen_ars": round(sensitivity_base * -0.05, 2)},
                {"escenario": "+5% rinde", "impacto_margen_ars": round(sensitivity_base * 0.05, 2)},
                {"escenario": "-3 pts packout", "impacto_margen_ars": round(sensitivity_base * -0.03, 2)},
                {"escenario": "+2 semanas demora", "impacto_margen_ars": round(sensitivity_base * -0.025, 2)},
            ],
            "insights": [
                {
                    "titulo": "Avance de cosecha",
                    "descripcion": (
                        "El avance va por delante del plan."
                        if summary["progress_pct"] >= 100
                        else "La cosecha todavía corre por debajo del plan acumulado."
                    ),
                    "severity": "success" if summary["progress_pct"] >= 100 else "warning",
                },
                {
                    "titulo": "Rinde proyectado",
                    "descripcion": (
                        f"El rinde proyectado ({summary['projected_kg_ha']:.0f} kg/ha) supera las 18 tn/ha — campaña sólida para Tucumán."
                        if summary["projected_kg_ha"] >= 18000
                        else f"El rinde proyectado ({summary['projected_kg_ha']:.0f} kg/ha) está en rango medio (12-18 tn/ha). Seguimiento lote por lote."
                        if summary["projected_kg_ha"] >= 12000
                        else f"El rinde proyectado ({summary['projected_kg_ha']:.0f} kg/ha) es bajo para la región — objetivo mínimo: 12 tn/ha."
                    ),
                    "severity": "success" if summary["projected_kg_ha"] >= 18000 else "warning" if summary["projected_kg_ha"] >= 12000 else "danger",
                },
                {
                    "titulo": "Lotes bajo objetivo",
                    "descripcion": f"{summary['under_target_lots']} lotes quedan al menos 10% debajo del objetivo si no se corrige el desvío.",
                    "severity": "warning" if summary["under_target_lots"] > 0 else "success",
                },
                {
                    "titulo": "Productividad laboral",
                    "descripcion": (
                        f"Productividad de cosecha en {summary['harvested_kg'] / max(summary['total_jornales'], 1):,.0f} kg/jornalero — dentro del benchmark industria (2.000–2.500 kg/día)."
                        if 2000 <= summary["harvested_kg"] / max(summary["total_jornales"], 1) <= 2500
                        else f"Productividad de cosecha en {summary['harvested_kg'] / max(summary['total_jornales'], 1):,.0f} kg/jornalero — por debajo del mínimo de 2.000 kg/día. Revisar cuadrillas, logística o condición de fruta."
                        if summary["harvested_kg"] / max(summary["total_jornales"], 1) < 2000
                        else f"Productividad de cosecha en {summary['harvested_kg'] / max(summary['total_jornales'], 1):,.0f} kg/jornalero — por encima del benchmark. Buenas condiciones operativas."
                    ),
                    "severity": (
                        "success" if summary["harvested_kg"] / max(summary["total_jornales"], 1) >= 2000
                        else "warning" if summary["harvested_kg"] / max(summary["total_jornales"], 1) >= 1500
                        else "danger"
                    ),
                },
                {
                    "titulo": "Riesgo hídrico",
                    "descripcion": f"{summary['hydric_risk_lots']} lotes muestran balance hídrico fuera de rango en la última medición.",
                    "severity": "warning" if summary["hydric_risk_lots"] > 0 else "success",
                },
            ],
        },
        "alerts": [
            {
                "id": "bajo-objetivo",
                "prioridad": "alta" if current_snapshot["alerts_source"]["delay"] else "media",
                "severidad": "warning" if summary["under_target_lots"] > 0 else "success",
                "titulo": "Lotes bajo objetivo",
                "impacto": f"{summary['under_target_lots']} lotes quedan por debajo del objetivo proyectado.",
                "modulo": "Producción de Campo",
                "detalle": current_snapshot["bottom_lots"][0]["lote"] if current_snapshot["bottom_lots"] else "Sin detalle",
                "accion": "Revisar primero los lotes de menor rinde proyectado y peor packout.",
            },
            {
                "id": "hidrico",
                "prioridad": "alta" if summary["hydric_risk_lots"] > 3 else "media",
                "severidad": "warning" if summary["hydric_risk_lots"] > 0 else "info",
                "titulo": "Lotes fuera de requerimiento hídrico",
                "impacto": f"{summary['hydric_risk_lots']} lotes recientes con déficit o exceso.",
                "modulo": "Riego y Fertirriego",
                "detalle": current_snapshot["alerts_source"]["water"][0]["lote"] if current_snapshot["alerts_source"]["water"] else "Monitoreo normal",
                "accion": "Ajustar láminas de riego y priorizar bloques con mayor balance negativo.",
            },
            {
                "id": "sanidad",
                "prioridad": "media",
                "severidad": "warning" if current_snapshot["alerts_source"]["scouting"] else "info",
                "titulo": "Eventos sanitarios recientes",
                "impacto": f"{len(current_snapshot['alerts_source']['scouting'])} lotes con scouting medio/alto en los últimos 45 días.",
                "modulo": "Sanidad y Monitoreo",
                "detalle": current_snapshot["alerts_source"]["scouting"][0]["lote"] if current_snapshot["alerts_source"]["scouting"] else "Sin foco crítico",
                "accion": "Incrementar seguimiento y tratamiento en los focos más severos.",
            },
            {
                "id": "kg-jornalero",
                "prioridad": "alta" if summary["harvested_kg"] / max(summary["total_jornales"], 1) < 1500 else "media" if summary["harvested_kg"] / max(summary["total_jornales"], 1) < 2000 else "baja",
                "severidad": "danger" if summary["harvested_kg"] / max(summary["total_jornales"], 1) < 1500 else "warning" if summary["harvested_kg"] / max(summary["total_jornales"], 1) < 2000 else "success",
                "titulo": (
                    "Productividad laboral crítica" if summary["harvested_kg"] / max(summary["total_jornales"], 1) < 1500
                    else "Productividad laboral bajo benchmark" if summary["harvested_kg"] / max(summary["total_jornales"], 1) < 2000
                    else "Productividad laboral en rango"
                ),
                "impacto": f"{summary['harvested_kg'] / max(summary['total_jornales'], 1):,.0f} kg/jornalero. Benchmark industria: 2.000–2.500 kg/día.",
                "modulo": "Producción de Campo",
                "detalle": "Verde ≥2.000 · Amarillo 1.500-2.000 · Rojo <1.500. Causas típicas: distancia al acopio, condición de fruta, calor extremo.",
                "accion": "Revisar distancia cuadrillas-acopio, reordenar sectores de cosecha y verificar cantidad efectiva de jornaleros por día.",
            },
            {
                "id": "demora",
                "prioridad": "alta" if current_snapshot["alerts_source"]["delay"] else "baja",
                "severidad": "critical" if current_snapshot["alerts_source"]["delay"] else "success",
                "titulo": "Ventana de cosecha atrasada",
                "impacto": f"{len(current_snapshot['alerts_source']['delay'])} lotes ya superan la fecha estimada sin cosecha relevante." if current_snapshot["alerts_source"]["delay"] else "No hay atrasos fuertes de arranque.",
                "modulo": "Producción de Campo",
                "detalle": current_snapshot["alerts_source"]["delay"][0]["lote"] if current_snapshot["alerts_source"]["delay"] else "Sin atraso",
                "accion": "Reasignar cuadrillas y priorizar lotes fuera de ventana.",
            },
        ],
    }
