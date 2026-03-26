from __future__ import annotations

import math

import pandas as pd


def prepare_finance_analysis(finance: pd.DataFrame) -> pd.DataFrame:
    if finance.empty:
        return finance.copy()

    enriched = finance.copy().sort_values("period_id").reset_index(drop=True)
    numeric_columns = [
        "revenue_net",
        "cogs",
        "gross_margin",
        "payroll_total",
        "maintenance_expense",
        "logistics_expense",
        "opex_total",
        "ebitda_approx",
        "collections_amount",
        "supplier_payments_amount",
        "payroll_cash_amount",
        "tax_payments_amount",
        "logistics_cash_amount",
        "net_cash_flow",
        "sold_tons",
    ]
    for column in numeric_columns:
        if column in enriched.columns:
            enriched[column] = pd.to_numeric(enriched[column], errors="coerce").fillna(0.0)

    enriched["gross_margin_pct_calc"] = _safe_divide(enriched["gross_margin"], enriched["revenue_net"])
    enriched["ebitda_margin_pct"] = _safe_divide(enriched["ebitda_approx"], enriched["revenue_net"])
    enriched["cogs_ratio"] = _safe_divide(enriched["cogs"], enriched["revenue_net"])
    enriched["opex_ratio"] = _safe_divide(enriched["opex_total"], enriched["revenue_net"])
    enriched["revenue_per_ton"] = _safe_divide(enriched["revenue_net"], enriched["sold_tons"])
    enriched["cogs_per_ton"] = _safe_divide(enriched["cogs"], enriched["sold_tons"])
    enriched["ebitda_per_ton"] = _safe_divide(enriched["ebitda_approx"], enriched["sold_tons"])
    enriched["cash_conversion_pct_calc"] = _safe_divide(enriched["net_cash_flow"], enriched["ebitda_approx"])
    enriched["total_cash_out"] = (
        enriched["supplier_payments_amount"]
        + enriched["payroll_cash_amount"]
        + enriched["tax_payments_amount"]
        + enriched["logistics_cash_amount"]
    )
    enriched["cash_gap_vs_ebitda"] = enriched["net_cash_flow"] - enriched["ebitda_approx"]
    return enriched


def build_finance_summary_cards(
    finance: pd.DataFrame,
    variant: str = "finance",
) -> list[dict[str, object]]:
    if finance.empty:
        return []

    totals = _build_totals(finance)
    periods = len(finance)
    avg_monthly_revenue = _safe_divide(totals["revenue_net"], periods)
    avg_realized_price = _safe_divide(totals["revenue_net"], totals["sold_tons"])
    payroll_share = _safe_divide(totals["payroll_total"], totals["opex_total"])

    if variant == "executive":
        return [
            {
                "label": "Ingresos netos",
                "value": totals["revenue_net"],
                "format": "currency",
                "detail": f"Promedio mensual: USD {avg_monthly_revenue:,.0f}",
                "tone": "neutral",
            },
            {
                "label": "Margen bruto",
                "value": totals["gross_margin"],
                "format": "currency",
                "detail": f"{_safe_divide(totals['gross_margin'], totals['revenue_net']):.1%} sobre ingresos",
                "tone": "success" if totals["gross_margin"] >= 0 else "danger",
            },
            {
                "label": "EBITDA aprox.",
                "value": totals["ebitda_approx"],
                "format": "currency",
                "detail": f"Margen EBITDA: {_safe_divide(totals['ebitda_approx'], totals['revenue_net']):.1%}",
                "tone": "success" if totals["ebitda_approx"] >= 0 else "danger",
            },
            {
                "label": "Costo de ventas",
                "value": totals["cogs"],
                "format": "currency",
                "detail": f"{_safe_divide(totals['cogs'], totals['revenue_net']):.1%} de ingresos",
                "tone": "warning" if _safe_divide(totals["cogs"], totals["revenue_net"]) > 0.65 else "neutral",
            },
            {
                "label": "Opex total",
                "value": totals["opex_total"],
                "format": "currency",
                "detail": f"Nomina pesa {payroll_share:.1%} del opex",
                "tone": "warning" if payroll_share > 0.75 else "neutral",
            },
            {
                "label": "Precio realizado",
                "value": avg_realized_price,
                "format": "currency",
                "detail": f"Sobre {totals['sold_tons']:,.0f} tn vendidas",
                "tone": "neutral",
            },
        ]

    return [
        {
            "label": "Ingresos netos",
            "value": totals["revenue_net"],
            "format": "currency",
            "detail": f"Promedio mensual: USD {avg_monthly_revenue:,.0f}",
            "tone": "neutral",
        },
        {
            "label": "Costo de ventas",
            "value": totals["cogs"],
            "format": "currency",
            "detail": f"{_safe_divide(totals['cogs'], totals['revenue_net']):.1%} de ingresos",
            "tone": "warning" if _safe_divide(totals["cogs"], totals["revenue_net"]) > 0.65 else "neutral",
        },
        {
            "label": "Opex total",
            "value": totals["opex_total"],
            "format": "currency",
            "detail": f"Nomina pesa {payroll_share:.1%} del opex",
            "tone": "warning" if payroll_share > 0.75 else "neutral",
        },
        {
            "label": "EBITDA aprox.",
            "value": totals["ebitda_approx"],
            "format": "currency",
            "detail": f"Margen EBITDA: {_safe_divide(totals['ebitda_approx'], totals['revenue_net']):.1%}",
            "tone": "success" if totals["ebitda_approx"] >= 0 else "danger",
        },
        {
            "label": "Margen EBITDA",
            "value": _safe_divide(totals["ebitda_approx"], totals["revenue_net"]),
            "format": "percent",
            "detail": f"Margen bruto: {_safe_divide(totals['gross_margin'], totals['revenue_net']):.1%}",
            "tone": "success" if totals["ebitda_approx"] >= 0 else "danger",
        },
        {
            "label": "Conversion a caja",
            "value": _safe_divide(totals["net_cash_flow"], totals["ebitda_approx"]),
            "format": "percent",
            "detail": f"Flujo neto: USD {totals['net_cash_flow']:,.0f}",
            "tone": "success" if totals["net_cash_flow"] >= 0 else "warning",
        },
    ]


