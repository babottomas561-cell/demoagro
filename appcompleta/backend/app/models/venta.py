from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Venta(Base, TimestampMixin):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    fecha = Column(Date, nullable=False)
    volumen = Column(Float, nullable=False)       # toneladas
    precio_tn = Column(Float, nullable=False)     # ARS/tn
    total = Column(Float, nullable=False)          # ARS
    estado = Column(String(50), nullable=False, default="confirmada")  # confirmada, pendiente, entregada, cancelada

    # Relationships
    empresa = relationship("Empresa", back_populates="ventas")
    producto = relationship("Producto", back_populates="ventas")
    cliente = relationship("Cliente", back_populates="ventas")
    campania = relationship("Campania", back_populates="ventas")
