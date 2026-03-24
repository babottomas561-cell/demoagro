from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Cliente(Base, TimestampMixin):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    cuit = Column(String(20), unique=True, nullable=False)
    provincia = Column(String(100), nullable=True)
    tipo = Column(String(50), nullable=False, default="exportador")  # exportador, molino, cooperativa, acopio, industria

    # Relationships
    ventas = relationship("Venta", back_populates="cliente", lazy="select")
    contratos = relationship("Contrato", back_populates="cliente", lazy="select")
