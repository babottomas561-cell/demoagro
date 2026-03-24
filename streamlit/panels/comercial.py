import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from api.client import fetch_comercial
from plotly_theme import apply_chart_style, add_hline, apply_pie_style
from ui_helpers import render_alerts, render_panel_context

COLORS = ["#30945a", "#74866f", "#a79c89", "#cf6e63", "#c1b29a"]
LEMON  = "#c8a800"

# Precios de referencia por mercado (FOB Argentina, benchmarks industria)
REF_PRICES = {
    "UE": (900, 1400), "Europa": (900, 1400), "USA": (800, 1200),
    "Rusia": (600, 900), "Chile": (400, 700), "Industria": (1800, 2500),
}


def fmt_ars(v):
    if abs(v) >= 1_000_000_000: return f"${v/1_000_000_000:.1f}B"
    if abs(v) >= 1_000_000:     return f"${v/1_000_000:.1f}M"
    if abs(v) >= 1_000:         return f"${v/1_000:.0f}K"
    return f"${v:,.0f}"


def pct(numerator, denominator):
    if not denominator:
        return 0.0
    return numerator / denominator * 100


def market_status(row):
    real = float(row.get("precio_promedio_usd_tn", 0) or 0)
    ref = float(row.get("precio_referencia_usd_tn", 0) or 0)
    if real <= 0 and ref <= 0:
        return "Sin operaciones"
    if ref <= 0:
        return "Sin referencia"
    gap_pct = pct(real - ref, ref)
    if gap_pct >= 3:
        return "Premium"
    if gap_pct >= -5:
        return "En línea"
    return "Bajo presión"


def collection_status(row):
    abierto = float(row.get("saldo_abierto_ars", 0) or 0)
    vencido = float(row.get("vencido_ars", 0) or 0)
    facturas = float(row.get("facturas_abiertas", 0) or 0)
    vencido_pct = pct(vencido, abierto)
    if abierto <= 0:
        return "Al día"
    if vencido_pct >= 15 or facturas >= 40:
        return "Riesgo"
    if vencido > 0:
        return "Seguimiento"
    return "Al día"


def channel_status(row):
    real = float(row.get("precio_promedio_usd_tn", 0) or 0)
    ref = float(row.get("precio_referencia_usd_tn", 0) or 0)
    part = float(row.get("participacion_pct", 0) or 0)
    if part < 5:
        return "Nicho"
    if ref <= 0:
        return "Sin referencia"
    gap_pct = pct(real - ref, ref)
    if gap_pct >= 3:
        return "Fuerte"
    if gap_pct >= -5:
        return "Estable"
    return "Presión"


