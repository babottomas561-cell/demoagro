from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from app.config import settings
import logging
import importlib
import pkgutil

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    poolclass=StaticPool if "sqlite" in settings.database_url else None,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    from app.models.base import Base
    import app.models as models_pkg

    for _, module_name, _ in pkgutil.iter_modules(models_pkg.__path__):
        if module_name.startswith("__"):
            continue
        importlib.import_module(f"app.models.{module_name}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")
