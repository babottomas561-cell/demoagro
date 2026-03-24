from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lemon_dimensions import (
    CampaniaDim,
    CampoDim,
    CanalDim,
    DestinoFrutaDim,
    EstablecimientoDim,
    LineaEmpaqueDim,
    LoteDim,
    MercadoDim,
    VariedadDim,
)
from app.models.lemon_field import LoteCampaniaFact


@dataclass
class LemonFilters:
    empresa_id: Optional[int] = None
    campania_id: Optional[int] = None
    establecimiento_id: Optional[int] = None
    campo_id: Optional[int] = None
    lote_id: Optional[int] = None
    variedad_id: Optional[int] = None
    cliente_id: Optional[int] = None
    mercado_id: Optional[int] = None
    canal_id: Optional[int] = None
    packhouse_id: Optional[int] = None
    linea_id: Optional[int] = None
    turno_id: Optional[int] = None
    destino_id: Optional[int] = None
    calibre_id: Optional[int] = None
    moneda: Optional[str] = None
    periodo: Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None


@dataclass
class CampaignPair:
    current: CampaniaDim
    previous: CampaniaDim | None


def month_key(value: date) -> str:
    return value.strftime("%Y-%m")


def week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def week_key(value: date) -> str:
    return week_start(value).isoformat()


def normalize_period(periodo: Optional[str]) -> str:
    candidate = (periodo or "").upper()
    if candidate in {"7D", "30D", "90D", "YTD", "12M", "ALL"}:
        return candidate
    return "ALL"


def resolve_time_window(
    campaign_start: date,
    campaign_end: date,
    filters: LemonFilters,
) -> tuple[date, date, str]:
    period = normalize_period(filters.periodo)
    natural_window_end = min(campaign_end, date.today())
    requested_end = filters.to_date
    if requested_end is not None and campaign_start <= requested_end <= campaign_end:
        window_end = requested_end
    else:
        window_end = natural_window_end

    window_end = min(max(window_end, campaign_start), campaign_end)

    use_explicit_range = (
        filters.from_date is not None
        and filters.to_date is not None
        and campaign_start <= filters.from_date <= campaign_end
        and campaign_start <= filters.to_date <= campaign_end
        and filters.from_date <= window_end
    )

    window_start = filters.from_date if use_explicit_range else None
    if window_start is None:
        if period == "7D":
            window_start = window_end - timedelta(days=6)
        elif period == "30D":
            window_start = window_end - timedelta(days=29)
        elif period == "90D":
            window_start = window_end - timedelta(days=89)
        elif period == "YTD":
            window_start = date(window_end.year, 1, 1)
        elif period == "12M":
            window_start = window_end - timedelta(days=364)
        else:
            window_start = campaign_start

    window_start = max(min(window_start, window_end), campaign_start)
    return window_start, window_end, period


def resolve_previous_window(
    current_window_start: date,
    current_window_end: date,
    current_campaign: CampaniaDim,
    previous_campaign: CampaniaDim,
) -> tuple[date, date]:
    start_offset = max((current_window_start - current_campaign.fecha_inicio).days, 0)
    duration_days = max((current_window_end - current_window_start).days, 0)
    previous_start = min(
        previous_campaign.fecha_fin,
        previous_campaign.fecha_inicio + timedelta(days=start_offset),
    )
    previous_end = min(previous_campaign.fecha_fin, previous_start + timedelta(days=duration_days))
    return previous_start, previous_end


def recent_window_start(window_start: date, window_end: date, days: int) -> date:
    return max(window_start, window_end - timedelta(days=max(days - 1, 0)))


async def resolve_campaign_pair(
    db: AsyncSession,
    campania_id: Optional[int] = None,
) -> CampaignPair:
    campaigns = (
        await db.execute(select(CampaniaDim).order_by(CampaniaDim.fecha_inicio))
    ).scalars().all()
    if not campaigns:
        raise ValueError("No hay campañas limoneras cargadas")

    current = None
    if campania_id:
        current = next((item for item in campaigns if item.campania_id == campania_id), None)
    if current is None:
        current = next((item for item in campaigns if item.activa), campaigns[-1])

    previous = None
    for index, campaign in enumerate(campaigns):
        if campaign.campania_id == current.campania_id and index > 0:
            previous = campaigns[index - 1]
            break

    return CampaignPair(current=current, previous=previous)


