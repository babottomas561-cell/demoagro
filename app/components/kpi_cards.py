from __future__ import annotations

from html import escape

import streamlit as st


def format_value(value: float, value_format: str) -> str:
    if value_format == "currency":
        return f"USD {value:,.0f}"
    if value_format == "percent":
        return f"{value:.1%}"
    if value_format == "tons":
        return f"{value:,.0f} tn"
    if value_format == "integer":
        return f"{value:,.0f}"
    return f"{value:,.2f}"


def render_kpi_cards(cards: list[dict[str, object]], columns: int = 4) -> None:
    if not cards:
        st.info("No hay indicadores para mostrar con el filtro actual.")
        return

    grid = st.columns(columns)
    for index, card in enumerate(cards):
        with grid[index % columns]:
            tone = escape(str(card.get("tone", "neutral")))
            label = escape(str(card.get("label", "")))
            detail = escape(str(card.get("detail", "")))
            value = format_value(float(card.get("value", 0.0)), str(card.get("format", "number")))
            st.markdown(
                f"""
                <div class="metric-card {tone}">
                    <div class="metric-label">{label}</div>
                    <div class="metric-value">{value}</div>
                    <div class="metric-detail">{detail}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
