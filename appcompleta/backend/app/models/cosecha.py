from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Cosecha(Base, TimestampMixin):
    __tablename__ = "cosechas"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    volumen_cosechado = Column(Float, nullable=False)  # en toneladas
    humedad = Column(Float, nullable=True)             # % humedad al momento de cosecha
    merma = Column(Float, nullable=True)               # % merma estimada
    rendimiento = Column(Float, nullable=False)        # tn/ha efectivo

    # Relationships
    lote = relationship("Lote", back_populates="cosechas")
