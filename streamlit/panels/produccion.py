import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from api.client import fetch_produccion
from plotly_theme import apply_chart_style, add_hline, add_vline, apply_pie_style
from ui_helpers import render_alerts, render_panel_context

COLORS = ["#30945a", "#74866f", "#a79c89", "#cf6e63", "#c1b29a"]
LEMON   = "#c8a800"
OBJ_KG_HA = 25_000   # benchmark industria Tucumán


def fmt_kg(v):
    if v >= 1_000_000: return f"{v/1_000_000:.2f}M kg"
    if v >= 1_000:     return f"{v/1_000:.1f} t"
    return f"{v:,.0f} kg"


def pct(numerator, denominator):
    if not denominator:
        return 0.0
    return numerator / denominator * 100


def lot_status(row):
    desvio = float(row.get("desvio_pct", 0) or 0)
    packout = float(row.get("packout_pct", 0) or 0)
    if desvio >= 0 and packout >= 57:
        return "Fuerte"
    if desvio >= -15 and packout >= 52:
        return "Seguimiento"
    return "Crítico"


def establishment_status(row):
    desvio = float(row.get("desvio_pct", 0) or 0)
    if desvio >= -5:
        return "En línea"
    if desvio >= -15:
        return "Seguimiento"
    return "Crítico"


