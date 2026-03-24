from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.models.base import Base, TimestampMixin


class PresupuestoLote(Base, TimestampMixin):
    __tablename__ = "presupuestos_lote"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    rendimiento_objetivo_tn_ha = Column(Float, nullable=False, default=0)
    rendimiento_real_tn_ha = Column(Float, nullable=True)
    precio_objetivo_tn = Column(Float, nullable=False, default=0)
    precio_real_tn = Column(Float, nullable=True)
    ingreso_plan_ha = Column(Float, nullable=False, default=0)
    ingreso_real_ha = Column(Float, nullable=False, default=0)
    costo_directo_plan_ha = Column(Float, nullable=False, default=0)
    costo_directo_real_ha = Column(Float, nullable=False, default=0)
    costo_indirecto_ha = Column(Float, nullable=False, default=0)
    margen_objetivo_ha = Column(Float, nullable=False, default=0)


class PresupuestoInsumo(Base, TimestampMixin):
    __tablename__ = "presupuestos_insumo"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    consumo_plan = Column(Float, nullable=False, default=0)
    costo_plan = Column(Float, nullable=False, default=0)
    unidad = Column(String(20), nullable=False, default="lt")


class PlanLabor(Base, TimestampMixin):
    __tablename__ = "plan_labores"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    tipo_labor = Column(String(50), nullable=False)
    ventana_inicio = Column(Date, nullable=False)
    ventana_fin = Column(Date, nullable=False)
    hectareas_planificadas = Column(Float, nullable=False, default=0)
    horas_estimadas = Column(Float, nullable=False, default=0)
    equipo = Column(String(120), nullable=True)
    operador = Column(String(120), nullable=True)
    prioridad = Column(String(20), nullable=False, default="media")
    dosis_objetivo = Column(Float, nullable=True)
    nutriente_objetivo = Column(String(80), nullable=True)
    ingrediente_activo = Column(String(120), nullable=True)


