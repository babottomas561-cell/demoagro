import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from api.client import fetch_packhouse
from plotly_theme import apply_chart_style, add_hline, apply_pie_style
from ui_helpers import render_alerts, render_panel_context

COLORS = ["#30945a", "#74866f", "#a79c89", "#cf6e63", "#c1b29a"]
LEMON  = "#c8a800"


def fmt_ars(v):
    if abs(v) >= 1_000_000: return f"${v/1_000_000:.1f}M"
    if abs(v) >= 1_000:     return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


def line_status(row: pd.Series) -> str:
    eff = row.get("eficiencia_pct", 0)
    downtime = row.get("downtime_pct", 0)
    if eff < 60 or downtime > 25:
        return "Crítica"
    if eff < 75 or downtime > 15:
        return "Seguimiento"
    return "Estable"


def process_status(summary: dict) -> str:
    eff = float(summary.get("eficiencia_promedio_pct", 0) or 0)
    downtime = float(summary.get("downtime_pct", 0) or 0)
    if eff >= 82 and downtime <= 8:
        return "Estable"
    if eff >= 72 and downtime <= 15:
        return "Seguimiento"
    return "Crítico"


def render():
    data = fetch_packhouse()
    if not data:
        st.error("❌ Sin conexión con el backend")
        return

    meta      = data.get("meta", {})
    s         = data.get("summary", {})
    series    = data.get("series", {})
    breakdown = data.get("breakdown", {})
    alerts    = data.get("alerts", [])

    render_alerts(alerts)

    st.info(
        "📘 Guía exportación: este panel vigila continuidad operativa, presentación homogénea y "
        "estabilidad de línea/turno para no degradar fruta exportable."
    )

    render_panel_context(meta)

    process_label = process_status(s)

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Fruta procesada", f"{s.get('tn_procesadas',0):,.1f} tn",
              f"{s.get('tn_procesadas_delta_pct',0):+.1f}%",
              help=s.get("tn_procesadas_detail",""))
    c2.metric("Eficiencia de línea", f"{s.get('eficiencia_promedio_pct',0):.1f}%",
              f"{s.get('eficiencia_delta_pct',0):+.1f}%",
              help=s.get("eficiencia_detail","Ref. industria: > 85%"))
    c3.metric("Paradas operativas", f"{s.get('downtime_pct',0):.1f}%",
              f"{s.get('downtime_delta_pct',0):+.1f}%",
              delta_color="inverse",
              help=s.get("downtime_detail","Objetivo: < 5%. Crítico: > 15%"))
    c4.metric("Costo acond./tn", fmt_ars(s.get("costo_tn_ars",0)),
              f"{s.get('costo_tn_delta_pct',0):+.1f}%",
              delta_color="inverse",
              help=s.get("costo_tn_detail",""))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Líneas críticas", str(s.get("lineas_criticas",0)), delta_color="inverse")
    c6.metric("Paradas críticas", str(s.get("paradas_criticas",0)), delta_color="inverse")
    c7.metric("Continuidad operativa", f"{100 - s.get('downtime_pct',0):.1f}%")
    c8.metric("Estado de proceso", process_label)

    st.subheader("🎯 Foco de empaque")
    f1, f2, f3 = st.columns(3)
    f1.metric("Estabilidad de proceso", process_label)
    f2.metric("Downtime objetivo", "< 5%")
    f3.metric("Líneas en riesgo", str(s.get("lineas_criticas",0)))
    st.caption(
        "Lectura guía: si la línea pierde estabilidad, suben paradas, baja homogeneidad de presentación "
        "y se compromete fruta con destino exportación."
    )

    st.divider()

    # ── Serie diaria ──────────────────────────────────────────────────────────
    proc = series.get("procesamiento_diario", [])
    if proc:
        df = pd.DataFrame(proc)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df[df["kg_procesados_tn"] > 0]

        ca, cb = st.columns(2)
        with ca:
            st.subheader("📊 Throughput diario (tn)")
            fig = go.Figure(go.Bar(
                x=df["fecha"], y=df["kg_procesados_tn"],
                marker_color=COLORS[0], opacity=0.85,
                hovertemplate="%{x|%d %b}<br><b>%{y:,.1f} tn</b><extra></extra>",
            ))
            apply_chart_style(fig, height=300, legend=False)
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            st.subheader("📈 Eficiencia y Downtime (%)")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df["fecha"], y=df["eficiencia_pct"],
                name="Eficiencia", line=dict(color=COLORS[0], width=2),
                hovertemplate="%{x|%d %b}<br>Eficiencia: %{y:.1f}%<extra></extra>",
            ))
            fig2.add_trace(go.Bar(
                x=df["fecha"], y=df["downtime_pct"],
                name="Downtime", marker_color=COLORS[3], opacity=0.6,
                hovertemplate="%{x|%d %b}<br>Downtime: %{y:.1f}%<extra></extra>",
            ))
            add_hline(fig2, 5, "Límite downtime 5%")
            apply_chart_style(fig2, height=300)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Breakdown: performance por línea ─────────────────────────────────────
    lineas = breakdown.get("performance_linea", [])
    downtime_m = breakdown.get("downtime_motivos", [])
    costos_r   = breakdown.get("costos_rubro", [])
    ranking    = breakdown.get("ranking_lineas", [])

    cc, cd = st.columns(2)
    with cc:
        st.subheader("🏭 Performance por línea (tn/h)")
        if lineas:
            df_l = pd.DataFrame(lineas).sort_values("tn_hora", ascending=True)
            bar_col = [COLORS[0] if e >= 85 else COLORS[3] for e in df_l["eficiencia_pct"]]
            fig3 = go.Figure(go.Bar(
                x=df_l["tn_hora"], y=df_l["linea"],
                orientation="h", marker_color=bar_col,
                hovertemplate="<b>%{y}</b><br>%{x:.2f} tn/h<br>Ef: %{customdata:.1f}%<extra></extra>",
                customdata=df_l["eficiencia_pct"],
            ))
            apply_chart_style(fig3, height=300, legend=False, ygrid=False)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sin datos de líneas")

    with cd:
        st.subheader("⏱️ Downtime por motivo (min)")
        if downtime_m:
            df_dt = pd.DataFrame(downtime_m).sort_values("minutos", ascending=False)
            fig4 = go.Figure(go.Bar(
                x=df_dt["minutos"], y=df_dt["motivo"],
                orientation="h", marker_color=COLORS[3], opacity=0.85,
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} min<extra></extra>",
            ))
            apply_chart_style(fig4, height=300, legend=False, ygrid=False)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Sin paradas registradas")

    # ── Costos por rubro ──────────────────────────────────────────────────────
    if costos_r:
        st.subheader("💰 Estructura de costos packhouse")
        df_cr = pd.DataFrame(costos_r).sort_values("costo_ars", ascending=False)
        fig5 = go.Figure(go.Bar(
            x=df_cr["costo_ars"],
            y=df_cr["rubro"],
            orientation="h",
            marker_color=COLORS[2],
            opacity=0.9,
            customdata=df_cr["participacion_pct"],
            hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<br>%{customdata:.1f}%<extra></extra>",
        ))
        apply_chart_style(fig5, height=300, legend=False, ygrid=False)
        st.plotly_chart(fig5, use_container_width=True)

    if ranking:
        st.subheader("📋 Estado operativo por línea/turno")
        df_r = pd.DataFrame(ranking)
        df_r["Estado"] = df_r.apply(line_status, axis=1)
        df_r = df_r[["linea", "turno", "kg_procesados_tn", "eficiencia_pct", "downtime_pct", "Estado"]]
        df_r.columns = ["Línea", "Turno", "Tn procesadas", "Eficiencia %", "Downtime %", "Estado"]
        st.dataframe(df_r, use_container_width=True, hide_index=True)
        st.caption("Estado calculado con eficiencia de línea y downtime como proxy de riesgo operativo sobre fruta exportable.")
