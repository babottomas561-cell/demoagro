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
    UniqueConstraint,
)

from app.models.base import Base, TimestampMixin


class LoteCampania(Base, TimestampMixin):
    __tablename__ = "lote_campania"
    __table_args__ = (UniqueConstraint("lote_id", "campania_id", name="uq_lote_campania"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    campo_id = Column(Integer, ForeignKey("campos.id"), nullable=True, index=True)
    lote_id = Column(Integer, ForeignKey("lotes.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    variedad_id = Column(Integer, ForeignKey("variedades.id"), nullable=True, index=True)
    centro_costo_id = Column(Integer, ForeignKey("centros_costos.id"), nullable=True, index=True)
    superficie_ha = Column(Float, nullable=False, default=0)
    modalidad = Column(String(30), nullable=False, default="propio")
    estado = Column(String(30), nullable=False, default="planificado")
    fecha_inicio = Column(Date, nullable=True)
    fecha_fin = Column(Date, nullable=True)
    fecha_siembra_plan = Column(Date, nullable=True)
    fecha_siembra_real = Column(Date, nullable=True)
    fecha_cosecha_plan = Column(Date, nullable=True)
    fecha_cosecha_real = Column(Date, nullable=True)
    objetivo_rinde_tn_ha = Column(Float, nullable=True)
    objetivo_margen_ha = Column(Float, nullable=True)
    responsable_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    observaciones = Column(Text, nullable=True)


class PlanSiembra(Base, TimestampMixin):
    __tablename__ = "plan_siembra"

    id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=False, index=True)
    labor_tipo_id = Column(Integer, ForeignKey("labores_tipos.id"), nullable=True, index=True)
    fecha_planificada = Column(Date, nullable=False)
    ventana_inicio = Column(Date, nullable=False)
    ventana_fin = Column(Date, nullable=False)
    superficie_objetivo_ha = Column(Float, nullable=False, default=0)
    densidad_semillas_ha = Column(Float, nullable=True)
    semilla_insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=True, index=True)
    dosis_semilla = Column(Float, nullable=True)
    unidad_medida_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    implemento_id = Column(Integer, ForeignKey("implementos.id"), nullable=True, index=True)
    operador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    contratista_id = Column(Integer, ForeignKey("contratistas.id"), nullable=True, index=True)
    costo_estimado_ha = Column(Float, nullable=True)
    prioridad = Column(String(20), nullable=False, default="media")
    estado = Column(String(20), nullable=False, default="planificado")


class EjecucionSiembra(Base, TimestampMixin):
    __tablename__ = "ejecucion_siembra"

    id = Column(Integer, primary_key=True, index=True)
    plan_siembra_id = Column(Integer, ForeignKey("plan_siembra.id"), nullable=False, index=True)
    fecha_labor = Column(Date, nullable=False)
    superficie_ejecutada_ha = Column(Float, nullable=False, default=0)
    semillas_consumidas = Column(Float, nullable=True)
    dosis_real = Column(Float, nullable=True)
    horas_operativas = Column(Float, nullable=True)
    horas_improductivas = Column(Float, nullable=True)
    velocidad_promedio_kmh = Column(Float, nullable=True)
    humedad_suelo = Column(Float, nullable=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    implemento_id = Column(Integer, ForeignKey("implementos.id"), nullable=True, index=True)
    operador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    contratista_id = Column(Integer, ForeignKey("contratistas.id"), nullable=True, index=True)
    costo_real = Column(Float, nullable=True)
    observaciones = Column(Text, nullable=True)


class PlanFertilizacion(Base, TimestampMixin):
    __tablename__ = "plan_fertilizacion"

    id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=False, index=True)
    fecha_planificada = Column(Date, nullable=False)
    ventana_inicio = Column(Date, nullable=False)
    ventana_fin = Column(Date, nullable=False)
    superficie_objetivo_ha = Column(Float, nullable=False, default=0)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    nutriente_objetivo = Column(String(80), nullable=True)
    dosis_objetivo = Column(Float, nullable=False, default=0)
    unidad_medida_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    implemento_id = Column(Integer, ForeignKey("implementos.id"), nullable=True, index=True)
    operador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    contratista_id = Column(Integer, ForeignKey("contratistas.id"), nullable=True, index=True)
    costo_estimado_ha = Column(Float, nullable=True)
    estado = Column(String(20), nullable=False, default="planificado")


class EjecucionFertilizacion(Base, TimestampMixin):
    __tablename__ = "ejecucion_fertilizacion"

    id = Column(Integer, primary_key=True, index=True)
    plan_fertilizacion_id = Column(Integer, ForeignKey("plan_fertilizacion.id"), nullable=False, index=True)
    fecha_labor = Column(Date, nullable=False)
    superficie_ejecutada_ha = Column(Float, nullable=False, default=0)
    dosis_real = Column(Float, nullable=True)
    volumen_aplicado = Column(Float, nullable=True)
    horas_operativas = Column(Float, nullable=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    implemento_id = Column(Integer, ForeignKey("implementos.id"), nullable=True, index=True)
    operador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    costo_real = Column(Float, nullable=True)
    observaciones = Column(Text, nullable=True)


class PlanPulverizacion(Base, TimestampMixin):
    __tablename__ = "plan_pulverizacion"

    id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=False, index=True)
    fecha_planificada = Column(Date, nullable=False)
    ventana_inicio = Column(Date, nullable=False)
    ventana_fin = Column(Date, nullable=False)
    superficie_objetivo_ha = Column(Float, nullable=False, default=0)
    objetivo = Column(String(120), nullable=True)
    ingrediente_activo = Column(String(120), nullable=True)
    producto_id = Column(Integer, ForeignKey("insumos.id"), nullable=True, index=True)
    dosis_objetivo = Column(Float, nullable=True)
    unidad_medida_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    implemento_id = Column(Integer, ForeignKey("implementos.id"), nullable=True, index=True)
    operador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    contratista_id = Column(Integer, ForeignKey("contratistas.id"), nullable=True, index=True)
    costo_estimado_ha = Column(Float, nullable=True)
    estado = Column(String(20), nullable=False, default="planificado")


class EjecucionPulverizacion(Base, TimestampMixin):
    __tablename__ = "ejecucion_pulverizacion"

    id = Column(Integer, primary_key=True, index=True)
    plan_pulverizacion_id = Column(Integer, ForeignKey("plan_pulverizacion.id"), nullable=False, index=True)
    fecha_labor = Column(Date, nullable=False)
    superficie_ejecutada_ha = Column(Float, nullable=False, default=0)
    dosis_real = Column(Float, nullable=True)
    volumen_aplicado = Column(Float, nullable=True)
    agua_litros_ha = Column(Float, nullable=True)
    condiciones = Column(String(120), nullable=True)
    horas_operativas = Column(Float, nullable=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    implemento_id = Column(Integer, ForeignKey("implementos.id"), nullable=True, index=True)
    operador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    costo_real = Column(Float, nullable=True)
    observaciones = Column(Text, nullable=True)


class RendimientoLote(Base, TimestampMixin):
    __tablename__ = "rendimientos_lote"

    id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=False, index=True)
    cosecha_id = Column(Integer, ForeignKey("cosechas.id"), nullable=True, index=True)
    fecha_cosecha = Column(Date, nullable=False)
    superficie_cosechada_ha = Column(Float, nullable=False, default=0)
    produccion_tn = Column(Float, nullable=False, default=0)
    rendimiento_tn_ha = Column(Float, nullable=False, default=0)
    humedad_pct = Column(Float, nullable=True)
    merma_pct = Column(Float, nullable=True)
    calidad = Column(String(40), nullable=True)
    precio_estimado_tn = Column(Float, nullable=True)
    ingreso_estimado = Column(Float, nullable=True)


class MonitoreoPlaga(Base, TimestampMixin):
    __tablename__ = "monitoreos_plagas"

    id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=False, index=True)
    ambiente_id = Column(Integer, ForeignKey("ambientes.id"), nullable=True, index=True)
    fecha = Column(Date, nullable=False)
    tipo = Column(String(40), nullable=False)
    organismo = Column(String(120), nullable=False)
    severidad = Column(String(20), nullable=False, default="media")
    incidencia_pct = Column(Float, nullable=True)
    umbral = Column(Float, nullable=True)
    accion_recomendada = Column(Text, nullable=True)
    monitoreador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)


