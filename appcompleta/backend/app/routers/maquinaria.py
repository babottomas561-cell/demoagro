from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.maquinaria_service import get_maquinaria_resumen, get_equipos_list
from app.schemas.maquinaria import MaquinariaResumenResponse, EquiposResponse

router = APIRouter()


@router.get(
    "/maquinaria/resumen",
    response_model=MaquinariaResumenResponse,
    summary="Resumen de maquinaria",
    description="Retorna estado de flota, servicios proximos, cuellos de botella y series de disponibilidad.",
)
async def maquinaria_resumen(
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_maquinaria_resumen(db, empresa_id, establecimiento_id)


@router.get(
    "/maquinaria/equipos",
    response_model=EquiposResponse,
    summary="Listado de equipos",
    description="Retorna la lista de equipos con su estado operativo y alertas de service.",
)
async def maquinaria_equipos(
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_equipos_list(db, empresa_id, estado, establecimiento_id)
