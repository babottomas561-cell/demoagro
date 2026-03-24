"""
Schemas Pydantic para el modulo Finanzas.
"""
from pydantic import BaseModel
from typing import Optional, Any


class SummaryFinanzas(BaseModel):
    capital_de_trabajo: float
    deuda_por_vencer: float
    cuentas_a_cobrar: float
    flujo_neto: float
    margen_bruto_total: float
    margen_por_ha: float
    desvio_presupuesto_pct: float
    costo_por_ha: float
    costo_por_tonelada: float
    capital_trabajo_comprometido: float
    deuda_corto_plazo: float
    riesgo_caja: str
    ingresos_operativos: float


class FlujoMensualItem(BaseModel):
    mes: str
    ingresos: float
    egresos: float
    neto: float
    proyectado: Optional[bool] = None


class CostBreakdownItem(BaseModel):
    label: str
    value: float
    kind: str


class FinanzasResumenResponse(BaseModel):
    summary: SummaryFinanzas
    flujo_mensual: list[FlujoMensualItem]
    flujo_categorias: list[Any]
    cash_projection: list[Any]
    cost_breakdown: list[CostBreakdownItem]
    resultados_lote: list[Any]
    rentabilidad_cultivo: list[Any]
    rentabilidad_establecimiento: list[Any]
    sensitivity: list[Any]
    alerts: list[Any]
    actions: list[Any]
    ultima_actualizacion: str


class FlujoSerieResponse(BaseModel):
    items: list[FlujoMensualItem]
    ultima_actualizacion: str
