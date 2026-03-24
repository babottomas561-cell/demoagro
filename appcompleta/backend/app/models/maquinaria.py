from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Maquinaria(Base, TimestampMixin):
    __tablename__ = "maquinarias"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)   # tractor, cosechadora, pulverizadora, sembradora, tolva
    marca = Column(String(100), nullable=False)
    modelo = Column(String(100), nullable=False)
    anio = Column(Integer, nullable=False)
    horas_totales = Column(Float, nullable=False, default=0)
    estado = Column(String(50), nullable=False, default="operativo")  # operativo, mantenimiento, baja

    # Relationships
    establecimiento = relationship("Establecimiento", back_populates="maquinarias")
    mantenimientos = relationship("Mantenimiento", back_populates="maquinaria", lazy="select")
