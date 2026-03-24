from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Empresa(Base, TimestampMixin):
    __tablename__ = "empresas"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(200), nullable=False)
    cuit = Column(String(20), unique=True, nullable=False)
    razon_social = Column(String(200), nullable=False)
    tipo = Column(String(50), nullable=False, default="SA")  # SA, SRL, SAS, Unipersonal
    activa = Column(Boolean, default=True, nullable=False)

    # Relationships
    establecimientos = relationship("Establecimiento", back_populates="empresa", lazy="select")
    ventas = relationship("Venta", back_populates="empresa", lazy="select")
    contratos = relationship("Contrato", back_populates="empresa", lazy="select")
    flujos = relationship("FlujoCaja", back_populates="empresa", lazy="select")
    usuarios = relationship("Usuario", back_populates="empresa", lazy="select")
