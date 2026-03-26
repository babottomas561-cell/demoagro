from __future__ import annotations

from dataclasses import asdict, dataclass

import pandas as pd


@dataclass(frozen=True)
class MetricDefinition:
    metric_id: str
    display_name: str
    domain: str
    business_question: str
    formula: str
    source_tables: tuple[str, ...]
    dimensions: tuple[str, ...]
    visualization: str
    warning: str


def metrics_catalog() -> list[MetricDefinition]:
    return finance_metrics() + operations_metrics() + commercial_metrics() + inventory_metrics()


def metrics_catalog_frame() -> pd.DataFrame:
    rows = []
    for metric in metrics_catalog():
        row = asdict(metric)
        row["source_tables"] = ", ".join(metric.source_tables)
        row["dimensions"] = ", ".join(metric.dimensions)
        rows.append(row)
    return pd.DataFrame(rows)


def finance_metrics() -> list[MetricDefinition]:
    return [
        MetricDefinition(
            "revenue_net",
            "Ingresos netos",
            "Finanzas",
            "Cuanto ingreso devengado genero la empresa por ventas.",
            "SUM(fin_facturas_venta.net_amount)",
            ("fin_facturas_venta",),
            ("period_id", "cliente_id", "producto_id"),
            "KPI + linea mensual",
            "Es devengado. No mezclar con cobranzas.",
        ),
        MetricDefinition(
            "cogs",
            "Costo de ventas",
            "Finanzas",
            "Cuanto costo el volumen efectivamente vendido.",
            "SUM(erp_despachos_venta_det.cost_total)",
            ("erp_despachos_venta_det",),
            ("period_id", "producto_id"),
            "KPI + barras por producto",
            "Depende del costo base del lote de calidad; no incluye overhead indirecto.",
        ),
        MetricDefinition(
            "gross_margin",
            "Margen bruto",
            "Finanzas",
            "Cuanta rentabilidad bruta queda despues del costo de ventas.",
            "Ingresos netos - Costo de ventas",
            ("fin_facturas_venta", "erp_despachos_venta_det"),
            ("period_id", "producto_id"),
            "KPI + waterfall",
            "No incluye nomina, logistica, mantenimiento ni impuestos.",
        ),
        MetricDefinition(
            "operating_margin",
            "Margen operativo",
            "Finanzas",
            "Cuanto queda despues de costos y gastos operativos principales.",
            "Margen bruto - payroll_total - maintenance_expense - logistics_expense",
            ("mart_finance_period",),
            ("period_id",),
            "KPI + linea",
            "No incluye depreciaciones ni resultado financiero. Es gerencial.",
        ),
        MetricDefinition(
            "ebitda_approx",
            "EBITDA aproximado",
            "Finanzas",
            "Proxy de generacion operativa antes de depreciacion y resultado financiero.",
            "revenue_net - cogs - payroll_total - maintenance_expense - logistics_expense",
            ("mart_finance_period",),
            ("period_id",),
            "KPI principal",
            "Aproximado. No representa cierre contable normativo.",
        ),
        MetricDefinition(
            "net_cash_flow",
            "Flujo de fondos neto",
            "Finanzas",
            "Como se movio la caja operativa del periodo.",
            "collections_amount - supplier_payments_amount - payroll_cash_amount - tax_payments_amount",
            ("mart_finance_period",),
            ("period_id",),
            "Barras mensuales",
            "Es flujo realizado, no devengado.",
        ),
        MetricDefinition(
            "ar_open_amount",
            "Cuentas por cobrar abiertas",
            "Finanzas",
            "Cuanto capital esta inmovilizado en clientes pendientes de cobro.",
            "SUM(fin_cuentas_cobrar.open_amount WHERE open_amount > 0)",
            ("fin_cuentas_cobrar", "mart_working_capital_ar"),
            ("cliente_id", "aging_bucket"),
            "KPI + tabla aging",
            "Mirar junto con antiguedad; saldo grande pero al dia no implica problema inmediato.",
        ),
        MetricDefinition(
            "ap_open_amount",
            "Cuentas por pagar abiertas",
            "Finanzas",
            "Cuanto pasivo comercial queda pendiente con proveedores.",
            "SUM(fin_cuentas_pagar.open_amount WHERE open_amount > 0)",
            ("fin_cuentas_pagar", "mart_working_capital_ap"),
            ("proveedor_id", "aging_bucket"),
            "KPI + tabla aging",
            "No mezclar con gasto devengado del periodo.",
        ),
    ]


