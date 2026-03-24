from pydantic import BaseModel
from typing import List, Optional
from datetime import date


class PrecioGrano(BaseModel):
    cultivo: str
    precio_mat: float       # precio MAT (Matba-Rofex) USD/tn
    precio_disponible: float  # precio disponible USD/tn
    precio_ars: float       # precio ARS/tn al cambio oficial
    variacion_dia: float    # variacion % dia
    variacion_semana: float


class TipoCambio(BaseModel):
    oficial: float
    blue: float
    mep: float
    ccl: float
    soja: float  # dolar soja si aplica
    fecha: date


class IndicadorMacro(BaseModel):
    nombre: str
    valor: float
    variacion: float
    unidad: str
    fecha: date


class MacroResponse(BaseModel):
    tipo_cambio: TipoCambio
    precios_granos: List[PrecioGrano]
    indicadores: List[IndicadorMacro]
    clima_pampa: dict
