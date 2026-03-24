"""
Schemas Pydantic para el modulo Comercial.
"""
from pydantic import BaseModel
from typing import Optional, Any


class SummaryComercial(BaseModel):
    volumen_vendido: float
    precio_promedio: float
    valor_total: float
    contratos_cerrados: int
    toneladas_producidas: float
    toneladas_comprometidas: float
    toneladas_fijadas: float
    toneladas_entregadas: float
    posicion_abierta_tn: float
    cobertura_promedio_pct: float
    desvio_precio_vs_referencia_pct: float


class OperacionItem(BaseModel):
    id: str
    fecha: Optional[str] = None
    cultivo: str
    cliente: str
    volumen_tn: float
    precio_ars_tn: float
    valor_total_ars: float
    estado: str
    tipo_contrato: str


class VentaClienteItem(BaseModel):
    cliente: str
    valor: float
    volumen: float


class PosicionItem(BaseModel):
    cultivo: str
    toneladas_producidas: float
    toneladas_comprometidas: float
    toneladas_fijadas: float
    toneladas_entregadas: float
    stock_fisico: float
    abierta_tn: float
    pendiente_entrega_tn: float
    cobertura_pct: float
    compromiso_pct: float
    desvio_stock_cobertura_tn: float
    precio_referencia: float
    recomendacion: str
    severidad: str


class ComercialResumenResponse(BaseModel):
    summary: SummaryComercial
    precios_historicos: list[Any]
    ventas_cliente: list[VentaClienteItem]
    operaciones: list[OperacionItem]
    posiciones: list[PosicionItem]
    entregas: list[Any]
    proximos_vencer: list[Any]
    alerts: list[Any]
    actions: list[Any]
    ultima_actualizacion: str


class OperacionesPageResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[Any]
