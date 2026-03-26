from __future__ import annotations

import pandas as pd

QUALITY_ANALYSIS_COLUMNS = [
    "analisis_calidad_id",
    "lote_calidad_id",
    "analysis_date",
    "humedad_pct",
    "impurezas_pct",
    "proteina_pct",
    "bonificacion_castigo_unit",
    "grado_comercial",
]

QUALITY_LOT_COLUMNS = [
    "lote_calidad_id",
    "producto_id",
    "deposito_id",
    "cosecha_id",
    "available_tons",
]

HARVEST_COLUMNS = [
    "cosecha_id",
    "lote_campania_id",
]

ASSIGNMENT_COLUMNS = [
    "lote_campania_id",
    "campania_id",
    "crop_code",
]

CAMPAIGN_COLUMNS = [
    "campania_id",
    "campaign_code",
]

QUALITY_PRODUCT_COLUMNS = [
    "producto_id",
    "product_code",
    "product_name",
]

PURCHASE_INVOICE_COLUMNS = [
    "factura_compra_id",
    "recepcion_compra_id",
    "proveedor_id",
    "invoice_date",
    "due_date",
    "net_amount",
    "vat_amount",
    "total_amount",
]

PURCHASE_DETAIL_COLUMNS = [
    "factura_compra_det_id",
    "factura_compra_id",
    "producto_id",
    "net_amount",
    "vat_rate",
]

PURCHASE_RECEIPT_COLUMNS = [
    "recepcion_compra_id",
    "orden_compra_id",
    "receipt_date",
]

PURCHASE_ORDER_COLUMNS = [
    "orden_compra_id",
    "order_date",
]

SUPPLIER_COLUMNS = [
    "proveedor_id",
    "supplier_name",
    "supplier_group",
    "payment_term_days",
]

PROCUREMENT_PRODUCT_COLUMNS = [
    "producto_id",
    "product_code",
    "product_name",
    "category_code",
]


def build_quality_supply_overview(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, object]]:
    quality_period = get_quality_period(bundle, filters)
    procurement_period = get_procurement_period(bundle, filters)
    supplier_summary = build_supplier_summary(bundle, filters)

    tons_analyzed = float(quality_period["tons_analyzed"].sum()) if not quality_period.empty else 0.0
    avg_humidity = _weighted_average(quality_period, "avg_humidity_pct", "tons_analyzed")
    grade_one_share = _safe_divide(
        float(quality_period["grade_one_tons"].sum()) if not quality_period.empty else 0.0,
        tons_analyzed,
    )
    avg_bonus = _weighted_average(quality_period, "avg_bonus_unit", "tons_analyzed")

    spend_net = float(procurement_period["spend_net"].sum()) if not procurement_period.empty else 0.0
    avg_lead_time = _weighted_average(procurement_period, "avg_lead_time_days", "invoice_count")
    top_supplier_share = _safe_divide(
        float(supplier_summary.iloc[0]["spend_net"]) if not supplier_summary.empty else 0.0,
        spend_net,
    )

    return [
        {
            "label": "Toneladas analizadas",
            "value": tons_analyzed,
            "format": "tons",
            "detail": "Volumen con analisis de calidad",
            "tone": "neutral",
        },
        {
            "label": "Humedad promedio",
            "value": avg_humidity,
            "format": "number",
            "detail": "Promedio ponderado por volumen",
            "tone": "warning" if avg_humidity > 13.5 else "neutral",
        },
        {
            "label": "Share grado 1",
            "value": grade_one_share,
            "format": "percent",
            "detail": "Participacion del volumen mejor clasificado",
            "tone": "success" if grade_one_share >= 0.65 else "warning",
        },
        {
            "label": "Castigo / bonif. medio",
            "value": avg_bonus,
            "format": "number",
            "detail": "USD por tn sobre el lote analizado",
            "tone": "warning" if avg_bonus < 0 else "neutral",
        },
        {
            "label": "Compras netas",
            "value": spend_net,
            "format": "currency",
            "detail": "Gasto neto devengado en abastecimiento",
            "tone": "neutral",
        },
        {
            "label": "Lead time promedio",
            "value": avg_lead_time,
            "format": "number",
            "detail": f"Top supplier share: {top_supplier_share:.1%}",
            "tone": "warning" if avg_lead_time > 6.0 else "neutral",
        },
    ]


