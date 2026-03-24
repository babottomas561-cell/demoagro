import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from api.client import fetch_riego
from plotly_theme import apply_chart_style, add_hline, add_vline
from ui_helpers import render_alerts, render_panel_context

COLORS     = ["#30945a", "#74866f", "#a79c89", "#cf6e63", "#c1b29a"]
WATER_BLUE = "#5ba4cf"
LEMON      = "#c8a800"


def render():
    data = fetch_riego()
    if not data:
        st.error("❌ Sin conexión con el backend")
        return

    meta      = data.get("meta", {})
    s         = data.get("summary", {})
    series    = data.get("series", {})
    breakdown = data.get("breakdown", {})
    alerts    = data.get("alerts", [])

    # ── Alerta déficit hídrico ────────────────────────────────────────────────
    cumpl = s.get("cumplimiento_hidrico_pct", 0)
    if cumpl < 50:
        st.error(f"🚨 Cobertura hídrica reciente crítica: {cumpl:.1f}% (umbral: 50%). Riesgo de estrés hídrico severo.")
    elif cumpl < 80:
        st.warning(f"⚠️ Cobertura hídrica reciente baja: {cumpl:.1f}% (objetivo: ≥ 80%)")

    render_alerts(alerts)
    render_panel_context(meta)

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("m³ aplicados", f"{s.get('m3_aplicados',0):,.0f} m³",
              f"{s.get('m3_aplicados_delta_pct',0):+.1f}%",
              help=s.get("m3_aplicados_detail",""))
    c2.metric("Cobertura hídrica reciente", f"{cumpl:.1f}%",
              f"{s.get('cumplimiento_delta_pct',0):+.1f}%",
              delta_color="normal" if cumpl >= 80 else "inverse",
              help=s.get("cumplimiento_detail","FAO-56: objetivo ≥ 80%"))
    c3.metric("Lluvia reciente", f"{s.get('lluvia_reciente_mm',0):.1f} mm",
              f"{s.get('lluvia_delta_pct',0):+.1f}%",
              help=s.get("lluvia_detail",""))
    c4.metric("Productividad agua", f"{s.get('productividad_agua_kg_m3',0):.2f} kg/m³",
              f"{s.get('productividad_delta_pct',0):+.1f}%",
              delta_color="normal" if s.get("productividad_agua_kg_m3",0) >= 4 else "inverse",
              help=s.get("productividad_detail","Ref. buena: > 4 kg/m³"))

    c5, c6, _, _ = st.columns(4)
    balance = s.get("balance_total_m3", 0)
    c5.metric("Lotes fuera de rango", str(s.get("lotes_fuera_rango",0)), delta_color="inverse")
    c6.metric("Balance hídrico reciente", f"{balance:,.0f} m³",
              delta_color="normal" if balance >= 0 else "inverse")
    st.caption(
        f"Aporte hídrico reciente: **{s.get('aporte_hidrico_reciente_m3', 0):,.0f} m³** "
        f"· Cobertura por riego puro: **{s.get('riego_cobertura_pct', 0):.1f}%** "
        f"· Lluvia acumulada del período: **{s.get('lluvia_acumulada_mm', 0):.1f} mm**"
    )

    st.divider()

    # ── Serie semanal ─────────────────────────────────────────────────────────
    semanal = series.get("agua_semanal", [])
    if semanal:
        df = pd.DataFrame(semanal)
        df["fecha"] = pd.to_datetime(df["fecha"])

        # Gráfico principal: riego + lluvia vs ET₀ (balance hídrico)
        ca, cb = st.columns(2)
        with ca:
            st.subheader("💧 Aporte hídrico vs Requerimiento (m³)")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["fecha"], y=df["m3_riego"],
                name="m³ Riego", marker_color=WATER_BLUE, opacity=0.85,
                hovertemplate="%{x|%d %b}<br>Riego: %{y:,.0f} m³<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["fecha"], y=df["m3_aportados"],
                name="Aporte total",
                line=dict(color=COLORS[0], width=2.5),
                mode="lines+markers",
                hovertemplate="%{x|%d %b}<br>Aporte total: %{y:,.0f} m³<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["fecha"], y=df["m3_requeridos"],
                name="Requerimiento", line=dict(color=COLORS[3], width=2, dash="dot"),
                hovertemplate="%{x|%d %b}<br>Req: %{y:,.0f} m³<extra></extra>",
            ))
            apply_chart_style(fig, height=300)
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            st.subheader("📊 Balance hídrico semanal (m³)")
            bal_colors = [COLORS[0] if v >= 0 else COLORS[3] for v in df["balance_hidrico_m3"]]
            fig2 = go.Figure(go.Bar(
                x=df["fecha"], y=df["balance_hidrico_m3"],
                marker_color=bal_colors, opacity=0.85,
                hovertemplate="%{x|%d %b}<br><b>Balance: %{y:,.0f} m³</b><extra></extra>",
            ))
            add_hline(fig2, 0, "Equilibrio", color=LEMON)
            apply_chart_style(fig2, height=300, legend=False)
            st.plotly_chart(fig2, use_container_width=True)

        # Lluvia + ET₀
        cc, cd = st.columns(2)
        with cc:
            st.subheader("🌧️ Lluvia semanal (mm)")
            fig3 = go.Figure(go.Bar(
                x=df["fecha"], y=df["lluvia_mm"],
                marker_color=WATER_BLUE, opacity=0.7,
                hovertemplate="%{x|%d %b}<br><b>%{y:.1f} mm</b><extra></extra>",
            ))
            apply_chart_style(fig3, height=260, legend=False)
            st.plotly_chart(fig3, use_container_width=True)

        with cd:
            st.subheader("☀️ ET₀ semanal (mm) — evapotranspiración")
            fig4 = go.Figure(go.Scatter(
                x=df["fecha"], y=df["et0_mm"],
                line=dict(color=COLORS[2], width=2), mode="lines+markers",
                fill="tozeroy", fillcolor="rgba(167,156,137,0.13)",
                hovertemplate="%{x|%d %b}<br><b>ET₀: %{y:.1f} mm</b><extra></extra>",
            ))
            apply_chart_style(fig4, height=260, legend=False)
            st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # ── Breakdown por lote ────────────────────────────────────────────────────
    m3_lotes  = breakdown.get("m3_lote", [])
    desvio    = breakdown.get("ranking_desvio", [])
    fert      = breakdown.get("fertirriego", [])

    ce, cf = st.columns(2)
    with ce:
        st.subheader("🌿 m³/ha por lote")
        if m3_lotes:
            df_l = pd.DataFrame(m3_lotes).sort_values("m3_ha", ascending=True)
            fig5 = go.Figure(go.Bar(
                x=df_l["m3_ha"], y=df_l["lote"],
                orientation="h", marker_color=WATER_BLUE, opacity=0.85,
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} m³/ha<br>Prod: %{customdata:.2f} kg/m³<extra></extra>",
                customdata=df_l["productividad_kg_m3"],
            ))
            apply_chart_style(fig5, height=320, legend=False, ygrid=False)
            st.plotly_chart(fig5, use_container_width=True)
        else:
            st.info("Sin datos por lote")

    with cf:
        st.subheader("⚠️ Balance hídrico por lote (ranking desvío)")
        if desvio:
            df_d = pd.DataFrame(desvio).sort_values("balance_hidrico_m3", ascending=True)
            bal_c = [COLORS[0] if v >= 0 else COLORS[3] for v in df_d["balance_hidrico_m3"]]
            fig6 = go.Figure(go.Bar(
                x=df_d["balance_hidrico_m3"], y=df_d["lote"],
                orientation="h", marker_color=bal_c, opacity=0.85,
                hovertemplate="<b>%{y}</b><br>Balance: %{x:,.0f} m³<extra></extra>",
            ))
            add_vline(fig6, 0, "0", color=LEMON)
            apply_chart_style(fig6, height=320, legend=False, ygrid=False)
            st.plotly_chart(fig6, use_container_width=True)
        else:
            st.info("Sin datos de desvío")

    # ── Fertirriego ───────────────────────────────────────────────────────────
    if fert:
        st.subheader("🧪 Fertirriego — eventos por lote")
        df_f = pd.DataFrame(fert)[["lote","establecimiento","variedad","fert_eventos","m3_ha","productividad_kg_m3"]].sort_values("fert_eventos", ascending=False)
        df_f.columns = ["Lote","Establecimiento","Variedad","Eventos fertirr.","m³/ha","Prod. kg/m³"]
        st.dataframe(df_f, use_container_width=True, hide_index=True)
