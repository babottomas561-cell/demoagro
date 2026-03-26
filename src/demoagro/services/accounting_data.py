from __future__ import annotations

import pandas as pd

TAX_COLUMNS = [
    "posicion_fiscal_id",
    "empresa_id",
    "period_id",
    "iva_debito",
    "iva_credito",
    "saldo_iva",
    "cargas_sociales",
    "payable_amount",
]

ENTRY_COLUMNS = [
    "asiento_id",
    "empresa_id",
    "entry_date",
    "entry_type",
    "source_table",
    "source_id",
]

DETAIL_COLUMNS = [
    "asiento_det_id",
    "asiento_id",
    "cuenta_contable_id",
    "centro_costo_id",
    "debit_amount",
    "credit_amount",
    "memo",
]

ACCOUNT_COLUMNS = [
    "cuenta_contable_id",
    "account_code",
    "account_name",
    "account_group",
]

BOOK_COLUMNS = [
    "asiento_id",
    "empresa_id",
    "entry_date",
    "entry_type",
    "source_table",
    "source_id",
    "asiento_det_id",
    "cuenta_contable_id",
    "centro_costo_id",
    "debit_amount",
    "credit_amount",
    "memo",
    "account_code",
    "account_name",
    "account_group",
    "period_id",
]


def get_tax_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    tax = _bundle_frame(bundle, "tax_posiciones_fiscales_periodo", TAX_COLUMNS)
    tax["period_id"] = pd.to_datetime(tax["period_id"].astype(str), format="%Y%m", errors="coerce").dt.strftime("%Y-%m")
    tax = _apply_period_filter(tax, "period_id", filters)
    return tax.sort_values("period_id").reset_index(drop=True)


def get_accounting_book(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    entries = _bundle_frame(bundle, "cont_asientos", ENTRY_COLUMNS)
    details = _bundle_frame(bundle, "cont_asientos_det", DETAIL_COLUMNS)
    accounts = _bundle_frame(bundle, "cont_plan_cuentas", ACCOUNT_COLUMNS)

    if entries.empty or details.empty or accounts.empty:
        return pd.DataFrame(columns=BOOK_COLUMNS)

    book = entries.merge(details, on="asiento_id", how="left").merge(accounts, on="cuenta_contable_id", how="left")
    book["period_id"] = pd.to_datetime(book["entry_date"], errors="coerce").dt.strftime("%Y-%m")
    book = _apply_period_filter(book, "period_id", filters)
    return book.sort_values(["entry_date", "asiento_id", "asiento_det_id"]).reset_index(drop=True)


def build_accounting_overview(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, object]]:
    book = get_accounting_book(bundle, filters)
    tax = get_tax_period(bundle, filters)
    result_accounts = build_result_account_summary(bundle, filters)
    latest_tax_period = tax["period_id"].max() if not tax.empty else "Sin datos"

    return [
        {
            "label": "Asientos contabilizados",
            "value": float(book["asiento_id"].nunique()) if not book.empty else 0.0,
            "format": "integer",
            "detail": "Cabeceras contables del rango",
            "tone": "neutral",
        },
        {
            "label": "Debitos contabilizados",
            "value": float(book["debit_amount"].sum()) if not book.empty else 0.0,
            "format": "currency",
            "detail": "Movimientos al debe",
            "tone": "neutral",
        },
        {
            "label": "Creditos contabilizados",
            "value": float(book["credit_amount"].sum()) if not book.empty else 0.0,
            "format": "currency",
            "detail": "Movimientos al haber",
            "tone": "neutral",
        },
        {
            "label": "Resultado contable",
            "value": float(result_accounts["result_component"].sum()) if not result_accounts.empty else 0.0,
            "format": "currency",
            "detail": "Resultado neto por cuentas de resultado",
            "tone": "success" if result_accounts["result_component"].sum() >= 0 else "danger",
        },
        {
            "label": "Saldo IVA al cierre",
            "value": float(tax.sort_values("period_id").iloc[-1]["saldo_iva"]) if not tax.empty else 0.0,
            "format": "currency",
            "detail": f"Cierre fiscal de {latest_tax_period}",
            "tone": "warning" if not tax.empty and float(tax.sort_values('period_id').iloc[-1]['saldo_iva']) > 0 else "neutral",
        },
        {
            "label": "Pasivo fiscal cierre",
            "value": float(tax.sort_values("period_id").iloc[-1]["payable_amount"]) if not tax.empty else 0.0,
            "format": "currency",
            "detail": f"Total exigible de {latest_tax_period}",
            "tone": "warning" if not tax.empty and float(tax.sort_values('period_id').iloc[-1]['payable_amount']) > 0 else "neutral",
        },
    ]


