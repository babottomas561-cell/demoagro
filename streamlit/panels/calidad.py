import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from api.client import fetch_calidad
from plotly_theme import apply_chart_style, add_hline, add_vline, apply_pie_style
from ui_helpers import render_alerts, render_panel_context

COLORS = ["#30945a", "#74866f", "#a79c89", "#cf6e63", "#c1b29a"]
LEMON  = "#c8a800"

GUIDE_NOTE = (
    "Guía CEC exportación 2018: mirar calidad mínima, madurez/coloración, calibre, "
    "tolerancias, presentación e inocuidad/trazabilidad. Este panel lo traduce en "
    "packout útil, rechazo, calibres exportables, defectos sanitarios y lotes fuera de rango."
)


def export_status(row: pd.Series) -> str:
    if row.get("packout_pct", 0) >= row.get("objetivo_packout_pct", 0) and row.get("rechazo_pct", 0) < 10:
        return "Apto"
    if row.get("packout_pct", 0) >= row.get("objetivo_packout_pct", 0) - 4 and row.get("rechazo_pct", 0) < 14:
        return "Seguimiento"
    return "Crítico"


def calibre_status(row: pd.Series) -> str:
    if not row.get("apto_exportacion", False):
        return "No exportable"
    if row.get("participacion_pct", 0) >= 12:
        return "Clave"
    return "Complementario"


def defect_status(row: pd.Series) -> str:
    name = str(row.get("defecto", "")).lower()
    category = str(row.get("categoria", "")).lower()
    pct = row.get("participacion_pct", 0)
    if ("mancha" in name or "negra" in name) and pct > 2:
        return "Barrera"
    if category == "sanitario" and pct >= 10:
        return "Crítico"
    if pct >= 12:
        return "Seguimiento"
    return "Controlado"


def export_board_status(summary: dict) -> str:
    packout = float(summary.get("packout_promedio_pct", 0) or 0)
    sanitario = float(summary.get("riesgo_sanitario_pct", 0) or 0)
    trazabilidad = float(summary.get("trazabilidad_pct", 0) or 0)
    if packout >= 58 and sanitario <= 12 and trazabilidad >= 98:
        return "Apto"
    if packout >= 54 and sanitario <= 18 and trazabilidad >= 95:
        return "Seguimiento"
    return "Crítico"


def tolerance_status(summary: dict) -> str:
    sanitario = float(summary.get("riesgo_sanitario_pct", 0) or 0)
    fuera = float(summary.get("lotes_fuera_tolerancia", 0) or 0)
    if sanitario <= 10 and fuera <= 2:
        return "Controlado"
    if sanitario <= 16 and fuera <= 4:
        return "Seguimiento"
    return "Presión"