def build_quality_supply_alerts(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, str]]:
    quality_period = get_quality_period(bundle, filters)
    procurement_period = get_procurement_period(bundle, filters)
    category_summary = build_procurement_category_summary(bundle, filters)

    alerts: list[dict[str, str]] = []

    avg_humidity = _weighted_average(quality_period, "avg_humidity_pct", "tons_analyzed")
    avg_bonus = _weighted_average(quality_period, "avg_bonus_unit", "tons_analyzed")
    if avg_humidity > 13.5:
        alerts.append(
            {
                "level": "warning",
                "title": "Humedad exigente",
                "body": f"La humedad media visible esta en {avg_humidity:.2f}%; puede generar castigos comerciales.",
            }
        )
    if avg_bonus < 0:
        alerts.append(
            {
                "level": "warning",
                "title": "Calidad con castigo neto",
                "body": f"El ajuste medio visible es {avg_bonus:.2f} USD/tn; conviene revisar grado y acondicionamiento.",
            }
        )

    avg_lead_time = _weighted_average(procurement_period, "avg_lead_time_days", "invoice_count")
    if avg_lead_time > 6.0:
        alerts.append(
            {
                "level": "info",
                "title": "Abastecimiento mas lento",
                "body": f"El lead time promedio visible esta en {avg_lead_time:.1f} dias.",
            }
        )

    if not category_summary.empty:
        top_category = category_summary.iloc[0]
        category_share = _safe_divide(float(top_category["spend_net"]), float(category_summary["spend_net"].sum()))
        if category_share > 0.45:
            alerts.append(
                {
                    "level": "info",
                    "title": "Mix de compra concentrado",
                    "body": f"{top_category['category_code']} explica {category_share:.1%} del gasto visible.",
                }
            )

    if not alerts:
        alerts.append(
            {
                "level": "success",
                "title": "Calidad y abastecimiento estables",
                "body": "No aparecen desvíos severos en calidad comercial ni en abastecimiento para el rango visible.",
            }
        )

    return alerts


def get_quality_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    quality = _quality_base(bundle, filters)
    if quality.empty:
        return pd.DataFrame(
            columns=[
                "period_id",
                "analysis_count",
                "tons_analyzed",
                "avg_humidity_pct",
                "avg_impurity_pct",
                "avg_protein_pct",
                "avg_bonus_unit",
                "grade_one_tons",
            ]
        )

    period = quality.groupby("period_id", as_index=False).agg(
        analysis_count=("analisis_calidad_id", "nunique"),
        tons_analyzed=("available_tons", "sum"),
        weighted_humidity=("weighted_humidity", "sum"),
        weighted_impurity=("weighted_impurity", "sum"),
        weighted_protein=("weighted_protein", "sum"),
        weighted_bonus=("weighted_bonus", "sum"),
        grade_one_tons=("grade_one_tons", "sum"),
    )
    period["avg_humidity_pct"] = period["weighted_humidity"] / period["tons_analyzed"].replace({0: pd.NA})
    period["avg_impurity_pct"] = period["weighted_impurity"] / period["tons_analyzed"].replace({0: pd.NA})
    period["avg_protein_pct"] = period["weighted_protein"] / period["tons_analyzed"].replace({0: pd.NA})
    period["avg_bonus_unit"] = period["weighted_bonus"] / period["tons_analyzed"].replace({0: pd.NA})
    return period.fillna(0.0).sort_values("period_id").reset_index(drop=True)


def build_quality_product_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    quality = _quality_base(bundle, filters)
    if quality.empty:
        return pd.DataFrame(
            columns=[
                "product_name",
                "tons_analyzed",
                "avg_humidity_pct",
                "avg_impurity_pct",
                "avg_bonus_unit",
                "grade_one_share",
            ]
        )

    summary = quality.groupby(["product_code", "product_name"], as_index=False).agg(
        tons_analyzed=("available_tons", "sum"),
        weighted_humidity=("weighted_humidity", "sum"),
        weighted_impurity=("weighted_impurity", "sum"),
        weighted_bonus=("weighted_bonus", "sum"),
        grade_one_tons=("grade_one_tons", "sum"),
    )
    summary["avg_humidity_pct"] = summary["weighted_humidity"] / summary["tons_analyzed"].replace({0: pd.NA})
    summary["avg_impurity_pct"] = summary["weighted_impurity"] / summary["tons_analyzed"].replace({0: pd.NA})
    summary["avg_bonus_unit"] = summary["weighted_bonus"] / summary["tons_analyzed"].replace({0: pd.NA})
    summary["grade_one_share"] = summary["grade_one_tons"] / summary["tons_analyzed"].replace({0: pd.NA})
    return summary.fillna(0.0).sort_values("tons_analyzed", ascending=False).reset_index(drop=True)


