"""
Schemas Pydantic para el modulo Maquinaria.
"""
from pydantic import BaseModel
from typing import Optional, Any


class SummaryMaquinaria(BaseModel):
    equipos_operativos: int
    horas_promedio: float
    costo_operativo: float
    proximos_services: int
    utilizacion_promedio_pct: float
    downtime_horas: float
    combustible_promedio_ha: float
    equipos_cuello_botella: int
    impacto_operativo_ha: float


class MaquinaItem(BaseModel):
    id: str
    nombre: str
    tipo: str
    marca: str
    modelo: str
    anio: int
    estado: str
    horas_totales: float
    horas_ultimo_service: float
    proximo_service_horas: Optional[float] = None
    dias_para_service: Optional[int] = None
    costo_operativo_mes: float
    alerta_service: str
    establecimiento: str
    horas_productivas: Optional[float] = None
    horas_improductivas: Optional[float] = None
    utilizacion_pct: Optional[float] = None
    combustible_ha: Optional[float] = None
    costo_por_hora: Optional[float] = None
    impacto_operativo_ha: Optional[float] = None
    service_proximo: Optional[str] = None
    riesgo_si_falla: Optional[str] = None
    es_cuello_botella: Optional[bool] = None


class MaquinariaResumenResponse(BaseModel):
    summary: SummaryMaquinaria
    maquinas: list[MaquinaItem]
    series: list[Any]
    bottlenecks: list[Any]
    service_schedule: list[Any]
    alerts: list[Any]
    actions: list[Any]
    ultima_actualizacion: str


class EquiposResponse(BaseModel):
    total: int
    items: list[MaquinaItem]
