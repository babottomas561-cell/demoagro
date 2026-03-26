from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ForeignKeySpec:
    columns: tuple[str, ...]
    reference_table: str
    reference_columns: tuple[str, ...]
    nullable: bool = False


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...] = ()
    primary_key: tuple[str, ...] = ()
    required_columns: tuple[str, ...] = ()
    date_columns: tuple[str, ...] = ()
    foreign_keys: tuple[ForeignKeySpec, ...] = ()
    numeric_min: dict[str, float] = field(default_factory=dict)


LOAD_ORDER: list[str] = [
    "fin_condiciones_iva",
    "erp_unidades_medida",
    "erp_categorias_producto",
    "erp_productos",
    "erp_empresas",
    "erp_establecimientos",
    "erp_centros_costo",
    "erp_depositos",
    "erp_clientes",
    "erp_proveedores",
    "erp_campanias",
    "erp_lotes",
    "erp_lote_campania",
    "erp_labores_tipo",
    "fin_cuentas_financieras",
    "rrhh_categorias",
    "rrhh_empleados",
    "mnt_activos",
    "log_transportistas",
    "cont_plan_cuentas",
    "tax_tipos_impuesto",
    "erp_rendimientos_objetivo",
    "erp_ordenes_compra",
    "erp_ordenes_compra_det",
    "erp_recepciones_compra",
    "erp_recepciones_compra_det",
    "fin_facturas_compra",
    "fin_facturas_compra_det",
    "erp_labores",
    "erp_consumo_insumos",
    "erp_cosechas",
    "erp_lotes_calidad",
    "erp_analisis_calidad",
    "erp_pedidos_venta",
    "erp_pedidos_venta_det",
    "erp_despachos_venta",
    "erp_despachos_venta_det",
    "fin_facturas_venta",
    "fin_facturas_venta_det",
    "log_viajes",
    "log_viajes_det",
    "mnt_planes_preventivos",
    "mnt_ordenes_trabajo",
    "mnt_ordenes_trabajo_det",
    "mnt_paradas_activo",
    "rrhh_novedades",
    "rrhh_liquidaciones",
    "rrhh_liquidaciones_det",
    "fin_cuentas_pagar",
    "fin_pagos",
    "fin_pagos_aplicacion",
    "fin_cuentas_cobrar",
    "fin_cobranzas",
    "fin_cobranzas_aplicacion",
    "tax_comprobantes_impuesto",
    "tax_posiciones_fiscales_periodo",
    "fin_movimientos_tesoreria",
    "erp_movimientos_stock",
    "erp_stock_actual",
    "erp_transferencias_stock",
    "erp_ajustes_stock",
    "cont_reglas_asiento",
    "cont_asientos",
    "cont_asientos_det",
]


DATE_COLUMNS: set[str] = {
    "campaign_start_date",
    "campaign_end_date",
    "order_date",
    "receipt_date",
    "invoice_date",
    "due_date",
    "fecha",
    "analysis_date",
    "dispatch_date",
    "delivery_date",
    "movement_date",
    "payment_date",
    "collection_date",
    "hire_date",
    "period_start",
    "pay_date",
    "start_date",
    "end_date",
    "entry_date",
    "close_date",
}


EMPTY_TABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "erp_transferencias_stock": (
        "transferencia_id",
        "deposito_origen_id",
        "deposito_destino_id",
        "transfer_date",
        "producto_id",
        "quantity",
        "unit_cost",
    ),
    "erp_ajustes_stock": (
        "ajuste_stock_id",
        "producto_id",
        "deposito_id",
        "adjustment_date",
        "quantity_delta",
        "unit_cost",
        "reason",
    ),
}


