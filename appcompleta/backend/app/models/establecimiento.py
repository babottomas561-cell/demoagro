from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Establecimiento(Base, TimestampMixin):
    __tablename__ = "establecimientos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    ubicacion = Column(String(300), nullable=True)
    provincia = Column(String(100), nullable=False)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)
    hectareas_totales = Column(Float, nullable=False, default=0)

    # Relationships
    empresa = relationship("Empresa", back_populates="establecimientos")
    lotes = relationship("Lote", back_populates="establecimiento", lazy="select")
    stocks = relationship("Stock", back_populates="establecimiento", lazy="select")
    movimientos_insumo = relationship("MovimientoInsumo", back_populates="establecimiento", lazy="select")
    maquinarias = relationship("Maquinaria", back_populates="establecimiento", lazy="select")
