import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from api.client import fetch_sanidad
from plotly_theme import apply_chart_style, add_hline, apply_pie_style
from ui_helpers import render_alerts, render_panel_context

COLORS = ["#30945a", "#74866f", "#a79c89", "#cf6e63", "#c1b29a"]
LEMON  = "#c8a800"


def render():
    data = fetch_sanidad()
    if not data:
        st.error("❌ Sin conexión con el backend")
        return

    meta      = data.get("meta", {})
    s         = data.get("summary", {})
    series    = data.get("series", {})
    breakdown = data.get("breakdown", {})
    alerts    = data.get("alerts", [])

    # ── Alertas críticas de sanidad ───────────────────────────────────────────
    diaphorina = s.get("diaphorina_capturas", 0)
    if diaphorina > 0:
        st.error(
            f"🚨 **EMERGENCIA HLB**: {diaphorina} captura(s) de *Diaphorina citri* detectadas. "
            f"Activar protocolo de emergencia fitosanitaria SENASA inmediatamente. "
            f"La Huanglongbing no tiene cura."
        )
    else:
        st.success("✅ **Diaphorina citri**: 0 capturas · Sin riesgo HLB activo")

    dias_cobre = s.get("dias_sin_cobre", 0)
    if dias_cobre > 21:
        st.error(f"⚠️ **Alerta cancrosis**: {dias_cobre} días sin aplicación de cobre · Umbral crítico: 21 días durante brotación")
    elif dias_cobre > 14:
        st.warning(f"⚠️ {dias_cobre} días sin cobre — próxima aplicación recomendada")

    render_alerts(alerts)
    render_panel_context(meta)

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Incidencia promedio", f"{s.get('incidencia_promedio_pct',0):.2f}%",
              f"{s.get('incidencia_delta_pct',0):+.2f}%",
              delta_color="inverse",
              help=s.get("incidencia_detail","Ref. umbral bueno: < 5%"))
    c2.metric("Lotes en alerta", str(s.get("lotes_alerta",0)),
              f"{s.get('lotes_alerta_delta_pct',0):+.0f}",
              delta_color="inverse",
              help=s.get("lotes_alerta_detail",""))
    c3.metric("Tratamientos 30d", str(s.get("tratamientos_30d",0)),
              f"{s.get('tratamientos_delta_pct',0):+.0f}%",
              help=s.get("tratamientos_detail",""))
    c4.metric("Días sin cobre", str(dias_cobre),
              delta_color="inverse" if dias_cobre > 14 else "off",
              help=s.get("dias_sin_cobre_detail","Umbral crítico: 21 días en brotación"))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Lotes riesgo alto", str(s.get("lotes_riesgo_alto",0)), delta_color="inverse")
    c6.metric("Eventos totales", str(s.get("eventos_totales",0)))
    c7.metric("Sin tratamiento", str(s.get("lotes_sin_tratamiento",0)), delta_color="inverse")
    c8.metric("Diaphorina capturas", str(diaphorina),
              delta_color="inverse" if diaphorina > 0 else "off",
              help=s.get("diaphorina_capturas_detail",""))

    st.divider()

    # ── Serie semanal ─────────────────────────────────────────────────────────
    semanal = series.get("sanidad_semanal", [])
    if semanal:
        df = pd.DataFrame(semanal)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df_act = df[df["eventos"] > 0]

        ca, cb = st.columns(2)
        with ca:
            st.subheader("📈 Incidencia semanal (%)")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_act["fecha"], y=df_act["incidencia_promedio_pct"],
                line=dict(color=COLORS[3], width=2.5),
                fill="tozeroy", fillcolor="rgba(207,110,99,0.13)",
                mode="lines+markers",
                hovertemplate="%{x|%d %b}<br><b>Incidencia: %{y:.2f}%</b><extra></extra>",
            ))
            add_hline(fig, 5, "Umbral alerta 5%")
            add_hline(fig, 15, "Umbral crítico 15%", color=COLORS[3])
            apply_chart_style(fig, height=300, legend=False)
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            st.subheader("📊 Alertas y tratamientos semanales")
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=df_act["fecha"], y=df_act["alertas"],
                name="Alertas", marker_color=COLORS[3], opacity=0.85,
                hovertemplate="%{x|%d %b}<br>Alertas: %{y}<extra></extra>",
            ))
            fig2.add_trace(go.Bar(
                x=df_act["fecha"], y=df_act["tratamientos"],
                name="Tratamientos", marker_color=COLORS[0], opacity=0.85,
                hovertemplate="%{x|%d %b}<br>Tratamientos: %{y}<extra></extra>",
            ))
            fig2.update_layout(barmode="group")
            apply_chart_style(fig2, height=300)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Breakdown ─────────────────────────────────────────────────────────────
    cc, cd = st.columns(2)

    with cc:
        st.subheader("🦠 Incidencias por tipo")
        tipos = breakdown.get("incidencias_tipo", [])
        if tipos:
            df_t = pd.DataFrame(tipos).sort_values("eventos", ascending=True)
            fig3 = go.Figure(go.Bar(
                x=df_t["eventos"], y=df_t["tipo"],
                orientation="h", marker_color=COLORS[3], opacity=0.85,
                hovertemplate="<b>%{y}</b><br>%{x} eventos · %{customdata:.2f}%<extra></extra>",
                customdata=df_t["incidencia_promedio_pct"],
            ))
            apply_chart_style(fig3, height=300, legend=False, ygrid=False)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sin incidencias registradas")

    with cd:
        st.subheader("💊 Tratamientos aplicados")
        trat = breakdown.get("tratamientos", [])
        if trat:
            df_tr = pd.DataFrame(trat).sort_values("aplicaciones", ascending=False)
            fig4 = go.Figure(go.Bar(
                x=df_tr["aplicaciones"], y=df_tr["producto"],
                orientation="h", marker_color=COLORS[0], opacity=0.85,
                hovertemplate="<b>%{y}</b><br>%{x} aplicaciones<br>$%{customdata:,.0f}/ha<extra></extra>",
                customdata=df_tr["costo_promedio_ars_ha"],
            ))
            apply_chart_style(fig4, height=300, legend=False, ygrid=False)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Sin tratamientos registrados")

    # ── Lotes críticos ────────────────────────────────────────────────────────
    lotes_crit = breakdown.get("lotes_criticos", [])
    if lotes_crit:
        st.subheader("🔴 Lotes con mayor incidencia")
        df_lc = pd.DataFrame(lotes_crit)[[
            "lote","establecimiento","variedad","incidencia_promedio_pct","alertas","tratamientos","eventos"
        ]].sort_values("incidencia_promedio_pct", ascending=False)
        df_lc.columns = ["Lote","Establecimiento","Variedad","Incidencia %","Alertas","Tratamientos","Eventos"]
        st.dataframe(df_lc, use_container_width=True, hide_index=True)
