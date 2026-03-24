from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from api.client import (
    fetch_synagro_contratos,
    fetch_synagro_cosechas,
    fetch_synagro_flujo_caja,
    fetch_synagro_labores,
    fetch_synagro_lotes,
    fetch_synagro_ventas,
)
from plotly_theme import DANGER, NEUTRAL, SUCCESS, WARNING, add_hline, apply_chart_style


def _fmt_ars(value):
    value = float(value or 0)
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:,.0f}"


def _fmt_tn(value):
    value = float(value or 0)
    return f"{value:,.1f} tn"


def _empty_df(payload: dict, key: str = "items") -> pd.DataFrame:
    items = payload.get(key, []) if payload else []
    return pd.DataFrame(items) if items else pd.DataFrame()


def _status_card(title: str, tone: str, message: str):
    colors = {
        "good": ("#ecf8ef", "#2f8b56", "#d4ecd8"),
        "warn": ("#fff8df", "#b08b00", "#eadca0"),
        "bad": ("#fff0ee", "#cf6e63", "#efc3bc"),
        "neutral": ("#f5f4ef", "#776b5a", "#e1d8c9"),
    }
    bg, fg, border = colors.get(tone, colors["neutral"])
    st.markdown(
        f"""
        <div style="padding:14px 16px;border-radius:18px;background:{bg};border:1px solid {border};margin-bottom:10px;">
          <div style="font-size:11px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;color:{fg};">{title}</div>
          <div style="margin-top:6px;color:#1b241d;font-size:14px;line-height:1.45;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _prepare_data():
    lotes = fetch_synagro_lotes()
    cosechas = fetch_synagro_cosechas({"page": 1, "limit": 5000})
    labores = fetch_synagro_labores({"page": 1, "limit": 5000, "tipo": st.session_state.get("gf_tipo_labor")})
    contratos = fetch_synagro_contratos({"estado": st.session_state.get("gf_estado_contrato")})
    ventas = fetch_synagro_ventas()
    flujo = fetch_synagro_flujo_caja({"categoria": st.session_state.get("gf_categoria_flujo")})

    datasets = {
        "lotes": lotes,
        "cosechas": cosechas,
        "labores": labores,
        "contratos": contratos,
        "ventas": ventas,
        "flujo": flujo,
    }
    if not any(datasets.values()):
        return None

    df_lotes = _empty_df(lotes)
    df_cosechas = _empty_df(cosechas)
    df_labores = _empty_df(labores)
    df_contratos = _empty_df(contratos)
    df_ventas = _empty_df(ventas)
    df_flujo = _empty_df(flujo)

    for df, col in [
        (df_cosechas, "fecha"),
        (df_labores, "fecha"),
        (df_ventas, "fecha"),
        (df_flujo, "fecha"),
    ]:
        if not df.empty and col in df:
            df[col] = pd.to_datetime(df[col])

    return datasets, df_lotes, df_cosechas, df_labores, df_contratos, df_ventas, df_flujo


def _render_scope():
    current_scope = []
    if st.session_state.get("gf_empresa_nombre"):
        current_scope.append(st.session_state["gf_empresa_nombre"])
    if st.session_state.get("gf_campania_nombre"):
        current_scope.append(st.session_state["gf_campania_nombre"])
    if st.session_state.get("gf_establecimiento_nombre"):
        current_scope.append(st.session_state["gf_establecimiento_nombre"])
    if st.session_state.get("gf_cliente_nombre"):
        current_scope.append(st.session_state["gf_cliente_nombre"])
    if st.session_state.get("gf_desde") or st.session_state.get("gf_hasta"):
        current_scope.append(f"{st.session_state.get('gf_desde') or '...'} → {st.session_state.get('gf_hasta') or '...'}")
    if current_scope:
        st.caption(" · ".join(current_scope))


def _render_management_lenses():
    c1, c2, c3 = st.columns(3)
    with c1:
        _status_card(
            "Estratégico",
            "good",
            "Responde si el negocio va bien o mal mirando resultado, ventas, cobranzas y producción acumulada.",
        )
    with c2:
        _status_card(
            "Táctico",
            "neutral",
            "Explica por qué pasó: desvíos por lote, peso de labores, clientes y presión comercial.",
        )
    with c3:
        _status_card(
            "Operativo",
            "warn",
            "Muestra cómo avanzamos hoy con cosecha, labores, ventas y caja sobre el último corte operativo.",
        )


def _render_strategic(df_lotes, df_cosechas, df_labores, df_ventas, df_flujo):
    ventas_ars = float(df_ventas["importe_total_ars"].sum()) if not df_ventas.empty else 0.0
    cobranzas_ars = float(
        df_flujo.loc[(df_flujo["tipo"] == "ingreso") & (df_flujo["categoria"] == "cobranzas"), "importe_ars"].sum()
    ) if not df_flujo.empty else 0.0
    resultado_neto = float(df_flujo["importe_ars"].where(df_flujo["tipo"] == "ingreso", -df_flujo["importe_ars"]).sum()) if not df_flujo.empty else 0.0
    cosecha_tn = float(df_cosechas["produccion_total_tn"].sum()) if not df_cosechas.empty else 0.0
    conversion = cobranzas_ars / ventas_ars if ventas_ars else 0.0

    if resultado_neto > 0 and conversion >= 0.8:
        _status_card("Estratégico · Vamos bien", "good", "El período muestra resultado positivo y la cobranza acompaña a las ventas.")
    elif resultado_neto > 0:
        _status_card("Estratégico · Atención", "warn", "El negocio sigue positivo, pero la conversión de ventas a caja todavía está por debajo de lo deseado.")
    else:
        _status_card("Estratégico · Presión", "bad", "El resultado del período está bajo presión y requiere revisar caja, costos y ritmo comercial.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Resultado neto", _fmt_ars(resultado_neto))
    c2.metric("Ventas del período", _fmt_ars(ventas_ars))
    c3.metric("Cobranzas del período", _fmt_ars(cobranzas_ars), f"{conversion * 100:.1f}% de ventas")
    c4.metric("Cosecha acumulada", _fmt_tn(cosecha_tn))

    left, right = st.columns(2)
    with left:
        st.subheader("Resultado diario acumulado")
        if not df_flujo.empty:
            df_daily = (
                df_flujo.assign(net=lambda x: x["importe_ars"].where(x["tipo"] == "ingreso", -x["importe_ars"]))
                .groupby("fecha", as_index=False)["net"]
                .sum()
                .sort_values("fecha")
            )
            df_daily["acumulado"] = df_daily["net"].cumsum()
            fig = go.Figure(go.Scatter(
                x=df_daily["fecha"],
                y=df_daily["acumulado"],
                mode="lines",
                line=dict(color=SUCCESS, width=3),
                fill="tozeroy",
                fillcolor="rgba(48,148,90,0.12)",
                name="Resultado acumulado",
            ))
            add_hline(fig, 0, "Equilibrio", color=WARNING)
            apply_chart_style(fig, height=320, legend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin movimientos de flujo para el alcance actual.")

    with right:
        st.subheader("Balance operativo por establecimiento")
        if not df_cosechas.empty:
            prod_est = df_cosechas.groupby("establecimiento", as_index=False)["produccion_total_tn"].sum()
            if not df_labores.empty:
                cost_est = df_labores.groupby("establecimiento", as_index=False)["costo_total"].sum()
                merged = prod_est.merge(cost_est, on="establecimiento", how="left").fillna(0)
            else:
                merged = prod_est.assign(costo_total=0.0)
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(x=merged["establecimiento"], y=merged["produccion_total_tn"], name="Producción tn", marker_color=SUCCESS), secondary_y=False)
            fig.add_trace(go.Scatter(x=merged["establecimiento"], y=merged["costo_total"], name="Costo labores ARS", mode="lines+markers", line=dict(color=WARNING, width=2.5)), secondary_y=True)
            apply_chart_style(fig, height=320)
            fig.update_yaxes(title_text="Toneladas", secondary_y=False)
            fig.update_yaxes(title_text="ARS", secondary_y=True)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin cosechas para comparar establecimientos.")


def _render_tactical(df_lotes, df_cosechas, df_labores, df_contratos, df_ventas):
    _status_card("Táctico · Por qué pasó", "neutral", "Acá se explican los desvíos por lote, por tipo de labor y por cliente para entender la causa del resultado.")

    top_left, top_right = st.columns(2)
    with top_left:
        st.subheader("Costo de labores por tipo")
        if not df_labores.empty:
            by_type = df_labores.groupby("tipo", as_index=False)["costo_total"].sum().sort_values("costo_total", ascending=True)
            fig = go.Figure(go.Bar(
                x=by_type["costo_total"],
                y=by_type["tipo"],
                orientation="h",
                marker_color=WARNING,
                name="Costo",
            ))
            apply_chart_style(fig, height=320, legend=False, ygrid=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin labores para explicar costos.")

    with top_right:
        st.subheader("Ventas por cliente")
        if not df_ventas.empty:
            by_client = df_ventas.groupby("cliente", as_index=False)["importe_total_ars"].sum().sort_values("importe_total_ars", ascending=True)
            fig = go.Figure(go.Bar(
                x=by_client["importe_total_ars"],
                y=by_client["cliente"],
                orientation="h",
                marker_color=NEUTRAL,
                name="Ventas",
            ))
            apply_chart_style(fig, height=320, legend=False, ygrid=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin ventas para explicar cartera.")

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        st.subheader("Lotes con desvío de rendimiento")
        if not df_lotes.empty:
            df_delta = df_lotes.copy()
            df_delta["delta_pct"] = ((df_delta["rendimiento_real"] - df_delta["rendimiento_historico"]) / df_delta["rendimiento_historico"].replace(0, pd.NA)) * 100
            df_delta = df_delta.sort_values("delta_pct").head(10)
            fig = go.Figure(go.Bar(
                x=df_delta["delta_pct"],
                y=df_delta["nombre"],
                orientation="h",
                marker_color=[DANGER if v < 0 else SUCCESS for v in df_delta["delta_pct"]],
                name="Desvío %",
            ))
            add_hline(fig, 0, "Histórico", color=WARNING)
            apply_chart_style(fig, height=360, legend=False, ygrid=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin lotes para analizar desvío.")

    with bottom_right:
        st.subheader("Contratos y presión comercial")
        if not df_contratos.empty:
            df_contratos["valor_total_usd"] = df_contratos["valor_total_usd"].fillna(0)
            by_state = df_contratos.groupby("estado", as_index=False)["valor_total_usd"].sum()
            fig = go.Figure(go.Bar(
                x=by_state["estado"],
                y=by_state["valor_total_usd"],
                marker_color=[WARNING if estado != "cumplido" else SUCCESS for estado in by_state["estado"]],
                name="Valor USD",
            ))
            apply_chart_style(fig, height=360, legend=False)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sin contratos para evaluar presión comercial.")


def _render_operational(df_cosechas, df_labores, df_ventas, df_flujo):
    date_candidates = []
    for df in (df_cosechas, df_labores, df_ventas, df_flujo):
        if not df.empty and "fecha" in df.columns:
            date_candidates.append(df["fecha"].max())

    latest_date = max(date_candidates) if date_candidates else None
    if latest_date is None:
        st.info("Sin actividad reciente para lectura operativa.")
        return

    _status_card("Operativo · Cómo avanzamos hoy", "neutral", f"La lectura operativa toma como corte el último día con actividad: {latest_date.date().isoformat()}.")

    cosecha_hoy = float(df_cosechas.loc[df_cosechas["fecha"] == latest_date, "produccion_total_tn"].sum()) if not df_cosechas.empty else 0.0
    labores_hoy = int((df_labores["fecha"] == latest_date).sum()) if not df_labores.empty else 0
    ventas_hoy = float(df_ventas.loc[df_ventas["fecha"] == latest_date, "importe_total_ars"].sum()) if not df_ventas.empty else 0.0
    caja_hoy = float(
        df_flujo.loc[df_flujo["fecha"] == latest_date, "importe_ars"].where(df_flujo["tipo"] == "ingreso", -df_flujo["importe_ars"]).sum()
    ) if not df_flujo.empty else 0.0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cosecha del día", _fmt_tn(cosecha_hoy))
    c2.metric("Labores del día", f"{labores_hoy}")
    c3.metric("Ventas del día", _fmt_ars(ventas_hoy))
    c4.metric("Caja neta del día", _fmt_ars(caja_hoy))

    window_start = latest_date - timedelta(days=13)
    harvest_daily = (
        df_cosechas.loc[df_cosechas["fecha"] >= window_start].groupby("fecha", as_index=False)["produccion_total_tn"].sum()
        if not df_cosechas.empty
        else pd.DataFrame(columns=["fecha", "produccion_total_tn"])
    )
    sales_daily = (
        df_ventas.loc[df_ventas["fecha"] >= window_start].groupby("fecha", as_index=False)["importe_total_ars"].sum()
        if not df_ventas.empty
        else pd.DataFrame(columns=["fecha", "importe_total_ars"])
    )
    cash_daily = (
        df_flujo.loc[df_flujo["fecha"] >= window_start]
        .assign(net=lambda x: x["importe_ars"].where(x["tipo"] == "ingreso", -x["importe_ars"]))
        .groupby("fecha", as_index=False)["net"]
        .sum()
        if not df_flujo.empty
        else pd.DataFrame(columns=["fecha", "net"])
    )
    base_dates = pd.DataFrame({"fecha": pd.date_range(window_start, latest_date, freq="D")})
    daily = (
        base_dates.merge(harvest_daily, on="fecha", how="left")
        .merge(sales_daily, on="fecha", how="left")
        .merge(cash_daily, on="fecha", how="left")
        .fillna(0)
    )

    st.subheader("Ritmo de los últimos 14 días")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=daily["fecha"], y=daily["produccion_total_tn"], name="Cosecha tn", marker_color=SUCCESS), secondary_y=False)
    fig.add_trace(go.Scatter(x=daily["fecha"], y=daily["importe_total_ars"], name="Ventas ARS", mode="lines+markers", line=dict(color=WARNING, width=2.3)), secondary_y=True)
    fig.add_trace(go.Scatter(x=daily["fecha"], y=daily["net"], name="Caja neta ARS", mode="lines+markers", line=dict(color=DANGER, width=2.3, dash="dot")), secondary_y=True)
    apply_chart_style(fig, height=360)
    fig.update_yaxes(title_text="Toneladas", secondary_y=False)
    fig.update_yaxes(title_text="ARS", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Últimas labores")
        if not df_labores.empty:
            latest_labores = (
                df_labores.sort_values("fecha", ascending=False)
                [["fecha", "establecimiento", "lote", "tipo", "costo_total", "observacion"]]
                .head(12)
            )
            latest_labores.columns = ["Fecha", "Establecimiento", "Lote", "Tipo", "Costo total", "Observación"]
            st.dataframe(latest_labores, use_container_width=True, hide_index=True)
        else:
            st.info("Sin labores recientes.")
    with right:
        st.subheader("Últimas ventas y caja")
        if not df_ventas.empty:
            latest_sales = (
                df_ventas.sort_values("fecha", ascending=False)
                [["fecha", "cliente", "cantidad_tn", "importe_total_ars", "condicion_pago"]]
                .head(12)
            )
            latest_sales.columns = ["Fecha", "Cliente", "Cantidad tn", "Importe ARS", "Condición"]
            st.dataframe(latest_sales, use_container_width=True, hide_index=True)
        else:
            st.info("Sin ventas recientes.")


def _render_raw_erp(df_lotes, df_cosechas, df_labores, df_contratos, df_ventas, df_flujo):
    raw_tabs = st.tabs(["Lotes", "Cosechas", "Labores", "Contratos", "Ventas", "Flujo"])
    frames = [
        ("Lotes", df_lotes),
        ("Cosechas", df_cosechas),
        ("Labores", df_labores),
        ("Contratos", df_contratos),
        ("Ventas", df_ventas),
        ("Flujo", df_flujo),
    ]
    for tab, (label, df) in zip(raw_tabs, frames):
        with tab:
            st.subheader(label)
            if df.empty:
                st.info(f"Sin datos en {label.lower()}.")
            else:
                st.dataframe(df, use_container_width=True, hide_index=True)


def render():
    prepared = _prepare_data()
    if prepared is None:
        st.error("❌ No se pudo consultar la API Synagro simulada.")
        return

    (_, df_lotes, df_cosechas, df_labores, df_contratos, df_ventas, df_flujo) = prepared

    st.info(
        "🧾 Esta vista consulta la API Synagro simulada y la organiza para tres preguntas de gestión: "
        "¿vamos bien o mal?, ¿por qué pasó? y ¿cómo avanzamos hoy?"
    )
    _render_scope()
    _render_management_lenses()

    strategic_tab, tactical_tab, operational_tab, raw_tab = st.tabs(
        ["Estratégico", "Táctico", "Operativo", "ERP crudo"]
    )

    with strategic_tab:
        _render_strategic(df_lotes, df_cosechas, df_labores, df_ventas, df_flujo)
    with tactical_tab:
        _render_tactical(df_lotes, df_cosechas, df_labores, df_contratos, df_ventas)
    with operational_tab:
        _render_operational(df_cosechas, df_labores, df_ventas, df_flujo)
    with raw_tab:
        _render_raw_erp(df_lotes, df_cosechas, df_labores, df_contratos, df_ventas, df_flujo)
