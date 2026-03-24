from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class InsumoV2(Base, TimestampMixin):
    """Insumo mejorado con stock actual."""
    __tablename__ = "insumos_v2"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)  # semilla/fertilizante/agroquimico/combustible/otro
    unidad = Column(String(20), nullable=False, default="lt")
    precio_actual_ars = Column(Float, nullable=False, default=0)
    stock_actual = Column(Float, nullable=False, default=0)

    # Relationships
    ordenes_compra_items = relationship("ItemOrdenCompraInsumo", back_populates="insumo", lazy="select")
    movimientos = relationship("MovimientoInsumoV2", back_populates="insumo", lazy="select")


class OrdenCompraInsumo(Base, TimestampMixin):
    __tablename__ = "ordenes_compra_insumo"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    fecha = Column(Date, nullable=False)
    estado = Column(String(30), nullable=False, default="pendiente")  # pendiente/recibido/cancelado
    total_ars = Column(Float, nullable=False, default=0)

    # Relationships
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")
    proveedor = relationship("Proveedor", foreign_keys=[proveedor_id], lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")
    items = relationship("ItemOrdenCompraInsumo", back_populates="orden", lazy="select")


class ItemOrdenCompraInsumo(Base, TimestampMixin):
    __tablename__ = "items_orden_compra_insumo"

    id = Column(Integer, primary_key=True, index=True)
    orden_id = Column(Integer, ForeignKey("ordenes_compra_insumo.id"), nullable=False, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos_v2.id"), nullable=False, index=True)
    cantidad = Column(Float, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    importe = Column(Float, nullable=False)

    # Relationships
    orden = relationship("OrdenCompraInsumo", back_populates="items", lazy="select")
    insumo = relationship("InsumoV2", back_populates="ordenes_compra_items", lazy="select")


class MovimientoInsumoV2(Base, TimestampMixin):
    __tablename__ = "movimientos_insumo_v2"

    id = Column(Integer, primary_key=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos_v2.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # compra/uso/ajuste
    fecha = Column(Date, nullable=False)
    cantidad = Column(Float, nullable=False)
    referencia = Column(String(200), nullable=True)

    # Relationships
    insumo = relationship("InsumoV2", back_populates="movimientos", lazy="select")
    establecimiento = relationship("Establecimiento", foreign_keys=[establecimiento_id], lazy="select")
