import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from api.client import fetch_gerencia
from plotly_theme import SUCCESS, WARNING, DANGER, apply_chart_style, add_hline, add_vline, apply_pie_style
from ui_helpers import render_alerts, render_panel_context

COLORS = ["#30945a", "#74866f", "#a79c89", "#cf6e63", "#c1b29a"]
LEMON  = "#c8a800"


def fmt_ars(v):
    if abs(v) >= 1_000_000_000: return f"${v/1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:     return f"${v/1_000_000:.1f}M"
    if abs(v) >= 1_000:         return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


def establishment_status(row):
    margen_ha = float(row.get("margen_ha_ars", 0) or 0)
    if margen_ha >= 8_000_000:
        return "Fuerte"
    if margen_ha >= 5_500_000:
        return "Seguimiento"
    return "Presión"


def packout_status(actual_pct):
    if actual_pct >= 90:
        return "Sólido"
    if actual_pct >= 84:
        return "Seguimiento"
    return "Presión"


def cobranza_status(dias_cobro, abierto_ars):
    if abierto_ars <= 0:
        return "Controlado"
    if dias_cobro is not None and dias_cobro > 45:
        return "Presión"
    if abierto_ars >= 1_500_000_000:
        return "Seguimiento"
    return "Controlado"


def render():
    data = fetch_gerencia()
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
        "📘 La guía de clasificación para exportación impacta directo en margen: menos fruta dentro de calidad, "
        "calibre y tolerancia reduce volumen exportable y empuja mix a industria."
    )

    render_panel_context(meta)

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Margen operativo", fmt_ars(s.get("margen_operativo_ars",0)),
              f"{s.get('margen_operativo_delta_pct',0):+.1f}%",
              help=s.get("margen_operativo_detail",""))
    c2.metric("Margen/ha", fmt_ars(s.get("margen_por_ha_ars",0)),
              f"{s.get('margen_por_ha_delta_pct',0):+.1f}%",
              help=s.get("margen_por_ha_detail","Ref. bueno: > ARS 8M/ha"))
    c3.metric("Ingresos acumulados", fmt_ars(s.get("ingresos_acumulados_ars",0)),
              f"{s.get('ingresos_acumulados_delta_pct',0):+.1f}%",
              help=s.get("ingresos_acumulados_detail",""))
    c4.metric("Desvío presupuesto", f"{s.get('desvio_presupuesto_pct',0):.1f}%",
              f"{s.get('desvio_presupuesto_delta_pct',0):+.1f}%",
              delta_color="inverse" if s.get("desvio_presupuesto_pct",0) < 0 else "normal",
              help=s.get("desvio_presupuesto_detail",""))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Margen hoy", fmt_ars(s.get("margen_hoy_ars",0)))
    c6.metric("Ventas hoy", fmt_ars(s.get("ventas_hoy_ars",0)))
    c7.metric("Packout comercial", f"{s.get('packout_comercial_pct',0):.1f}%",
              f"{s.get('packout_comercial_delta_pct',0):+.1f}%",
              help=s.get("packout_comercial_detail",""))
    c8.metric("Cobranza abierta", fmt_ars(s.get("cobranza_abierta_ars",0)),
              delta_color="inverse")

    st.divider()

    # ── Serie resultado diario ────────────────────────────────────────────────
    resultado = series.get("resultado_diario", [])
    if resultado:
        df = pd.DataFrame(resultado)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df[(df["ingresos_ars"] > 0) | (df["costos_ars"] > 0)].tail(90)

        ca, cb = st.columns(2)
        with ca:
            st.subheader("📊 Ingresos vs Costos diarios")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df["fecha"], y=df["ingresos_ars"],
                name="Ingresos", marker_color=COLORS[0], opacity=0.85,
                hovertemplate="%{x|%d %b}<br>Ingresos: $%{y:,.0f}<extra></extra>",
            ))
            fig.add_trace(go.Bar(
                x=df["fecha"], y=df["costos_ars"],
                name="Costos", marker_color=COLORS[3], opacity=0.75,
                hovertemplate="%{x|%d %b}<br>Costos: $%{y:,.0f}<extra></extra>",
            ))
            fig.update_layout(barmode="group")
            apply_chart_style(fig, height=300)
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            st.subheader("📈 Margen acumulado")
            df["margen_acum"] = df["margen_ars"].cumsum()
            fig2 = go.Figure(go.Scatter(
                x=df["fecha"], y=df["margen_acum"],
                fill="tozeroy",
                fillcolor="rgba(48,148,90,0.13)",
                line=dict(color=COLORS[0], width=2.5),
                hovertemplate="%{x|%d %b}<br>Margen acum.: $%{y:,.0f}<extra></extra>",
            ))
            apply_chart_style(fig2, height=300, legend=False)
            add_hline(fig2, 0, "Equilibrio", color=WARNING)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Breakdown ─────────────────────────────────────────────────────────────
    cc, cd = st.columns(2)

    with cc:
        st.subheader("🏠 Margen por establecimiento")
        est = breakdown.get("margen_establecimiento", [])
        if est:
            df_e = pd.DataFrame(est).sort_values("margen_ars", ascending=True)
            bar_col = [COLORS[0] if v >= 0 else COLORS[3] for v in df_e["margen_ars"]]
            fig3 = go.Figure(go.Bar(
                x=df_e["margen_ars"], y=df_e["establecimiento"],
                orientation="h", marker_color=bar_col, opacity=0.85,
                hovertemplate="<b>%{y}</b><br>Margen: $%{x:,.0f}<extra></extra>",
            ))
            add_vline(fig3, 0, "0", color=WARNING)
            apply_chart_style(fig3, height=300, legend=False, ygrid=False)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sin datos de establecimientos")

    with cd:
        st.subheader("💰 Costos por categoría")
        costos = breakdown.get("costos_categoria", [])
        if costos:
            df_k = pd.DataFrame(costos).sort_values("monto_ars", ascending=True)
            fig4 = go.Figure(go.Bar(
                x=df_k["monto_ars"],
                y=df_k["categoria"],
                orientation="h",
                marker_color=COLORS[2],
                opacity=0.9,
                hovertemplate="<b>%{y}</b><br>$%{x:,.0f}<extra></extra>",
            ))
            apply_chart_style(fig4, height=300, legend=False, ygrid=False)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Sin datos de costos")

    est = breakdown.get("margen_establecimiento", [])
    if est:
        st.subheader("🏷️ Estado económico por establecimiento")
        df_est = pd.DataFrame(est).copy()
        df_est["Estado"] = df_est.apply(establishment_status, axis=1)
        df_est = df_est[["establecimiento", "superficie_ha", "ingresos_ars", "costos_ars", "margen_ha_ars", "Estado"]]
        df_est.columns = ["Establecimiento", "Ha", "Ingresos ARS", "Costos ARS", "Margen/ha ARS", "Estado"]
        st.dataframe(
            df_est.sort_values("Margen/ha ARS", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Ha": st.column_config.NumberColumn(format="%.1f"),
                "Ingresos ARS": st.column_config.NumberColumn(format="$ %.0f"),
                "Costos ARS": st.column_config.NumberColumn(format="$ %.0f"),
                "Margen/ha ARS": st.column_config.NumberColumn(format="$ %.0f"),
            },
        )

    st.subheader("🎯 Foco ejecutivo")
    focus_col1, focus_col2, focus_col3 = st.columns(3)
    focus_col1.metric(
        "Aprovechamiento comercial",
        f"{s.get('packout_comercial_pct', 0):.1f}%",
        help=f"Estado: {packout_status(s.get('packout_comercial_pct', 0))}",
    )
    focus_col2.metric(
        "Días promedio de cobro",
        f"{s.get('dias_promedio_cobro', 0) or 0:.1f} días",
        help=f"Estado: {cobranza_status(s.get('dias_promedio_cobro'), s.get('cobranza_abierta_ars', 0))}",
    )
    focus_col3.metric(
        "Cobranza abierta",
        fmt_ars(s.get("cobranza_abierta_ars", 0)),
        help=f"Estado: {cobranza_status(s.get('dias_promedio_cobro'), s.get('cobranza_abierta_ars', 0))}",
    )

    # ── Ingresos/costos por canal ─────────────────────────────────────────────
    canal_data = breakdown.get("ingresos_costos_canal", [])
    if canal_data:
        st.subheader("📦 Ingresos, Costos y Margen por canal")
        df_c = pd.DataFrame(canal_data).sort_values("margen_ars", ascending=False)
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(name="Ingresos", x=df_c["canal"], y=df_c["ingresos_ars"],
                              marker_color=COLORS[0],
                              hovertemplate="%{x}<br>Ingresos: $%{y:,.0f}<extra></extra>"))
        fig5.add_trace(go.Bar(name="Costos", x=df_c["canal"], y=df_c["costos_ars"],
                              marker_color=COLORS[3],
                              hovertemplate="%{x}<br>Costos: $%{y:,.0f}<extra></extra>"))
        fig5.add_trace(go.Scatter(name="Margen", x=df_c["canal"], y=df_c["margen_ars"],
                                  mode="markers+lines", marker=dict(color=LEMON, size=10),
                                  line=dict(color=LEMON, dash="dot"),
                                  hovertemplate="%{x}<br>Margen: $%{y:,.0f}<extra></extra>"))
        fig5.update_layout(barmode="group")
        apply_chart_style(fig5, height=320)
        st.plotly_chart(fig5, use_container_width=True)

    # ── Ranking de lotes ──────────────────────────────────────────────────────
    ranking = breakdown.get("ranking_lotes", [])
    if ranking:
        st.subheader("📋 Ranking de lotes por margen")
        df_r = pd.DataFrame(ranking)[[
            "lote","establecimiento","variedad","margen_ha_ars","desvio_presupuesto_pct","packout_pct"
        ]].sort_values("margen_ha_ars", ascending=False)
        df_r.columns = ["Lote","Establecimiento","Variedad","Margen/ha ARS","Desvío presup. %","Packout %"]
        st.dataframe(df_r, use_container_width=True, hide_index=True)
