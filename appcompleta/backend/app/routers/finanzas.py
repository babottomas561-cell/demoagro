from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.finanzas_service import get_finanzas_resumen, get_flujo_serie
from app.schemas.finanzas import FinanzasResumenResponse, FlujoSerieResponse

router = APIRouter()


@router.get(
    "/finanzas/resumen",
    response_model=FinanzasResumenResponse,
    summary="Resumen financiero",
    description="Retorna KPIs financieros, flujo mensual, rentabilidad por cultivo y establecimiento.",
)
async def finanzas_resumen(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_finanzas_resumen(db, empresa_id, campania_id)


@router.get(
    "/finanzas/flujo",
    response_model=FlujoSerieResponse,
    summary="Serie de flujo de caja mensual",
    description="Retorna la serie mensual de ingresos y egresos con proyeccion a 3 meses.",
)
async def finanzas_flujo(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_flujo_serie(db, empresa_id, campania_id)
