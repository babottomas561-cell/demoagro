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
from components.tables import render_alerts, show_table
from components.theme import apply_page_theme, page_header, section_header
from data_access import get_dashboard_bundle, get_dashboard_filter_options, get_dashboard_snapshot_metadata
from demoagro.services.quality_supply_data import (
    build_procurement_category_summary,
    build_quality_grade_summary,
    build_quality_product_summary,
    build_quality_supply_alerts,
    build_quality_supply_overview,
    build_supplier_summary,
    get_procurement_period,
    get_quality_period,
)

apply_page_theme("Calidad y Abastecimiento")
page_header(
    "Calidad y abastecimiento",
    "Lectura ejecutiva del aseguramiento de calidad y del circuito de compras: volumen analizado, castigos comerciales, gasto y tiempos de abastecimiento.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options(), get_dashboard_snapshot_metadata())

quality_period = get_quality_period(bundle, filters)
quality_products = build_quality_product_summary(bundle, filters)
quality_grades = build_quality_grade_summary(bundle, filters)
procurement_period = get_procurement_period(bundle, filters)
procurement_categories = build_procurement_category_summary(bundle, filters)
suppliers = build_supplier_summary(bundle, filters)
alerts = build_quality_supply_alerts(bundle, filters)

tons_analyzed = float(quality_period["tons_analyzed"].sum()) if not quality_period.empty else 0.0
avg_impurity = (
    float((quality_period["avg_impurity_pct"] * quality_period["tons_analyzed"]).sum() / tons_analyzed)
    if tons_analyzed > 0
    else 0.0
)
invoice_count = float(procurement_period["invoice_count"].sum()) if not procurement_period.empty else 0.0
avg_payment_term = (
    float((procurement_period["avg_payment_term_days"] * procurement_period["invoice_count"]).sum() / invoice_count)
    if invoice_count > 0
    else 0.0
)
top_supplier_share = float(suppliers.iloc[0]["spend_share_pct"]) if not suppliers.empty else 0.0
supplier_group_mix = (
    suppliers.groupby("supplier_group", as_index=False).agg(spend_net=("spend_net", "sum")).sort_values("spend_net", ascending=False)
    if not suppliers.empty
    else pd.DataFrame(columns=["supplier_group", "spend_net"])
)
quality_product_mix = (
    quality_products[["product_name", "tons_analyzed"]].copy()
    if not quality_products.empty
    else pd.DataFrame(columns=["product_name", "tons_analyzed"])
)

cards = build_quality_supply_overview(bundle, filters)
cards.extend(
    [
        {
            "label": "Impureza promedio",
            "value": avg_impurity,
            "format": "number",
            "detail": "Promedio ponderado por volumen",
            "tone": "warning" if avg_impurity > 2.0 else "neutral",
        },
        {
            "label": "Plazo medio de pago",
            "value": avg_payment_term,
            "format": "number",
            "detail": f"Top supplier share: {top_supplier_share:.1%}",
            "tone": "neutral",
        },
    ]
)
render_kpi_cards(cards, columns=4)

top_left, top_right = st.columns([1.45, 1.0])

with top_left:
    section_header("Pulso de calidad", "Humedad, castigo/bonificacion y volumen analizado por periodo.")
    if quality_period.empty:
        st.info("No hay analisis de calidad para el filtro seleccionado.")
    else:
        quality_trend = quality_period[
            ["period_id", "avg_humidity_pct", "avg_bonus_unit", "tons_analyzed"]
        ].melt(id_vars="period_id", var_name="metric", value_name="amount")
        st.plotly_chart(
            line_chart(quality_trend, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

with top_right:
    section_header("Alertas", "Desvios comerciales y de abastecimiento que merecen seguimiento.")
    render_alerts(alerts)

middle_left, middle_right = st.columns(2)

with middle_left:
    section_header("Pulso de compras", "Gasto neto, lead time y términos de pago visibles.")
    if procurement_period.empty:
        st.info("No hay compras para el filtro seleccionado.")
    else:
        procurement_trend = procurement_period[
            ["period_id", "spend_net", "avg_lead_time_days", "avg_payment_term_days"]
        ].melt(id_vars="period_id", var_name="metric", value_name="amount")
        st.plotly_chart(
            line_chart(procurement_trend, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

with middle_right:
    section_header("Mix de compra", "Peso relativo por categoria de abastecimiento.")
    if procurement_categories.empty:
        st.info("No hay categorias de compra para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(procurement_categories, names="category_code", values="spend_net"),
            width="stretch",
        )

row_three_left, row_three_right = st.columns(2)

with row_three_left:
    section_header("Categorias de compra", "Ranking de gasto por categoria de abastecimiento.")
    if procurement_categories.empty:
        st.info("No hay categorias de compra para mostrar.")
    else:
        st.plotly_chart(
            bar_chart(procurement_categories, x="category_code", y="spend_net", color="category_code"),
            width="stretch",
        )

with row_three_right:
    section_header("Mix de calidad", "Distribucion del volumen analizado por grado comercial.")
    if quality_grades.empty:
        st.info("No hay mix de calidad para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(quality_grades, names="grado_comercial", values="tons_analyzed"),
            width="stretch",
        )

bottom_left, bottom_right = st.columns(2)

with bottom_left:
    section_header("Calidad por producto", "Volumen, humedad y ajuste comercial promedio.")
    if quality_products.empty:
        st.info("No hay calidad por producto para mostrar.")
    else:
        product_chart = quality_products[["product_name", "tons_analyzed", "avg_bonus_unit"]].head(8)
        st.plotly_chart(
            bar_chart(product_chart, x="product_name", y="tons_analyzed", horizontal=True),
            width="stretch",
        )

with bottom_right:
    section_header("Mix de proveedores", "Participacion del gasto por grupo de proveedor.")
    if supplier_group_mix.empty:
        st.info("No hay grupos de proveedor para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(supplier_group_mix, names="supplier_group", values="spend_net"),
            width="stretch",
        )

row_four_left, row_four_right = st.columns(2)

with row_four_left:
    section_header("Mix de calidad por producto", "Participacion del volumen analizado por producto.")
    if quality_product_mix.empty:
        st.info("No hay productos de calidad para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(quality_product_mix, names="product_name", values="tons_analyzed"),
            width="stretch",
        )

with row_four_right:
    section_header("Calidad por producto", "Tabla complementaria del mix de volumen analizado.")
    quality_mix_table = quality_products[
        ["product_name", "tons_analyzed", "avg_humidity_pct", "avg_bonus_unit"]
    ].copy()
    show_table(quality_mix_table.round(2), height=260)

supplier_left, supplier_right = st.columns(2)

with supplier_left:
    section_header("Proveedores principales", "Concentracion de gasto y lead time medio por proveedor.")
    if suppliers.empty:
        st.info("No hay proveedores para mostrar.")
    else:
        supplier_chart = suppliers[["supplier_name", "spend_net"]].head(8)
        st.plotly_chart(
            bar_chart(supplier_chart, x="supplier_name", y="spend_net", horizontal=True),
            width="stretch",
        )

with supplier_right:
    section_header("Lotes por grado", "Distribucion del volumen analizado por grado comercial.")
    show_table(quality_grades.round(2), height=320)

table_left, table_middle, table_right = st.columns([1.0, 0.85, 1.15])

with table_left:
    section_header("Calidad por producto", "Detalle de humedad, impurezas y share grado 1.")
    quality_table = quality_products[
        ["product_name", "tons_analyzed", "avg_humidity_pct", "avg_impurity_pct", "avg_bonus_unit", "grade_one_share"]
    ].copy()
    show_table(quality_table.round(2), height=320)

with table_middle:
    section_header("Abastecimiento por proveedor", "Gasto, lead time y participación de compra.")
    supplier_table = suppliers[
        ["supplier_name", "supplier_group", "invoice_count", "spend_net", "avg_lead_time_days", "spend_share_pct"]
    ].copy()
    show_table(supplier_table.round(2), height=320)

with table_right:
    section_header("Compras por categoria", "Mix, lead time y peso relativo por categoria.")
    category_table = procurement_categories[
        ["category_code", "invoice_count", "spend_net", "avg_lead_time_days", "spend_share_pct"]
    ].copy()
    show_table(category_table.round(2), height=320)
