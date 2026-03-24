"""
Paginacion estandar para DemoAgro API.

Provee PaginatedResponse, un modelo Pydantic generico para respuestas paginadas,
y la funcion paginate() para aplicar paginacion a queries SQLAlchemy.
"""
from typing import Generic, TypeVar, Any, Sequence
from pydantic import BaseModel
from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Respuesta paginada estandar."""

    total: int
    page: int
    limit: int
    items: list[T]
    has_next: bool
    has_prev: bool

    @classmethod
    def from_query(
        cls,
        items: Sequence[Any],
        total: int,
        page: int,
        limit: int,
    ) -> "PaginatedResponse[Any]":
        """
        Construye un PaginatedResponse a partir de los resultados y metadatos.

        Args:
            items:  Lista de items de la pagina actual.
            total:  Total de registros (sin paginacion).
            page:   Numero de pagina actual (base 1).
            limit:  Cantidad maxima de items por pagina.

        Returns:
            Instancia de PaginatedResponse.
        """
        return cls(
            total=total,
            page=page,
            limit=limit,
            items=list(items),
            has_next=(page * limit) < total,
            has_prev=page > 1,
        )


async def paginate(
    db: AsyncSession,
    query: Select,
    page: int,
    limit: int,
) -> tuple[list[Any], int]:
    """
    Ejecuta un query con paginacion y retorna (items, total).

    Args:
        db:     Sesion de base de datos async.
        query:  Query SQLAlchemy sin offset/limit aplicado.
        page:   Numero de pagina (base 1).
        limit:  Items por pagina.

    Returns:
        Tuple (items_de_la_pagina, total_registros).

    Example::
        items, total = await paginate(db, base_query, page=1, limit=20)
        return PaginatedResponse.from_query(items, total, page=1, limit=20)
    """
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    paginated_query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(paginated_query)

    # Soporta tanto rows escalares como rows con multiples columnas
    rows = result.all()
    if rows and hasattr(rows[0], "_mapping"):
        items = [dict(row._mapping) for row in rows]
    else:
        items = list(rows)

    return items, total
