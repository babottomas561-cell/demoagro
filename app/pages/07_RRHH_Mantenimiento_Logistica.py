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
from demoagro.services.support_ops_data import (
    build_logistics_mode_summary,
    build_maintenance_asset_summary,
    build_payroll_category_summary,
    build_payroll_center_summary,
    build_support_alerts,
    build_support_overview,
    build_transporter_summary,
    get_logistics_period,
    get_maintenance_period,
    get_payroll_period,
)

apply_page_theme("RRHH Mantenimiento y Logistica")
page_header(
    "RRHH, mantenimiento y logistica",
    "Capa de soporte del ERP: costo laboral, confiabilidad de activos y desempeño logistico en una sola lectura ejecutiva.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options(), get_dashboard_snapshot_metadata())

payroll = get_payroll_period(bundle, filters)
payroll_centers = build_payroll_center_summary(bundle, filters)
payroll_categories = build_payroll_category_summary(bundle, filters)
maintenance = get_maintenance_period(bundle, filters)
maintenance_assets = build_maintenance_asset_summary(bundle, filters)
logistics = get_logistics_period(bundle, filters)
logistics_modes = build_logistics_mode_summary(bundle, filters)
transporters = build_transporter_summary(bundle, filters)
alerts = build_support_alerts(bundle, filters)

avg_headcount = float(payroll["headcount"].mean()) if not payroll.empty else 0.0
corrective_share = (
    float(maintenance["corrective_orders"].sum() / maintenance["order_count"].sum())
    if not maintenance.empty and maintenance["order_count"].sum() > 0
    else 0.0
)
logistics_cost_per_ton = (
    float(logistics["total_cost"].sum() / logistics["tons_moved"].sum())
    if not logistics.empty and logistics["tons_moved"].sum() > 0
    else 0.0
)

payroll_mix = payroll_categories[["category_name", "payroll_total"]].copy()
maintenance_mix = pd.DataFrame(
    [
        {"work_type": "Preventivo", "orders": float(maintenance["preventive_orders"].sum()) if not maintenance.empty else 0.0},
        {"work_type": "Correctivo", "orders": float(maintenance["corrective_orders"].sum()) if not maintenance.empty else 0.0},
    ]
)
logistics_mode_mix = logistics_modes[["mode", "total_cost"]].copy()
support_cost_mix = pd.DataFrame(
    [
        {"concepto": "RRHH", "amount": float(payroll["payroll_total"].sum()) if not payroll.empty else 0.0},
        {"concepto": "Mantenimiento", "amount": float(maintenance["total_cost"].sum()) if not maintenance.empty else 0.0},
        {"concepto": "Logistica", "amount": float(logistics["total_cost"].sum()) if not logistics.empty else 0.0},
    ]
)
support_cost_mix = support_cost_mix.loc[support_cost_mix["amount"] > 0].reset_index(drop=True)

cards = build_support_overview(bundle, filters)
cards.extend(
    [
        {
            "label": "Dotacion media",
            "value": avg_headcount,
            "format": "number",
            "detail": "Headcount promedio del rango visible",
            "tone": "neutral",
        },
        {
            "label": "Share correctivo",
            "value": corrective_share,
            "format": "percent",
            "detail": "Ordenes correctivas sobre el total",
            "tone": "warning" if corrective_share > 0.12 else "success",
        },
        {
            "label": "Costo logistico por tn",
            "value": logistics_cost_per_ton,
            "format": "currency",
            "detail": "Costo medio visible de traslado",
            "tone": "neutral",
        },
    ]
)
render_kpi_cards(cards, columns=3)

top_left, top_right = st.columns([1.45, 1.0])

with top_left:
    section_header("Pulso laboral", "Costo laboral, neto pagado y carga extra del periodo visible.")
    if payroll.empty:
        st.info("No hay liquidaciones para el filtro seleccionado.")
    else:
        payroll_trend = payroll[
            ["period_id", "payroll_total", "net_salary", "extra_amount"]
        ].melt(id_vars="period_id", var_name="metric", value_name="amount")
        st.plotly_chart(
            line_chart(payroll_trend, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

with top_right:
    section_header("Alertas de soporte", "Senales operativas que conviene seguir de cerca.")
    render_alerts(alerts)

row_one_left, row_one_right = st.columns(2)

with row_one_left:
    section_header("Costo laboral por centro", "Donde se concentra la carga salarial del rango visible.")
    if payroll_centers.empty:
        st.info("No hay centros de costo para mostrar.")
    else:
        chart_data = payroll_centers[["center_name", "payroll_total"]].head(8)
        st.plotly_chart(
            bar_chart(chart_data, x="center_name", y="payroll_total", horizontal=True),
            width="stretch",
        )

with row_one_right:
    section_header("Mix salarial", "Participacion del costo laboral por categoria.")
    if payroll_mix.empty:
        st.info("No hay mix salarial para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(payroll_mix, names="category_name", values="payroll_total"),
            width="stretch",
        )

row_one_bis_left, row_one_bis_right = st.columns(2)

with row_one_bis_left:
    section_header("Mix total de soporte", "Participacion relativa de RRHH, mantenimiento y logistica dentro del costo de soporte.")
    if support_cost_mix.empty:
        st.info("No hay costo de soporte para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(support_cost_mix, names="concepto", values="amount"),
            width="stretch",
        )

with row_one_bis_right:
    section_header("Costo soporte por capa", "Tabla complementaria del mix total de soporte.")
    show_table(support_cost_mix.round(2), height=220)

row_two_left, row_two_right = st.columns(2)

with row_two_left:
    section_header("Mantenimiento por periodo", "Costo total, horas de parada y perfil preventivo/correctivo.")
    if maintenance.empty:
        st.info("No hay ordenes de trabajo para el filtro seleccionado.")
    else:
        maintenance_trend = maintenance[
            ["period_id", "total_cost", "downtime_hours", "corrective_orders"]
        ].melt(id_vars="period_id", var_name="metric", value_name="amount")
        st.plotly_chart(
            line_chart(maintenance_trend, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

with row_two_right:
    section_header("Mix de mantenimiento", "Participacion de ordenes preventivas y correctivas.")
    if float(maintenance_mix["orders"].sum()) == 0.0:
        st.info("No hay mix de mantenimiento para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(maintenance_mix, names="work_type", values="orders"),
            width="stretch",
        )

row_three_left, row_three_right = st.columns(2)

with row_three_left:
    section_header("Activos con mayor carga", "Equipos que concentran costo y paradas.")
    if maintenance_assets.empty:
        st.info("No hay activos para mostrar.")
    else:
        asset_chart = maintenance_assets[["asset_name", "total_cost"]].head(8)
        st.plotly_chart(
            bar_chart(asset_chart, x="asset_name", y="total_cost", horizontal=True),
            width="stretch",
        )

with row_three_right:
    section_header("Logistica por periodo", "Costo, toneladas movidas y dependencia tercerizada.")
    if logistics.empty:
        st.info("No hay viajes para el filtro seleccionado.")
    else:
        logistics_trend = logistics[
            ["period_id", "total_cost", "tons_moved", "third_party_cost"]
        ].melt(id_vars="period_id", var_name="metric", value_name="amount")
        st.plotly_chart(
            line_chart(logistics_trend, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

row_four_left, row_four_right = st.columns(2)

with row_four_left:
    section_header("Transportistas principales", "Costo total visible por operador logistico.")
    if transporters.empty:
        st.info("No hay transportistas para mostrar.")
    else:
        transporter_chart = transporters[["transporter_name", "total_cost"]].head(8)
        st.plotly_chart(
            bar_chart(transporter_chart, x="transporter_name", y="total_cost", horizontal=True),
            width="stretch",
        )

with row_four_right:
    section_header("Mix logistico", "Comparativo de modo propio vs tercerizado.")
    if logistics_mode_mix.empty:
        st.info("No hay mix logistico para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(logistics_mode_mix, names="mode", values="total_cost"),
            width="stretch",
        )

table_left, table_middle, table_right = st.columns([1.0, 1.05, 1.1])

with table_left:
    section_header("RRHH por categoria", "Dotacion, costo y horas extra por perfil.")
    category_table = payroll_categories[
        ["category_name", "headcount", "payroll_total", "avg_gross_salary", "extra_hours"]
    ].copy()
    show_table(category_table.round(2), height=340)

with table_middle:
    section_header("Activos con mayor carga", "Equipos que concentran costo y paradas.")
    asset_table = maintenance_assets[
        ["asset_name", "asset_type", "order_count", "corrective_orders", "downtime_hours", "total_cost"]
    ].copy()
    show_table(asset_table.round(2), height=340)

with table_right:
    section_header("Transportistas y viajes", "Costo y volumen movido por operador.")
    transporter_table = transporters[
        ["transporter_name", "mode", "trip_count", "tons_moved", "cost_per_ton", "total_cost"]
    ].copy()
    show_table(transporter_table.round(2), height=340)