def render():
    data = fetch_produccion()
    if not data:
        st.error("❌ Sin conexión con el backend")
        return

    meta      = data.get("meta", {})
    s         = data.get("summary", {})
    series    = data.get("series", {})
    breakdown = data.get("breakdown", {})
    alerts    = data.get("alerts", [])

    # ── Alertas del backend ───────────────────────────────────────────────────
    render_alerts(alerts)

    st.info(
        "📘 La calidad exportable se empieza a definir en finca: rendimiento, condición sanitaria y manejo de cosecha "
        "impactan después en packout, rechazos y precio."
    )

    render_panel_context(meta)

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    kg_cos  = s.get("kg_cosechados", 0)
    plan_kg = s.get("plan_kg", 0)
    kg_pie  = max(0, plan_kg - kg_cos)

    c1.metric("Kg Cosechados", fmt_kg(kg_cos),
              f"{s.get('kg_cosechados_delta_pct',0):+.1f}% vs campaña ant.",
              help=s.get("kg_cosechados_detail",""))
    c2.metric("Kg en Pie (restantes)", fmt_kg(kg_pie),
              help="Plan campaña menos lo ya cosechado")
    c3.metric("Rend. Proyectado", f"{s.get('rendimiento_proyectado_kg_ha',0):,.0f} kg/ha",
              f"{s.get('rendimiento_proyectado_delta_pct',0):+.1f}%",
              help=s.get("rendimiento_proyectado_detail",""))
    c4.metric("Packout Promedio", f"{s.get('packout_promedio_pct',0):.1f}%",
              f"{s.get('packout_promedio_delta_pct',0):+.1f}%",
              delta_color="normal" if s.get("packout_promedio_pct",0) >= s.get("packout_objetivo_pct",57.5) else "inverse",
              help=s.get("packout_promedio_detail",""))

    # ── Avance cosecha (barra de progreso) ───────────────────────────────────
    avance = s.get("avance_cosecha_pct", 0) / 100
    st.markdown(f"**Avance de cosecha: {s.get('avance_cosecha_pct',0):.1f}%** "
                f"{'✅' if avance >= 0.9 else '⚠️' if avance >= 0.75 else '🔴'} "
                f"*(objetivo: 90%)*")
    st.progress(min(avance, 1.0))

    # ── KPI row 2 ─────────────────────────────────────────────────────────────
    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Kg/Jornalero/día", f"{s.get('kg_jornalero',0):,.0f}",
              f"{s.get('kg_jornalero_delta_pct',0):+.1f}%",
              help=s.get("kg_jornalero_detail","Ref. industria: 2.000–2.500 kg/jornalero/día"))
    c6.metric("Costo Cosecha/kg", f"${s.get('costo_kg_ars',0):.2f} ARS",
              f"{s.get('costo_kg_ars_delta_pct',0):+.1f}%",
              delta_color="inverse",
              help=s.get("costo_kg_ars_detail",""))
    c7.metric("Lotes bajo objetivo", str(s.get("lotes_bajo_objetivo",0)),
              f"{s.get('lotes_bajo_objetivo_delta_pct',0):+.0f}",
              delta_color="inverse",
              help=s.get("lotes_bajo_objetivo_detail",""))
    c8.metric("Lotes riesgo hídrico", str(s.get("lotes_riesgo_hidrico",0)),
              delta_color="inverse")

    st.divider()

    # ── Series temporales ─────────────────────────────────────────────────────
    cosecha = series.get("cosecha_diaria", [])
    if cosecha:
        df = pd.DataFrame(cosecha)
        df["fecha"] = pd.to_datetime(df["fecha"])
        df_act = df[df["kg_cosechados"] > 0]

        ca, cb = st.columns(2)
        with ca:
            st.subheader("📊 Cosecha diaria (kg)")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_act["fecha"], y=df_act["kg_cosechados"],
                name="Kg/día", marker_color=COLORS[0], opacity=0.85,
                hovertemplate="%{x|%d %b}<br><b>%{y:,.0f} kg</b><extra></extra>",
            ))
            apply_chart_style(fig, height=300, legend=False)
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            st.subheader("📈 Acumulado vs Plan")
            fig2 = go.Figure()
            fig2.add_trace(go.Scatter(
                x=df_act["fecha"], y=df_act["kg_plan_acumulado"],
                name="Plan", line=dict(color=LEMON, width=2, dash="dot"),
                hovertemplate="%{x|%d %b}<br>Plan: %{y:,.0f} kg<extra></extra>",
            ))
            fig2.add_trace(go.Scatter(
                x=df_act["fecha"], y=df_act["kg_acumulados"],
                name="Real", line=dict(color=COLORS[0], width=2.5),
                fill="tonexty", fillcolor="rgba(48,148,90,0.09)",
                hovertemplate="%{x|%d %b}<br>Real: %{y:,.0f} kg<extra></extra>",
            ))
            apply_chart_style(fig2, height=300)
            st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Breakdown: rendimiento por lote ───────────────────────────────────────
    lotes = breakdown.get("rendimiento_lotes", [])
    if lotes:
        df_l = pd.DataFrame(lotes)
        cc, cd = st.columns(2)

        with cc:
            st.subheader("🌿 Rendimiento por lote (kg/ha proyectado)")
            df_l_s = df_l.sort_values("kg_ha_proyectado", ascending=True).tail(15)
            bar_colors = [COLORS[0] if v >= OBJ_KG_HA else COLORS[3]
                          for v in df_l_s["kg_ha_proyectado"]]
            fig3 = go.Figure(go.Bar(
                x=df_l_s["kg_ha_proyectado"],
                y=df_l_s["lote"],
                orientation="h",
                marker_color=bar_colors,
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} kg/ha<extra></extra>",
            ))
            add_vline(fig3, OBJ_KG_HA, f"Obj {OBJ_KG_HA:,}")
            apply_chart_style(fig3, height=360, legend=False, ygrid=False)
            st.plotly_chart(fig3, use_container_width=True)

        with cd:
            st.subheader("🍊 Producción por establecimiento y variedad")
            var = breakdown.get("produccion_variedad_establecimiento", [])
            if var:
                df_v = pd.DataFrame(var)
                fig4 = go.Figure()
                variedades = list(df_v["variedad"].drop_duplicates())
                for i, variedad in enumerate(variedades):
                    subset = df_v[df_v["variedad"] == variedad]
                    fig4.add_trace(go.Bar(
                        x=subset["establecimiento"],
                        y=subset["kg_cosechados_tn"],
                        name=variedad,
                        marker_color=COLORS[i % len(COLORS)],
                        hovertemplate="<b>%{x}</b><br>Variedad: " + variedad + "<br>Real: %{y:.1f} tn<extra></extra>",
                    ))
                plan = df_v.groupby("establecimiento", as_index=False)["kg_plan_tn"].sum()
                fig4.add_trace(go.Scatter(
                    x=plan["establecimiento"],
                    y=plan["kg_plan_tn"],
                    name="Plan",
                    mode="markers+lines",
                    marker=dict(color=LEMON, size=10),
                    line=dict(color=LEMON, dash="dot"),
                    hovertemplate="<b>%{x}</b><br>Plan: %{y:.1f} tn<extra></extra>",
                ))
                fig4.update_layout(barmode="stack")
                apply_chart_style(fig4, height=360)
                st.plotly_chart(fig4, use_container_width=True)

    variedad_est = breakdown.get("produccion_variedad_establecimiento", [])
    if variedad_est:
        st.subheader("🏷️ Estado productivo por establecimiento")
        df_est = pd.DataFrame(variedad_est)
        df_est = df_est.groupby("establecimiento", as_index=False)[["kg_cosechados_tn", "kg_plan_tn"]].sum()
        df_est["desvio_pct"] = (
            (df_est["kg_cosechados_tn"] - df_est["kg_plan_tn"]) / df_est["kg_plan_tn"].replace({0: pd.NA}) * 100
        ).fillna(0.0)
        df_est["Estado"] = df_est.apply(establishment_status, axis=1)
        df_est.columns = ["Establecimiento", "Tn reales", "Tn plan", "Desvío %", "Estado"]
        st.dataframe(
            df_est.sort_values("Tn reales", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Tn reales": st.column_config.NumberColumn(format="%.1f"),
                "Tn plan": st.column_config.NumberColumn(format="%.1f"),
                "Desvío %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    # ── Ranking bajo rendimiento ──────────────────────────────────────────────
    ranking = breakdown.get("ranking_bajo_rendimiento", [])
    if ranking:
        st.subheader("🔴 Lotes con menor rendimiento")
        df_r = pd.DataFrame(ranking).head(8)
        df_r["Estado"] = df_r.apply(lot_status, axis=1)
        df_r = df_r[[
            "lote","establecimiento","variedad","kg_ha_proyectado","objetivo_kg_ha","desvio_pct","packout_pct"
        ] + ["Estado"]]
        df_r.columns = ["Lote","Establecimiento","Variedad","Rend. proy. kg/ha","Obj. kg/ha","Desvío %","Packout %","Estado"]
        st.dataframe(
            df_r,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Rend. proy. kg/ha": st.column_config.NumberColumn(format="%.0f"),
                "Obj. kg/ha": st.column_config.NumberColumn(format="%.0f"),
                "Desvío %": st.column_config.NumberColumn(format="%.1f%%"),
                "Packout %": st.column_config.NumberColumn(format="%.1f%%"),
            },
        )

    st.subheader("🎯 Foco de campo")
    worst_lot = ranking[0] if ranking else None
    f1, f2, f3 = st.columns(3)
    f1.metric("Avance de cosecha", f"{s.get('avance_cosecha_pct', 0):.1f}%")
    f2.metric("Lotes atrasados", f"{s.get('lotes_atrasados', 0)}")
    if worst_lot:
        f3.metric(
            "Lote más comprometido",
            worst_lot.get("codigo_lote", worst_lot.get("lote", "—")),
            help=f"Desvío {worst_lot.get('desvio_pct', 0):.1f}% · Packout {worst_lot.get('packout_pct', 0):.1f}%",
        )
        st.info(
            f"Prioridad operativa: {worst_lot.get('codigo_lote', worst_lot.get('lote', '—'))} en "
            f"{worst_lot.get('establecimiento', '—')} con desvío de {worst_lot.get('desvio_pct', 0):.1f}% "
            f"y packout de {worst_lot.get('packout_pct', 0):.1f}%."
        )
