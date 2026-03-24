from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.erp_operational import CuentaCobrar, CuentaPagar, Liquidacion, ContratoVenta
from app.models.flujo_financiero import FlujoCaja
from app.models.venta import Venta
from app.services.campaign_scope import resolve_campaign_id
from app.services.decision_data import (
    load_alert_rows,
    load_budget_rows,
    load_task_rows,
)

MONTH_FIELDS = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def _next_month(value: date) -> date:
    if value.month == 12:
        return date(value.year + 1, 1, 1)
    return date(value.year, value.month + 1, 1)


def _monthly_series(flujos: list[FlujoCaja]) -> list[dict]:
    month_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {"ingresos": 0.0, "egresos": 0.0}
    )

    for flujo in flujos:
        if not flujo.fecha:
            continue
        key = flujo.fecha.strftime("%Y-%m")
        if flujo.tipo == "ingreso":
            month_map[key]["ingresos"] += flujo.monto or 0
        else:
            month_map[key]["egresos"] += flujo.monto or 0

    series = []
    for mes, valores in sorted(month_map.items())[-12:]:
        neto = valores["ingresos"] - valores["egresos"]
        series.append(
            {
                "mes": mes,
                "ingresos": round(valores["ingresos"], 2),
                "egresos": round(valores["egresos"], 2),
                "neto": round(neto, 2),
            }
        )
    return series


def _project_series(series: list[dict]) -> list[dict]:
    if not series:
        return []

    reales = series[-6:]
    promedio_ingresos = sum(item["ingresos"] for item in reales) / len(reales)
    promedio_egresos = sum(item["egresos"] for item in reales) / len(reales)

    last_period = datetime.strptime(f"{series[-1]['mes']}-01", "%Y-%m-%d").date()
    proyectados = list(series)

    current_period = last_period
    for _ in range(3):
        current_period = _next_month(current_period)
        proyectados.append(
            {
                "mes": current_period.strftime("%Y-%m"),
                "ingresos": round(promedio_ingresos, 2),
                "egresos": round(promedio_egresos, 2),
                "neto": round(promedio_ingresos - promedio_egresos, 2),
                "proyectado": True,
            }
        )

    return proyectados


def _cash_projection(series: list[dict]) -> list[dict]:
    saldo = 0.0
    projection = []
    for item in series:
        saldo += item["neto"]
        projection.append(
            {
                **item,
                "saldo_acumulado": round(saldo, 2),
            }
        )
    return projection


def _scenario(label: str, margin_value: float, base_margin: float) -> dict:
    delta_pct = round(
        ((margin_value - base_margin) / base_margin) * 100,
        1,
    ) if base_margin else 0
    return {
        "scenario": label,
        "margen_total": round(margin_value, 2),
        "delta_pct": delta_pct,
    }


