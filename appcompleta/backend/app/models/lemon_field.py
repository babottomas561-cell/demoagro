from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.models.base import Base, TimestampMixin


class LoteCampaniaFact(Base, TimestampMixin):
    __tablename__ = "lote_campania_fact"
    __table_args__ = (UniqueConstraint("lote_id", "campania_id", name="uq_lote_campania_fact"),)

    lote_campania_id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lote_dim.lote_id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campania_dim.campania_id"), nullable=False, index=True)
    variedad_id = Column(Integer, ForeignKey("variedad_dim.variedad_id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimiento_dim.establecimiento_id"), nullable=False, index=True)
    superficie_ha = Column(Float, nullable=False, default=0)
    arboles_productivos = Column(Integer, nullable=False, default=0)
    fecha_inicio_cosecha_estimada = Column(Date, nullable=True)
    fecha_fin_cosecha_estimada = Column(Date, nullable=True)
    objetivo_kg_ha = Column(Float, nullable=False, default=0)
    objetivo_packout_pct = Column(Float, nullable=False, default=0)
    objetivo_margen_ha = Column(Float, nullable=False, default=0)
    estado = Column(String(30), nullable=False, default="planificado")
    condicion_hidrica = Column(String(20), nullable=False, default="normal")


class CosechaFact(Base, TimestampMixin):
    __tablename__ = "cosecha_fact"

    cosecha_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_cosecha = Column(Date, nullable=False, index=True)
    kg_cosechados = Column(Float, nullable=False, default=0)
    jornales = Column(Float, nullable=False, default=0)
    cuadrillas = Column(Integer, nullable=False, default=0)
    bins_cosechados = Column(Integer, nullable=False, default=0)
    costo_cosecha_ars = Column(Float, nullable=False, default=0)
    fruta_danada_pct = Column(Float, nullable=False, default=0)


class RendimientoLoteFact(Base, TimestampMixin):
    __tablename__ = "rendimiento_lote_fact"
    __table_args__ = (UniqueConstraint("lote_campania_id", name="uq_rendimiento_lote_fact_lc"),)

    rendimiento_lote_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    kg_totales = Column(Float, nullable=False, default=0)
    kg_ha = Column(Float, nullable=False, default=0)
    fruta_exportable_pct = Column(Float, nullable=False, default=0)
    fruta_industria_pct = Column(Float, nullable=False, default=0)
    fruta_descarte_pct = Column(Float, nullable=False, default=0)
    semana_pico = Column(Integer, nullable=True)
    desvio_vs_objetivo_pct = Column(Float, nullable=False, default=0)


class RendimientoAmbienteFact(Base, TimestampMixin):
    __tablename__ = "rendimiento_ambiente_fact"

    rendimiento_ambiente_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    ambiente = Column(String(40), nullable=False)
    superficie_ha = Column(Float, nullable=False, default=0)
    kg_ha = Column(Float, nullable=False, default=0)
    packout_pct = Column(Float, nullable=False, default=0)
    observacion = Column(Text, nullable=True)


class ScoutingFact(Base, TimestampMixin):
    __tablename__ = "scouting_fact"

    scouting_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_evento = Column(Date, nullable=False, index=True)
    plaga_id = Column(Integer, ForeignKey("plaga_dim.plaga_id"), nullable=True, index=True)
    enfermedad_id = Column(Integer, ForeignKey("enfermedad_dim.enfermedad_id"), nullable=True, index=True)
    severidad = Column(String(20), nullable=False, default="media")
    incidencia_pct = Column(Float, nullable=False, default=0)
    lotes_afectados_pct = Column(Float, nullable=False, default=0)
    alerta = Column(Boolean, nullable=False, default=False)
    recomendacion = Column(Text, nullable=True)


class AplicacionFitosanitariaFact(Base, TimestampMixin):
    __tablename__ = "aplicacion_fitosanitaria_fact"

    aplicacion_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_aplicacion = Column(Date, nullable=False, index=True)
    objetivo = Column(String(120), nullable=False)
    producto = Column(String(120), nullable=False)
    ingrediente_activo = Column(String(120), nullable=True)
    dosis_l_ha = Column(Float, nullable=False, default=0)
    volumen_caldo_l_ha = Column(Float, nullable=False, default=0)
    costo_ars_ha = Column(Float, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="ejecutada")


class RiegoFact(Base, TimestampMixin):
    __tablename__ = "riego_fact"

    riego_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_riego = Column(Date, nullable=False, index=True)
    m3_aplicados = Column(Float, nullable=False, default=0)
    m3_ha = Column(Float, nullable=False, default=0)
    horas_riego = Column(Float, nullable=False, default=0)
    energia_kwh = Column(Float, nullable=False, default=0)
    costo_ars = Column(Float, nullable=False, default=0)


class FertirriegoFact(Base, TimestampMixin):
    __tablename__ = "fertirriego_fact"

    fertirriego_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_fertirriego = Column(Date, nullable=False, index=True)
    nutriente = Column(String(80), nullable=False)
    kg_aplicados = Column(Float, nullable=False, default=0)
    m3_aplicados = Column(Float, nullable=False, default=0)
    costo_ars = Column(Float, nullable=False, default=0)


class RequerimientoHidricoFact(Base, TimestampMixin):
    __tablename__ = "requerimiento_hidrico_fact"
    __table_args__ = (UniqueConstraint("lote_campania_id", "fecha_id", name="uq_requerimiento_hidrico_lc_fecha"),)

    requerimiento_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    m3_requeridos = Column(Float, nullable=False, default=0)
    m3_aportados = Column(Float, nullable=False, default=0)
    balance_hidrico_m3 = Column(Float, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="normal")


class Et0Fact(Base, TimestampMixin):
    __tablename__ = "et0_fact"
    __table_args__ = (UniqueConstraint("establecimiento_id", "fecha_id", name="uq_et0_establecimiento_fecha"),)

    et0_id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimiento_dim.establecimiento_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    et0_mm = Column(Float, nullable=False, default=0)
    kc = Column(Float, nullable=False, default=0)
    eto_ajustada_mm = Column(Float, nullable=False, default=0)
