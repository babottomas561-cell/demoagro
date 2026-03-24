from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_commercial import (
    CobranzasFact,
    ContratoVentaFact,
    CostosDirectosFact,
    CostosIndirectosFact,
    CuentasCobrarFact,
    EmbarqueFact,
    LiquidacionFact,
    PrecioVentaFact,
    PresupuestoLoteFact,
    StockFinalFact,
)
from app.models.lemon_dimensions import (
    CampaniaDim,
    ClienteDim,
    EmpresaDim,
    EstablecimientoDim,
    FechaDim,
    LineaEmpaqueDim,
    LoteDim,
    VariedadDim,
)
from app.models.lemon_external import (
    ClimaDiarioFact,
    CostoEnergiaFact,
    CostoFleteFact,
    MacroSeriesFact,
    PrecioExportacionFact,
    TipoCambioFact,
)
from app.models.lemon_field import (
    AplicacionFitosanitariaFact,
    CosechaFact,
    FertirriegoFact,
    LoteCampaniaFact,
    RequerimientoHidricoFact,
    RendimientoLoteFact,
    RiegoFact,
    ScoutingFact,
)
from app.models.lemon_packhouse import (
    ConsumoPackhouseFact,
    DowntimePackhouseFact,
    MantenimientoPackhouseFact,
    ManoObraPackhouseFact,
    PackhouseTurnoFact,
)
from app.models.lemon_quality import (
    ClasificacionCalidadFact,
    PackoutFact,
    RecepcionFrutaFact,
    RechazoFact,
)
from app.seed.seed_limon import CURRENT_DATE, PACKHOUSE_INCIDENT_END, PACKHOUSE_INCIDENT_START, QUALITY_ALERT_END, QUALITY_ALERT_START


async def _count(db: AsyncSession, model) -> int:
    return int(await db.scalar(select(func.count()).select_from(model)) or 0)


async def _range(db: AsyncSession, model, field) -> dict[str, str | None]:
    minimum = await db.scalar(select(func.min(field)).select_from(model))
    maximum = await db.scalar(select(func.max(field)).select_from(model))
    return {
        "min": minimum.isoformat() if minimum else None,
        "max": maximum.isoformat() if maximum else None,
    }


