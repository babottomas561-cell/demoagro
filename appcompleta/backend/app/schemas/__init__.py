"""
Schemas Pydantic para DemoAgro API.
"""
from app.schemas.dashboard import (
    KpisDashboard,
    IngresoEgreso,
    VentaCultivo,
    InsightItem,
    SummaryDashboard,
    LoteProfitability,
    ResultBridgeItem,
    SemaforoItem,
    AlertItem,
    ActionItem,
    DashboardExecutiveResponse,
)
from app.schemas.agricola import (
    SummaryAgricola,
    AvanceCultivo,
    LoteItem,
    RendimientoHistorico,
    PlanVsActualItem,
    AgricolaResumenResponse,
    LoteListResponse,
)
from app.schemas.comercial import (
    SummaryComercial,
    OperacionItem,
    VentaClienteItem,
    PosicionItem,
    ComercialResumenResponse,
    OperacionesPageResponse,
)
from app.schemas.finanzas import (
    SummaryFinanzas,
    FlujoMensualItem,
    CostBreakdownItem,
    FinanzasResumenResponse,
    FlujoSerieResponse,
)
from app.schemas.stock import (
    SummaryStock,
    StockItem,
    InsumoItem,
    StockResumenResponse,
    MovimientosResponse,
)
from app.schemas.maquinaria import (
    SummaryMaquinaria,
    MaquinaItem,
    MaquinariaResumenResponse,
    EquiposResponse,
)

__all__ = [
    # dashboard
    "KpisDashboard",
    "IngresoEgreso",
    "VentaCultivo",
    "InsightItem",
    "SummaryDashboard",
    "LoteProfitability",
    "ResultBridgeItem",
    "SemaforoItem",
    "AlertItem",
    "ActionItem",
    "DashboardExecutiveResponse",
    # agricola
    "SummaryAgricola",
    "AvanceCultivo",
    "LoteItem",
    "RendimientoHistorico",
    "PlanVsActualItem",
    "AgricolaResumenResponse",
    "LoteListResponse",
    # comercial
    "SummaryComercial",
    "OperacionItem",
    "VentaClienteItem",
    "PosicionItem",
    "ComercialResumenResponse",
    "OperacionesPageResponse",
    # finanzas
    "SummaryFinanzas",
    "FlujoMensualItem",
    "CostBreakdownItem",
    "FinanzasResumenResponse",
    "FlujoSerieResponse",
    # stock
    "SummaryStock",
    "StockItem",
    "InsumoItem",
    "StockResumenResponse",
    "MovimientosResponse",
    # maquinaria
    "SummaryMaquinaria",
    "MaquinaItem",
    "MaquinariaResumenResponse",
    "EquiposResponse",
]