def operations_metrics() -> list[MetricDefinition]:
    return [
        MetricDefinition(
            "production_tons",
            "Produccion total",
            "Operaciones",
            "Cuanto volumen neto produjo la empresa.",
            "SUM(erp_cosechas.toneladas_netas)",
            ("erp_cosechas",),
            ("period_id", "crop_code", "lote_campania_id"),
            "KPI + barras por cultivo",
            "Usa toneladas netas despues de merma.",
        ),
        MetricDefinition(
            "yield_tn_ha",
            "Rendimiento por hectarea",
            "Operaciones",
            "Que tan productivos fueron los lotes sembrados.",
            "SUM(toneladas_netas) / SUM(sown_hectares)",
            ("mart_operations_lot_campaign", "mart_operations_period"),
            ("crop_code", "lote_campania_id"),
            "Heatmap o ranking",
            "Comparar solo lotes/cultivos equivalentes.",
        ),
        MetricDefinition(
            "yield_vs_target_pct",
            "Cumplimiento de rendimiento",
            "Operaciones",
            "Que tan cerca estuvo el rinde real del objetivo esperado.",
            "actual_yield_tn_ha / target_tn_ha",
            ("mart_operations_lot_campaign",),
            ("campaign_code", "lot_name", "crop_code"),
            "Tabla con desvio",
            "Si el target estaba mal seteado, el indicador se distorsiona.",
        ),
        MetricDefinition(
            "shrink_pct",
            "Merma",
            "Operaciones",
            "Cuanto volumen se pierde entre bruto y neto.",
            "(gross_tons - production_tons) / gross_tons",
            ("mart_operations_period",),
            ("period_id", "crop_code"),
            "Linea o barras",
            "Merma alta no siempre es operativa; puede venir por humedad/calidad.",
        ),
        MetricDefinition(
            "direct_cost_per_ton",
            "Costo directo por tonelada",
            "Operaciones",
            "Cuanto costo producir una tonelada neta antes de overhead.",
            "direct_cost_total / production_tons",
            ("mart_operations_period", "mart_operations_lot_campaign"),
            ("period_id", "crop_code", "lot_name"),
            "Ranking por lote",
            "No incluye costos indirectos ni administrativos.",
        ),
    ]


def commercial_metrics() -> list[MetricDefinition]:
    return [
        MetricDefinition(
            "sold_tons",
            "Volumen vendido",
            "Comercial",
            "Cuanto volumen se coloco en el mercado.",
            "SUM(fin_facturas_venta_det.quantity)",
            ("fin_facturas_venta_det", "mart_sales_period"),
            ("period_id", "product_code", "cliente_id"),
            "Barras y linea",
            "Es volumen facturado, no necesariamente entregas futuras en contrato.",
        ),
        MetricDefinition(
            "avg_unit_price",
            "Precio promedio",
            "Comercial",
            "A que precio promedio se vendio cada producto.",
            "AVG(fin_facturas_venta_det.unit_price)",
            ("fin_facturas_venta_det", "mart_sales_period"),
            ("period_id", "product_code"),
            "Linea por producto",
            "Promedio simple; para precision usar promedio ponderado por volumen.",
        ),
        MetricDefinition(
            "sales_mix_pct",
            "Mix comercial",
            "Comercial",
            "Que peso tiene cada producto en la facturacion.",
            "revenue_net del producto / revenue_net total del periodo",
            ("mart_sales_period",),
            ("period_id", "product_code"),
            "Barras apiladas",
            "Un mix sano no siempre maximiza margen; mirar junto con rentabilidad.",
        ),
        MetricDefinition(
            "customer_concentration_pct",
            "Concentracion de clientes",
            "Comercial",
            "Que tan dependiente es la empresa de pocos clientes.",
            "SUM(revenue top N clientes) / SUM(revenue total)",
            ("mart_sales_customer",),
            ("cliente_id",),
            "Pareto o barra horizontal",
            "Alta concentracion eleva riesgo comercial aunque el revenue crezca.",
        ),
    ]


def inventory_metrics() -> list[MetricDefinition]:
    return [
        MetricDefinition(
            "stock_quantity",
            "Stock actual",
            "Stock",
            "Cuanto inventario fisico queda disponible al corte.",
            "SUM(erp_stock_actual.quantity)",
            ("erp_stock_actual", "mart_stock_snapshot"),
            ("producto_id", "deposito_id", "category_code"),
            "KPI + tabla",
            "Es snapshot al corte, no promedio del periodo.",
        ),
        MetricDefinition(
            "stock_value",
            "Stock valorizado",
            "Stock",
            "Cuanto capital queda inmovilizado en inventario.",
            "SUM(erp_stock_actual.stock_value)",
            ("erp_stock_actual", "mart_stock_snapshot"),
            ("producto_id", "deposito_id", "category_code"),
            "KPI + treemap",
            "La valuacion depende del costo base simulado, no de normas contables completas.",
        ),
        MetricDefinition(
            "stock_turnover_approx",
            "Rotacion de stock aproximada",
            "Stock",
            "Que tan rapido gira el inventario disponible.",
            "cogs / stock_value_snapshot",
            ("mart_finance_period", "mart_stock_snapshot"),
            ("product_code",),
            "KPI + barras",
            "Aproximada porque usa stock de cierre y no promedio historico diario.",
        ),
    ]
