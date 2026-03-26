from __future__ import annotations

from pathlib import Path

import pandas as pd

from demoagro.db.sqlite import connect_sqlite, default_sqlite_path

MART_TABLES = [
    "mart_finance_period",
    "mart_working_capital_ar",
    "mart_working_capital_ap",
    "mart_working_capital_summary",
    "mart_operations_lot_campaign",
    "mart_operations_period",
    "mart_sales_period",
    "mart_stock_snapshot",
    "mart_metric_catalog",
]

SUPPORT_TABLES = [
    "erp_clientes",
    "erp_centros_costo",
    "erp_campanias",
    "erp_lote_campania",
    "erp_cosechas",
    "erp_lotes_calidad",
    "erp_analisis_calidad",
    "erp_ordenes_compra",
    "erp_ordenes_compra_det",
    "erp_recepciones_compra",
    "erp_proveedores",
    "erp_productos",
    "erp_depositos",
    "fin_facturas_compra",
    "fin_facturas_compra_det",
    "fin_facturas_venta",
    "fin_facturas_venta_det",
    "cont_asientos",
    "cont_asientos_det",
    "cont_plan_cuentas",
    "tax_posiciones_fiscales_periodo",
    "rrhh_categorias",
    "rrhh_empleados",
    "rrhh_liquidaciones",
    "rrhh_novedades",
    "mnt_activos",
    "mnt_ordenes_trabajo",
    "mnt_ordenes_trabajo_det",
    "mnt_paradas_activo",
    "log_transportistas",
    "log_viajes",
    "log_viajes_det",
]

AGING_BUCKET_ORDER = ["Al dia", "1-30", "31-60", "61-90", "90+", "Sin vencimiento"]


