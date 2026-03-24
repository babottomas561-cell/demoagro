from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cliente import Cliente
from app.models.campania import Campania
from app.models.contrato import Contrato
from app.models.cultivo import Cultivo
from app.models.decision_support import EntregaComercial
from app.models.empresa import Empresa
from app.models.producto import Producto
from app.models.stock import Stock
from app.models.venta import Venta
from app.models.establecimiento import Establecimiento
from app.services.campaign_scope import resolve_campaign_id, resolve_previous_campaign_id
from app.services.decision_data import load_alert_rows, load_position_rows


def _build_operacion(
    venta: Venta,
    cultivo_nombre: str,
    cliente_nombre: str,
) -> dict:
    return {
        "id": str(venta.id),
        "fecha": venta.fecha.isoformat() if venta.fecha else None,
        "cultivo": cultivo_nombre,
        "cliente": cliente_nombre,
        "volumen_tn": round(venta.volumen or 0, 2),
        "precio_ars_tn": round(venta.precio_tn or 0, 2),
        "valor_total_ars": round(venta.total or 0, 2),
        "estado": venta.estado,
        "tipo_contrato": "Venta directa",
    }


def _iter_months(start_month: str, end_month: str):
    year, month = map(int, start_month.split("-"))
    end_year, end_month_num = map(int, end_month.split("-"))

    while (year, month) <= (end_year, end_month_num):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month > 12:
            month = 1
            year += 1