async def load_scope_rows(
    db: AsyncSession,
    filters: LemonFilters,
    campaign_id: int,
):
    query = (
        select(
            LoteCampaniaFact,
            LoteDim,
            CampoDim,
            EstablecimientoDim,
            VariedadDim,
        )
        .join(LoteDim, LoteCampaniaFact.lote_id == LoteDim.lote_id)
        .join(CampoDim, LoteDim.campo_id == CampoDim.campo_id)
        .join(EstablecimientoDim, LoteCampaniaFact.establecimiento_id == EstablecimientoDim.establecimiento_id)
        .join(VariedadDim, LoteCampaniaFact.variedad_id == VariedadDim.variedad_id)
        .where(LoteCampaniaFact.campania_id == campaign_id)
        .order_by(EstablecimientoDim.nombre, CampoDim.nombre, LoteDim.codigo)
    )

    if filters.empresa_id:
        query = query.where(EstablecimientoDim.empresa_id == filters.empresa_id)
    if filters.establecimiento_id:
        query = query.where(EstablecimientoDim.establecimiento_id == filters.establecimiento_id)
    if filters.campo_id:
        query = query.where(CampoDim.campo_id == filters.campo_id)
    if filters.lote_id:
        query = query.where(LoteDim.lote_id == filters.lote_id)
    if filters.variedad_id:
        query = query.where(VariedadDim.variedad_id == filters.variedad_id)

    return (await db.execute(query)).all()


async def load_establishment_surface_map(
    db: AsyncSession,
    campaign_id: int,
) -> dict[int, float]:
    rows = (
        await db.execute(
            select(LoteCampaniaFact, EstablecimientoDim)
            .join(
                EstablecimientoDim,
                LoteCampaniaFact.establecimiento_id == EstablecimientoDim.establecimiento_id,
            )
            .where(LoteCampaniaFact.campania_id == campaign_id)
        )
    ).all()
    totals: dict[int, float] = defaultdict(float)
    for lot_campaign, establecimiento in rows:
        totals[establecimiento.establecimiento_id] += float(lot_campaign.superficie_ha or 0)
    return totals


async def load_channel_maps(db: AsyncSession):
    canales = (await db.execute(select(CanalDim))).scalars().all()
    mercados = (await db.execute(select(MercadoDim))).scalars().all()
    destinos = (await db.execute(select(DestinoFrutaDim))).scalars().all()
    lineas = (await db.execute(select(LineaEmpaqueDim))).scalars().all()
    return {
        "canal_by_code": {item.codigo: item for item in canales},
        "mercado_by_code": {item.codigo: item for item in mercados},
        "destino_by_code": {item.codigo: item for item in destinos},
        "linea_by_id": {item.linea_id: item for item in lineas},
    }


def nearest_week_value(
    lookup: dict[tuple[date, int], float],
    value_date: date,
    entity_id: int,
) -> float:
    probe = week_start(value_date)
    for _ in range(0, 8):
        key = (probe, entity_id)
        if key in lookup:
            return lookup[key]
        probe -= timedelta(days=7)
    candidates = [value for (row_date, row_id), value in lookup.items() if row_id == entity_id and row_date <= value_date]
    return candidates[-1] if candidates else 0.0


def iso_now() -> str:
    return date.today().isoformat()


# ---------------------------------------------------------------------------
# Campaign phase — used in every panel's meta section to provide seasonal
# context. Tucumán lemon calendar drives which KPIs are most critical at
# any given time, so the frontend can surface the right emphasis.
# ---------------------------------------------------------------------------