async def get_finanzas_resumen(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
):
    resolved_campania_id = await resolve_campaign_id(db=db, campania_id=campania_id)

    query = select(FlujoCaja).order_by(FlujoCaja.fecha)
    if empresa_id:
        query = query.where(FlujoCaja.empresa_id == empresa_id)
    if resolved_campania_id:
        query = query.where(FlujoCaja.campania_id == resolved_campania_id)
    flujos = (await db.execute(query)).scalars().all()

    ventas_query = select(Venta)
    if empresa_id:
        ventas_query = ventas_query.where(Venta.empresa_id == empresa_id)
    if resolved_campania_id:
        ventas_query = ventas_query.where(Venta.campania_id == resolved_campania_id)
    ventas = (await db.execute(ventas_query)).scalars().all()

    budget_rows = await load_budget_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
    )
    alert_rows = await load_alert_rows(db=db, modules=("finanzas",))
    task_rows = await load_task_rows(db=db, modules=("finanzas",))

    ingresos_total = sum(
        (flujo.monto or 0) for flujo in flujos if flujo.tipo == "ingreso"
    )
    egresos_total = sum(
        (flujo.monto or 0) for flujo in flujos if flujo.tipo == "egreso"
    )
    capital_trabajo = round(ingresos_total - egresos_total, 2)

    flujo_mensual_real = _monthly_series(flujos)
    flujo_mensual = _project_series(flujo_mensual_real)
    cash_projection = _cash_projection(flujo_mensual)
    flujo_neto = flujo_mensual_real[-1]["neto"] if flujo_mensual_real else 0

    cuentas_cobrar_query = select(CuentaCobrar)
    if empresa_id:
        cuentas_cobrar_query = cuentas_cobrar_query.where(CuentaCobrar.empresa_id == empresa_id)
    if resolved_campania_id:
        cuentas_cobrar_query = (
            cuentas_cobrar_query
            .join(Liquidacion, CuentaCobrar.liquidacion_id == Liquidacion.id)
            .join(ContratoVenta, Liquidacion.contrato_venta_id == ContratoVenta.id)
            .where(ContratoVenta.campania_id == resolved_campania_id)
        )
    cuentas_cobrar_rows = (await db.execute(cuentas_cobrar_query)).scalars().all()

    cuentas_pagar_query = select(CuentaPagar)
    if empresa_id:
        cuentas_pagar_query = cuentas_pagar_query.where(CuentaPagar.empresa_id == empresa_id)
    cuentas_pagar_rows = (await db.execute(cuentas_pagar_query)).scalars().all()

    cuentas_a_cobrar = round(
        sum(
            (cuenta.saldo or 0)
            for cuenta in cuentas_cobrar_rows
            if cuenta.estado in {"pendiente", "parcial"}
        ),
        2,
    )

    reference_date = max(
        (flujo.fecha for flujo in flujos if flujo.fecha),
        default=date.today(),
    )
    cuentas_pagar_abiertas = [
        cuenta
        for cuenta in cuentas_pagar_rows
        if cuenta.estado in {"pendiente", "parcial"} and (cuenta.saldo or 0) > 0
    ]
    compromisos_futuros = sum(
        (cuenta.saldo or 0)
        for cuenta in cuentas_pagar_abiertas
        if not cuenta.fecha_vencimiento or cuenta.fecha_vencimiento <= reference_date + timedelta(days=90)
    )
    capital_trabajo_comprometido = sum(
        (cuenta.saldo or 0)
        for cuenta in cuentas_pagar_abiertas
        if not cuenta.fecha_vencimiento or cuenta.fecha_vencimiento <= reference_date + timedelta(days=60)
    )
    deuda_corto_plazo = sum(
        (cuenta.saldo or 0)
        for cuenta in cuentas_pagar_abiertas
        if not cuenta.fecha_vencimiento or cuenta.fecha_vencimiento <= reference_date + timedelta(days=45)
    )

    if compromisos_futuros == 0:
        compromisos_futuros = sum(
            (flujo.monto or 0)
            for flujo in flujos
            if flujo.tipo == "egreso"
            and flujo.fecha
            and flujo.fecha >= reference_date - timedelta(days=90)
            and flujo.categoria in {"credito", "impuesto", "salarios", "alquiler"}
        )

    current_year = reference_date.year
    pivot: dict[tuple[str, str], dict[str, float]] = defaultdict(
        lambda: {
            "categoria": "",
            "tipo": "",
            "enero": 0.0,
            "febrero": 0.0,
            "marzo": 0.0,
            "abril": 0.0,
            "mayo": 0.0,
            "junio": 0.0,
            "julio": 0.0,
            "agosto": 0.0,
            "septiembre": 0.0,
            "octubre": 0.0,
            "noviembre": 0.0,
            "diciembre": 0.0,
            "total": 0.0,
        }
    )

    for flujo in flujos:
        if not flujo.fecha or flujo.fecha.year != current_year:
            continue
        month_field = MONTH_FIELDS[flujo.fecha.month]
        key = (flujo.categoria, flujo.tipo)
        pivot[key]["categoria"] = flujo.categoria
        pivot[key]["tipo"] = flujo.tipo
        pivot[key][month_field] += flujo.monto or 0
        pivot[key]["total"] += flujo.monto or 0

    flujo_categorias = []
    for row in pivot.values():
        flujo_categorias.append(
            {
                **row,
                **{
                    month: round(row[month], 2)
                    for month in MONTH_FIELDS.values()
                },
                "total": round(row["total"], 2),
            }
        )
    flujo_categorias.sort(key=lambda item: (item["tipo"], -item["total"]))

    resultados_lote = []
    rentabilidad_cultivo_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "ingreso": 0.0,
            "costo": 0.0,
            "margen": 0.0,
            "hectareas": 0.0,
            "toneladas": 0.0,
            "plan_margen": 0.0,
        }
    )
    rentabilidad_establecimiento_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "ingreso": 0.0,
            "costo": 0.0,
            "margen": 0.0,
            "hectareas": 0.0,
            "toneladas": 0.0,
        }
    )

    total_hectareas = 0.0
    total_toneladas = 0.0
    total_costos = 0.0
    total_costos_directos = 0.0
    total_costos_indirectos = 0.0
    margen_total = 0.0
    margen_plan_total = 0.0
    ingresos_operativos = 0.0

    for presupuesto, lote, establecimiento, cultivo in budget_rows:
        ingreso_ha = presupuesto.ingreso_real_ha or 0
        costo_directo_ha = presupuesto.costo_directo_real_ha or 0
        costo_indirecto_ha = presupuesto.costo_indirecto_ha or 0
        costo_ha = costo_directo_ha + costo_indirecto_ha
        ingreso_total_lote = ingreso_ha * lote.hectareas
        costo_total_lote = costo_ha * lote.hectareas
        margen_ha = ingreso_ha - costo_ha
        margen_total_lote = margen_ha * lote.hectareas
        toneladas = (presupuesto.rendimiento_real_tn_ha or 0) * lote.hectareas
        costo_tonelada = round(costo_total_lote / toneladas, 2) if toneladas else 0
        margen_plan_ha = (
            (presupuesto.ingreso_plan_ha or 0)
            - (presupuesto.costo_directo_plan_ha or 0)
            - costo_indirecto_ha
        )
        desvio_pct = round(
            ((margen_ha - margen_plan_ha) / margen_plan_ha) * 100,
            1,
        ) if margen_plan_ha else 0

        resultados_lote.append(
            {
                "lote": lote.nombre,
                "establecimiento": establecimiento.nombre,
                "cultivo": cultivo.nombre,
                "hectareas": round(lote.hectareas, 2),
                "ingreso_total": round(ingreso_total_lote, 2),
                "costo_total": round(costo_total_lote, 2),
                "costo_ha": round(costo_ha, 2),
                "costo_tonelada": costo_tonelada,
                "margen_ha": round(margen_ha, 2),
                "margen_total": round(margen_total_lote, 2),
                "desvio_pct": desvio_pct,
                "rentabilidad_pct": round(
                    (margen_total_lote / ingreso_total_lote) * 100,
                    1,
                ) if ingreso_total_lote else 0,
            }
        )

        rentabilidad_cultivo = rentabilidad_cultivo_map[cultivo.nombre]
        rentabilidad_cultivo["ingreso"] += ingreso_total_lote
        rentabilidad_cultivo["costo"] += costo_total_lote
        rentabilidad_cultivo["margen"] += margen_total_lote
        rentabilidad_cultivo["hectareas"] += lote.hectareas
        rentabilidad_cultivo["toneladas"] += toneladas
        rentabilidad_cultivo["plan_margen"] += margen_plan_ha * lote.hectareas

        rentabilidad_est = rentabilidad_establecimiento_map[establecimiento.nombre]
        rentabilidad_est["ingreso"] += ingreso_total_lote
        rentabilidad_est["costo"] += costo_total_lote
        rentabilidad_est["margen"] += margen_total_lote
        rentabilidad_est["hectareas"] += lote.hectareas
        rentabilidad_est["toneladas"] += toneladas

        total_hectareas += lote.hectareas
        total_toneladas += toneladas
        total_costos += costo_total_lote
        total_costos_directos += costo_directo_ha * lote.hectareas
        total_costos_indirectos += costo_indirecto_ha * lote.hectareas
        margen_total += margen_total_lote
        margen_plan_total += margen_plan_ha * lote.hectareas
        ingresos_operativos += ingreso_total_lote

    resultados_lote.sort(key=lambda item: item["margen_total"], reverse=True)

    rentabilidad_cultivo = []
    for cultivo, valores in rentabilidad_cultivo_map.items():
        rentabilidad_cultivo.append(
            {
                "cultivo": cultivo,
                "ingreso_total": round(valores["ingreso"], 2),
                "costo_total": round(valores["costo"], 2),
                "margen_total": round(valores["margen"], 2),
                "margen_ha": round(
                    valores["margen"] / valores["hectareas"],
                    2,
                ) if valores["hectareas"] else 0,
                "costo_ha": round(
                    valores["costo"] / valores["hectareas"],
                    2,
                ) if valores["hectareas"] else 0,
                "costo_tonelada": round(
                    valores["costo"] / valores["toneladas"],
                    2,
                ) if valores["toneladas"] else 0,
                "desvio_pct": round(
                    ((valores["margen"] - valores["plan_margen"]) / valores["plan_margen"]) * 100,
                    1,
                ) if valores["plan_margen"] else 0,
            }
        )
    rentabilidad_cultivo.sort(key=lambda item: item["margen_total"], reverse=True)

    rentabilidad_establecimiento = []
    for establecimiento, valores in rentabilidad_establecimiento_map.items():
        rentabilidad_establecimiento.append(
            {
                "establecimiento": establecimiento,
                "ingreso_total": round(valores["ingreso"], 2),
                "costo_total": round(valores["costo"], 2),
                "margen_total": round(valores["margen"], 2),
                "margen_ha": round(
                    valores["margen"] / valores["hectareas"],
                    2,
                ) if valores["hectareas"] else 0,
                "costo_tonelada": round(
                    valores["costo"] / valores["toneladas"],
                    2,
                ) if valores["toneladas"] else 0,
            }
        )
    rentabilidad_establecimiento.sort(
        key=lambda item: item["margen_total"],
        reverse=True,
    )

    desvio_presupuesto_pct = round(
        ((margen_total - margen_plan_total) / margen_plan_total) * 100,
        2,
    ) if margen_plan_total else 0
    costo_por_ha = round(total_costos / total_hectareas, 2) if total_hectareas else 0
    costo_por_tonelada = round(total_costos / total_toneladas, 2) if total_toneladas else 0
    margen_por_ha = round(margen_total / total_hectareas, 2) if total_hectareas else 0

    sensibilidad = [
        _scenario("Base", margen_total, margen_total),
        _scenario(
            "Rinde -10%",
            sum(
                (
                    ((presupuesto.ingreso_real_ha or 0) * 0.9)
                    - (presupuesto.costo_directo_real_ha or 0)
                    - (presupuesto.costo_indirecto_ha or 0)
                ) * lote.hectareas
                for presupuesto, lote, _, _ in budget_rows
            ),
            margen_total,
        ),
        _scenario(
            "Precio -10%",
            sum(
                (
                    ((presupuesto.ingreso_real_ha or 0) * 0.9)
                    - (presupuesto.costo_directo_real_ha or 0)
                    - (presupuesto.costo_indirecto_ha or 0)
                ) * lote.hectareas
                for presupuesto, lote, _, _ in budget_rows
            ),
            margen_total,
        ),
        _scenario(
            "TC +10%",
            sum(
                (
                    ((presupuesto.ingreso_real_ha or 0) * 1.07)
                    - ((presupuesto.costo_directo_real_ha or 0) * 1.03)
                    - ((presupuesto.costo_indirecto_ha or 0) * 1.01)
                ) * lote.hectareas
                for presupuesto, lote, _, _ in budget_rows
            ),
            margen_total,
        ),
    ]

    saldo_proyectado = [
        item["saldo_acumulado"]
        for item in cash_projection
        if item.get("proyectado")
    ]
    saldo_minimo = min(saldo_proyectado, default=0)
    riesgo_caja = (
        "alto"
        if saldo_minimo < 0
        else "medio"
        if saldo_minimo < max(compromisos_futuros * 0.25, 1)
        else "bajo"
    )

    alerts = [
        {
            "titulo": alert.titulo,
            "descripcion": alert.descripcion,
            "accion": alert.accion_sugerida,
            "severidad": alert.severidad,
            "prioridad": alert.prioridad,
        }
        for alert in alert_rows
    ]

    acciones = []
    if desvio_presupuesto_pct < -5:
        worst_lote = min(
            resultados_lote,
            key=lambda item: item["desvio_pct"],
            default=None,
        )
        acciones.append(
            {
                "titulo": "Corregir desvío presupuesto vs real",
                "descripcion": (
                    f"El margen consolidado cae {abs(desvio_presupuesto_pct):.1f}% vs presupuesto. "
                    f"{worst_lote['lote']} es el principal detractor."
                ) if worst_lote else "El margen consolidado cae por debajo del presupuesto.",
                "owner": "Administración y campo",
                "impacto": "Recupera margen por ha en lotes con mayor desvío",
                "severity": "critical" if desvio_presupuesto_pct < -12 else "warning",
            }
        )
    if riesgo_caja != "bajo":
        acciones.append(
            {
                "titulo": "Ajustar caja de corto plazo",
                "descripcion": (
                    f"Hay ARS {capital_trabajo_comprometido:,.0f} comprometidos en 60 días. "
                    "Coordinar cobranzas y diferir egresos no críticos."
                ),
                "owner": "Finanzas",
                "impacto": "Reduce tensión de caja y necesidad de financiamiento",
                "severity": "critical" if riesgo_caja == "alto" else "warning",
            }
        )
    if cuentas_a_cobrar > max(compromisos_futuros, 1) * 0.7:
        acciones.append(
            {
                "titulo": "Acelerar cobranzas de operaciones pendientes",
                "descripcion": "La cartera a cobrar puede financiar parte importante de los compromisos próximos.",
                "owner": "Tesorería",
                "impacto": "Mejora capital de trabajo sin tomar deuda adicional",
                "severity": "warning",
            }
        )
    for task in task_rows[:2]:
        acciones.append(
            {
                "titulo": task.descripcion,
                "descripcion": task.impacto or "Tarea financiera prioritaria",
                "owner": task.responsable or "Finanzas",
                "impacto": task.impacto or "Resultado y caja",
                "severity": "critical" if task.prioridad == "alta" else "warning",
            }
        )

    last_update = max((flujo.fecha for flujo in flujos if flujo.fecha), default=None)

    cost_breakdown = [
        {
            "label": "Ingresos operativos",
            "value": round(ingresos_operativos, 2),
            "kind": "positive",
        },
        {
            "label": "Costos directos",
            "value": round(total_costos_directos, 2),
            "kind": "negative",
        },
        {
            "label": "Costos indirectos",
            "value": round(total_costos_indirectos, 2),
            "kind": "negative",
        },
        {
            "label": "Margen bruto",
            "value": round(margen_total, 2),
            "kind": "total",
        },
    ]

    return {
        "summary": {
            "capital_de_trabajo": capital_trabajo,
            "deuda_por_vencer": round(compromisos_futuros, 2),
            "cuentas_a_cobrar": cuentas_a_cobrar,
            "flujo_neto": round(flujo_neto, 2),
            "margen_bruto_total": round(margen_total, 2),
            "margen_por_ha": margen_por_ha,
            "desvio_presupuesto_pct": desvio_presupuesto_pct,
            "costo_por_ha": costo_por_ha,
            "costo_por_tonelada": costo_por_tonelada,
            "capital_trabajo_comprometido": round(capital_trabajo_comprometido, 2),
            "deuda_corto_plazo": round(deuda_corto_plazo, 2),
            "riesgo_caja": riesgo_caja,
            "ingresos_operativos": round(ingresos_operativos, 2),
        },
        "flujo_mensual": flujo_mensual,
        "flujo_categorias": flujo_categorias,
        "cash_projection": cash_projection,
        "cost_breakdown": cost_breakdown,
        "resultados_lote": resultados_lote[:12],
        "rentabilidad_cultivo": rentabilidad_cultivo,
        "rentabilidad_establecimiento": rentabilidad_establecimiento,
        "sensitivity": sensibilidad,
        "alerts": alerts[:5],
        "actions": acciones[:5],
        "ultima_actualizacion": (
            datetime.combine(last_update, datetime.min.time()).isoformat()
            if last_update
            else datetime.now().isoformat()
        ),
    }


async def get_flujo_serie(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
):
    query = select(FlujoCaja).order_by(FlujoCaja.fecha)
    if empresa_id:
        query = query.where(FlujoCaja.empresa_id == empresa_id)
    if campania_id:
        query = query.where(FlujoCaja.campania_id == campania_id)

    flujos = (await db.execute(query)).scalars().all()
    serie = _project_series(_monthly_series(flujos))

    return {
        "items": serie,
        "ultima_actualizacion": datetime.now().isoformat(),
    }
