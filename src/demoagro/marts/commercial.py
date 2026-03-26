from __future__ import annotations

import pandas as pd

from demoagro.marts.common import period_from_date, safe_divide


def build_sales_period(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sales = tables["fin_facturas_venta_det"].copy()
    invoices = tables["fin_facturas_venta"][["factura_venta_id", "cliente_id", "invoice_date"]].copy()
    products = tables["erp_productos"][["producto_id", "product_code", "product_name"]].copy()
    customers = tables["erp_clientes"][["cliente_id", "client_name"]].copy()

    sales_period = (
        sales.merge(invoices, on="factura_venta_id", how="left")
        .merge(products, on="producto_id", how="left")
        .merge(customers, on="cliente_id", how="left")
    )
    sales_period["period_id"] = period_from_date(sales_period["invoice_date"])
    grouped = sales_period.groupby(["period_id", "product_code", "product_name"], as_index=False).agg(
        sold_tons=("quantity", "sum"),
        revenue_net=("net_amount", "sum"),
        avg_unit_price=("unit_price", "mean"),
        invoice_lines=("factura_venta_det_id", "count"),
    )
    revenue_total = grouped.groupby("period_id")["revenue_net"].transform("sum")
    grouped["sales_mix_pct"] = safe_divide(grouped["revenue_net"], revenue_total)
    grouped.insert(0, "mart_id", [f"MSP_{index + 1:04d}" for index in range(len(grouped))])
    return grouped.sort_values(["period_id", "revenue_net"], ascending=[True, False]).reset_index(drop=True)


def build_sales_customer(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    invoices = tables["fin_facturas_venta"][["factura_venta_id", "cliente_id", "invoice_date", "net_amount"]].copy()
    invoice_details = tables["fin_facturas_venta_det"][["factura_venta_id", "quantity", "unit_price"]].copy()
    customers = tables["erp_clientes"][["cliente_id", "client_name"]].copy()

    customer_sales = (
        invoices.merge(customers, on="cliente_id", how="left")
        .merge(invoice_details, on="factura_venta_id", how="left")
    )
    grouped = customer_sales.groupby(["cliente_id", "client_name"], as_index=False).agg(
        revenue_net=("net_amount", "sum"),
        sold_tons=("quantity", "sum"),
        avg_unit_price=("unit_price", "mean"),
        invoice_count=("factura_venta_id", "nunique"),
        last_invoice_date=("invoice_date", "max"),
    )
    grouped["revenue_share_pct"] = safe_divide(grouped["revenue_net"], grouped["revenue_net"].sum())
    grouped.insert(0, "mart_id", [f"MSC_{index + 1:04d}" for index in range(len(grouped))])
    return grouped.sort_values("revenue_net", ascending=False).reset_index(drop=True)
