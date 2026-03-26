from __future__ import annotations

from demoagro.services.dashboard_data import load_dashboard_bundle
from demoagro.services.support_ops_data import (
    build_support_overview,
    get_logistics_period,
    get_maintenance_period,
    get_payroll_period,
)


def test_support_views_return_data_for_recent_periods() -> None:
    bundle = load_dashboard_bundle()
    filters = {"period_start": "2025-07", "period_end": "2025-12"}

    assert not get_payroll_period(bundle, filters).empty
    assert not get_maintenance_period(bundle, filters).empty
    assert not get_logistics_period(bundle, filters).empty


def test_support_overview_returns_expected_cards() -> None:
    bundle = load_dashboard_bundle()
    filters = {"period_start": "2025-07", "period_end": "2025-12"}
    cards = build_support_overview(bundle, filters)

    assert len(cards) == 6
    assert {card["label"] for card in cards} == {
        "Costo laboral total",
        "Horas extra",
        "Gasto mantenimiento",
        "Horas de parada",
        "Costo logistico",
        "Share tercerizado",
    }