def build_finance_insight_panels(finance: pd.DataFrame) -> list[dict[str, str]]:
    if finance.empty:
        return []

    totals = _build_totals(finance)
    best_ebitda_period = finance.sort_values("ebitda_approx", ascending=False).iloc[0]
    worst_ebitda_period = finance.sort_values("ebitda_approx", ascending=True).iloc[0]

    cost_mix = build_finance_cost_mix(finance)
    top_cost = cost_mix.iloc[0] if not cost_mix.empty else None
    cash_conversion = _safe_divide(totals["net_cash_flow"], totals["ebitda_approx"])

    panels = [
        {
            "title": "Mejor mes operativo",
            "headline": str(best_ebitda_period["period_id"]),
            "body": (
                f"EBITDA de USD {best_ebitda_period['ebitda_approx']:,.0f} "
                f"con margen de {best_ebitda_period['ebitda_margin_pct']:.1%}."
            ),
            "tone": "success",
        },
        {
            "title": "Mes mas exigente",
            "headline": str(worst_ebitda_period["period_id"]),
            "body": (
                f"EBITDA de USD {worst_ebitda_period['ebitda_approx']:,.0f}. "
                f"Revenue del periodo: USD {worst_ebitda_period['revenue_net']:,.0f}."
            ),
            "tone": "danger" if float(worst_ebitda_period["ebitda_approx"]) < 0 else "warning",
        },
        {
            "title": "Costo dominante",
            "headline": (
                f"{top_cost['concepto']} {top_cost['share_pct']:.1%}" if top_cost is not None else "Sin costos"
            ),
            "body": (
                f"USD {top_cost['amount']:,.0f} dentro del costo visible."
                if top_cost is not None
                else "No hay costos visibles para el filtro."
            ),
            "tone": "warning" if top_cost is not None and float(top_cost["share_pct"]) > 0.65 else "neutral",
        },
        {
            "title": "Conversion de EBITDA a caja",
            "headline": f"{cash_conversion:.1%}",
            "body": (
                f"Flujo neto de USD {totals['net_cash_flow']:,.0f} "
                f"contra EBITDA de USD {totals['ebitda_approx']:,.0f}."
            ),
            "tone": "success" if cash_conversion >= 0.8 else "warning",
        },
    ]
    return panels


def build_finance_bridge(finance: pd.DataFrame) -> pd.DataFrame:
    if finance.empty:
        return pd.DataFrame(columns=["concepto", "amount", "measure"])

    totals = _build_totals(finance)
    return pd.DataFrame(
        [
            {"concepto": "Ingresos netos", "amount": totals["revenue_net"], "measure": "absolute"},
            {"concepto": "Costo de ventas", "amount": -totals["cogs"], "measure": "relative"},
            {"concepto": "Nomina total", "amount": -totals["payroll_total"], "measure": "relative"},
            {"concepto": "Mantenimiento", "amount": -totals["maintenance_expense"], "measure": "relative"},
            {"concepto": "Logistica", "amount": -totals["logistics_expense"], "measure": "relative"},
            {"concepto": "EBITDA aprox.", "amount": totals["ebitda_approx"], "measure": "total"},
        ]
    )


