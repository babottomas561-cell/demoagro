from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
import math
from statistics import mean, pstdev

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_commercial import (
    CobranzasFact,
    ContratoVentaFact,
    CostosDirectosFact,
    CostosIndirectosFact,
    EmbarqueFact,
    LiquidacionFact,
    PrecioVentaFact,
    StockFinalFact,
)
from app.models.lemon_dimensions import (
    CampaniaDim,
    ClienteDim,
    DefectoDim,
    DestinoFrutaDim,
    LineaEmpaqueDim,
    LoteDim,
    MercadoDim,
)
from app.models.lemon_external import (
    ClimaDiarioFact,
    MacroSeriesFact,
    PrecioExportacionFact,
    TipoCambioFact,
)
from app.models.lemon_field import (
    CosechaFact,
    LoteCampaniaFact,
    RequerimientoHidricoFact,
    RiegoFact,
    ScoutingFact,
)
from app.models.lemon_packhouse import DowntimePackhouseFact, PackhouseTurnoFact
from app.models.lemon_quality import ClasificacionCalidadFact, PackoutFact, RecepcionFrutaFact, RechazoFact
from app.seed.audit_limon_seed import audit_limon_seed
from app.seed.seed_limon import CURRENT_DATE


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _month_start(value: date) -> date:
    return date(value.year, value.month, 1)


def _aggregate_sum(rows: list[tuple[date, float]], bucket: str) -> list[tuple[date, float]]:
    grouped: dict[date, float] = defaultdict(float)
    for row_date, value in rows:
        key = _week_start(row_date) if bucket == "weekly" else _month_start(row_date) if bucket == "monthly" else row_date
        grouped[key] += float(value or 0)
    return sorted(grouped.items(), key=lambda item: item[0])


def _aggregate_weighted_ratio(rows: list[tuple[date, float, float]], bucket: str) -> list[tuple[date, float]]:
    numerators: dict[date, float] = defaultdict(float)
    denominators: dict[date, float] = defaultdict(float)
    for row_date, numerator, denominator in rows:
        key = _week_start(row_date) if bucket == "weekly" else _month_start(row_date) if bucket == "monthly" else row_date
        numerators[key] += float(numerator or 0)
        denominators[key] += float(denominator or 0)
    return sorted(
        [
            (key, numerators[key] / denominators[key] if denominators[key] else 0.0)
            for key in numerators
        ],
        key=lambda item: item[0],
    )


def _series_density_thresholds(cadence: str) -> dict[str, int]:
    if cadence == "daily":
        return {"7D": 5, "30D": 22, "90D": 70, "12M": 260}
    if cadence == "weekly":
        return {"7D": 1, "30D": 4, "90D": 10, "12M": 40}
    return {"30D": 1, "90D": 3, "12M": 10}


