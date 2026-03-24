from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Aplicacion(Base, TimestampMixin):
    __tablename__ = "aplicaciones"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)  # herbicida/fungicida/insecticida/fertilizante
    fecha = Column(Date, nullable=False)
    producto = Column(String(200), nullable=False)
    dosis = Column(Float, nullable=True)
    unidad = Column(String(20), nullable=True)   # lt/ha, kg/ha, tn/ha
    ha_aplicadas = Column(Float, nullable=False)
    costo_total = Column(Float, nullable=True)   # ARS

    # Relationships
    lote = relationship("Lote", foreign_keys=[lote_id], lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")