def render():
    data = fetch_comercial()
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
        "📘 No existe un único precio del limón: el valor depende de mercado, canal y del volumen que logra "
        "cumplir calidad mínima, calibre y tolerancias de exportación."
    )

    render_panel_context(meta)

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    obj_precio = s.get("precio_objetivo_usd_tn", 0)
    precio_real = s.get("precio_realizado_usd_tn", 0)
    precio_ref  = s.get("precio_referencia_usd_tn", 0)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Precio realizado", f"USD {precio_real:,.0f}/tn",
              f"{s.get('precio_delta_pct',0):+.1f}%",
              delta_color="normal" if precio_real >= obj_precio else "inverse",
              help=s.get("precio_detail",""))
    c2.metric("Precio referencia mercado", f"USD {precio_ref:,.0f}/tn",
              help="Precio de referencia según el mercado y canal activo de hoy")
    c3.metric("Volumen exportado", f"{s.get('volumen_exportado_tn',0):,.1f} tn",
              f"{s.get('volumen_delta_pct',0):+.1f}%",
              help=s.get("volumen_detail",""))
    c4.metric("Cobrado acumulado", fmt_ars(s.get("cobrado_ars",0)))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Cobranza abierta", fmt_ars(s.get("cobranza_abierta_ars",0)),
              f"{s.get('cobranza_delta_pct',0):+.1f}%",
              delta_color="inverse",
              help=s.get("cobranza_detail",""))
    c6.metric("Pendiente entrega", f"{s.get('pendiente_entrega_tn',0):,.1f} tn",
              f"{s.get('pendiente_delta_pct',0):+.1f}%",
              help=s.get("pendiente_detail",""))
    c7.metric("Cumplimiento contratos", f"{s.get('cumplimiento_contratos_pct',0):.1f}%",
              delta_color="normal" if s.get("cumplimiento_contratos_pct",0) >= 90 else "inverse")
    c8.metric("Precio objetivo", f"USD {obj_precio:,.0f}/tn")

    contexto_mercado = s.get("precio_contexto_mercado")
    contexto_canal = s.get("precio_contexto_canal")
    contexto_volumen = s.get("precio_contexto_volumen_tn")
    if contexto_mercado or contexto_canal:
        st.caption(
            f"Contexto del precio de hoy: **{contexto_canal or '—'}** en **{contexto_mercado or '—'}**"
            + (f" · {contexto_volumen:,.1f} tn" if contexto_volumen else "")
        )

    st.divider()

    # ── Series: precio diario + volumen semanal ───────────────────────────────
    precio_d  = series.get("precio_diario", [])
    vol_sem   = series.get("precio_volumen_semanal", [])

    ca, cb = st.columns(2)
    with ca:
        st.subheader("📈 Precio realizado vs referencia (USD/tn)")
        if precio_d:
            df = pd.DataFrame(precio_d)
            df["fecha"] = pd.to_datetime(df["fecha"])
            df = df[df["precio_promedio_usd_tn"] > 0]
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["fecha"], y=df["precio_referencia_usd_tn"],
                name="Referencia", line=dict(color=LEMON, width=1.5, dash="dot"),
                hovertemplate="%{x|%d %b}<br>Ref: USD %{y:,.0f}<extra></extra>",
            ))
            fig.add_trace(go.Scatter(
                x=df["fecha"], y=df["precio_realizado_usd_tn"],
                name="Realizado", line=dict(color=COLORS[0], width=2.8),
                mode="lines+markers",
                marker=dict(size=6, color=COLORS[0]),
                fill="tozeroy",
                fillcolor="rgba(48,148,90,0.08)",
                hovertemplate="%{x|%d %b}<br>Real: USD %{y:,.0f}<extra></extra>",
            ))
            add_hline(fig, obj_precio, f"Obj USD {obj_precio:,.0f}", color=COLORS[3], dash="dash")
            apply_chart_style(fig, height=300, hovermode="x unified")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin serie de precios")

    with cb:
        st.subheader("📊 Volumen exportado semanal (tn)")
        if vol_sem:
            df2 = pd.DataFrame(vol_sem)
            df2["fecha"] = pd.to_datetime(df2["fecha"])
            df2 = df2[df2["volumen_tn"] > 0]
            fig2 = go.Figure(go.Bar(
                x=df2["fecha"], y=df2["volumen_tn"],
                marker_color=COLORS[0], opacity=0.85,
                hovertemplate="%{x|%d %b}<br><b>%{y:,.1f} tn</b><extra></extra>",
            ))
            apply_chart_style(fig2, height=300, legend=False)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Sin datos de volumen semanal")

    st.divider()

    # ── Breakdown: mercados ───────────────────────────────────────────────────
    mercados  = breakdown.get("mercados", [])
    clientes  = breakdown.get("ranking_clientes", [])
    contratos = breakdown.get("estado_contratos", [])
    mix_c     = breakdown.get("mix_canal", [])
    canales   = breakdown.get("canales", [])
    cobranzas = breakdown.get("clientes_cobranza", [])

    cc, cd = st.columns(2)
    with cc:
        st.subheader("🌍 Precio realizado vs referencia por mercado")
        if mercados:
            df_m = pd.DataFrame(mercados).sort_values("precio_promedio_usd_tn", ascending=True)
            fig3 = go.Figure()
            fig3.add_trace(go.Bar(
                x=df_m["precio_promedio_usd_tn"], y=df_m["mercado"],
                name="Realizado", orientation="h", marker_color=COLORS[0], opacity=0.9,
                hovertemplate="<b>%{y}</b><br>Realizado: USD %{x:,.0f}/tn<extra></extra>",
            ))
            fig3.add_trace(go.Scatter(
                x=df_m["precio_referencia_usd_tn"], y=df_m["mercado"],
                name="Referencia", mode="markers",
                marker=dict(color=LEMON, size=10, symbol="diamond"),
                hovertemplate="<b>%{y}</b><br>Ref: USD %{x:,.0f}/tn<extra></extra>",
            ))
            apply_chart_style(fig3, height=320, ygrid=False)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sin datos de mercados")

    with cd:
        st.subheader("📦 Mix por canal (tn)")
        if mix_c:
            df_mix = pd.DataFrame(mix_c).sort_values("toneladas", ascending=True)
            fig4 = go.Figure(go.Bar(
                x=df_mix["toneladas"],
                y=df_mix["canal"],
                orientation="h",
                marker_color=[COLORS[0], LEMON, COLORS[1]][:len(df_mix)],
                customdata=df_mix["participacion_pct"],
                hovertemplate="<b>%{y}</b><br>%{x:.1f} tn<br>%{customdata:.1f}% del mix<extra></extra>",
            ))
            apply_chart_style(fig4, height=320, legend=False, ygrid=False)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Sin datos de canal")

    ce, cf = st.columns(2)
    with ce:
        st.subheader("🌍 Estado por mercado")
        if mercados:
            df_m_table = pd.DataFrame(mercados).copy()
            df_m_table["gap_pct"] = (
                (df_m_table["precio_promedio_usd_tn"] - df_m_table["precio_referencia_usd_tn"])
                / df_m_table["precio_referencia_usd_tn"].replace({0: pd.NA})
                * 100
            ).fillna(0.0)
            df_m_table["Estado"] = df_m_table.apply(market_status, axis=1)
            df_m_table = df_m_table[
                ["mercado", "toneladas", "participacion_pct", "precio_promedio_usd_tn", "precio_referencia_usd_tn", "gap_pct", "Estado"]
            ].sort_values("toneladas", ascending=False)
            df_m_table.columns = ["Mercado", "Tn", "% mix", "Real USD/tn", "Ref USD/tn", "Gap %", "Estado"]
            st.dataframe(
                df_m_table,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Tn": st.column_config.NumberColumn(format="%.1f"),
                    "% mix": st.column_config.NumberColumn(format="%.1f%%"),
                    "Real USD/tn": st.column_config.NumberColumn(format="USD %.0f"),
                    "Ref USD/tn": st.column_config.NumberColumn(format="USD %.0f"),
                    "Gap %": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )
        else:
            st.info("Sin estado de mercados")

    with cf:
        st.subheader("💳 Riesgo de cobranza por cliente")
        if cobranzas:
            df_cob = pd.DataFrame(cobranzas).copy()
            df_cob["vencido_pct"] = (
                df_cob["vencido_ars"] / df_cob["saldo_abierto_ars"].replace({0: pd.NA}) * 100
            ).fillna(0.0)
            df_cob["Estado"] = df_cob.apply(collection_status, axis=1)
            df_cob = df_cob[
                ["cliente", "saldo_abierto_ars", "vencido_ars", "vencido_pct", "facturas_abiertas", "Estado"]
            ].sort_values(["vencido_pct", "saldo_abierto_ars"], ascending=[False, False]).head(10)
            df_cob.columns = ["Cliente", "Abierto ARS", "Vencido ARS", "% vencido", "Facturas", "Estado"]
            st.dataframe(
                df_cob,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Abierto ARS": st.column_config.NumberColumn(format="$ %.0f"),
                    "Vencido ARS": st.column_config.NumberColumn(format="$ %.0f"),
                    "% vencido": st.column_config.NumberColumn(format="%.1f%%"),
                    "Facturas": st.column_config.NumberColumn(format="%d"),
                },
            )
        else:
            st.info("Sin cuentas abiertas")

    # ── Estado de contratos ───────────────────────────────────────────────────
    if contratos:
        st.subheader("📋 Estado de contratos por canal")
        df_con = pd.DataFrame(contratos)
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(name="Contratado", x=df_con["canal"], y=df_con["contratado_tn"],
                              marker_color=COLORS[1], opacity=0.7,
                              hovertemplate="%{x}<br>Contratado: %{y:,.1f} tn<extra></extra>"))
        fig5.add_trace(go.Bar(name="Entregado", x=df_con["canal"], y=df_con["entregado_tn"],
                              marker_color=COLORS[0],
                              hovertemplate="%{x}<br>Entregado: %{y:,.1f} tn<extra></extra>"))
        fig5.add_trace(go.Bar(name="Pendiente", x=df_con["canal"], y=df_con["pendiente_tn"],
                              marker_color=LEMON, opacity=0.8,
                              hovertemplate="%{x}<br>Pendiente: %{y:,.1f} tn<extra></extra>"))
        fig5.update_layout(barmode="group")
        apply_chart_style(fig5, height=300)
        fig5.update_yaxes(title="Toneladas")
        st.plotly_chart(fig5, use_container_width=True)

    if canales:
        st.subheader("📑 Estado económico por canal")
        df_can = pd.DataFrame(canales).copy()
        df_can["gap_pct"] = (
            (df_can["precio_promedio_usd_tn"] - df_can["precio_referencia_usd_tn"])
            / df_can["precio_referencia_usd_tn"].replace({0: pd.NA})
            * 100
        ).fillna(0.0)
        df_can["Estado"] = df_can.apply(channel_status, axis=1)
        df_can = df_can[
            ["canal", "toneladas", "participacion_pct", "precio_promedio_usd_tn", "precio_referencia_usd_tn", "gap_pct", "Estado"]
        ].sort_values("toneladas", ascending=False)
        df_can.columns = ["Canal", "Tn", "% mix", "Real USD/tn", "Ref USD/tn", "Gap %", "Estado"]
        st.dataframe(
            df_can,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tn": st.column_config.NumberColumn(format="%.1f"),
                "% mix": st.column_config.NumberColumn(format="%.1f%%"),
                "Real USD/tn": st.column_config.NumberColumn(format="USD %.0f"),
                "Ref USD/tn": st.column_config.NumberColumn(format="USD %.0f"),
                "Gap %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    # ── Top clientes ──────────────────────────────────────────────────────────
    if clientes:
        st.subheader("👥 Top clientes por revenue")
        df_cli = pd.DataFrame(clientes)[[
            "cliente","mercado","toneladas","precio_promedio_usd_tn","revenue_usd"
        ]].sort_values("revenue_usd", ascending=False).head(10)
        df_cli.columns = ["Cliente","Mercado","Tn","Precio prom. USD/tn","Revenue USD"]
        st.dataframe(df_cli, use_container_width=True, hide_index=True)
