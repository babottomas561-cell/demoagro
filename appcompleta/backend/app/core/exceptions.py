"""
Excepciones custom y handlers para DemoAgro API.
"""
import logging
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AgroException(Exception):
    """Excepcion base para errores de negocio de DemoAgro."""

    def __init__(self, message: str, code: str = "AGRO_ERROR", status_code: int = 400):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class ResourceNotFoundException(AgroException):
    """Recurso no encontrado en la base de datos."""

    def __init__(self, resource: str, identifier: str | int | None = None):
        detail = f"{resource} no encontrado"
        if identifier is not None:
            detail = f"{resource} con id={identifier} no encontrado"
        super().__init__(message=detail, code="NOT_FOUND", status_code=404)


class InvalidFilterException(AgroException):
    """Filtro de consulta invalido."""

    def __init__(self, field: str, value: str):
        super().__init__(
            message=f"Valor invalido '{value}' para el filtro '{field}'",
            code="INVALID_FILTER",
            status_code=422,
        )


class DatabaseException(AgroException):
    """Error de acceso a base de datos."""

    def __init__(self, detail: str = "Error de base de datos"):
        super().__init__(message=detail, code="DB_ERROR", status_code=500)


async def agro_exception_handler(request: Request, exc: AgroException) -> JSONResponse:
    """Handler global para AgroException."""
    logger.warning(
        "AgroException [%s] en %s %s: %s",
        exc.code,
        request.method,
        request.url.path,
        exc.message,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.code,
            "message": exc.message,
            "path": str(request.url.path),
        },
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler global para HTTPException estandar."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTP_ERROR",
            "message": exc.detail,
            "path": str(request.url.path),
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler de ultimo recurso para excepciones no controladas."""
    logger.exception(
        "Excepcion no controlada en %s %s",
        request.method,
        request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_ERROR",
            "message": "Error interno del servidor",
            "path": str(request.url.path),
        },
    )
