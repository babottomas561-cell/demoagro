from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cultivo import Cultivo
from app.models.establecimiento import Establecimiento
from app.models.insumo import Insumo, MovimientoInsumo
from app.models.lote import Lote
from app.models.producto import Producto
from app.models.stock import Stock
from app.services.decision_data import (
    load_alert_rows,
    load_presupuesto_insumo_rows,
    load_stock_projection_rows,
)


def _alert_level(libre_pct: float) -> str:
    if libre_pct < 10:
        return "rojo"
    if libre_pct < 30:
        return "amarillo"
    return "verde"


def _severity_rank(value: str) -> int:
    return {"critical": 0, "warning": 1, "ok": 2}.get(value, 3)


async def get_stock_resumen(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    query = (
        select(Stock, Producto, Cultivo, Establecimiento)
        .join(Producto, Stock.producto_id == Producto.id)
        .outerjoin(Cultivo, Producto.cultivo_id == Cultivo.id)
        .join(Establecimiento, Stock.establecimiento_id == Establecimiento.id)
    )

    if empresa_id:
        query = query.where(Establecimiento.empresa_id == empresa_id)
    if establecimiento_id:
        query = query.where(Stock.establecimiento_id == establecimiento_id)
    if cultivo_id:
        query = query.where(Producto.cultivo_id == cultivo_id)

    rows = (await db.execute(query)).all()
    projection_rows = await load_stock_projection_rows(
        db=db,
        empresa_id=empresa_id,
        establecimiento_id=establecimiento_id,
    )
    presupuesto_rows = await load_presupuesto_insumo_rows(
        db=db,
        empresa_id=empresa_id,
        establecimiento_id=establecimiento_id,
    )
    alert_rows = await load_alert_rows(db=db, modules=("stock",))

    items = []
    valor_total = 0.0
    total_stock = 0.0
    total_alertas = 0
    last_updated: Optional[datetime] = None

    for stock, producto, cultivo, establecimiento in rows:
        stock_disponible = round(stock.volumen_disponible or 0, 2)
        vendido = round(stock.volumen_vendido or 0, 2)
        comprometido = round(stock.volumen_comprometido or 0, 2)
        libre = round(max(stock_disponible - comprometido, 0), 2)
        libre_pct = round(
            (libre / stock_disponible) * 100,
            1,
        ) if stock_disponible > 0 else 0.0
        precio_referencia = round(producto.precio_referencia or 0, 2)
        valor_estimado = round(stock_disponible * precio_referencia, 2)
        alerta = _alert_level(libre_pct)

        if alerta != "verde":
            total_alertas += 1

        total_stock += stock_disponible
        valor_total += valor_estimado

        if stock.fecha_actualizacion and (
            last_updated is None or stock.fecha_actualizacion > last_updated
        ):
            last_updated = stock.fecha_actualizacion

        items.append(
            {
                "id": str(stock.id),
                "cultivo": cultivo.nombre if cultivo else producto.nombre,
                "establecimiento": establecimiento.nombre,
                "stock_disponible_tn": stock_disponible,
                "vendido_tn": vendido,
                "comprometido_tn": comprometido,
                "libre_tn": libre,
                "libre_pct": libre_pct,
                "precio_referencia": precio_referencia,
                "valor_estimado": valor_estimado,
                "alerta": alerta,
            }
        )

    items.sort(key=lambda item: item["valor_estimado"], reverse=True)

    presupuesto_map = {
        (presupuesto.establecimiento_id, presupuesto.insumo_id): presupuesto
        for presupuesto, _, _ in presupuesto_rows
    }
    insumos = []
    cobertura_vals = []
    costo_inventario = 0.0
    necesidad_compra = 0.0
    stock_inmovilizado = 0.0

    for projection, insumo, establecimiento in projection_rows:
        presupuesto = presupuesto_map.get((establecimiento.id, insumo.id))
        desvio_consumo_pct = round(
            ((projection.consumo_real_mes - presupuesto.consumo_plan) / presupuesto.consumo_plan) * 100,
            1,
        ) if presupuesto and presupuesto.consumo_plan else 0
        coverage = {
            "insumo": insumo.nombre,
            "tipo": insumo.tipo,
            "unidad": insumo.unidad,
            "establecimiento": establecimiento.nombre,
            "stock_actual": round(projection.stock_actual, 2),
            "cobertura_dias": round(projection.cobertura_dias, 1),
            "cobertura_ha": round(projection.cobertura_ha, 1),
            "quiebre_en_dias": projection.quiebre_en_dias,
            "compra_sugerida": round(projection.compra_sugerida or 0, 2),
            "stock_inmovilizado": round(projection.stock_inmovilizado or 0, 2),
            "costo_inventario": round(projection.costo_inventario or 0, 2),
            "consumo_plan_mes": round(projection.consumo_plan_mes, 2),
            "consumo_real_mes": round(projection.consumo_real_mes, 2),
            "desvio_consumo_pct": desvio_consumo_pct,
            "severidad": projection.severidad,
        }
        insumos.append(coverage)
        cobertura_vals.append(projection.cobertura_dias)
        costo_inventario += projection.costo_inventario or 0
        necesidad_compra += projection.compra_sugerida or 0
        stock_inmovilizado += projection.stock_inmovilizado or 0

    insumos.sort(
        key=lambda item: (_severity_rank(item["severidad"]), item["cobertura_dias"])
    )

    consumo_vs_plan_map: dict[str, dict[str, float]] = {}
    for item in insumos:
        bucket = consumo_vs_plan_map.setdefault(
            item["insumo"],
            {
                "insumo": item["insumo"],
                "consumo_plan_mes": 0.0,
                "consumo_real_mes": 0.0,
                "compra_sugerida": 0.0,
            },
        )
        bucket["consumo_plan_mes"] += item["consumo_plan_mes"]
        bucket["consumo_real_mes"] += item["consumo_real_mes"]
        bucket["compra_sugerida"] += item["compra_sugerida"]

    consumo_vs_plan = []
    for item in consumo_vs_plan_map.values():
        consumo_vs_plan.append(
            {
                **item,
                "consumo_plan_mes": round(item["consumo_plan_mes"], 2),
                "consumo_real_mes": round(item["consumo_real_mes"], 2),
                "compra_sugerida": round(item["compra_sugerida"], 2),
                "desvio_pct": round(
                    ((item["consumo_real_mes"] - item["consumo_plan_mes"]) / item["consumo_plan_mes"]) * 100,
                    1,
                ) if item["consumo_plan_mes"] else 0,
            }
        )
    consumo_vs_plan.sort(key=lambda item: abs(item["desvio_pct"]), reverse=True)

    productos_criticos = len([item for item in insumos if item["severidad"] == "critical"])
    cobertura_promedio_dias = round(
        sum(cobertura_vals) / len(cobertura_vals),
        1,
    ) if cobertura_vals else 0

    alerts = [
        {
            "id": item["id"],
            "cultivo": item["cultivo"],
            "establecimiento": item["establecimiento"],
            "mensaje": (
                "Stock libre crítico"
                if item["alerta"] == "rojo"
                else "Stock libre ajustado"
            ),
            "severidad": "critical" if item["alerta"] == "rojo" else "warning",
        }
        for item in items
        if item["alerta"] != "verde"
    ]
    for insumo in insumos[:3]:
        if insumo["severidad"] == "ok":
            continue
        alerts.append(
            {
                "id": f"{insumo['establecimiento']}-{insumo['insumo']}",
                "cultivo": insumo["insumo"],
                "establecimiento": insumo["establecimiento"],
                "mensaje": (
                    f"{insumo['insumo']} cubre solo {insumo['cobertura_dias']:.0f} días"
                ),
                "severidad": "critical" if insumo["severidad"] == "critical" else "warning",
            }
        )
    for alert in alert_rows[:2]:
        alerts.append(
            {
                "id": f"operativa-{alert.id}",
                "cultivo": alert.titulo,
                "establecimiento": "Operación",
                "mensaje": alert.descripcion,
                "severidad": alert.severidad,
            }
        )

    actions = []
    critical_item = next((item for item in insumos if item["severidad"] == "critical"), None)
    if critical_item:
        actions.append(
            {
                "titulo": f"Comprar {critical_item['insumo']} para {critical_item['establecimiento']}",
                "descripcion": (
                    f"La cobertura cae a {critical_item['cobertura_dias']:.0f} días y el quiebre "
                    f"se proyecta en {critical_item['quiebre_en_dias'] or 0} días."
                ),
                "owner": "Abastecimiento",
                "impacto": "Evita quiebre de labores pendientes",
                "severity": "critical",
            }
        )
    immobilized_item = max(insumos, key=lambda item: item["stock_inmovilizado"], default=None)
    if immobilized_item and immobilized_item["stock_inmovilizado"] > 0:
        actions.append(
            {
                "titulo": f"Reducir stock inmovilizado de {immobilized_item['insumo']}",
                "descripcion": (
                    f"Hay {immobilized_item['stock_inmovilizado']:.0f} {immobilized_item['unidad']} "
                    "sin consumo proyectado de corto plazo."
                ),
                "owner": "Compras",
                "impacto": "Libera capital de trabajo y espacio operativo",
                "severity": "warning",
            }
        )
    over_consuming = next(
        (item for item in consumo_vs_plan if item["desvio_pct"] > 12),
        None,
    )
    if over_consuming:
        actions.append(
            {
                "titulo": f"Ajustar consumo real de {over_consuming['insumo']}",
                "descripcion": "El ritmo de consumo supera al plan y acelera quiebres proyectados.",
                "owner": "Campo y abastecimiento",
                "impacto": "Rebaja desvío de costo y urgencias de compra",
                "severity": "warning",
            }
        )

    return {
        "summary": {
            "stock_total_tn": round(total_stock, 2),
            "valor_stock": round(valor_total, 2),
            "unidades_alerta": total_alertas,
            "productos_criticos": productos_criticos,
            "cobertura_promedio_dias": cobertura_promedio_dias,
            "costo_inventario_insumos": round(costo_inventario, 2),
            "necesidad_compra": round(necesidad_compra, 2),
            "stock_inmovilizado": round(stock_inmovilizado, 2),
        },
        "items": items,
        "insumos": insumos,
        "consumo_vs_plan": consumo_vs_plan,
        "alerts": alerts[:6],
        "actions": actions[:5],
        "ultima_actualizacion": (
            last_updated.isoformat() if last_updated else datetime.now().isoformat()
        ),
    }


async def get_movimientos(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    tipo: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
):
    query = (
        select(MovimientoInsumo, Insumo, Establecimiento, Lote)
        .join(Insumo, MovimientoInsumo.insumo_id == Insumo.id)
        .join(Establecimiento, MovimientoInsumo.establecimiento_id == Establecimiento.id)
        .outerjoin(Lote, MovimientoInsumo.lote_id == Lote.id)
    )

    if empresa_id:
        query = query.where(Establecimiento.empresa_id == empresa_id)
    if tipo:
        query = query.where(MovimientoInsumo.tipo == tipo)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = (
        query.order_by(MovimientoInsumo.fecha.desc(), MovimientoInsumo.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows = (await db.execute(query)).all()
    items = []
    for movimiento, insumo, establecimiento, lote in rows:
        items.append(
            {
                "id": str(movimiento.id),
                "fecha": movimiento.fecha.isoformat() if movimiento.fecha else None,
                "tipo": movimiento.tipo,
                "establecimiento": establecimiento.nombre,
                "insumo": insumo.nombre,
                "unidad": insumo.unidad,
                "cantidad": round(movimiento.cantidad or 0, 2),
                "costo_total": round(movimiento.costo_total or 0, 2),
                "lote": lote.nombre if lote else None,
            }
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
