from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint

from app.models.base import Base, TimestampMixin


class ClimaDiarioFact(Base, TimestampMixin):
    __tablename__ = "clima_diario_fact"
    __table_args__ = (UniqueConstraint("establecimiento_id", "fecha_id", name="uq_clima_diario_fact_est_fecha"),)

    clima_diario_id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimiento_dim.establecimiento_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    temperatura_min_c = Column(Float, nullable=False, default=0)
    temperatura_max_c = Column(Float, nullable=False, default=0)
    temperatura_media_c = Column(Float, nullable=False, default=0)
    precipitacion_mm = Column(Float, nullable=False, default=0)
    humedad_relativa_pct = Column(Float, nullable=False, default=0)
    horas_frio = Column(Float, nullable=False, default=0)


class MacroSeriesFact(Base, TimestampMixin):
    __tablename__ = "macro_series_fact"
    __table_args__ = (UniqueConstraint("fecha_id", "variable", name="uq_macro_series_fact_fecha_variable"),)

    macro_serie_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    variable = Column(String(60), nullable=False)
    valor = Column(Float, nullable=False, default=0)
    unidad = Column(String(30), nullable=False)
    fuente = Column(String(80), nullable=False)


class TipoCambioFact(Base, TimestampMixin):
    __tablename__ = "tipo_cambio_fact"
    __table_args__ = (UniqueConstraint("fecha_id", name="uq_tipo_cambio_fact_fecha"),)

    tipo_cambio_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    oficial = Column(Float, nullable=False, default=0)
    mayorista = Column(Float, nullable=False, default=0)
    exportacion = Column(Float, nullable=False, default=0)


class PrecioExportacionFact(Base, TimestampMixin):
    __tablename__ = "precio_exportacion_fact"
    __table_args__ = (UniqueConstraint("fecha_id", "mercado_id", name="uq_precio_exportacion_fact_fecha_mercado"),)

    precio_exportacion_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    mercado_id = Column(Integer, ForeignKey("mercado_dim.mercado_id"), nullable=False, index=True)
    precio_promedio_usd_tn = Column(Float, nullable=False, default=0)
    volumen_kg = Column(Float, nullable=False, default=0)


class CostoEnergiaFact(Base, TimestampMixin):
    __tablename__ = "costo_energia_fact"
    __table_args__ = (UniqueConstraint("fecha_id", name="uq_costo_energia_fact_fecha"),)

    costo_energia_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    ars_kwh = Column(Float, nullable=False, default=0)
    indice = Column(Float, nullable=False, default=100)


class CostoFleteFact(Base, TimestampMixin):
    __tablename__ = "costo_flete_fact"
    __table_args__ = (UniqueConstraint("fecha_id", "mercado_id", name="uq_costo_flete_fact_fecha_mercado"),)

    costo_flete_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    mercado_id = Column(Integer, ForeignKey("mercado_dim.mercado_id"), nullable=False, index=True)
    usd_tn = Column(Float, nullable=False, default=0)
    combustible_pct = Column(Float, nullable=False, default=0)