def render():
    data = fetch_calidad()
    if not data:
        st.error("❌ Sin conexión con el backend")
        return

    meta      = data.get("meta", {})
    s         = data.get("summary", {})
    series    = data.get("series", {})
    breakdown = data.get("breakdown", {})
    alerts    = data.get("alerts", [])

    render_alerts(alerts)

    st.info(f"📘 {GUIDE_NOTE}")

    # ── Alerta mancha negra ───────────────────────────────────────────────────
    defectos = breakdown.get("defectos_tipo", [])
    if defectos:
        df_def = pd.DataFrame(defectos)
        mancha = df_def[df_def["defecto"].str.lower().str.contains("mancha|negra", na=False)]
        if not mancha.empty and mancha.iloc[0]["participacion_pct"] > 2:
            st.error(f"🚨 ALERTA UE: Mancha negra supera el 2% ({mancha.iloc[0]['participacion_pct']:.1f}%) — riesgo de barrera fitosanitaria")

    render_panel_context(meta)
    st.caption(f"Campaña **{meta.get('campania','—')}**")

    # Defecto dominante
    if defectos:
        df_def = pd.DataFrame(defectos)
        dom = df_def.sort_values("participacion_pct", ascending=False).iloc[0]
        st.info(f"🔍 Defecto dominante del período: **{dom['defecto']}** ({dom['participacion_pct']:.1f}% del rechazo) — categoría: {dom.get('categoria','—')}")

    export_status_label = export_board_status(s)
    tolerance_label = tolerance_status(s)

    # ── KPI row 1 ─────────────────────────────────────────────────────────────
    obj = s.get("packout_objetivo_pct", 57.5)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Aptitud exportadora", f"{s.get('packout_promedio_pct',0):.1f}%",
              f"{s.get('packout_promedio_delta_pct',0):+.1f}%",
              delta_color="normal" if s.get("packout_promedio_pct",0) >= obj else "inverse",
              help=f"{s.get('packout_promedio_detail','')} Estado: {export_status_label}")
    c2.metric("Calibre exportable", f"{s.get('calibre_exportable_pct',0):.1f}%",
              help=s.get("calibre_exportable_detail",""))
    c3.metric("Tolerancia sanitaria", f"{s.get('riesgo_sanitario_pct',0):.1f}%",
              help=f"{s.get('riesgo_sanitario_detail','')} Estado: {tolerance_label}")
    c4.metric("Trazabilidad", f"{s.get('trazabilidad_pct',0):.1f}%",
              help=s.get("trazabilidad_detail",""))

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("Packout hoy", f"{s.get('packout_hoy_pct',0):.1f}%",
              delta_color="normal" if s.get("packout_hoy_pct",0) >= obj else "inverse")
    c6.metric("Industria", f"{s.get('industria_share_pct',0):.1f}%",
              help="Parte de la fruta que no llega a fresco y se deriva a industria.")
    c7.metric("Descarte", f"{s.get('descarte_share_pct',0):.1f}%",
              help="Fruta que no logra salida comercial ni industrial útil.")
    c8.metric("Lotes fuera tolerancia", str(s.get("lotes_fuera_tolerancia", s.get('lotes_criticos', 0))),
              f"{s.get('lotes_criticos_delta_pct',0):+.0f}", delta_color="inverse")

    st.subheader("🎯 Foco exportación")
    f1, f2, f3 = st.columns(3)
    f1.metric("Estado general", export_status_label)
    f2.metric("Control de tolerancia", tolerance_label)
    f3.metric("Share exportación", f"{s.get('exportacion_share_pct',0):.1f}%",
              f"{s.get('exportacion_delta_pct',0):+.1f}%",
              help=s.get("exportacion_detail",""))
    st.caption(
        "Lectura guía: calidad mínima + tolerancias + trazabilidad. Si cae el packout útil o sube el riesgo sanitario, "
        "la fruta pierde aptitud exportadora y se desplaza a industria o descarte."
    )

    st.divider()

    # ── Serie diaria ──────────────────────────────────────────────────────────
    cal_d = series.get("calidad_diaria", [])
    if cal_d:
        df = pd.DataFrame(cal_d)
        df["fecha"] = pd.to_datetime(df["fecha"])

        ca, cb = st.columns(2)
        with ca:
            st.subheader("📈 Packout diario (%)")
            df["color"] = df["packout_pct"].apply(lambda v: COLORS[0] if v >= obj else COLORS[3])
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df["fecha"], y=df["packout_pct"],
                mode="lines+markers",
                line=dict(color=COLORS[0], width=2.8),
                marker=dict(size=7, color=df["color"]),
                fill="tozeroy",
                fillcolor="rgba(48,148,90,0.08)",
                hovertemplate="%{x|%d %b}<br><b>Packout: %{y:.1f}%</b><extra></extra>",
            ))
            add_hline(fig, obj, f"Obj {obj:.0f}%")
            apply_chart_style(fig, height=300, legend=False, hovermode="x unified")
            fig.update_yaxes(range=[0, 105])
            st.plotly_chart(fig, use_container_width=True)

        with cb:
            st.subheader("📏 Calibres y aptitud exportación")
            calibres = breakdown.get("calibres_exportacion", [])
            if calibres:
                df_cal = pd.DataFrame(calibres).sort_values("kg", ascending=True)
                fig2 = go.Figure(go.Bar(
                    x=df_cal["kg"],
                    y=df_cal["calibre"],
                    orientation="h",
                    marker_color=[COLORS[0] if ok else COLORS[3] for ok in df_cal["apto_exportacion"]],
                    customdata=df_cal[["participacion_pct", "banda_mm", "apto_exportacion"]],
                    hovertemplate=(
                        "<b>%{y}</b><br>%{x:,.0f} kg"
                        "<br>%{customdata[0]:.1f}% del clasificado"
                        "<br>%{customdata[1]}"
                        "<br>Apto exportación: %{customdata[2]}"
                        "<extra></extra>"
                    ),
                ))
                apply_chart_style(fig2, height=300, legend=False, ygrid=False)
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("Sin distribución de calibres")

    st.divider()

    # ── Breakdown ─────────────────────────────────────────────────────────────
    cc, cd = st.columns(2)

    with cc:
        st.subheader("🍊 Destino de fruta")
        dest = breakdown.get("destino_fruta", [])
        if dest:
            df_d = pd.DataFrame(dest).sort_values("kg", ascending=True)
            color_map = {
                "Fresco exportación": COLORS[0],
                "Fresco local": COLORS[1],
                "Industria": LEMON,
                "Descarte": COLORS[3],
            }
            fig3 = go.Figure(go.Bar(
                x=df_d["kg"],
                y=df_d["destino"],
                orientation="h",
                marker_color=[color_map.get(v, COLORS[2]) for v in df_d["destino"]],
                customdata=df_d["participacion_pct"],
                hovertemplate="<b>%{y}</b><br>%{x:,.0f} kg<br>%{customdata:.1f}%<extra></extra>",
            ))
            apply_chart_style(fig3, height=300, legend=False, ygrid=False)
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sin datos de destino")

    with cd:
        st.subheader("🔍 Defectos por tipo (% del rechazo)")
        if defectos:
            df_def2 = pd.DataFrame(defectos).sort_values("participacion_pct", ascending=True)
            mancha_mask = df_def2["defecto"].str.lower().str.contains("mancha|negra", na=False)
            bar_col = [COLORS[3] if m else COLORS[2] for m in mancha_mask]
            fig4 = go.Figure(go.Bar(
                x=df_def2["participacion_pct"], y=df_def2["defecto"],
                orientation="h", marker_color=bar_col, opacity=0.9,
                hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
            ))
            add_vline(fig4, 2, "Límite UE 2%", color=COLORS[3])
            apply_chart_style(fig4, height=300, legend=False, ygrid=False)
            st.plotly_chart(fig4, use_container_width=True)
        else:
            st.info("Sin defectos registrados")

    calibres = breakdown.get("calibres_exportacion", [])
    if calibres:
        st.subheader("📏 Estado de calibres")
        df_cal_t = pd.DataFrame(calibres)
        df_cal_t["Estado"] = df_cal_t.apply(calibre_status, axis=1)
        df_cal_t = df_cal_t[["calibre", "banda_mm", "participacion_pct", "apto_exportacion", "Estado"]]
        df_cal_t.columns = ["Calibre", "Banda", "% clasificado", "Apto exportación", "Estado"]
        st.dataframe(df_cal_t, use_container_width=True, hide_index=True)

    if defectos:
        st.subheader("🦠 Estado de defectos")
        df_def_t = pd.DataFrame(defectos)
        df_def_t["Estado"] = df_def_t.apply(defect_status, axis=1)
        df_def_t = df_def_t[["defecto", "categoria", "participacion_pct", "Estado"]]
        df_def_t.columns = ["Defecto", "Categoría", "% del rechazo", "Estado"]
        st.dataframe(df_def_t, use_container_width=True, hide_index=True)

    # ── Packout por lote ──────────────────────────────────────────────────────
    packout_l = breakdown.get("packout_lotes", [])
    if packout_l:
        st.subheader("📋 Cumplimiento exportación por lote")
        df_pl = pd.DataFrame(packout_l)
        df_pl["Estado exportación"] = df_pl.apply(export_status, axis=1)
        df_pl["Desvío vs obj %"] = (df_pl["packout_pct"] - df_pl["objetivo_packout_pct"]).round(1)
        order_map = {"Crítico": 0, "Seguimiento": 1, "Apto": 2}
        df_pl["order_estado"] = df_pl["Estado exportación"].map(order_map).fillna(3)
        df_pl = df_pl[[
            "lote","establecimiento","variedad","packout_pct","objetivo_packout_pct",
            "Desvío vs obj %","rechazo_pct","principal_defecto","Estado exportación","order_estado"
        ]].sort_values(["order_estado", "packout_pct", "rechazo_pct"], ascending=[True, True, False])
        df_pl = df_pl.drop(columns=["order_estado"])
        df_pl.columns = [
            "Lote","Establecimiento","Variedad","Packout %","Obj. Packout %",
            "Desvío vs obj %","Rechazo %","Defecto principal","Estado"
        ]
        st.dataframe(df_pl, use_container_width=True, hide_index=True)
        st.caption("Estado calculado con packout vs objetivo y rechazo operativo como proxy de tolerancia exportadora.")
