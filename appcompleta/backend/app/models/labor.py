from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Labor(Base, TimestampMixin):
    __tablename__ = "labores"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)  # siembra, fumigacion, fertilizacion, cosecha, labranza
    fecha = Column(Date, nullable=False)
    costo_ha = Column(Float, nullable=False, default=0)  # costo por hectárea en ARS
    observacion = Column(Text, nullable=True)

    # Relationships
    lote = relationship("Lote", back_populates="labores")
