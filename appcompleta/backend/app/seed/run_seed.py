import logging
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.empresa import Empresa
from app.models.erp_catalog import Moneda
from app.models.lemon_dimensions import EmpresaDim

logger = logging.getLogger(__name__)


async def run_all_seeds():
    async with AsyncSessionLocal() as db:
        from app.seed.seed_limon import seed_limon_data
        from app.seed.seed_synagro_erp import sync_synagro_erp

        lemon_seeded = (await db.execute(select(EmpresaDim).limit(1))).scalar_one_or_none()
        generic_seeded = (await db.execute(select(Empresa).limit(1))).scalar_one_or_none()
        erp_seeded = (await db.execute(select(Moneda).limit(1))).scalar_one_or_none()

        if not lemon_seeded:
            logger.info("Seeding Lemon BI database...")
            await seed_limon_data(db, force=True)
            await db.commit()
            logger.info("Lemon BI seed completed successfully.")
        else:
            logger.info("Lemon BI analytical layer already seeded.")

        if not generic_seeded or not erp_seeded:
            logger.info("Syncing Synagro-like ERP layer...")
            result = await sync_synagro_erp(db, force=True)
            await db.commit()
            logger.info("Synagro-like ERP layer synced: %s", result)
        else:
            logger.info("Synagro-like ERP layer already seeded.")
