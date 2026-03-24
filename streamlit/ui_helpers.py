from datetime import date

import streamlit as st


def render_alerts(alerts: list[dict] | None):
    for alert in alerts or []:
        severity = (alert.get("severidad") or alert.get("nivel") or "info").lower()
        title = alert.get("titulo") or alert.get("mensaje") or "Alerta"
        impact = alert.get("impacto") or ""
        detail = alert.get("detalle") or ""

        parts = [f"**{title}**"]
        if impact:
            parts.append(impact)
        if detail and detail not in {"Sin atraso"}:
            parts.append(detail)
        message = " · ".join(parts)

        if severity in {"critical", "danger", "error"}:
            st.error(message)
        elif severity == "warning":
            st.warning(message)
        elif severity == "success":
            st.success(message)
        else:
            st.info(message)


def render_panel_context(meta: dict):
    st.caption(f"📡 {meta.get('source', '—')}  ·  Actualizado: **{meta.get('last_updated', '—')}**")

    scope = [f"Campaña **{meta.get('campania', '—')}**"]
    if meta.get("scope_lotes") is not None:
        scope.append(f"{meta.get('scope_lotes', 0)} lotes")
    if meta.get("scope_superficie_ha"):
        scope.append(f"{meta.get('scope_superficie_ha', 0):.0f} ha")
    st.caption("  ·  ".join(scope))

    fase = meta.get("fase_campania") or {}
    if fase:
        st.caption(f"🍋 **{fase.get('label', 'Fase de campaña')}** · {fase.get('descripcion', '')}")

    last_updated = meta.get("last_updated")
    if isinstance(last_updated, str):
        try:
            snapshot_date = date.fromisoformat(last_updated)
        except ValueError:
            snapshot_date = None
        if snapshot_date and (date.today() - snapshot_date).days > 45:
            st.caption("🗂️ Campaña histórica cerrada: los KPI diarios refieren al último día con operación dentro del período filtrado.")
