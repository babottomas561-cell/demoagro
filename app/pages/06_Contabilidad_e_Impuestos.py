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
from demoagro.services.accounting_data import (
    build_account_balance_summary,
    build_account_group_summary,
    build_accounting_overview,
    build_entry_type_summary,
    build_result_account_summary,
    get_accounting_book,
    get_tax_period,
)

apply_page_theme("Contabilidad e Impuestos")
page_header(
    "Contabilidad e impuestos",
    "Lectura contable y fiscal sobre asientos reales del ERP simulado, sin mezclarla con la capa comercial.",
)

bundle = get_dashboard_bundle()
filters = render_global_filters(get_dashboard_filter_options(), get_dashboard_snapshot_metadata())

tax_period = get_tax_period(bundle, filters)
book = get_accounting_book(bundle, filters)
balances = build_account_balance_summary(bundle, filters)
result_accounts = build_result_account_summary(bundle, filters)
entry_types = build_entry_type_summary(bundle, filters)
group_summary = build_account_group_summary(bundle, filters)

result_type_mix = (
    result_accounts.groupby("result_type", as_index=False)
    .agg(result_abs=("result_abs", "sum"))
    .sort_values("result_abs", ascending=False)
    if not result_accounts.empty
    else pd.DataFrame(columns=["result_type", "result_abs"])
)
book_period = (
    book.groupby("period_id", as_index=False).agg(
        debit_amount=("debit_amount", "sum"),
        credit_amount=("credit_amount", "sum"),
        entry_count=("asiento_id", "nunique"),
    )
    if not book.empty
    else pd.DataFrame(columns=["period_id", "debit_amount", "credit_amount", "entry_count"])
)
if not book_period.empty:
    book_period_trend = book_period[["period_id", "debit_amount", "credit_amount"]].melt(
        id_vars="period_id",
        var_name="metric",
        value_name="amount",
    )
else:
    book_period_trend = pd.DataFrame(columns=["period_id", "metric", "amount"])
balance_side_mix = (
    balances.groupby("balance_side", as_index=False).agg(display_balance=("display_balance", "sum"))
    if not balances.empty
    else pd.DataFrame(columns=["balance_side", "display_balance"])
)
entry_type_mix = entry_types[["entry_type", "entry_count"]].copy() if not entry_types.empty else pd.DataFrame(columns=["entry_type", "entry_count"])

cards = build_accounting_overview(bundle, filters)
cards.extend(
    [
        {
            "label": "Tipos de asiento",
            "value": float(entry_types["entry_type"].nunique()) if not entry_types.empty else 0.0,
            "format": "integer",
            "detail": "Procesos que alimentan contabilidad",
            "tone": "neutral",
        },
        {
            "label": "Cuentas activas",
            "value": float(balances["account_code"].nunique()) if not balances.empty else 0.0,
            "format": "integer",
            "detail": "Cuentas con saldo o movimiento visible",
            "tone": "neutral",
        },
    ]
)
render_kpi_cards(cards, columns=4)

row_one_left, row_one_right = st.columns(2)

with row_one_left:
    section_header("Posicion fiscal por periodo", "IVA debito, IVA credito y saldo mensual del rango visible.")
    if tax_period.empty:
        st.info("No hay posicion fiscal para la seleccion actual.")
    else:
        tax_trend = tax_period[["period_id", "iva_debito", "iva_credito", "saldo_iva"]].melt(
            id_vars="period_id",
            var_name="metric",
            value_name="amount",
        )
        st.plotly_chart(
            line_chart(tax_trend, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

with row_one_right:
    section_header("Mix contable", "Peso relativo de activo, pasivo y resultado en los saldos visibles.")
    if group_summary.empty:
        st.info("No hay grupos contables para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(group_summary, names="account_group", values="display_balance"),
            width="stretch",
        )

row_two_left, row_two_right = st.columns(2)

with row_two_left:
    section_header("Asientos por tipo", "Que procesos estan generando mayor volumen contable.")
    if entry_types.empty:
        st.info("No hay asientos para la seleccion actual.")
    else:
        st.plotly_chart(
            bar_chart(entry_types, x="entry_type", y="debit_amount"),
            width="stretch",
        )

with row_two_right:
    section_header("Resultado por cuenta", "Aportes positivos y negativos de las cuentas de resultado.")
    if result_accounts.empty:
        st.info("No hay cuentas de resultado en el rango actual.")
    else:
        chart_data = result_accounts.head(12)[["account_name", "result_component", "result_type"]].copy()
        st.plotly_chart(
            bar_chart(chart_data, x="account_name", y="result_component", color="result_type", horizontal=True),
            width="stretch",
        )

row_three_left, row_three_right = st.columns(2)

with row_three_left:
    section_header("Tipo de resultado", "Mix entre cuentas que aportan ingreso y gasto.")
    if result_type_mix.empty:
        st.info("No hay mix de resultado para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(result_type_mix, names="result_type", values="result_abs"),
            width="stretch",
        )

with row_three_right:
    section_header("Saldo por grupo contable", "Comparativo de saldo visible por gran familia contable.")
    if group_summary.empty:
        st.info("No hay grupos contables para mostrar.")
    else:
        st.plotly_chart(
            bar_chart(group_summary, x="account_group", y="display_balance", color="account_group"),
            width="stretch",
        )

row_four_left, row_four_right = st.columns(2)

with row_four_left:
    section_header("Debitos vs creditos", "Segunda serie temporal para seguir el pulso contable del rango visible.")
    if book_period_trend.empty:
        st.info("No hay movimientos contables por periodo para mostrar.")
    else:
        st.plotly_chart(
            line_chart(book_period_trend, x="period_id", y="amount", color="metric"),
            width="stretch",
        )

with row_four_right:
    section_header("Lado del saldo", "Mix entre saldos deudores y acreedores sobre cuentas activas.")
    if balance_side_mix.empty:
        st.info("No hay lados de saldo para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(balance_side_mix, names="balance_side", values="display_balance"),
            width="stretch",
        )

row_five_left, row_five_right = st.columns(2)

with row_five_left:
    section_header("Mix de tipos de asiento", "Participacion relativa de los procesos que alimentan la contabilidad.")
    if entry_type_mix.empty:
        st.info("No hay tipos de asiento para mostrar.")
    else:
        st.plotly_chart(
            donut_chart(entry_type_mix, names="entry_type", values="entry_count"),
            width="stretch",
        )

with row_five_right:
    section_header("Resumen contable por periodo", "Tabla complementaria de la serie de debitos y creditos.")
    show_table(book_period.round(2), height=260)

table_left, table_right = st.columns([1.1, 0.9])

with table_left:
    section_header("Mayores saldos por cuenta", "Ranking contable de las cuentas mas relevantes.")
    balance_table = balances[
        [
            "account_code",
            "account_name",
            "account_group",
            "debit_amount",
            "credit_amount",
            "display_balance",
            "balance_side",
        ]
    ].copy()
    show_table(balance_table.round(2), height=380)

with table_right:
    section_header("Libro diario reciente", "Ultimas lineas contables dentro del filtro seleccionado.")
    journal_table = book[
        [
            "entry_date",
            "entry_type",
            "source_table",
            "source_id",
            "account_code",
            "account_name",
            "debit_amount",
            "credit_amount",
        ]
    ].sort_values(["entry_date", "source_id"], ascending=[False, False]).head(20)
    show_table(journal_table.round(2), height=380)
