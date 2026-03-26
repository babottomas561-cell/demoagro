from __future__ import annotations

from html import escape

import pandas as pd
import streamlit as st


def show_table(dataframe: pd.DataFrame, height: int = 320) -> None:
    if dataframe.empty:
        st.info("No hay filas para mostrar con el filtro actual.")
        return
    st.dataframe(dataframe, width="stretch", height=height, hide_index=True)


def render_alerts(alerts: list[dict[str, str]]) -> None:
    for alert in alerts:
        level = escape(alert.get("level", "info"))
        title = escape(alert.get("title", ""))
        body = escape(alert.get("body", ""))
        st.markdown(
            f"""
            <div class="alert-card {level}">
                <div class="alert-title">{title}</div>
                <p class="alert-body">{body}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
