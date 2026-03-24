from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class FlujoCaja(Base, TimestampMixin):
    __tablename__ = "flujo_caja"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    tipo = Column(String(20), nullable=False)       # ingreso, egreso
    concepto = Column(String(300), nullable=False)
    monto = Column(Float, nullable=False)            # ARS
    categoria = Column(String(50), nullable=False)   # venta, insumo, labores, credito, impuesto, salarios, alquiler, otro
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)

    # Relationships
    empresa = relationship("Empresa", back_populates="flujos")
    campania = relationship("Campania", back_populates="flujos")