_FASE_META: dict[str, dict[str, str]] = {
    "arranque": {
        "label": "Arranque de campaña",
        "descripcion": "Cosecha temprana (variedades verdes / Genova). Volúmenes bajos, precio premium potencial. Preparación de packhouse y negociación de contratos forward con Europa.",
        "kpis_criticos": "packout_pct, dias_sin_cobre, contratos_export_cerrados, riego_cobertura",
        "riesgos_tipicos": "Fruta verde con brix bajo, líneas packhouse sin calibrar, falta de contratos forward.",
    },
    "apertura": {
        "label": "Apertura de campaña principal",
        "descripcion": "Arranca la campaña Eureka. Presión operativa máxima: contratación de cuadrillas, calibración de packhouse y cierre de contratos de exportación para Europa.",
        "kpis_criticos": "kg_jornalero, avance_cosecha_pct, eficiencia_packhouse, contratos_cerrados_pct",
        "riesgos_tipicos": "Escasez de cuadrillas, primer rechazo alto por calibración de línea, fruta temprana con acidez alta.",
    },
    "pico": {
        "label": "Pico de cosecha",
        "descripcion": "Máximo volumen. Packhouse a capacidad total. Mercados europeos muy activos. Riesgo de heladas nocturnas que bajan el packout.",
        "kpis_criticos": "kg_jornalero, eficiencia_packhouse, packout_pct, precio_exportacion_usd_tn",
        "riesgos_tipicos": "Heladas nocturnas (daño superficial → industria), cuello de botella en frío, sobreoferta global que baja precios spot.",
    },
    "madurez": {
        "label": "Madurez de campaña",
        "descripcion": "Fruta de calidad óptima (color, brix). Segunda ventana comercial. El psílido Diaphorina citri es más activo → máximo riesgo de transmisión de HLB.",
        "kpis_criticos": "packout_pct, incidencia_hlb_pct, diaphorina_capturas, precio_realizado_vs_objetivo",
        "riesgos_tipicos": "Sobreoferta global junio-julio, HLB activo, fruta tardía que pasa a industria.",
    },
    "cierre": {
        "label": "Cierre de campaña",
        "descripcion": "Fruta tardía. Mayor proporción a industria. Evaluación final de rindes y packout. Presupuesto para la próxima campaña.",
        "kpis_criticos": "rendimiento_final_kg_ha, margen_neto_campania, costo_tn_usd, saldo_cobro_pendiente",
        "riesgos_tipicos": "Precio fruta tardía muy bajo, cobros pendientes de verano, fruta que no clasifica.",
    },
    "receso": {
        "label": "Receso de campaña",
        "descripcion": "Mantenimiento de packhouse, poda y preparación de infraestructura de riego. Monitoreo intensivo de HLB. El granizo veranero puede comprometer la próxima cosecha.",
        "kpis_criticos": "incidencia_hlb_pct, diaphorina_capturas, mantenimiento_packhouse, riego_cobertura",
        "riesgos_tipicos": "Granizo (nov-feb), HLB sin síntomas visibles pero con dispersión activa, frío que afecta floración.",
    },
}


def get_fase_campania(reference_date: date) -> dict[str, str]:
    """Return campaign phase metadata based on the month of reference_date.

    Phases follow the operational story seeded for the demo:
      - arranque: Nov–Dec  (pre-campaña, contratos tempranos, alistamiento)
      - apertura: Jan      (inicio de corte y calibración de proceso)
      - pico:     Feb–Mar  (máximo volumen y presión de packhouse)
      - madurez:  Apr–May  (segunda ventana comercial y calidad estable)
      - cierre:   Jun      (fruta tardía y cierre económico)
      - receso:   Jul–Oct  (intercampaña, mantenimiento y preparación)
    """
    month = reference_date.month
    if month in (11, 12):
        fase = "arranque"
    elif month == 1:
        fase = "apertura"
    elif month in (2, 3):
        fase = "pico"
    elif month in (4, 5):
        fase = "madurez"
    elif month == 6:
        fase = "cierre"
    else:
        fase = "receso"
    return {"fase": fase, **_FASE_META[fase]}
