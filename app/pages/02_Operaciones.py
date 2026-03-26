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
from demoagro.services.dashboard_data import get_operations_lot_campaign, get_operations_period

apply_page_theme("Operaciones")
page_header(
    "Operaciones",
    "Seguimiento de produccion, rendimiento, merma y costo agricola por periodo y por lote.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options())

operations_period = get_operations_period(bundle, filters)
operations_lot = get_operations_lot_campaign(bundle, filters)

total_hectares = float(operations_period["sown_hectares"].sum()) if not operations_period.empty else 0.0
production_total = float(operations_period["production_tons"].sum()) if not operations_period.empty else 0.0
direct_cost_total = float(operations_period["direct_cost_total"].sum()) if not operations_period.empty else 0.0
gross_output_total = float(operations_lot["gross_output_value"].sum()) if not operations_lot.empty else 0.0
direct_margin_total = gross_output_total - float(operations_lot["direct_cost_total"].sum()) if not operations_lot.empty else 0.0
weighted_yield = (
    (operations_period["yield_tn_ha"] * operations_period["sown_hectares"]).sum() / operations_period["sown_hectares"].sum()
    if not operations_period.empty and operations_period["sown_hectares"].sum() > 0
    else 0.0
)
weighted_shrink = (
    (operations_period["shrink_pct"] * operations_period["gross_tons"]).sum() / operations_period["gross_tons"].sum()
    if not operations_period.empty and operations_period["gross_tons"].sum() > 0
    else 0.0
)
weighted_cost = (
    operations_period["direct_cost_total"].sum() / operations_period["production_tons"].sum()
    if not operations_period.empty and operations_period["production_tons"].sum() > 0
    else 0.0
)
under_target_count = int((operations_lot["yield_vs_target_pct"] < 1.0).sum()) if not operations_lot.empty else 0
on_target_share = (
    float((operations_lot["yield_vs_target_pct"] >= 1.0).sum() / len(operations_lot))
    if not operations_lot.empty
    else 0.0
)

crop_mix = (
    operations_period.groupby("crop_code", as_index=False)
    .agg(
        production_tons=("production_tons", "sum"),
        direct_cost_total=("direct_cost_total", "sum"),
        gross_tons=("gross_tons", "sum"),
        sown_hectares=("sown_hectares", "sum"),
    )
    .sort_values("production_tons", ascending=False)
    if not operations_period.empty
    else pd.DataFrame(columns=["crop_code", "production_tons", "direct_cost_total", "gross_tons", "sown_hectares"])
)
value_mix = (
    operations_lot.groupby("crop_code", as_index=False)
    .agg(gross_output_value=("gross_output_value", "sum"))
    .sort_values("gross_output_value", ascending=False)
    if not operations_lot.empty
    else pd.DataFrame(columns=["crop_code", "gross_output_value"])
)
yield_trend = (
    operations_period[["period_id", "crop_code", "yield_tn_ha"]].copy()
    if not operations_period.empty
    else pd.DataFrame(columns=["period_id", "crop_code", "yield_tn_ha"])
)
hectare_mix = crop_mix[["crop_code", "sown_hectares"]].copy() if not crop_mix.empty else pd.DataFrame(columns=["crop_code", "sown_hectares"])

performance_mix = pd.DataFrame(columns=["performance_band", "tons"])
worst_lots = pd.DataFrame()
if not operations_lot.empty:
    performance = operations_lot.copy()
    performance["performance_band"] = performance["yield_vs_target_pct"].apply(
        lambda value: "Critico"
        if value < 0.9
        else "Bajo objetivo"
        if value < 1.0
        else "En linea"
        if value < 1.08
        else "Sobre objetivo"
    )
    performance_mix = (
        performance.groupby("performance_band", as_index=False)
        .agg(tons=("toneladas_netas", "sum"))
        .sort_values("tons", ascending=False)
    )
    worst_lots = performance[
        ["lot_name", "product_name", "yield_vs_target_pct", "cost_per_ton", "gross_output_value"]
    ].sort_values(["yield_vs_target_pct", "cost_per_ton"], ascending=[True, False]).head(10)

cards = [
    {
        "label": "Produccion neta",
        "value": production_total,
        "format": "tons",
        "detail": "Toneladas netas cosechadas",
        "tone": "neutral",
    },
    {
        "label": "Hectareas sembradas",
        "value": total_hectares,
        "format": "number",
        "detail": "Superficie visible del rango",
        "tone": "neutral",
    },
    {
        "label": "Rendimiento promedio",
        "value": float(weighted_yield),
        "format": "number",
        "detail": "tn/ha ponderado por superficie",
        "tone": "success",
    },
    {
        "label": "Merma promedio",
        "value": float(weighted_shrink),
        "format": "percent",
        "detail": "Ponderada por toneladas brutas",
        "tone": "warning",
    },
    {
        "label": "Costo directo por tn",
        "value": float(weighted_cost),
        "format": "currency",
        "detail": "Costo agricola directo",
        "tone": "neutral",
    },
    {
        "label": "Margen directo visible",
        "value": direct_margin_total,
        "format": "currency",
        "detail": f"Lotes sobre objetivo: {on_target_share:.1%}",
        "tone": "success" if direct_margin_total >= 0 else "danger",
    },
    {
        "label": "Lotes bajo objetivo",
        "value": float(under_target_count),
        "format": "integer",
        "detail": "Lotes por debajo del target",
        "tone": "warning",
    },
    {
        "label": "Costo directo total",
        "value": direct_cost_total,
        "format": "currency",
        "detail": "Desembolso agricola del rango",
        "tone": "neutral",
    },
]
render_kpi_cards(cards, columns=4)

row_one_left, row_one_right = st.columns(2)

with row_one_left:
    section_header("Produccion por periodo", "Lectura temporal de volumen neto por cultivo.")
    if operations_period.empty:
        st.info("No hay datos operativos para la seleccion actual.")
    else:
        st.plotly_chart(
            bar_chart(operations_period, x="period_id", y="production_tons", color="crop_code", barmode="stack"),
            width="stretch",
        )

with row_one_right:
    section_header("Mix productivo", "Participacion de cada cultivo en la produccion visible.")
    if crop_mix.empty:
        st.info("No hay mix productivo para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(crop_mix, names="crop_code", values="production_tons"),
            width="stretch",
        )

row_two_left, row_two_right = st.columns(2)

with row_two_left:
    section_header("Costo por cultivo", "Comparativo de desembolso agricola directo por cultivo.")
    if crop_mix.empty:
        st.info("No hay costos para la seleccion actual.")
    else:
        st.plotly_chart(
            bar_chart(crop_mix, x="crop_code", y="direct_cost_total", color="crop_code"),
            width="stretch",
        )

with row_two_right:
    section_header("Cumplimiento de objetivo", "Volumen neto clasificado por banda de performance.")
    if performance_mix.empty:
        st.info("No hay bandas de rendimiento para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(performance_mix, names="performance_band", values="tons"),
            width="stretch",
        )

row_three_left, row_three_right = st.columns(2)

with row_three_left:
    section_header("Rendimiento por periodo", "Segunda serie temporal para seguir la productividad real por cultivo.")
    if yield_trend.empty:
        st.info("No hay rendimiento por periodo para mostrar.")
    else:
        st.plotly_chart(
            line_chart(yield_trend, x="period_id", y="yield_tn_ha", color="crop_code"),
            width="stretch",
        )

with row_three_right:
    section_header("Mix de hectareas", "Participacion de superficie sembrada por cultivo.")
    if hectare_mix.empty:
        st.info("No hay hectareas para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(hectare_mix, names="crop_code", values="sown_hectares"),
            width="stretch",
        )

row_four_left, row_four_right = st.columns(2)

with row_four_left:
    section_header("Mix de valor bruto", "Participacion de cada cultivo en el valor bruto generado.")
    if value_mix.empty:
        st.info("No hay valor bruto para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(value_mix, names="crop_code", values="gross_output_value"),
            width="stretch",
        )

with row_four_right:
    section_header("Mapa de lotes", "Relacion entre rendimiento real y costo por tonelada.")
    if operations_lot.empty:
        st.info("No hay lotes para la seleccion actual.")
    else:
        st.plotly_chart(
            scatter_chart(
                operations_lot,
                x="actual_yield_tn_ha",
                y="cost_per_ton",
                color="crop_code",
                size="sown_hectares",
                hover_name="lot_name",
            ),
            width="stretch",
        )

row_five_left, row_five_right = st.columns([1.35, 1.0])

with row_five_right:
    section_header("Lotes mas exigidos", "Ranking de lotes con peor cumplimiento y mayor costo unitario.")
    if worst_lots.empty:
        st.info("No hay lotes para rankear.")
    else:
        st.plotly_chart(
            bar_chart(worst_lots, x="lot_name", y="cost_per_ton", color="product_name", horizontal=True),
            width="stretch",
        )

with row_five_left:
    section_header("Cultivos foco", "Tabla complementaria del mix productivo y de costos por cultivo.")
    crop_table = crop_mix.copy()
    if not crop_table.empty:
        crop_table["costo_por_tn"] = crop_table["direct_cost_total"] / crop_table["production_tons"].replace({0: pd.NA})
        crop_table = crop_table.fillna(0.0)
    show_table(crop_table.round(2), height=320)

section_header("Detalle por lote", "Ranking de rendimiento versus target y costo unitario.")
lot_table = operations_lot[
    [
        "campaign_code",
        "lot_name",
        "product_name",
        "sown_hectares",
        "actual_yield_tn_ha",
        "yield_vs_target_pct",
        "merma_pct",
        "cost_per_ton",
        "direct_cost_total",
        "gross_output_value",
    ]
].copy()
lot_table["direct_margin"] = lot_table["gross_output_value"] - lot_table["direct_cost_total"]
lot_table = lot_table.sort_values(["yield_vs_target_pct", "cost_per_ton"], ascending=[True, False])
show_table(lot_table.round(2), height=420)
