"""
Utilidades de filtros compartidos para queries SQLAlchemy.

Provee funciones reutilizables para aplicar filtros estandar
(empresa_id, campania_id, establecimiento_id, cultivo_id) sobre Select statements.
"""
from typing import Optional, Any
from sqlalchemy import Select


def apply_empresa_filter(query: Select, model: Any, empresa_id: Optional[int]) -> Select:
    """
    Aplica filtro por empresa_id sobre el campo empresa_id del modelo dado.

    Args:
        query:      Query SQLAlchemy existente.
        model:      Clase del modelo ORM que tiene el campo empresa_id.
        empresa_id: ID de empresa a filtrar, o None para no filtrar.

    Returns:
        Query con el filtro aplicado (o sin cambios si empresa_id es None).
    """
    if empresa_id is not None:
        query = query.where(model.empresa_id == empresa_id)
    return query


def apply_campania_filter(query: Select, model: Any, campania_id: Optional[int]) -> Select:
    """
    Aplica filtro por campania_id sobre el campo campania_id del modelo dado.

    Args:
        query:       Query SQLAlchemy existente.
        model:       Clase del modelo ORM que tiene el campo campania_id.
        campania_id: ID de campania a filtrar, o None para no filtrar.

    Returns:
        Query con el filtro aplicado (o sin cambios si campania_id es None).
    """
    if campania_id is not None:
        query = query.where(model.campania_id == campania_id)
    return query


def apply_establecimiento_filter(
    query: Select,
    model: Any,
    establecimiento_id: Optional[int],
) -> Select:
    """
    Aplica filtro por establecimiento_id sobre el campo establecimiento_id del modelo dado.
    """
    if establecimiento_id is not None:
        query = query.where(model.establecimiento_id == establecimiento_id)
    return query


def apply_cultivo_filter(query: Select, model: Any, cultivo_id: Optional[int]) -> Select:
    """
    Aplica filtro por cultivo_id sobre el campo cultivo_id del modelo dado.
    """
    if cultivo_id is not None:
        query = query.where(model.cultivo_id == cultivo_id)
    return query


def apply_estado_filter(query: Select, model: Any, estado: Optional[str]) -> Select:
    """
    Aplica filtro por estado (string) sobre el campo estado del modelo dado.
    """
    if estado is not None:
        query = query.where(model.estado == estado)
    return query


def apply_tipo_filter(query: Select, model: Any, tipo: Optional[str]) -> Select:
    """
    Aplica filtro por tipo (string) sobre el campo tipo del modelo dado.
    """
    if tipo is not None:
        query = query.where(model.tipo == tipo)
    return query
