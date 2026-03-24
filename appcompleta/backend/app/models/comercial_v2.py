from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class VentaV2(Base, TimestampMixin):
    """Venta mejorada con campos USD y tipo de cambio."""
    __tablename__ = "ventas_v2"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos_v2.id"), nullable=True, index=True)
    fecha = Column(Date, nullable=False)
    cantidad_tn = Column(Float, nullable=False)
    precio_ars_tn = Column(Float, nullable=False)
    precio_usd_tn = Column(Float, nullable=True)
    importe_total_ars = Column(Float, nullable=False)
    tipo_cambio = Column(Float, nullable=True)           # ARS/USD al momento
    condicion_pago = Column(String(50), nullable=True)   # contado/credito/canje

    # Relationships
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")
    cultivo = relationship("Cultivo", foreign_keys=[cultivo_id], lazy="select")
    cliente = relationship("Cliente", foreign_keys=[cliente_id], lazy="select")
    remitos = relationship("RemitoCampo", back_populates="venta", lazy="select")


class ContratoV2(Base, TimestampMixin):
    """Contrato comercial mejorado."""
    __tablename__ = "contratos_v2"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False, default="disponible")  # forward/disponible/canje
    cantidad_tn = Column(Float, nullable=False)
    precio_usd = Column(Float, nullable=True)
    precio_ars = Column(Float, nullable=True)
    fecha_firma = Column(Date, nullable=False)
    fecha_entrega = Column(Date, nullable=True)
    estado = Column(String(30), nullable=False, default="pendiente")  # pendiente/parcial/cumplido/cancelado

    # Relationships
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")
    cultivo = relationship("Cultivo", foreign_keys=[cultivo_id], lazy="select")
    cliente = relationship("Cliente", foreign_keys=[cliente_id], lazy="select")
    ventas = relationship("VentaV2", foreign_keys="VentaV2.contrato_id", lazy="select")


class RemitoCampo(Base, TimestampMixin):
    """Remito de campo para ventas."""
    __tablename__ = "remitos_campo"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas_v2.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    cantidad_tn = Column(Float, nullable=False)
    chofer = Column(String(200), nullable=True)
    patente = Column(String(50), nullable=True)
    destino = Column(String(300), nullable=True)

    # Relationships
    venta = relationship("VentaV2", back_populates="remitos", lazy="select")