TABLE_SPECS: dict[str, TableSpec] = {
    "erp_productos": TableSpec(
        name="erp_productos",
        primary_key=("producto_id",),
        required_columns=("producto_id", "product_code", "product_name", "category_code", "uom_code"),
    ),
    "erp_clientes": TableSpec(
        name="erp_clientes",
        primary_key=("cliente_id",),
        required_columns=("cliente_id", "client_name", "condicion_iva_id"),
        foreign_keys=(ForeignKeySpec(("condicion_iva_id",), "fin_condiciones_iva", ("condicion_iva_id",)),),
    ),
    "erp_proveedores": TableSpec(
        name="erp_proveedores",
        primary_key=("proveedor_id",),
        required_columns=("proveedor_id", "supplier_name", "condicion_iva_id"),
        foreign_keys=(ForeignKeySpec(("condicion_iva_id",), "fin_condiciones_iva", ("condicion_iva_id",)),),
    ),
    "erp_campanias": TableSpec(
        name="erp_campanias",
        primary_key=("campania_id",),
        required_columns=("campania_id", "campaign_code", "campaign_start_date", "campaign_end_date"),
        date_columns=("campaign_start_date", "campaign_end_date"),
    ),
    "erp_lotes": TableSpec(
        name="erp_lotes",
        primary_key=("lote_id",),
        required_columns=("lote_id", "establecimiento_id", "lot_name", "net_hectares"),
        foreign_keys=(ForeignKeySpec(("establecimiento_id",), "erp_establecimientos", ("establecimiento_id",)),),
        numeric_min={"net_hectares": 0.0},
    ),
    "erp_lote_campania": TableSpec(
        name="erp_lote_campania",
        primary_key=("lote_campania_id",),
        required_columns=("lote_campania_id", "lote_id", "campania_id", "producto_id", "sown_hectares"),
        foreign_keys=(
            ForeignKeySpec(("lote_id",), "erp_lotes", ("lote_id",)),
            ForeignKeySpec(("campania_id",), "erp_campanias", ("campania_id",)),
            ForeignKeySpec(("producto_id",), "erp_productos", ("producto_id",)),
        ),
        numeric_min={"sown_hectares": 0.0},
    ),
    "erp_ordenes_compra": TableSpec(
        name="erp_ordenes_compra",
        primary_key=("orden_compra_id",),
        required_columns=("orden_compra_id", "proveedor_id", "order_date"),
        date_columns=("order_date",),
        foreign_keys=(ForeignKeySpec(("proveedor_id",), "erp_proveedores", ("proveedor_id",)),),
    ),
    "erp_ordenes_compra_det": TableSpec(
        name="erp_ordenes_compra_det",
        primary_key=("orden_compra_det_id",),
        required_columns=("orden_compra_det_id", "orden_compra_id", "producto_id", "ordered_quantity", "unit_price"),
        foreign_keys=(
            ForeignKeySpec(("orden_compra_id",), "erp_ordenes_compra", ("orden_compra_id",)),
            ForeignKeySpec(("producto_id",), "erp_productos", ("producto_id",)),
            ForeignKeySpec(("centro_costo_id",), "erp_centros_costo", ("centro_costo_id",)),
        ),
        numeric_min={"ordered_quantity": 0.0, "unit_price": 0.0, "line_total": 0.0},
    ),
    "erp_recepciones_compra": TableSpec(
        name="erp_recepciones_compra",
        primary_key=("recepcion_compra_id",),
        required_columns=("recepcion_compra_id", "orden_compra_id", "deposito_id", "receipt_date"),
        date_columns=("receipt_date",),
        foreign_keys=(
            ForeignKeySpec(("orden_compra_id",), "erp_ordenes_compra", ("orden_compra_id",)),
            ForeignKeySpec(("deposito_id",), "erp_depositos", ("deposito_id",)),
        ),
    ),
    "erp_recepciones_compra_det": TableSpec(
        name="erp_recepciones_compra_det",
        primary_key=("recepcion_compra_det_id",),
        required_columns=("recepcion_compra_det_id", "recepcion_compra_id", "producto_id", "received_quantity", "unit_cost"),
        foreign_keys=(
            ForeignKeySpec(("recepcion_compra_id",), "erp_recepciones_compra", ("recepcion_compra_id",)),
            ForeignKeySpec(("producto_id",), "erp_productos", ("producto_id",)),
            ForeignKeySpec(("orden_compra_det_id",), "erp_ordenes_compra_det", ("orden_compra_det_id",)),
        ),
        numeric_min={"received_quantity": 0.0, "unit_cost": 0.0, "line_total": 0.0},
    ),
    "fin_facturas_compra": TableSpec(
        name="fin_facturas_compra",
        primary_key=("factura_compra_id",),
        required_columns=("factura_compra_id", "proveedor_id", "recepcion_compra_id", "invoice_date", "due_date", "total_amount"),
        date_columns=("invoice_date", "due_date"),
        foreign_keys=(
            ForeignKeySpec(("proveedor_id",), "erp_proveedores", ("proveedor_id",)),
            ForeignKeySpec(("recepcion_compra_id",), "erp_recepciones_compra", ("recepcion_compra_id",)),
        ),
        numeric_min={"net_amount": 0.0, "vat_amount": 0.0, "total_amount": 0.0},
    ),
    "erp_labores": TableSpec(
        name="erp_labores",
        primary_key=("labor_id",),
        required_columns=("labor_id", "lote_campania_id", "labor_tipo_id", "fecha", "superficie_ha"),
        date_columns=("fecha",),
        foreign_keys=(
            ForeignKeySpec(("lote_campania_id",), "erp_lote_campania", ("lote_campania_id",)),
            ForeignKeySpec(("labor_tipo_id",), "erp_labores_tipo", ("labor_tipo_id",)),
            ForeignKeySpec(("centro_costo_id",), "erp_centros_costo", ("centro_costo_id",)),
        ),
        numeric_min={"superficie_ha": 0.0, "horas_maquina": 0.0, "horas_hombre": 0.0, "costo_directo": 0.0},
    ),
    "erp_consumo_insumos": TableSpec(
        name="erp_consumo_insumos",
        primary_key=("consumo_id",),
        required_columns=("consumo_id", "labor_id", "producto_id", "deposito_id", "quantity"),
        foreign_keys=(
            ForeignKeySpec(("labor_id",), "erp_labores", ("labor_id",)),
            ForeignKeySpec(("producto_id",), "erp_productos", ("producto_id",)),
            ForeignKeySpec(("deposito_id",), "erp_depositos", ("deposito_id",)),
        ),
        numeric_min={"quantity": 0.0, "unit_cost": 0.0, "total_cost": 0.0},
    ),
    "erp_cosechas": TableSpec(
        name="erp_cosechas",
        primary_key=("cosecha_id",),
        required_columns=("cosecha_id", "lote_campania_id", "labor_id", "fecha", "toneladas_netas"),
        date_columns=("fecha",),
        foreign_keys=(
            ForeignKeySpec(("lote_campania_id",), "erp_lote_campania", ("lote_campania_id",)),
            ForeignKeySpec(("labor_id",), "erp_labores", ("labor_id",)),
        ),
        numeric_min={"toneladas_brutas": 0.0, "toneladas_netas": 0.0, "cost_per_ton": 0.0},
    ),
    "erp_lotes_calidad": TableSpec(
        name="erp_lotes_calidad",
        primary_key=("lote_calidad_id",),
        required_columns=("lote_calidad_id", "producto_id", "deposito_id", "cosecha_id", "available_tons"),
        foreign_keys=(
            ForeignKeySpec(("producto_id",), "erp_productos", ("producto_id",)),
            ForeignKeySpec(("deposito_id",), "erp_depositos", ("deposito_id",)),
            ForeignKeySpec(("cosecha_id",), "erp_cosechas", ("cosecha_id",)),
        ),
        numeric_min={"available_tons": 0.0, "base_cost_per_ton": 0.0},
    ),
    "erp_despachos_venta": TableSpec(
        name="erp_despachos_venta",
        primary_key=("despacho_venta_id",),
        required_columns=("despacho_venta_id", "cliente_id", "deposito_id", "dispatch_date"),
        date_columns=("dispatch_date",),
        foreign_keys=(
            ForeignKeySpec(("cliente_id",), "erp_clientes", ("cliente_id",)),
            ForeignKeySpec(("deposito_id",), "erp_depositos", ("deposito_id",)),
        ),
    ),
    "erp_despachos_venta_det": TableSpec(
        name="erp_despachos_venta_det",
        primary_key=("despacho_venta_det_id",),
        required_columns=("despacho_venta_det_id", "despacho_venta_id", "producto_id", "lote_calidad_id", "quantity"),
        foreign_keys=(
            ForeignKeySpec(("despacho_venta_id",), "erp_despachos_venta", ("despacho_venta_id",)),
            ForeignKeySpec(("producto_id",), "erp_productos", ("producto_id",)),
            ForeignKeySpec(("lote_calidad_id",), "erp_lotes_calidad", ("lote_calidad_id",)),
        ),
        numeric_min={"quantity": 0.0, "cost_per_ton": 0.0, "cost_total": 0.0},
    ),
    "fin_facturas_venta": TableSpec(
        name="fin_facturas_venta",
        primary_key=("factura_venta_id",),
        required_columns=("factura_venta_id", "cliente_id", "despacho_venta_id", "invoice_date", "due_date", "total_amount"),
        date_columns=("invoice_date", "due_date"),
        foreign_keys=(
            ForeignKeySpec(("cliente_id",), "erp_clientes", ("cliente_id",)),
            ForeignKeySpec(("despacho_venta_id",), "erp_despachos_venta", ("despacho_venta_id",)),
        ),
        numeric_min={"net_amount": 0.0, "vat_amount": 0.0, "total_amount": 0.0},
    ),
    "fin_cuentas_pagar": TableSpec(
        name="fin_cuentas_pagar",
        primary_key=("cuenta_pagar_id",),
        required_columns=("cuenta_pagar_id", "proveedor_id", "factura_compra_id", "due_date", "open_amount"),
        date_columns=("invoice_date", "due_date"),
        foreign_keys=(
            ForeignKeySpec(("proveedor_id",), "erp_proveedores", ("proveedor_id",)),
            ForeignKeySpec(("factura_compra_id",), "fin_facturas_compra", ("factura_compra_id",)),
        ),
        numeric_min={"open_amount": 0.0},
    ),
    "fin_cuentas_cobrar": TableSpec(
        name="fin_cuentas_cobrar",
        primary_key=("cuenta_cobrar_id",),
        required_columns=("cuenta_cobrar_id", "cliente_id", "factura_venta_id", "due_date", "open_amount"),
        date_columns=("invoice_date", "due_date"),
        foreign_keys=(
            ForeignKeySpec(("cliente_id",), "erp_clientes", ("cliente_id",)),
            ForeignKeySpec(("factura_venta_id",), "fin_facturas_venta", ("factura_venta_id",)),
        ),
        numeric_min={"open_amount": 0.0},
    ),
    "fin_pagos": TableSpec(
        name="fin_pagos",
        primary_key=("pago_id",),
        required_columns=("pago_id", "proveedor_id", "cuenta_financiera_id", "payment_date", "amount"),
        date_columns=("payment_date",),
        foreign_keys=(
            ForeignKeySpec(("proveedor_id",), "erp_proveedores", ("proveedor_id",)),
            ForeignKeySpec(("cuenta_financiera_id",), "fin_cuentas_financieras", ("cuenta_financiera_id",)),
        ),
        numeric_min={"amount": 0.0},
    ),
    "fin_cobranzas": TableSpec(
        name="fin_cobranzas",
        primary_key=("cobranza_id",),
        required_columns=("cobranza_id", "cliente_id", "cuenta_financiera_id", "collection_date", "amount"),
        date_columns=("collection_date",),
        foreign_keys=(
            ForeignKeySpec(("cliente_id",), "erp_clientes", ("cliente_id",)),
            ForeignKeySpec(("cuenta_financiera_id",), "fin_cuentas_financieras", ("cuenta_financiera_id",)),
        ),
        numeric_min={"amount": 0.0},
    ),
    "rrhh_liquidaciones": TableSpec(
        name="rrhh_liquidaciones",
        primary_key=("liquidacion_id",),
        required_columns=("liquidacion_id", "empleado_id", "period_id", "period_start", "pay_date", "net_salary"),
        date_columns=("period_start", "pay_date"),
        foreign_keys=(
            ForeignKeySpec(("empleado_id",), "rrhh_empleados", ("empleado_id",)),
            ForeignKeySpec(("centro_costo_id",), "erp_centros_costo", ("centro_costo_id",)),
        ),
        numeric_min={"gross_salary": 0.0, "employee_deductions": 0.0, "employer_contrib": 0.0, "net_salary": 0.0},
    ),
    "erp_movimientos_stock": TableSpec(
        name="erp_movimientos_stock",
        primary_key=("movimiento_stock_id",),
        required_columns=("movimiento_stock_id", "movement_type", "movement_date", "product_id", "deposit_id"),
        date_columns=("movement_date",),
        foreign_keys=(
            ForeignKeySpec(("product_id",), "erp_productos", ("producto_id",)),
            ForeignKeySpec(("deposit_id",), "erp_depositos", ("deposito_id",)),
            ForeignKeySpec(("lot_quality_id",), "erp_lotes_calidad", ("lote_calidad_id",), nullable=True),
        ),
    ),
    "erp_stock_actual": TableSpec(
        name="erp_stock_actual",
        primary_key=("stock_actual_id",),
        required_columns=("stock_actual_id", "producto_id", "deposito_id", "quantity"),
        foreign_keys=(
            ForeignKeySpec(("producto_id",), "erp_productos", ("producto_id",)),
            ForeignKeySpec(("deposito_id",), "erp_depositos", ("deposito_id",)),
            ForeignKeySpec(("lote_calidad_id",), "erp_lotes_calidad", ("lote_calidad_id",), nullable=True),
        ),
        numeric_min={"quantity": 0.0},
    ),
    "cont_asientos": TableSpec(
        name="cont_asientos",
        primary_key=("asiento_id",),
        required_columns=("asiento_id", "entry_date", "entry_type"),
        date_columns=("entry_date",),
    ),
    "cont_asientos_det": TableSpec(
        name="cont_asientos_det",
        primary_key=("asiento_det_id",),
        required_columns=("asiento_det_id", "asiento_id", "cuenta_contable_id", "debit_amount", "credit_amount"),
        foreign_keys=(
            ForeignKeySpec(("asiento_id",), "cont_asientos", ("asiento_id",)),
            ForeignKeySpec(("cuenta_contable_id",), "cont_plan_cuentas", ("cuenta_contable_id",)),
            ForeignKeySpec(("centro_costo_id",), "erp_centros_costo", ("centro_costo_id",), nullable=True),
        ),
        numeric_min={"debit_amount": 0.0, "credit_amount": 0.0},
    ),
    "tax_comprobantes_impuesto": TableSpec(
        name="tax_comprobantes_impuesto",
        primary_key=("comp_impuesto_id",),
        required_columns=("comp_impuesto_id", "tipo_impuesto_id", "period_id", "amount"),
        foreign_keys=(ForeignKeySpec(("tipo_impuesto_id",), "tax_tipos_impuesto", ("tipo_impuesto_id",)),),
        numeric_min={"amount": 0.0},
    ),
    "tax_posiciones_fiscales_periodo": TableSpec(
        name="tax_posiciones_fiscales_periodo",
        primary_key=("posicion_fiscal_id",),
        required_columns=("posicion_fiscal_id", "empresa_id", "period_id", "payable_amount"),
        foreign_keys=(ForeignKeySpec(("empresa_id",), "erp_empresas", ("empresa_id",)),),
    ),
}


REQUIRED_RAW_TABLES: tuple[str, ...] = (
    "erp_productos",
    "erp_clientes",
    "erp_proveedores",
    "erp_campanias",
    "erp_lotes",
    "erp_lote_campania",
    "erp_ordenes_compra",
    "erp_labores",
    "erp_cosechas",
    "erp_despachos_venta",
    "fin_facturas_compra",
    "fin_facturas_venta",
    "fin_movimientos_tesoreria",
    "erp_movimientos_stock",
    "cont_asientos",
    "cont_asientos_det",
)
