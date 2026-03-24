from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.establecimiento import Establecimiento
from app.models.erp_operational import DisponibilidadEquipo, HorasMaquina
from app.models.mantenimiento import Mantenimiento
from app.models.maquinaria import Maquinaria
from app.services.decision_data import (
    load_alert_rows,
    load_fleet_support_rows,
    load_task_rows,
)

STATE_MAP = {
    "operativo": "operativo",
    "mantenimiento": "en_reparacion",
    "baja": "fuera_de_servicio",
}

STATE_FILTER_MAP = {
    "operativo": "operativo",
    "en_reparacion": "mantenimiento",
    "fuera_de_servicio": "baja",
    "mantenimiento": "mantenimiento",
    "baja": "baja",
}

PRODUCTIVITY_RATES = {
    "sembradora": 18,
    "cosechadora": 12,
    "pulverizadora": 24,
    "tractor": 20,
    "tolva": 26,
}


def _month_key(value: date | datetime) -> str:
    return value.strftime("%Y-%m")


def _iter_month_keys(start_key: str, end_key: str):
    year, month = map(int, start_key.split("-"))
    end_year, end_month = map(int, end_key.split("-"))

    while (year, month) <= (end_year, end_month):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month > 12:
            month = 1
            year += 1


def _alert_level(hours_left: Optional[float]) -> str:
    if hours_left is None:
        return "verde"
    if hours_left <= 50:
        return "rojo"
    if hours_left <= 120:
        return "amarillo"
    return "verde"


async def _load_maquinaria_payload(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    estado: Optional[str] = None,
):
    query = (
        select(Maquinaria, Establecimiento)
        .join(Establecimiento, Maquinaria.establecimiento_id == Establecimiento.id)
    )
    if empresa_id:
        query = query.where(Establecimiento.empresa_id == empresa_id)
    if establecimiento_id:
        query = query.where(Maquinaria.establecimiento_id == establecimiento_id)
    if estado:
        query = query.where(Maquinaria.estado == STATE_FILTER_MAP.get(estado, estado))

    rows = (await db.execute(query)).all()
    maquinas = [row[0] for row in rows]
    maquinaria_ids = [maquina.id for maquina in maquinas]

    latest_by_machine: dict[int, Mantenimiento] = {}
    monthly_costs: dict[int, float] = defaultdict(float)
    rolling_costs: dict[int, float] = defaultdict(float)
    last_update: Optional[date] = None

    if maquinaria_ids:
        maint_query = (
            select(Mantenimiento)
            .where(Mantenimiento.maquinaria_id.in_(maquinaria_ids))
            .order_by(Mantenimiento.maquinaria_id, Mantenimiento.fecha.desc())
        )
        mantenimientos = (await db.execute(maint_query)).scalars().all()
        reference_date = max(
            (mantenimiento.fecha for mantenimiento in mantenimientos),
            default=date.today(),
        )
        six_months_ago = reference_date - timedelta(days=180)
        current_month = reference_date.month
        current_year = reference_date.year

        for mantenimiento in mantenimientos:
            latest_by_machine.setdefault(mantenimiento.maquinaria_id, mantenimiento)
            if (
                mantenimiento.fecha.month == current_month
                and mantenimiento.fecha.year == current_year
            ):
                monthly_costs[mantenimiento.maquinaria_id] += mantenimiento.costo or 0
            if mantenimiento.fecha >= six_months_ago:
                rolling_costs[mantenimiento.maquinaria_id] += mantenimiento.costo or 0
            if last_update is None or mantenimiento.fecha > last_update:
                last_update = mantenimiento.fecha

    items = []
    for maquinaria, establecimiento in rows:
        ultimo = latest_by_machine.get(maquinaria.id)
        horas_ultimo_service = (
            ultimo.horas_maquina if ultimo and ultimo.horas_maquina else 0
        )
        proximo_service_horas = (
            ultimo.proximo_service_hs if ultimo and ultimo.proximo_service_hs else None
        )
        horas_restantes = (
            proximo_service_horas - (maquinaria.horas_totales or 0)
            if proximo_service_horas is not None
            else None
        )
        dias_para_service = (
            max(int(round(horas_restantes / 8)), 0)
            if horas_restantes is not None
            else None
        )
        alerta_service = _alert_level(horas_restantes)
        costo_operativo_mes = monthly_costs[maquinaria.id]
        if costo_operativo_mes == 0 and rolling_costs[maquinaria.id] > 0:
            costo_operativo_mes = rolling_costs[maquinaria.id] / 6

        items.append(
            {
                "id": str(maquinaria.id),
                "nombre": f"{maquinaria.marca} {maquinaria.modelo}",
                "tipo": maquinaria.tipo,
                "marca": maquinaria.marca,
                "modelo": maquinaria.modelo,
                "anio": maquinaria.anio,
                "estado": STATE_MAP.get(maquinaria.estado, maquinaria.estado),
                "horas_totales": round(maquinaria.horas_totales or 0, 1),
                "horas_ultimo_service": round(horas_ultimo_service or 0, 1),
                "proximo_service_horas": (
                    round(proximo_service_horas, 1)
                    if proximo_service_horas is not None
                    else None
                ),
                "dias_para_service": dias_para_service,
                "costo_operativo_mes": round(costo_operativo_mes, 2),
                "alerta_service": alerta_service,
                "establecimiento": establecimiento.nombre,
            }
        )

    items.sort(
        key=lambda item: (
            item["dias_para_service"] is None,
            item["dias_para_service"] or 9999,
        )
    )
    return items, last_update


