from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_commercial import (
    CobranzasFact,
    ContratoVentaFact,
    CostosDirectosFact,
    CostosIndirectosFact,
    CuentasCobrarFact,
    EmbarqueFact,
    LiquidacionFact,
    PresupuestoLoteFact,
    PrecioVentaFact,
)
from app.models.lemon_dimensions import DestinoFrutaDim
from app.models.lemon_external import TipoCambioFact
from app.models.lemon_field import LoteCampaniaFact, RequerimientoHidricoFact, ScoutingFact
from app.models.lemon_packhouse import PackhouseTurnoFact
from app.models.lemon_quality import PackoutFact, RecepcionFrutaFact
from app.services.lemon_panel_utils import (
    LemonFilters,
    get_fase_campania,
    load_channel_maps,
    load_establishment_surface_map,
    load_scope_rows,
    month_key,
    recent_window_start,
    resolve_previous_window,
    resolve_campaign_pair,
    resolve_time_window,
    week_start,
)


DESTINATION_TO_CHANNEL = {
    "EXP": "FRESCO_EXP",
    "LOC": "FRESCO_LOC",
    "IND": "INDUSTRIA",
}


@dataclass
class LotMeta:
    lote_campania_id: int
    lote_id: int
    lote: str
    codigo_lote: str
    campo: str
    establecimiento: str
    establecimiento_id: int
    variedad: str
    superficie_ha: float
    objetivo_packout_pct: float
    objetivo_margen_ha: float


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


def _build_price_lookup(rows: list[PrecioVentaFact]) -> dict[tuple[date, int], float]:
    grouped: dict[tuple[date, int], dict[str, float]] = defaultdict(lambda: {"importe": 0.0, "volumen": 0.0})
    for row in rows:
        key = (week_start(row.fecha), row.canal_id)
        grouped[key]["importe"] += _safe_float(row.precio_promedio_usd_tn) * max(_safe_float(row.volumen_kg), 1)
        grouped[key]["volumen"] += max(_safe_float(row.volumen_kg), 1)
    return {
        key: values["importe"] / values["volumen"]
        for key, values in grouped.items()
        if values["volumen"] > 0
    }


def _nearest_channel_price(
    lookup: dict[tuple[date, int], float],
    value_date: date,
    canal_id: int,
) -> float:
    probe = week_start(value_date)
    for _ in range(0, 12):
        value = lookup.get((probe, canal_id))
        if value is not None:
            return value
        probe -= timedelta(days=7)
    candidates = [
        price
        for (row_date, row_channel_id), price in lookup.items()
        if row_channel_id == canal_id and row_date <= value_date
    ]
    return candidates[-1] if candidates else 0.0


def _build_fx_lookup(rows: list[TipoCambioFact]) -> dict[date, float]:
    return {week_start(row.fecha): _safe_float(row.exportacion or row.mayorista or row.oficial) for row in rows}


def _nearest_fx(lookup: dict[date, float], value_date: date) -> float:
    probe = week_start(value_date)
    for _ in range(0, 12):
        value = lookup.get(probe)
        if value is not None:
            return value
        probe -= timedelta(days=7)
    candidates = [value for row_date, value in lookup.items() if row_date <= value_date]
    return candidates[-1] if candidates else 0.0


def _kpi_status_margin(actual: float, budget: float) -> str:
    if actual <= 0:
        return "danger"
    if budget and actual < budget * 0.95:
        return "warning"
    return "success"


def _kpi_status_deviation(value_pct: float) -> str:
    if value_pct >= -2:
        return "success"
    if value_pct >= -8:
        return "warning"
    return "danger"


def _kpi_status_packout(actual_pct: float, target_pct: float) -> str:
    if actual_pct >= target_pct:
        return "success"
    if actual_pct >= target_pct - 4:
        return "warning"
    return "danger"


def _kpi_status_utilization(actual_pct: float, target_pct: float) -> str:
    if actual_pct >= target_pct:
        return "success"
    if actual_pct >= target_pct - 6:
        return "warning"
    return "danger"


async def _load_lot_metadata(
    db: AsyncSession,
    filters: LemonFilters,
    campania_id: int,
) -> list[LotMeta]:
    rows = await load_scope_rows(db, filters, campania_id)
    result: list[LotMeta] = []
    for lot_campaign, lote, campo, establecimiento, variedad in rows:
        result.append(
            LotMeta(
                lote_campania_id=lot_campaign.lote_campania_id,
                lote_id=lote.lote_id,
                lote=lote.nombre,
                codigo_lote=lote.codigo,
                campo=campo.nombre,
                establecimiento=establecimiento.nombre,
                establecimiento_id=establecimiento.establecimiento_id,
                variedad=variedad.nombre,
                superficie_ha=_safe_float(lot_campaign.superficie_ha),
                objetivo_packout_pct=_safe_float(lot_campaign.objetivo_packout_pct),
                objetivo_margen_ha=_safe_float(lot_campaign.objetivo_margen_ha),
            )
        )
    return result


