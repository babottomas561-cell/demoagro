from sqlalchemy import Column, Integer, String, Float, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class MaquinariaV2(Base, TimestampMixin):
    """Maquinaria mejorada con campos de valor y horas de motor."""
    __tablename__ = "maquinarias_v2"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    tipo = Column(String(50), nullable=False)
    marca = Column(String(100), nullable=False)
    modelo = Column(String(100), nullable=False)
    anio = Column(Integer, nullable=False)
    patente_o_serie = Column(String(50), nullable=True)
    estado = Column(String(30), nullable=False, default="operativa")  # operativa/mantenimiento/baja
    valor_libro_ars = Column(Float, nullable=True)
    horas_motor = Column(Float, nullable=False, default=0)

    # Relationships
    empresa = relationship("Empresa", foreign_keys=[empresa_id], lazy="select")
    ordenes_trabajo = relationship("OrdenTrabajo", back_populates="maquinaria", lazy="select")
    mantenimientos_v2 = relationship("MantenimientoV2", back_populates="maquinaria", lazy="select")


class OrdenTrabajo(Base, TimestampMixin):
    __tablename__ = "ordenes_trabajo"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias_v2.id"), nullable=False, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=True, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    tipo_labor = Column(String(50), nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=True)
    hs_trabajadas = Column(Float, nullable=True)
    combustible_litros = Column(Float, nullable=True)
    costo_total = Column(Float, nullable=True)
    operador = Column(String(200), nullable=True)

    # Relationships
    maquinaria = relationship("MaquinariaV2", back_populates="ordenes_trabajo", lazy="select")
    lote = relationship("Lote", foreign_keys=[lote_id], lazy="select")
    campania = relationship("Campania", foreign_keys=[campania_id], lazy="select")


class MantenimientoV2(Base, TimestampMixin):
    __tablename__ = "mantenimientos_v2"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias_v2.id"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False)   # preventivo/correctivo/revision
    fecha = Column(Date, nullable=False)
    descripcion = Column(String(500), nullable=True)
    costo = Column(Float, nullable=False, default=0)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    hs_motor_al_momento = Column(Float, nullable=True)
    proxima_revision_hs = Column(Float, nullable=True)

    # Relationships
    maquinaria = relationship("MaquinariaV2", back_populates="mantenimientos_v2", lazy="select")
    proveedor = relationship("Proveedor", foreign_keys=[proveedor_id], lazy="select")
