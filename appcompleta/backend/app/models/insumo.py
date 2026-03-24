from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Insumo(Base, TimestampMixin):
    __tablename__ = "insumos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False)  # herbicida, fungicida, fertilizante, semilla, combustible, otro
    unidad = Column(String(20), nullable=False, default="lt")  # lt, kg, tn, unidad
    precio_unitario = Column(Float, nullable=False, default=0)  # ARS por unidad

    # Relationships
    movimientos = relationship("MovimientoInsumo", back_populates="insumo", lazy="select")


class MovimientoInsumo(Base, TimestampMixin):
    __tablename__ = "movimientos_insumo"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)  # ingreso, egreso
    cantidad = Column(Float, nullable=False)
    fecha = Column(Date, nullable=False)
    costo_total = Column(Float, nullable=False, default=0)  # ARS total
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=True, index=True)

    # Relationships
    establecimiento = relationship("Establecimiento", back_populates="movimientos_insumo")
    insumo = relationship("Insumo", back_populates="movimientos")
    lote = relationship("Lote", back_populates="movimientos_insumo")
