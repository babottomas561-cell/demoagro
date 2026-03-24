import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import (
    health, auth, catalogos,
    gerencia, produccion, calidad, packhouse, comercial_exportacion,
    sanidad, riego, macro_mercado, erp, synagro,
)
from app.core.exceptions import (
    AgroException,
    agro_exception_handler,
    http_exception_handler,
    generic_exception_handler,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("Starting up Lemon BI API...")
    await init_db()

    # Run seed if DB is empty
    try:
        from app.seed.run_seed import run_all_seeds
        await run_all_seeds()
    except Exception as e:
        logger.warning("Seed warning (may already be seeded): %s", e)

    logger.info("Lemon BI API started successfully")
    yield
    logger.info("Shutting down Lemon BI API...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Backend API para Lemon BI - Plataforma de inteligencia operativa y comercial para negocio limonero",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(AgroException, agro_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
PREFIX = "/api"
app.include_router(health.router, prefix=PREFIX, tags=["Health"])
app.include_router(auth.router, prefix=PREFIX, tags=["Auth"])
app.include_router(catalogos.router, prefix=PREFIX, tags=["Catalogos"])
app.include_router(gerencia.router, prefix=PREFIX, tags=["Gerencia"])
app.include_router(produccion.router, prefix=PREFIX, tags=["Produccion"])
app.include_router(calidad.router, prefix=PREFIX, tags=["Calidad"])
app.include_router(packhouse.router, prefix=PREFIX, tags=["Packhouse"])
app.include_router(comercial_exportacion.router, prefix=PREFIX, tags=["Comercial Exportacion"])
app.include_router(sanidad.router, prefix=PREFIX, tags=["Sanidad"])
app.include_router(riego.router, prefix=PREFIX, tags=["Riego"])
app.include_router(macro_mercado.router, prefix=PREFIX, tags=["Macro Mercado"])
app.include_router(erp.router, prefix=PREFIX, tags=["ERP"])
app.include_router(synagro.router, prefix=PREFIX, tags=["Synagro"])


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "status": "running",
    }
