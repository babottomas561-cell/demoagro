from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.comercial_service import get_comercial_resumen, get_operaciones
from app.schemas.comercial import ComercialResumenResponse, OperacionesPageResponse

router = APIRouter()


@router.get(
    "/comercial/resumen",
    response_model=ComercialResumenResponse,
    summary="Resumen comercial",
    description="Retorna posicion comercial, ventas, contratos y cobertura de la campaña.",
)
async def comercial_resumen(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    cultivo_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_comercial_resumen(db, empresa_id, campania_id, cultivo_id)


@router.get(
    "/comercial/operaciones",
    response_model=OperacionesPageResponse,
    summary="Operaciones comerciales paginadas",
    description="Retorna el listado paginado de ventas y contratos comerciales.",
)
async def comercial_operaciones(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    cultivo_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_operaciones(db, empresa_id, campania_id, cultivo_id, page, page_size)
