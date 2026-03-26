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

from components.charts import bar_chart, donut_chart, line_chart, scatter_chart
from components.filters import render_global_filters
from components.kpi_cards import render_kpi_cards
from components.tables import show_table
from components.theme import apply_page_theme, page_header, section_header
from data_access import get_dashboard_bundle, get_dashboard_filter_options
from demoagro.services.dashboard_data import (
    build_product_overview,
    build_sales_customer_view,
    get_operations_lot_campaign,
    get_sales_period,
    get_stock_snapshot,
)

apply_page_theme("Analisis por Producto")
page_header(
    "Analisis por producto/cultivo",
    "Cruce entre produccion, ventas y stock para leer cada cultivo como mini unidad de negocio.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options())

product_overview = build_product_overview(bundle, filters)
operations_lot = get_operations_lot_campaign(bundle, filters)
sales_period = get_sales_period(bundle, filters)

if product_overview.empty:
    st.info("No hay productos para analizar con el filtro actual.")
    st.stop()

product_options = product_overview["product_code"].tolist()
selected_product = st.selectbox("Producto foco", product_options)

selected_overview = product_overview.loc[product_overview["product_code"] == selected_product].iloc[0]
product_sales_period = sales_period.loc[sales_period["product_code"] == selected_product].copy()
product_lots = operations_lot.loc[operations_lot["product_code"] == selected_product].copy()
product_filters = dict(filters)
product_filters["products"] = [selected_product]
product_customers = build_sales_customer_view(bundle, product_filters)
product_stock = get_stock_snapshot(bundle, product_filters)

visible_volume = float(selected_overview["sold_tons"] + selected_overview["stock_qty"])
sell_out_share = (
    float(selected_overview["sold_tons"] / visible_volume)
    if visible_volume > 0
    else 0.0
)
avg_sale_price = (
    float(selected_overview["revenue_net"] / selected_overview["sold_tons"])
    if float(selected_overview["sold_tons"]) > 0
    else 0.0
)
volume_bridge = pd.DataFrame(
    [
        {"concepto": "Vendido", "tons": float(selected_overview["sold_tons"])},
        {"concepto": "Stock actual", "tons": float(selected_overview["stock_qty"])},
    ]
)
unassigned_volume = max(
    float(selected_overview["harvested_tons"]) - float(selected_overview["sold_tons"]) - float(selected_overview["stock_qty"]),
    0.0,
)
if unassigned_volume > 0:
    volume_bridge = pd.concat(
        [volume_bridge, pd.DataFrame([{"concepto": "Otro destino", "tons": unassigned_volume}])],
        ignore_index=True,
    )

campaign_mix = (
    product_lots.groupby("campaign_code", as_index=False)
    .agg(
        toneladas_netas=("toneladas_netas", "sum"),
        gross_output_value=("gross_output_value", "sum"),
    )
    .sort_values("toneladas_netas", ascending=False)
    if not product_lots.empty
    else pd.DataFrame(columns=["campaign_code", "toneladas_netas", "gross_output_value"])
)
customer_mix = product_customers[["client_name", "revenue_net"]].copy() if not product_customers.empty else pd.DataFrame(columns=["client_name", "revenue_net"])
if len(customer_mix) > 5:
    customer_mix = pd.concat(
        [
            customer_mix.head(5),
            pd.DataFrame([{"client_name": "Otros", "revenue_net": float(customer_mix.iloc[5:]["revenue_net"].sum())}]),
        ],
        ignore_index=True,
    )
stock_location_mix = (
    product_stock.groupby("deposit_name", as_index=False).agg(stock_value=("stock_value", "sum")).sort_values("stock_value", ascending=False)
    if not product_stock.empty
    else pd.DataFrame(columns=["deposit_name", "stock_value"])
)
volume_period = (
    product_sales_period[["period_id", "sold_tons"]].rename(columns={"sold_tons": "amount"})
    if not product_sales_period.empty
    else pd.DataFrame(columns=["period_id", "amount"])
)
lot_rank = (
    product_lots[["lot_name", "gross_output_value", "actual_yield_tn_ha", "cost_per_ton"]]
    .sort_values("gross_output_value", ascending=False)
    .head(8)
    if not product_lots.empty
    else pd.DataFrame(columns=["lot_name", "gross_output_value", "actual_yield_tn_ha", "cost_per_ton"])
)

cards = [
    {
        "label": "Produccion neta",
        "value": float(selected_overview["harvested_tons"]),
        "format": "tons",
        "detail": "Toneladas cosechadas",
        "tone": "neutral",
    },
    {
        "label": "Volumen vendido",
        "value": float(selected_overview["sold_tons"]),
        "format": "tons",
        "detail": "Toneladas facturadas",
        "tone": "neutral",
    },
    {
        "label": "Stock actual",
        "value": float(selected_overview["stock_qty"]),
        "format": "number",
        "detail": "Saldo disponible en snapshot",
        "tone": "warning",
    },
    {
        "label": "Sell out visible",
        "value": sell_out_share,
        "format": "percent",
        "detail": "Vendido sobre volumen visible",
        "tone": "success" if sell_out_share >= 0.6 else "warning",
    },
    {
        "label": "Revenue neto",
        "value": float(selected_overview["revenue_net"]),
        "format": "currency",
        "detail": "Ventas del producto en el rango visible",
        "tone": "success",
    },
    {
        "label": "Precio realizado",
        "value": avg_sale_price,
        "format": "currency",
        "detail": "USD por tonelada vendida",
        "tone": "success",
    },
    {
        "label": "Costo directo por tn",
        "value": float(selected_overview["direct_cost_per_ton"]),
        "format": "currency",
        "detail": "Base agricola de produccion",
        "tone": "neutral",
    },
    {
        "label": "Valor bruto visible",
        "value": float(selected_overview["gross_output_value"]),
        "format": "currency",
        "detail": "Valor bruto de produccion del producto",
        "tone": "neutral",
    },
]
render_kpi_cards(cards, columns=4)

row_one_left, row_one_right = st.columns(2)

with row_one_left:
    section_header("Revenue por periodo", "Evolucion comercial del producto seleccionado.")
    if product_sales_period.empty:
        st.info("No hay ventas para este producto en el filtro actual.")
    else:
        st.plotly_chart(
            line_chart(product_sales_period, x="period_id", y="revenue_net"),
            width="stretch",
        )

with row_one_right:
    section_header("Destino del volumen", "Distribucion visible entre venta, stock y otros destinos.")
    if volume_bridge.empty or float(volume_bridge["tons"].sum()) == 0:
        st.info("No hay volumen visible para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(volume_bridge, names="concepto", values="tons"),
            width="stretch",
        )

row_two_left, row_two_right = st.columns(2)

with row_two_left:
    section_header("Volumen por periodo", "Segunda serie temporal para leer cuándo se materializa la salida comercial del producto.")
    if volume_period.empty:
        st.info("No hay volumen vendido por periodo para este producto.")
    else:
        st.plotly_chart(
            line_chart(volume_period, x="period_id", y="amount"),
            width="stretch",
        )

with row_two_right:
    section_header("Mix de clientes", "Participacion del revenue visible por cliente comprador del producto.")
    if customer_mix.empty:
        st.info("No hay clientes para este producto.")
    else:
        st.plotly_chart(
            donut_chart(customer_mix, names="client_name", values="revenue_net"),
            width="stretch",
        )

row_three_left, row_three_right = st.columns(2)

with row_three_left:
    section_header("Lotes del producto", "Ranking por valor bruto generado.")
    if lot_rank.empty:
        st.info("No hay lotes productivos para este producto.")
    else:
        st.plotly_chart(
            bar_chart(lot_rank, x="lot_name", y="gross_output_value", horizontal=True),
            width="stretch",
        )

with row_three_right:
    section_header("Mapa de lotes", "Rendimiento real versus costo por tonelada para el cultivo.")
    if product_lots.empty:
        st.info("No hay lotes productivos para este producto.")
    else:
        st.plotly_chart(
            scatter_chart(
                product_lots,
                x="actual_yield_tn_ha",
                y="cost_per_ton",
                color="campaign_code",
                size="sown_hectares",
                hover_name="lot_name",
            ),
            width="stretch",
        )

row_four_left, row_four_right = st.columns(2)

with row_four_left:
    section_header("Mix por campaña", "Participacion del volumen cosechado por campaña.")
    if campaign_mix.empty:
        st.info("No hay campañas para este producto.")
    else:
        st.plotly_chart(
            donut_chart(campaign_mix, names="campaign_code", values="toneladas_netas"),
            width="stretch",
        )

with row_four_right:
    section_header("Valor por campaña", "Comparativo de valor bruto generado entre campañas.")
    if campaign_mix.empty:
        st.info("No hay campañas para este producto.")
    else:
        st.plotly_chart(
            bar_chart(campaign_mix, x="campaign_code", y="gross_output_value", color="campaign_code"),
            width="stretch",
        )

row_five_left, row_five_right = st.columns(2)

with row_five_left:
    section_header("Mix de stock por deposito", "Participacion del stock visible del producto por ubicacion.")
    if stock_location_mix.empty:
        st.info("No hay stock de este producto para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(stock_location_mix, names="deposit_name", values="stock_value"),
            width="stretch",
        )

with row_five_right:
    section_header("Clientes del producto", "Tabla complementaria del mix comercial por cliente.")
    customer_table = product_customers[
        ["client_name", "revenue_net", "sold_tons", "avg_unit_price", "invoice_count", "revenue_share_pct"]
    ].copy()
    show_table(customer_table.round(2), height=320)

table_left, table_right = st.columns(2)

with table_left:
    section_header("Lotes del producto", "Detalle operativo del cultivo seleccionado.")
    product_lot_table = product_lots[
        [
            "campaign_code",
            "lot_name",
            "sown_hectares",
            "actual_yield_tn_ha",
            "yield_vs_target_pct",
            "toneladas_netas",
            "cost_per_ton",
            "gross_output_value",
        ]
    ].copy()
    product_lot_table = product_lot_table.sort_values(["yield_vs_target_pct", "gross_output_value"], ascending=[True, False])
    show_table(product_lot_table.round(2), height=360)

with table_right:
    section_header("Stock del producto", "Tabla complementaria del mix de stock por deposito.")
    stock_table = product_stock[
        ["deposit_name", "deposit_type", "quantity", "stock_value", "stock_value_share_pct"]
    ].copy()
    show_table(stock_table.round(2), height=360)
