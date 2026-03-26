from __future__ import annotations

import pandas as pd

from demoagro.marts.common import aging_bucket, latest_date, period_from_date, safe_divide


def build_finance_period(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    sales = tables["fin_facturas_venta"].copy()
    sales["period_id"] = period_from_date(sales["invoice_date"])
    revenue = sales.groupby("period_id", as_index=False).agg(
        revenue_net=("net_amount", "sum"),
        revenue_gross=("total_amount", "sum"),
        vat_debit=("vat_amount", "sum"),
    )

    dispatches = tables["erp_despachos_venta"][["despacho_venta_id", "dispatch_date"]].copy()
    dispatches["period_id"] = period_from_date(dispatches["dispatch_date"])
    cogs = (
        tables["erp_despachos_venta_det"]
        .merge(dispatches[["despacho_venta_id", "period_id"]], on="despacho_venta_id", how="left")
        .groupby("period_id", as_index=False)
        .agg(cogs=("cost_total", "sum"), sold_tons=("quantity", "sum"))
    )

    payroll = tables["rrhh_liquidaciones"].copy()
    payroll["period_id"] = period_from_date(payroll["period_start"])
    payroll_period = payroll.groupby("period_id", as_index=False).agg(
        payroll_expense=("gross_salary", "sum"),
        employer_contrib=("employer_contrib", "sum"),
        payroll_cash_net=("net_salary", "sum"),
    )
    payroll_period["payroll_total"] = payroll_period["payroll_expense"] + payroll_period["employer_contrib"]

    maintenance_orders = tables["mnt_ordenes_trabajo"][["orden_trabajo_id", "close_date", "internal_labor_cost"]].copy()
    maintenance_orders["period_id"] = period_from_date(maintenance_orders["close_date"])
    maintenance_parts = (
        tables["mnt_ordenes_trabajo_det"]
        .groupby("orden_trabajo_id", as_index=False)
        .agg(parts_cost=("total_cost", "sum"))
    )
    maintenance = maintenance_orders.merge(maintenance_parts, on="orden_trabajo_id", how="left").fillna({"parts_cost": 0.0})
    maintenance["maintenance_total"] = maintenance["internal_labor_cost"] + maintenance["parts_cost"]
    maintenance_period = maintenance.groupby("period_id", as_index=False).agg(
        maintenance_expense=("maintenance_total", "sum")
    )

    trips = tables["log_viajes"].copy()
    trips = trips.loc[trips["mode"] == "TERCERO"].copy()
    trips["period_id"] = period_from_date(trips["dispatch_date"])
    logistics = trips.groupby("period_id", as_index=False).agg(
        logistics_expense=("total_cost", "sum"),
        logistics_trip_count=("viaje_id", "count"),
    )

    tax = tables["tax_posiciones_fiscales_periodo"].copy()
    tax["period_id"] = pd.to_datetime(tax["period_id"], format="%Y%m", errors="coerce").dt.strftime("%Y-%m")
    tax_period = tax.groupby("period_id", as_index=False).agg(
        tax_accrued=("payable_amount", "sum"),
        iva_saldo=("saldo_iva", "sum"),
        cargas_sociales=("cargas_sociales", "sum"),
    )

    treasury = tables["fin_movimientos_tesoreria"].copy()
    treasury["period_id"] = period_from_date(treasury["movement_date"])
    treasury["cash_in"] = treasury["amount"].where(treasury["amount"] > 0, 0.0)
    treasury["cash_out"] = (-treasury["amount"]).where(treasury["amount"] < 0, 0.0)
    treasury_period = treasury.groupby(["period_id", "movement_type"], as_index=False).agg(amount=("amount", "sum"))
    treasury_pivot = (
        treasury_period.pivot(index="period_id", columns="movement_type", values="amount")
        .fillna(0.0)
        .reset_index()
    )

    periods = _base_periods([revenue, cogs, payroll_period, maintenance_period, logistics, tax_period, treasury_pivot])
    finance_period = periods.merge(revenue, on="period_id", how="left")
    for dataset in [cogs, payroll_period, maintenance_period, logistics, tax_period, treasury_pivot]:
        finance_period = finance_period.merge(dataset, on="period_id", how="left")
    finance_period = finance_period.fillna(0.0)

    finance_period["gross_margin"] = finance_period["revenue_net"] - finance_period["cogs"]
    finance_period["gross_margin_pct"] = safe_divide(finance_period["gross_margin"], finance_period["revenue_net"])
    finance_period["opex_total"] = (
        finance_period["payroll_total"]
        + finance_period["maintenance_expense"]
        + finance_period["logistics_expense"]
    )
    finance_period["operating_margin"] = finance_period["gross_margin"] - finance_period["opex_total"]
    finance_period["operating_margin_pct"] = safe_divide(finance_period["operating_margin"], finance_period["revenue_net"])
    finance_period["ebitda_approx"] = finance_period["operating_margin"]
    finance_period["collections_amount"] = finance_period.get("COBRANZA_CLIENTE", 0.0)
    finance_period["supplier_payments_amount"] = finance_period.get("PAGO_PROVEEDOR", 0.0).abs()
    finance_period["payroll_cash_amount"] = finance_period.get("PAGO_NOMINA", 0.0).abs()
    finance_period["tax_payments_amount"] = finance_period.get("PAGO_IMPUESTO", 0.0).abs()
    if "PAGO_LOGISTICA" in finance_period.columns:
        finance_period["logistics_cash_amount"] = finance_period["PAGO_LOGISTICA"].abs()
    else:
        finance_period["logistics_cash_amount"] = 0.0
    finance_period["net_cash_flow"] = (
        finance_period["collections_amount"]
        - finance_period["supplier_payments_amount"]
        - finance_period["payroll_cash_amount"]
        - finance_period["tax_payments_amount"]
        - finance_period["logistics_cash_amount"]
    )
    finance_period["cash_conversion_ratio"] = safe_divide(finance_period["collections_amount"], finance_period["revenue_net"])

    finance_period.insert(0, "mart_id", [f"MFIN_{index + 1:04d}" for index in range(len(finance_period))])
    return finance_period.sort_values("period_id").reset_index(drop=True)


def build_working_capital_snapshot(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    ar = tables["fin_cuentas_cobrar"].copy()
    ar = ar.loc[ar["open_amount"] > 0].copy()
    ap = tables["fin_cuentas_pagar"].copy()
    ap = ap.loc[ap["open_amount"] > 0].copy()

    snapshot_date = _working_capital_snapshot_date(tables, ar, ap)

    ar["snapshot_date"] = snapshot_date.date().isoformat()
    ar["days_overdue"] = (snapshot_date - pd.to_datetime(ar["due_date"])).dt.days
    ar["aging_bucket"] = ar["days_overdue"].map(aging_bucket)
    ar = ar.merge(tables["erp_clientes"][["cliente_id", "client_name"]], on="cliente_id", how="left")
    ar.insert(0, "mart_id", [f"MAR_{index + 1:04d}" for index in range(len(ar))])

    ap["snapshot_date"] = snapshot_date.date().isoformat()
    ap["days_overdue"] = (snapshot_date - pd.to_datetime(ap["due_date"])).dt.days
    ap["aging_bucket"] = ap["days_overdue"].map(aging_bucket)
    ap = ap.merge(tables["erp_proveedores"][["proveedor_id", "supplier_name"]], on="proveedor_id", how="left")
    ap.insert(0, "mart_id", [f"MAP_{index + 1:04d}" for index in range(len(ap))])

    summary = pd.DataFrame(
        [
            {
                "mart_id": "MWK_0001",
                "snapshot_date": snapshot_date.date().isoformat(),
                "ar_open_amount": round(float(ar["open_amount"].sum()), 2),
                "ap_open_amount": round(float(ap["open_amount"].sum()), 2),
                "ar_overdue_amount": round(float(ar.loc[ar["days_overdue"] > 0, "open_amount"].sum()), 2),
                "ap_overdue_amount": round(float(ap.loc[ap["days_overdue"] > 0, "open_amount"].sum()), 2),
            }
        ]
    )
    return {
        "mart_working_capital_ar": ar,
        "mart_working_capital_ap": ap,
        "mart_working_capital_summary": summary,
    }


def _working_capital_snapshot_date(
    tables: dict[str, pd.DataFrame],
    ar_open: pd.DataFrame,
    ap_open: pd.DataFrame,
) -> pd.Timestamp:
    candidate_series: list[pd.Series] = []

    for dataframe in (ar_open, ap_open):
        for column in ("due_date", "invoice_date"):
            if column in dataframe.columns and not dataframe.empty:
                candidate_series.append(dataframe[column])

    if candidate_series:
        return latest_date(candidate_series)

    return latest_date(
        [
            tables["fin_facturas_venta"]["invoice_date"],
            tables["fin_facturas_compra"]["invoice_date"],
        ]
    )


def _base_periods(datasets: list[pd.DataFrame]) -> pd.DataFrame:
    period_values: set[str] = set()
    for dataset in datasets:
        if "period_id" in dataset.columns:
            period_values.update(dataset["period_id"].dropna().astype(str).tolist())
    return pd.DataFrame({"period_id": sorted(period_values)})
