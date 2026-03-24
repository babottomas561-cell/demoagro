from sqlalchemy import Column, Integer, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base, TimestampMixin


class Stock(Base, TimestampMixin):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    volumen_disponible = Column(Float, nullable=False, default=0)    # tn disponible para venta
    volumen_vendido = Column(Float, nullable=False, default=0)        # tn ya vendida/entregada
    volumen_comprometido = Column(Float, nullable=False, default=0)   # tn comprometida en contratos
    fecha_actualizacion = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    establecimiento = relationship("Establecimiento", back_populates="stocks")
    producto = relationship("Producto", back_populates="stocks")
