from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin


class Silo(Base, TimestampMixin):
    __tablename__ = "silos"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    capacidad_tn = Column(Float, nullable=False)
    tipo = Column(String(50), nullable=False, default="chapa")  # chapa/bolsa/planchada

    # Relationships
    establecimiento = relationship("Establecimiento", foreign_keys=[establecimiento_id], lazy="select")
    stocks_actuales = relationship("StockActualV2", back_populates="silo", lazy="select")


class StockActualV2(Base, TimestampMixin):
    """Stock actual por silo/establecimiento/cultivo/campaña."""
    __tablename__ = "stock_actual_v2"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    silo_id = Column(Integer, ForeignKey("silos.id"), nullable=True, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    tn_disponibles = Column(Float, nullable=False, default=0)
    tn_comprometidas = Column(Float, nullable=False, default=0)
    calidad = Column(String(50), nullable=True)
    humedad = Column(Float, nullable=True)
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    establecimiento = relationship("Establecimiento", foreign_keys=[establecimiento_id], lazy="select")
    cultivo = relationship("Cultivo", foreign_keys=[cultivo_id], lazy="select")
    silo = relationship("Silo", back_populates="stocks_actuales", lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")


class MovimientoStockV2(Base, TimestampMixin):
    """Movimientos de stock de granos."""
    __tablename__ = "movimientos_stock_v2"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False)  # ingreso/egreso/transferencia
    fecha = Column(DateTime, nullable=False, default=datetime.utcnow)
    cantidad_tn = Column(Float, nullable=False)
    origen = Column(String(200), nullable=True)
    destino = Column(String(200), nullable=True)
    referencia_venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True, index=True)
    observaciones = Column(String(500), nullable=True)

    # Relationships
    establecimiento = relationship("Establecimiento", foreign_keys=[establecimiento_id], lazy="select")
    cultivo = relationship("Cultivo", foreign_keys=[cultivo_id], lazy="select")
