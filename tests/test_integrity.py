from __future__ import annotations

import pandas as pd

from demoagro.db.sqlite import connect_sqlite
from demoagro.services.dashboard_data import get_snapshot_metadata, load_dashboard_bundle


def test_sqlite_connections_enforce_foreign_keys() -> None:
    connection = connect_sqlite()
    try:
        assert connection.execute("PRAGMA foreign_keys;").fetchone()[0] == 1
    finally:
        connection.close()


def test_stock_is_never_negative() -> None:
    connection = connect_sqlite()
    try:
        stock = pd.read_sql_query(
            "SELECT quantity, stock_value FROM erp_stock_actual",
            connection,
        )
    finally:
        connection.close()

    assert (stock["quantity"] >= 0).all()
    assert (stock["stock_value"] >= 0).all()


def test_service_products_do_not_generate_inventory() -> None:
    connection = connect_sqlite()
    try:
        service_stock = pd.read_sql_query(
            """
            SELECT COUNT(*) AS service_rows
            FROM erp_stock_actual stock
            JOIN erp_productos prod ON prod.producto_id = stock.producto_id
            WHERE prod.category_code = 'SERVICIO'
            """,
            connection,
        )
    finally:
        connection.close()

    assert int(service_stock.iloc[0]["service_rows"]) == 0


def test_quality_lots_are_not_oversold() -> None:
    connection = connect_sqlite()
    try:
        lots = pd.read_sql_query(
            "SELECT lote_calidad_id, available_tons FROM erp_lotes_calidad",
            connection,
        )
        sold = pd.read_sql_query(
            """
            SELECT lote_calidad_id, SUM(quantity) AS sold_tons
            FROM erp_despachos_venta_det
            GROUP BY lote_calidad_id
            """,
            connection,
        )
    finally:
        connection.close()

    merged = lots.merge(sold, on="lote_calidad_id", how="left").fillna({"sold_tons": 0.0})
    assert (merged["sold_tons"] <= merged["available_tons"] + 1e-6).all()


def test_accounting_entries_are_balanced() -> None:
    connection = connect_sqlite()
    try:
        unbalanced = pd.read_sql_query(
            """
            SELECT asiento_id
            FROM cont_asientos_det
            GROUP BY asiento_id
            HAVING ABS(SUM(debit_amount) - SUM(credit_amount)) > 0.01
            """,
            connection,
        )
    finally:
        connection.close()

    assert unbalanced.empty


def test_working_capital_summary_matches_detail() -> None:
    bundle = load_dashboard_bundle()
    summary = bundle["mart_working_capital_summary"].iloc[0]
    ar = bundle["mart_working_capital_ar"]
    ap = bundle["mart_working_capital_ap"]

    assert round(float(summary["ar_open_amount"]), 2) == round(float(ar["open_amount"].sum()), 2)
    assert round(float(summary["ap_open_amount"]), 2) == round(float(ap["open_amount"].sum()), 2)
    assert round(float(summary["ar_overdue_amount"]), 2) == round(float(ar.loc[ar["days_overdue"] > 0, "open_amount"].sum()), 2)
    assert round(float(summary["ap_overdue_amount"]), 2) == round(float(ap.loc[ap["days_overdue"] > 0, "open_amount"].sum()), 2)


def test_working_capital_snapshot_uses_open_portfolio_horizon() -> None:
    bundle = load_dashboard_bundle()
    summary = bundle["mart_working_capital_summary"].iloc[0]
    ar = bundle["mart_working_capital_ar"]
    ap = bundle["mart_working_capital_ap"]

    due_dates = pd.concat([ar["due_date"], ap["due_date"]], ignore_index=True).dropna()
    expected_snapshot_date = pd.to_datetime(due_dates).max().date().isoformat()

    assert summary["snapshot_date"] == expected_snapshot_date


def test_logistics_cash_matches_treasury_movements() -> None:
    bundle = load_dashboard_bundle()
    finance = bundle["mart_finance_period"]
    treasury = finance["PAGO_LOGISTICA"].abs().sum() if "PAGO_LOGISTICA" in finance.columns else 0.0
    logistics_cash = finance["logistics_cash_amount"].sum()

    assert round(float(logistics_cash), 2) == round(float(treasury), 2)


def test_accounts_payable_keeps_short_term_balance() -> None:
    bundle = load_dashboard_bundle()
    ap = bundle["mart_working_capital_ap"]

    assert ((ap["days_overdue"] <= 60) | (ap["days_overdue"].isna())).any()


def test_snapshot_metadata_flags_historical_period() -> None:
    bundle = load_dashboard_bundle()
    metadata = get_snapshot_metadata(
        bundle,
        {"period_start": "2023-12", "period_end": "2023-12"},
    )

    assert metadata["snapshot_date"] == bundle["mart_working_capital_summary"].iloc[0]["snapshot_date"]
    assert metadata["period_excludes_snapshot"] is True