class ConsumoInsumo(Base, TimestampMixin):
    __tablename__ = "consumos_insumos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    movimiento_stock_id = Column(Integer, ForeignKey("movimientos_stock.id"), nullable=True, index=True)
    fecha_consumo = Column(Date, nullable=False)
    labor_origen = Column(String(40), nullable=True)
    cantidad = Column(Float, nullable=False, default=0)
    unidad_medida_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=True, index=True)
    costo_total = Column(Float, nullable=True)
    costo_ha = Column(Float, nullable=True)


class ParteTrabajo(Base, TimestampMixin):
    __tablename__ = "partes_trabajo"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=False, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=True, index=True)
    fecha_trabajo = Column(Date, nullable=False)
    labor_tipo_id = Column(Integer, ForeignKey("labores_tipos.id"), nullable=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=True, index=True)
    implemento_id = Column(Integer, ForeignKey("implementos.id"), nullable=True, index=True)
    operador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    contratista_id = Column(Integer, ForeignKey("contratistas.id"), nullable=True, index=True)
    horas_operativas = Column(Float, nullable=False, default=0)
    horas_improductivas = Column(Float, nullable=False, default=0)
    superficie_trabajada_ha = Column(Float, nullable=True)
    combustible_litros = Column(Float, nullable=True)
    estado = Column(String(20), nullable=False, default="cerrado")
    observaciones = Column(Text, nullable=True)


