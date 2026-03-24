"""
Schemas Pydantic para el modulo Agricola.
"""
from pydantic import BaseModel
from typing import Optional, Any


class SummaryAgricola(BaseModel):
    superficie_total: float
    sembrado: float
    cosechado: float
    rendimiento_promedio: float
    variabilidad_rinde_pct: float
    hectareas_fuera_ventana: float
    lotes_atrasados: int
    desvio_aplicacion_promedio: float


class AvanceCultivo(BaseModel):
    cultivo: str
    sembrado_ha: float
    total_ha: float
    porcentaje: float


class LoteItem(BaseModel):
    id: str
    nombre: str
    establecimiento: str
    cultivo: str
    hectareas: float
    estado: str
    fecha_siembra: Optional[str] = None
    rendimiento_tn_ha: Optional[float] = None
    costo_por_ha: Optional[float] = None


class RendimientoHistorico(BaseModel):
    campania: str
    soja: Optional[float] = None
    maiz: Optional[float] = None
    trigo: Optional[float] = None
    girasol: Optional[float] = None


class PlanVsActualItem(BaseModel):
    labor: str
    plan_ha: float
    real_ha: float
    pendiente_ha: float
    cumplimiento_pct: float


class AgricolaResumenResponse(BaseModel):
    summary: SummaryAgricola
    avance_cultivos: list[AvanceCultivo]
    lotes: list[LoteItem]
    rendimiento_historico: list[RendimientoHistorico]
    plan_vs_actual: list[PlanVsActualItem]
    lotes_atrasados: list[Any]
    pendientes_establecimiento: list[Any]
    productividad: list[Any]
    performance_lotes: list[Any]
    rendimiento_ambientes: list[Any]
    aplicaciones: list[Any]
    nutrientes_lote: list[Any]
    observaciones: list[Any]
    recomendaciones: list[Any]
    alerts: list[Any]
    actions: list[Any]
    ultima_actualizacion: str


class LoteListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[LoteItem]
