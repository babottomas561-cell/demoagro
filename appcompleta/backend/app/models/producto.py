from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Producto(Base, TimestampMixin):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=True, index=True)
    unidad = Column(String(20), nullable=False, default="tn")
    precio_referencia = Column(Float, nullable=True)  # precio referencia ARS/tn

    # Relationships
    cultivo = relationship("Cultivo", back_populates="productos")
    ventas = relationship("Venta", back_populates="producto", lazy="select")
    stocks = relationship("Stock", back_populates="producto", lazy="select")
