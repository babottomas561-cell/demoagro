import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from api.client import fetch_macro
from plotly_theme import apply_chart_style, add_vline
from ui_helpers import render_alerts, render_panel_context

COLORS     = ["#30945a", "#74866f", "#a79c89", "#cf6e63", "#c1b29a"]
WATER_BLUE = "#5ba4cf"
LEMON      = "#c8a800"


def render():
    data = fetch_macro()
    if not data:
        st.error("❌ Sin conexión con el backend")
        return

    meta      = data.get("meta", {})
    s         = data.get("summary", {})
    series    = data.get("series", {})
    breakdown = data.get("breakdown", {})
    alerts    = data.get("alerts", [])

    render_alerts(alerts)
    render_panel_context(meta)

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TC Exportación", f"${s.get('tc_exportacion',0):,.2f}",
              f"{s.get('tc_delta_pct',0):+.2f}%",
              help=s.get("tc_detail","Tipo de cambio oficial exportación"))
    c2.metric("Inflación mensual", f"{s.get('inflacion_mensual_pct',0):.2f}%",
              f"{s.get('inflacion_delta_pct',0):+.2f}%",
              delta_color="inverse",
              help=s.get("inflacion_detail","Presión sobre costos en ARS"))
    c3.metric("Precio export. USD/tn", f"USD {s.get('precio_exportacion_usd_tn',0):,.2f}",
              f"{s.get('precio_exportacion_delta_pct',0):+.2f}%",
              help=s.get("precio_exportacion_detail","Precio prom. ponderado entre mercados activos"))
    c4.metric("Flete USD/tn", f"USD {s.get('costo_flete_usd_tn',0):,.2f}",
              f"{s.get('costo_flete_delta_pct',0):+.2f}%",
              delta_color="inverse",
              help=s.get("costo_flete_detail","Costo logístico medio mercados exportadores"))

    # Precio neto estimado (precio - flete)
    precio_neto = s.get("precio_exportacion_usd_tn", 0) - s.get("costo_flete_usd_tn", 0)
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Precio jugo USD/tn", f"USD {s.get('precio_jugo_usd_tn',0):,.0f}",
              f"{s.get('precio_jugo_delta_pct',0):+.2f}%",
              help=s.get("precio_jugo_detail","Precio spot jugo 400gpl FOB Argentina"))
    c6.metric("Presión macro", f"{s.get('presion_macro_pct',0):.1f}%",
              delta_color="inverse",
              help="Indicador compuesto de presión macroeconómica sobre el negocio")
    c7.metric("Energía ARS/kWh", f"${s.get('costo_energia_ars_kwh',0):.2f}",
              delta_color="inverse")
    c8.metric("Precio neto est. (exc. flete)", f"USD {precio_neto:,.0f}/tn",
              help="Precio exportación menos flete — proxy del margen logístico")

    st.divider()

    # ── Serie macro semanal ───────────────────────────────────────────────────
    macro_sem = series.get("macro_semanal", [])
    if macro_sem:
        df = pd.DataFrame(macro_sem)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df = df[df["tc_exportacion"] > 0]

        ca, cb = st.columns(2)
        with ca:
            st.subheader("💱 Tipo de cambio exportación")
            fig = go.Figure(go.Scatter(
                x=df["fecha"], y=df["tc_exportacion"],
                line=dict(color=COLORS[0], width=2.5),
                fill="tozeroy", fillcolor="rgba(48,148,90,0.09)",
                hovertemplate="%{x|%d %b}<br><b>TC: ${%{y:,.2f}}</b><extra></extra>",
            ))
            apply_chart_style(fig, height=300, legend=False)
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            st.subheader("📈 Precio export. vs Flete (USD/tn)")
            df_filt = df[df["precio_exportacion_usd_tn"] > 0]
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df_filt["fecha"], y=df_filt["precio_exportacion_usd_tn"],
                name="Precio export.", line=dict(color=COLORS[0], width=2.5),
                hovertemplate="%{x|%d %b}<br>Precio: USD %{y:,.0f}/tn<extra></extra>",
            ))
            fig2.add_trace(go.Scatter(
                x=df_filt["fecha"], y=df_filt["flete_usd_tn"],
                name="Flete", line=dict(color=COLORS[3], width=2, dash="dot"),
                hovertemplate="%{x|%d %b}<br>Flete: USD %{y:,.0f}/tn<extra></extra>",
            ))
            # Precio neto en la serie
            if "flete_usd_tn" in df_filt.columns:
                df_filt = df_filt.copy()
                df_filt["precio_neto"] = df_filt["precio_exportacion_usd_tn"] - df_filt["flete_usd_tn"]
                fig2.add_trace(go.Scatter(
                    x=df_filt["fecha"], y=df_filt["precio_neto"],
                    name="Neto (exc. flete)", line=dict(color=LEMON, width=1.5, dash="dashdot"),
                    hovertemplate="%{x|%d %b}<br>Neto: USD %{y:,.0f}/tn<extra></extra>",
                ))
            apply_chart_style(fig2, height=300)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Breakdown ─────────────────────────────────────────────────────────────
    mercados  = breakdown.get("mercados", [])
    ranking   = breakdown.get("ranking_mercados", [])
    costos_e  = breakdown.get("costos_externos", [])
    variables = breakdown.get("variables", [])

    cc, cd = st.columns(2)
    with cc:
        st.subheader("🌍 Margen bruto por mercado (USD/tn)")
        if mercados:
            df_m = pd.DataFrame(mercados).sort_values("margen_bruto_usd_tn", ascending=True)
            bar_col = [COLORS[0] if v >= 0 else COLORS[3] for v in df_m["margen_bruto_usd_tn"]]
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                x=df_m["margen_bruto_usd_tn"], y=df_m["mercado"],
                orientation="h", marker_color=bar_col, opacity=0.9,
                name="Margen bruto",
                hovertemplate="<b>%{y}</b><br>Margen: USD %{x:,.0f}/tn<extra></extra>",
            ))
            fig3.add_trace(go.Scatter(
                x=df_m["precio_exportacion_usd_tn"], y=df_m["mercado"],
                mode="markers", name="Precio export.",
                marker=dict(color=LEMON, size=9, symbol="diamond"),
                hovertemplate="<b>%{y}</b><br>Precio: USD %{x:,.0f}/tn<extra></extra>",
            ))
            add_vline(fig3, 0, "0", color=LEMON)
            apply_chart_style(fig3, height=300, ygrid=False)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sin datos de mercados")

    with cd:
        st.subheader("💸 Costos externos por rubro")
        if costos_e:
            df_ce = pd.DataFrame(costos_e)
            # valor puede ser numérico o string
            try:
                df_ce["valor_num"] = pd.to_numeric(df_ce["valor"], errors="coerce")
                df_num = df_ce.dropna(subset=["valor_num"]).sort_values("valor_num", ascending=False)
                if not df_num.empty:
                    fig4 = go.Figure(go.Bar(
                        x=df_num["valor_num"], y=df_num["rubro"],
                        orientation="h", marker_color=COLORS[2], opacity=0.85,
                        hovertemplate="<b>%{y}</b><br>%{x}<extra></extra>",
                    ))
                    apply_chart_style(fig4, height=300, legend=False, ygrid=False)
                    st.plotly_chart(fig4, use_container_width=True)
                else:
                    # mostrar como tabla si no son numéricos
                    st.dataframe(df_ce[["rubro","valor"]], use_container_width=True, hide_index=True)
            except Exception:
                st.dataframe(pd.DataFrame(costos_e), use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos de costos externos")

    # ── Variables macro ───────────────────────────────────────────────────────
    if variables:
        st.subheader("📊 Variables macroeconómicas clave")
        df_var = pd.DataFrame(variables)
        st.dataframe(df_var, use_container_width=True, hide_index=True)
