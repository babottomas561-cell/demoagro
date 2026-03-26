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
from data_access import get_dashboard_bundle, get_dashboard_filter_options, get_dashboard_snapshot_metadata
from demoagro.services.dashboard_data import (
    build_stock_uom_summary,
    get_operations_period,
    get_sales_period,
    get_stock_snapshot,
)
from demoagro.services.quality_supply_data import get_procurement_period

apply_page_theme("Stock")
page_header(
    "Stock",
    "Inventario valorizado y snapshot actual del ERP simulado, con foco en capital inmovilizado y composicion.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options(), get_dashboard_snapshot_metadata())
snapshot_info = get_dashboard_snapshot_metadata(filters)

stock = get_stock_snapshot(bundle, filters)
stock_uom = build_stock_uom_summary(bundle, filters)
operations_period = get_operations_period(bundle, filters)
sales_period = get_sales_period(bundle, filters)
procurement_period = get_procurement_period(bundle, filters)

top_share = float(stock.iloc[0]["stock_value_share_pct"]) if not stock.empty else 0.0
uom_count = int(stock["uom_code"].nunique()) if not stock.empty else 0
product_count = int(stock["product_code"].nunique()) if not stock.empty else 0
position_count = int(stock["stock_actual_id"].nunique()) if not stock.empty else 0
deposit_count = int(stock["deposit_name"].nunique()) if not stock.empty else 0
single_uom = stock["uom_code"].dropna().iloc[0] if uom_count == 1 and not stock.empty else None
single_uom_quantity = float(stock["quantity"].sum()) if single_uom else 0.0
single_uom_avg_value = (
    float(stock["stock_value"].sum() / stock["quantity"].sum())
    if single_uom and stock["quantity"].sum() > 0
    else 0.0
)

category_mix = (
    stock.groupby("category_code", as_index=False).agg(stock_value=("stock_value", "sum")).sort_values("stock_value", ascending=False)
    if not stock.empty
    else stock.iloc[0:0]
)
deposit_rank = (
    stock.groupby("deposit_name", as_index=False).agg(stock_value=("stock_value", "sum")).sort_values("stock_value", ascending=False)
    if not stock.empty
    else stock.iloc[0:0]
)
deposit_type_mix = (
    stock.groupby("deposit_type", as_index=False).agg(stock_value=("stock_value", "sum")).sort_values("stock_value", ascending=False)
    if not stock.empty
    else stock.iloc[0:0]
)
stock_product_mix = (
    stock.groupby("product_name", as_index=False).agg(stock_value=("stock_value", "sum")).sort_values("stock_value", ascending=False)
    if not stock.empty
    else pd.DataFrame(columns=["product_name", "stock_value"])
)
if len(stock_product_mix) > 5:
    stock_product_mix = pd.concat(
        [
            stock_product_mix.head(5),
            pd.DataFrame(
                [{"product_name": "Otros", "stock_value": float(stock_product_mix.iloc[5:]["stock_value"].sum())}]
            ),
        ],
        ignore_index=True,
    )
uom_value_mix = (
    stock_uom[["uom_code", "stock_value"]].copy()
    if not stock_uom.empty
    else pd.DataFrame(columns=["uom_code", "stock_value"])
)
grain_flow_period = pd.DataFrame(columns=["period_id", "metric", "amount"])
if not operations_period.empty or not sales_period.empty:
    inflow = (
        operations_period.groupby("period_id", as_index=False).agg(production_tons=("production_tons", "sum"))
        if not operations_period.empty
        else pd.DataFrame(columns=["period_id", "production_tons"])
    )
    outflow = (
        sales_period.groupby("period_id", as_index=False).agg(sold_tons=("sold_tons", "sum"))
        if not sales_period.empty
        else pd.DataFrame(columns=["period_id", "sold_tons"])
    )
    grain_flow_period = inflow.merge(outflow, on="period_id", how="outer").fillna(0.0)
    grain_flow_period = grain_flow_period.sort_values("period_id").melt(
        id_vars="period_id",
        var_name="metric",
        value_name="amount",
    )
    grain_flow_period["metric"] = grain_flow_period["metric"].replace(
        {
            "production_tons": "Ingreso por produccion",
            "sold_tons": "Salida por ventas",
        }
    )
procurement_trend = (
    procurement_period[["period_id", "spend_net", "spend_total"]].melt(
        id_vars="period_id",
        var_name="metric",
        value_name="amount",
    )
    if not procurement_period.empty
    else pd.DataFrame(columns=["period_id", "metric", "amount"])
)
if not procurement_trend.empty:
    procurement_trend["metric"] = procurement_trend["metric"].replace(
        {
            "spend_net": "Compras netas",
            "spend_total": "Compras totales",
        }
    )
top_category_share = (
    float(category_mix.iloc[0]["stock_value"] / category_mix["stock_value"].sum())
    if len(category_mix) > 0 and float(category_mix["stock_value"].sum()) > 0
    else 0.0
)

cards = [
    {
        "label": "Stock valorizado",
        "value": float(stock["stock_value"].sum()) if not stock.empty else 0.0,
        "format": "currency",
        "detail": f"Snapshot actual: {snapshot_info['snapshot_date'] or 'sin snapshot'}",
        "tone": "neutral",
    },
    {
        "label": "Posiciones activas",
        "value": float(position_count),
        "format": "integer",
        "detail": "Filas activas del snapshot",
        "tone": "neutral",
    },
    {
        "label": "Productos con stock",
        "value": float(product_count),
        "format": "integer",
        "detail": f"Depositos activos: {deposit_count}",
        "tone": "neutral",
    },
]

if single_uom:
    cards.extend(
        [
            {
                "label": "Cantidad fisica",
                "value": single_uom_quantity,
                "format": "number",
                "detail": f"Unidad homogenea detectada: {single_uom}",
                "tone": "neutral",
            },
            {
                "label": "Valor unitario promedio",
                "value": single_uom_avg_value,
                "format": "currency",
                "detail": f"Promedio calculado solo para {single_uom}",
                "tone": "success",
            },
        ]
    )
else:
    cards.extend(
        [
            {
                "label": "UOM presentes",
                "value": float(uom_count),
                "format": "integer",
                "detail": "Cantidad de unidades de medida visibles",
                "tone": "neutral",
            },
            {
                "label": "Top categoria",
                "value": float(top_category_share),
                "format": "percent",
                "detail": "Participacion de la categoria dominante",
                "tone": "warning" if top_category_share > 0.45 else "neutral",
            },
        ]
    )

cards.append(
    {
        "label": "Concentracion top item",
        "value": float(top_share),
        "format": "percent",
        "detail": "Participacion del item de mayor valor",
        "tone": "warning" if top_share > 0.3 else "success",
    }
)
render_kpi_cards(cards, columns=3)

row_one_left, row_one_right = st.columns(2)

with row_one_left:
    section_header("Ingreso y salida fisica", "Serie temporal para leer cómo se forma y se consume el stock de granos.")
    if grain_flow_period.empty:
        st.info("No hay flujo fisico para mostrar.")
    else:
        st.plotly_chart(
            line_chart(grain_flow_period, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

with row_one_right:
    section_header("Ritmo de reposicion", "Segunda serie temporal para seguir el abastecimiento de insumos.")
    if procurement_trend.empty:
        st.info("No hay compras para mostrar como reposicion.")
    else:
        st.plotly_chart(
            line_chart(procurement_trend, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

row_two_left, row_two_right = st.columns(2)

with row_two_left:
    section_header("Posiciones mas valiosas", "Productos que hoy explican la mayor parte del capital inmovilizado.")
    if stock.empty:
        st.info("No hay stock para la seleccion actual.")
    else:
        stock_rank = stock[["product_name", "stock_value"]].groupby("product_name", as_index=False).sum()
        stock_rank = stock_rank.sort_values("stock_value", ascending=False).head(10)
        st.plotly_chart(
            bar_chart(stock_rank, x="product_name", y="stock_value", horizontal=True),
            width="stretch",
        )

with row_two_right:
    section_header("Depositos mas cargados", "Donde hoy se concentra mas valor de inventario.")
    if deposit_rank.empty:
        st.info("No hay depositos para mostrar.")
    else:
        st.plotly_chart(
            bar_chart(deposit_rank.head(8), x="deposit_name", y="stock_value", horizontal=True),
            width="stretch",
        )

row_three_left, row_three_right = st.columns(2)

with row_three_left:
    section_header("Composicion del inventario", "Participacion por categoria de producto.")
    if category_mix.empty:
        st.info("No hay composicion para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(category_mix, names="category_code", values="stock_value"),
            width="stretch",
        )

with row_three_right:
    section_header("Mix por tipo de deposito", "Peso relativo del stock por tipo de ubicacion.")
    if deposit_type_mix.empty:
        st.info("No hay tipos de deposito para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(deposit_type_mix, names="deposit_type", values="stock_value"),
            width="stretch",
        )

row_four_left, row_four_right = st.columns(2)

with row_four_left:
    section_header("Mix por producto", "Participacion de las principales posiciones dentro del valor de inventario.")
    if stock_product_mix.empty:
        st.info("No hay productos para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(stock_product_mix, names="product_name", values="stock_value"),
            width="stretch",
        )

with row_four_right:
    section_header("Mix por UOM valorizada", "Peso relativo del valor visible por unidad de medida.")
    if uom_value_mix.empty:
        st.info("No hay UOM para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(uom_value_mix, names="uom_code", values="stock_value"),
            width="stretch",
        )

row_five_left, row_five_right = st.columns(2)

with row_five_left:
    section_header("Cantidad fisica por UOM", "Las cantidades se leen por unidad de medida, no agregadas entre si.")
    if stock_uom.empty:
        st.info("No hay cantidades para mostrar.")
    else:
        st.plotly_chart(
            bar_chart(stock_uom, x="uom_code", y="quantity"),
            width="stretch",
        )

with row_five_right:
    section_header("Top productos valorizados", "Tabla complementaria del ranking de posiciones mas valiosas.")
    stock_rank_table = (
        stock.groupby(["product_name", "category_code"], as_index=False)
        .agg(stock_value=("stock_value", "sum"), quantity=("quantity", "sum"))
        .sort_values("stock_value", ascending=False)
    )
    show_table(stock_rank_table.round(2), height=260)

row_six_left, row_six_right = st.columns(2)

with row_six_left:
    section_header("Resumen por deposito", "Tabla complementaria del ranking de depositos mas cargados.")
    show_table(deposit_rank.round(2), height=260)

with row_six_right:
    section_header("Resumen por UOM", "Corte fisico y valorizado por unidad de medida.")
    show_table(stock_uom.round(2), height=260)

section_header(
    "Detalle de stock",
    f"Snapshot actual por producto, deposito y lote de calidad al {snapshot_info['snapshot_date'] or 'sin snapshot'}.",
)
stock_table = stock[
    [
        "product_name",
        "category_code",
        "uom_code",
        "deposit_name",
        "deposit_type",
        "quantity",
        "unit_value",
        "stock_value",
        "stock_value_share_pct",
    ]
].copy()
show_table(stock_table.round(2), height=420)