async def audit_limon_seed(db: AsyncSession) -> dict:
    active_campaign = await db.scalar(select(CampaniaDim).where(CampaniaDim.activa.is_(True)))
    active_campaign_id = active_campaign.campania_id if active_campaign else None

    harvested = float(await db.scalar(select(func.coalesce(func.sum(CosechaFact.kg_cosechados), 0.0))) or 0)
    received = float(await db.scalar(select(func.coalesce(func.sum(RecepcionFrutaFact.kg_recibidos), 0.0))) or 0)
    classified = float(await db.scalar(select(func.coalesce(func.sum(ClasificacionCalidadFact.kg_clasificados), 0.0))) or 0)
    packed = float(await db.scalar(select(func.coalesce(func.sum(PackoutFact.kg_salida), 0.0))) or 0)
    rejected = float(await db.scalar(select(func.coalesce(func.sum(RechazoFact.kg_rechazo), 0.0))) or 0)
    shipped = float(await db.scalar(select(func.coalesce(func.sum(EmbarqueFact.kg_embarcados), 0.0))) or 0)
    liquidated_ars = float(await db.scalar(select(func.coalesce(func.sum(LiquidacionFact.importe_neto_ars), 0.0))) or 0)
    collected_ars = float(await db.scalar(select(func.coalesce(func.sum(CobranzasFact.monto_cobrado_ars), 0.0))) or 0)
    open_ar = float(await db.scalar(select(func.coalesce(func.sum(CuentasCobrarFact.saldo_abierto_ars), 0.0))) or 0)

    active_metrics = {
        "lotes_campania": int(
            await db.scalar(select(func.count()).select_from(LoteCampaniaFact).where(LoteCampaniaFact.campania_id == active_campaign_id))
            or 0
        ),
        "cosecha_rows": int(
            await db.scalar(
                select(func.count())
                .select_from(CosechaFact)
                .join(LoteCampaniaFact, CosechaFact.lote_campania_id == LoteCampaniaFact.lote_campania_id)
                .where(LoteCampaniaFact.campania_id == active_campaign_id)
            )
            or 0
        ),
        "recepcion_rows": int(
            await db.scalar(
                select(func.count())
                .select_from(RecepcionFrutaFact)
                .join(LoteCampaniaFact, RecepcionFrutaFact.lote_campania_id == LoteCampaniaFact.lote_campania_id)
                .where(LoteCampaniaFact.campania_id == active_campaign_id)
            )
            or 0
        ),
        "packhouse_rows": int(
            await db.scalar(
                select(func.count())
                .select_from(PackhouseTurnoFact)
                .where(PackhouseTurnoFact.fecha <= date(2026, 3, 22))
                .where(PackhouseTurnoFact.fecha >= date(2026, 3, 1))
            )
            or 0
        ),
        "contratos": int(
            await db.scalar(
                select(func.count()).select_from(ContratoVentaFact).where(ContratoVentaFact.campania_id == active_campaign_id)
            )
            or 0
        ),
        "embarques": int(
            await db.scalar(
                select(func.count())
                .select_from(EmbarqueFact)
                .join(ContratoVentaFact, EmbarqueFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
                .where(ContratoVentaFact.campania_id == active_campaign_id)
            )
            or 0
        ),
        "cobranzas": int(
            await db.scalar(
                select(func.count())
                .select_from(CobranzasFact)
                .join(CuentasCobrarFact, CobranzasFact.cuenta_cobrar_id == CuentasCobrarFact.cuenta_cobrar_id)
                .join(ContratoVentaFact, CuentasCobrarFact.contrato_venta_id == ContratoVentaFact.contrato_venta_id)
                .where(ContratoVentaFact.campania_id == active_campaign_id)
            )
            or 0
        ),
    }

    weekly_price_points = int(await db.scalar(select(func.count()).select_from(PrecioVentaFact)) or 0)
    climate_daily_points = int(await db.scalar(select(func.count()).select_from(ClimaDiarioFact)) or 0)
    stock_daily_points = int(await db.scalar(select(func.count()).select_from(StockFinalFact)) or 0)

    all_limon = bool(
        await db.scalar(
            select(func.count())
            .select_from(VariedadDim)
            .where(func.lower(VariedadDim.grupo) != "limon")
        )
        == 0
    )

    baseline_packout = float(
        await db.scalar(
            select(func.avg(PackoutFact.packout_pct))
            .select_from(PackoutFact)
            .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .join(LoteCampaniaFact, RecepcionFrutaFact.lote_campania_id == LoteCampaniaFact.lote_campania_id)
            .where(LoteCampaniaFact.campania_id == active_campaign_id)
            .where(PackoutFact.fecha_proceso >= QUALITY_ALERT_START - date.resolution * 7)
            .where(PackoutFact.fecha_proceso < QUALITY_ALERT_START)
        )
        or 0.0
    )
    alert_packout = float(
        await db.scalar(
            select(func.avg(PackoutFact.packout_pct))
            .select_from(PackoutFact)
            .join(RecepcionFrutaFact, PackoutFact.recepcion_id == RecepcionFrutaFact.recepcion_id)
            .join(LoteCampaniaFact, RecepcionFrutaFact.lote_campania_id == LoteCampaniaFact.lote_campania_id)
            .where(LoteCampaniaFact.campania_id == active_campaign_id)
            .where(PackoutFact.fecha_proceso >= QUALITY_ALERT_START)
            .where(PackoutFact.fecha_proceso <= QUALITY_ALERT_END)
        )
        or 0.0
    )
    ec_l2_downtime = float(
        await db.scalar(
            select(func.coalesce(func.sum(DowntimePackhouseFact.minutos), 0.0))
            .select_from(DowntimePackhouseFact)
            .join(LineaEmpaqueDim, DowntimePackhouseFact.linea_id == LineaEmpaqueDim.linea_id)
            .where(LineaEmpaqueDim.codigo == "EC-L2")
            .where(DowntimePackhouseFact.fecha >= PACKHOUSE_INCIDENT_START)
            .where(DowntimePackhouseFact.fecha <= PACKHOUSE_INCIDENT_END)
        )
        or 0.0
    )
    ec_l1_downtime = float(
        await db.scalar(
            select(func.coalesce(func.sum(DowntimePackhouseFact.minutos), 0.0))
            .select_from(DowntimePackhouseFact)
            .join(LineaEmpaqueDim, DowntimePackhouseFact.linea_id == LineaEmpaqueDim.linea_id)
            .where(LineaEmpaqueDim.codigo == "EC-L1")
            .where(DowntimePackhouseFact.fecha >= PACKHOUSE_INCIDENT_START)
            .where(DowntimePackhouseFact.fecha <= PACKHOUSE_INCIDENT_END)
        )
        or 0.0
    )
    late_client_open_ars = float(
        await db.scalar(
            select(func.coalesce(func.sum(CuentasCobrarFact.saldo_abierto_ars), 0.0))
            .select_from(CuentasCobrarFact)
            .join(ClienteDim, CuentasCobrarFact.cliente_id == ClienteDim.cliente_id)
            .where(ClienteDim.codigo == "AR_MAYOR")
        )
        or 0.0
    )
    late_client_overdue_docs = int(
        await db.scalar(
            select(func.count())
            .select_from(CuentasCobrarFact)
            .join(ClienteDim, CuentasCobrarFact.cliente_id == ClienteDim.cliente_id)
            .where(ClienteDim.codigo == "AR_MAYOR")
            .where(CuentasCobrarFact.saldo_abierto_ars > 0)
            .where(CuentasCobrarFact.fecha_vencimiento < CURRENT_DATE)
        )
        or 0
    )
    low_yield_lots = int(
        await db.scalar(
            select(func.count())
            .select_from(RendimientoLoteFact)
            .join(LoteCampaniaFact, RendimientoLoteFact.lote_campania_id == LoteCampaniaFact.lote_campania_id)
            .where(LoteCampaniaFact.campania_id == active_campaign_id)
            .where(RendimientoLoteFact.desvio_vs_objetivo_pct < -8)
        )
        or 0
    )
    non_usd_contracts = int(
        await db.scalar(
            select(func.count())
            .select_from(ContratoVentaFact)
            .where(ContratoVentaFact.moneda != "USD")
        )
        or 0
    )

    return {
        "tables": {
            "empresa_dim": await _count(db, EmpresaDim),
            "campania_dim": await _count(db, CampaniaDim),
            "establecimiento_dim": await _count(db, EstablecimientoDim),
            "lote_dim": await _count(db, LoteDim),
            "variedad_dim": await _count(db, VariedadDim),
            "fecha_dim": await _count(db, FechaDim),
            "lote_campania_fact": await _count(db, LoteCampaniaFact),
            "cosecha_fact": await _count(db, CosechaFact),
            "recepcion_fruta_fact": await _count(db, RecepcionFrutaFact),
            "clasificacion_calidad_fact": await _count(db, ClasificacionCalidadFact),
            "packout_fact": await _count(db, PackoutFact),
            "rechazo_fact": await _count(db, RechazoFact),
            "packhouse_turno_fact": await _count(db, PackhouseTurnoFact),
            "downtime_packhouse_fact": await _count(db, DowntimePackhouseFact),
            "scouting_fact": await _count(db, ScoutingFact),
            "aplicacion_fitosanitaria_fact": await _count(db, AplicacionFitosanitariaFact),
            "riego_fact": await _count(db, RiegoFact),
            "fertirriego_fact": await _count(db, FertirriegoFact),
            "requerimiento_hidrico_fact": await _count(db, RequerimientoHidricoFact),
            "contrato_venta_fact": await _count(db, ContratoVentaFact),
            "embarque_fact": await _count(db, EmbarqueFact),
            "precio_venta_fact": await _count(db, PrecioVentaFact),
            "liquidacion_fact": await _count(db, LiquidacionFact),
            "cuentas_cobrar_fact": await _count(db, CuentasCobrarFact),
            "cobranzas_fact": await _count(db, CobranzasFact),
            "costos_directos_fact": await _count(db, CostosDirectosFact),
            "costos_indirectos_fact": await _count(db, CostosIndirectosFact),
            "stock_final_fact": await _count(db, StockFinalFact),
            "clima_diario_fact": await _count(db, ClimaDiarioFact),
            "macro_series_fact": await _count(db, MacroSeriesFact),
            "tipo_cambio_fact": await _count(db, TipoCambioFact),
            "precio_exportacion_fact": await _count(db, PrecioExportacionFact),
            "costo_energia_fact": await _count(db, CostoEnergiaFact),
            "costo_flete_fact": await _count(db, CostoFleteFact),
            "rendimiento_lote_fact": await _count(db, RendimientoLoteFact),
            "presupuesto_lote_fact": await _count(db, PresupuestoLoteFact),
            "mano_obra_packhouse_fact": await _count(db, ManoObraPackhouseFact),
            "consumo_packhouse_fact": await _count(db, ConsumoPackhouseFact),
            "mantenimiento_packhouse_fact": await _count(db, MantenimientoPackhouseFact),
        },
        "periods": {
            "cosecha_fact": await _range(db, CosechaFact, CosechaFact.fecha_cosecha),
            "recepcion_fruta_fact": await _range(db, RecepcionFrutaFact, RecepcionFrutaFact.fecha_recepcion),
            "packhouse_turno_fact": await _range(db, PackhouseTurnoFact, PackhouseTurnoFact.fecha),
            "embarque_fact": await _range(db, EmbarqueFact, EmbarqueFact.fecha_embarque),
            "cobranzas_fact": await _range(db, CobranzasFact, CobranzasFact.fecha_cobranza),
            "riego_fact": await _range(db, RiegoFact, RiegoFact.fecha_riego),
            "clima_diario_fact": await _range(db, ClimaDiarioFact, ClimaDiarioFact.fecha),
            "precio_venta_fact": await _range(db, PrecioVentaFact, PrecioVentaFact.fecha),
            "tipo_cambio_fact": await _range(db, TipoCambioFact, TipoCambioFact.fecha),
        },
        "series_quality": {
            "weekly_price_points": weekly_price_points,
            "climate_daily_points": climate_daily_points,
            "stock_daily_points": stock_daily_points,
        },
        "closures": {
            "harvest_to_reception_ratio": round(received / harvested, 4) if harvested else 0,
            "reception_to_classification_ratio": round(classified / received, 4) if received else 0,
            "classification_to_packout_plus_rejection_ratio": round((packed + rejected) / classified, 4) if classified else 0,
            "liquidated_vs_collected_ratio": round(collected_ars / liquidated_ars, 4) if liquidated_ars else 0,
            "open_accounts_receivable_ars": round(open_ar, 2),
            "total_shipped_kg": round(shipped, 2),
        },
        "active_campaign": {
            "campania": active_campaign.nombre if active_campaign else None,
            **active_metrics,
        },
        "problem_signals": {
            "packout_avg_prev_week_pct": round(baseline_packout, 2),
            "packout_avg_alert_window_pct": round(alert_packout, 2),
            "packout_drop_pct_points": round(alert_packout - baseline_packout, 2),
            "ec_l2_downtime_min_incident": round(ec_l2_downtime, 2),
            "ec_l1_downtime_min_incident": round(ec_l1_downtime, 2),
            "ar_mayor_open_ars": round(late_client_open_ars, 2),
            "ar_mayor_overdue_docs": late_client_overdue_docs,
            "active_campaign_low_yield_lots": low_yield_lots,
        },
        "quality_flags": {
            "all_varieties_are_limon": all_limon,
            "non_usd_contracts": non_usd_contracts,
        },
    }
