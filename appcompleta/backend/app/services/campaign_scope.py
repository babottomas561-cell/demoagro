from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.campania import Campania


async def resolve_campaign_id(
    db: AsyncSession,
    campania_id: Optional[int] = None,
) -> Optional[int]:
    if campania_id:
        return campania_id

    active_query = (
        select(Campania.id)
        .where(Campania.activa.is_(True))
        .order_by(Campania.fecha_inicio.desc())
    )
    active_campaign_id = (await db.execute(active_query)).scalars().first()
    if active_campaign_id:
        return active_campaign_id

    latest_query = select(Campania.id).order_by(Campania.fecha_inicio.desc())
    return (await db.execute(latest_query)).scalars().first()


async def resolve_previous_campaign_id(
    db: AsyncSession,
    current_campaign_id: Optional[int],
) -> Optional[int]:
    if not current_campaign_id:
        return None

    current_campaign = (
        await db.execute(select(Campania).where(Campania.id == current_campaign_id))
    ).scalar_one_or_none()
    if current_campaign is None:
        return None

    previous_query = (
        select(Campania.id)
        .where(Campania.fecha_inicio < current_campaign.fecha_inicio)
        .order_by(Campania.fecha_inicio.desc())
    )
    return (await db.execute(previous_query)).scalars().first()
