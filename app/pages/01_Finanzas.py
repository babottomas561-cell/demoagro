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
from components.tables import show_table
from components.theme import apply_page_theme, page_header, section_header
from data_access import get_dashboard_bundle, get_dashboard_filter_options, get_dashboard_snapshot_metadata
from demoagro.services.dashboard_data import (
    build_snapshot_kpis,
    get_ap_aging,
    get_ar_aging,
    get_finance_period,
    get_working_capital_overview,
    latest_period_value,
    summarize_aging,
)
from demoagro.services.finance_analysis import (
    build_finance_bridge,
    build_finance_cash_components,
    build_finance_cost_mix,
    build_finance_cost_trend,
    build_finance_insight_panels,
    build_finance_scorecard,
    build_finance_summary_cards,
    prepare_finance_analysis,
)

apply_page_theme("Finanzas")
page_header(
    "Finanzas",
    "Lectura de resultado, caja y capital de trabajo sobre el ERP simulado.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options(), get_dashboard_snapshot_metadata())
snapshot_info = get_dashboard_snapshot_metadata(filters)

finance = prepare_finance_analysis(get_finance_period(bundle, filters))
ar = get_ar_aging(bundle, filters)
ap = get_ap_aging(bundle, filters)
working_capital = get_working_capital_overview(bundle, filters)
latest_finance_period = finance["period_id"].max() if not finance.empty else "Sin datos"
result_vs_cash = (
    finance[["period_id", "revenue_net", "ebitda_approx", "net_cash_flow"]].melt(
        id_vars="period_id",
        var_name="concepto",
        value_name="amount",
    )
    if not finance.empty
    else pd.DataFrame(columns=["period_id", "concepto", "amount"])
)
if not result_vs_cash.empty:
    result_vs_cash["concepto"] = result_vs_cash["concepto"].replace(
        {
            "revenue_net": "Ingresos netos",
            "ebitda_approx": "EBITDA",
            "net_cash_flow": "Flujo neto",
        }
    )
cash_out_mix = pd.DataFrame(
    [
        {"concepto": "Pago a proveedores", "amount": float(finance["supplier_payments_amount"].sum()) if not finance.empty else 0.0},
        {"concepto": "Pago de nomina", "amount": float(finance["payroll_cash_amount"].sum()) if not finance.empty else 0.0},
        {"concepto": "Pago de impuestos", "amount": float(finance["tax_payments_amount"].sum()) if not finance.empty else 0.0},
        {"concepto": "Pago logistico", "amount": float(finance["logistics_cash_amount"].sum()) if not finance.empty else 0.0},
    ]
)
cash_out_mix = cash_out_mix.loc[cash_out_mix["amount"] > 0].reset_index(drop=True)
working_capital_mix = working_capital.loc[
    working_capital["concepto"].isin(["Cuentas por cobrar", "Cuentas por pagar"]),
    ["concepto", "monto_abierto"],
].copy()

scope_filters = [
    label
    for key, label in (
        ("campaigns", "campaña"),
        ("crops", "cultivo"),
        ("products", "producto"),
        ("clients", "cliente"),
    )
    if filters.get(key)
]
if scope_filters:
    st.info(
        "La página financiera sigue una lectura consolidada por período. "
        f"Los filtros de {' / '.join(scope_filters)} impactan otras vistas, pero no prorratean este P&L."
    )

cards = build_finance_summary_cards(finance, variant="finance")
cards.extend(
    [
        {
            "label": "Impuesto devengado",
            "value": float(finance["tax_accrued"].sum()) if not finance.empty else 0.0,
            "format": "currency",
            "detail": "Acumulado del rango visible",
            "tone": "neutral",
        },
        {
            "label": "Saldo IVA al cierre",
            "value": latest_period_value(finance, "iva_saldo"),
            "format": "currency",
            "detail": f"Cierre del periodo visible: {latest_finance_period}",
            "tone": "neutral",
        },
    ]
)
render_kpi_cards(cards, columns=4)

section_header("Lecturas gerenciales", "Meses clave, estructura de costos y capacidad de traducir EBITDA en caja.")
render_insight_panels(build_finance_insight_panels(finance), columns=4)

section_header(
    "Snapshot de capital de trabajo",
    f"Cuentas abiertas al cierre actual del {snapshot_info['snapshot_date'] or 'sin snapshot'}.",
)
render_kpi_cards(build_snapshot_kpis(bundle, filters)[1:], columns=2)

row_one_left, row_one_right = st.columns([1.5, 1.0])

with row_one_left:
    section_header("Resultado por periodo", "Ingresos netos con lectura simultanea de margen bruto y margen EBITDA.")
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

with row_one_right:
    bridge_tab, cost_tab = st.tabs(["Puente EBITDA", "Mix de costos"])
    with bridge_tab:
        section_header("Puente EBITDA", "De ingresos netos a EBITDA acumulado del rango.")
        bridge = build_finance_bridge(finance)
        if bridge.empty:
            st.info("No hay resultado para construir el puente.")
        else:
            st.plotly_chart(
                waterfall_chart(bridge, x="concepto", y="amount", measure="measure"),
                width="stretch",
            )
    with cost_tab:
        section_header("Mix de costos", "Participacion relativa de costos visibles en el resultado.")
        cost_mix = build_finance_cost_mix(finance)
        if cost_mix.empty:
            st.info("No hay costos visibles para el filtro seleccionado.")
        else:
            st.plotly_chart(
                donut_chart(cost_mix, names="concepto", values="amount"),
                width="stretch",
            )

row_two_left, row_two_right = st.columns(2)

with row_two_left:
    section_header("Estructura de costos por periodo", "Peso mensual de costo de ventas, nomina, mantenimiento y logistica.")
    cost_trend = build_finance_cost_trend(finance)
    if cost_trend.empty:
        st.info("No hay costos visibles para graficar.")
    else:
        st.plotly_chart(
            bar_chart(cost_trend, x="period_id", y="amount", color="concepto", barmode="stack"),
            width="stretch",
        )

with row_two_right:
    section_header("Caja operativa", "Cobranza contra salidas de caja; los egresos se muestran en negativo.")
    cash_components = build_finance_cash_components(finance)
    if cash_components.empty:
        st.info("No hay movimientos de caja para graficar.")
    else:
        st.plotly_chart(
            bar_chart(cash_components, x="period_id", y="amount", color="concepto", barmode="relative"),
            width="stretch",
        )

row_three_left, row_three_right = st.columns(2)

with row_three_left:
    section_header("Resultado vs caja", "Serie temporal de ingresos, EBITDA y flujo neto para medir calidad del resultado.")
    if result_vs_cash.empty:
        st.info("No hay serie temporal suficiente para comparar resultado y caja.")
    else:
        st.plotly_chart(
            line_chart(result_vs_cash, x="period_id", y="amount", color="concepto"),
            width="stretch",
        )

with row_three_right:
    section_header("Mix de salidas de caja", "Participacion relativa de pagos a proveedores, nomina, impuestos y logistica.")
    if cash_out_mix.empty:
        st.info("No hay salidas de caja para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(cash_out_mix, names="concepto", values="amount"),
            width="stretch",
        )

section_header("Scorecard mensual", "Comparativo por periodo para revenue, costo, margen, EBITDA y caja.")
scorecard = build_finance_scorecard(finance).rename(
    columns={
        "period_id": "Periodo",
        "revenue_net": "Ingresos netos",
        "sold_tons": "Toneladas vendidas",
        "revenue_per_ton": "Precio realizado USD/tn",
        "cogs": "Costo de ventas",
        "gross_margin_pct_calc": "Margen bruto %",
        "opex_total": "Opex total",
        "ebitda_approx": "EBITDA aprox.",
        "ebitda_margin_pct": "Margen EBITDA %",
        "net_cash_flow": "Flujo neto",
        "cash_conversion_pct_calc": "Conversion a caja",
    }
)
show_table(scorecard.round(2), height=340)

row_four_left, row_four_right = st.columns(2)

with row_four_left:
    section_header("Antiguedad de CxC", "Monto abierto y cantidad de documentos por bucket.")
    ar_summary = summarize_aging(ar)
    if ar_summary.empty:
        st.info("No hay cuentas por cobrar abiertas.")
    else:
        st.plotly_chart(
            bar_chart(ar_summary, x="aging_bucket", y="open_amount"),
            width="stretch",
        )

with row_four_right:
    section_header("Antiguedad de CxP", "Exposicion a proveedores por bucket de vencimiento.")
    ap_summary = summarize_aging(ap)
    if ap_summary.empty:
        st.info("No hay cuentas por pagar abiertas.")
    else:
        st.plotly_chart(
            bar_chart(ap_summary, x="aging_bucket", y="open_amount"),
            width="stretch",
        )

row_five_left, row_five_right = st.columns(2)

with row_five_left:
    section_header("Mix CxC abiertas", "Distribucion porcentual de cuentas por cobrar por bucket.")
    ar_summary = summarize_aging(ar)
    if ar_summary.empty:
        st.info("No hay cuentas por cobrar abiertas.")
    else:
        st.plotly_chart(
            donut_chart(ar_summary, names="aging_bucket", values="open_amount"),
            width="stretch",
        )

with row_five_right:
    section_header("Mix CxP abiertas", "Distribucion porcentual de cuentas por pagar por bucket.")
    ap_summary = summarize_aging(ap)
    if ap_summary.empty:
        st.info("No hay cuentas por pagar abiertas.")
    else:
        st.plotly_chart(
            donut_chart(ap_summary, names="aging_bucket", values="open_amount"),
            width="stretch",
        )

row_six_left, row_six_right = st.columns(2)

with row_six_left:
    section_header("Mix de capital de trabajo", "Peso relativo de cuentas por cobrar y pagar dentro del capital abierto.")
    if working_capital_mix.empty:
        st.info("No hay capital de trabajo abierto para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(working_capital_mix, names="concepto", values="monto_abierto"),
            width="stretch",
        )

with row_six_right:
    section_header(
        "Capital de trabajo",
        f"Resumen de cuentas abiertas y vencidas al snapshot {snapshot_info['snapshot_date'] or 'sin snapshot'}.",
    )
    show_table(working_capital.round(2), height=180)

table_left, table_right = st.columns(2)

with table_left:
    section_header("Principales CxC vencidas", "Clientes que hoy tensionan la caja.")
    ar_focus = ar[["client_name", "invoice_date", "due_date", "open_amount", "days_overdue", "aging_bucket"]].head(12)
    show_table(ar_focus.round(2), height=340)

with table_right:
    section_header("Principales CxP vencidas", "Compromisos prioritarios con proveedores.")
    ap_focus = ap[["supplier_name", "invoice_date", "due_date", "open_amount", "days_overdue", "aging_bucket"]].head(12)
    show_table(ap_focus.round(2), height=340)