def load_dashboard_bundle(db_path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    resolved_path = Path(db_path) if db_path else default_sqlite_path()
    connection = connect_sqlite(resolved_path)
    try:
        bundle: dict[str, pd.DataFrame] = {}
        for table_name in MART_TABLES + SUPPORT_TABLES:
            bundle[table_name] = pd.read_sql_query(f'SELECT * FROM "{table_name}"', connection)
        return bundle
    finally:
        connection.close()


def get_filter_options(bundle: dict[str, pd.DataFrame]) -> dict[str, list[str]]:
    finance = bundle["mart_finance_period"]
    operations_period = bundle["mart_operations_period"]
    operations_lot = bundle["mart_operations_lot_campaign"]
    sales_period = bundle["mart_sales_period"]
    stock = bundle["mart_stock_snapshot"]
    customers = bundle["erp_clientes"]

    periods = _sorted_unique(
        finance.get("period_id", pd.Series(dtype="object")),
        operations_period.get("period_id", pd.Series(dtype="object")),
        sales_period.get("period_id", pd.Series(dtype="object")),
    )
    return {
        "periods": periods,
        "campaigns": _sorted_unique(operations_lot.get("campaign_code", pd.Series(dtype="object"))),
        "crops": _sorted_unique(operations_lot.get("crop_code", pd.Series(dtype="object"))),
        "products": _sorted_unique(
            sales_period.get("product_code", pd.Series(dtype="object")),
            stock.get("product_code", pd.Series(dtype="object")),
        ),
        "product_names": _sorted_unique(
            sales_period.get("product_name", pd.Series(dtype="object")),
            stock.get("product_name", pd.Series(dtype="object")),
        ),
        "clients": _sorted_unique(customers.get("client_name", pd.Series(dtype="object"))),
        "categories": _sorted_unique(stock.get("category_code", pd.Series(dtype="object"))),
        "deposits": _sorted_unique(stock.get("deposit_name", pd.Series(dtype="object"))),
        "deposit_types": _sorted_unique(stock.get("deposit_type", pd.Series(dtype="object"))),
    }


def get_finance_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    finance = bundle["mart_finance_period"].copy()
    finance = _apply_period_filter(finance, "period_id", filters)
    return finance.sort_values("period_id").reset_index(drop=True)


def get_operations_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    operations = bundle["mart_operations_period"].copy()
    operations = _apply_period_filter(operations, "period_id", filters)
    operations = _apply_selection(operations, "crop_code", filters.get("crops"))
    return operations.sort_values(["period_id", "crop_code"]).reset_index(drop=True)


def get_operations_lot_campaign(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    operations = bundle["mart_operations_lot_campaign"].copy()
    operations["period_id"] = pd.to_datetime(operations["fecha"], errors="coerce").dt.strftime("%Y-%m")
    operations = _apply_period_filter(operations, "period_id", filters)
    operations = _apply_selection(operations, "campaign_code", filters.get("campaigns"))
    operations = _apply_selection(operations, "crop_code", filters.get("crops"))
    operations = _apply_selection(operations, "product_code", filters.get("products"))
    return operations.sort_values(["campaign_code", "product_code", "lot_name"]).reset_index(drop=True)


def get_sales_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    sales = bundle["mart_sales_period"].copy()
    sales = _apply_period_filter(sales, "period_id", filters)
    sales = _apply_selection(sales, "product_code", filters.get("products"))
    sales["sales_mix_pct"] = _share(sales["revenue_net"])
    return sales.sort_values(["period_id", "revenue_net"], ascending=[True, False]).reset_index(drop=True)


def get_stock_snapshot(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    stock = bundle["mart_stock_snapshot"].copy()
    product_uoms = bundle["erp_productos"][["producto_id", "uom_code"]].copy()
    stock = stock.merge(product_uoms, on="producto_id", how="left")
    stock = _apply_selection(stock, "product_code", filters.get("products"))
    stock = _apply_selection(stock, "category_code", filters.get("categories"))
    stock = _apply_selection(stock, "deposit_name", filters.get("deposits"))
    stock = _apply_selection(stock, "deposit_type", filters.get("deposit_types"))
    stock["stock_value_share_pct"] = _share(stock["stock_value"])
    stock["unit_value"] = _safe_divide(stock["stock_value"], stock["quantity"])
    return stock.sort_values("stock_value", ascending=False).reset_index(drop=True)


def build_sales_customer_view(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    invoices = bundle["fin_facturas_venta"][["factura_venta_id", "cliente_id", "invoice_date"]].copy()
    details = bundle["fin_facturas_venta_det"][
        ["factura_venta_id", "producto_id", "quantity", "unit_price", "net_amount"]
    ].copy()
    customers = bundle["erp_clientes"][["cliente_id", "client_name"]].copy()
    products = bundle["erp_productos"][["producto_id", "product_code"]].copy()

    sales = (
        invoices.merge(details, on="factura_venta_id", how="left")
        .merge(customers, on="cliente_id", how="left")
        .merge(products, on="producto_id", how="left")
    )
    sales["period_id"] = pd.to_datetime(sales["invoice_date"], errors="coerce").dt.strftime("%Y-%m")
    sales = _apply_period_filter(sales, "period_id", filters)
    sales = _apply_selection(sales, "product_code", filters.get("products"))
    sales = _apply_selection(sales, "client_name", filters.get("clients"))

    grouped = sales.groupby(["cliente_id", "client_name"], as_index=False).agg(
        revenue_net=("net_amount", "sum"),
        sold_tons=("quantity", "sum"),
        invoice_count=("factura_venta_id", "nunique"),
        last_invoice_date=("invoice_date", "max"),
    )
    grouped["avg_unit_price"] = _safe_divide(grouped["revenue_net"], grouped["sold_tons"])
    grouped["revenue_share_pct"] = _share(grouped["revenue_net"])
    return grouped.sort_values("revenue_net", ascending=False).reset_index(drop=True)


def get_ar_aging(bundle: dict[str, pd.DataFrame], filters: dict[str, object]) -> pd.DataFrame:
    ar = bundle["mart_working_capital_ar"].copy()
    ar = _apply_selection(ar, "client_name", filters.get("clients"))
    return ar.sort_values(["days_overdue", "open_amount"], ascending=[False, False]).reset_index(drop=True)


def get_ap_aging(bundle: dict[str, pd.DataFrame], _filters: dict[str, object]) -> pd.DataFrame:
    ap = bundle["mart_working_capital_ap"].copy()
    return ap.sort_values(["days_overdue", "open_amount"], ascending=[False, False]).reset_index(drop=True)


def summarize_aging(aging_df: pd.DataFrame) -> pd.DataFrame:
    if aging_df.empty:
        return pd.DataFrame(columns=["aging_bucket", "open_amount", "document_count"])

    summary = aging_df.groupby("aging_bucket", as_index=False).agg(
        open_amount=("open_amount", "sum"),
        document_count=(aging_df.columns[1], "count"),
    )
    summary["aging_bucket"] = pd.Categorical(
        summary["aging_bucket"],
        categories=AGING_BUCKET_ORDER,
        ordered=True,
    )
    return summary.sort_values("aging_bucket").reset_index(drop=True)


def build_product_overview(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    sales = get_sales_period(bundle, filters)
    stock = get_stock_snapshot(bundle, filters)
    operations = get_operations_lot_campaign(bundle, filters)

    sales_grouped = sales.groupby(["product_code", "product_name"], as_index=False).agg(
        sold_tons=("sold_tons", "sum"),
        revenue_net=("revenue_net", "sum"),
    )
    sales_grouped["avg_sale_price"] = _safe_divide(sales_grouped["revenue_net"], sales_grouped["sold_tons"])

    stock_grouped = stock.groupby(["product_code", "product_name"], as_index=False).agg(
        stock_qty=("quantity", "sum"),
        stock_value=("stock_value", "sum"),
    )

    operations_grouped = operations.groupby(["product_code", "product_name"], as_index=False).agg(
        harvested_tons=("toneladas_netas", "sum"),
        direct_cost_total=("direct_cost_total", "sum"),
        gross_output_value=("gross_output_value", "sum"),
    )
    operations_grouped["direct_cost_per_ton"] = _safe_divide(
        operations_grouped["direct_cost_total"],
        operations_grouped["harvested_tons"],
    )

    overview = sales_grouped.merge(stock_grouped, on=["product_code", "product_name"], how="outer")
    overview = overview.merge(operations_grouped, on=["product_code", "product_name"], how="outer")
    numeric_columns = [
        "sold_tons",
        "revenue_net",
        "avg_sale_price",
        "stock_qty",
        "stock_value",
        "harvested_tons",
        "direct_cost_total",
        "gross_output_value",
        "direct_cost_per_ton",
    ]
    for column in numeric_columns:
        if column in overview.columns:
            overview[column] = overview[column].fillna(0.0)
    overview = overview[(overview["sold_tons"] > 0) | (overview["harvested_tons"] > 0) | (overview["stock_qty"] > 0)]
    return overview.sort_values("revenue_net", ascending=False).reset_index(drop=True)


def build_executive_kpis(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, object]]:
    return build_period_kpis(bundle, filters) + build_snapshot_kpis(bundle, filters)


def build_period_kpis(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, object]]:
    finance = get_finance_period(bundle, filters)
    operations = get_operations_period(bundle, filters)
    latest_label = finance["period_id"].max() if not finance.empty else "Sin datos"

    return [
        {
            "label": "Ingresos netos",
            "value": float(finance["revenue_net"].sum()) if not finance.empty else 0.0,
            "format": "currency",
            "detail": f"Ultimo periodo visible: {latest_label}",
            "tone": "neutral",
        },
        {
            "label": "Margen bruto",
            "value": float(finance["gross_margin"].sum()) if not finance.empty else 0.0,
            "format": "currency",
            "detail": f"% bruto: {_safe_divide(finance['gross_margin'].sum(), finance['revenue_net'].sum()):.1%}"
            if not finance.empty
            else "Sin datos",
            "tone": "success" if finance["gross_margin"].sum() >= 0 else "danger",
        },
        {
            "label": "EBITDA aprox.",
            "value": float(finance["ebitda_approx"].sum()) if not finance.empty else 0.0,
            "format": "currency",
            "detail": "Gerencial acumulado",
            "tone": "success" if finance["ebitda_approx"].sum() >= 0 else "danger",
        },
        {
            "label": "Flujo de fondos neto",
            "value": float(finance["net_cash_flow"].sum()) if not finance.empty else 0.0,
            "format": "currency",
            "detail": "Cobranza menos pagos y nomina",
            "tone": "success" if finance["net_cash_flow"].sum() >= 0 else "warning",
        },
        {
            "label": "Produccion total",
            "value": float(operations["production_tons"].sum()) if not operations.empty else 0.0,
            "format": "tons",
            "detail": "Toneladas netas cosechadas",
            "tone": "neutral",
        },
    ]


def build_snapshot_kpis(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, object]]:
    snapshot = get_snapshot_metadata(bundle, filters)
    stock = get_stock_snapshot(bundle, filters)
    ar = get_ar_aging(bundle, filters)
    ap = get_ap_aging(bundle, filters)

    overdue_ar = float(ar.loc[ar["days_overdue"] > 0, "open_amount"].sum()) if not ar.empty else 0.0
    overdue_ap = float(ap.loc[ap["days_overdue"] > 0, "open_amount"].sum()) if not ap.empty else 0.0
    top_stock = stock.iloc[0]["product_name"] if not stock.empty else "Sin stock"
    top_stock_share = float(stock.iloc[0]["stock_value_share_pct"]) if not stock.empty else 0.0
    snapshot_date = snapshot["snapshot_date"] or "Sin snapshot"
    snapshot_detail = f"Snapshot actual: {snapshot_date}"

    return [
        {
            "label": "Stock valorizado",
            "value": float(stock["stock_value"].sum()) if not stock.empty else 0.0,
            "format": "currency",
            "detail": f"{snapshot_detail}. Mayor posicion: {top_stock} ({top_stock_share:.1%})",
            "tone": "neutral",
        },
        {
            "label": "CxC abiertas",
            "value": float(ar["open_amount"].sum()) if not ar.empty else 0.0,
            "format": "currency",
            "detail": f"{snapshot_detail}. Vencido: {overdue_ar:,.0f}",
            "tone": "warning" if overdue_ar > 0 else "success",
        },
        {
            "label": "CxP abiertas",
            "value": float(ap["open_amount"].sum()) if not ap.empty else 0.0,
            "format": "currency",
            "detail": f"{snapshot_detail}. Vencido: {overdue_ap:,.0f}",
            "tone": "warning" if overdue_ap > 0 else "success",
        },
    ]


def get_snapshot_metadata(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object] | None = None,
) -> dict[str, object]:
    summary = bundle["mart_working_capital_summary"].copy()
    snapshot_date = str(summary.iloc[0]["snapshot_date"]) if not summary.empty else None
    snapshot_period = snapshot_date[:7] if snapshot_date else None
    period_start = None if not filters else filters.get("period_start")
    period_end = None if not filters else filters.get("period_end")
    excludes_snapshot = bool(
        snapshot_period
        and period_start
        and period_end
        and (str(period_end) < snapshot_period or str(period_start) > snapshot_period)
    )
    return {
        "snapshot_date": snapshot_date,
        "snapshot_period": snapshot_period,
        "period_excludes_snapshot": excludes_snapshot,
    }


def build_executive_alerts(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, str]]:
    finance = get_finance_period(bundle, filters)
    stock = get_stock_snapshot(bundle, filters)
    ar = get_ar_aging(bundle, filters)
    operations = get_operations_lot_campaign(bundle, filters)
    snapshot = get_snapshot_metadata(bundle, filters)

    alerts: list[dict[str, str]] = []

    if snapshot["period_excludes_snapshot"]:
        alerts.append(
            {
                "level": "info",
                "title": "Alcance mixto de lectura",
                "body": (
                    f"El rango temporal afecta flujos del periodo. "
                    f"Stock y capital de trabajo siguen en snapshot {snapshot['snapshot_date']}."
                ),
            }
        )

    overdue_ar = float(ar.loc[ar["days_overdue"] > 0, "open_amount"].sum()) if not ar.empty else 0.0
    if overdue_ar > 0:
        alerts.append(
            {
                "level": "warning",
                "title": "Capital trabado en cobranzas",
                "body": (
                    f"Hay USD {overdue_ar:,.0f} vencidos en cuentas por cobrar "
                    f"al snapshot {snapshot['snapshot_date']}."
                ),
            }
        )

    negative_months = finance.loc[finance["ebitda_approx"] < 0, "period_id"].tolist() if not finance.empty else []
    if negative_months:
        alerts.append(
            {
                "level": "danger",
                "title": "Meses con EBITDA negativo",
                "body": f"Se detectaron {len(negative_months)} periodos en rojo dentro del filtro actual.",
            }
        )

    if not stock.empty and float(stock.iloc[0]["stock_value_share_pct"]) > 0.35:
        alerts.append(
            {
                "level": "warning",
                "title": "Concentracion alta de inventario",
                "body": (
                    f"{stock.iloc[0]['product_name']} concentra "
                    f"{float(stock.iloc[0]['stock_value_share_pct']):.1%} del valor de stock "
                    f"al snapshot {snapshot['snapshot_date']}."
                ),
            }
        )

    under_target = operations.loc[operations["yield_vs_target_pct"] < 0.92] if not operations.empty else pd.DataFrame()
    if not under_target.empty:
        alerts.append(
            {
                "level": "info",
                "title": "Lotes bajo objetivo",
                "body": f"{len(under_target)} lotes quedaron por debajo del 92% del rendimiento objetivo.",
            }
        )

    if not alerts:
        alerts.append(
            {
                "level": "success",
                "title": "Sin desvíos críticos",
                "body": "El corte actual no muestra alertas prioritarias para gerencia.",
            }
        )
    return alerts


