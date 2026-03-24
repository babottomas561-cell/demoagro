from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Siembra(Base, TimestampMixin):
    __tablename__ = "siembras"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    ha_sembradas = Column(Float, nullable=False)
    densidad = Column(Float, nullable=True)          # semillas/m2 o kg/ha
    hibrido = Column(String(200), nullable=True)     # nombre variedad/hibrido
    observaciones = Column(Text, nullable=True)

    # Relationships
    lote = relationship("Lote", foreign_keys=[lote_id], lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")
    cultivo = relationship("Cultivo", foreign_keys=[cultivo_id], lazy="select")
    cosechas = relationship("CosechaV2", back_populates="siembra", lazy="select")
