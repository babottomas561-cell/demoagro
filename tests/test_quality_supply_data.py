from __future__ import annotations

from demoagro.services.dashboard_data import load_dashboard_bundle
from demoagro.services.quality_supply_data import (
    build_quality_supply_overview,
    get_procurement_period,
    get_quality_period,
)


def test_quality_and_procurement_views_return_data() -> None:
    bundle = load_dashboard_bundle()
    filters = {"period_start": "2025-01", "period_end": "2025-12"}

    assert not get_quality_period(bundle, filters).empty
    assert not get_procurement_period(bundle, filters).empty


def test_quality_supply_overview_returns_expected_cards() -> None:
    bundle = load_dashboard_bundle()
    filters = {"period_start": "2025-01", "period_end": "2025-12"}
    cards = build_quality_supply_overview(bundle, filters)

    assert len(cards) == 6
    assert {card["label"] for card in cards} == {
        "Toneladas analizadas",
        "Humedad promedio",
        "Share grado 1",
        "Castigo / bonif. medio",
        "Compras netas",
        "Lead time promedio",
    }
