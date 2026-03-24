from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.venta import Venta
from app.models.flujo_financiero import FlujoCaja
from app.models.lote import Lote
from app.models.stock import Stock
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.models.cultivo import Cultivo
from app.models.establecimiento import Establecimiento
from app.services.campaign_scope import (
    resolve_campaign_id,
    resolve_previous_campaign_id,
)
from app.services.decision_data import (
    load_alert_rows,
    load_budget_rows,
    load_fleet_support_rows,
    load_plan_rows,
    load_position_rows,
    load_stock_projection_rows,
    load_task_rows,
)


def _month_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


def _build_insights(
    ventas_totales: float,
    margen_bruto_pct: float,
    rendimiento_promedio: float,
    stock_valorizado: float,
    variacion_campania: float,
    ventas_cultivo: list[dict],
) -> list[dict]:
    insights: list[dict] = []
    now = datetime.now().isoformat()

    if variacion_campania:
        insights.append(
            {
                "id": "ventas-variacion",
                "titulo": (
                    "Ventas arriba de la base comparativa"
                    if variacion_campania >= 0
                    else "Ventas por debajo de la base comparativa"
                ),
                "descripcion": (
                    f"La facturacion vario {abs(variacion_campania):.1f}% frente al periodo anterior."
                ),
                "severidad": "success" if variacion_campania >= 0 else "warning",
                "modulo": "comercial",
                "timestamp": now,
            }
        )

    insights.append(
        {
            "id": "margen-operativo",
            "titulo": (
                "Margen bruto saludable"
                if margen_bruto_pct >= 28
                else "Margen bruto bajo presion"
            ),
            "descripcion": (
                f"El margen bruto consolidado se ubica en {margen_bruto_pct:.1f}%."
            ),
            "severidad": "success" if margen_bruto_pct >= 28 else "warning",
            "modulo": "finanzas",
            "timestamp": now,
        }
    )

    insights.append(
        {
            "id": "rendimiento-agricola",
            "titulo": (
                "Rendimiento de lotes consistente"
                if rendimiento_promedio >= 3
                else "Rendimiento a revisar"
            ),
            "descripcion": (
                f"El promedio actual de lotes con cosecha declarada es {rendimiento_promedio:.2f} tn/ha."
            ),
            "severidad": "success" if rendimiento_promedio >= 3 else "warning",
            "modulo": "agricola",
            "timestamp": now,
        }
    )

    if ventas_totales > 0 and stock_valorizado / ventas_totales > 0.45:
        insights.append(
            {
                "id": "stock-concentrado",
                "titulo": "Posicion de stock relevante para cerrar ventas",
                "descripcion": (
                    "El stock valorizado representa una porcion alta sobre las ventas acumuladas."
                ),
                "severidad": "info",
                "modulo": "stock",
                "timestamp": now,
            }
        )

    if ventas_cultivo:
        principal = ventas_cultivo[0]
        insights.append(
            {
                "id": "mix-cultivos",
                "titulo": f"{principal['cultivo']} lidera el mix comercial",
                "descripcion": (
                    f"Es el cultivo con mayor facturacion del periodo, con ARS {principal['valor']:.0f}."
                ),
                "severidad": "info",
                "modulo": "comercial",
                "timestamp": now,
            }
        )

    return insights[:4]


def _normalize_severity(value: str) -> str:
    return {
        "critical": "critical",
        "warning": "warning",
        "success": "success",
        "info": "info",
    }.get(value, "info")


