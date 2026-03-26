from __future__ import annotations

from html import escape

import streamlit as st


def render_insight_panels(panels: list[dict[str, str]], columns: int = 4) -> None:
    if not panels:
        return

    grid = st.columns(columns)
    for index, panel in enumerate(panels):
        with grid[index % columns]:
            tone = escape(panel.get("tone", "neutral"))
            title = escape(panel.get("title", ""))
            headline = escape(panel.get("headline", ""))
            body = escape(panel.get("body", ""))
            st.markdown(
                f"""
                <div class="insight-panel {tone}">
                    <div class="insight-title">{title}</div>
                    <div class="insight-headline">{headline}</div>
                    <div class="insight-body">{body}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
