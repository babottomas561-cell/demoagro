from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.models.base import Base, TimestampMixin


class UnidadNegocio(Base, TimestampMixin):
    __tablename__ = "unidades_negocio"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_unidad_negocio_empresa_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    codigo = Column(String(30), nullable=False)
    nombre = Column(String(120), nullable=False)
    descripcion = Column(Text, nullable=True)
    activa = Column(Boolean, nullable=False, default=True)


class Campo(Base, TimestampMixin):
    __tablename__ = "campos"
    __table_args__ = (UniqueConstraint("establecimiento_id", "codigo", name="uq_campo_establecimiento_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    unidad_negocio_id = Column(Integer, ForeignKey("unidades_negocio.id"), nullable=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    codigo = Column(String(40), nullable=False)
    nombre = Column(String(150), nullable=False)
    superficie_total_ha = Column(Float, nullable=False, default=0)
    arrendado = Column(Boolean, nullable=False, default=False)
    observaciones = Column(Text, nullable=True)


class Ambiente(Base, TimestampMixin):
    __tablename__ = "ambientes"
    __table_args__ = (UniqueConstraint("lote_id", "codigo", name="uq_ambiente_lote_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    codigo = Column(String(30), nullable=False)
    nombre = Column(String(120), nullable=False)
    superficie_ha = Column(Float, nullable=False, default=0)
    potencial_productivo = Column(String(30), nullable=False, default="medio")
    textura_suelo = Column(String(50), nullable=True)
    materia_organica_pct = Column(Float, nullable=True)
    ph = Column(Float, nullable=True)


class Variedad(Base, TimestampMixin):
    __tablename__ = "variedades"
    __table_args__ = (UniqueConstraint("cultivo_id", "nombre", name="uq_variedad_cultivo_nombre"),)

    id = Column(Integer, primary_key=True, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    nombre = Column(String(120), nullable=False)
    marca = Column(String(120), nullable=True)
    ciclo = Column(String(40), nullable=True)
    tecnologia = Column(String(80), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)


class Deposito(Base, TimestampMixin):
    __tablename__ = "depositos"
    __table_args__ = (UniqueConstraint("establecimiento_id", "codigo", name="uq_deposito_establecimiento_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    codigo = Column(String(30), nullable=False)
    nombre = Column(String(120), nullable=False)
    tipo = Column(String(40), nullable=False, default="insumos")
    capacidad = Column(Float, nullable=True)
    unidad_capacidad = Column(String(20), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)


class CentroCosto(Base, TimestampMixin):
    __tablename__ = "centros_costos"
    __table_args__ = (UniqueConstraint("empresa_id", "codigo", name="uq_centro_costo_empresa_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    unidad_negocio_id = Column(Integer, ForeignKey("unidades_negocio.id"), nullable=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True, index=True)
    codigo = Column(String(30), nullable=False)
    nombre = Column(String(120), nullable=False)
    tipo = Column(String(40), nullable=False, default="operativo")
    activo = Column(Boolean, nullable=False, default=True)


class Moneda(Base, TimestampMixin):
    __tablename__ = "monedas"
    __table_args__ = (UniqueConstraint("codigo", name="uq_moneda_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(10), nullable=False)
    nombre = Column(String(60), nullable=False)
    simbolo = Column(String(10), nullable=False)
    es_base = Column(Boolean, nullable=False, default=False)


class UnidadMedida(Base, TimestampMixin):
    __tablename__ = "unidades_medida"
    __table_args__ = (UniqueConstraint("codigo", name="uq_unidad_medida_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(20), nullable=False)
    nombre = Column(String(80), nullable=False)
    categoria = Column(String(40), nullable=False)
    factor_base = Column(Float, nullable=False, default=1)


class Empleado(Base, TimestampMixin):
    __tablename__ = "empleados"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    centro_costo_id = Column(Integer, ForeignKey("centros_costos.id"), nullable=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True, index=True)
    legajo = Column(String(30), nullable=False, unique=True)
    nombre = Column(String(160), nullable=False)
    rol = Column(String(80), nullable=False)
    tipo = Column(String(40), nullable=False, default="propio")
    activo = Column(Boolean, nullable=False, default=True)
    telefono = Column(String(40), nullable=True)


class Contratista(Base, TimestampMixin):
    __tablename__ = "contratistas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    nombre = Column(String(160), nullable=False)
    especialidad = Column(String(80), nullable=False)
    cuit = Column(String(20), nullable=True)
    telefono = Column(String(40), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)


class Implemento(Base, TimestampMixin):
    __tablename__ = "implementos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    tipo = Column(String(60), nullable=False)
    marca = Column(String(80), nullable=True)
    modelo = Column(String(80), nullable=True)
    ancho_trabajo_m = Column(Float, nullable=True)
    activo = Column(Boolean, nullable=False, default=True)


class CategoriaProducto(Base, TimestampMixin):
    __tablename__ = "categorias_producto"
    __table_args__ = (UniqueConstraint("codigo", name="uq_categoria_producto_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(30), nullable=False)
    nombre = Column(String(120), nullable=False)
    tipo = Column(String(40), nullable=False)
    descripcion = Column(Text, nullable=True)


class LaborTipo(Base, TimestampMixin):
    __tablename__ = "labores_tipos"
    __table_args__ = (UniqueConstraint("codigo", name="uq_labor_tipo_codigo"),)

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String(30), nullable=False)
    nombre = Column(String(120), nullable=False)
    categoria = Column(String(40), nullable=False)
    requiere_equipo = Column(Boolean, nullable=False, default=True)
    requiere_producto = Column(Boolean, nullable=False, default=False)
    requiere_dosis = Column(Boolean, nullable=False, default=False)
    descripcion = Column(Text, nullable=True)
