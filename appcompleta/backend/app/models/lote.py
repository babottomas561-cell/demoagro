from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Lote(Base, TimestampMixin):
    __tablename__ = "lotes"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    nombre = Column(String(100), nullable=False)
    hectareas = Column(Float, nullable=False)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=True, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    estado = Column(String(50), nullable=False, default="barbecho")  # sembrado, cosechado, barbecho
    fecha_siembra = Column(Date, nullable=True)
    fecha_cosecha = Column(Date, nullable=True)
    rendimiento_real = Column(Float, nullable=True)       # tn/ha
    rendimiento_historico = Column(Float, nullable=True)  # tn/ha promedio histórico

    # Relationships
    establecimiento = relationship("Establecimiento", back_populates="lotes")
    cultivo = relationship("Cultivo", back_populates="lotes")
    campania = relationship("Campania", back_populates="lotes")
    labores = relationship("Labor", back_populates="lote", lazy="select")
    cosechas = relationship("Cosecha", back_populates="lote", lazy="select")
    movimientos_insumo = relationship("MovimientoInsumo", back_populates="lote", lazy="select")