def build_quality_grade_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    quality = _quality_base(bundle, filters)
    if quality.empty:
        return pd.DataFrame(columns=["grado_comercial", "tons_analyzed", "avg_bonus_unit"])

    summary = quality.groupby("grado_comercial", as_index=False).agg(
        tons_analyzed=("available_tons", "sum"),
        weighted_bonus=("weighted_bonus", "sum"),
        analysis_count=("analisis_calidad_id", "nunique"),
    )
    summary["avg_bonus_unit"] = summary["weighted_bonus"] / summary["tons_analyzed"].replace({0: pd.NA})
    return summary.fillna(0.0).sort_values("tons_analyzed", ascending=False).reset_index(drop=True)


def get_procurement_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    purchases = _procurement_base(bundle, filters)
    if purchases.empty:
        return pd.DataFrame(
            columns=[
                "period_id",
                "invoice_count",
                "spend_net",
                "spend_total",
                "avg_lead_time_days",
                "avg_payment_term_days",
            ]
        )

    invoice_level = purchases.groupby("factura_compra_id", as_index=False).agg(
        period_id=("period_id", "first"),
        spend_net=("line_net_amount", "sum"),
        spend_total=("line_total_amount", "sum"),
        lead_time_days=("lead_time_days", "first"),
        payment_term_days=("payment_term_days", "first"),
    )

    period = invoice_level.groupby("period_id", as_index=False).agg(
        invoice_count=("factura_compra_id", "nunique"),
        spend_net=("spend_net", "sum"),
        spend_total=("spend_total", "sum"),
        lead_time_sum=("lead_time_days", "sum"),
        payment_term_sum=("payment_term_days", "sum"),
    )
    period["avg_lead_time_days"] = period["lead_time_sum"] / period["invoice_count"].replace({0: pd.NA})
    period["avg_payment_term_days"] = period["payment_term_sum"] / period["invoice_count"].replace({0: pd.NA})
    return period.fillna(0.0).sort_values("period_id").reset_index(drop=True)


def build_supplier_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    purchases = _procurement_base(bundle, filters)
    if purchases.empty:
        return pd.DataFrame(columns=["supplier_name", "supplier_group", "invoice_count", "spend_net", "avg_lead_time_days", "payment_term_days"])

    summary = purchases.groupby(["supplier_name", "supplier_group"], as_index=False).agg(
        invoice_count=("factura_compra_id", "nunique"),
        spend_net=("line_net_amount", "sum"),
        avg_lead_time_days=("lead_time_days", "mean"),
        payment_term_days=("payment_term_days", "mean"),
    )
    summary["spend_share_pct"] = summary["spend_net"] / summary["spend_net"].sum()
    return summary.fillna(0.0).sort_values("spend_net", ascending=False).reset_index(drop=True)


def build_procurement_category_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    purchases = _procurement_base(bundle, filters)
    if purchases.empty:
        return pd.DataFrame(columns=["category_code", "invoice_count", "spend_net", "avg_lead_time_days", "spend_share_pct"])

    summary = purchases.groupby("category_code", as_index=False).agg(
        invoice_count=("factura_compra_id", "nunique"),
        spend_net=("line_net_amount", "sum"),
        avg_lead_time_days=("lead_time_days", "mean"),
    )
    summary["spend_share_pct"] = summary["spend_net"] / summary["spend_net"].sum()
    return summary.fillna(0.0).sort_values("spend_net", ascending=False).reset_index(drop=True)


