"""
Schemas Pydantic para el modulo Stock.
"""
from pydantic import BaseModel
from typing import Optional, Any


class SummaryStock(BaseModel):
    stock_total_tn: float
    valor_stock: float
    unidades_alerta: int
    productos_criticos: int
    cobertura_promedio_dias: float
    costo_inventario_insumos: float
    necesidad_compra: float
    stock_inmovilizado: float


class StockItem(BaseModel):
    id: str
    cultivo: str
    establecimiento: str
    stock_disponible_tn: float
    vendido_tn: float
    comprometido_tn: float
    libre_tn: float
    libre_pct: float
    precio_referencia: float
    valor_estimado: float
    alerta: str


class InsumoItem(BaseModel):
    insumo: str
    tipo: str
    unidad: str
    establecimiento: str
    stock_actual: float
    cobertura_dias: float
    cobertura_ha: float
    quiebre_en_dias: Optional[int] = None
    compra_sugerida: float
    stock_inmovilizado: float
    costo_inventario: float
    consumo_plan_mes: float
    consumo_real_mes: float
    desvio_consumo_pct: float
    severidad: str


class StockResumenResponse(BaseModel):
    summary: SummaryStock
    items: list[StockItem]
    insumos: list[InsumoItem]
    consumo_vs_plan: list[Any]
    alerts: list[Any]
    actions: list[Any]
    ultima_actualizacion: str


class MovimientosResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Any]