def _series_stats(
    name: str,
    points: list[tuple[date, float]],
    cadence: str,
    min_points: int,
    *,
    density_thresholds: dict[str, int] | None = None,
    check_gaps: bool = True,
    min_cv: float = 0.04,
    min_range_pct: float = 0.08,
) -> dict:
    if not points:
        return {
            "name": name,
            "points": 0,
            "status": "fail",
            "issues": ["serie vacía"],
        }

    dates = [item[0] for item in points]
    values = [float(item[1]) for item in points]
    gaps = [(dates[idx] - dates[idx - 1]).days for idx in range(1, len(dates))]
    max_gap = max(gaps) if gaps else 0
    cadence_days = {"daily": 1, "weekly": 7, "monthly": 30}[cadence]
    avg_value = mean(values)
    stdev_value = pstdev(values) if len(values) > 1 else 0.0
    cv = stdev_value / avg_value if avg_value else 0.0
    min_value = min(values)
    max_value = max(values)
    range_pct = ((max_value - min_value) / avg_value) if avg_value else 0.0
    rounded_uniques = len({round(value, 4) for value in values})
    non_zero_points = sum(1 for value in values if abs(value) > 1e-6)
    positive_points = [value for value in values if value > 0]
    positive_avg = mean(positive_points) if positive_points else 0.0
    positive_stdev = pstdev(positive_points) if len(positive_points) > 1 else 0.0
    outliers = 0
    if positive_points and positive_stdev:
        for value in positive_points:
            if abs(value - positive_avg) / positive_stdev > 3.4:
                outliers += 1

    range_counts = {}
    for label, threshold in (density_thresholds or _series_density_thresholds(cadence)).items():
        if label == "7D":
            lower = CURRENT_DATE - timedelta(days=6)
        elif label == "30D":
            lower = CURRENT_DATE - timedelta(days=29)
        elif label == "90D":
            lower = CURRENT_DATE - timedelta(days=89)
        else:
            lower = CURRENT_DATE - timedelta(days=364)
        count = sum(1 for row_date, _ in points if row_date >= lower)
        range_counts[label] = {"points": count, "expected_min": threshold, "ok": count >= threshold}

    issues: list[str] = []
    if len(points) < min_points:
        issues.append(f"pocos puntos ({len(points)}/{min_points})")
    if check_gaps and max_gap > cadence_days * 2:
        issues.append(f"gap máximo alto ({max_gap} días)")
    if rounded_uniques <= max(3, len(points) // 10):
        issues.append("serie demasiado plana")
    if avg_value > 0 and cv < min_cv and range_pct < min_range_pct:
        issues.append("variabilidad insuficiente")
    if outliers > max(2, math.ceil(len(positive_points) * 0.05)):
        issues.append("demasiados outliers")
    if non_zero_points == 0:
        issues.append("todos los puntos están en cero")
    for label, stats in range_counts.items():
        if not stats["ok"]:
            issues.append(f"densidad insuficiente en {label}")

    return {
        "name": name,
        "cadence": cadence,
        "points": len(points),
        "date_min": dates[0].isoformat(),
        "date_max": dates[-1].isoformat(),
        "non_zero_points": non_zero_points,
        "max_gap_days": max_gap,
        "variability_cv": round(cv, 4),
        "range_pct_over_mean": round(range_pct, 4),
        "unique_values": rounded_uniques,
        "outlier_points": outliers,
        "density_by_range": range_counts,
        "status": "ok" if not issues else "warn",
        "issues": issues,
    }


def _bar_chart_stats(
    name: str,
    values: list[float],
    min_categories: int = 4,
    *,
    min_cv: float = 0.05,
    min_spread: float = 0.15,
) -> dict:
    cleaned = [float(value) for value in values if value is not None]
    issues: list[str] = []
    if len(cleaned) < min_categories:
        issues.append(f"pocas categorías ({len(cleaned)}/{min_categories})")
    if cleaned:
        avg_value = mean(cleaned)
        cv = pstdev(cleaned) / avg_value if len(cleaned) > 1 and avg_value else 0.0
        spread = (max(cleaned) - min(cleaned)) / avg_value if avg_value else 0.0
    else:
        cv = 0.0
        spread = 0.0
    if cleaned and cv < min_cv and spread < min_spread:
        issues.append("dispersión pobre para barras")
    return {
        "name": name,
        "categories": len(cleaned),
        "variability_cv": round(cv, 4),
        "spread_pct_over_mean": round(spread, 4),
        "status": "ok" if not issues else "warn",
        "issues": issues,
    }


def _pie_chart_stats(name: str, shares: list[float]) -> dict:
    normalized = [max(0.0, float(share)) for share in shares]
    total = sum(normalized)
    issues: list[str] = []
    if total <= 0:
        return {"name": name, "status": "fail", "issues": ["pie sin valores"]}
    ratios = [share / total for share in normalized]
    max_share = max(ratios)
    min_share = min(ratios)
    hhi = sum(ratio * ratio for ratio in ratios)
    if max_share > 0.88:
        issues.append("composición dominada por una categoría")
    if min_share < 0.01:
        issues.append("categoría casi invisible")
    return {
        "name": name,
        "categories": len(ratios),
        "max_share": round(max_share, 4),
        "min_share": round(min_share, 4),
        "concentration_hhi": round(hhi, 4),
        "status": "ok" if not issues else "warn",
        "issues": issues,
    }


def _ranking_stats(name: str, values: list[float]) -> dict:
    cleaned = sorted([float(value) for value in values if value is not None], reverse=True)
    issues: list[str] = []
    if len(cleaned) < 6:
        issues.append("ranking corto")
    if cleaned:
        spread = (cleaned[0] - cleaned[-1]) / (mean(cleaned) or 1)
        top_bottom_ratio = cleaned[0] / cleaned[-1] if cleaned[-1] else 999.0
    else:
        spread = 0.0
        top_bottom_ratio = 0.0
    if spread < 0.18:
        issues.append("top y bottom demasiado parecidos")
    return {
        "name": name,
        "items": len(cleaned),
        "spread_pct_over_mean": round(spread, 4),
        "top_bottom_ratio": round(top_bottom_ratio, 4),
        "status": "ok" if not issues else "warn",
        "issues": issues,
    }


async def validate_limon_bi(db: AsyncSession) -> dict:
    base_audit = await audit_limon_seed(db)
    active_campaign = await db.scalar(select(CampaniaDim).where(CampaniaDim.activa.is_(True)))
    active_campaign_id = active_campaign.campania_id if active_campaign else None

    issues: list[dict[str, str]] = []

    # Series base
    harvest_all_rows = (
        await db.execute(select(CosechaFact.fecha_cosecha, CosechaFact.kg_cosechados).order_by(CosechaFact.fecha_cosecha))
    ).all()
    harvest_active_rows = (
        await db.execute(
            select(CosechaFact.fecha_cosecha, CosechaFact.kg_cosechados)
            .join(LoteCampaniaFact, CosechaFact.lote_campania_id == LoteCampaniaFact.lote_campania_id)
            .where(LoteCampaniaFact.campania_id == active_campaign_id)
            .order_by(CosechaFact.fecha_cosecha)
        )
    ).all()
    packout_active_rows = (
        await db.execute(
            select(PackoutFact.fecha_proceso, PackoutFact.packout_pct, PackoutFact.kg_entrada)
            .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .join(LoteCampaniaFact, RecepcionFrutaFact.lote_campania_id == LoteCampaniaFact.lote_campania_id)
            .where(LoteCampaniaFact.campania_id == active_campaign_id)
            .order_by(PackoutFact.fecha_proceso)
        )
    ).all()
    packhouse_active_rows = (
        await db.execute(
            select(PackhouseTurnoFact.fecha, PackhouseTurnoFact.kg_procesados)
            .where(PackhouseTurnoFact.fecha <= CURRENT_DATE)
            .order_by(PackhouseTurnoFact.fecha)
        )
    ).all()
    scouting_rows = (
        await db.execute(select(ScoutingFact.fecha_evento, ScoutingFact.incidencia_pct).order_by(ScoutingFact.fecha_evento))
    ).all()
    irrigation_rows = (
        await db.execute(select(RiegoFact.fecha_riego, RiegoFact.m3_aplicados).order_by(RiegoFact.fecha_riego))
    ).all()
    climate_rows = (
        await db.execute(select(ClimaDiarioFact.fecha, ClimaDiarioFact.precipitacion_mm).order_by(ClimaDiarioFact.fecha))
    ).all()
    fx_rows = (
        await db.execute(select(TipoCambioFact.fecha, TipoCambioFact.exportacion).order_by(TipoCambioFact.fecha))
    ).all()
    export_price_rows = (
        await db.execute(select(PrecioExportacionFact.fecha, PrecioExportacionFact.precio_promedio_usd_tn).order_by(PrecioExportacionFact.fecha))
    ).all()
    sales_price_rows = (
        await db.execute(select(PrecioVentaFact.fecha, PrecioVentaFact.precio_promedio_usd_tn).order_by(PrecioVentaFact.fecha))
    ).all()
    shipments_rows = (
        await db.execute(select(EmbarqueFact.fecha_embarque, EmbarqueFact.kg_embarcados).order_by(EmbarqueFact.fecha_embarque))
    ).all()
    collections_rows = (
        await db.execute(select(CobranzasFact.fecha_cobranza, CobranzasFact.monto_cobrado_ars).order_by(CobranzasFact.fecha_cobranza))
    ).all()
    revenue_rows = (
        await db.execute(select(LiquidacionFact.fecha_liquidacion, LiquidacionFact.importe_neto_ars).order_by(LiquidacionFact.fecha_liquidacion))
    ).all()
    direct_cost_rows = (
        await db.execute(select(CostosDirectosFact.fecha, CostosDirectosFact.monto_ars).order_by(CostosDirectosFact.fecha))
    ).all()
    indirect_cost_rows = (
        await db.execute(select(CostosIndirectosFact.fecha, CostosIndirectosFact.monto_ars).order_by(CostosIndirectosFact.fecha))
    ).all()
    inflation_rows = (
        await db.execute(
            select(MacroSeriesFact.fecha, MacroSeriesFact.valor)
            .where(MacroSeriesFact.variable == "inflacion_mensual")
            .order_by(MacroSeriesFact.fecha)
        )
    ).all()

    monthly_revenue = _aggregate_sum([(row[0], row[1]) for row in revenue_rows], "monthly")
    monthly_direct_costs = _aggregate_sum([(row[0], row[1]) for row in direct_cost_rows], "monthly")
    monthly_indirect_costs = _aggregate_sum([(row[0], row[1]) for row in indirect_cost_rows], "monthly")
    margin_by_month: dict[date, float] = defaultdict(float)
    for item_date, value in monthly_revenue:
        margin_by_month[item_date] += value
    for item_date, value in monthly_direct_costs:
        margin_by_month[item_date] -= value
    for item_date, value in monthly_indirect_costs:
        margin_by_month[item_date] -= value
    monthly_margin = sorted(margin_by_month.items(), key=lambda item: item[0])

    series_validation = {
        "gerencia.revenue_monthly": _series_stats(
            "gerencia.revenue_monthly",
            monthly_revenue,
            "monthly",
            18,
            density_thresholds={"30D": 1, "90D": 2, "12M": 6},
            check_gaps=False,
        ),
        "gerencia.margin_monthly": _series_stats("gerencia.margin_monthly", monthly_margin, "monthly", 18),
        "produccion.cosecha_weekly_all": _series_stats(
            "produccion.cosecha_weekly_all",
            _aggregate_sum([(row[0], row[1]) for row in harvest_all_rows], "weekly"),
            "weekly",
            32,
            density_thresholds={"7D": 1, "30D": 4, "90D": 8, "12M": 18},
            check_gaps=False,
        ),
        "produccion.cosecha_weekly_active": _series_stats(
            "produccion.cosecha_weekly_active",
            _aggregate_sum([(row[0], row[1]) for row in harvest_active_rows], "weekly"),
            "weekly",
            6,
            density_thresholds={"7D": 1, "30D": 4, "90D": 8, "12M": 8},
            check_gaps=False,
        ),
        "calidad.packout_weekly_active": _series_stats(
            "calidad.packout_weekly_active",
            _aggregate_weighted_ratio([(row[0], row[1] * row[2], row[2]) for row in packout_active_rows], "weekly"),
            "weekly",
            6,
            density_thresholds={"7D": 1, "30D": 4, "90D": 8, "12M": 8},
            check_gaps=False,
            min_cv=0.012,
            min_range_pct=0.035,
        ),
        "packhouse.procesado_daily": _series_stats(
            "packhouse.procesado_daily",
            _aggregate_sum([(row[0], row[1]) for row in packhouse_active_rows], "daily"),
            "daily",
            60,
            density_thresholds={"7D": 5, "30D": 20, "90D": 55, "12M": 140},
            check_gaps=False,
        ),
        "sanidad.incidencia_weekly": _series_stats(
            "sanidad.incidencia_weekly",
            _aggregate_sum([(row[0], row[1]) for row in scouting_rows], "weekly"),
            "weekly",
            24,
            density_thresholds={"7D": 0, "30D": 2, "90D": 5, "12M": 16},
            check_gaps=False,
        ),
        "riego.m3_weekly": _series_stats(
            "riego.m3_weekly",
            _aggregate_sum([(row[0], row[1]) for row in irrigation_rows], "weekly"),
            "weekly",
            24,
            density_thresholds={"7D": 0, "30D": 3, "90D": 10, "12M": 24},
            check_gaps=False,
        ),
        "riego.lluvia_daily": _series_stats("riego.lluvia_daily", _aggregate_sum([(row[0], row[1]) for row in climate_rows], "daily"), "daily", 180),
        "comercial.precio_venta_weekly": _series_stats("comercial.precio_venta_weekly", _aggregate_sum([(row[0], row[1]) for row in sales_price_rows], "weekly"), "weekly", 32),
        "comercial.embarques_weekly": _series_stats(
            "comercial.embarques_weekly",
            _aggregate_sum([(row[0], row[1]) for row in shipments_rows], "weekly"),
            "weekly",
            24,
            density_thresholds={"7D": 1, "30D": 4, "90D": 6, "12M": 20},
            check_gaps=False,
        ),
        "finanzas.cobranzas_weekly": _series_stats(
            "finanzas.cobranzas_weekly",
            _aggregate_sum([(row[0], row[1]) for row in collections_rows], "weekly"),
            "weekly",
            18,
            density_thresholds={"7D": 1, "30D": 4, "90D": 5, "12M": 18},
            check_gaps=False,
        ),
        "macro.tipo_cambio_daily": _series_stats("macro.tipo_cambio_daily", fx_rows, "daily", 365),
        "macro.precio_exportacion_weekly": _series_stats("macro.precio_exportacion_weekly", _aggregate_sum([(row[0], row[1]) for row in export_price_rows], "weekly"), "weekly", 32),
        "macro.inflacion_monthly": _series_stats("macro.inflacion_monthly", inflation_rows, "monthly", 18),
    }

    # Módulos específicos para barras / pies / rankings
    yield_by_lot_rows = (
        await db.execute(
            select(LoteDim.codigo, LoteCampaniaFact.superficie_ha, CosechaFact.kg_cosechados)
            .join(LoteCampaniaFact, LoteDim.lote_id == LoteCampaniaFact.lote_id)
            .join(CosechaFact, LoteCampaniaFact.lote_campania_id == CosechaFact.lote_campania_id)
            .where(LoteCampaniaFact.campania_id == active_campaign_id)
        )
    ).all()
    yield_by_lot: dict[str, dict[str, float]] = defaultdict(lambda: {"kg": 0.0, "ha": 0.0})
    for lote_codigo, superficie_ha, kg_cosechados in yield_by_lot_rows:
        yield_by_lot[lote_codigo]["kg"] += float(kg_cosechados or 0)
        yield_by_lot[lote_codigo]["ha"] = float(superficie_ha or 0)
    yield_values = [values["kg"] / values["ha"] for values in yield_by_lot.values() if values["ha"] > 0]

    destination_rows = (
        await db.execute(
            select(DestinoFrutaDim.nombre, ClasificacionCalidadFact.kg_clasificados)
            .join(DestinoFrutaDim, ClasificacionCalidadFact.destino_id == DestinoFrutaDim.destino_id)
            .order_by(DestinoFrutaDim.destino_id)
        )
    ).all()
    destination_mix: dict[str, float] = defaultdict(float)
    for destination_name, kg_clasificados in destination_rows:
        destination_mix[destination_name] += float(kg_clasificados or 0)

    rejection_rows = (
        await db.execute(
            select(LoteDim.codigo, RechazoFact.kg_rechazo)
            .join(RecepcionFrutaFact, RechazoFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .join(LoteCampaniaFact, RecepcionFrutaFact.lote_campania_id == LoteCampaniaFact.lote_campania_id)
            .join(LoteDim, LoteCampaniaFact.lote_id == LoteDim.lote_id)
            .where(LoteCampaniaFact.campania_id == active_campaign_id)
        )
    ).all()
    rejection_by_lot: dict[str, float] = defaultdict(float)
    for lote_codigo, kg_rechazo in rejection_rows:
        rejection_by_lot[lote_codigo] += float(kg_rechazo or 0)

    line_efficiency_rows = (
        await db.execute(select(LineaEmpaqueDim.nombre, PackhouseTurnoFact.eficiencia_pct).join(LineaEmpaqueDim, PackhouseTurnoFact.linea_id == LineaEmpaqueDim.linea_id))
    ).all()
    efficiency_by_line: dict[str, list[float]] = defaultdict(list)
    for line_name, eficiencia_pct in line_efficiency_rows:
        efficiency_by_line[line_name].append(float(eficiencia_pct or 0))

    downtime_rows = (
        await db.execute(select(DowntimePackhouseFact.motivo, DowntimePackhouseFact.minutos))
    ).all()
    downtime_by_motivo: dict[str, float] = defaultdict(float)
    for motivo, minutos in downtime_rows:
        downtime_by_motivo[motivo] += float(minutos or 0)
    total_downtime = sum(downtime_by_motivo.values())
    significant_downtime_values = [
        value
        for value in downtime_by_motivo.values()
        if total_downtime <= 0 or (value / total_downtime) >= 0.01
    ]

    market_rows = (
        await db.execute(select(MercadoDim.nombre, EmbarqueFact.kg_embarcados).join(MercadoDim, EmbarqueFact.mercado_id == MercadoDim.mercado_id))
    ).all()
    market_mix: dict[str, float] = defaultdict(float)
    for market_name, kg_embarcados in market_rows:
        market_mix[market_name] += float(kg_embarcados or 0)

    client_rows = (
        await db.execute(select(ClienteDim.nombre, EmbarqueFact.kg_embarcados).join(ClienteDim, EmbarqueFact.cliente_id == ClienteDim.cliente_id))
    ).all()
    client_ranking: dict[str, float] = defaultdict(float)
    for client_name, kg_embarcados in client_rows:
        client_ranking[client_name] += float(kg_embarcados or 0)

    irrigation_status_rows = (
        await db.execute(select(RequerimientoHidricoFact.estado, RequerimientoHidricoFact.balance_hidrico_m3))
    ).all()
    irrigation_status_count: dict[str, float] = defaultdict(float)
    for status, balance in irrigation_status_rows:
        irrigation_status_count[status] += abs(float(balance or 0))

    chart_validation = {
        "produccion.rendimiento_lote_bar": _bar_chart_stats("produccion.rendimiento_lote_bar", yield_values),
        "produccion.bottom_lotes_ranking": _ranking_stats("produccion.bottom_lotes_ranking", yield_values),
        "calidad.destino_fruta_pie": _pie_chart_stats("calidad.destino_fruta_pie", list(destination_mix.values())),
        "calidad.rechazo_lotes_ranking": _ranking_stats("calidad.rechazo_lotes_ranking", list(rejection_by_lot.values())),
        "packhouse.eficiencia_linea_bar": _bar_chart_stats(
            "packhouse.eficiencia_linea_bar",
            [mean(values) for values in efficiency_by_line.values() if values],
            min_categories=2,
            min_cv=0.03,
            min_spread=0.08,
        ),
        "packhouse.downtime_motivo_pie": _pie_chart_stats("packhouse.downtime_motivo_pie", significant_downtime_values),
        "comercial.mercado_pie": _pie_chart_stats("comercial.mercado_pie", list(market_mix.values())),
        "comercial.cliente_ranking": _ranking_stats("comercial.cliente_ranking", list(client_ranking.values())),
        "riego.estado_hidrico_bar": _bar_chart_stats("riego.estado_hidrico_bar", list(irrigation_status_count.values()), min_categories=2),
    }

    # Coherencia visual / estacional
    weekly_harvest_all = _aggregate_sum([(row[0], row[1]) for row in harvest_all_rows], "weekly")
    peak_season_kg = sum(value for row_date, value in weekly_harvest_all if row_date.month in {1, 2, 3, 4, 5, 6})
    off_season_kg = sum(value for row_date, value in weekly_harvest_all if row_date.month in {7, 8, 9, 10, 11, 12})
    seasonality = {
        "harvest_peak_share": round(peak_season_kg / (peak_season_kg + off_season_kg), 4) if (peak_season_kg + off_season_kg) else 0,
        "price_range_pct": round(
            ((max(value for _, value in export_price_rows) - min(value for _, value in export_price_rows)) / mean(value for _, value in export_price_rows)),
            4,
        ) if export_price_rows else 0,
        "packout_range_points": round(
            max(value for _, value in _aggregate_weighted_ratio([(row[0], row[1] * row[2], row[2]) for row in packout_active_rows], "weekly")) -
            min(value for _, value in _aggregate_weighted_ratio([(row[0], row[1] * row[2], row[2]) for row in packout_active_rows], "weekly")),
            4,
        ) if packout_active_rows else 0,
    }

    visual_checks = {
        "flat_series": [name for name, stats in series_validation.items() if "serie demasiado plana" in stats["issues"] or "variabilidad insuficiente" in stats["issues"]],
        "sparse_series": [name for name, stats in series_validation.items() if any(issue.startswith("pocos puntos") or issue.startswith("densidad insuficiente") for issue in stats["issues"])],
        "outlier_series": [name for name, stats in series_validation.items() if "demasiados outliers" in stats["issues"]],
        "dominated_pies": [name for name, stats in chart_validation.items() if "composición dominada por una categoría" in stats["issues"]],
        "seasonality": seasonality,
    }

    if seasonality["harvest_peak_share"] < 0.62:
        issues.append({"severity": "warn", "area": "produccion", "message": "la cosecha no concentra suficiente volumen en temporada"})
    if seasonality["price_range_pct"] < 0.08:
        issues.append({"severity": "warn", "area": "macro/comercial", "message": "los precios muestran poca fluctuación"})
    if seasonality["packout_range_points"] < 0.035:
        issues.append({"severity": "warn", "area": "calidad", "message": "el packout semanal varía poco"})

    # Cierre end-to-end volumen y valor
    stock_rows = (
        await db.execute(select(StockFinalFact.fecha, StockFinalFact.kg_stock, StockFinalFact.valor_ars).order_by(StockFinalFact.fecha))
    ).all()
    latest_stock_date = max((row[0] for row in stock_rows), default=None)
    latest_stock_kg = sum(float(row[1] or 0) for row in stock_rows if row[0] == latest_stock_date) if latest_stock_date else 0.0
    latest_stock_value = sum(float(row[2] or 0) for row in stock_rows if row[0] == latest_stock_date) if latest_stock_date else 0.0

    total_received = sum(float(row[1] or 0) for row in (await db.execute(select(RecepcionFrutaFact.fecha_recepcion, RecepcionFrutaFact.kg_recibidos))).all())
    total_classified = sum(float(row[0] or 0) for row in (await db.execute(select(ClasificacionCalidadFact.kg_clasificados))).all())
    total_packed = sum(float(row[0] or 0) for row in (await db.execute(select(PackoutFact.kg_salida))).all())
    total_rejected = sum(float(row[0] or 0) for row in (await db.execute(select(RechazoFact.kg_rechazo))).all())
    total_shipped = sum(float(row[0] or 0) for row in (await db.execute(select(EmbarqueFact.kg_embarcados))).all())
    total_liquidated = sum(float(row[0] or 0) for row in (await db.execute(select(LiquidacionFact.importe_neto_ars))).all())
    total_collected = sum(float(row[0] or 0) for row in (await db.execute(select(CobranzasFact.monto_cobrado_ars))).all())
    non_usd_contracts = int(
        await db.scalar(
            select(func.count())
            .select_from(ContratoVentaFact)
            .where(ContratoVentaFact.moneda != "USD")
        )
        or 0
    )

    end_to_end = {
        "received_vs_classified_ratio": round(total_classified / total_received, 4) if total_received else 0,
        "classified_vs_packout_plus_rejection_ratio": round((total_packed + total_rejected) / total_classified, 4) if total_classified else 0,
        "shipped_vs_packout_plus_stock_ratio": round((total_shipped + latest_stock_kg) / total_packed, 4) if total_packed else 0,
        "collected_vs_liquidated_ratio": round(total_collected / total_liquidated, 4) if total_liquidated else 0,
        "latest_stock_kg": round(latest_stock_kg, 2),
        "latest_stock_value_ars": round(latest_stock_value, 2),
        "non_usd_contracts": non_usd_contracts,
    }

    if not (0.99 <= end_to_end["received_vs_classified_ratio"] <= 1.01):
        issues.append({"severity": "fail", "area": "end_to_end", "message": "recepción y clasificación no cierran"})
    if not (0.99 <= end_to_end["classified_vs_packout_plus_rejection_ratio"] <= 1.01):
        issues.append({"severity": "fail", "area": "end_to_end", "message": "clasificación no cierra con packout y rechazo"})
    if not (0.95 <= end_to_end["shipped_vs_packout_plus_stock_ratio"] <= 1.05):
        issues.append({"severity": "fail", "area": "end_to_end", "message": "packout, stock y ventas no cierran"})
    if end_to_end["collected_vs_liquidated_ratio"] <= 0.5:
        issues.append({"severity": "warn", "area": "finanzas", "message": "cobranza demasiado baja sobre liquidado"})
    if non_usd_contracts > 0:
        issues.append({"severity": "warn", "area": "comercial", "message": "hay contratos con moneda inconsistente frente al esquema de precios"})

    for name, stats in series_validation.items():
        if stats["status"] == "warn":
            for issue in stats["issues"]:
                severity = "fail" if issue.startswith("pocos puntos") or issue.startswith("serie vacía") else "warn"
                issues.append({"severity": severity, "area": name, "message": issue})
    for name, stats in chart_validation.items():
        if stats["status"] == "warn":
            for issue in stats["issues"]:
                issues.append({"severity": "warn", "area": name, "message": issue})

    status = "pass"
    if any(item["severity"] == "fail" for item in issues):
        status = "fail"
    elif issues:
        status = "warn"

    return {
        "status": status,
        "seed_audit": base_audit,
        "series_validation": series_validation,
        "chart_validation": chart_validation,
        "visual_checks": visual_checks,
        "end_to_end": end_to_end,
        "issues": issues,
    }