def build_finance_cost_mix(finance: pd.DataFrame) -> pd.DataFrame:
    if finance.empty:
        return pd.DataFrame(columns=["concepto", "amount", "share_pct"])

    totals = _build_totals(finance)
    mix = pd.DataFrame(
        [
            {"concepto": "Costo de ventas", "amount": totals["cogs"]},
            {"concepto": "Nomina total", "amount": totals["payroll_total"]},
            {"concepto": "Mantenimiento", "amount": totals["maintenance_expense"]},
            {"concepto": "Logistica", "amount": totals["logistics_expense"]},
        ]
    )
    mix = mix[mix["amount"] > 0].copy()
    mix["share_pct"] = _safe_divide(mix["amount"], float(mix["amount"].sum()))
    return mix.sort_values("amount", ascending=False).reset_index(drop=True)


def build_finance_cost_trend(finance: pd.DataFrame) -> pd.DataFrame:
    if finance.empty:
        return pd.DataFrame(columns=["period_id", "concepto", "amount"])

    trend = finance[
        ["period_id", "cogs", "payroll_total", "maintenance_expense", "logistics_expense"]
    ].rename(
        columns={
            "cogs": "Costo de ventas",
            "payroll_total": "Nomina total",
            "maintenance_expense": "Mantenimiento",
            "logistics_expense": "Logistica",
        }
    )
    return trend.melt(id_vars="period_id", var_name="concepto", value_name="amount")


def build_finance_cash_components(finance: pd.DataFrame) -> pd.DataFrame:
    if finance.empty:
        return pd.DataFrame(columns=["period_id", "concepto", "amount"])

    cash = finance[
        [
            "period_id",
            "collections_amount",
            "supplier_payments_amount",
            "payroll_cash_amount",
            "tax_payments_amount",
            "logistics_cash_amount",
        ]
    ].rename(
        columns={
            "collections_amount": "Cobranza",
            "supplier_payments_amount": "Pago a proveedores",
            "payroll_cash_amount": "Pago de nomina",
            "tax_payments_amount": "Pago de impuestos",
            "logistics_cash_amount": "Pago logistico",
        }
    )
    long_cash = cash.melt(id_vars="period_id", var_name="concepto", value_name="amount")
    outflow_labels = {"Pago a proveedores", "Pago de nomina", "Pago de impuestos", "Pago logistico"}
    long_cash["amount"] = long_cash.apply(
        lambda row: -float(row["amount"]) if row["concepto"] in outflow_labels else float(row["amount"]),
        axis=1,
    )
    return long_cash


def build_finance_scorecard(finance: pd.DataFrame) -> pd.DataFrame:
    if finance.empty:
        return pd.DataFrame(
            columns=[
                "period_id",
                "revenue_net",
                "sold_tons",
                "revenue_per_ton",
                "cogs",
                "gross_margin_pct_calc",
                "opex_total",
                "ebitda_approx",
                "ebitda_margin_pct",
                "net_cash_flow",
                "cash_conversion_pct_calc",
            ]
        )

    scorecard = finance[
        [
            "period_id",
            "revenue_net",
            "sold_tons",
            "revenue_per_ton",
            "cogs",
            "gross_margin_pct_calc",
            "opex_total",
            "ebitda_approx",
            "ebitda_margin_pct",
            "net_cash_flow",
            "cash_conversion_pct_calc",
        ]
    ].copy()
    return scorecard.sort_values("period_id").reset_index(drop=True)


def _build_totals(finance: pd.DataFrame) -> dict[str, float]:
    return {
        "revenue_net": float(finance["revenue_net"].sum()),
        "gross_margin": float(finance["gross_margin"].sum()),
        "cogs": float(finance["cogs"].sum()),
        "payroll_total": float(finance["payroll_total"].sum()),
        "maintenance_expense": float(finance["maintenance_expense"].sum()),
        "logistics_expense": float(finance["logistics_expense"].sum()),
        "opex_total": float(finance["opex_total"].sum()),
        "ebitda_approx": float(finance["ebitda_approx"].sum()),
        "net_cash_flow": float(finance["net_cash_flow"].sum()),
        "sold_tons": float(finance["sold_tons"].sum()),
    }


def _safe_divide(numerator: pd.Series | float, denominator: pd.Series | float) -> pd.Series | float:
    if isinstance(numerator, pd.Series) and isinstance(denominator, pd.Series):
        numerator_series = pd.to_numeric(numerator, errors="coerce")
        denominator_series = pd.to_numeric(denominator, errors="coerce").replace({0: math.nan})
        return numerator_series.divide(denominator_series).fillna(0.0)
    if isinstance(numerator, pd.Series):
        if float(denominator or 0.0) == 0.0:
            return pd.Series(0.0, index=numerator.index)
        numerator_series = pd.to_numeric(numerator, errors="coerce")
        return numerator_series.divide(float(denominator)).fillna(0.0)
    if isinstance(denominator, pd.Series):
        denominator_series = pd.to_numeric(denominator, errors="coerce").replace({0: math.nan})
        return pd.Series(float(numerator), index=denominator.index).divide(denominator_series).fillna(0.0)
    if float(denominator or 0.0) == 0.0:
        return 0.0
    return float(numerator) / float(denominator)
