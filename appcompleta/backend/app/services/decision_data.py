from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cultivo import Cultivo
from app.models.decision_support import (
    AlertaOperativa,
    AplicacionDetalle,
    ConsumoCombustible,
    CostosIndirectosAsignados,
    DesvioPlanReal,
    DowntimeMaquinaria,
    EjecucionLabor,
    EntregaComercial,
    ObservacionCampo,
    PlanLabor,
    PosicionComercial,
    PresupuestoInsumo,
    PresupuestoLote,
    RecomendacionAgronomica,
    RendimientoAmbiente,
    ServiceSchedule,
    StockProyectado,
    TareaCritica,
)
from app.models.establecimiento import Establecimiento
from app.models.insumo import Insumo
from app.models.lote import Lote
from app.models.maquinaria import Maquinaria


def _filter_lotes(
    query,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    if empresa_id:
        query = query.where(Establecimiento.empresa_id == empresa_id)
    if campania_id:
        query = query.where(Lote.campania_id == campania_id)
    if establecimiento_id:
        query = query.where(Lote.establecimiento_id == establecimiento_id)
    if cultivo_id:
        query = query.where(Lote.cultivo_id == cultivo_id)
    return query


async def load_budget_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    query = (
        select(PresupuestoLote, Lote, Establecimiento, Cultivo)
        .join(Lote, PresupuestoLote.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Cultivo, Lote.cultivo_id == Cultivo.id)
    )
    query = _filter_lotes(query, empresa_id, campania_id, establecimiento_id, cultivo_id)
    return (await db.execute(query)).all()


async def load_plan_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    query = (
        select(PlanLabor, EjecucionLabor, Lote, Establecimiento, Cultivo)
        .join(Lote, PlanLabor.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Cultivo, Lote.cultivo_id == Cultivo.id)
        .outerjoin(EjecucionLabor, EjecucionLabor.plan_labor_id == PlanLabor.id)
    )
    query = _filter_lotes(query, empresa_id, campania_id, establecimiento_id, cultivo_id)
    return (await db.execute(query)).all()


async def load_observation_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    query = (
        select(ObservacionCampo, Lote, Establecimiento, Cultivo)
        .join(Lote, ObservacionCampo.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Cultivo, Lote.cultivo_id == Cultivo.id)
    )
    query = _filter_lotes(query, empresa_id, campania_id, establecimiento_id, cultivo_id)
    return (await db.execute(query)).all()


async def load_recommendation_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    query = (
        select(RecomendacionAgronomica, Lote, Establecimiento, Cultivo)
        .join(Lote, RecomendacionAgronomica.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Cultivo, Lote.cultivo_id == Cultivo.id)
    )
    query = _filter_lotes(query, empresa_id, campania_id, establecimiento_id, cultivo_id)
    return (await db.execute(query)).all()


async def load_application_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    query = (
        select(AplicacionDetalle, Lote, Establecimiento, Cultivo)
        .join(Lote, AplicacionDetalle.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Cultivo, Lote.cultivo_id == Cultivo.id)
    )
    query = _filter_lotes(query, empresa_id, campania_id, establecimiento_id, cultivo_id)
    return (await db.execute(query)).all()


async def load_ambiente_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    query = (
        select(RendimientoAmbiente, Lote, Establecimiento, Cultivo)
        .join(Lote, RendimientoAmbiente.lote_id == Lote.id)
        .join(Establecimiento, Lote.establecimiento_id == Establecimiento.id)
        .join(Cultivo, Lote.cultivo_id == Cultivo.id)
    )
    query = _filter_lotes(query, empresa_id, campania_id, establecimiento_id, cultivo_id)
    return (await db.execute(query)).all()


async def load_stock_projection_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
):
    query = (
        select(StockProyectado, Insumo, Establecimiento)
        .join(Insumo, StockProyectado.insumo_id == Insumo.id)
        .join(Establecimiento, StockProyectado.establecimiento_id == Establecimiento.id)
    )
    if empresa_id:
        query = query.where(Establecimiento.empresa_id == empresa_id)
    if establecimiento_id:
        query = query.where(Establecimiento.id == establecimiento_id)
    return (await db.execute(query)).all()


