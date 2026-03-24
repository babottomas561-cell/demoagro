"""
ERP API endpoints - simulación de un ERP agro completo.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.erp_service import (
    get_erp_filters,
    get_siembras,
    get_cosechas_erp,
    get_labores_erp,
    get_contratos_erp,
    get_ventas_erp,
    get_flujo_caja_erp,
    get_lotes_erp,
)

router = APIRouter()


@router.get("/erp/filtros")
async def erp_filtros(
    db: AsyncSession = Depends(get_db),
):
    return await get_erp_filters(db)


@router.get("/erp/siembras")
async def erp_siembras(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    cultivo_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    return await get_siembras(db, campania_id, empresa_id, cultivo_id, page, limit)


@router.get("/erp/cosechas")
async def erp_cosechas(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    return await get_cosechas_erp(db, campania_id, empresa_id, establecimiento_id, page, limit)


@router.get("/erp/labores")
async def erp_labores(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    return await get_labores_erp(db, campania_id, empresa_id, establecimiento_id, tipo, page, limit)


@router.get("/erp/contratos")
async def erp_contratos(
    estado: Optional[str] = Query(None),
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_contratos_erp(db, estado, campania_id, empresa_id, cliente_id)


@router.get("/erp/ventas")
async def erp_ventas(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None),
    desde: Optional[str] = Query(None, description="Fecha desde YYYY-MM-DD"),
    hasta: Optional[str] = Query(None, description="Fecha hasta YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    return await get_ventas_erp(db, campania_id, empresa_id, cliente_id, desde, hasta)


@router.get("/erp/flujo-caja")
async def erp_flujo_caja(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    desde: Optional[str] = Query(None, description="Fecha desde YYYY-MM-DD"),
    hasta: Optional[str] = Query(None, description="Fecha hasta YYYY-MM-DD"),
    categoria: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_flujo_caja_erp(db, empresa_id, campania_id, desde, hasta, categoria)


@router.get("/erp/lotes")
async def erp_lotes(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return await get_lotes_erp(db, campania_id, empresa_id, establecimiento_id, estado)
