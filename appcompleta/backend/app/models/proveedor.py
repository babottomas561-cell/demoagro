from sqlalchemy import Column, Integer, String
from app.models.base import Base, TimestampMixin


class Proveedor(Base, TimestampMixin):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    cuit = Column(String(20), unique=True, nullable=False)
    tipo = Column(String(50), nullable=False, default="insumos")  # insumos, servicios, maquinaria, transporte
