import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="Verifica el estado del servicio y la conectividad con la base de datos.",
)
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "ok"
    table_count = 0

    try:
        await db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as exc:
        db_status = f"error: {str(exc)}"
        logger.error("Health check DB error: %s", exc)

    if db_status == "ok":
        try:
            result = await db.execute(
                text(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            )
            table_count = result.scalar() or 0
        except Exception as exc:
            logger.warning("Could not count tables: %s", exc)

    return {
        "status": "ok",
        "database": db_status,
        "tables": table_count,
        "version": settings.app_version,
        "app": settings.app_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
