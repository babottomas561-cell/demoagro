from __future__ import annotations

import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent
if not (_APP_DIR / "_bootstrap.py").exists():
    _APP_DIR = _APP_DIR.parent

_app_dir_str = str(_APP_DIR)
if _app_dir_str not in sys.path:
    sys.path.insert(0, _app_dir_str)

from _bootstrap import bootstrap_project_path

bootstrap_project_path()

import pandas as pd
import streamlit as st

from components.charts import bar_chart, donut_chart, line_chart
from components.filters import render_global_filters
from components.kpi_cards import render_kpi_cards
from components.tables import show_table
from components.theme import apply_page_theme, page_header, section_header
from data_access import get_dashboard_bundle, get_dashboard_filter_options
from demoagro.services.dashboard_data import build_sales_customer_view, get_sales_period

apply_page_theme("Ventas")
page_header(
    "Ventas",
    "Performance comercial por periodo, producto y cliente sobre facturacion real del ERP simulado.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options())

sales_period = get_sales_period(bundle, filters)
sales_customer = build_sales_customer_view(bundle, filters)

avg_price = (
    sales_period["revenue_net"].sum() / sales_period["sold_tons"].sum()
    if not sales_period.empty and sales_period["sold_tons"].sum() > 0
    else 0.0
)
active_clients = int(sales_customer["client_name"].nunique()) if not sales_customer.empty else 0
top_client_share = float(sales_customer.iloc[0]["revenue_share_pct"]) if not sales_customer.empty else 0.0
active_products = int(sales_period["product_name"].nunique()) if not sales_period.empty else 0
avg_monthly_revenue = (
    float(sales_period.groupby("period_id")["revenue_net"].sum().mean())
    if not sales_period.empty
    else 0.0
)

product_mix = (
    sales_period.groupby("product_name", as_index=False)
    .agg(
        revenue_net=("revenue_net", "sum"),
        sold_tons=("sold_tons", "sum"),
        avg_unit_price=("avg_unit_price", "mean"),
        invoice_lines=("invoice_lines", "sum"),
    )
    .sort_values("revenue_net", ascending=False)
    if not sales_period.empty
    else pd.DataFrame(columns=["product_name", "revenue_net", "sold_tons", "avg_unit_price", "invoice_lines"])
)
top_product_share = (
    float(product_mix.iloc[0]["revenue_net"] / product_mix["revenue_net"].sum())
    if not product_mix.empty and product_mix["revenue_net"].sum() > 0
    else 0.0
)

client_mix = sales_customer[["client_name", "revenue_net"]].copy()
if len(client_mix) > 5:
    other_revenue = float(client_mix.iloc[5:]["revenue_net"].sum())
    client_mix = pd.concat(
        [
            client_mix.head(5),
            pd.DataFrame([{"client_name": "Otros", "revenue_net": other_revenue}]),
        ],
        ignore_index=True,
    )
volume_mix = product_mix[["product_name", "sold_tons"]].copy() if not product_mix.empty else pd.DataFrame(columns=["product_name", "sold_tons"])
invoice_mix = product_mix[["product_name", "invoice_lines"]].copy() if not product_mix.empty else pd.DataFrame(columns=["product_name", "invoice_lines"])

cards = [
    {
        "label": "Revenue neto",
        "value": float(sales_period["revenue_net"].sum()) if not sales_period.empty else 0.0,
        "format": "currency",
        "detail": f"Promedio mensual: USD {avg_monthly_revenue:,.0f}",
        "tone": "neutral",
    },
    {
        "label": "Volumen vendido",
        "value": float(sales_period["sold_tons"].sum()) if not sales_period.empty else 0.0,
        "format": "tons",
        "detail": "Toneladas facturadas",
        "tone": "neutral",
    },
    {
        "label": "Precio promedio",
        "value": float(avg_price),
        "format": "currency",
        "detail": "USD por tonelada",
        "tone": "success",
    },
    {
        "label": "Clientes activos",
        "value": float(active_clients),
        "format": "integer",
        "detail": f"Productos activos: {active_products}",
        "tone": "neutral",
    },
    {
        "label": "Top cliente",
        "value": float(top_client_share),
        "format": "percent",
        "detail": "Participacion del principal cliente",
        "tone": "warning" if top_client_share > 0.3 else "success",
    },
    {
        "label": "Top producto",
        "value": float(top_product_share),
        "format": "percent",
        "detail": "Participacion del principal producto",
        "tone": "warning" if top_product_share > 0.45 else "neutral",
    },
]
render_kpi_cards(cards, columns=3)

row_one_left, row_one_right = st.columns(2)

with row_one_left:
    section_header("Revenue por periodo", "Mezcla comercial por producto a lo largo del tiempo.")
    if sales_period.empty:
        st.info("No hay ventas para la seleccion actual.")
    else:
        st.plotly_chart(
            bar_chart(sales_period, x="period_id", y="revenue_net", color="product_name", barmode="stack"),
            width="stretch",
        )

with row_one_right:
    section_header("Mix comercial", "Participacion de revenue por producto dentro del rango visible.")
    if product_mix.empty:
        st.info("No hay mix comercial para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(product_mix, names="product_name", values="revenue_net"),
            width="stretch",
        )

row_two_left, row_two_right = st.columns(2)

with row_two_left:
    section_header("Precio promedio por periodo", "Lectura de pricing realizado por producto.")
    if sales_period.empty:
        st.info("No hay datos comerciales para la seleccion actual.")
    else:
        st.plotly_chart(
            line_chart(sales_period, x="period_id", y="avg_unit_price", color="product_name"),
            width="stretch",
        )

with row_two_right:
    section_header("Clientes principales", "Ranking de revenue por cliente.")
    top_clients = sales_customer.head(10)[["client_name", "revenue_net", "revenue_share_pct"]].copy()
    if top_clients.empty:
        st.info("No hay clientes para la seleccion actual.")
    else:
        st.plotly_chart(
            bar_chart(top_clients, x="client_name", y="revenue_net", horizontal=True),
            width="stretch",
        )

row_three_left, row_three_right = st.columns(2)

with row_three_left:
    section_header("Concentracion de clientes", "Peso relativo de los principales compradores visibles.")
    if client_mix.empty:
        st.info("No hay concentracion para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(client_mix, names="client_name", values="revenue_net"),
            width="stretch",
        )

with row_three_right:
    section_header("Productos mas rentables en precio", "Comparativo de precio realizado por producto.")
    if product_mix.empty:
        st.info("No hay productos para mostrar.")
    else:
        product_rank = product_mix[["product_name", "avg_unit_price"]].head(8)
        st.plotly_chart(
            bar_chart(product_rank, x="product_name", y="avg_unit_price", horizontal=True),
            width="stretch",
        )

row_four_left, row_four_right = st.columns(2)

with row_four_left:
    section_header("Mix por volumen", "Participacion del volumen vendido por producto.")
    if volume_mix.empty:
        st.info("No hay volumen vendido para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(volume_mix, names="product_name", values="sold_tons"),
            width="stretch",
        )

with row_four_right:
    section_header("Mix por lineas facturadas", "Peso relativo de cada producto en la cantidad de lineas emitidas.")
    if invoice_mix.empty:
        st.info("No hay lineas facturadas para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(invoice_mix, names="product_name", values="invoice_lines"),
            width="stretch",
        )

table_left, table_right = st.columns(2)

with table_left:
    section_header("Base comercial por cliente", "Tabla complementaria del ranking de clientes principales.")
    customer_table = sales_customer[
        ["client_name", "revenue_net", "sold_tons", "avg_unit_price", "invoice_count", "revenue_share_pct", "last_invoice_date"]
    ].copy()
    show_table(customer_table.round(2), height=360)

with table_right:
    section_header("Base comercial por producto", "Tabla complementaria del mix, volumen y pricing por producto.")
    product_table = product_mix[
        ["product_name", "revenue_net", "sold_tons", "avg_unit_price", "invoice_lines"]
    ].copy()
    show_table(product_table.round(2), height=360)
