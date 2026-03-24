from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.lemon_panel_utils import LemonFilters
from app.services.lemon_sanidad_service import get_sanidad_monitoreo
from app.services.panel_realtime import cached_panel

router = APIRouter()


@router.get("/sanidad/monitoreo")
async def sanidad_monitoreo(
    empresa_id: Optional[int] = None,
    campania_id: Optional[int] = None,
    establecimiento_id: Optional[int] = None,
    campo_id: Optional[int] = None,
    lote_id: Optional[int] = None,
    variedad_id: Optional[int] = None,
    periodo: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    from_alias: Optional[date] = Query(None, alias="from"),
    to_alias: Optional[date] = Query(None, alias="to"),
    db: AsyncSession = Depends(get_db),
):
    filters = LemonFilters(
        empresa_id=empresa_id,
        campania_id=campania_id,
        establecimiento_id=establecimiento_id,
        campo_id=campo_id,
        lote_id=lote_id,
        variedad_id=variedad_id,
        periodo=periodo,
        from_date=from_date or from_alias,
        to_date=to_date or to_alias,
    )
    return await cached_panel("sanidad", filters, lambda: get_sanidad_monitoreo(db, filters))
