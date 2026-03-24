from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class CosechaV2(Base, TimestampMixin):
    """Versión mejorada de Cosecha con campos adicionales para ERP completo."""
    __tablename__ = "cosechas_v2"

    id = Column(Integer, primary_key=True, index=True)
    siembra_id = Column(Integer, ForeignKey("siembras.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    ha_cosechadas = Column(Float, nullable=False)
    rendimiento_tn_ha = Column(Float, nullable=False)    # tn/ha efectivo
    humedad = Column(Float, nullable=True)               # % humedad
    calidad = Column(String(50), nullable=True)          # buena/regular/mala
    precio_mercado = Column(Float, nullable=True)        # USD/tn precio al momento
    valor_total = Column(Float, nullable=True)           # ARS total estimado

    # Relationships
    siembra = relationship("Siembra", back_populates="cosechas", lazy="select")
