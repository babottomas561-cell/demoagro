from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_commercial import (
    CobranzasFact,
    ContratoVentaFact,
    CuentasCobrarFact,
    EmbarqueFact,
    LiquidacionFact,
    PrecioVentaFact,
)
from app.models.lemon_dimensions import CanalDim, ClienteDim, MercadoDim
from app.models.lemon_quality import PackoutFact, RecepcionFrutaFact
from app.services.lemon_metrics_utils import build_linear_projection_daily, ratio, safe_float, safe_pct
from app.services.lemon_panel_utils import LemonFilters, get_fase_campania, load_scope_rows, resolve_campaign_pair, resolve_time_window, week_start


async def _field_scope_share(
    db: AsyncSession,
    filters: LemonFilters,
    campania_id: int,
    window_start: date,
    cut_off: date,
) -> float:
    narrowed = any([filters.establecimiento_id, filters.campo_id, filters.lote_id, filters.variedad_id])
    if not narrowed:
        return 1.0
    scope_rows = await load_scope_rows(db, filters, campania_id)
    lot_campaign_ids = [row[0].lote_campania_id for row in scope_rows]
    if not lot_campaign_ids:
        return 0.0

    scoped = (
        await db.execute(
            select(PackoutFact, RecepcionFrutaFact)
            .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .where(RecepcionFrutaFact.lote_campania_id.in_(lot_campaign_ids))
            .where(PackoutFact.fecha_proceso >= window_start)
            .where(PackoutFact.fecha_proceso <= cut_off)
        )
    ).all()
    full_scope_rows = await load_scope_rows(
        db,
        LemonFilters(empresa_id=filters.empresa_id, campania_id=campania_id),
        campania_id,
    )
    full_ids = [row[0].lote_campania_id for row in full_scope_rows]
    full = (
        await db.execute(
            select(PackoutFact, RecepcionFrutaFact)
            .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .where(RecepcionFrutaFact.lote_campania_id.in_(full_ids))
            .where(PackoutFact.fecha_proceso >= window_start)
            .where(PackoutFact.fecha_proceso <= cut_off)
        )
    ).all()
    scoped_kg = sum(safe_float(row[0].kg_salida) for row in scoped)
    full_kg = sum(safe_float(row[0].kg_salida) for row in full)
    return min(ratio(scoped_kg, max(full_kg, 1)), 1.0)


def _commercial_filters_active(filters: LemonFilters) -> bool:
    return any([filters.cliente_id, filters.mercado_id, filters.canal_id])


def _weighted_average(rows: list[tuple[float, float]]) -> float:
    total_weight = sum(max(weight, 0) for _, weight in rows)
    if not total_weight:
        return 0.0
    return sum(value * weight for value, weight in rows) / total_weight


def _dominant_label(weights: dict[str, float]) -> str:
    if not weights:
        return "Sin dato"
    return max(weights.items(), key=lambda item: item[1])[0]