async def _build_snapshot(
    db: AsyncSession,
    filters: LemonFilters,
    campania_id: int,
    campania_inicio: date,
    campania_fin: date,
    window_start: date,
    cut_off: date | None = None,
) -> dict:
    lot_meta = await _load_lot_metadata(db, filters, campania_id)
    if not lot_meta:
        return {
            "meta": [],
            "summary": {
                "revenue_ars": 0.0,
                "direct_costs_ars": 0.0,
                "indirect_costs_ars": 0.0,
                "margin_ars": 0.0,
                "margin_per_ha_ars": 0.0,
                "budget_margin_ars": 0.0,
                "budget_revenue_ars": 0.0,
                "budget_direct_costs_ars": 0.0,
                "budget_indirect_costs_ars": 0.0,
                "packout_pct": 0.0,
                "packout_target_pct": 0.0,
                "surface_ha": 0.0,
                "received_kg": 0.0,
                "commercial_kg": 0.0,
            },
            "daily": [],
            "lots": [],
            "establishments": [],
            "channels": [],
            "cost_categories": [],
            "recent_water": [],
            "recent_scouting": [],
            "packhouse_metrics": [],
            "last_date": cut_off or window_start,
        }

    cut_off_date = cut_off or campania_fin
    lot_campaign_ids = [item.lote_campania_id for item in lot_meta]
    establishment_ids = sorted({item.establecimiento_id for item in lot_meta})
    meta_by_lot = {item.lote_campania_id: item for item in lot_meta}
    surface_by_est_scope: dict[int, float] = defaultdict(float)
    for item in lot_meta:
        surface_by_est_scope[item.establecimiento_id] += item.superficie_ha
    surface_by_est_total = await load_establishment_surface_map(db, campania_id)

    packout_rows = (
        await db.execute(
            select(PackoutFact, RecepcionFrutaFact)
            .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .where(RecepcionFrutaFact.lote_campania_id.in_(lot_campaign_ids))
            .where(PackoutFact.fecha_proceso >= window_start)
            .where(PackoutFact.fecha_proceso <= cut_off_date)
            .order_by(PackoutFact.fecha_proceso)
        )
    ).all()
    direct_cost_rows = (
        await db.execute(
            select(CostosDirectosFact)
            .where(CostosDirectosFact.lote_campania_id.in_(lot_campaign_ids))
            .where(CostosDirectosFact.fecha >= window_start)
            .where(CostosDirectosFact.fecha <= cut_off_date)
            .order_by(CostosDirectosFact.fecha)
        )
    ).scalars().all()
    indirect_cost_rows = (
        await db.execute(
            select(CostosIndirectosFact)
            .where(CostosIndirectosFact.campania_id == campania_id)
            .where(CostosIndirectosFact.establecimiento_id.in_(establishment_ids))
            .where(CostosIndirectosFact.fecha >= window_start)
            .where(CostosIndirectosFact.fecha <= cut_off_date)
            .order_by(CostosIndirectosFact.fecha)
        )
    ).scalars().all()
    budget_rows = (
        await db.execute(
            select(PresupuestoLoteFact)
            .where(PresupuestoLoteFact.lote_campania_id.in_(lot_campaign_ids))
        )
    ).scalars().all()
    price_rows = (
        await db.execute(
            select(PrecioVentaFact)
            .where(PrecioVentaFact.fecha <= cut_off_date)
        )
    ).scalars().all()
    fx_rows = (
        await db.execute(
            select(TipoCambioFact)
            .where(TipoCambioFact.fecha <= cut_off_date)
        )
    ).scalars().all()
    water_rows = (
        await db.execute(
            select(RequerimientoHidricoFact)
            .where(RequerimientoHidricoFact.lote_campania_id.in_(lot_campaign_ids))
            .where(RequerimientoHidricoFact.fecha >= window_start)
            .where(RequerimientoHidricoFact.fecha <= cut_off_date)
            .order_by(RequerimientoHidricoFact.fecha.desc())
        )
    ).scalars().all()
    scouting_rows = (
        await db.execute(
            select(ScoutingFact)
            .where(ScoutingFact.lote_campania_id.in_(lot_campaign_ids))
            .where(ScoutingFact.fecha_evento <= cut_off_date)
            .where(ScoutingFact.fecha_evento >= recent_window_start(window_start, cut_off_date, 45))
            .order_by(ScoutingFact.fecha_evento.desc())
        )
    ).scalars().all()
    packhouse_rows = (
        await db.execute(
            select(PackhouseTurnoFact)
            .where(PackhouseTurnoFact.establecimiento_id.in_(establishment_ids))
            .where(PackhouseTurnoFact.fecha >= window_start)
            .where(PackhouseTurnoFact.fecha <= cut_off_date)
            .order_by(PackhouseTurnoFact.fecha)
        )
    ).scalars().all()

    maps = await load_channel_maps(db)
    destino_by_id = {item.destino_id: item for item in maps["destino_by_code"].values()}
    channel_lookup = maps["canal_by_code"]
    price_lookup = _build_price_lookup(price_rows)
    fx_lookup = _build_fx_lookup(fx_rows)

    lot_accumulator: dict[int, dict[str, float | str | int]] = {}
    for item in lot_meta:
        lot_accumulator[item.lote_campania_id] = {
            "lote_campania_id": item.lote_campania_id,
            "lote": item.lote,
            "codigo_lote": item.codigo_lote,
            "campo": item.campo,
            "establecimiento": item.establecimiento,
            "establecimiento_id": item.establecimiento_id,
            "variedad": item.variedad,
            "superficie_ha": item.superficie_ha,
            "target_packout_pct": item.objetivo_packout_pct,
            "target_margin_ha": item.objetivo_margen_ha,
            "revenue_ars": 0.0,
            "kg_packout": 0.0,
            "kg_received": 0.0,
            "direct_costs_ars": 0.0,
            "indirect_costs_ars": 0.0,
            "budget_margin_ars": 0.0,
            "budget_revenue_ars": 0.0,
        }

    daily_revenue: dict[date, float] = defaultdict(float)
    daily_costs: dict[date, float] = defaultdict(float)
    channel_rows: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {"channel": "", "revenue_ars": 0.0, "kg": 0.0}
    )
    last_dates = [campania_inicio]

    seen_receptions: set[int] = set()
    for packout, recepcion in packout_rows:
        lot = lot_accumulator.get(recepcion.lote_campania_id)
        if not lot:
            continue
        destino = destino_by_id.get(packout.destino_id)
        destino_code = destino.codigo if destino else ""
        channel_code = DESTINATION_TO_CHANNEL.get(destino_code)
        revenue_ars = 0.0
        if channel_code and channel_lookup.get(channel_code):
            channel = channel_lookup[channel_code]
            price_usd_tn = _nearest_channel_price(price_lookup, packout.fecha_proceso, channel.canal_id)
            fx_value = _nearest_fx(fx_lookup, packout.fecha_proceso)
            revenue_ars = (_safe_float(packout.kg_salida) / 1000.0) * price_usd_tn * fx_value
            channel_rows[channel.nombre]["channel"] = channel.nombre
            channel_rows[channel.nombre]["revenue_ars"] += revenue_ars
            channel_rows[channel.nombre]["kg"] += _safe_float(packout.kg_salida)
        lot["revenue_ars"] += revenue_ars
        lot["kg_packout"] += _safe_float(packout.kg_salida)
        if recepcion.recepcion_id not in seen_receptions:
            lot["kg_received"] += _safe_float(recepcion.kg_recibidos)
            seen_receptions.add(recepcion.recepcion_id)
        daily_revenue[packout.fecha_proceso] += revenue_ars
        last_dates.append(packout.fecha_proceso)

    cost_categories: dict[str, float] = defaultdict(float)
    for row in direct_cost_rows:
        amount = _safe_float(row.monto_ars)
        daily_costs[row.fecha] += amount
        cost_categories[f"Directo · {row.categoria.title()}"] += amount
        lot = lot_accumulator.get(row.lote_campania_id)
        if lot:
            lot["direct_costs_ars"] += amount
        last_dates.append(row.fecha)

    for row in indirect_cost_rows:
        est_total = _safe_float(surface_by_est_total.get(row.establecimiento_id))
        scope_surface = _safe_float(surface_by_est_scope.get(row.establecimiento_id))
        if est_total <= 0 or scope_surface <= 0:
            continue
        scoped_amount = _safe_float(row.monto_ars) * _ratio(scope_surface, est_total)
        daily_costs[row.fecha] += scoped_amount
        cost_categories[f"Indirecto · {row.categoria.title()}"] += scoped_amount
        for item in lot_meta:
            if item.establecimiento_id != row.establecimiento_id:
                continue
            lot_share = _ratio(item.superficie_ha, est_total)
            lot_accumulator[item.lote_campania_id]["indirect_costs_ars"] += _safe_float(row.monto_ars) * lot_share
        last_dates.append(row.fecha)

    budget_total = {
        "revenue": 0.0,
        "direct": 0.0,
        "indirect": 0.0,
        "margin": 0.0,
    }
    for row in budget_rows:
        lot = lot_accumulator.get(row.lote_campania_id)
        if not lot:
            continue
        budget_total["revenue"] += _safe_float(row.ingreso_plan_ars)
        budget_total["direct"] += _safe_float(row.costo_directo_plan_ars)
        budget_total["indirect"] += _safe_float(row.costo_indirecto_plan_ars)
        budget_total["margin"] += _safe_float(row.margen_plan_ars)
        lot["budget_margin_ars"] += _safe_float(row.margen_plan_ars)
        lot["budget_revenue_ars"] += _safe_float(row.ingreso_plan_ars)

    total_surface = round(sum(item.superficie_ha for item in lot_meta), 2)
    total_revenue = round(sum(_safe_float(item["revenue_ars"]) for item in lot_accumulator.values()), 2)
    total_direct = round(sum(_safe_float(item["direct_costs_ars"]) for item in lot_accumulator.values()), 2)
    total_indirect = round(sum(_safe_float(item["indirect_costs_ars"]) for item in lot_accumulator.values()), 2)
    total_margin = round(total_revenue - total_direct - total_indirect, 2)
    total_received_kg = round(sum(_safe_float(item["kg_received"]) for item in lot_accumulator.values()), 2)
    total_commercial_kg = round(sum(_safe_float(item["kg_packout"]) for item in lot_accumulator.values()), 2)
    packout_target_pct = round(mean([item.objetivo_packout_pct for item in lot_meta if item.objetivo_packout_pct > 0]) if lot_meta else 0, 1)
    packout_pct = round(_ratio(total_commercial_kg, total_received_kg) * 100, 1) if total_received_kg else 0.0

    elapsed_days = max(1, (cut_off_date - window_start).days + 1)
    total_campaign_days = max(1, (campania_fin - campania_inicio).days + 1)
    elapsed_ratio = _clamp(elapsed_days / total_campaign_days, 0, 1)
    budget_revenue_to_date = round(budget_total["revenue"] * elapsed_ratio, 2)
    budget_direct_to_date = round(budget_total["direct"] * elapsed_ratio, 2)
    budget_indirect_to_date = round(budget_total["indirect"] * elapsed_ratio, 2)
    budget_margin_to_date = round(budget_total["margin"] * elapsed_ratio, 2)

    establishment_rows: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {"establecimiento": "", "revenue_ars": 0.0, "direct_costs_ars": 0.0, "indirect_costs_ars": 0.0, "margin_ars": 0.0, "surface_ha": 0.0}
    )
    lot_rows = []
    for item in lot_accumulator.values():
        margin_total = _safe_float(item["revenue_ars"]) - _safe_float(item["direct_costs_ars"]) - _safe_float(item["indirect_costs_ars"])
        margin_ha = margin_total / max(_safe_float(item["superficie_ha"]), 1)
        deviation_budget_pct = _safe_pct(margin_total, _safe_float(item["budget_margin_ars"])) if _safe_float(item["budget_margin_ars"]) else 0.0
        packout_lot_pct = _ratio(_safe_float(item["kg_packout"]), _safe_float(item["kg_received"])) * 100 if _safe_float(item["kg_received"]) else 0.0
        row = {
            "lote_campania_id": int(item["lote_campania_id"]),
            "lote": str(item["lote"]),
            "codigo_lote": str(item["codigo_lote"]),
            "campo": str(item["campo"]),
            "establecimiento": str(item["establecimiento"]),
            "variedad": str(item["variedad"]),
            "superficie_ha": round(_safe_float(item["superficie_ha"]), 1),
            "ingresos_ars": round(_safe_float(item["revenue_ars"]), 2),
            "costos_directos_ars": round(_safe_float(item["direct_costs_ars"]), 2),
            "costos_indirectos_ars": round(_safe_float(item["indirect_costs_ars"]), 2),
            "margen_ars": round(margin_total, 2),
            "margen_ha_ars": round(margin_ha, 2),
            "desvio_presupuesto_pct": round(deviation_budget_pct, 2),
            "packout_pct": round(packout_lot_pct, 1),
            "objetivo_packout_pct": round(_safe_float(item["target_packout_pct"]), 1),
            "objetivo_margen_ha": round(_safe_float(item["target_margin_ha"]), 2),
        }
        lot_rows.append(row)
        establishment = establishment_rows[str(item["establecimiento"])]
        establishment["establecimiento"] = str(item["establecimiento"])
        establishment["revenue_ars"] += _safe_float(item["revenue_ars"])
        establishment["direct_costs_ars"] += _safe_float(item["direct_costs_ars"])
        establishment["indirect_costs_ars"] += _safe_float(item["indirect_costs_ars"])
        establishment["surface_ha"] += _safe_float(item["superficie_ha"])

    for row in establishment_rows.values():
        row["margin_ars"] = round(_safe_float(row["revenue_ars"]) - _safe_float(row["direct_costs_ars"]) - _safe_float(row["indirect_costs_ars"]), 2)

    if total_revenue > 0:
        for row in channel_rows.values():
            share = _ratio(_safe_float(row["revenue_ars"]), total_revenue)
            allocated_cost = (total_direct + total_indirect) * share
            row["costs_ars"] = round(allocated_cost, 2)
            row["margin_ars"] = round(_safe_float(row["revenue_ars"]) - allocated_cost, 2)
            row["share_pct"] = round(share * 100, 1)
            row["kg_tn"] = round(_safe_float(row["kg"]) / 1000.0, 2)
    else:
        for row in channel_rows.values():
            row["costs_ars"] = 0.0
            row["margin_ars"] = 0.0
            row["share_pct"] = 0.0
            row["kg_tn"] = round(_safe_float(row["kg"]) / 1000.0, 2)

    latest_water_by_lot: dict[int, RequerimientoHidricoFact] = {}
    for row in water_rows:
        latest_water_by_lot.setdefault(row.lote_campania_id, row)

    latest_scout_by_lot: dict[int, ScoutingFact] = {}
    for row in scouting_rows:
        latest_scout_by_lot.setdefault(row.lote_campania_id, row)

    return {
        "meta": lot_meta,
        "summary": {
            "revenue_ars": total_revenue,
            "direct_costs_ars": total_direct,
            "indirect_costs_ars": total_indirect,
            "margin_ars": total_margin,
            "margin_per_ha_ars": round(total_margin / max(total_surface, 1), 2),
            "budget_margin_ars": budget_margin_to_date,
            "budget_revenue_ars": budget_revenue_to_date,
            "budget_direct_costs_ars": budget_direct_to_date,
            "budget_indirect_costs_ars": budget_indirect_to_date,
            "packout_pct": packout_pct,
            "packout_target_pct": packout_target_pct,
            "surface_ha": total_surface,
            "received_kg": total_received_kg,
            "commercial_kg": total_commercial_kg,
        },
        "daily": [
            {
                "fecha": day.isoformat(),
                "ingresos_ars": round(daily_revenue.get(day, 0.0), 2),
                "costos_ars": round(daily_costs.get(day, 0.0), 2),
                "margen_ars": round(daily_revenue.get(day, 0.0) - daily_costs.get(day, 0.0), 2),
            }
            for day in _daterange(window_start, max(last_dates))
        ],
        "lots": sorted(lot_rows, key=lambda item: item["margen_ars"], reverse=True),
        "establishments": sorted(establishment_rows.values(), key=lambda item: _safe_float(item["margin_ars"]), reverse=True),
        "channels": sorted(channel_rows.values(), key=lambda item: _safe_float(item["revenue_ars"]), reverse=True),
        "cost_categories": [
            {"categoria": key, "monto_ars": round(value, 2)}
            for key, value in sorted(cost_categories.items(), key=lambda item: item[1], reverse=True)
        ],
        "recent_water": [
            {
                "lote": meta_by_lot[row.lote_campania_id].lote,
                "establecimiento": meta_by_lot[row.lote_campania_id].establecimiento,
                "estado": row.estado,
                "balance_hidrico_m3": round(_safe_float(row.balance_hidrico_m3), 2),
                "fecha": row.fecha.isoformat(),
            }
            for row in latest_water_by_lot.values()
        ],
        "recent_scouting": [
            {
                "lote": meta_by_lot[row.lote_campania_id].lote,
                "establecimiento": meta_by_lot[row.lote_campania_id].establecimiento,
                "severidad": row.severidad,
                "incidencia_pct": round(_safe_float(row.incidencia_pct), 2),
                "fecha": row.fecha_evento.isoformat(),
                "alerta": bool(row.alerta),
            }
            for row in latest_scout_by_lot.values()
        ],
        "packhouse_metrics": [
            {
                "fecha": row.fecha.isoformat(),
                "establecimiento_id": row.establecimiento_id,
                "eficiencia_pct": round(_safe_float(row.eficiencia_pct), 2),
                "kg_procesados": round(_safe_float(row.kg_procesados), 2),
                "horas_downtime": round(_safe_float(row.horas_downtime), 2),
            }
            for row in packhouse_rows
        ],
        "last_date": max(last_dates),
    }


