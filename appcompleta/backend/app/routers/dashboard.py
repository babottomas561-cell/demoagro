from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.dashboard_service import get_dashboard_executive
from app.schemas.dashboard import DashboardExecutiveResponse

router = APIRouter()


@router.get(
    "/dashboard/executive",
    response_model=DashboardExecutiveResponse,
    summary="Dashboard ejecutivo consolidado",
    description="Retorna KPIs, flujo de caja, ventas por cultivo, insights y alertas para el panel ejecutivo.",
)
async def dashboard_executive(
    empresa_id: Optional[int] = Query(None, description="ID de empresa"),
    campania_id: Optional[int] = Query(None, description="ID de campaña"),
    cultivo_id: Optional[int] = Query(None, description="ID del cultivo"),
    db: AsyncSession = Depends(get_db),
):
    return await get_dashboard_executive(db, empresa_id, campania_id, cultivo_id)