async def get_maquinaria_resumen(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
):
    maquinas, last_update = await _load_maquinaria_payload(
        db=db,
        empresa_id=empresa_id,
        establecimiento_id=establecimiento_id,
    )
    fleet_rows, downtime_rows, consumos, service_rows = await load_fleet_support_rows(
        db=db,
        empresa_id=empresa_id,
        establecimiento_id=establecimiento_id,
    )
    maquinaria_ids = [int(maquina["id"]) for maquina in maquinas]
    disponibilidad_rows = []
    horas_rows = []
    if maquinaria_ids:
        disponibilidad_rows = (
            await db.execute(
                select(DisponibilidadEquipo).where(
                    DisponibilidadEquipo.maquinaria_id.in_(maquinaria_ids)
                )
            )
        ).scalars().all()
        horas_rows = (
            await db.execute(
                select(HorasMaquina).where(HorasMaquina.maquinaria_id.in_(maquinaria_ids))
            )
        ).scalars().all()
    alert_rows = await load_alert_rows(db=db, modules=("maquinaria",))
    task_rows = await load_task_rows(db=db, modules=("maquinaria",))

    downtime_by_machine: dict[int, dict[str, float]] = defaultdict(
        lambda: {"horas": 0.0, "impacto_ha": 0.0, "count": 0.0}
    )
    for downtime in downtime_rows:
        bucket = downtime_by_machine[downtime.maquinaria_id]
        bucket["horas"] += downtime.horas_downtime or 0
        bucket["impacto_ha"] += downtime.impacto_ha or 0
        bucket["count"] += 1

    consumo_by_machine: dict[int, dict[str, float]] = defaultdict(
        lambda: {"litros": 0.0, "hectareas": 0.0, "horas_productivas": 0.0}
    )
    for consumo in consumos:
        bucket = consumo_by_machine[consumo.maquinaria_id]
        bucket["litros"] += consumo.litros or 0
        bucket["hectareas"] += consumo.hectareas or 0
        rate = PRODUCTIVITY_RATES.get(
            next(
                (
                    maquina["tipo"]
                    for maquina in maquinas
                    if int(maquina["id"]) == consumo.maquinaria_id
                ),
                "tractor",
            ),
            20,
        )
        bucket["horas_productivas"] += (
            (consumo.hectareas or 0) / rate if rate else 0
        )

    next_service_by_machine = {}
    today = date.today()
    for service in service_rows:
        if service.completado:
            continue
        current = next_service_by_machine.get(service.maquinaria_id)
        if current is None or service.fecha_programada < current.fecha_programada:
            next_service_by_machine[service.maquinaria_id] = service

    riesgo_total_ha = 0.0
    utilization_values = []
    downtime_total = 0.0
    combustible_values = []
    bottlenecks = []

    for maquina in maquinas:
        machine_id = int(maquina["id"])
        downtime_data = downtime_by_machine.get(machine_id, {})
        consumo_data = consumo_by_machine.get(machine_id, {})
        service = next_service_by_machine.get(machine_id)

        horas_productivas = round(consumo_data.get("horas_productivas", 0), 1)
        horas_improductivas = round(downtime_data.get("horas", 0), 1)
        utilization_pct = round(
            (horas_productivas / (horas_productivas + horas_improductivas)) * 100,
            1,
        ) if horas_productivas or horas_improductivas else 0
        combustible_ha = round(
            consumo_data.get("litros", 0) / consumo_data.get("hectareas", 1),
            2,
        ) if consumo_data.get("hectareas") else 0
        costo_por_hora = round(
            maquina["costo_operativo_mes"] / horas_productivas,
            2,
        ) if horas_productivas else maquina["costo_operativo_mes"]
        criticidad = (
            "alta"
            if maquina["tipo"] in {"sembradora", "cosechadora"}
            else "media"
        )
        score = 0
        if maquina["alerta_service"] == "rojo":
            score += 3
        elif maquina["alerta_service"] == "amarillo":
            score += 2
        if horas_improductivas > 8:
            score += 2
        elif horas_improductivas > 0:
            score += 1
        if criticidad == "alta":
            score += 2

        riesgo_total_ha += downtime_data.get("impacto_ha", 0)
        downtime_total += horas_improductivas
        if utilization_pct:
            utilization_values.append(utilization_pct)
        if combustible_ha:
            combustible_values.append(combustible_ha)

        maquina["horas_productivas"] = horas_productivas
        maquina["horas_improductivas"] = horas_improductivas
        maquina["utilizacion_pct"] = utilization_pct
        maquina["combustible_ha"] = combustible_ha
        maquina["costo_por_hora"] = costo_por_hora
        maquina["impacto_operativo_ha"] = round(downtime_data.get("impacto_ha", 0), 1)
        maquina["service_proximo"] = service.fecha_programada.isoformat() if service else None
        maquina["riesgo_si_falla"] = service.riesgo_si_falla if service else None
        maquina["es_cuello_botella"] = score >= 5

        if score >= 4:
            bottlenecks.append(
                {
                    "maquina": maquina["nombre"],
                    "tipo": maquina["tipo"],
                    "establecimiento": maquina["establecimiento"],
                    "utilizacion_pct": utilization_pct,
                    "downtime_horas": horas_improductivas,
                    "combustible_ha": combustible_ha,
                    "costo_por_hora": costo_por_hora,
                    "impacto_operativo_ha": round(downtime_data.get("impacto_ha", 0), 1),
                    "riesgo_si_falla": service.riesgo_si_falla if service else "Riesgo operativo elevado",
                    "severity": "critical" if score >= 6 else "warning",
                    "score": score,
                }
            )

    bottlenecks.sort(key=lambda item: (-item["score"], -item["impacto_operativo_ha"]))

    service_schedule = []
    for service in service_rows:
        if service.completado:
            continue
        maquina = next(
            (item for item in maquinas if int(item["id"]) == service.maquinaria_id),
            None,
        )
        if not maquina:
            continue
        service_schedule.append(
            {
                "maquina": maquina["nombre"],
                "tipo": maquina["tipo"],
                "fecha_programada": service.fecha_programada.isoformat(),
                "dias_restantes": (service.fecha_programada - today).days,
                "tipo_service": service.tipo_service,
                "criticidad_operativa": service.criticidad_operativa,
                "riesgo_si_falla": service.riesgo_si_falla,
            }
        )
    service_schedule.sort(key=lambda item: item["dias_restantes"])

    monthly_series: dict[str, dict[str, float | str | int]] = defaultdict(
        lambda: {
            "mes": "",
            "hist_horas_productivas": 0.0,
            "hist_downtime_horas": 0.0,
            "avail_horas_productivas": 0.0,
            "avail_downtime_horas": 0.0,
            "estimated_horas_productivas": 0.0,
            "combustible_litros": 0.0,
            "availability_points": 0,
        }
    )
    update_candidates = [last_update] if last_update else []

    for horas in horas_rows:
        if not horas.fecha:
            continue
        key = _month_key(horas.fecha)
        bucket = monthly_series[key]
        bucket["mes"] = key
        if horas.tipo_hora == "productiva":
            bucket["hist_horas_productivas"] += horas.horas or 0
        else:
            bucket["hist_downtime_horas"] += horas.horas or 0
        update_candidates.append(horas.fecha)

    for disponibilidad in disponibilidad_rows:
        if not disponibilidad.fecha:
            continue
        key = _month_key(disponibilidad.fecha)
        bucket = monthly_series[key]
        bucket["mes"] = key
        bucket["avail_horas_productivas"] += disponibilidad.horas_productivas or 0
        bucket["avail_downtime_horas"] += disponibilidad.downtime_horas or 0
        bucket["availability_points"] += 1
        update_candidates.append(disponibilidad.fecha)

    for consumo in consumos:
        if not consumo.fecha:
            continue
        key = _month_key(consumo.fecha)
        bucket = monthly_series[key]
        bucket["mes"] = key
        rate = PRODUCTIVITY_RATES.get(
            next(
                (
                    maquina["tipo"]
                    for maquina in maquinas
                    if int(maquina["id"]) == consumo.maquinaria_id
                ),
                "tractor",
            ),
            20,
        )
        bucket["estimated_horas_productivas"] += (
            (consumo.hectareas or 0) / rate if rate else 0
        )
        bucket["combustible_litros"] += consumo.litros or 0
        update_candidates.append(consumo.fecha)

    for downtime in downtime_rows:
        if not downtime.fecha_inicio:
            continue
        key = _month_key(downtime.fecha_inicio)
        bucket = monthly_series[key]
        bucket["mes"] = key
        if not bucket["availability_points"]:
            bucket["hist_downtime_horas"] += downtime.horas_downtime or 0
        update_candidates.append(downtime.fecha_inicio.date())

    if update_candidates:
        last_update = max(update_candidates)

    sorted_months = sorted(monthly_series.keys())
    if sorted_months:
        for month_key in _iter_month_keys(sorted_months[0], sorted_months[-1]):
            monthly_series[month_key]["mes"] = month_key

    series = []
    for mes in sorted(monthly_series.keys()):
        bucket = monthly_series[mes]
        use_availability = int(bucket["availability_points"]) > 0
        horas_productivas = float(
            bucket["avail_horas_productivas"]
            if use_availability
            else (
                bucket["hist_horas_productivas"]
                if bucket["hist_horas_productivas"]
                else bucket["estimated_horas_productivas"]
            )
        )
        downtime_horas = float(
            bucket["avail_downtime_horas"]
            if use_availability
            else bucket["hist_downtime_horas"]
        )
        total_horas = horas_productivas + downtime_horas
        series.append(
            {
                "mes": mes,
                "horas_productivas": round(horas_productivas, 1),
                "downtime_horas": round(downtime_horas, 1),
                "combustible_litros": round(float(bucket["combustible_litros"]), 1),
                "disponibilidad_pct": round(
                    (horas_productivas / total_horas) * 100,
                    1,
                ) if total_horas else 0,
            }
        )

    total = len(maquinas)
    equipos_operativos = len(
        [maquina for maquina in maquinas if maquina["estado"] == "operativo"]
    )
    horas_promedio = round(
        sum(maquina["horas_totales"] for maquina in maquinas) / total if total else 0,
        1,
    )
    costo_operativo = round(
        sum(maquina["costo_operativo_mes"] for maquina in maquinas),
        2,
    )
    proximos_services = len(
        [maquina for maquina in maquinas if maquina["alerta_service"] != "verde"]
    )

    alerts = [
        {
            "id": maquina["id"],
            "nombre": maquina["nombre"],
            "mensaje": (
                "Service urgente"
                if maquina["alerta_service"] == "rojo"
                else "Service próximo"
            ),
            "severidad": (
                "critical" if maquina["alerta_service"] == "rojo" else "warning"
            ),
        }
        for maquina in maquinas
        if maquina["alerta_service"] != "verde"
    ]
    for alert in alert_rows[:2]:
        alerts.append(
            {
                "id": f"operativa-{alert.id}",
                "nombre": alert.titulo,
                "mensaje": alert.descripcion,
                "severidad": alert.severidad,
            }
        )

    actions = []
    if bottlenecks:
        first = bottlenecks[0]
        actions.append(
            {
                "titulo": f"Destrabar cuello de botella: {first['maquina']}",
                "descripcion": first["riesgo_si_falla"],
                "owner": "Taller y operaciones",
                "impacto": (
                    f"Protege hasta {first['impacto_operativo_ha']:.0f} ha de capacidad operativa"
                ),
                "severity": first["severity"],
            }
        )
    if service_schedule:
        next_service = service_schedule[0]
        actions.append(
            {
                "titulo": f"Confirmar service de {next_service['maquina']}",
                "descripcion": (
                    f"Vence en {next_service['dias_restantes']} días con criticidad "
                    f"{next_service['criticidad_operativa']}."
                ),
                "owner": "Mantenimiento",
                "impacto": "Reduce probabilidad de parada en plena labor",
                "severity": (
                    "critical"
                    if next_service["criticidad_operativa"] == "alta"
                    and next_service["dias_restantes"] <= 10
                    else "warning"
                ),
            }
        )
    for task in task_rows[:2]:
        actions.append(
            {
                "titulo": task.descripcion,
                "descripcion": task.impacto or "Tarea crítica de flota",
                "owner": task.responsable or "Taller",
                "impacto": task.impacto or "Capacidad operativa",
                "severity": "critical" if task.prioridad == "alta" else "warning",
            }
        )

    return {
        "summary": {
            "equipos_operativos": equipos_operativos,
            "horas_promedio": horas_promedio,
            "costo_operativo": costo_operativo,
            "proximos_services": proximos_services,
            "utilizacion_promedio_pct": round(
                sum(utilization_values) / len(utilization_values),
                1,
            ) if utilization_values else 0,
            "downtime_horas": round(downtime_total, 1),
            "combustible_promedio_ha": round(
                sum(combustible_values) / len(combustible_values),
                2,
            ) if combustible_values else 0,
            "equipos_cuello_botella": len(bottlenecks),
            "impacto_operativo_ha": round(riesgo_total_ha, 1),
        },
        "maquinas": maquinas,
        "series": series,
        "bottlenecks": bottlenecks[:8],
        "service_schedule": service_schedule[:8],
        "alerts": alerts[:6],
        "actions": actions[:5],
        "ultima_actualizacion": (
            datetime.combine(last_update, datetime.min.time()).isoformat()
            if last_update
            else datetime.now().isoformat()
        ),
    }


async def get_equipos_list(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    estado: Optional[str] = None,
    establecimiento_id: Optional[int] = None,
):
    maquinas, _ = await _load_maquinaria_payload(
        db=db,
        empresa_id=empresa_id,
        establecimiento_id=establecimiento_id,
        estado=estado,
    )
    return {"total": len(maquinas), "items": maquinas}