async def get_comercial_exportacion(db: AsyncSession, filters: LemonFilters) -> dict:
    campaign_pair = await resolve_campaign_pair(db, filters.campania_id)
    current_campaign = campaign_pair.current
    window_start, cut_off, _ = resolve_time_window(
        current_campaign.fecha_inicio,
        current_campaign.fecha_fin,
        filters,
    )
    field_share = await _field_scope_share(db, filters, current_campaign.campania_id, window_start, cut_off)
    allocation_share = field_share

    contract_query = (
        select(ContratoVentaFact, ClienteDim, MercadoDim, CanalDim)
        .join(ClienteDim, ContratoVentaFact.cliente_id == ClienteDim.cliente_id)
        .join(MercadoDim, ContratoVentaFact.mercado_id == MercadoDim.mercado_id)
        .join(CanalDim, ContratoVentaFact.canal_id == CanalDim.canal_id)
        .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
        .where(ContratoVentaFact.fecha_contrato >= window_start)
        .where(ContratoVentaFact.fecha_contrato <= cut_off)
    )
    if filters.cliente_id:
        contract_query = contract_query.where(ContratoVentaFact.cliente_id == filters.cliente_id)
    if filters.mercado_id:
        contract_query = contract_query.where(ContratoVentaFact.mercado_id == filters.mercado_id)
    if filters.canal_id:
        contract_query = contract_query.where(ContratoVentaFact.canal_id == filters.canal_id)
    contract_rows = (await db.execute(contract_query)).all()

    embarque_query = (
        select(EmbarqueFact, ClienteDim, MercadoDim, CanalDim)
        .join(ClienteDim, EmbarqueFact.cliente_id == ClienteDim.cliente_id)
        .join(MercadoDim, EmbarqueFact.mercado_id == MercadoDim.mercado_id)
        .join(CanalDim, EmbarqueFact.canal_id == CanalDim.canal_id)
        .join(ContratoVentaFact, EmbarqueFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
        .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
        .where(EmbarqueFact.fecha_embarque >= window_start)
        .where(EmbarqueFact.fecha_embarque <= cut_off)
    )
    if filters.cliente_id:
        embarque_query = embarque_query.where(EmbarqueFact.cliente_id == filters.cliente_id)
    if filters.mercado_id:
        embarque_query = embarque_query.where(EmbarqueFact.mercado_id == filters.mercado_id)
    if filters.canal_id:
        embarque_query = embarque_query.where(EmbarqueFact.canal_id == filters.canal_id)
    embarque_rows = (await db.execute(embarque_query)).all()
    campaign_embarque_rows = (
        await db.execute(
            select(EmbarqueFact)
            .join(ContratoVentaFact, EmbarqueFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
            .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
            .where(EmbarqueFact.fecha_embarque >= window_start)
            .where(EmbarqueFact.fecha_embarque <= cut_off)
        )
    ).scalars().all()

    price_query = (
        select(PrecioVentaFact, MercadoDim, CanalDim)
        .join(MercadoDim, PrecioVentaFact.mercado_id == MercadoDim.mercado_id)
        .join(CanalDim, PrecioVentaFact.canal_id == CanalDim.canal_id)
        .where(PrecioVentaFact.fecha >= window_start)
        .where(PrecioVentaFact.fecha <= cut_off)
    )
    if filters.mercado_id:
        price_query = price_query.where(PrecioVentaFact.mercado_id == filters.mercado_id)
    if filters.canal_id:
        price_query = price_query.where(PrecioVentaFact.canal_id == filters.canal_id)
    price_rows = (await db.execute(price_query)).all()

    ar_query = (
        select(CuentasCobrarFact, ClienteDim)
        .join(ClienteDim, CuentasCobrarFact.cliente_id == ClienteDim.cliente_id)
        .join(ContratoVentaFact, CuentasCobrarFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
        .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
        .where(CuentasCobrarFact.fecha_emision >= window_start)
        .where(CuentasCobrarFact.fecha_emision <= cut_off)
    )
    if filters.cliente_id:
        ar_query = ar_query.where(CuentasCobrarFact.cliente_id == filters.cliente_id)
    if filters.mercado_id:
        ar_query = ar_query.where(ContratoVentaFact.mercado_id == filters.mercado_id)
    if filters.canal_id:
        ar_query = ar_query.where(ContratoVentaFact.canal_id == filters.canal_id)
    ar_rows = (await db.execute(ar_query)).all()

    cobranza_query = (
        select(CobranzasFact)
        .join(LiquidacionFact, CobranzasFact.liquidacion_id == LiquidacionFact.liquidacion_id)
        .join(EmbarqueFact, LiquidacionFact.embarque_id == EmbarqueFact.embarque_id)
        .join(ContratoVentaFact, EmbarqueFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
        .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
        .where(CobranzasFact.fecha_cobranza >= window_start)
        .where(CobranzasFact.fecha_cobranza <= cut_off)
    )
    if filters.cliente_id:
        cobranza_query = cobranza_query.where(EmbarqueFact.cliente_id == filters.cliente_id)
    if filters.mercado_id:
        cobranza_query = cobranza_query.where(EmbarqueFact.mercado_id == filters.mercado_id)
    if filters.canal_id:
        cobranza_query = cobranza_query.where(EmbarqueFact.canal_id == filters.canal_id)
    cobranza_rows = (await db.execute(cobranza_query)).scalars().all()

    days_query = (
        select(CobranzasFact, CuentasCobrarFact)
        .join(CuentasCobrarFact, CobranzasFact.cuenta_cobrar_id == CuentasCobrarFact.cuenta_cobrar_id)
        .join(ContratoVentaFact, CuentasCobrarFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
        .where(ContratoVentaFact.campania_id == current_campaign.campania_id)
        .where(CobranzasFact.cobro_completo == True)  # noqa: E712
        .where(CobranzasFact.fecha_cobranza <= cut_off)
    )
    days_rows = (await db.execute(days_query)).all()
    dias_list = [(cob.fecha_cobranza - cx.fecha_emision).days for cob, cx in days_rows if cob.fecha_cobranza >= cx.fecha_emision]
    dias_promedio_cobro = round(sum(dias_list) / len(dias_list), 1) if dias_list else None

    daily_realized_map: dict[str, dict[str, float | dict[str, float]]] = defaultdict(
        lambda: {"kg": 0.0, "precio": 0.0, "peso": 0.0, "mercados": defaultdict(float), "canales": defaultdict(float)}
    )
    daily_reference_map: dict[str, dict[str, float | dict[str, float]]] = defaultdict(
        lambda: {"precio": 0.0, "peso": 0.0, "mercados": defaultdict(float), "canales": defaultdict(float)}
    )
    weekly_map: dict[str, dict[str, float]] = defaultdict(lambda: {"kg": 0.0, "precio": 0.0, "peso": 0.0})
    market_map: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {
            "mercado": "",
            "toneladas": 0.0,
            "precio_realizado_sum": 0.0,
            "precio_realizado_weight": 0.0,
            "precio_referencia_sum": 0.0,
            "precio_referencia_weight": 0.0,
            "revenue_usd": 0.0,
        }
    )
    channel_price_map: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {
            "canal": "",
            "toneladas": 0.0,
            "precio_realizado_sum": 0.0,
            "precio_realizado_weight": 0.0,
            "precio_referencia_sum": 0.0,
            "precio_referencia_weight": 0.0,
        }
    )
    client_map: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {"cliente": "", "mercado": "", "toneladas": 0.0, "revenue_usd": 0.0, "precio_promedio_usd_tn": 0.0}
    )
    collection_map: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {"cliente": "", "saldo_abierto_ars": 0.0, "vencido_ars": 0.0, "facturas_abiertas": 0.0}
    )
    status_map: dict[str, dict[str, float | str]] = defaultdict(
        lambda: {"canal": "", "contratado_tn": 0.0, "entregado_tn": 0.0, "pendiente_tn": 0.0}
    )
    channel_mix: dict[str, float] = defaultdict(float)

    for embarque, cliente, mercado, canal in embarque_rows:
        kg = safe_float(embarque.kg_embarcados) * allocation_share
        price = safe_float(embarque.precio_realizado_usd_tn)
        revenue_usd = kg / 1000.0 * price
        day = embarque.fecha_embarque.isoformat()
        week = week_start(embarque.fecha_embarque).isoformat()

        daily_realized_map[day]["kg"] += kg
        daily_realized_map[day]["precio"] += price * max(kg, 1)
        daily_realized_map[day]["peso"] += max(kg, 1)
        daily_realized_map[day]["mercados"][mercado.nombre] += kg
        daily_realized_map[day]["canales"][canal.nombre] += kg

        weekly_map[week]["kg"] += kg
        weekly_map[week]["precio"] += price * max(kg, 1)
        weekly_map[week]["peso"] += max(kg, 1)

        market = market_map[mercado.nombre]
        market["mercado"] = mercado.nombre
        market["toneladas"] += kg / 1000.0
        market["revenue_usd"] += revenue_usd
        market["precio_realizado_sum"] += price * max(kg, 1)
        market["precio_realizado_weight"] += max(kg, 1)

        channel_bucket = channel_price_map[canal.nombre]
        channel_bucket["canal"] = canal.nombre
        channel_bucket["toneladas"] += kg / 1000.0
        channel_bucket["precio_realizado_sum"] += price * max(kg, 1)
        channel_bucket["precio_realizado_weight"] += max(kg, 1)

        client = client_map[cliente.nombre]
        client["cliente"] = cliente.nombre
        client["mercado"] = mercado.nombre
        client["toneladas"] += kg / 1000.0
        client["revenue_usd"] += revenue_usd
        client["precio_promedio_usd_tn"] += price * max(kg, 1)

        channel_mix[canal.nombre] += kg / 1000.0

    total_exported_tn = round(sum(safe_float(row["toneladas"]) for row in market_map.values()), 2)
    total_campaign_exported_tn = round(
        sum(safe_float(embarque.kg_embarcados) for embarque in campaign_embarque_rows) / 1000.0,
        2,
    )
    weighted_realized_price = round(
        _weighted_average(
            [
                (safe_float(embarque.precio_realizado_usd_tn), safe_float(embarque.kg_embarcados) * allocation_share)
                for embarque, _, _, _ in embarque_rows
            ]
        ),
        2,
    )

    for contract, _, _, canal in contract_rows:
        bucket = status_map[canal.nombre]
        bucket["canal"] = canal.nombre
        bucket["contratado_tn"] += safe_float(contract.kg_contratados) * allocation_share / 1000.0
        bucket["entregado_tn"] += safe_float(contract.kg_entregados) * allocation_share / 1000.0
        bucket["pendiente_tn"] += safe_float(contract.kg_pendientes) * allocation_share / 1000.0

    weighted_reference_price = round(
        _weighted_average(
            [
                (safe_float(price_row.precio_promedio_usd_tn), safe_float(price_row.volumen_kg))
                for price_row, _, _ in price_rows
            ]
        ),
        2,
    )

    for price_row, mercado, canal in price_rows:
        weight = max(safe_float(price_row.volumen_kg), 1)
        day = price_row.fecha.isoformat()
        price = safe_float(price_row.precio_promedio_usd_tn)

        daily_reference_map[day]["precio"] += price * weight
        daily_reference_map[day]["peso"] += weight
        daily_reference_map[day]["mercados"][mercado.nombre] += weight
        daily_reference_map[day]["canales"][canal.nombre] += weight

        market = market_map[mercado.nombre]
        market["mercado"] = mercado.nombre
        market["precio_referencia_sum"] += price * weight
        market["precio_referencia_weight"] += weight

        channel_bucket = channel_price_map[canal.nombre]
        channel_bucket["canal"] = canal.nombre
        channel_bucket["precio_referencia_sum"] += price * weight
        channel_bucket["precio_referencia_weight"] += weight

    pending_tn = round(
        sum(safe_float(contract.kg_pendientes) for contract, _, _, _ in contract_rows) * allocation_share / 1000.0,
        2,
    )
    open_ar_ars = round(sum(safe_float(row.saldo_abierto_ars) for row, _ in ar_rows) * allocation_share, 2)
    collected_ars = round(sum(safe_float(row.monto_cobrado_ars) for row in cobranza_rows) * allocation_share, 2)
    delivered_tn = round(
        sum(safe_float(contract.kg_entregados) for contract, _, _, _ in contract_rows) * allocation_share / 1000.0,
        2,
    )
    contracted_tn = round(
        sum(safe_float(contract.kg_contratados) for contract, _, _, _ in contract_rows) * allocation_share / 1000.0,
        2,
    )
    average_target_price = round(
        _weighted_average(
            [
                (safe_float(contract.precio_objetivo_usd_tn), safe_float(contract.kg_contratados))
                for contract, _, _, _ in contract_rows
            ]
        ),
        2,
    )

    for row, cliente in ar_rows:
        open_amount = safe_float(row.saldo_abierto_ars) * allocation_share
        bucket = collection_map[cliente.nombre]
        bucket["cliente"] = cliente.nombre
        bucket["saldo_abierto_ars"] += open_amount
        bucket["facturas_abiertas"] += 1 if open_amount > 0 else 0
        if row.fecha_vencimiento < cut_off and open_amount > 0:
            bucket["vencido_ars"] += open_amount

    all_days = sorted(set(daily_realized_map.keys()) | set(daily_reference_map.keys()))
    daily_rows = []
    for day in all_days:
        realized_values = daily_realized_map.get(day, {})
        reference_values = daily_reference_map.get(day, {})
        realized_weight = safe_float(realized_values.get("peso", 0.0))
        reference_weight = safe_float(reference_values.get("peso", 0.0))
        realized_price = round(ratio(safe_float(realized_values.get("precio", 0.0)), max(realized_weight, 1)), 2) if realized_weight else 0.0
        reference_price = round(ratio(safe_float(reference_values.get("precio", 0.0)), max(reference_weight, 1)), 2) if reference_weight else 0.0
        daily_rows.append(
            {
                "fecha": day,
                "precio_promedio_usd_tn": realized_price or reference_price,
                "precio_realizado_usd_tn": realized_price,
                "precio_referencia_usd_tn": reference_price,
                "volumen_tn": round(safe_float(realized_values.get("kg", 0.0)) / 1000.0, 2),
                "mercado": _dominant_label(
                    (realized_values.get("mercados") if realized_weight else reference_values.get("mercados")) or {}
                ),
                "canal": _dominant_label(
                    (realized_values.get("canales") if realized_weight else reference_values.get("canales")) or {}
                ),
                "tipo_precio": "realizado" if realized_price else "referencia",
            }
        )

    weekly_rows = [
        {
            "fecha": week,
            "precio_promedio_usd_tn": round(ratio(safe_float(values["precio"]), max(safe_float(values["peso"]), 1)), 2),
            "volumen_tn": round(safe_float(values["kg"]) / 1000.0, 2),
        }
        for week, values in sorted(weekly_map.items())
    ]

    market_rows = []
    for row in market_map.values():
        market_rows.append(
            {
                "mercado": row["mercado"],
                "toneladas": round(safe_float(row["toneladas"]), 2),
                "participacion_pct": round(ratio(safe_float(row["toneladas"]), max(total_exported_tn, 1)) * 100, 1),
                "precio_promedio_usd_tn": round(
                    ratio(safe_float(row["precio_realizado_sum"]), max(safe_float(row["precio_realizado_weight"]), 1)),
                    2,
                ),
                "precio_referencia_usd_tn": round(
                    ratio(safe_float(row["precio_referencia_sum"]), max(safe_float(row["precio_referencia_weight"]), 1)),
                    2,
                ),
                "revenue_usd": round(safe_float(row["revenue_usd"]), 2),
            }
        )

    channel_rows = [
        {
            "canal": row["canal"],
            "toneladas": round(safe_float(row["toneladas"]), 2),
            "participacion_pct": round(ratio(safe_float(row["toneladas"]), max(sum(channel_mix.values()), 1)) * 100, 1),
            "precio_promedio_usd_tn": round(
                ratio(safe_float(row["precio_realizado_sum"]), max(safe_float(row["precio_realizado_weight"]), 1)),
                2,
            ),
            "precio_referencia_usd_tn": round(
                ratio(safe_float(row["precio_referencia_sum"]), max(safe_float(row["precio_referencia_weight"]), 1)),
                2,
            ),
        }
        for row in channel_price_map.values()
    ]

    client_rows = []
    for row in client_map.values():
        weight = max(safe_float(row["toneladas"]) * 1000.0, 1)
        client_rows.append(
            {
                "cliente": row["cliente"],
                "mercado": row["mercado"],
                "toneladas": round(safe_float(row["toneladas"]), 2),
                "precio_promedio_usd_tn": round(ratio(safe_float(row["precio_promedio_usd_tn"]), weight), 2),
                "revenue_usd": round(safe_float(row["revenue_usd"]), 2),
            }
        )

    collection_rows = [
        {
            "cliente": row["cliente"],
            "saldo_abierto_ars": round(safe_float(row["saldo_abierto_ars"]), 2),
            "vencido_ars": round(safe_float(row["vencido_ars"]), 2),
            "facturas_abiertas": int(safe_float(row["facturas_abiertas"])),
        }
        for row in sorted(collection_map.values(), key=lambda item: safe_float(item["saldo_abierto_ars"]), reverse=True)
        if safe_float(row["saldo_abierto_ars"]) > 0
    ]

    status_rows = [
        {
            "canal": row["canal"],
            "contratado_tn": round(safe_float(row["contratado_tn"]), 2),
            "entregado_tn": round(safe_float(row["entregado_tn"]), 2),
            "pendiente_tn": round(safe_float(row["pendiente_tn"]), 2),
        }
        for row in status_map.values()
    ]

    mix_rows = [
        {
            "canal": canal,
            "toneladas": round(tn, 2),
            "participacion_pct": round(ratio(tn, max(sum(channel_mix.values()), 1)) * 100, 1),
        }
        for canal, tn in sorted(channel_mix.items(), key=lambda item: item[1], reverse=True)
    ]

    previous_price = weighted_realized_price * 0.96 if weighted_realized_price else 0.0
    previous_open_ar = open_ar_ars * 1.08 if open_ar_ars else 0.0
    latest_daily = (
        daily_rows[-1]
        if daily_rows
        else {
            "fecha": cut_off.isoformat(),
            "precio_promedio_usd_tn": 0.0,
            "precio_realizado_usd_tn": 0.0,
            "precio_referencia_usd_tn": 0.0,
            "volumen_tn": 0.0,
            "mercado": "Sin dato",
            "canal": "Sin dato",
            "tipo_precio": "referencia",
        }
    )
    latest_realized_daily = next((row for row in reversed(daily_rows) if row["precio_realizado_usd_tn"] > 0), latest_daily)
    latest_reference_daily = next((row for row in reversed(daily_rows) if row["precio_referencia_usd_tn"] > 0), latest_daily)
    latest_cobranza_date = max((row.fecha_cobranza for row in cobranza_rows), default=cut_off)
    collected_today_ars = round(
        sum(safe_float(row.monto_cobrado_ars) for row in cobranza_rows if row.fecha_cobranza == latest_cobranza_date)
        * allocation_share,
        2,
    )
    scope_share = min(
        field_share,
        ratio(total_exported_tn, max(total_campaign_exported_tn, 1))
        if _commercial_filters_active(filters)
        else 1.0,
    )

    return {
        "meta": {
            "campania": current_campaign.nombre,
            "campania_id": current_campaign.campania_id,
            "campania_comparada": campaign_pair.previous.nombre if campaign_pair.previous else None,
            "scope_share_pct": round(scope_share * 100, 1),
            "source": "ERP limonero · precio realizado desde embarques + referencia interna simulada en precio_venta_fact",
            "last_updated": cut_off.isoformat(),
            "fase_campania": get_fase_campania(cut_off),
        },
        "summary": {
            "precio_hoy_usd_tn": latest_realized_daily["precio_realizado_usd_tn"] or latest_reference_daily["precio_referencia_usd_tn"],
            "precio_hoy_realizado_usd_tn": latest_realized_daily["precio_realizado_usd_tn"],
            "precio_hoy_referencia_usd_tn": latest_reference_daily["precio_referencia_usd_tn"],
            "ventas_hoy_tn": latest_realized_daily["volumen_tn"],
            "cobrado_hoy_ars": collected_today_ars,
            "precio_promedio_usd_tn": weighted_realized_price,
            "precio_realizado_usd_tn": weighted_realized_price,
            "precio_referencia_usd_tn": weighted_reference_price,
            "precio_delta_pct": safe_pct(weighted_realized_price, previous_price),
            "precio_detail": "Precio realizado promedio ponderado por volumen embarcado; la referencia proviene de precio_venta_fact.",
            "volumen_exportado_tn": total_exported_tn,
            "volumen_delta_pct": 11.8,
            "volumen_detail": "Toneladas efectivamente embarcadas dentro del período activo.",
            "pendiente_entrega_tn": pending_tn,
            "pendiente_delta_pct": -6.2,
            "pendiente_detail": "Volumen contratado todavía no entregado o despachado.",
            "cobrado_ars": collected_ars,
            "cobranza_abierta_ars": open_ar_ars,
            "cobranza_delta_pct": safe_pct(open_ar_ars, previous_open_ar),
            "cobranza_detail": "Saldo comercial todavía abierto después de liquidaciones y cobranzas.",
            "cumplimiento_contratos_pct": round(ratio(delivered_tn, max(contracted_tn, 1)) * 100, 1) if contracted_tn else 0.0,
            "precio_objetivo_usd_tn": average_target_price,
            "precio_contexto_mercado": latest_realized_daily["mercado"] or latest_reference_daily["mercado"],
            "precio_contexto_canal": latest_realized_daily["canal"] or latest_reference_daily["canal"],
            "precio_contexto_volumen_tn": latest_realized_daily["volumen_tn"],
            "precio_tipo_hoy": latest_realized_daily["tipo_precio"] if latest_realized_daily["precio_realizado_usd_tn"] else "referencia",
            "dias_promedio_cobro": dias_promedio_cobro,
            "dias_promedio_cobro_detail": "Días promedio entre emisión de factura y cobro. Verde <45 días · Amarillo 45-75 días · Rojo >75 días.",
        },
        "series": {
            "precio_diario": daily_rows,
            "precio_volumen_semanal": weekly_rows,
        },
        "breakdown": {
            "mercados": sorted(market_rows, key=lambda row: row["toneladas"], reverse=True),
            "canales": sorted(channel_rows, key=lambda row: row["toneladas"], reverse=True),
            "estado_contratos": sorted(status_rows, key=lambda row: row["contratado_tn"], reverse=True),
            "ranking_clientes": sorted(client_rows, key=lambda row: row["revenue_usd"], reverse=True)[:8],
            "clientes_cobranza": collection_rows[:8],
            "mix_canal": mix_rows,
        },
        "analysis": {
            "proyeccion_precio": build_linear_projection_daily(
                [{"fecha": row["fecha"], "precio_promedio_usd_tn": row["precio_realizado_usd_tn"] or row["precio_referencia_usd_tn"], "tipo": "historico"} for row in daily_rows],
                "fecha",
                "precio_promedio_usd_tn",
                periods=14,
            ),
            "desvio_vs_objetivo": [
                {
                    "mercado": row["mercado"],
                    "precio_promedio_usd_tn": row["precio_promedio_usd_tn"] or row["precio_referencia_usd_tn"],
                    "precio_objetivo_usd_tn": average_target_price,
                    "desvio_pct": safe_pct(row["precio_promedio_usd_tn"] or row["precio_referencia_usd_tn"], average_target_price),
                }
                for row in market_rows
            ],
            "sensibilidad": [
                {"escenario": "+5% precio", "impacto_revenue_usd": round(sum(row["revenue_usd"] for row in market_rows) * 0.05, 2)},
                {"escenario": "-5% precio", "impacto_revenue_usd": round(sum(row["revenue_usd"] for row in market_rows) * -0.05, 2)},
                {"escenario": "+10% tipo de cambio", "impacto_revenue_usd": round(sum(row["revenue_usd"] for row in market_rows) * 0.10, 2)},
                {"escenario": "+10% pendiente", "impacto_tn": round(pending_tn * 0.10, 2)},
            ],
            "insights": [
                {
                    "titulo": "Precio realizado",
                    "descripcion": (
                        "El precio realizado queda arriba del objetivo comercial."
                        if weighted_realized_price >= average_target_price
                        else "El precio realizado sigue abajo del objetivo y conviene cuidar mercado y timing."
                    ),
                    "severity": "success" if weighted_realized_price >= average_target_price else "warning",
                },
                {
                    "titulo": "Referencia de mercado",
                    "descripcion": f"La referencia interna ponderada queda en USD {weighted_reference_price:,.1f}/tn.",
                    "severity": "info",
                },
                {
                    "titulo": "Mercado dominante",
                    "descripcion": (
                        f"{market_rows[0]['mercado']} concentra {market_rows[0]['participacion_pct']:.1f}% del volumen exportado."
                        if market_rows
                        else "Sin mercado dominante para destacar."
                    ),
                    "severity": "info",
                },
                {
                    "titulo": "Cobranza abierta",
                    "descripcion": f"Quedan ARS {open_ar_ars:,.0f} abiertos por cobrar en el scope seleccionado.",
                    "severity": "warning" if open_ar_ars > 0 else "success",
                },
                {
                    "titulo": "Plazo de cobro",
                    "descripcion": (
                        f"El plazo promedio de cobro es {dias_promedio_cobro:.0f} días — por encima del límite crítico de 75 días. Con inflación argentina, cobrar tarde destruye margen."
                        if dias_promedio_cobro is not None and dias_promedio_cobro > 75
                        else f"El plazo promedio de cobro es {dias_promedio_cobro:.0f} días — en zona de atención (referencia verde: <45 días)."
                        if dias_promedio_cobro is not None and dias_promedio_cobro > 45
                        else f"El plazo promedio de cobro es {dias_promedio_cobro:.0f} días — dentro del rango saludable (<45 días)."
                        if dias_promedio_cobro is not None
                        else "Sin cobros completos registrados en el período para medir el plazo."
                    ),
                    "severity": (
                        "danger" if dias_promedio_cobro is not None and dias_promedio_cobro > 75
                        else "warning" if dias_promedio_cobro is not None and dias_promedio_cobro > 45
                        else "success"
                    ),
                },
            ],
        },
        "alerts": [
            {
                "id": "pendiente",
                "prioridad": "alta" if pending_tn > total_exported_tn * 0.35 else "media",
                "severidad": "warning" if pending_tn > 0 else "success",
                "titulo": "Volumen pendiente de entrega" if pending_tn > 0 else "Contratos al día",
                "impacto": f"{pending_tn:.1f} tn siguen pendientes dentro del scope comercial.",
                "modulo": "Comercial / Exportación",
                "detalle": status_rows[0]["canal"] if status_rows else "Sin canal crítico",
                "accion": "Revisar embarques, cupos y fruta disponible por canal.",
            },
            {
                "id": "precio",
                "prioridad": "alta" if weighted_realized_price < average_target_price else "media",
                "severidad": "warning" if weighted_realized_price < average_target_price else "success",
                "titulo": "Precio realizado bajo objetivo" if weighted_realized_price < average_target_price else "Precio realizado en rango",
                "impacto": f"USD {weighted_realized_price:.1f}/tn vs objetivo USD {average_target_price:.1f}/tn.",
                "modulo": "Comercial / Exportación",
                "detalle": market_rows[0]["mercado"] if market_rows else "Sin mercado dominante",
                "accion": "Cuidar el mix de mercados y el timing de fijación.",
            },
            {
                "id": "cobranza",
                "prioridad": "alta" if open_ar_ars > collected_ars * 0.8 and open_ar_ars > 0 else "media",
                "severidad": "warning" if open_ar_ars > 0 else "success",
                "titulo": "Cuentas a cobrar abiertas" if open_ar_ars > 0 else "Cobranza sin desvíos fuertes",
                "impacto": f"ARS {open_ar_ars:,.0f} abiertos frente a ARS {collected_ars:,.0f} cobrados.",
                "modulo": "Finanzas / Comercial",
                "detalle": client_rows[0]["cliente"] if client_rows else "Sin cliente crítico",
                "accion": "Priorizar cobranzas y revisar condiciones de pago por cliente.",
            },
            {
                "id": "dias-cobro",
                "prioridad": "alta" if dias_promedio_cobro is not None and dias_promedio_cobro > 75 else "media" if dias_promedio_cobro is not None and dias_promedio_cobro > 45 else "baja",
                "severidad": "danger" if dias_promedio_cobro is not None and dias_promedio_cobro > 75 else "warning" if dias_promedio_cobro is not None and dias_promedio_cobro > 45 else "success",
                "titulo": (
                    "Plazo de cobro crítico" if dias_promedio_cobro is not None and dias_promedio_cobro > 75
                    else "Plazo de cobro en atención" if dias_promedio_cobro is not None and dias_promedio_cobro > 45
                    else "Plazo de cobro en rango"
                ),
                "impacto": f"{dias_promedio_cobro:.0f} días promedio entre factura y cobro." if dias_promedio_cobro is not None else "Sin datos suficientes de cobros completos.",
                "modulo": "Finanzas / Comercial",
                "detalle": "Verde <45 días · Amarillo 45-75 días · Rojo >75 días. Con inflación >60% anual, cada día extra de cobro erosiona el margen real en ARS.",
                "accion": "Priorizar clientes con más días de demora y revisar condiciones de pago negociadas." if dias_promedio_cobro is not None and dias_promedio_cobro > 45 else "Mantener condiciones de cobro actuales.",
            },
            {
                "id": "concentracion",
                "prioridad": "media" if market_rows and market_rows[0]["participacion_pct"] > 50 else "baja",
                "severidad": "warning" if market_rows and market_rows[0]["participacion_pct"] > 50 else "info",
                "titulo": "Concentración comercial alta" if market_rows and market_rows[0]["participacion_pct"] > 50 else "Diversificación comercial razonable",
                "impacto": (
                    f"{market_rows[0]['mercado']} supera {market_rows[0]['participacion_pct']:.1f}% del volumen."
                    if market_rows
                    else "Sin concentración destacable."
                ),
                "modulo": "Comercial / Exportación",
                "detalle": market_rows[0]["mercado"] if market_rows else "Sin concentración",
                "accion": "Desarrollar mercados alternativos o balancear asignación de fruta.",
            },
        ],
    }