def get_working_capital_overview(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    ar = get_ar_aging(bundle, filters)
    ap = get_ap_aging(bundle, filters)
    ar_open = float(ar["open_amount"].sum()) if not ar.empty else 0.0
    ap_open = float(ap["open_amount"].sum()) if not ap.empty else 0.0
    ar_overdue = float(ar.loc[ar["days_overdue"] > 0, "open_amount"].sum()) if not ar.empty else 0.0
    ap_overdue = float(ap.loc[ap["days_overdue"] > 0, "open_amount"].sum()) if not ap.empty else 0.0

    rows = [
        {
            "concepto": "Cuentas por cobrar",
            "monto_abierto": ar_open,
            "monto_vencido": ar_overdue,
        },
        {
            "concepto": "Cuentas por pagar",
            "monto_abierto": ap_open,
            "monto_vencido": ap_overdue,
        },
        {
            "concepto": "Capital de trabajo neto",
            "monto_abierto": ar_open - ap_open,
            "monto_vencido": ar_overdue - ap_overdue,
        },
    ]
    return pd.DataFrame(rows)


def build_stock_uom_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    stock = get_stock_snapshot(bundle, filters)
    if stock.empty:
        return pd.DataFrame(columns=["uom_code", "quantity", "stock_value", "position_count"])

    summary = stock.groupby("uom_code", as_index=False).agg(
        quantity=("quantity", "sum"),
        stock_value=("stock_value", "sum"),
        position_count=("stock_actual_id", "count"),
    )
    return summary.sort_values("stock_value", ascending=False).reset_index(drop=True)


def latest_period_value(dataframe: pd.DataFrame, column: str) -> float:
    if dataframe.empty or column not in dataframe.columns:
        return 0.0
    ordered = dataframe.sort_values("period_id")
    return float(ordered.iloc[-1][column])


def _apply_period_filter(
    dataframe: pd.DataFrame,
    period_column: str,
    filters: dict[str, object],
) -> pd.DataFrame:
    if dataframe.empty or period_column not in dataframe.columns:
        return dataframe

    start = filters.get("period_start")
    end = filters.get("period_end")
    result = dataframe.copy()
    result[period_column] = result[period_column].astype(str)
    if start:
        result = result[result[period_column] >= str(start)]
    if end:
        result = result[result[period_column] <= str(end)]
    return result


def _apply_selection(
    dataframe: pd.DataFrame,
    column: str,
    selected_values: object,
) -> pd.DataFrame:
    if dataframe.empty or column not in dataframe.columns:
        return dataframe
    if not selected_values:
        return dataframe
    values = list(selected_values)
    return dataframe[dataframe[column].isin(values)].copy()


def _sorted_unique(*series_list: pd.Series) -> list[str]:
    values: set[str] = set()
    for series in series_list:
        if series is None or series.empty:
            continue
        cleaned = series.dropna().astype(str).str.strip()
        values.update(value for value in cleaned if value)
    return sorted(values)


def _share(series: pd.Series) -> pd.Series:
    return _safe_divide(series.fillna(0.0), float(series.fillna(0.0).sum()))


def _safe_divide(numerator: pd.Series | float, denominator: pd.Series | float) -> pd.Series | float:
    if isinstance(numerator, pd.Series) and isinstance(denominator, pd.Series):
        denominator_series = denominator.replace({0: pd.NA})
        return numerator.divide(denominator_series).fillna(0.0)
    if isinstance(numerator, pd.Series):
        if float(denominator or 0.0) == 0.0:
            return pd.Series(0.0, index=numerator.index)
        return numerator.divide(float(denominator)).fillna(0.0)
    if isinstance(denominator, pd.Series):
        denominator_series = denominator.replace({0: pd.NA})
        return pd.Series(float(numerator), index=denominator.index).divide(denominator_series).fillna(0.0)
    if float(denominator or 0.0) == 0.0:
        return 0.0
    return float(numerator) / float(denominator)