async def get_dashboard_executive(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    resolved_campania_id = await resolve_campaign_id(db=db, campania_id=campania_id)

    ventas_query = (
        select(Venta, Producto, Cultivo, Cliente)
        .join(Producto, Venta.producto_id == Producto.id)
        .outerjoin(Cultivo, Producto.cultivo_id == Cultivo.id)
        .join(Cliente, Venta.cliente_id == Cliente.id)
    )
    if empresa_id:
        ventas_query = ventas_query.where(Venta.empresa_id == empresa_id)
    if resolved_campania_id:
        ventas_query = ventas_query.where(Venta.campania_id == resolved_campania_id)
    if cultivo_id:
        ventas_query = ventas_query.where(Producto.cultivo_id == cultivo_id)
    ventas_rows = (await db.execute(ventas_query)).all()

    flujo_query = select(FlujoCaja).order_by(FlujoCaja.fecha)
    if empresa_id:
        flujo_query = flujo_query.where(FlujoCaja.empresa_id == empresa_id)
    if resolved_campania_id:
        flujo_query = flujo_query.where(FlujoCaja.campania_id == resolved_campania_id)
    flujos = (await db.execute(flujo_query)).scalars().all()

    stock_query = (
        select(Stock, Producto, Cultivo, Establecimiento)
        .join(Producto, Stock.producto_id == Producto.id)
        .outerjoin(Cultivo, Producto.cultivo_id == Cultivo.id)
        .join(Establecimiento, Stock.establecimiento_id == Establecimiento.id)
    )
    if empresa_id:
        stock_query = stock_query.where(Establecimiento.empresa_id == empresa_id)
    if cultivo_id:
        stock_query = stock_query.where(Producto.cultivo_id == cultivo_id)
    stock_rows = (await db.execute(stock_query)).all()

    lotes_query = select(Lote)
    if resolved_campania_id:
        lotes_query = lotes_query.where(Lote.campania_id == resolved_campania_id)
    if cultivo_id:
        lotes_query = lotes_query.where(Lote.cultivo_id == cultivo_id)
    if empresa_id:
        lotes_query = lotes_query.join(Establecimiento).where(
            Establecimiento.empresa_id == empresa_id
        )
    lotes = (await db.execute(lotes_query)).scalars().all()

    ventas_totales = round(sum((venta.total or 0) for venta, _, _, _ in ventas_rows), 2)
    rendimiento_vals = [
        lote.rendimiento_real for lote in lotes if lote.rendimiento_real is not None
    ]
    rendimiento_promedio = round(
        sum(rendimiento_vals) / len(rendimiento_vals) if rendimiento_vals else 0,
        2,
    )
    stock_valorizado = round(
        sum(
            (stock.volumen_disponible or 0) * (producto.precio_referencia or 0)
            for stock, producto, _, _ in stock_rows
        ),
        2,
    )
    ingresos_egresos_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {"ingresos": 0.0, "egresos": 0.0}
    )
    for flujo in flujos:
        if not flujo.fecha:
            continue
        key = flujo.fecha.strftime("%Y-%m")
        if flujo.tipo == "ingreso":
            ingresos_egresos_map[key]["ingresos"] += flujo.monto or 0
        else:
            ingresos_egresos_map[key]["egresos"] += flujo.monto or 0

    ingresos_egresos = [
        {
            "mes": mes,
            "ingresos": round(valores["ingresos"], 2),
            "egresos": round(valores["egresos"], 2),
        }
        for mes, valores in sorted(ingresos_egresos_map.items())[-12:]
    ]

    netos_recientes = [
        item["ingresos"] - item["egresos"] for item in ingresos_egresos[-3:]
    ]
    flujo_neto_mensual = round(
        sum(netos_recientes) / len(netos_recientes) if netos_recientes else 0,
        2,
    )

    ventas_cultivo_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {"valor": 0.0, "volumen": 0.0}
    )
    for venta, _, cultivo, _ in ventas_rows:
        cultivo_nombre = cultivo.nombre if cultivo else "Sin cultivo"
        ventas_cultivo_map[cultivo_nombre]["valor"] += venta.total or 0
        ventas_cultivo_map[cultivo_nombre]["volumen"] += venta.volumen or 0

    ventas_cultivo = [
        {
            "cultivo": cultivo,
            "valor": round(valores["valor"], 2),
            "volumen": round(valores["volumen"], 2),
        }
        for cultivo, valores in ventas_cultivo_map.items()
    ]
    ventas_cultivo.sort(key=lambda item: item["valor"], reverse=True)

    budget_rows = await load_budget_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        cultivo_id=cultivo_id,
    )
    plan_rows = await load_plan_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        cultivo_id=cultivo_id,
    )
    position_rows = await load_position_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        cultivo_id=cultivo_id,
    )
    stock_projection_rows = await load_stock_projection_rows(db=db, empresa_id=empresa_id)
    fleet_rows, downtime_rows, _, service_rows = await load_fleet_support_rows(
        db=db,
        empresa_id=empresa_id,
    )
    alert_rows = await load_alert_rows(
        db=db,
        modules=("dashboard", "agricola", "comercial", "stock", "maquinaria", "finanzas"),
    )
    task_rows = await load_task_rows(
        db=db,
        modules=("agricola", "maquinaria"),
    )

    margin_total = 0.0
    margin_plan_total = 0.0
    ingreso_total = 0.0
    costo_directo_total = 0.0
    costo_indirecto_total = 0.0
    total_hectareas = 0.0
    lot_profitability = []
    for presupuesto, lote, establecimiento, cultivo in budget_rows:
        margen_real_ha = (
            presupuesto.ingreso_real_ha
            - presupuesto.costo_directo_real_ha
            - presupuesto.costo_indirecto_ha
        )
        margen_plan_ha = (
            presupuesto.ingreso_plan_ha
            - presupuesto.costo_directo_plan_ha
            - presupuesto.costo_indirecto_ha
        )
        margen_total_lote = margen_real_ha * lote.hectareas
        margin_total += margen_total_lote
        margin_plan_total += margen_plan_ha * lote.hectareas
        ingreso_total += presupuesto.ingreso_real_ha * lote.hectareas
        costo_directo_total += presupuesto.costo_directo_real_ha * lote.hectareas
        costo_indirecto_total += presupuesto.costo_indirecto_ha * lote.hectareas
        total_hectareas += lote.hectareas
        desvio_pct = round(
            ((margen_real_ha - margen_plan_ha) / margen_plan_ha) * 100,
            1,
        ) if margen_plan_ha else 0
        lot_profitability.append(
            {
                "lote": lote.nombre,
                "establecimiento": establecimiento.nombre,
                "cultivo": cultivo.nombre,
                "margen_ha": round(margen_real_ha, 2),
                "margen_total": round(margen_total_lote, 2),
                "desvio_pct": desvio_pct,
                "contribucion_pct": 0,
            }
        )

    for item in lot_profitability:
        item["contribucion_pct"] = round(
            (item["margen_total"] / margin_total) * 100,
            1,
        ) if margin_total else 0

    lot_profitability.sort(key=lambda item: item["margen_total"], reverse=True)
    top_lotes = lot_profitability[:5]
    bottom_lotes = sorted(lot_profitability, key=lambda item: item["margen_total"])[:5]

    costos_operativos = round(costo_directo_total + costo_indirecto_total, 2)
    margen_bruto = round(margin_total, 2)
    margen_bruto_pct = round(
        (margen_bruto / ingreso_total) * 100 if ingreso_total > 0 else 0,
        2,
    )
    ebitda_estimado = round(margen_bruto * 0.82, 2)

    variacion_campania_anterior = 0.0
    if resolved_campania_id:
        previous_campaign_id = await resolve_previous_campaign_id(
            db=db,
            current_campaign_id=resolved_campania_id,
        )
        ventas_actual = ventas_totales
        ventas_previa = 0.0
        if previous_campaign_id:
            previous_sales_query = select(Venta.total).where(
                Venta.campania_id == previous_campaign_id
            )
            if empresa_id:
                previous_sales_query = previous_sales_query.where(
                    Venta.empresa_id == empresa_id
                )
            if cultivo_id:
                previous_sales_query = previous_sales_query.join(
                    Producto, Venta.producto_id == Producto.id
                ).where(Producto.cultivo_id == cultivo_id)
            previous_sales_rows = (await db.execute(previous_sales_query)).scalars().all()
            ventas_previa = sum(item or 0 for item in previous_sales_rows)

        variacion_campania_anterior = round(
            ((ventas_actual - ventas_previa) / ventas_previa) * 100 if ventas_previa else 0,
            2,
        )
    else:
        sales_years = [
            venta.fecha.year
            for venta, _, _, _ in ventas_rows
            if venta.fecha is not None
        ]
        current_year = max(sales_years) if sales_years else datetime.now().year
        ventas_actual = sum(
            (venta.total or 0)
            for venta, _, _, _ in ventas_rows
            if venta.fecha and venta.fecha.year == current_year
        )
        ventas_previa = sum(
            (venta.total or 0)
            for venta, _, _, _ in ventas_rows
            if venta.fecha and venta.fecha.year == current_year - 1
        )
        variacion_campania_anterior = round(
            ((ventas_actual - ventas_previa) / ventas_previa) * 100 if ventas_previa else 0,
            2,
        )

    plan_status: dict[int, dict] = {}
    for plan, ejecucion, lote, establecimiento, cultivo in plan_rows:
        bucket = plan_status.setdefault(
            plan.id,
            {
                "plan": plan,
                "lote": lote,
                "establecimiento": establecimiento,
                "cultivo": cultivo,
                "ejecutado": 0.0,
            },
        )
        bucket["ejecutado"] += ejecucion.hectareas_ejecutadas if ejecucion else 0

    today = datetime.now().date()
    hectareas_fuera_ventana = round(
        sum(
            max(bucket["plan"].hectareas_planificadas - bucket["ejecutado"], 0)
            for bucket in plan_status.values()
            if bucket["plan"].ventana_fin < today and bucket["ejecutado"] < bucket["plan"].hectareas_planificadas
        ),
        2,
    )

    toneladas_sin_fijar = round(
        sum(max(pos.toneladas_producidas - pos.toneladas_fijadas, 0) for pos, _ in position_rows),
        2,
    )
    toneladas_producidas = round(
        sum(pos.toneladas_producidas or 0 for pos, _ in position_rows),
        2,
    )
    toneladas_fijadas = round(
        sum(pos.toneladas_fijadas or 0 for pos, _ in position_rows),
        2,
    )
    stock_critico = len([row for row, _, _ in stock_projection_rows if row.severidad == "critical"])
    maquinas_criticas = len(
        [
            service
            for service in service_rows
            if not service.completado
            and service.fecha_programada <= today + timedelta(days=14)
            and service.criticidad_operativa == "alta"
        ]
    ) + len([item for item in downtime_rows if item.criticidad == "alta"])

    desvio_presupuesto_pct = round(
        ((margin_total - margin_plan_total) / margin_plan_total) * 100,
        2,
    ) if margin_plan_total else 0
    margen_por_ha = round(margin_total / total_hectareas, 2) if total_hectareas else 0

    result_bridge = [
        {"label": "Ingreso esperado/real", "value": round(ingreso_total, 2), "kind": "positive"},
        {"label": "Costo directo", "value": round(-costo_directo_total, 2), "kind": "negative"},
        {"label": "Costo indirecto", "value": round(-costo_indirecto_total, 2), "kind": "negative"},
        {"label": "Margen bruto", "value": round(margin_total, 2), "kind": "total"},
    ]

    semaforos = [
        {
            "label": "Margen vs presupuesto",
            "status": "danger" if desvio_presupuesto_pct < -10 else "warning" if desvio_presupuesto_pct < -3 else "success",
            "detail": f"{desvio_presupuesto_pct:+.1f}% vs presupuesto",
        },
        {
            "label": "Ventana operativa",
            "status": "danger" if hectareas_fuera_ventana > 250 else "warning" if hectareas_fuera_ventana > 0 else "success",
            "detail": f"{hectareas_fuera_ventana:.0f} ha fuera de ventana",
        },
        {
            "label": "Cobertura comercial",
            "status": "danger" if toneladas_sin_fijar > 1800 else "warning" if toneladas_sin_fijar > 800 else "success",
            "detail": f"{toneladas_sin_fijar:.0f} tn sin fijar",
        },
        {
            "label": "Continuidad operativa",
            "status": "danger" if maquinas_criticas >= 3 else "warning" if maquinas_criticas > 0 else "success",
            "detail": f"{maquinas_criticas} equipos criticos",
        },
    ]

    alerts = [
        {
            "id": f"alert-{index}",
            "titulo": alert.titulo,
            "descripcion": alert.descripcion,
            "severidad": _normalize_severity(alert.severidad),
            "modulo": alert.modulo,
            "accion": alert.accion_sugerida,
            "prioridad": alert.prioridad,
        }
        for index, alert in enumerate(alert_rows[:6], start=1)
    ]

    acciones = []
    if hectareas_fuera_ventana > 0:
        acciones.append(
            {
                "id": "accion-siembra",
                "titulo": "Recuperar superficie fuera de ventana",
                "descripcion": f"Hay {hectareas_fuera_ventana:.0f} ha atrasadas. Priorizar lotes de mayor margen esperado.",
                "owner": "Operaciones",
                "impacto": "Evita perdida de rinde y reprogramaciones",
                "due": "Esta semana",
                "severity": "critical" if hectareas_fuera_ventana > 250 else "warning",
            }
        )
    if toneladas_sin_fijar > 0:
        acciones.append(
            {
                "id": "accion-cobertura",
                "titulo": "Definir cobertura comercial parcial",
                "descripcion": f"Quedan {toneladas_sin_fijar:.0f} tn sin fijacion. Evaluar escalonar ventas y coberturas.",
                "owner": "Comercial",
                "impacto": "Reduce exposicion a precio y tipo de cambio",
                "due": "48 hs",
                "severity": "warning",
            }
        )
    if stock_critico > 0:
        acciones.append(
            {
                "id": "accion-insumos",
                "titulo": "Emitir compras tacticas de insumos",
                "descripcion": f"Hay {stock_critico} productos con cobertura critica segun labores pendientes.",
                "owner": "Abastecimiento",
                "impacto": "Evita quiebres de ejecucion",
                "due": "72 hs",
                "severity": "critical",
            }
        )
    if maquinas_criticas > 0:
        acciones.append(
            {
                "id": "accion-flota",
                "titulo": "Cerrar services de equipos cuello de botella",
                "descripcion": "Adelantar mantenimiento de sembradoras/cosechadoras con alta criticidad operativa.",
                "owner": "Taller",
                "impacto": "Sostiene avance de labores",
                "due": "Antes del proximo frente de trabajo",
                "severity": "warning",
            }
        )

    for task in task_rows[:3]:
        acciones.append(
            {
                "id": f"task-{task.id}",
                "titulo": task.descripcion,
                "descripcion": task.impacto or "Tarea critica de continuidad operativa",
                "owner": task.responsable or "Equipo campo",
                "impacto": task.impacto or "Operacion",
                "due": task.vence_el.isoformat(),
                "severity": "critical" if task.prioridad == "alta" else "warning",
            }
        )

    return {
        "kpis": {
            "ventas_totales": ventas_totales,
            "margen_bruto_pct": margen_bruto_pct,
            "rendimiento_promedio": rendimiento_promedio,
            "stock_valorizado": stock_valorizado,
            "ebitda_estimado": ebitda_estimado,
            "flujo_neto_mensual": flujo_neto_mensual,
            "costos_operativos": costos_operativos,
            "variacion_campania_anterior": variacion_campania_anterior,
        },
        "ingresos_egresos": ingresos_egresos,
        "ventas_cultivo": ventas_cultivo,
        "insights": _build_insights(
            ventas_totales=ventas_totales,
            margen_bruto_pct=margen_bruto_pct,
            rendimiento_promedio=rendimiento_promedio,
            stock_valorizado=stock_valorizado,
            variacion_campania=variacion_campania_anterior,
            ventas_cultivo=ventas_cultivo,
        ),
        "summary": {
            "margen_bruto_total": round(margin_total, 2),
            "margen_por_ha": margen_por_ha,
            "desvio_presupuesto_pct": desvio_presupuesto_pct,
            "hectareas_fuera_ventana": hectareas_fuera_ventana,
            "toneladas_sin_fijar": toneladas_sin_fijar,
            "toneladas_producidas": toneladas_producidas,
            "toneladas_fijadas": toneladas_fijadas,
            "stock_critico": stock_critico,
            "maquinas_criticas": maquinas_criticas,
        },
        "lot_profitability": lot_profitability,
        "top_lotes": top_lotes,
        "bottom_lotes": bottom_lotes,
        "result_bridge": result_bridge,
        "semaforos": semaforos,
        "alerts": alerts,
        "actions": acciones[:6],
        "ultima_actualizacion": datetime.now().isoformat(),
    }
