from sqlalchemy import Column, Integer, String, Date, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Campania(Base, TimestampMixin):
    __tablename__ = "campanias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False, unique=True)  # ej: "2023/2024"
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    activa = Column(Boolean, default=False, nullable=False)

    # Relationships
    lotes = relationship("Lote", back_populates="campania", lazy="select")
    ventas = relationship("Venta", back_populates="campania", lazy="select")
    contratos = relationship("Contrato", back_populates="campania", lazy="select")
    flujos = relationship("FlujoCaja", back_populates="campania", lazy="select")