class EjecucionLabor(Base, TimestampMixin):
    __tablename__ = "ejecucion_labores"

    id = Column(Integer, primary_key=True, index=True)
    plan_labor_id = Column(Integer, ForeignKey("plan_labores.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    hectareas_ejecutadas = Column(Float, nullable=False, default=0)
    horas_trabajadas = Column(Float, nullable=False, default=0)
    equipo = Column(String(120), nullable=True)
    operador = Column(String(120), nullable=True)
    dosis_aplicada = Column(Float, nullable=True)
    combustible_litros = Column(Float, nullable=True)
    estado = Column(String(20), nullable=False, default="completado")
    observacion = Column(Text, nullable=True)


class ObservacionCampo(Base, TimestampMixin):
    __tablename__ = "observaciones_campo"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    categoria = Column(String(50), nullable=False)
    severidad = Column(String(20), nullable=False, default="media")
    ambiente = Column(String(80), nullable=True)
    cobertura_pct = Column(Float, nullable=True)
    descripcion = Column(Text, nullable=False)
    accion_sugerida = Column(Text, nullable=True)


class RecomendacionAgronomica(Base, TimestampMixin):
    __tablename__ = "recomendaciones_agronomicas"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    tipo_labor = Column(String(50), nullable=False)
    nutriente = Column(String(80), nullable=True)
    ingrediente_activo = Column(String(120), nullable=True)
    dosis_recomendada = Column(Float, nullable=True)
    dosis_aplicada = Column(Float, nullable=True)
    desvio_pct = Column(Float, nullable=True)
    prioridad = Column(String(20), nullable=False, default="media")
    recomendacion = Column(Text, nullable=False)


class AplicacionDetalle(Base, TimestampMixin):
    __tablename__ = "aplicaciones_detalle"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    producto = Column(String(120), nullable=False)
    ingrediente_activo = Column(String(120), nullable=True)
    dosis_objetivo = Column(Float, nullable=True)
    dosis_real = Column(Float, nullable=True)
    unidad = Column(String(20), nullable=False, default="lt/ha")


class RendimientoAmbiente(Base, TimestampMixin):
    __tablename__ = "rendimiento_por_ambiente"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    ambiente = Column(String(80), nullable=False)
    hectareas = Column(Float, nullable=False, default=0)
    rendimiento_objetivo = Column(Float, nullable=False, default=0)
    rendimiento_real = Column(Float, nullable=False, default=0)
    margen_ha = Column(Float, nullable=True)


class DowntimeMaquinaria(Base, TimestampMixin):
    __tablename__ = "downtime_maquinaria"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    motivo = Column(String(200), nullable=False)
    horas_downtime = Column(Float, nullable=False, default=0)
    criticidad = Column(String(20), nullable=False, default="media")
    impacto_ha = Column(Float, nullable=True)


class ConsumoCombustible(Base, TimestampMixin):
    __tablename__ = "consumo_combustible"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=True, index=True)
    fecha = Column(Date, nullable=False)
    litros = Column(Float, nullable=False, default=0)
    hectareas = Column(Float, nullable=False, default=0)
    labor_tipo = Column(String(50), nullable=False)


class CostosIndirectosAsignados(Base, TimestampMixin):
    __tablename__ = "costos_indirectos_asignados"

    id = Column(Integer, primary_key=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    concepto = Column(String(120), nullable=False)
    monto_total = Column(Float, nullable=False, default=0)
    costo_ha = Column(Float, nullable=False, default=0)


class StockProyectado(Base, TimestampMixin):
    __tablename__ = "stock_proyectado"

    id = Column(Integer, primary_key=True, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    fecha_corte = Column(Date, nullable=False)
    stock_actual = Column(Float, nullable=False, default=0)
    consumo_plan_mes = Column(Float, nullable=False, default=0)
    consumo_real_mes = Column(Float, nullable=False, default=0)
    cobertura_dias = Column(Float, nullable=False, default=0)
    cobertura_ha = Column(Float, nullable=False, default=0)
    quiebre_en_dias = Column(Float, nullable=True)
    compra_sugerida = Column(Float, nullable=True)
    stock_inmovilizado = Column(Float, nullable=False, default=0)
    costo_inventario = Column(Float, nullable=False, default=0)
    severidad = Column(String(20), nullable=False, default="ok")


class EntregaComercial(Base, TimestampMixin):
    __tablename__ = "entregas_comerciales"

    id = Column(Integer, primary_key=True, index=True)
    contrato_id = Column(Integer, ForeignKey("contratos.id"), nullable=False, index=True)
    fecha_programada = Column(Date, nullable=False)
    fecha_entrega = Column(Date, nullable=True)
    volumen_tn = Column(Float, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="pendiente")


class PosicionComercial(Base, TimestampMixin):
    __tablename__ = "posicion_comercial"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    toneladas_producidas = Column(Float, nullable=False, default=0)
    toneladas_comprometidas = Column(Float, nullable=False, default=0)
    toneladas_fijadas = Column(Float, nullable=False, default=0)
    toneladas_entregadas = Column(Float, nullable=False, default=0)
    stock_fisico = Column(Float, nullable=False, default=0)
    precio_referencia = Column(Float, nullable=False, default=0)
    recomendacion = Column(String(40), nullable=True)


class AlertaOperativa(Base, TimestampMixin):
    __tablename__ = "alertas_operativas"

    id = Column(Integer, primary_key=True, index=True)
    modulo = Column(String(40), nullable=False, index=True)
    severidad = Column(String(20), nullable=False, default="warning")
    entidad_tipo = Column(String(40), nullable=False)
    entidad_id = Column(String(40), nullable=True)
    titulo = Column(String(180), nullable=False)
    descripcion = Column(Text, nullable=False)
    accion_sugerida = Column(Text, nullable=True)
    prioridad = Column(Integer, nullable=False, default=50)


class TareaCritica(Base, TimestampMixin):
    __tablename__ = "tareas_criticas"

    id = Column(Integer, primary_key=True, index=True)
    modulo = Column(String(40), nullable=False, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    descripcion = Column(Text, nullable=False)
    responsable = Column(String(120), nullable=True)
    vence_el = Column(Date, nullable=False)
    estado = Column(String(20), nullable=False, default="abierta")
    prioridad = Column(String(20), nullable=False, default="media")
    impacto = Column(String(180), nullable=True)


class ServiceSchedule(Base, TimestampMixin):
    __tablename__ = "service_schedule"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    fecha_programada = Column(Date, nullable=False)
    horas_programadas = Column(Float, nullable=True)
    tipo_service = Column(String(80), nullable=False)
    criticidad_operativa = Column(String(20), nullable=False, default="media")
    riesgo_si_falla = Column(String(180), nullable=True)
    completado = Column(Boolean, nullable=False, default=False)


class DesvioPlanReal(Base, TimestampMixin):
    __tablename__ = "desvio_plan_real"

    id = Column(Integer, primary_key=True, index=True)
    modulo = Column(String(40), nullable=False, index=True)
    referencia = Column(String(120), nullable=False)
    metrica = Column(String(80), nullable=False)
    plan_valor = Column(Float, nullable=False, default=0)
    real_valor = Column(Float, nullable=False, default=0)
    desvio_pct = Column(Float, nullable=False, default=0)
    impacto_ars = Column(Float, nullable=True)
    criticidad = Column(String(20), nullable=False, default="media")
