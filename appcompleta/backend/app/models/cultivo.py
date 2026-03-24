from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Cultivo(Base, TimestampMixin):
    __tablename__ = "cultivos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False, unique=True)  # Soja, Maíz, Trigo, Girasol, Sorgo
    unidad = Column(String(20), nullable=False, default="tn")  # tn, qq

    # Relationships
    lotes = relationship("Lote", back_populates="cultivo", lazy="select")
    productos = relationship("Producto", back_populates="cultivo", lazy="select")
    contratos = relationship("Contrato", back_populates="cultivo", lazy="select")
