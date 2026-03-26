from __future__ import annotations

import pandas as pd

from demoagro.services.accounting_data import get_accounting_book, get_tax_period


def test_get_tax_period_tolerates_missing_tax_table() -> None:
    tax_period = get_tax_period(bundle={}, filters={})

    assert tax_period.empty
    assert {"period_id", "saldo_iva", "payable_amount"}.issubset(tax_period.columns)


def test_get_accounting_book_tolerates_missing_accounting_tables() -> None:
    book = get_accounting_book(bundle={}, filters={})

    assert book.empty
    assert {"asiento_id", "entry_date", "account_code", "period_id"}.issubset(book.columns)


def test_get_tax_period_formats_period_when_table_exists() -> None:
    bundle = {
        "tax_posiciones_fiscales_periodo": pd.DataFrame(
            [
                {
                    "posicion_fiscal_id": "TAX_1",
                    "empresa_id": "EMP_1",
                    "period_id": "202501",
                    "iva_debito": 10.0,
                    "iva_credito": 7.0,
                    "saldo_iva": 3.0,
                    "cargas_sociales": 1.0,
                    "payable_amount": 4.0,
                }
            ]
        )
    }

    tax_period = get_tax_period(bundle=bundle, filters={})

    assert list(tax_period["period_id"]) == ["2025-01"]
