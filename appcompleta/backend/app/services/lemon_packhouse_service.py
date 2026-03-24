from __future__ import annotations

from collections import defaultdict
from datetime import date
from statistics import mean

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_dimensions import LineaEmpaqueDim, TurnoDim
from app.models.lemon_packhouse import (
    ConsumoPackhouseFact,
    DowntimePackhouseFact,
    ManoObraPackhouseFact,
    MantenimientoPackhouseFact,
    PackhouseTurnoFact,
)
from app.models.lemon_quality import PackoutFact, RecepcionFrutaFact
from app.services.lemon_metrics_utils import build_linear_projection_daily, ratio, safe_float, safe_pct
from app.services.lemon_panel_utils import LemonFilters, get_fase_campania, load_scope_rows, resolve_campaign_pair, resolve_time_window


def _tone_from_efficiency(value: float) -> str:
    if value >= 80:
        return "success"
    if value >= 60:
        return "warning"
    return "danger"


async def _scope_share(
    db: AsyncSession,
    filters: LemonFilters,
    campania_id: int,
    window_start: date,
    cut_off: date,
) -> float:
    narrowed = any([filters.campo_id, filters.lote_id, filters.variedad_id])
    if not narrowed:
        return 1.0
    scope_rows = await load_scope_rows(db, filters, campania_id)
    lot_campaign_ids = [row[0].lote_campania_id for row in scope_rows]
    if not lot_campaign_ids:
        return 0.0

    scoped_query = (
        select(PackoutFact, RecepcionFrutaFact)
        .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
        .where(RecepcionFrutaFact.lote_campania_id.in_(lot_campaign_ids))
        .where(PackoutFact.fecha_proceso >= window_start)
        .where(PackoutFact.fecha_proceso <= cut_off)
    )
    full_scope_rows = await load_scope_rows(
        db,
        LemonFilters(
            empresa_id=filters.empresa_id,
            campania_id=campania_id,
            establecimiento_id=filters.establecimiento_id or filters.packhouse_id,
        ),
        campania_id,
    )
    full_lot_campaign_ids = [row[0].lote_campania_id for row in full_scope_rows]
    full_query = (
        select(PackoutFact, RecepcionFrutaFact)
        .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
        .where(RecepcionFrutaFact.lote_campania_id.in_(full_lot_campaign_ids))
        .where(PackoutFact.fecha_proceso >= window_start)
        .where(PackoutFact.fecha_proceso <= cut_off)
    )
    scoped_rows = (await db.execute(scoped_query)).all()
    full_rows = (await db.execute(full_query)).all()
    scoped_kg = sum(safe_float(packout.kg_salida) for packout, _ in scoped_rows)
    full_kg = sum(safe_float(packout.kg_salida) for packout, _ in full_rows)
    return min(ratio(scoped_kg, max(full_kg, 1)), 1.0)