class StockActual(Base, TimestampMixin):
    __tablename__ = "stock_actual"
    __table_args__ = (
        UniqueConstraint(
            "deposito_id",
            "producto_id",
            "insumo_id",
            "fecha_corte",
            name="uq_stock_actual_corte_item",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True, index=True)
    deposito_id = Column(Integer, ForeignKey("depositos.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=True, index=True)
    fecha_corte = Column(Date, nullable=False)
    lote = Column(String(60), nullable=True)
    cantidad = Column(Float, nullable=False, default=0)
    reservado = Column(Float, nullable=False, default=0)
    disponible = Column(Float, nullable=False, default=0)
    costo_unitario = Column(Float, nullable=True)
    valor_total = Column(Float, nullable=True)


class MovimientoStock(Base, TimestampMixin):
    __tablename__ = "movimientos_stock"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True, index=True)
    deposito_id = Column(Integer, ForeignKey("depositos.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=True, index=True)
    fecha_movimiento = Column(Date, nullable=False, index=True)
    tipo_movimiento = Column(String(30), nullable=False)
    origen = Column(String(60), nullable=True)
    referencia = Column(String(80), nullable=True)
    cantidad = Column(Float, nullable=False, default=0)
    unidad_medida_id = Column(Integer, ForeignKey("unidades_medida.id"), nullable=True, index=True)
    costo_unitario = Column(Float, nullable=True)
    monto_total = Column(Float, nullable=True)
    observaciones = Column(Text, nullable=True)


class IngresoInsumo(Base, TimestampMixin):
    __tablename__ = "ingresos_insumos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    deposito_id = Column(Integer, ForeignKey("depositos.id"), nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra.id"), nullable=True, index=True)
    remito_id = Column(Integer, ForeignKey("remitos.id"), nullable=True, index=True)
    fecha_ingreso = Column(Date, nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    cantidad = Column(Float, nullable=False, default=0)
    costo_unitario = Column(Float, nullable=True)
    monto_total = Column(Float, nullable=True)
    movimiento_stock_id = Column(Integer, ForeignKey("movimientos_stock.id"), nullable=True, index=True)


class SalidaInsumo(Base, TimestampMixin):
    __tablename__ = "salidas_insumos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    deposito_id = Column(Integer, ForeignKey("depositos.id"), nullable=False, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=True, index=True)
    fecha_salida = Column(Date, nullable=False)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=False, index=True)
    cantidad = Column(Float, nullable=False, default=0)
    destino = Column(String(80), nullable=True)
    movimiento_stock_id = Column(Integer, ForeignKey("movimientos_stock.id"), nullable=True, index=True)
    costo_total = Column(Float, nullable=True)


class TransferenciaDeposito(Base, TimestampMixin):
    __tablename__ = "transferencias_deposito"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    deposito_origen_id = Column(Integer, ForeignKey("depositos.id"), nullable=False, index=True)
    deposito_destino_id = Column(Integer, ForeignKey("depositos.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=True, index=True)
    fecha_transferencia = Column(Date, nullable=False)
    cantidad = Column(Float, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="confirmada")
    referencia = Column(String(80), nullable=True)


class PedidoCompra(Base, TimestampMixin):
    __tablename__ = "pedidos_compra"
    __table_args__ = (UniqueConstraint("empresa_id", "numero", name="uq_pedido_compra_empresa_numero"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True, index=True)
    centro_costo_id = Column(Integer, ForeignKey("centros_costos.id"), nullable=True, index=True)
    solicitante_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    numero = Column(String(40), nullable=False)
    fecha_pedido = Column(Date, nullable=False)
    estado = Column(String(20), nullable=False, default="aprobado")
    prioridad = Column(String(20), nullable=False, default="media")
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    monto_estimado = Column(Float, nullable=True)
    observaciones = Column(Text, nullable=True)


class OrdenCompra(Base, TimestampMixin):
    __tablename__ = "ordenes_compra"
    __table_args__ = (UniqueConstraint("empresa_id", "numero", name="uq_orden_compra_empresa_numero"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    pedido_compra_id = Column(Integer, ForeignKey("pedidos_compra.id"), nullable=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    deposito_id = Column(Integer, ForeignKey("depositos.id"), nullable=True, index=True)
    numero = Column(String(40), nullable=False)
    fecha_orden = Column(Date, nullable=False)
    fecha_entrega_estimada = Column(Date, nullable=True)
    estado = Column(String(20), nullable=False, default="emitida")
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    monto_total = Column(Float, nullable=True)
    condicion_pago = Column(String(80), nullable=True)


class Remito(Base, TimestampMixin):
    __tablename__ = "remitos"
    __table_args__ = (UniqueConstraint("numero", name="uq_remito_numero"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra.id"), nullable=True, index=True)
    contrato_venta_id = Column(Integer, ForeignKey("contratos_venta.id"), nullable=True, index=True)
    numero = Column(String(60), nullable=False)
    fecha_remito = Column(Date, nullable=False)
    tipo = Column(String(20), nullable=False)
    estado = Column(String(20), nullable=False, default="emitido")
    observaciones = Column(Text, nullable=True)


class ContratoVenta(Base, TimestampMixin):
    __tablename__ = "contratos_venta"
    __table_args__ = (UniqueConstraint("empresa_id", "numero", name="uq_contrato_venta_empresa_numero"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=True, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    numero = Column(String(40), nullable=False)
    fecha_contrato = Column(Date, nullable=False)
    fecha_entrega_desde = Column(Date, nullable=True)
    fecha_entrega_hasta = Column(Date, nullable=True)
    volumen_tn = Column(Float, nullable=False, default=0)
    precio_tn = Column(Float, nullable=True)
    volumen_fijado_tn = Column(Float, nullable=False, default=0)
    volumen_entregado_tn = Column(Float, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="vigente")
    condicion = Column(String(80), nullable=True)


class ContratoCompra(Base, TimestampMixin):
    __tablename__ = "contratos_compra"
    __table_args__ = (UniqueConstraint("empresa_id", "numero", name="uq_contrato_compra_empresa_numero"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True, index=True)
    insumo_id = Column(Integer, ForeignKey("insumos.id"), nullable=True, index=True)
    numero = Column(String(40), nullable=False)
    fecha_contrato = Column(Date, nullable=False)
    fecha_entrega = Column(Date, nullable=True)
    cantidad = Column(Float, nullable=False, default=0)
    precio_unitario = Column(Float, nullable=True)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    estado = Column(String(20), nullable=False, default="vigente")


class Entrega(Base, TimestampMixin):
    __tablename__ = "entregas"

    id = Column(Integer, primary_key=True, index=True)
    contrato_venta_id = Column(Integer, ForeignKey("contratos_venta.id"), nullable=False, index=True)
    remito_id = Column(Integer, ForeignKey("remitos.id"), nullable=True, index=True)
    deposito_id = Column(Integer, ForeignKey("depositos.id"), nullable=True, index=True)
    fecha_programada = Column(Date, nullable=False)
    fecha_entrega = Column(Date, nullable=True)
    volumen_tn = Column(Float, nullable=False, default=0)
    calidad = Column(String(40), nullable=True)
    estado = Column(String(20), nullable=False, default="pendiente")


class Fijacion(Base, TimestampMixin):
    __tablename__ = "fijaciones"

    id = Column(Integer, primary_key=True, index=True)
    contrato_venta_id = Column(Integer, ForeignKey("contratos_venta.id"), nullable=False, index=True)
    fecha_fijacion = Column(Date, nullable=False)
    volumen_tn = Column(Float, nullable=False, default=0)
    precio_tn = Column(Float, nullable=False, default=0)
    mercado_referencia = Column(String(80), nullable=True)
    observaciones = Column(Text, nullable=True)


class Liquidacion(Base, TimestampMixin):
    __tablename__ = "liquidaciones"
    __table_args__ = (UniqueConstraint("numero", name="uq_liquidacion_numero"),)

    id = Column(Integer, primary_key=True, index=True)
    contrato_venta_id = Column(Integer, ForeignKey("contratos_venta.id"), nullable=True, index=True)
    entrega_id = Column(Integer, ForeignKey("entregas.id"), nullable=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True, index=True)
    numero = Column(String(60), nullable=False)
    fecha_liquidacion = Column(Date, nullable=False)
    volumen_tn = Column(Float, nullable=False, default=0)
    precio_tn = Column(Float, nullable=False, default=0)
    bonificaciones = Column(Float, nullable=False, default=0)
    gastos_comerciales = Column(Float, nullable=False, default=0)
    importe_neto = Column(Float, nullable=False, default=0)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)


class PosicionComercialERP(Base, TimestampMixin):
    __tablename__ = "posiciones_comerciales"
    __table_args__ = (UniqueConstraint("empresa_id", "campania_id", "cultivo_id", name="uq_posicion_comercial_erp"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    cultivo_id = Column(Integer, ForeignKey("cultivos.id"), nullable=False, index=True)
    toneladas_estimadas = Column(Float, nullable=False, default=0)
    toneladas_producidas = Column(Float, nullable=False, default=0)
    toneladas_contratadas = Column(Float, nullable=False, default=0)
    toneladas_fijadas = Column(Float, nullable=False, default=0)
    toneladas_entregadas = Column(Float, nullable=False, default=0)
    toneladas_sin_precio = Column(Float, nullable=False, default=0)
    stock_fisico_tn = Column(Float, nullable=False, default=0)
    precio_promedio = Column(Float, nullable=True)
    precio_mercado = Column(Float, nullable=True)
    riesgo = Column(String(20), nullable=False, default="medio")


class PresupuestoCampania(Base, TimestampMixin):
    __tablename__ = "presupuestos_campania"
    __table_args__ = (UniqueConstraint("empresa_id", "campania_id", name="uq_presupuesto_campania"),)

    id = Column(Integer, primary_key=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    campania_id = Column(Integer, ForeignKey("campanias.id"), nullable=False, index=True)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    ingreso_plan = Column(Float, nullable=False, default=0)
    costo_directo_plan = Column(Float, nullable=False, default=0)
    costo_indirecto_plan = Column(Float, nullable=False, default=0)
    margen_plan = Column(Float, nullable=False, default=0)
    capital_trabajo_objetivo = Column(Float, nullable=True)
    observaciones = Column(Text, nullable=True)


class CostoDirecto(Base, TimestampMixin):
    __tablename__ = "costos_directos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=False, index=True)
    centro_costo_id = Column(Integer, ForeignKey("centros_costos.id"), nullable=True, index=True)
    fecha_costo = Column(Date, nullable=False)
    categoria = Column(String(40), nullable=False)
    subcategoria = Column(String(60), nullable=True)
    concepto = Column(String(160), nullable=False)
    monto = Column(Float, nullable=False, default=0)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    referencia = Column(String(80), nullable=True)
    origen_tipo = Column(String(40), nullable=True)
    origen_id = Column(Integer, nullable=True)


class CostoIndirecto(Base, TimestampMixin):
    __tablename__ = "costos_indirectos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True, index=True)
    centro_costo_id = Column(Integer, ForeignKey("centros_costos.id"), nullable=True, index=True)
    fecha_costo = Column(Date, nullable=False)
    categoria = Column(String(40), nullable=False)
    concepto = Column(String(160), nullable=False)
    monto = Column(Float, nullable=False, default=0)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)


class AsignacionCosto(Base, TimestampMixin):
    __tablename__ = "asignaciones_costos"

    id = Column(Integer, primary_key=True, index=True)
    costo_indirecto_id = Column(Integer, ForeignKey("costos_indirectos.id"), nullable=False, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=False, index=True)
    criterio = Column(String(40), nullable=False, default="ha")
    base_valor = Column(Float, nullable=False, default=0)
    monto_asignado = Column(Float, nullable=False, default=0)


class CuentaCobrar(Base, TimestampMixin):
    __tablename__ = "cuentas_cobrar"
    __table_args__ = (UniqueConstraint("empresa_id", "numero_comprobante", name="uq_cxc_empresa_comprobante"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    liquidacion_id = Column(Integer, ForeignKey("liquidaciones.id"), nullable=True, index=True)
    numero_comprobante = Column(String(60), nullable=False)
    fecha_emision = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    monto_original = Column(Float, nullable=False, default=0)
    saldo = Column(Float, nullable=False, default=0)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    estado = Column(String(20), nullable=False, default="pendiente")


class CuentaPagar(Base, TimestampMixin):
    __tablename__ = "cuentas_pagar"
    __table_args__ = (UniqueConstraint("empresa_id", "numero_comprobante", name="uq_cxp_empresa_comprobante"),)

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False, index=True)
    orden_compra_id = Column(Integer, ForeignKey("ordenes_compra.id"), nullable=True, index=True)
    numero_comprobante = Column(String(60), nullable=False)
    fecha_emision = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    monto_original = Column(Float, nullable=False, default=0)
    saldo = Column(Float, nullable=False, default=0)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    estado = Column(String(20), nullable=False, default="pendiente")


class Pago(Base, TimestampMixin):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cuenta_pagar_id = Column(Integer, ForeignKey("cuentas_pagar.id"), nullable=False, index=True)
    fecha_pago = Column(Date, nullable=False)
    monto = Column(Float, nullable=False, default=0)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    medio_pago = Column(String(40), nullable=True)
    referencia = Column(String(80), nullable=True)


class Cobranza(Base, TimestampMixin):
    __tablename__ = "cobranzas"

    id = Column(Integer, primary_key=True, index=True)
    empresa_id = Column(Integer, ForeignKey("empresas.id"), nullable=False, index=True)
    cuenta_cobrar_id = Column(Integer, ForeignKey("cuentas_cobrar.id"), nullable=False, index=True)
    fecha_cobranza = Column(Date, nullable=False)
    monto = Column(Float, nullable=False, default=0)
    moneda_id = Column(Integer, ForeignKey("monedas.id"), nullable=True, index=True)
    medio_cobro = Column(String(40), nullable=True)
    referencia = Column(String(80), nullable=True)


class ParteMaquinaria(Base, TimestampMixin):
    __tablename__ = "partes_maquinaria"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimientos.id"), nullable=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania.id"), nullable=True, index=True)
    fecha = Column(Date, nullable=False)
    labor_tipo_id = Column(Integer, ForeignKey("labores_tipos.id"), nullable=True, index=True)
    horometro_inicio = Column(Float, nullable=True)
    horometro_fin = Column(Float, nullable=True)
    horas_operativas = Column(Float, nullable=False, default=0)
    horas_improductivas = Column(Float, nullable=False, default=0)
    hectareas = Column(Float, nullable=True)
    operador_id = Column(Integer, ForeignKey("empleados.id"), nullable=True, index=True)
    observaciones = Column(Text, nullable=True)


class HorasMaquina(Base, TimestampMixin):
    __tablename__ = "horas_maquina"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    parte_maquinaria_id = Column(Integer, ForeignKey("partes_maquinaria.id"), nullable=True, index=True)
    fecha = Column(Date, nullable=False)
    tipo_hora = Column(String(20), nullable=False, default="productiva")
    horas = Column(Float, nullable=False, default=0)
    costo_hora = Column(Float, nullable=True)
    costo_total = Column(Float, nullable=True)


class MantenimientoPreventivo(Base, TimestampMixin):
    __tablename__ = "mantenimientos_preventivos"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    service_schedule_id = Column(Integer, ForeignKey("service_schedule.id"), nullable=True, index=True)
    fecha_programada = Column(Date, nullable=False)
    fecha_ejecucion = Column(Date, nullable=True)
    horas_equipo = Column(Float, nullable=True)
    descripcion = Column(Text, nullable=False)
    costo = Column(Float, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="pendiente")


class MantenimientoCorrectivo(Base, TimestampMixin):
    __tablename__ = "mantenimientos_correctivos"

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    downtime_id = Column(Integer, ForeignKey("downtime_maquinaria.id"), nullable=True, index=True)
    fecha_falla = Column(DateTime, nullable=False)
    fecha_resolucion = Column(DateTime, nullable=True)
    descripcion = Column(Text, nullable=False)
    criticidad = Column(String(20), nullable=False, default="media")
    costo = Column(Float, nullable=False, default=0)
    horas_perdidas = Column(Float, nullable=True)
    estado = Column(String(20), nullable=False, default="abierto")


class DisponibilidadEquipo(Base, TimestampMixin):
    __tablename__ = "disponibilidad_equipos"
    __table_args__ = (UniqueConstraint("maquinaria_id", "fecha", name="uq_disponibilidad_equipo_fecha"),)

    id = Column(Integer, primary_key=True, index=True)
    maquinaria_id = Column(Integer, ForeignKey("maquinarias.id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False)
    disponible = Column(Boolean, nullable=False, default=True)
    capacidad_teorica_horas = Column(Float, nullable=False, default=0)
    horas_productivas = Column(Float, nullable=False, default=0)
    horas_improductivas = Column(Float, nullable=False, default=0)
    downtime_horas = Column(Float, nullable=False, default=0)
    criticidad = Column(String(20), nullable=False, default="baja")
