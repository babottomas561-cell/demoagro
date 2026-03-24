from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.stock_service import get_stock_resumen, get_movimientos
from app.schemas.stock import StockResumenResponse, MovimientosResponse

router = APIRouter()


@router.get(
    "/stock/resumen",
    response_model=StockResumenResponse,
    summary="Resumen de stock",
    description="Retorna el inventario de granos e insumos con cobertura y alertas.",
)
async def stock_resumen(
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    cultivo_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_stock_resumen(db, empresa_id, establecimiento_id, cultivo_id)


@router.get(
    "/stock/movimientos",
    response_model=MovimientosResponse,
    summary="Movimientos de insumos paginados",
    description="Retorna el historico paginado de ingresos y egresos de insumos.",
)
async def stock_movimientos(
    empresa_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None, description="ingreso o egreso"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_movimientos(db, empresa_id, tipo, page, page_size)