async def load_presupuesto_insumo_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    campania_id: Optional[int] = None,
):
    query = (
        select(PresupuestoInsumo, Insumo, Establecimiento)
        .join(Insumo, PresupuestoInsumo.insumo_id == Insumo.id)
        .join(Establecimiento, PresupuestoInsumo.establecimiento_id == Establecimiento.id)
    )
    if empresa_id:
        query = query.where(Establecimiento.empresa_id == empresa_id)
    if establecimiento_id:
        query = query.where(Establecimiento.id == establecimiento_id)
    if campania_id:
        query = query.where(PresupuestoInsumo.campania_id == campania_id)
    return (await db.execute(query)).all()


async def load_position_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    cultivo_id: Optional[int] = None,
):
    query = select(PosicionComercial, Cultivo)
    query = query.join(Cultivo, PosicionComercial.cultivo_id == Cultivo.id)
    if empresa_id:
        query = query.where(PosicionComercial.empresa_id == empresa_id)
    if campania_id:
        query = query.where(PosicionComercial.campania_id == campania_id)
    if cultivo_id:
        query = query.where(PosicionComercial.cultivo_id == cultivo_id)
    return (await db.execute(query)).all()


async def load_delivery_rows(db: AsyncSession):
    query = select(EntregaComercial)
    return (await db.execute(query)).scalars().all()


async def load_fleet_support_rows(
    db: AsyncSession,
    empresa_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
):
    maquinas_query = (
        select(Maquinaria, Establecimiento)
        .join(Establecimiento, Maquinaria.establecimiento_id == Establecimiento.id)
    )
    if empresa_id:
        maquinas_query = maquinas_query.where(Establecimiento.empresa_id == empresa_id)
    if establecimiento_id:
        maquinas_query = maquinas_query.where(Establecimiento.id == establecimiento_id)
    maquinas = (await db.execute(maquinas_query)).all()
    maquinaria_ids = [maquina.id for maquina, _ in maquinas]

    downtime = []
    consumos = []
    services = []
    if maquinaria_ids:
        downtime = (
            await db.execute(
                select(DowntimeMaquinaria).where(DowntimeMaquinaria.maquinaria_id.in_(maquinaria_ids))
            )
        ).scalars().all()
        consumos = (
            await db.execute(
                select(ConsumoCombustible).where(ConsumoCombustible.maquinaria_id.in_(maquinaria_ids))
            )
        ).scalars().all()
        services = (
            await db.execute(
                select(ServiceSchedule).where(ServiceSchedule.maquinaria_id.in_(maquinaria_ids))
            )
        ).scalars().all()
    return maquinas, downtime, consumos, services


async def load_costos_indirectos_rows(
    db: AsyncSession,
    lote_ids: Sequence[int],
    campania_id: Optional[int] = None,
):
    if not lote_ids:
        return []
    query = select(CostosIndirectosAsignados).where(CostosIndirectosAsignados.lote_id.in_(lote_ids))
    if campania_id:
        query = query.where(CostosIndirectosAsignados.campania_id == campania_id)
    return (await db.execute(query)).scalars().all()


async def load_desvios_rows(
    db: AsyncSession,
    modulo: Optional[str] = None,
):
    query = select(DesvioPlanReal)
    if modulo:
        query = query.where(DesvioPlanReal.modulo == modulo)
    return (await db.execute(query)).scalars().all()


async def load_alert_rows(
    db: AsyncSession,
    modules: Optional[Sequence[str]] = None,
):
    query = select(AlertaOperativa).order_by(AlertaOperativa.prioridad.asc())
    if modules:
        query = query.where(AlertaOperativa.modulo.in_(modules))
    return (await db.execute(query)).scalars().all()


async def load_task_rows(
    db: AsyncSession,
    modules: Optional[Sequence[str]] = None,
):
    query = select(TareaCritica).order_by(TareaCritica.vence_el.asc())
    if modules:
        query = query.where(TareaCritica.modulo.in_(modules))
    return (await db.execute(query)).scalars().all()
