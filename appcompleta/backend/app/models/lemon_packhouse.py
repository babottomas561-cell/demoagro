from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint

from app.models.base import Base, TimestampMixin


class PackhouseTurnoFact(Base, TimestampMixin):
    __tablename__ = "packhouse_turno_fact"
    __table_args__ = (UniqueConstraint("fecha_id", "linea_id", "turno_id", name="uq_packhouse_turno_fact_fecha_linea_turno"),)

    packhouse_turno_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimiento_dim.establecimiento_id"), nullable=False, index=True)
    linea_id = Column(Integer, ForeignKey("linea_empaque_dim.linea_id"), nullable=False, index=True)
    turno_id = Column(Integer, ForeignKey("turno_dim.turno_id"), nullable=False, index=True)
    kg_procesados = Column(Float, nullable=False, default=0)
    horas_programadas = Column(Float, nullable=False, default=0)
    horas_productivas = Column(Float, nullable=False, default=0)
    horas_downtime = Column(Float, nullable=False, default=0)
    eficiencia_pct = Column(Float, nullable=False, default=0)
    toneladas_hora = Column(Float, nullable=False, default=0)
    operarios = Column(Integer, nullable=False, default=0)


class DowntimePackhouseFact(Base, TimestampMixin):
    __tablename__ = "downtime_packhouse_fact"

    downtime_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    linea_id = Column(Integer, ForeignKey("linea_empaque_dim.linea_id"), nullable=False, index=True)
    turno_id = Column(Integer, ForeignKey("turno_dim.turno_id"), nullable=False, index=True)
    motivo = Column(String(120), nullable=False)
    minutos = Column(Float, nullable=False, default=0)
    criticidad = Column(String(20), nullable=False, default="media")


class ManoObraPackhouseFact(Base, TimestampMixin):
    __tablename__ = "mano_obra_packhouse_fact"
    __table_args__ = (UniqueConstraint("fecha_id", "linea_id", "turno_id", name="uq_mano_obra_packhouse_fecha_linea_turno"),)

    mano_obra_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    linea_id = Column(Integer, ForeignKey("linea_empaque_dim.linea_id"), nullable=False, index=True)
    turno_id = Column(Integer, ForeignKey("turno_dim.turno_id"), nullable=False, index=True)
    operarios = Column(Integer, nullable=False, default=0)
    horas_hombre = Column(Float, nullable=False, default=0)
    costo_ars = Column(Float, nullable=False, default=0)


class ConsumoPackhouseFact(Base, TimestampMixin):
    __tablename__ = "consumo_packhouse_fact"

    consumo_packhouse_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    linea_id = Column(Integer, ForeignKey("linea_empaque_dim.linea_id"), nullable=False, index=True)
    rubro = Column(String(80), nullable=False)
    unidad = Column(String(20), nullable=False)
    cantidad = Column(Float, nullable=False, default=0)
    costo_ars = Column(Float, nullable=False, default=0)


class MantenimientoPackhouseFact(Base, TimestampMixin):
    __tablename__ = "mantenimiento_packhouse_fact"

    mantenimiento_packhouse_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    linea_id = Column(Integer, ForeignKey("linea_empaque_dim.linea_id"), nullable=False, index=True)
    tipo = Column(String(40), nullable=False)
    preventivo = Column(Boolean, nullable=False, default=True)
    minutos_intervencion = Column(Float, nullable=False, default=0)
    costo_ars = Column(Float, nullable=False, default=0)
