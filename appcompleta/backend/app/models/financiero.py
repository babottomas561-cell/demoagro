from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class CuentaCorriente(Base, TimestampMixin):
    __tablename__ = "cuentas_corrientes"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    banco = Column(String(100), nullable=False)
    nro_cuenta = Column(String(50), nullable=True)
    tipo = Column(String(50), nullable=False, default="corriente")  # corriente/caja_ahorro
    moneda = Column(String(10), nullable=False, default="ARS")      # ARS/USD

    # Relationships
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")
    flujos = relationship("FlujoCajaV2", back_populates="cuenta", lazy="select")


class FlujoCajaV2(Base, TimestampMixin):
    """Flujo de caja mejorado con campos USD y subcategoría."""
    __tablename__ = "flujo_caja_v2"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    tipo = Column(String(20), nullable=False)       # ingreso/egreso
    categoria = Column(String(50), nullable=False)
    subcategoria = Column(String(100), nullable=True)
    importe_ars = Column(Float, nullable=False, default=0)
    importe_usd = Column(Float, nullable=True)
    tipo_cambio = Column(Float, nullable=True)
    descripcion = Column(String(500), nullable=True)
    referencia_tipo = Column(String(50), nullable=True)  # venta/compra/labor/etc
    referencia_id = Column(Integer, nullable=True)
    cuenta_id = Column(Integer, ForeignKey("cuentas_corrientes.id"), nullable=True, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)

    # Relationships
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")
    cuenta = relationship("CuentaCorriente", back_populates="flujos", lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")


class Presupuesto(Base, TimestampMixin):
    """Presupuesto por empresa/campaña/categoría."""
    __tablename__ = "presupuestos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    categoria = Column(String(100), nullable=False)
    importe_presupuestado = Column(Float, nullable=False)
    importe_ejecutado = Column(Float, nullable=False, default=0)
    fecha_creacion = Column(Date, nullable=True)

    # Relationships
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")
