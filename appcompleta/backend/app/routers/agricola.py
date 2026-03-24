from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.agricola_service import get_agricola_resumen, get_lotes_list
from app.schemas.agricola import AgricolaResumenResponse, LoteListResponse

router = APIRouter()


@router.get(
    "/agricola/resumen",
    response_model=AgricolaResumenResponse,
    summary="Resumen agricola",
    description="Retorna KPIs agricolas, avance de cultivos, rendimiento historico y plan vs actual.",
)
async def agricola_resumen(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    cultivo_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_agricola_resumen(
        db,
        empresa_id,
        campania_id,
        establecimiento_id,
        cultivo_id,
    )


@router.get(
    "/agricola/lotes",
    response_model=LoteListResponse,
    summary="Listado de lotes paginado",
    description="Retorna la lista paginada de lotes con estado, rendimiento y datos de siembra.",
)
async def agricola_lotes(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    cultivo_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await get_lotes_list(
        db,
        empresa_id,
        campania_id,
        establecimiento_id,
        estado,
        cultivo_id,
        page,
        page_size,
    )
