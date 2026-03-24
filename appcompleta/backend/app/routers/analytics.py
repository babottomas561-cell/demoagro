"""
Analytics API endpoints - proyecciones, desvíos, anomalías, sensibilidad.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.analytics_service import (
    get_proyecciones,
    get_desvios,
    get_anomalias,
    get_sensibilidad,
)

router = APIRouter()


@router.get("/analytics/proyecciones")
async def analytics_proyecciones(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_proyecciones(db, empresa_id, campania_id)


@router.get("/analytics/desvios")
async def analytics_desvios(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_desvios(db, empresa_id, campania_id)


@router.get("/analytics/anomalias")
async def analytics_anomalias(
    empresa_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_anomalias(db, empresa_id)


@router.get("/analytics/sensibilidad")
async def analytics_sensibilidad(
    cultivo: str = Query("Soja", description="Nombre del cultivo"),
    precio_base: float = Query(270.0, description="Precio base USD/tn"),
    costo_base: float = Query(580.0, description="Costo base USD/ha"),
    db: AsyncSession = Depends(get_db),
):
    return await get_sensibilidad(db, cultivo, precio_base, costo_base)
