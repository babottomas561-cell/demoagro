from sqlalchemy import Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint

from app.models.base import Base, TimestampMixin


class RecepcionFrutaFact(Base, TimestampMixin):
    __tablename__ = "recepcion_fruta_fact"

    recepcion_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_recepcion = Column(Date, nullable=False, index=True)
    kg_recibidos = Column(Float, nullable=False, default=0)
    bins_recibidos = Column(Integer, nullable=False, default=0)
    temperatura_fruta_c = Column(Float, nullable=True)
    brix = Column(Float, nullable=True)
    acidez = Column(Float, nullable=True)
    observaciones = Column(String(240), nullable=True)


class ClasificacionCalidadFact(Base, TimestampMixin):
    __tablename__ = "clasificacion_calidad_fact"

    clasificacion_id = Column(Integer, primary_key=True, index=True)
    recepcion_id = Column(Integer, ForeignKey("recepcion_fruta_fact.recepcion_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_clasificacion = Column(Date, nullable=False, index=True)
    destino_id = Column(Integer, ForeignKey("destino_fruta_dim.destino_id"), nullable=False, index=True)
    calibre_id = Column(Integer, ForeignKey("calibre_dim.calibre_id"), nullable=True, index=True)
    kg_clasificados = Column(Float, nullable=False, default=0)
    porcentaje = Column(Float, nullable=False, default=0)
    color_indice = Column(Float, nullable=True)
    firmeza = Column(Float, nullable=True)


class PackoutFact(Base, TimestampMixin):
    __tablename__ = "packout_fact"
    __table_args__ = (
        UniqueConstraint(
            "recepcion_id",
            "linea_id",
            "turno_id",
            "destino_id",
            "calibre_id",
            "fecha_id",
            name="uq_packout_fact_core",
        ),
    )

    packout_id = Column(Integer, primary_key=True, index=True)
    recepcion_id = Column(Integer, ForeignKey("recepcion_fruta_fact.recepcion_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_proceso = Column(Date, nullable=False, index=True)
    linea_id = Column(Integer, ForeignKey("linea_empaque_dim.linea_id"), nullable=False, index=True)
    turno_id = Column(Integer, ForeignKey("turno_dim.turno_id"), nullable=False, index=True)
    destino_id = Column(Integer, ForeignKey("destino_fruta_dim.destino_id"), nullable=False, index=True)
    calibre_id = Column(Integer, ForeignKey("calibre_dim.calibre_id"), nullable=True, index=True)
    kg_entrada = Column(Float, nullable=False, default=0)
    kg_salida = Column(Float, nullable=False, default=0)
    cajas = Column(Integer, nullable=False, default=0)
    packout_pct = Column(Float, nullable=False, default=0)
    eficiencia_pct = Column(Float, nullable=False, default=0)


class RechazoFact(Base, TimestampMixin):
    __tablename__ = "rechazo_fact"
    __table_args__ = (UniqueConstraint("recepcion_id", "defecto_id", "fecha_id", name="uq_rechazo_fact_recepcion_defecto_fecha"),)

    rechazo_id = Column(Integer, primary_key=True, index=True)
    recepcion_id = Column(Integer, ForeignKey("recepcion_fruta_fact.recepcion_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_rechazo = Column(Date, nullable=False, index=True)
    defecto_id = Column(Integer, ForeignKey("defecto_dim.defecto_id"), nullable=False, index=True)
    kg_rechazo = Column(Float, nullable=False, default=0)
    porcentaje_rechazo = Column(Float, nullable=False, default=0)
