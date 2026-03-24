from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, UniqueConstraint

from app.models.base import Base, TimestampMixin


class ContratoVentaFact(Base, TimestampMixin):
    __tablename__ = "contrato_venta_fact"

    contrato_venta_id = Column(Integer, primary_key=True, index=True)
    campania_id = Column(Integer, ForeignKey("campania_dim.campania_id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("cliente_dim.cliente_id"), nullable=False, index=True)
    mercado_id = Column(Integer, ForeignKey("mercado_dim.mercado_id"), nullable=False, index=True)
    canal_id = Column(Integer, ForeignKey("canal_dim.canal_id"), nullable=False, index=True)
    fecha_contrato = Column(Date, nullable=False, index=True)
    estado = Column(String(20), nullable=False, default="pendiente")
    kg_contratados = Column(Float, nullable=False, default=0)
    kg_entregados = Column(Float, nullable=False, default=0)
    kg_pendientes = Column(Float, nullable=False, default=0)
    precio_objetivo_usd_tn = Column(Float, nullable=False, default=0)
    moneda = Column(String(10), nullable=False, default="USD")
    condicion_pago_dias = Column(Integer, nullable=False, default=30)


class EmbarqueFact(Base, TimestampMixin):
    __tablename__ = "embarque_fact"

    embarque_id = Column(Integer, primary_key=True, index=True)
    contrato_venta_id = Column(Integer, ForeignKey("contrato_venta_fact.contrato_venta_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_embarque = Column(Date, nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("cliente_dim.cliente_id"), nullable=False, index=True)
    mercado_id = Column(Integer, ForeignKey("mercado_dim.mercado_id"), nullable=False, index=True)
    canal_id = Column(Integer, ForeignKey("canal_dim.canal_id"), nullable=False, index=True)
    kg_embarcados = Column(Float, nullable=False, default=0)
    cajas = Column(Integer, nullable=False, default=0)
    precio_realizado_usd_tn = Column(Float, nullable=False, default=0)
    estado_logistico = Column(String(20), nullable=False, default="embarcado")
    estado_cobro = Column(String(20), nullable=False, default="pendiente")


class PrecioVentaFact(Base, TimestampMixin):
    __tablename__ = "precio_venta_fact"
    __table_args__ = (UniqueConstraint("fecha_id", "mercado_id", "canal_id", name="uq_precio_venta_fact_fecha_mercado_canal"),)

    precio_venta_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    mercado_id = Column(Integer, ForeignKey("mercado_dim.mercado_id"), nullable=False, index=True)
    canal_id = Column(Integer, ForeignKey("canal_dim.canal_id"), nullable=False, index=True)
    precio_promedio_usd_tn = Column(Float, nullable=False, default=0)
    volumen_kg = Column(Float, nullable=False, default=0)


class LiquidacionFact(Base, TimestampMixin):
    __tablename__ = "liquidacion_fact"

    liquidacion_id = Column(Integer, primary_key=True, index=True)
    embarque_id = Column(Integer, ForeignKey("embarque_fact.embarque_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_liquidacion = Column(Date, nullable=False, index=True)
    importe_bruto_usd = Column(Float, nullable=False, default=0)
    descuentos_usd = Column(Float, nullable=False, default=0)
    importe_neto_usd = Column(Float, nullable=False, default=0)
    tipo_cambio_aplicado = Column(Float, nullable=False, default=0)
    importe_neto_ars = Column(Float, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="pendiente")


class StockFinalFact(Base, TimestampMixin):
    __tablename__ = "stock_final_fact"
    __table_args__ = (UniqueConstraint("fecha_id", "deposito_id", "destino_id", name="uq_stock_final_fact_fecha_dep_dest"),)

    stock_final_id = Column(Integer, primary_key=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    deposito_id = Column(Integer, ForeignKey("deposito_dim.deposito_id"), nullable=False, index=True)
    destino_id = Column(Integer, ForeignKey("destino_fruta_dim.destino_id"), nullable=False, index=True)
    kg_stock = Column(Float, nullable=False, default=0)
    cajas_stock = Column(Integer, nullable=False, default=0)
    valor_ars = Column(Float, nullable=False, default=0)


class PresupuestoLoteFact(Base, TimestampMixin):
    __tablename__ = "presupuesto_lote_fact"
    __table_args__ = (UniqueConstraint("lote_campania_id", name="uq_presupuesto_lote_fact_lc"),)

    presupuesto_lote_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    kg_plan = Column(Float, nullable=False, default=0)
    packout_plan_pct = Column(Float, nullable=False, default=0)
    ingreso_plan_ars = Column(Float, nullable=False, default=0)
    costo_directo_plan_ars = Column(Float, nullable=False, default=0)
    costo_indirecto_plan_ars = Column(Float, nullable=False, default=0)
    margen_plan_ars = Column(Float, nullable=False, default=0)


class CostosDirectosFact(Base, TimestampMixin):
    __tablename__ = "costos_directos_fact"

    costo_directo_id = Column(Integer, primary_key=True, index=True)
    lote_campania_id = Column(Integer, ForeignKey("lote_campania_fact.lote_campania_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    categoria = Column(String(60), nullable=False)
    subcategoria = Column(String(80), nullable=True)
    monto_ars = Column(Float, nullable=False, default=0)


class CostosIndirectosFact(Base, TimestampMixin):
    __tablename__ = "costos_indirectos_fact"

    costo_indirecto_id = Column(Integer, primary_key=True, index=True)
    campania_id = Column(Integer, ForeignKey("campania_dim.campania_id"), nullable=False, index=True)
    establecimiento_id = Column(Integer, ForeignKey("establecimiento_dim.establecimiento_id"), nullable=False, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha = Column(Date, nullable=False, index=True)
    categoria = Column(String(60), nullable=False)
    monto_ars = Column(Float, nullable=False, default=0)


class CuentasCobrarFact(Base, TimestampMixin):
    __tablename__ = "cuentas_cobrar_fact"

    cuenta_cobrar_id = Column(Integer, primary_key=True, index=True)
    contrato_venta_id = Column(Integer, ForeignKey("contrato_venta_fact.contrato_venta_id"), nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("cliente_dim.cliente_id"), nullable=False, index=True)
    fecha_emision = Column(Date, nullable=False, index=True)
    fecha_vencimiento = Column(Date, nullable=False, index=True)
    monto_original_ars = Column(Float, nullable=False, default=0)
    saldo_abierto_ars = Column(Float, nullable=False, default=0)
    estado = Column(String(20), nullable=False, default="pendiente")


class CobranzasFact(Base, TimestampMixin):
    __tablename__ = "cobranzas_fact"

    cobranza_id = Column(Integer, primary_key=True, index=True)
    cuenta_cobrar_id = Column(Integer, ForeignKey("cuentas_cobrar_fact.cuenta_cobrar_id"), nullable=False, index=True)
    liquidacion_id = Column(Integer, ForeignKey("liquidacion_fact.liquidacion_id"), nullable=True, index=True)
    fecha_id = Column(Integer, ForeignKey("fecha_dim.fecha_id"), nullable=False, index=True)
    fecha_cobranza = Column(Date, nullable=False, index=True)
    monto_cobrado_ars = Column(Float, nullable=False, default=0)
    medio = Column(String(40), nullable=False, default="transferencia")
    cobro_completo = Column(Boolean, nullable=False, default=False)
