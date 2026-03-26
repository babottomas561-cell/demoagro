from __future__ import annotations

import pandas as pd

from demoagro.services.dashboard_data import get_finance_period, load_dashboard_bundle
from demoagro.services.finance_analysis import (
    build_finance_bridge,
    build_finance_cost_mix,
    build_finance_summary_cards,
    prepare_finance_analysis,
)


def test_finance_analysis_builds_expected_artifacts() -> None:
    bundle = load_dashboard_bundle()
    finance = prepare_finance_analysis(get_finance_period(bundle, {}))

    assert not finance.empty
    assert {"gross_margin_pct_calc", "ebitda_margin_pct", "cash_conversion_pct_calc"}.issubset(finance.columns)

    cards = build_finance_summary_cards(finance, variant="finance")
    assert len(cards) == 6
    assert {card["label"] for card in cards} >= {
        "Ingresos netos",
        "Costo de ventas",
        "Opex total",
        "EBITDA aprox.",
    }


def test_finance_bridge_reconciles_with_ebitda() -> None:
    bundle = load_dashboard_bundle()
    finance = prepare_finance_analysis(get_finance_period(bundle, {}))

    bridge = build_finance_bridge(finance)
    assert len(bridge) == 6
    assert bridge.iloc[-1]["concepto"] == "EBITDA aprox."

    cost_mix = build_finance_cost_mix(finance)
    assert not cost_mix.empty
    assert abs(float(cost_mix["share_pct"].sum()) - 1.0) < 1e-6


def test_finance_analysis_tolerates_missing_cash_columns() -> None:
    finance = pd.DataFrame(
        [
            {
                "period_id": "2025-01",
                "revenue_net": 100.0,
                "cogs": 40.0,
                "gross_margin": 60.0,
                "payroll_total": 10.0,
                "maintenance_expense": 5.0,
                "logistics_expense": 4.0,
                "opex_total": 19.0,
                "ebitda_approx": 41.0,
                "net_cash_flow": 30.0,
                "sold_tons": 2.0,
            }
        ]
    )

    enriched = prepare_finance_analysis(finance)

    assert "logistics_cash_amount" in enriched.columns
    assert float(enriched.iloc[0]["logistics_cash_amount"]) == 0.0
    assert float(enriched.iloc[0]["total_cash_out"]) == 0.0