async def get_comercial_resumen(
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

    pricing_campaign_ids: list[int] = []
    if resolved_campania_id:
        pricing_campaign_ids.append(resolved_campania_id)
        previous_campaign_id = await resolve_previous_campaign_id(
            db=db,
            current_campaign_id=resolved_campania_id,
        )
        if previous_campaign_id:
            pricing_campaign_ids.append(previous_campaign_id)

    pricing_query = (
        select(Venta, Producto, Cultivo)
        .join(Producto, Venta.producto_id == Producto.id)
        .outerjoin(Cultivo, Producto.cultivo_id == Cultivo.id)
    )
    if empresa_id:
        pricing_query = pricing_query.where(Venta.empresa_id == empresa_id)
    if pricing_campaign_ids:
        pricing_query = pricing_query.where(Venta.campania_id.in_(pricing_campaign_ids))
    if cultivo_id:
        pricing_query = pricing_query.where(Producto.cultivo_id == cultivo_id)
    pricing_rows = (await db.execute(pricing_query)).all()

    contratos_query = (
        select(Contrato, Cultivo, Cliente)
        .join(Cultivo, Contrato.cultivo_id == Cultivo.id)
        .join(Cliente, Contrato.cliente_id == Cliente.id)
    )
    if empresa_id:
        contratos_query = contratos_query.where(Contrato.empresa_id == empresa_id)
    if resolved_campania_id:
        contratos_query = contratos_query.where(Contrato.campania_id == resolved_campania_id)
    if cultivo_id:
        contratos_query = contratos_query.where(Contrato.cultivo_id == cultivo_id)
    contratos_rows = (await db.execute(contratos_query)).all()

    deliveries_query = (
        select(EntregaComercial, Contrato, Cultivo, Cliente)
        .join(Contrato, EntregaComercial.contrato_id == Contrato.id)
        .join(Cultivo, Contrato.cultivo_id == Cultivo.id)
        .join(Cliente, Contrato.cliente_id == Cliente.id)
    )
    if empresa_id:
        deliveries_query = deliveries_query.where(Contrato.empresa_id == empresa_id)
    if resolved_campania_id:
        deliveries_query = deliveries_query.where(Contrato.campania_id == resolved_campania_id)
    if cultivo_id:
        deliveries_query = deliveries_query.where(Contrato.cultivo_id == cultivo_id)
    delivery_rows = (await db.execute(deliveries_query)).all()

    position_rows = await load_position_rows(
        db=db,
        empresa_id=empresa_id,
        campania_id=resolved_campania_id,
        cultivo_id=cultivo_id,
    )
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
    alert_rows = await load_alert_rows(db=db, modules=("comercial",))

    valor_total = round(sum((venta.total or 0) for venta, _, _, _ in ventas_rows), 2)
    volumen_vendido = round(sum((venta.volumen or 0) for venta, _, _, _ in ventas_rows), 2)
    precio_promedio = round(
        (valor_total / volumen_vendido) if volumen_vendido > 0 else 0,
        2,
    )

    ventas_cliente_map: dict[str, dict[str, float]] = defaultdict(
        lambda: {"valor": 0.0, "volumen": 0.0}
    )
    precios_historicos_map: dict[str, dict[str, Optional[float]]] = {}
    precios_acumulados: dict[str, dict[str, dict[str, float]]] = defaultdict(dict)

    operaciones = []
    for venta, _, cultivo, cliente in ventas_rows:
        cultivo_nombre = cultivo.nombre if cultivo else "Sin cultivo"
        cliente_nombre = cliente.nombre if cliente else "Cliente"

        ventas_cliente_map[cliente_nombre]["valor"] += venta.total or 0
        ventas_cliente_map[cliente_nombre]["volumen"] += venta.volumen or 0

        operaciones.append(_build_operacion(venta, cultivo_nombre, cliente_nombre))

    for venta, _, cultivo in pricing_rows:
        if not venta.fecha or not cultivo:
            continue
        mes = venta.fecha.strftime("%Y-%m")
        cultivo_key = cultivo.nombre.lower()
        precios_acumulados.setdefault(mes, {})
        precios_acumulados[mes].setdefault(cultivo_key, {"total": 0.0, "count": 0})
        precios_acumulados[mes][cultivo_key]["total"] += venta.precio_tn or 0
        precios_acumulados[mes][cultivo_key]["count"] += 1

    monthly_average_map: dict[str, dict[str, Optional[float]]] = {}
    for mes, cultivos in precios_acumulados.items():
        monthly_average_map[mes] = {
            "soja": None,
            "maiz": None,
            "trigo": None,
            "girasol": None,
        }
        for cultivo_key, valores in cultivos.items():
            if cultivo_key in monthly_average_map[mes] and valores["count"] > 0:
                monthly_average_map[mes][cultivo_key] = round(
                    valores["total"] / valores["count"],
                    2,
                )

    if monthly_average_map:
        sorted_months = sorted(monthly_average_map.keys())
        carry_forward = {
            "soja": None,
            "maiz": None,
            "trigo": None,
            "girasol": None,
        }
        for mes in _iter_months(sorted_months[0], sorted_months[-1]):
            month_values = monthly_average_map.get(mes, {})
            row = {"fecha": mes, "soja": None, "maiz": None, "trigo": None, "girasol": None}
            for cultivo_key in ("soja", "maiz", "trigo", "girasol"):
                value = month_values.get(cultivo_key)
                if value is not None:
                    carry_forward[cultivo_key] = value
                row[cultivo_key] = carry_forward[cultivo_key]
            precios_historicos_map[mes] = row

    ventas_cliente = [
        {
            "cliente": cliente,
            "valor": round(valores["valor"], 2),
            "volumen": round(valores["volumen"], 2),
        }
        for cliente, valores in ventas_cliente_map.items()
    ]
    ventas_cliente.sort(key=lambda item: item["valor"], reverse=True)

    operaciones.sort(
        key=lambda item: item["fecha"] or "",
        reverse=True,
    )

    precios_historicos = [
        precios_historicos_map[mes]
        for mes in sorted(precios_historicos_map.keys())[-12:]
    ]

    contratos_cerrados = len(
        [contrato for contrato, _, _ in contratos_rows if contrato.estado == "cumplido"]
    )

    stock_by_crop: dict[str, float] = defaultdict(float)
    for stock, _, cultivo, _ in stock_rows:
        crop_name = cultivo.nombre if cultivo else "Sin cultivo"
        stock_by_crop[crop_name] += stock.volumen_disponible or 0

    posiciones_map: dict[str, dict[str, float | str]] = {}
    total_producidas = 0.0
    total_comprometidas = 0.0
    total_fijadas = 0.0
    total_entregadas = 0.0
    weighted_reference_value = 0.0
    weighted_reference_volume = 0.0
    for posicion, cultivo in position_rows:
        crop_name = cultivo.nombre
        bucket = posiciones_map.setdefault(
            crop_name,
            {
                "cultivo": crop_name,
                "toneladas_producidas": 0.0,
                "toneladas_comprometidas": 0.0,
                "toneladas_fijadas": 0.0,
                "toneladas_entregadas": 0.0,
                "stock_fisico": 0.0,
                "precio_referencia": 0.0,
                "precio_referencia_pond": 0.0,
                "recomendacion": posicion.recomendacion or "esperar",
            },
        )
        produced = posicion.toneladas_producidas or 0
        bucket["toneladas_producidas"] += produced
        bucket["toneladas_comprometidas"] += posicion.toneladas_comprometidas or 0
        bucket["toneladas_fijadas"] += posicion.toneladas_fijadas or 0
        bucket["toneladas_entregadas"] += posicion.toneladas_entregadas or 0
        bucket["precio_referencia_pond"] += (posicion.precio_referencia or 0) * produced
        if posicion.recomendacion in {"cubrir", "fijar"}:
            bucket["recomendacion"] = posicion.recomendacion

    posiciones = []
    for cultivo_nombre, bucket in posiciones_map.items():
        toneladas_producidas = float(bucket["toneladas_producidas"])
        toneladas_comprometidas = float(bucket["toneladas_comprometidas"])
        toneladas_fijadas = float(bucket["toneladas_fijadas"])
        toneladas_entregadas = float(bucket["toneladas_entregadas"])
        precio_referencia = round(
            float(bucket["precio_referencia_pond"]) / toneladas_producidas,
            2,
        ) if toneladas_producidas else 0
        stock_fisico = round(stock_by_crop.get(cultivo_nombre, 0), 2)
        abierta_tn = max(toneladas_producidas - toneladas_fijadas, 0)
        pendiente_entrega = max(toneladas_comprometidas - toneladas_entregadas, 0)
        cobertura_pct = round(
            (toneladas_fijadas / toneladas_producidas) * 100,
            1,
        ) if toneladas_producidas else 0
        compromiso_pct = round(
            (toneladas_comprometidas / toneladas_producidas) * 100,
            1,
        ) if toneladas_producidas else 0
        desvio_stock_cobertura = round(stock_fisico - pendiente_entrega, 2)
        severity = (
            "critical"
            if toneladas_producidas and abierta_tn > toneladas_producidas * 0.4
            else "warning"
            if toneladas_producidas and abierta_tn > toneladas_producidas * 0.25
            else "success"
        )
        posiciones.append(
            {
                "cultivo": cultivo_nombre,
                "toneladas_producidas": round(toneladas_producidas, 2),
                "toneladas_comprometidas": round(toneladas_comprometidas, 2),
                "toneladas_fijadas": round(toneladas_fijadas, 2),
                "toneladas_entregadas": round(toneladas_entregadas, 2),
                "stock_fisico": stock_fisico,
                "abierta_tn": round(abierta_tn, 2),
                "pendiente_entrega_tn": round(pendiente_entrega, 2),
                "cobertura_pct": cobertura_pct,
                "compromiso_pct": compromiso_pct,
                "desvio_stock_cobertura_tn": desvio_stock_cobertura,
                "precio_referencia": precio_referencia,
                "recomendacion": bucket["recomendacion"],
                "severidad": severity,
            }
        )

        total_producidas += toneladas_producidas
        total_comprometidas += toneladas_comprometidas
        total_fijadas += toneladas_fijadas
        total_entregadas += toneladas_entregadas
        weighted_reference_value += precio_referencia * toneladas_producidas
        weighted_reference_volume += toneladas_producidas

    posiciones.sort(key=lambda item: item["abierta_tn"], reverse=True)
    posicion_abierta_tn = round(max(total_producidas - total_fijadas, 0), 2)
    cobertura_promedio_pct = round(
        (total_fijadas / total_producidas) * 100,
        1,
    ) if total_producidas else 0
    precio_referencia_ponderado = round(
        weighted_reference_value / weighted_reference_volume,
        2,
    ) if weighted_reference_volume else 0
    desvio_precio_vs_referencia = round(
        ((precio_promedio - precio_referencia_ponderado) / precio_referencia_ponderado) * 100,
        1,
    ) if precio_referencia_ponderado else 0

    proximos_vencer = []
    today = date.today()
    for contrato, cultivo, cliente in contratos_rows:
        if contrato.estado == "cumplido":
            continue
        dias = (contrato.fecha_entrega - today).days
        if dias <= 21:
            proximos_vencer.append(
                {
                    "id": contrato.id,
                    "cultivo": cultivo.nombre,
                    "cliente": cliente.nombre,
                    "volumen_tn": round(contrato.volumen_contratado, 2),
                    "fecha_entrega": contrato.fecha_entrega.isoformat(),
                    "dias_para_vencer": dias,
                    "estado": contrato.estado,
                    "precio_fijado": round(contrato.precio_fijado or 0, 2),
                }
            )
    proximos_vencer.sort(key=lambda item: item["dias_para_vencer"])

    entregas = []
    for entrega, contrato, cultivo, cliente in delivery_rows:
        pendiente = max((contrato.volumen_contratado or 0) - (entrega.volumen_tn or 0), 0)
        entregas.append(
            {
                "cultivo": cultivo.nombre,
                "cliente": cliente.nombre,
                "fecha_programada": entrega.fecha_programada.isoformat(),
                "fecha_entrega": entrega.fecha_entrega.isoformat() if entrega.fecha_entrega else None,
                "volumen_tn": round(entrega.volumen_tn or 0, 2),
                "pendiente_tn": round(pendiente, 2),
                "estado": entrega.estado,
            }
        )
    entregas.sort(key=lambda item: item["fecha_programada"])

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
    if proximos_vencer:
        first_due = proximos_vencer[0]
        alerts.insert(
            0,
            {
                "titulo": f"Contrato próximo a vencer: {first_due['cultivo']}",
                "descripcion": (
                    f"Quedan {first_due['dias_para_vencer']} días para cumplir con "
                    f"{first_due['volumen_tn']:.0f} tn hacia {first_due['cliente']}."
                ),
                "accion": "Confirmar cupo, entrega y fijación pendiente",
                "severidad": "critical" if first_due["dias_para_vencer"] <= 7 else "warning",
                "prioridad": 1,
            }
        )

    actions = []
    if posiciones:
        exposed = posiciones[0]
        recommendation_text = {
            "fijar": "Cerrar una fijación parcial escalonada",
            "cubrir": "Cubrir faltante comercial o asegurar mercadería física",
            "esperar": "Esperar una mejor ventana de precio con control de riesgo",
        }.get(exposed["recomendacion"], "Definir estrategia comercial")
        actions.append(
            {
                "titulo": f"{recommendation_text} para {exposed['cultivo']}",
                "descripcion": (
                    f"Hay {exposed['abierta_tn']:.0f} tn abiertas y "
                    f"{exposed['pendiente_entrega_tn']:.0f} tn pendientes de entrega."
                ),
                "owner": "Mesa comercial",
                "impacto": "Reduce exposición de precio y riesgo de incumplimiento",
                "severity": "critical" if exposed["severidad"] == "critical" else "warning",
            }
        )
    if desvio_precio_vs_referencia < -4:
        actions.append(
            {
                "titulo": "Revisar estrategia de fijación vs mercado",
                "descripcion": (
                    f"El precio promedio realizado está {abs(desvio_precio_vs_referencia):.1f}% "
                    "por debajo de la referencia ponderada."
                ),
                "owner": "Comercial",
                "impacto": "Mejora precio medio y protege margen",
                "severity": "warning",
            }
        )
    if proximos_vencer:
        actions.append(
            {
                "titulo": "Asegurar entregas de contratos cercanos",
                "descripcion": "Hay contratos que vencen dentro de las próximas tres semanas.",
                "owner": "Logística y comercial",
                "impacto": "Evita penalidades y desvíos de cupo",
                "severity": "critical" if proximos_vencer[0]["dias_para_vencer"] <= 7 else "warning",
            }
        )

    return {
        "summary": {
            "volumen_vendido": volumen_vendido,
            "precio_promedio": precio_promedio,
            "valor_total": valor_total,
            "contratos_cerrados": contratos_cerrados,
            "toneladas_producidas": round(total_producidas, 2),
            "toneladas_comprometidas": round(total_comprometidas, 2),
            "toneladas_fijadas": round(total_fijadas, 2),
            "toneladas_entregadas": round(total_entregadas, 2),
            "posicion_abierta_tn": posicion_abierta_tn,
            "cobertura_promedio_pct": cobertura_promedio_pct,
            "desvio_precio_vs_referencia_pct": desvio_precio_vs_referencia,
        },
        "precios_historicos": precios_historicos,
        "ventas_cliente": ventas_cliente[:8],
        "operaciones": operaciones[:25],
        "posiciones": posiciones,
        "entregas": entregas[:10],
        "proximos_vencer": proximos_vencer[:8],
        "alerts": alerts[:6],
        "actions": actions[:5],
        "ultima_actualizacion": datetime.now().isoformat(),
    }


async def get_operaciones(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 20,
):
    v_q = (
        select(Venta, Producto, Cliente, Empresa, Campania)
        .join(Producto, Venta.producto_id == Producto.id)
        .join(Cliente, Venta.cliente_id == Cliente.id)
        .join(Empresa, Venta.empresa_id == Empresa.id)
        .outerjoin(Campania, Venta.campania_id == Campania.id)
    )

    if empresa_id:
        v_q = v_q.where(Venta.empresa_id == empresa_id)
    if campania_id:
        v_q = v_q.where(Venta.campania_id == campania_id)
    if cultivo_id:
        v_q = v_q.join(Cultivo, Producto.cultivo_id == Cultivo.id).where(
            Producto.cultivo_id == cultivo_id
        )

    count_q = select(func.count()).select_from(v_q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    v_q = (
        v_q.order_by(Venta.fecha.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(v_q)
    rows = result.all()

    items = []
    for venta, producto, cliente, empresa, campania in rows:
        items.append(
            {
                "id": venta.id,
                "empresa_id": venta.empresa_id,
                "empresa_nombre": empresa.nombre,
                "producto_id": venta.producto_id,
                "producto_nombre": producto.nombre,
                "cliente_id": venta.cliente_id,
                "cliente_nombre": cliente.nombre,
                "campania_id": venta.campania_id,
                "campania_nombre": campania.nombre if campania else None,
                "fecha": venta.fecha,
                "volumen": venta.volumen,
                "precio_tn": venta.precio_tn,
                "total": venta.total,
                "estado": venta.estado,
            }
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