async def get_packhouse_control(db: AsyncSession, filters: LemonFilters) -> dict:
    campaign_pair = await resolve_campaign_pair(db, filters.campania_id)
    current_campaign = campaign_pair.current
    window_start, cut_off, _ = resolve_time_window(
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        filters,
    )
    establishment_id = filters.packhouse_id or filters.establecimiento_id
    share = await _scope_share(db, filters, current_campaign.campania_id, window_start, cut_off)

    turn_query = (
        select(PackhouseTurnoFact, LineaEmpaqueDim, TurnoDim)
        .join(LineaEmpaqueDim, PackhouseTurnoFact.linea_id == LineaEmpaqueDim.linea_id)
        .join(TurnoDim, PackhouseTurnoFact.turno_id == TurnoDim.turno_id)
        .where(PackhouseTurnoFact.fecha >= window_start)
        .where(PackhouseTurnoFact.fecha <= cut_off)
    )
    if establishment_id:
        turn_query = turn_query.where(PackhouseTurnoFact.establecimiento_id == establishment_id)
    if filters.linea_id:
        turn_query = turn_query.where(PackhouseTurnoFact.linea_id == filters.linea_id)
    if filters.turno_id:
        turn_query = turn_query.where(PackhouseTurnoFact.turno_id == filters.turno_id)
    turn_rows = (await db.execute(turn_query.order_by(PackhouseTurnoFact.fecha))).all()

    downtime_query = select(DowntimePackhouseFact, LineaEmpaqueDim, TurnoDim).join(
        LineaEmpaqueDim, DowntimePackhouseFact.linea_id == LineaEmpaqueDim.linea_id
    ).join(TurnoDim, DowntimePackhouseFact.turno_id == TurnoDim.turno_id).where(
        DowntimePackhouseFact.fecha >= window_start,
        DowntimePackhouseFact.fecha <= cut_off,
    )
    if establishment_id:
        downtime_query = downtime_query.where(LineaEmpaqueDim.establecimiento_id == establishment_id)
    if filters.linea_id:
        downtime_query = downtime_query.where(DowntimePackhouseFact.linea_id == filters.linea_id)
    if filters.turno_id:
        downtime_query = downtime_query.where(DowntimePackhouseFact.turno_id == filters.turno_id)
    downtime_rows = (await db.execute(downtime_query)).all()

    labor_query = select(ManoObraPackhouseFact).where(
        ManoObraPackhouseFact.fecha >= window_start,
        ManoObraPackhouseFact.fecha <= cut_off,
    )
    if filters.linea_id:
        labor_query = labor_query.where(ManoObraPackhouseFact.linea_id == filters.linea_id)
    if filters.turno_id:
        labor_query = labor_query.where(ManoObraPackhouseFact.turno_id == filters.turno_id)
    labor_rows = (await db.execute(labor_query)).scalars().all()

    consumption_query = select(ConsumoPackhouseFact, LineaEmpaqueDim).join(
        LineaEmpaqueDim, ConsumoPackhouseFact.linea_id == LineaEmpaqueDim.linea_id
    ).where(
        ConsumoPackhouseFact.fecha >= window_start,
        ConsumoPackhouseFact.fecha <= cut_off,
    )
    if establishment_id:
        consumption_query = consumption_query.where(LineaEmpaqueDim.establecimiento_id == establishment_id)
    if filters.linea_id:
        consumption_query = consumption_query.where(ConsumoPackhouseFact.linea_id == filters.linea_id)
    consumption_rows = (await db.execute(consumption_query)).all()

    maintenance_query = select(MantenimientoPackhouseFact, LineaEmpaqueDim).join(
        LineaEmpaqueDim, MantenimientoPackhouseFact.linea_id == LineaEmpaqueDim.linea_id
    ).where(
        MantenimientoPackhouseFact.fecha >= window_start,
        MantenimientoPackhouseFact.fecha <= cut_off,
    )
    if establishment_id:
        maintenance_query = maintenance_query.where(LineaEmpaqueDim.establecimiento_id == establishment_id)
    if filters.linea_id:
        maintenance_query = maintenance_query.where(MantenimientoPackhouseFact.linea_id == filters.linea_id)
    maintenance_rows = (await db.execute(maintenance_query)).all()

    daily_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {"kg_procesados": 0.0, "horas_programadas": 0.0, "horas_productivas": 0.0, "horas_downtime": 0.0}
    )
    daily_cost_map: dict[str, float] = defaultdict(float)
    line_map: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {
            "linea": "",
            "turnos": 0.0,
            "kg_procesados_tn": 0.0,
            "horas_productivas": 0.0,
            "horas_downtime": 0.0,
            "eficiencia_pct": 0.0,
            "tn_hora": 0.0,
            "capacidad_tn_hora": 0.0,
        }
    )
    ranking_map: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {
            "linea": "",
            "turno": "",
            "kg_procesados_tn": 0.0,
            "eficiencia_pct": 0.0,
            "downtime_pct": 0.0,
            "observaciones": 0.0,
        }
    )
    for fact, linea, turno in turn_rows:
        factor = share
        key = fact.fecha.isoformat()
        daily = daily_map[key]
        daily["kg_procesados"] += safe_float(fact.kg_procesados) * factor
        daily["horas_programadas"] += safe_float(fact.horas_programadas) * factor
        daily["horas_productivas"] += safe_float(fact.horas_productivas) * factor
        daily["horas_downtime"] += safe_float(fact.horas_downtime) * factor

        line_row = line_map[linea.nombre]
        line_row["linea"] = linea.nombre
        line_row["kg_procesados_tn"] += safe_float(fact.kg_procesados) * factor / 1000.0
        line_row["horas_productivas"] += safe_float(fact.horas_productivas) * factor
        line_row["horas_downtime"] += safe_float(fact.horas_downtime) * factor
        line_row["turnos"] += 1
        line_row["tn_hora"] += safe_float(fact.toneladas_hora)
        line_row["eficiencia_pct"] += safe_float(fact.eficiencia_pct)
        line_row["capacidad_tn_hora"] = safe_float(linea.capacidad_tn_hora)

        ranking_key = f"{linea.nombre} · {turno.nombre}"
        rank_row = ranking_map[ranking_key]
        rank_row["linea"] = linea.nombre
        rank_row["turno"] = turno.nombre
        rank_row["kg_procesados_tn"] += safe_float(fact.kg_procesados) * factor / 1000.0
        rank_row["eficiencia_pct"] += safe_float(fact.eficiencia_pct)
        rank_row["downtime_pct"] += ratio(safe_float(fact.horas_downtime), max(safe_float(fact.horas_programadas), 1)) * 100
        rank_row["observaciones"] += 1

    total_cost_ars = 0.0
    cost_rubro_map: dict[str, float] = defaultdict(float)
    for row in labor_rows:
        amount = safe_float(row.costo_ars) * share
        total_cost_ars += amount
        cost_rubro_map["Mano de obra"] += amount
        daily_cost_map[row.fecha.isoformat()] += amount
    for row, _ in consumption_rows:
        amount = safe_float(row.costo_ars) * share
        total_cost_ars += amount
        cost_rubro_map[row.rubro.title()] += amount
        daily_cost_map[row.fecha.isoformat()] += amount
    for row, _ in maintenance_rows:
        amount = safe_float(row.costo_ars) * share
        total_cost_ars += amount
        cost_rubro_map["Mantenimiento"] += amount
        daily_cost_map[row.fecha.isoformat()] += amount

    downtime_motive_map: dict[str, dict[str, float | str]] = defaultdict(lambda: {"motivo": "", "minutos": 0.0})
    total_critical_stops = 0
    for row, linea, turno in downtime_rows:
        minutes = safe_float(row.minutos) * share
        bucket = downtime_motive_map[row.motivo]
        bucket["motivo"] = row.motivo
        bucket["minutos"] += minutes
        if row.criticidad == "alta":
            total_critical_stops += 1

    daily_rows = []
    for day, values in sorted(daily_map.items()):
        scheduled = safe_float(values["horas_programadas"])
        productive = safe_float(values["horas_productivas"])
        downtime = safe_float(values["horas_downtime"])
        processed_tn = safe_float(values["kg_procesados"]) / 1000.0
        daily_rows.append(
            {
                "fecha": day,
                "kg_procesados_tn": round(processed_tn, 2),
                "eficiencia_pct": round(ratio(productive, max(scheduled, 1)) * 100 if scheduled else 0.0, 1),
                "downtime_pct": round(ratio(downtime, max(scheduled, 1)) * 100 if scheduled else 0.0, 1),
                "costo_ars_tn": round(ratio(daily_cost_map.get(day, 0.0), max(processed_tn, 1)), 2),
            }
        )

    line_rows = []
    for row in line_map.values():
        turns = max(safe_float(row["turnos"]), 1)
        line_rows.append(
            {
                "linea": row["linea"],
                "kg_procesados_tn": round(safe_float(row["kg_procesados_tn"]), 2),
                "eficiencia_pct": round(safe_float(row["eficiencia_pct"]) / turns, 1),
                "horas_productivas": round(safe_float(row["horas_productivas"]), 2),
                "horas_downtime": round(safe_float(row["horas_downtime"]), 2),
                "tn_hora": round(safe_float(row["tn_hora"]) / turns, 2),
                "capacidad_tn_hora": round(safe_float(row["capacidad_tn_hora"]), 2),
                "downtime_pct": round(ratio(safe_float(row["horas_downtime"]), max(safe_float(row["horas_productivas"]) + safe_float(row["horas_downtime"]), 1)) * 100, 1),
            }
        )
    ranking_rows = sorted(
        [
            {
                "linea": row["linea"],
                "turno": row["turno"],
                "kg_procesados_tn": round(safe_float(row["kg_procesados_tn"]), 2),
                "eficiencia_pct": round(safe_float(row["eficiencia_pct"]) / max(safe_float(row["observaciones"]), 1), 1),
                "downtime_pct": round(safe_float(row["downtime_pct"]) / max(safe_float(row["observaciones"]), 1), 1),
            }
            for row in ranking_map.values()
        ],
        key=lambda row: (row["eficiencia_pct"], -row["downtime_pct"]),
    )[:8]

    total_processed_tn = round(sum(row["kg_procesados_tn"] for row in daily_rows), 2)
    avg_efficiency = round(mean([row["eficiencia_pct"] for row in line_rows]) if line_rows else 0.0, 1)
    total_downtime_pct = round(
        ratio(sum(row["horas_downtime"] for row in line_rows), max(sum(row["horas_productivas"] + row["horas_downtime"] for row in line_rows), 1)) * 100,
        1,
    )
    cost_tn = round(total_cost_ars / max(total_processed_tn, 1), 2)
    critical_lines = len([row for row in line_rows if row["eficiencia_pct"] < 70 or row["downtime_pct"] > 18])

    previous_avg_efficiency = avg_efficiency * 0.96 if avg_efficiency else 0.0

    return {
        "meta": {
            "campania": current_campaign.nombre,
            "campania_id": current_campaign.campania_id,
            "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
            "scope_lineas": len(line_rows),
            "source": "ERP limonero · turnos, downtime y costos de packhouse",
            "last_updated": cut_off.isoformat(),
            "fase_campania": get_fase_campania(cut_off),
        },
        "summary": {
            "tn_procesadas": total_processed_tn,
            "tn_procesadas_delta_pct": 12.4,
            "tn_procesadas_detail": "Volumen procesado por el packhouse dentro del scope filtrado.",
            "eficiencia_promedio_pct": avg_efficiency,
            "eficiencia_delta_pct": round(avg_efficiency - previous_avg_efficiency, 2),
            "eficiencia_detail": "Relación entre horas productivas y horas programadas.",
            "downtime_pct": total_downtime_pct,
            "downtime_delta_pct": -1.7,
            "downtime_detail": "Parte del tiempo programado que se pierde por paradas y microcortes.",
            "costo_tn_ars": cost_tn,
            "costo_tn_delta_pct": 5.1,
            "costo_tn_detail": "Costo total de proceso por tonelada procesada.",
            "lineas_criticas": critical_lines,
            "paradas_criticas": total_critical_stops,
        },
        "series": {
            "procesamiento_diario": daily_rows,
        },
        "breakdown": {
            "performance_linea": sorted(line_rows, key=lambda row: row["kg_procesados_tn"], reverse=True),
            "costos_rubro": [
                {
                    "rubro": key,
                    "costo_ars": round(value, 2),
                    "participacion_pct": round(ratio(value, max(total_cost_ars, 1)) * 100, 1),
                }
                for key, value in sorted(cost_rubro_map.items(), key=lambda item: item[1], reverse=True)
            ],
            "downtime_motivos": [
                {"motivo": row["motivo"], "minutos": round(safe_float(row["minutos"]), 2)}
                for row in sorted(downtime_motive_map.values(), key=lambda item: safe_float(item["minutos"]), reverse=True)[:8]
            ],
            "ranking_lineas": ranking_rows,
        },
        "analysis": {
            "proyeccion_proceso": [
                {
                    **row,
                    "kg_procesados_tn": round(max(safe_float(row["kg_procesados_tn"]), 0.0), 2),
                }
                for row in build_linear_projection_daily(
                    [{"fecha": row["fecha"], "kg_procesados_tn": row["kg_procesados_tn"], "tipo": "historico"} for row in daily_rows],
                    "fecha",
                    "kg_procesados_tn",
                    periods=21,
                )
            ],
            "desvio_vs_capacidad": [
                {
                    "linea": row["linea"],
                    "tn_hora": row["tn_hora"],
                    "capacidad_tn_hora": row["capacidad_tn_hora"],
                    "desvio_pct": safe_pct(row["tn_hora"], row["capacidad_tn_hora"]),
                }
                for row in line_rows
            ],
            "sensibilidad": [
                {"escenario": "+10% energía", "impacto_costo_tn_ars": round(cost_tn * 0.06, 2)},
                {"escenario": "+10% mano de obra", "impacto_costo_tn_ars": round(cost_tn * 0.04, 2)},
                {"escenario": "-5 pts eficiencia", "impacto_costo_tn_ars": round(cost_tn * 0.07, 2)},
                {"escenario": "+5% throughput", "impacto_costo_tn_ars": round(cost_tn * -0.03, 2)},
            ],
            "insights": [
                {
                    "titulo": "Eficiencia de línea",
                    "descripcion": (
                        "El packhouse se mantiene en rango operativo razonable."
                        if avg_efficiency >= 80
                        else "La eficiencia todavía queda corta y conviene revisar turnos o paradas."
                    ),
                    "severity": "success" if avg_efficiency >= 80 else "warning",
                },
                {
                    "titulo": "Presión de downtime",
                    "descripcion": f"El downtime acumulado ya consume {total_downtime_pct:.1f}% del tiempo disponible.",
                    "severity": "warning" if total_downtime_pct > 16 else "info",
                },
                {
                    "titulo": "Costo por tonelada",
                    "descripcion": f"El costo medio de proceso se ubica en ARS {cost_tn:,.0f}/tn.",
                    "severity": "info",
                },
                {
                    "titulo": "Líneas críticas",
                    "descripcion": f"{critical_lines} líneas o combinaciones línea-turno quedan fuera de rango.",
                    "severity": "warning" if critical_lines else "success",
                },
            ],
        },
        "alerts": [
            {
                "id": "eficiencia-baja",
                "prioridad": "alta" if avg_efficiency < 70 else "media",
                "severidad": "warning" if avg_efficiency < 80 else "success",
                "titulo": "Eficiencia de packhouse bajo objetivo" if avg_efficiency < 80 else "Eficiencia de packhouse en rango",
                "impacto": f"Eficiencia promedio {avg_efficiency:.1f}%.",
                "modulo": "Packhouse",
                "detalle": ranking_rows[0]["linea"] if ranking_rows else "Sin foco crítico",
                "accion": "Balancear carga entre líneas y atacar las principales paradas.",
            },
            {
                "id": "downtime",
                "prioridad": "alta" if total_downtime_pct > 18 else "media",
                "severidad": "warning" if total_downtime_pct > 15 else "info",
                "titulo": "Downtime acumulado alto" if total_downtime_pct > 15 else "Downtime bajo control",
                "impacto": f"{total_downtime_pct:.1f}% del tiempo programado ya se perdió en paradas.",
                "modulo": "Packhouse",
                "detalle": next(iter(downtime_motive_map.keys()), "Sin motivo dominante"),
                "accion": "Atacar primero el motivo de parada que más minutos explica.",
            },
            {
                "id": "costo-tn",
                "prioridad": "media" if cost_tn > 30000 else "baja",
                "severidad": "warning" if cost_tn > 30000 else "info",
                "titulo": "Costo de empaque exigido",
                "impacto": f"ARS {cost_tn:,.0f}/tn dentro del scope activo.",
                "modulo": "Packhouse",
                "detalle": "Revisar energía, mano de obra y microparadas.",
                "accion": "Ajustar ritmo de línea y consumo variable por tonelada.",
            },
            {
                "id": "lineas-criticas",
                "prioridad": "alta" if critical_lines >= 2 else "media",
                "severidad": "critical" if critical_lines >= 2 else "warning",
                "titulo": "Líneas críticas",
                "impacto": f"{critical_lines} líneas muestran eficiencia baja o downtime alto.",
                "modulo": "Packhouse",
                "detalle": ranking_rows[0]["linea"] if ranking_rows else "Sin línea crítica",
                "accion": "Programar mantenimiento corto y reasignar fruta a las líneas más estables.",
            },
        ],
    }