def _quality_base(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    analyses = _bundle_frame(bundle, "erp_analisis_calidad", QUALITY_ANALYSIS_COLUMNS)
    quality_lots = _bundle_frame(bundle, "erp_lotes_calidad", QUALITY_LOT_COLUMNS)
    harvests = _bundle_frame(bundle, "erp_cosechas", HARVEST_COLUMNS)[HARVEST_COLUMNS].copy()
    assignments = _bundle_frame(bundle, "erp_lote_campania", ASSIGNMENT_COLUMNS)[ASSIGNMENT_COLUMNS].copy()
    campaigns = _bundle_frame(bundle, "erp_campanias", CAMPAIGN_COLUMNS)[CAMPAIGN_COLUMNS].copy()
    products = _bundle_frame(bundle, "erp_productos", QUALITY_PRODUCT_COLUMNS)[QUALITY_PRODUCT_COLUMNS].copy()

    if analyses.empty or quality_lots.empty or harvests.empty or assignments.empty or campaigns.empty or products.empty:
        return pd.DataFrame(
            columns=[
                "period_id",
                "analisis_calidad_id",
                "available_tons",
                "weighted_humidity",
                "weighted_impurity",
                "weighted_protein",
                "weighted_bonus",
                "grade_one_tons",
                "grado_comercial",
                "campaign_code",
                "crop_code",
                "product_code",
                "product_name",
            ]
        )

    quality = (
        analyses.merge(quality_lots, on="lote_calidad_id", how="left")
        .merge(harvests, on="cosecha_id", how="left")
        .merge(assignments, on="lote_campania_id", how="left")
        .merge(campaigns, on="campania_id", how="left")
        .merge(products, on="producto_id", how="left")
    )
    quality["period_id"] = pd.to_datetime(quality["analysis_date"], errors="coerce").dt.strftime("%Y-%m")
    quality = _apply_period_filter(quality, "period_id", filters)
    quality = _apply_selection(quality, "campaign_code", filters.get("campaigns"))
    quality = _apply_selection(quality, "crop_code", filters.get("crops"))
    quality = _apply_selection(quality, "product_code", filters.get("products"))
    quality["weighted_humidity"] = quality["humedad_pct"] * quality["available_tons"]
    quality["weighted_impurity"] = quality["impurezas_pct"] * quality["available_tons"]
    quality["weighted_protein"] = quality["proteina_pct"] * quality["available_tons"]
    quality["weighted_bonus"] = quality["bonificacion_castigo_unit"] * quality["available_tons"]
    quality["grade_one_tons"] = quality["available_tons"].where(quality["grado_comercial"] == "GRADO_1", 0.0)
    return quality


def _procurement_base(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    invoices = _bundle_frame(bundle, "fin_facturas_compra", PURCHASE_INVOICE_COLUMNS).rename(
        columns={
            "net_amount": "invoice_net_amount",
            "vat_amount": "invoice_vat_amount",
            "total_amount": "invoice_total_amount",
        }
    )
    details = _bundle_frame(bundle, "fin_facturas_compra_det", PURCHASE_DETAIL_COLUMNS).rename(
        columns={"net_amount": "line_net_amount"}
    )
    receipts = _bundle_frame(bundle, "erp_recepciones_compra", PURCHASE_RECEIPT_COLUMNS)
    orders = _bundle_frame(bundle, "erp_ordenes_compra", PURCHASE_ORDER_COLUMNS)
    suppliers = _bundle_frame(bundle, "erp_proveedores", SUPPLIER_COLUMNS)[SUPPLIER_COLUMNS].copy()
    products = _bundle_frame(bundle, "erp_productos", PROCUREMENT_PRODUCT_COLUMNS)[PROCUREMENT_PRODUCT_COLUMNS].copy()

    if invoices.empty or details.empty or receipts.empty or orders.empty or suppliers.empty or products.empty:
        return pd.DataFrame(
            columns=[
                "period_id",
                "factura_compra_id",
                "supplier_name",
                "supplier_group",
                "product_code",
                "product_name",
                "category_code",
                "line_net_amount",
                "line_total_amount",
                "lead_time_days",
                "payment_term_days",
            ]
        )

    purchases = (
        invoices.merge(details, on="factura_compra_id", how="left")
        .merge(receipts[["recepcion_compra_id", "orden_compra_id", "receipt_date"]], on="recepcion_compra_id", how="left")
        .merge(orders[["orden_compra_id", "order_date"]], on="orden_compra_id", how="left")
        .merge(suppliers, on="proveedor_id", how="left")
        .merge(products, on="producto_id", how="left")
    )
    purchases["period_id"] = pd.to_datetime(purchases["invoice_date"], errors="coerce").dt.strftime("%Y-%m")
    purchases["line_total_amount"] = purchases["line_net_amount"] * (1.0 + purchases["vat_rate"].fillna(0.0))
    purchases["lead_time_days"] = (
        pd.to_datetime(purchases["receipt_date"], errors="coerce") - pd.to_datetime(purchases["order_date"], errors="coerce")
    ).dt.days
    purchases["payment_term_days"] = (
        pd.to_datetime(purchases["due_date"], errors="coerce") - pd.to_datetime(purchases["invoice_date"], errors="coerce")
    ).dt.days
    purchases = _apply_period_filter(purchases, "period_id", filters)
    purchases = _apply_selection(purchases, "product_code", filters.get("products"))
    return purchases


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
    column_name: str,
    values: object,
) -> pd.DataFrame:
    if dataframe.empty or column_name not in dataframe.columns or not values:
        return dataframe
    return dataframe[dataframe[column_name].isin(values)].copy()


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _weighted_average(
    dataframe: pd.DataFrame,
    value_column: str,
    weight_column: str,
) -> float:
    if dataframe.empty:
        return 0.0
    weight_total = float(dataframe[weight_column].sum())
    if weight_total == 0:
        return 0.0
    return float((dataframe[value_column] * dataframe[weight_column]).sum() / weight_total)


def _bundle_frame(
    bundle: dict[str, pd.DataFrame],
    key: str,
    columns: list[str],
) -> pd.DataFrame:
    dataframe = bundle.get(key)
    if isinstance(dataframe, pd.DataFrame):
        return dataframe.copy()
    return pd.DataFrame(columns=columns)
