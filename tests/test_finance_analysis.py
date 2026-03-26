from __future__ import annotations

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
