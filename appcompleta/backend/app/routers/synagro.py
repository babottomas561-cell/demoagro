"""API Synagro simulada sobre la base ERP local."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.erp_service import (
    get_cosechas_erp,
    get_contratos_erp,
    get_erp_filters,
    get_flujo_caja_erp,
    get_labores_erp,
    get_lotes_erp,
    get_siembras,
    get_ventas_erp,
)

router = APIRouter()


def _wrap(payload: dict) -> dict:
    return {
        **payload,
        "source_system": "Synagro simulado",
        "source_mode": "API sobre base ERP local",
    }


@router.get("/synagro/filtros")
async def synagro_filtros(db: AsyncSession = Depends(get_db)):
    return _wrap(await get_erp_filters(db))


@router.get("/synagro/siembras")
async def synagro_siembras(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    cultivo_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    return _wrap(await get_siembras(db, campania_id, empresa_id, cultivo_id, page, limit))


@router.get("/synagro/lotes")
async def synagro_lotes(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    estado: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return _wrap(await get_lotes_erp(db, campania_id, empresa_id, establecimiento_id, estado))


@router.get("/synagro/cosechas")
async def synagro_cosechas(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    return _wrap(await get_cosechas_erp(db, campania_id, empresa_id, establecimiento_id, page, limit))


@router.get("/synagro/labores")
async def synagro_labores(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    establecimiento_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(200, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    return _wrap(await get_labores_erp(db, campania_id, empresa_id, establecimiento_id, tipo, page, limit))


@router.get("/synagro/contratos")
async def synagro_contratos(
    estado: Optional[str] = Query(None),
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return _wrap(await get_contratos_erp(db, estado, campania_id, empresa_id, cliente_id))


@router.get("/synagro/ventas")
async def synagro_ventas(
    campania_id: Optional[int] = Query(None),
    empresa_id: Optional[int] = Query(None),
    cliente_id: Optional[int] = Query(None),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return _wrap(await get_ventas_erp(db, campania_id, empresa_id, cliente_id, desde, hasta))


@router.get("/synagro/flujo-caja")
async def synagro_flujo_caja(
    empresa_id: Optional[int] = Query(None),
    campania_id: Optional[int] = Query(None),
    desde: Optional[str] = Query(None),
    hasta: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return _wrap(await get_flujo_caja_erp(db, empresa_id, campania_id, desde, hasta, categoria))