def _build_projection(monthly_rows: list[dict]) -> list[dict]:
    if not monthly_rows:
        return []
    observed = monthly_rows[-4:] if len(monthly_rows) >= 4 else monthly_rows
    if len(observed) < 2:
        return [{"periodo": row["periodo"], "margen_ars": row["margen_ars"], "tipo": "historico"} for row in monthly_rows]
    values = [row["margen_ars"] for row in observed]
    slope = (values[-1] - values[0]) / max(len(values) - 1, 1)
    projection = [{"periodo": row["periodo"], "margen_ars": row["margen_ars"], "tipo": "historico"} for row in monthly_rows]
    base_date = date.fromisoformat(f"{monthly_rows[-1]['periodo']}-01")
    current_value = monthly_rows[-1]["margen_ars"]
    for index in range(1, 4):
        next_period = month_key((base_date.replace(day=1) + timedelta(days=32 * index)).replace(day=1))
        projection.append(
            {
                "periodo": next_period,
                "margen_ars": round(current_value + slope * index, 2),
                "tipo": "proyeccion",
            }
        )
    return projection


async def get_gerencia_general(
    db: AsyncSession,
    filters: LemonFilters,
) -> dict:
    campaign_pair = await resolve_campaign_pair(db, filters.campania_id)
    current_campaign = campaign_pair.current
    current_window_start, current_window_end, _ = resolve_time_window(
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        filters,
    )
    narrowed_scope = any(
        [
            filters.establecimiento_id,
            filters.campo_id,
            filters.lote_id,
            filters.variedad_id,
        ]
    )
    current_snapshot = await _build_snapshot(
        db,
        filters,
        current_campaign.campania_id,
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        current_window_start,
        current_window_end,
    )
    full_campaign_snapshot = (
        await _build_snapshot(
            db,
            LemonFilters(
                empresa_id=filters.empresa_id,
                campania_id=current_campaign.campania_id,
            ),
            current_campaign.campania_id,
            current_campaign.fecha_inicio,
            current_campaign.fecha_fin,
            current_window_start,
            current_window_end,
        )
        if narrowed_scope
        else current_snapshot
    )

    comparison_summary = None
    if campaign_pair.previous:
        previous_window_start, previous_cut_off = resolve_previous_window(
            current_window_start,
            current_window_end,
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
        comparison_summary = previous_snapshot["summary"]

    summary = current_snapshot["summary"]
    previous = comparison_summary or {
        "margin_ars": 0.0,
        "margin_per_ha_ars": 0.0,
        "revenue_ars": 0.0,
        "packout_pct": 0.0,
    }
    budget_margin = summary["budget_margin_ars"]
    budget_revenue = summary["budget_revenue_ars"]
    deviation_budget_pct = _safe_pct(summary["margin_ars"], budget_margin) if budget_margin else 0.0

    monthly_rows_map: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {"periodo": "", "ingresos_ars": 0.0, "costos_ars": 0.0, "margen_ars": 0.0}
    )
    for row in current_snapshot["daily"]:
        period = row["fecha"][:7]
        bucket = monthly_rows_map[period]
        bucket["periodo"] = period
        bucket["ingresos_ars"] += row["ingresos_ars"]
        bucket["costos_ars"] += row["costos_ars"]
        bucket["margen_ars"] += row["margen_ars"]
    monthly_rows = sorted(monthly_rows_map.values(), key=lambda item: str(item["periodo"]))

    lot_rows = current_snapshot["lots"]
    worst_lots = [item for item in lot_rows if item["margen_ars"] < 0][:5]
    water_risk = [item for item in current_snapshot["recent_water"] if item["estado"] != "normal"]
    scout_risk = [item for item in current_snapshot["recent_scouting"] if item["severidad"] in {"alta", "media"}]
    avg_packhouse_efficiency = mean([item["eficiencia_pct"] for item in current_snapshot["packhouse_metrics"]]) if current_snapshot["packhouse_metrics"] else 0.0

    contrato_rows = (
        await db.execute(
            select(ContratoVentaFact)
            .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
            .where(ContratoVentaFact.fecha_contrato >= current_window_start)
            .where(ContratoVentaFact.fecha_contrato <= current_snapshot["last_date"])
        )
    ).scalars().all()
    cobranza_rows = (
        await db.execute(
            select(CobranzasFact)
            .join(LiquidacionFact, CobranzasFact.liquidacion_id == LiquidacionFact.liquidacion_id)
            .join(EmbarqueFact, LiquidacionFact.embarque_id == EmbarqueFact.embarque_id)
            .join(ContratoVentaFact, EmbarqueFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
            .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
            .where(CobranzasFact.fecha_cobranza >= current_window_start)
            .where(CobranzasFact.fecha_cobranza <= current_snapshot["last_date"])
        )
    ).scalars().all()
    cx_rows = (
        await db.execute(
            select(CuentasCobrarFact)
            .join(ContratoVentaFact, CuentasCobrarFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
            .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
            .where(CuentasCobrarFact.fecha_emision >= current_window_start)
            .where(CuentasCobrarFact.fecha_emision <= current_snapshot["last_date"])
        )
    ).scalars().all()
    latest_daily_row = (
        current_snapshot["daily"][-1]
        if current_snapshot["daily"]
        else {"fecha": current_snapshot["last_date"].isoformat(), "ingresos_ars": 0.0, "margen_ars": 0.0}
    )
    latest_cobranza_date = max((row.fecha_cobranza for row in cobranza_rows), default=current_snapshot["last_date"])
    full_pending_contract_kg = round(sum(_safe_float(row.kg_pendientes) for row in contrato_rows) / 1000.0, 2)
    full_delivered_contract_tn = round(sum(_safe_float(row.kg_entregados) for row in contrato_rows) / 1000.0, 2)
    full_accounts_open_ars = round(sum(_safe_float(row.saldo_abierto_ars) for row in cx_rows), 2)
    revenue_scope_ratio = _ratio(summary["revenue_ars"], max(_safe_float(full_campaign_snapshot["summary"]["revenue_ars"]), 1))
    commercial_scope_ratio = _ratio(summary["commercial_kg"], max(_safe_float(full_campaign_snapshot["summary"]["commercial_kg"]), 1))
    pending_contract_kg = round(full_pending_contract_kg * commercial_scope_ratio, 2)
    delivered_contract_tn = round(full_delivered_contract_tn * commercial_scope_ratio, 2)
    accounts_open_ars = round(full_accounts_open_ars * revenue_scope_ratio, 2)
    cobranzas_hoy_ars = round(
        sum(_safe_float(row.monto_cobrado_ars) for row in cobranza_rows if row.fecha_cobranza == latest_cobranza_date)
        * revenue_scope_ratio,
        2,
    )
    stock_disponible_tn = round(max(summary["commercial_kg"] / 1000.0 - delivered_contract_tn, 0.0), 2)
    commercial_utilization_target = 88.0

    cx_by_id = {row.cuenta_cobrar_id: row for row in cx_rows}
    gerencia_dias_list = [
        (row.fecha_cobranza - cx_by_id[row.cuenta_cobrar_id].fecha_emision).days
        for row in cobranza_rows
        if row.cuenta_cobrar_id in cx_by_id and row.fecha_cobranza >= cx_by_id[row.cuenta_cobrar_id].fecha_emision
    ]
    dias_promedio_cobro = round(sum(gerencia_dias_list) / len(gerencia_dias_list), 1) if gerencia_dias_list else None

    latest_fx_rows = (
        await db.execute(
            select(TipoCambioFact)
            .where(TipoCambioFact.fecha <= current_snapshot["last_date"])
            .order_by(TipoCambioFact.fecha)
        )
    ).scalars().all()
    fx_lookup = _build_fx_lookup(latest_fx_rows)
    latest_tc = max((v for v in fx_lookup.values() if v > 0), default=0.0)
    total_costs_ars = _safe_float(summary.get("direct_costs_ars", 0.0)) + _safe_float(summary.get("indirect_costs_ars", 0.0))
    processed_tn = _safe_float(summary.get("received_kg", 0.0)) / 1000.0
    costo_tn_usd = round(total_costs_ars / max(latest_tc, 1) / max(processed_tn, 1), 2) if latest_tc and processed_tn else None

    channels_for_insight = [
        {
            "canal": row["channel"],
            "margen_ars": round(_safe_float(row["margin_ars"]), 2),
        }
        for row in current_snapshot["channels"]
    ]
    dominant_channel = max(channels_for_insight, key=lambda item: item["margen_ars"]) if channels_for_insight else None

    response = {
        "meta": {
            "campania": current_campaign.nombre,
            "campania_id": current_campaign.campania_id,
            "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
            "scope_lotes": len(current_snapshot["meta"]),
            "scope_superficie_ha": summary["surface_ha"],
            "source": "ERP limonero + precio realizado y referencia por canal",
            "last_updated": current_snapshot["last_date"].isoformat(),
            "fase_campania": get_fase_campania(current_snapshot["last_date"]),
        },
        "summary": {
            "margen_hoy_ars": round(_safe_float(latest_daily_row["margen_ars"]), 2),
            "ventas_hoy_ars": round(_safe_float(latest_daily_row["ingresos_ars"]), 2),
            "cobranzas_hoy_ars": cobranzas_hoy_ars,
            "margen_operativo_ars": round(summary["margin_ars"], 2),
            "margen_operativo_delta_pct": _safe_pct(summary["margin_ars"], previous["margin_ars"]),
            "margen_operativo_status": _kpi_status_margin(summary["margin_ars"], budget_margin),
            "margen_operativo_detail": "Resultado neto estimado después de costos directos e indirectos.",
            "margen_por_ha_ars": round(summary["margin_per_ha_ars"], 2),
            "margen_por_ha_delta_pct": _safe_pct(summary["margin_per_ha_ars"], previous["margin_per_ha_ars"]),
            "margen_por_ha_status": _kpi_status_margin(summary["margin_per_ha_ars"], _ratio(budget_margin, max(summary["surface_ha"], 1))),
            "margen_por_ha_detail": "Permite comparar eficiencia económica entre establecimientos y lotes.",
            "ingresos_acumulados_ars": round(summary["revenue_ars"], 2),
            "ingresos_acumulados_delta_pct": _safe_pct(summary["revenue_ars"], previous["revenue_ars"]),
            "ingresos_acumulados_status": _kpi_status_margin(summary["revenue_ars"], budget_revenue),
            "ingresos_acumulados_detail": "Valor estimado de fruta comercial procesada con precio y dólar de referencia.",
            "desvio_presupuesto_pct": round(deviation_budget_pct, 2),
            "desvio_presupuesto_delta_pct": round(deviation_budget_pct, 2),
            "desvio_presupuesto_status": _kpi_status_deviation(deviation_budget_pct),
            "desvio_presupuesto_detail": "Compara el margen acumulado contra el presupuesto faseado de campaña.",
            "packout_comercial_pct": round(summary["packout_pct"], 1),
            "packout_comercial_delta_pct": _safe_pct(summary["packout_pct"], previous["packout_pct"]),
            "packout_comercial_status": _kpi_status_utilization(summary["packout_pct"], commercial_utilization_target),
            "packout_comercial_detail": "Mide qué parte de la fruta recibida termina con salida comercial o industrial útil.",
            "packout_objetivo_pct": commercial_utilization_target,
            "cobranza_abierta_ars": accounts_open_ars,
            "toneladas_pendientes_contrato": pending_contract_kg,
            "stock_disponible_tn": stock_disponible_tn,
            "dias_promedio_cobro": dias_promedio_cobro,
            "dias_promedio_cobro_detail": "Plazo promedio entre emisión de factura y cobro. Verde <45 días · Rojo >75 días.",
            "costo_tn_usd": costo_tn_usd,
            "costo_tn_usd_detail": "Costo total por tonelada recibida en packhouse, expresado en USD. Benchmark saludable: <USD 85/tn.",
        },
        "series": {
            "resultado_diario": current_snapshot["daily"],
        },
        "breakdown": {
            "margen_establecimiento": [
                {
                    "establecimiento": row["establecimiento"],
                    "ingresos_ars": round(_safe_float(row["revenue_ars"]), 2),
                    "costos_ars": round(_safe_float(row["direct_costs_ars"]) + _safe_float(row["indirect_costs_ars"]), 2),
                    "margen_ars": round(_safe_float(row["margin_ars"]), 2),
                    "margen_ha_ars": round(_safe_float(row["margin_ars"]) / max(_safe_float(row["surface_ha"]), 1), 2),
                    "superficie_ha": round(_safe_float(row["surface_ha"]), 1),
                }
                for row in current_snapshot["establishments"]
            ],
            "ingresos_costos_canal": [
                {
                    "canal": row["channel"],
                    "ingresos_ars": round(_safe_float(row["revenue_ars"]), 2),
                    "costos_ars": round(_safe_float(row["costs_ars"]), 2),
                    "margen_ars": round(_safe_float(row["margin_ars"]), 2),
                    "participacion_pct": round(_safe_float(row["share_pct"]), 1),
                    "toneladas": round(_safe_float(row["kg_tn"]), 2),
                }
                for row in current_snapshot["channels"]
            ],
            "ranking_lotes": lot_rows,
            "costos_categoria": current_snapshot["cost_categories"],
        },
        "analysis": {
            "proyeccion_margen": _build_projection(monthly_rows),
            "presupuesto_vs_real": [
                {
                    "concepto": "Ingresos",
                    "real_ars": round(summary["revenue_ars"], 2),
                    "presupuesto_ars": round(summary["budget_revenue_ars"], 2),
                    "desvio_ars": round(summary["revenue_ars"] - summary["budget_revenue_ars"], 2),
                    "desvio_pct": _safe_pct(summary["revenue_ars"], summary["budget_revenue_ars"]),
                },
                {
                    "concepto": "Costos directos",
                    "real_ars": round(summary["direct_costs_ars"], 2),
                    "presupuesto_ars": round(summary["budget_direct_costs_ars"], 2),
                    "desvio_ars": round(summary["direct_costs_ars"] - summary["budget_direct_costs_ars"], 2),
                    "desvio_pct": _safe_pct(summary["direct_costs_ars"], summary["budget_direct_costs_ars"]),
                },
                {
                    "concepto": "Costos indirectos",
                    "real_ars": round(summary["indirect_costs_ars"], 2),
                    "presupuesto_ars": round(summary["budget_indirect_costs_ars"], 2),
                    "desvio_ars": round(summary["indirect_costs_ars"] - summary["budget_indirect_costs_ars"], 2),
                    "desvio_pct": _safe_pct(summary["indirect_costs_ars"], summary["budget_indirect_costs_ars"]),
                },
                {
                    "concepto": "Margen",
                    "real_ars": round(summary["margin_ars"], 2),
                    "presupuesto_ars": round(summary["budget_margin_ars"], 2),
                    "desvio_ars": round(summary["margin_ars"] - summary["budget_margin_ars"], 2),
                    "desvio_pct": _safe_pct(summary["margin_ars"], summary["budget_margin_ars"]),
                },
            ],
            "sensibilidad": [
                {"escenario": "+5% precio exportación", "margen_ars": round(summary["margin_ars"] + summary["revenue_ars"] * 0.05, 2)},
                {"escenario": "-5% precio exportación", "margen_ars": round(summary["margin_ars"] - summary["revenue_ars"] * 0.05, 2)},
                {"escenario": "+5% costo directo", "margen_ars": round(summary["margin_ars"] - summary["direct_costs_ars"] * 0.05, 2)},
                {"escenario": "+10% tipo de cambio", "margen_ars": round(summary["margin_ars"] + summary["revenue_ars"] * 0.10, 2)},
            ],
            "insights": [
                {
                    "titulo": "Canal con mayor contribución",
                    "descripcion": (
                        f"{dominant_channel['canal']} explica la mayor parte del margen estimado."
                        if dominant_channel
                        else "Sin canal dominante para destacar."
                    ),
                    "severity": "success",
                },
                {
                    "titulo": "Margen proyectado",
                    "descripcion": (
                        "La proyección apunta a cierre arriba del presupuesto faseado."
                        if summary["margin_ars"] >= summary["budget_margin_ars"]
                        else "La campaña corre debajo del presupuesto y necesita corrección comercial u operativa."
                    ),
                    "severity": "success" if summary["margin_ars"] >= summary["budget_margin_ars"] else "warning",
                },
                {
                    "titulo": "Presión de calidad",
                    "descripcion": (
                        f"El aprovechamiento comercial está en {summary['packout_pct']:.1f}% contra un piso gerencial de {commercial_utilization_target:.1f}%."
                    ),
                    "severity": "success" if summary["packout_pct"] >= commercial_utilization_target else "warning",
                },
                {
                    "titulo": "Cobranza pendiente",
                    "descripcion": f"Quedan {pending_contract_kg:.1f} tn por entregar o formalizar y ARS {accounts_open_ars:,.0f} abiertos por cobrar.",
                    "severity": "info",
                },
                {
                    "titulo": "Plazo de cobro",
                    "descripcion": (
                        f"El plazo promedio de cobro es {dias_promedio_cobro:.0f} días — crítico. Con inflación >60% anual, cobrar tarde destruye margen real."
                        if dias_promedio_cobro is not None and dias_promedio_cobro > 75
                        else f"Plazo de cobro promedio: {dias_promedio_cobro:.0f} días. Atención: el rango saludable es <45 días."
                        if dias_promedio_cobro is not None and dias_promedio_cobro > 45
                        else f"Plazo de cobro promedio: {dias_promedio_cobro:.0f} días — dentro del rango saludable."
                        if dias_promedio_cobro is not None
                        else "Sin cobros completos registrados para medir el plazo."
                    ),
                    "severity": (
                        "danger" if dias_promedio_cobro is not None and dias_promedio_cobro > 75
                        else "warning" if dias_promedio_cobro is not None and dias_promedio_cobro > 45
                        else "success"
                    ),
                },
                {
                    "titulo": "Costo por tonelada",
                    "descripcion": (
                        f"El costo de producción se ubica en USD {costo_tn_usd:,.0f}/tn — dentro del rango saludable (benchmark verde: <USD 85/tn)."
                        if costo_tn_usd is not None and costo_tn_usd <= 85
                        else f"El costo de producción se ubica en USD {costo_tn_usd:,.0f}/tn — por encima del benchmark. Revisar costos de cosecha y packhouse."
                        if costo_tn_usd is not None
                        else "Sin datos suficientes para calcular costo/tn en USD."
                    ),
                    "severity": (
                        "success" if costo_tn_usd is not None and costo_tn_usd <= 85
                        else "warning" if costo_tn_usd is not None and costo_tn_usd <= 110
                        else "danger" if costo_tn_usd is not None
                        else "info"
                    ),
                },
            ],
        },
        "alerts": [
            {
                "id": "margen-negativo",
                "prioridad": "alta" if worst_lots else "media",
                "severidad": "critical" if worst_lots else "info",
                "titulo": "Lotes destruyendo margen" if worst_lots else "Sin lotes con margen negativo",
                "impacto": (
                    f"{len(worst_lots)} lotes ya están por debajo de cero."
                    if worst_lots
                    else "La cartera actual no muestra lotes en pérdida directa."
                ),
                "modulo": "Producción de Campo",
                "detalle": worst_lots[0]["lote"] if worst_lots else "Seguimiento semanal",
                "accion": "Revisar calidad, costos y destino comercial de los peores lotes.",
            },
            {
                "id": "packout-meta",
                "prioridad": "alta" if summary["packout_pct"] < commercial_utilization_target - 6 else "media",
                "severidad": "warning" if summary["packout_pct"] < commercial_utilization_target else "success",
                "titulo": "Aprovechamiento comercial bajo piso" if summary["packout_pct"] < commercial_utilization_target else "Aprovechamiento comercial dentro de rango",
                "impacto": f"{summary['packout_pct']:.1f}% vs piso {commercial_utilization_target:.1f}%.",
                "modulo": "Calidad / Packhouse",
                "detalle": f"{summary['commercial_kg'] / 1000:.1f} tn comerciales procesadas.",
                "accion": "Priorizar lotes con mejor calidad y corregir defectos de rechazo.",
            },
            {
                "id": "hidrico",
                "prioridad": "media" if water_risk else "baja",
                "severidad": "warning" if water_risk else "info",
                "titulo": "Lotes con estrés hídrico" if water_risk else "Sin alerta hídrica destacable",
                "impacto": f"{len(water_risk)} lotes con balance fuera de rango." if water_risk else "El balance hídrico reciente no muestra focos críticos.",
                "modulo": "Riego y Fertirriego",
                "detalle": water_risk[0]["lote"] if water_risk else "Monitoreo normal",
                "accion": "Reordenar riego en los lotes con mayor déficit acumulado.",
            },
            {
                "id": "packhouse",
                "prioridad": "media" if avg_packhouse_efficiency < 80 else "baja",
                "severidad": "warning" if avg_packhouse_efficiency < 80 else "success",
                "titulo": "Eficiencia de packhouse",
                "impacto": f"Eficiencia promedio {avg_packhouse_efficiency:.1f}% en la campaña filtrada.",
                "modulo": "Packhouse",
                "detalle": "Revisar líneas o turnos con más downtime." if avg_packhouse_efficiency < 80 else "Sin desvíos fuertes de proceso.",
                "accion": "Programar mantenimiento corto y balancear carga por línea.",
            },
            {
                "id": "sanidad",
                "prioridad": "media" if scout_risk else "baja",
                "severidad": "warning" if scout_risk else "info",
                "titulo": "Focos sanitarios recientes" if scout_risk else "Sin focos sanitarios relevantes",
                "impacto": f"{len(scout_risk)} lotes con scouting medio/alto en 45 días." if scout_risk else "La presión sanitaria reciente es baja.",
                "modulo": "Sanidad y Monitoreo",
                "detalle": scout_risk[0]["lote"] if scout_risk else "Seguimiento semanal",
                "accion": "Ajustar monitoreo y tratamiento donde la incidencia sube más rápido.",
            },
        ],
    }

    return response
