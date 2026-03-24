from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Contrato(Base, TimestampMixin):
    __tablename__ = "contratos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    volumen_contratado = Column(Float, nullable=False)   # toneladas
    precio_fijado = Column(Float, nullable=True)          # ARS/tn precio ya fijado
    precio_a_fijar = Column(Float, nullable=True)         # ARS/tn precio pendiente de fijar
    fecha_entrega = Column(Date, nullable=False)
    estado = Column(String(50), nullable=False, default="vigente")  # vigente, cumplido, vencido, cancelado

    # Relationships
    empresa = relationship("Empresa", back_populates="contratos")
    cultivo = relationship("Cultivo", back_populates="contratos")
    cliente = relationship("Cliente", back_populates="contratos")
    campania = relationship("Campania", back_populates="contratos")
