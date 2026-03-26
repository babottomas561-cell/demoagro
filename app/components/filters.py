from __future__ import annotations

import streamlit as st


def render_global_filters(
    filter_options: dict[str, list[str]],
    snapshot_info: dict[str, object] | None = None,
) -> dict[str, object]:
    periods = filter_options.get("periods", [])
    default_periods = (periods[0], periods[-1]) if periods else (None, None)

    with st.sidebar:
        st.markdown("## Filtros")
        st.caption("Si un selector queda vacio, se interpreta como todos los valores.")

        if periods:
            period_start, period_end = st.select_slider(
                "Ventana temporal",
                options=periods,
                value=default_periods,
            )
        else:
            period_start, period_end = (None, None)

        campaigns = st.multiselect("Campania", filter_options.get("campaigns", []))
        crops = st.multiselect("Cultivo", filter_options.get("crops", []))
        products = st.multiselect("Producto", filter_options.get("products", []))
        clients = st.multiselect("Cliente", filter_options.get("clients", []))
        categories = st.multiselect("Categoria de stock", filter_options.get("categories", []))
        deposits = st.multiselect("Deposito", filter_options.get("deposits", []))
        deposit_types = st.multiselect("Tipo de deposito", filter_options.get("deposit_types", []))

        if snapshot_info:
            snapshot_date = snapshot_info.get("snapshot_date")
            if snapshot_date:
                st.markdown("## Alcance")
                st.caption("El rango temporal afecta resultado, ventas y operaciones.")
                st.caption(f"Stock, CxC y CxP se muestran al ultimo snapshot: {snapshot_date}.")
                snapshot_period = snapshot_info.get("snapshot_period")
                if snapshot_period and period_start and period_end:
                    if str(period_end) < str(snapshot_period) or str(period_start) > str(snapshot_period):
                        st.warning(
                            "Elegiste un corte historico. Los flujos siguen el periodo, "
                            "pero los snapshots se mantienen al ultimo cierre disponible."
                        )

    return {
        "period_start": period_start,
        "period_end": period_end,
        "campaigns": campaigns,
        "crops": crops,
        "products": products,
        "clients": clients,
        "categories": categories,
        "deposits": deposits,
        "deposit_types": deposit_types,
    }
