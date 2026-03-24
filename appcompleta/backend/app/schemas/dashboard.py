"""
Schemas Pydantic para el modulo Dashboard.
"""
from pydantic import BaseModel
from typing import Optional, Any


class KpisDashboard(BaseModel):
    ventas_totales: float
    margen_bruto_pct: float
    rendimiento_promedio: float
    stock_valorizado: float
    ebitda_estimado: float
    flujo_neto_mensual: float
    costos_operativos: float
    variacion_campania_anterior: float


class IngresoEgreso(BaseModel):
    mes: str
    ingresos: float
    egresos: float


class VentaCultivo(BaseModel):
    cultivo: str
    valor: float
    volumen: float


class InsightItem(BaseModel):
    id: str
    titulo: str
    descripcion: str
    severidad: str
    modulo: str
    timestamp: str


class SummaryDashboard(BaseModel):
    margen_bruto_total: float
    margen_por_ha: float
    desvio_presupuesto_pct: float
    hectareas_fuera_ventana: float
    toneladas_sin_fijar: float
    toneladas_producidas: float
    toneladas_fijadas: float
    stock_critico: int
    maquinas_criticas: int


class LoteProfitability(BaseModel):
    lote: str
    establecimiento: str
    cultivo: str
    margen_ha: float
    margen_total: float
    desvio_pct: float
    contribucion_pct: float


class ResultBridgeItem(BaseModel):
    label: str
    value: float
    kind: str


class SemaforoItem(BaseModel):
    label: str
    status: str
    detail: str


class AlertItem(BaseModel):
    id: str
    titulo: str
    descripcion: str
    severidad: str
    modulo: str
    accion: Optional[str] = None
    prioridad: Optional[int] = None


class ActionItem(BaseModel):
    id: str
    titulo: str
    descripcion: str
    owner: str
    impacto: str
    due: str
    severity: str


class DashboardExecutiveResponse(BaseModel):
    kpis: KpisDashboard
    ingresos_egresos: list[IngresoEgreso]
    ventas_cultivo: list[VentaCultivo]
    insights: list[InsightItem]
    summary: SummaryDashboard
    lot_profitability: list[LoteProfitability]
    top_lotes: list[LoteProfitability]
    bottom_lotes: list[LoteProfitability]
    result_bridge: list[ResultBridgeItem]
    semaforos: list[SemaforoItem]
    alerts: list[AlertItem]
    actions: list[Any]
    ultima_actualizacion: str
