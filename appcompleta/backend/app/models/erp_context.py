from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.models.base import Base, TimestampMixin


class ClimaDiario(Base, TimestampMixin):
    __tablename__ = "clima_diario"
    __table_args__ = (
        UniqueConstraint("establecimiento_id", "fecha", name="uq_clima_establecimiento_fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    temp_min_c = Column(Float, nullable=True)
    temp_max_c = Column(Float, nullable=True)
    temp_media_c = Column(Float, nullable=True)
    precipitacion_mm = Column(Float, nullable=True)
    humedad_relativa = Column(Float, nullable=True)
    viento_kmh = Column(Float, nullable=True)
    et0_mm = Column(Float, nullable=True)
    riesgo_operativo = Column(String(20), nullable=False, default="medio")
    fuente = Column(String(80), nullable=False, default="Open-Meteo")


class CommoditiesPrecio(Base, TimestampMixin):
    __tablename__ = "commodities_precios"
    __table_args__ = (
        UniqueConstraint("cultivo_id", "mercado", "fecha", name="uq_commodity_mercado_fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    mercado = Column(String(40), nullable=False, default="CBOT")
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    precio = Column(Float, nullable=False, default=0)
    precio_min = Column(Float, nullable=True)
    precio_max = Column(Float, nullable=True)
    volumen = Column(Float, nullable=True)
    interes_abierto = Column(Float, nullable=True)
    fuente = Column(String(80), nullable=False, default="Mercado externo")


class MacroSerie(Base, TimestampMixin):
    __tablename__ = "macro_series"
    __table_args__ = (
        UniqueConstraint("codigo", "fecha", name="uq_macro_codigo_fecha"),
    )

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(40), nullable=False, index=True)
    nombre = Column(String(120), nullable=False)
    categoria = Column(String(40), nullable=False)
    fecha = Column(Date, nullable=False, index=True)
    valor = Column(Float, nullable=False, default=0)
    unidad = Column(String(20), nullable=False)
    variacion_diaria = Column(Float, nullable=True)
    variacion_mensual = Column(Float, nullable=True)
    variacion_interanual = Column(Float, nullable=True)
    fuente = Column(String(80), nullable=False, default="BCRA / Datos Argentina")


class AlertaContexto(Base, TimestampMixin):
    __tablename__ = "alertas_contexto"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(30), nullable=False, index=True)
    modulo = Column(String(30), nullable=False, index=True)
    referencia = Column(String(120), nullable=True)
    severidad = Column(String(20), nullable=False, default="media")
    fecha = Column(Date, nullable=False, index=True)
    titulo = Column(String(160), nullable=False)
    descripcion = Column(Text, nullable=False)
    impacto = Column(String(160), nullable=True)
    accion_sugerida = Column(Text, nullable=True)
    fuente = Column(String(80), nullable=False, default="Sistema")