def build_account_balance_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    book = get_accounting_book(bundle, filters)
    if book.empty:
        return pd.DataFrame(
            columns=[
                "account_code",
                "account_name",
                "account_group",
                "debit_amount",
                "credit_amount",
                "net_balance",
                "display_balance",
                "balance_side",
            ]
        )

    summary = book.groupby(["account_code", "account_name", "account_group"], as_index=False).agg(
        debit_amount=("debit_amount", "sum"),
        credit_amount=("credit_amount", "sum"),
        line_count=("asiento_det_id", "count"),
    )
    summary["net_balance"] = summary["debit_amount"] - summary["credit_amount"]
    summary["display_balance"] = summary["net_balance"].abs()
    summary["balance_side"] = summary["net_balance"].apply(lambda value: "Deudor" if value >= 0 else "Acreedor")
    return summary.sort_values("display_balance", ascending=False).reset_index(drop=True)


def build_result_account_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    balances = build_account_balance_summary(bundle, filters)
    result_accounts = balances.loc[balances["account_group"] == "RESULTADO"].copy()
    if result_accounts.empty:
        return pd.DataFrame(
            columns=[
                "account_code",
                "account_name",
                "debit_amount",
                "credit_amount",
                "result_component",
                "result_type",
            ]
        )

    result_accounts["result_component"] = result_accounts["credit_amount"] - result_accounts["debit_amount"]
    result_accounts["result_type"] = result_accounts["result_component"].apply(
        lambda value: "Ingreso" if value >= 0 else "Gasto"
    )
    result_accounts["result_abs"] = result_accounts["result_component"].abs()
    return result_accounts.sort_values("result_abs", ascending=False).reset_index(drop=True)


def build_entry_type_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    book = get_accounting_book(bundle, filters)
    if book.empty:
        return pd.DataFrame(columns=["entry_type", "entry_count", "debit_amount", "credit_amount"])

    entries = book.groupby("entry_type", as_index=False).agg(
        entry_count=("asiento_id", "nunique"),
        debit_amount=("debit_amount", "sum"),
        credit_amount=("credit_amount", "sum"),
    )
    return entries.sort_values("debit_amount", ascending=False).reset_index(drop=True)


def build_account_group_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    balances = build_account_balance_summary(bundle, filters)
    if balances.empty:
        return pd.DataFrame(columns=["account_group", "display_balance"])

    grouped = balances.groupby("account_group", as_index=False).agg(
        display_balance=("display_balance", "sum"),
        debit_amount=("debit_amount", "sum"),
        credit_amount=("credit_amount", "sum"),
    )
    return grouped.sort_values("display_balance", ascending=False).reset_index(drop=True)


def _apply_period_filter(
    dataframe: pd.DataFrame,
    period_column: str,
    filters: dict[str, object],
) -> pd.DataFrame:
    if dataframe.empty or period_column not in dataframe.columns:
        return dataframe

    start = filters.get("period_start")
    end = filters.get("period_end")
    result = dataframe.copy()
    result[period_column] = result[period_column].astype(str)
    if start:
        result = result[result[period_column] >= str(start)]
    if end:
        result = result[result[period_column] <= str(end)]
    return result


def _bundle_frame(
    bundle: dict[str, pd.DataFrame],
    key: str,
    columns: list[str],
) -> pd.DataFrame:
    dataframe = bundle.get(key)
    if isinstance(dataframe, pd.DataFrame):
        return dataframe.copy()
    return pd.DataFrame(columns=columns)
