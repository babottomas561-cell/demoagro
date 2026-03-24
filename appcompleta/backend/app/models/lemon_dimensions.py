from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from app.models.base import Base, TimestampMixin


class EmpresaDim(Base, TimestampMixin):
    __tablename__ = "empresa_dim"

    empresa_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False, unique=True)
    nombre = Column(String(160), nullable=False)
    razon_social = Column(String(200), nullable=False)
    provincia_base = Column(String(80), nullable=False)
    pais = Column(String(80), nullable=False, default="Argentina")
    activa = Column(Boolean, nullable=False, default=True)


class CampaniaDim(Base, TimestampMixin):
    __tablename__ = "campania_dim"

    campania_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False, unique=True)
    nombre = Column(String(40), nullable=False, unique=True)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    estado = Column(String(20), nullable=False, default="planificada")
    activa = Column(Boolean, nullable=False, default=False)


class EstablecimientoDim(Base, TimestampMixin):
    __tablename__ = "establecimiento_dim"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_establecimiento_dim_empresa_codigo"),)

    establecimiento_id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresa_dim.empresa_id"), nullable=False, index=True)
    codigo = Column(String(20), nullable=False)
    nombre = Column(String(160), nullable=False)
    provincia = Column(String(80), nullable=False)
    localidad = Column(String(120), nullable=True)
    superficie_total_ha = Column(Float, nullable=False, default=0)
    packhouse_activo = Column(Boolean, nullable=False, default=False)
    lat = Column(Float, nullable=True)
    lon = Column(Float, nullable=True)


class CampoDim(Base, TimestampMixin):
    __tablename__ = "campo_dim"
    __table_args__ = (UniqueConstraint("establecimiento_id", "codigo", name="uq_campo_dim_establecimiento_codigo"),)

    campo_id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimiento_dim.establecimiento_id"), nullable=False, index=True)
    codigo = Column(String(20), nullable=False)
    nombre = Column(String(160), nullable=False)
    superficie_ha = Column(Float, nullable=False, default=0)
    altitud_msnm = Column(Float, nullable=True)
    tipo_suelo = Column(String(80), nullable=True)


class LoteDim(Base, TimestampMixin):
    __tablename__ = "lote_dim"
    __table_args__ = (UniqueConstraint("campo_id", "codigo", name="uq_lote_dim_campo_codigo"),)

    lote_id = Column(Integer, primary_key=True, index=True)
    campo_id = Column(Integer, ForeignKey("campo_dim.campo_id"), nullable=False, index=True)
    codigo = Column(String(24), nullable=False)
    nombre = Column(String(160), nullable=False)
    superficie_ha = Column(Float, nullable=False, default=0)
    anio_plantacion = Column(Integer, nullable=False)
    densidad_plantas_ha = Column(Integer, nullable=False, default=416)
    marco_plantacion = Column(String(40), nullable=True)
    orientacion = Column(String(40), nullable=True)


class VariedadDim(Base, TimestampMixin):
    __tablename__ = "variedad_dim"

    variedad_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False, unique=True)
    grupo = Column(String(60), nullable=False, default="limon")
    epoca_principal = Column(String(40), nullable=True)
    destino_preferido = Column(String(40), nullable=True)
    activa = Column(Boolean, nullable=False, default=True)


class ClienteDim(Base, TimestampMixin):
    __tablename__ = "cliente_dim"

    cliente_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(160), nullable=False)
    tipo = Column(String(40), nullable=False, default="exportador")
    pais = Column(String(80), nullable=False)
    region = Column(String(80), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)


class MercadoDim(Base, TimestampMixin):
    __tablename__ = "mercado_dim"

    mercado_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False)
    region = Column(String(80), nullable=False)
    moneda = Column(String(10), nullable=False, default="USD")
    activo = Column(Boolean, nullable=False, default=True)


class CanalDim(Base, TimestampMixin):
    __tablename__ = "canal_dim"

    canal_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False)
    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)


class DestinoFrutaDim(Base, TimestampMixin):
    __tablename__ = "destino_fruta_dim"

    destino_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False)
    orden = Column(Integer, nullable=False, default=0)
    es_comercial = Column(Boolean, nullable=False, default=True)


class CalibreDim(Base, TimestampMixin):
    __tablename__ = "calibre_dim"

    calibre_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False)
    diametro_min_mm = Column(Float, nullable=True)
    diametro_max_mm = Column(Float, nullable=True)
    apto_exportacion = Column(Boolean, nullable=False, default=True)


class DefectoDim(Base, TimestampMixin):
    __tablename__ = "defecto_dim"

    defecto_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False)
    categoria = Column(String(60), nullable=False)
    severidad_base = Column(String(20), nullable=False, default="media")


class LineaEmpaqueDim(Base, TimestampMixin):
    __tablename__ = "linea_empaque_dim"
    __table_args__ = (UniqueConstraint("establecimiento_id", "codigo", name="uq_linea_empaque_dim_est_codigo"),)

    linea_id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimiento_dim.establecimiento_id"), nullable=False, index=True)
    codigo = Column(String(24), nullable=False)
    nombre = Column(String(120), nullable=False)
    capacidad_tn_hora = Column(Float, nullable=False, default=0)
    activa = Column(Boolean, nullable=False, default=True)


class TurnoDim(Base, TimestampMixin):
    __tablename__ = "turno_dim"

    turno_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(80), nullable=False)
    hora_inicio = Column(String(5), nullable=False)
    hora_fin = Column(String(5), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)


class PlagaDim(Base, TimestampMixin):
    __tablename__ = "plaga_dim"

    plaga_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False)
    categoria = Column(String(60), nullable=False)
    monitoreo_semanal = Column(Boolean, nullable=False, default=True)


class EnfermedadDim(Base, TimestampMixin):
    __tablename__ = "enfermedad_dim"

    enfermedad_id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(24), nullable=False, unique=True)
    nombre = Column(String(120), nullable=False)
    categoria = Column(String(60), nullable=False)
    monitoreo_semanal = Column(Boolean, nullable=False, default=True)


class DepositoDim(Base, TimestampMixin):
    __tablename__ = "deposito_dim"
    __table_args__ = (UniqueConstraint("establecimiento_id", "codigo", name="uq_deposito_dim_est_codigo"),)

    deposito_id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimiento_dim.establecimiento_id"), nullable=False, index=True)
    codigo = Column(String(24), nullable=False)
    nombre = Column(String(120), nullable=False)
    tipo = Column(String(40), nullable=False, default="producto_terminado")
    capacidad_kg = Column(Float, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)


class FechaDim(Base, TimestampMixin):
    __tablename__ = "fecha_dim"

    fecha_id = Column(Integer, primary_key=True, index=True)
    fecha = Column(Date, nullable=False, unique=True, index=True)
    anio = Column(Integer, nullable=False)
    mes = Column(Integer, nullable=False)
    dia = Column(Integer, nullable=False)
    semana = Column(Integer, nullable=False)
    trimestre = Column(Integer, nullable=False)
    nombre_mes = Column(String(20), nullable=False)
    es_fin_de_semana = Column(Boolean, nullable=False, default=False)
