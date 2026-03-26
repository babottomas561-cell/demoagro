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

from components.charts import bar_chart, combo_chart, donut_chart, line_chart, waterfall_chart
from components.filters import render_global_filters
from components.kpi_cards import render_kpi_cards
from components.panels import render_insight_panels
from components.tables import render_alerts, show_table
from components.theme import apply_page_theme, page_header, section_header
from data_access import get_dashboard_bundle, get_dashboard_filter_options, get_dashboard_snapshot_metadata
from demoagro.services.dashboard_data import (
    build_executive_alerts,
    build_product_overview,
    build_sales_customer_view,
    build_snapshot_kpis,
    get_finance_period,
    get_operations_lot_campaign,
    get_operations_period,
    get_sales_period,
    get_stock_snapshot,
    get_working_capital_overview,
)
from demoagro.services.finance_analysis import (
    build_finance_bridge,
    build_finance_cost_mix,
    build_finance_insight_panels,
    build_finance_summary_cards,
    prepare_finance_analysis,
)

apply_page_theme("Resumen Gerencial")
page_header(
    "Resumen gerencial",
    "Vista ejecutiva del ERP simulado: resultado economico, capital de trabajo, ventas, operaciones y stock en una sola lectura.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options(), get_dashboard_snapshot_metadata())
snapshot_info = get_dashboard_snapshot_metadata(filters)

finance = prepare_finance_analysis(get_finance_period(bundle, filters))
sales_customer = build_sales_customer_view(bundle, filters)
sales_period = get_sales_period(bundle, filters)
operations_period = get_operations_period(bundle, filters)
operations_lot = get_operations_lot_campaign(bundle, filters)
stock = get_stock_snapshot(bundle, filters)
product_overview = build_product_overview(bundle, filters)
working_capital = get_working_capital_overview(bundle, filters)
alerts = build_executive_alerts(bundle, filters)

flow_period = pd.DataFrame(columns=["period_id", "metric", "amount"])
if not sales_period.empty or not operations_period.empty:
    sold_by_period = (
        sales_period.groupby("period_id", as_index=False).agg(sold_tons=("sold_tons", "sum"))
        if not sales_period.empty
        else pd.DataFrame(columns=["period_id", "sold_tons"])
    )
    production_by_period = (
        operations_period.groupby("period_id", as_index=False).agg(production_tons=("production_tons", "sum"))
        if not operations_period.empty
        else pd.DataFrame(columns=["period_id", "production_tons"])
    )
    flow_period = production_by_period.merge(sold_by_period, on="period_id", how="outer").fillna(0.0)
    flow_period = flow_period.sort_values("period_id")
    flow_period = flow_period.melt(id_vars="period_id", var_name="metric", value_name="amount")
    flow_period["metric"] = flow_period["metric"].replace(
        {
            "production_tons": "Produccion neta",
            "sold_tons": "Toneladas vendidas",
        }
    )

product_mix = (
    product_overview.loc[product_overview["revenue_net"] > 0, ["product_name", "revenue_net"]]
    .sort_values("revenue_net", ascending=False)
    if not product_overview.empty
    else pd.DataFrame(columns=["product_name", "revenue_net"])
)
client_mix = sales_customer[["client_name", "revenue_net"]].copy()
if len(client_mix) > 5:
    client_mix = pd.concat(
        [
            client_mix.head(5),
            pd.DataFrame([{"client_name": "Otros", "revenue_net": float(client_mix.iloc[5:]["revenue_net"].sum())}]),
        ],
        ignore_index=True,
    )
stock_category_mix = (
    stock.groupby("category_code", as_index=False)
    .agg(stock_value=("stock_value", "sum"))
    .sort_values("stock_value", ascending=False)
    if not stock.empty
    else pd.DataFrame(columns=["category_code", "stock_value"])
)
top_clients_table = sales_customer.head(8)[
    ["client_name", "revenue_net", "sold_tons", "avg_unit_price", "revenue_share_pct"]
].copy()
top_stock_table = stock.head(8)[
    ["product_name", "category_code", "deposit_name", "quantity", "stock_value", "stock_value_share_pct"]
].copy()

section_header("Flujo del periodo", "Resultado y estructura economica afectados por la ventana temporal seleccionada.")
render_kpi_cards(build_finance_summary_cards(finance, variant="executive"), columns=3)

section_header("Lecturas gerenciales", "Highlights del resultado visible: meses clave, presión de costos y conversión a caja.")
render_insight_panels(build_finance_insight_panels(finance), columns=4)

section_header(
    "Snapshot actual",
    f"Saldos al cierre disponible del {snapshot_info['snapshot_date'] or 'sin snapshot'}.",
)
render_kpi_cards(build_snapshot_kpis(bundle, filters), columns=3)

top_left, top_right = st.columns([1.7, 1.0])

with top_left:
    section_header("Pulso economico", "Ingresos como base, con márgenes bruto y EBITDA sobre eje secundario.")
    if finance.empty:
        st.info("No hay informacion financiera para la seleccion actual.")
    else:
        st.plotly_chart(
            combo_chart(
                finance,
                x="period_id",
                bar_column="revenue_net",
                line_columns=["gross_margin_pct_calc", "ebitda_margin_pct"],
                bar_name="Ingresos netos",
                line_names={
                    "gross_margin_pct_calc": "Margen bruto %",
                    "ebitda_margin_pct": "Margen EBITDA %",
                },
                line_tickformat=".0%",
            ),
            width="stretch",
        )

with top_right:
    section_header("Alertas gerenciales", "Desvios que merecen seguimiento inmediato.")
    render_alerts(alerts)
    section_header(
        "Capital de trabajo",
        f"Corte actual de cuentas abiertas y vencidas al snapshot {snapshot_info['snapshot_date'] or 'sin snapshot'}.",
    )
    show_table(working_capital.round(2), height=180)

middle_left, middle_right = st.columns(2)

with middle_left:
    section_header("Flujo fisico", "Relacion temporal entre produccion neta y toneladas ya comercializadas.")
    if flow_period.empty:
        st.info("No hay flujo fisico para la seleccion actual.")
    else:
        st.plotly_chart(
            line_chart(flow_period, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

with middle_right:
    section_header("Puente EBITDA", "Cómo se transforma el ingreso visible en EBITDA gerencial del rango.")
    bridge = build_finance_bridge(finance)
    if bridge.empty:
        st.info("No hay resultado para construir el puente de EBITDA.")
    else:
        st.plotly_chart(
            waterfall_chart(bridge, x="concepto", y="amount", measure="measure"),
            width="stretch",
        )

donut_one_left, donut_one_right = st.columns(2)

with donut_one_left:
    section_header("Estructura de costos", "Peso relativo de costos visibles dentro del resultado operativo.")
    cost_mix = build_finance_cost_mix(finance)
    if cost_mix.empty:
        st.info("No hay costos visibles para el filtro seleccionado.")
    else:
        st.plotly_chart(
            donut_chart(cost_mix, names="concepto", values="amount"),
            width="stretch",
        )

with donut_one_right:
    section_header("Mix de revenue", "Participacion del ingreso visible por producto.")
    if product_mix.empty:
        st.info("No hay revenue por producto para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(product_mix, names="product_name", values="revenue_net"),
            width="stretch",
        )

donut_two_left, donut_two_right = st.columns(2)

with donut_two_left:
    section_header("Concentracion comercial", "Peso relativo de los principales clientes visibles.")
    if client_mix.empty:
        st.info("No hay concentracion comercial para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(client_mix, names="client_name", values="revenue_net"),
            width="stretch",
        )

with donut_two_right:
    section_header("Mix de inventario", "Participacion del capital inmovilizado por categoria.")
    if stock_category_mix.empty:
        st.info("No hay inventario para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(stock_category_mix, names="category_code", values="stock_value"),
            width="stretch",
        )

bottom_left, bottom_right = st.columns(2)

with bottom_left:
    section_header("Top clientes", "Participacion de revenue dentro del filtro actual.")
    top_clients = sales_customer.head(8)[["client_name", "revenue_net", "revenue_share_pct"]].copy()
    if top_clients.empty:
        st.info("No hay ventas para el filtro seleccionado.")
    else:
        st.plotly_chart(
            bar_chart(top_clients, x="client_name", y="revenue_net", horizontal=True),
            width="stretch",
        )

with bottom_right:
    section_header("Inventario mas valioso", "Posiciones que hoy inmovilizan mas capital.")
    top_stock = stock.head(8)[["product_name", "stock_value", "stock_value_share_pct"]].copy()
    if top_stock.empty:
        st.info("No hay stock para el filtro seleccionado.")
    else:
        st.plotly_chart(
            bar_chart(top_stock, x="product_name", y="stock_value", horizontal=True),
            width="stretch",
        )

table_left, table_right = st.columns(2)

with table_left:
    section_header("Detalle top clientes", "Tabla complementaria del ranking comercial principal.")
    show_table(top_clients_table.round(2), height=300)

with table_right:
    section_header("Detalle top stock", "Tabla complementaria de las posiciones mas valiosas.")
    show_table(top_stock_table.round(2), height=300)

section_header("Lotes para mirar", "Comparativo rapido de rendimiento, costo y valor bruto por lote.")
lot_focus = operations_lot[
    [
        "campaign_code",
        "lot_name",
        "product_name",
        "toneladas_netas",
        "actual_yield_tn_ha",
        "yield_vs_target_pct",
        "cost_per_ton",
        "gross_output_value",
    ]
].copy()
lot_focus = lot_focus.sort_values(["yield_vs_target_pct", "gross_output_value"], ascending=[True, False]).head(12)
show_table(lot_focus.round(2), height=360)
