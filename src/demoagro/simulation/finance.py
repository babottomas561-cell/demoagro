from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np
import pandas as pd

from demoagro.config import SimulationConfig
from demoagro.simulation.common import add_days, frame


def simulate_finance(
    config: SimulationConfig,
    rng: np.random.Generator,
    masters: dict[str, pd.DataFrame],
    purchase_data: dict[str, pd.DataFrame],
    sales_data: dict[str, pd.DataFrame],
    payroll_data: dict[str, pd.DataFrame],
    logistics_data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    suppliers = masters["erp_proveedores"].set_index("proveedor_id")
    purchase_invoices = purchase_data["fin_facturas_compra"]
    sales_invoices = sales_data["fin_facturas_venta"]
    payroll = payroll_data["rrhh_liquidaciones"]
    logistics_trips = logistics_data["log_viajes"]
    purchase_date_bounds = _date_bounds(purchase_invoices["invoice_date"])
    sales_date_bounds = _date_bounds(sales_invoices["invoice_date"])

    rows = defaultdict(list)
    ap_seq = 1
    pay_seq = 1
    pay_app_seq = 1
    ar_seq = 1
    collection_seq = 1
    collection_app_seq = 1
    treasury_seq = 1
    tax_line_seq = 1
    tax_position_seq = 1

    for _, invoice in purchase_invoices.iterrows():
        recency_score = _recency_score(invoice["invoice_date"], purchase_date_bounds)
        settled_ratio = _settlement_ratio(rng, flow="payable", recency_score=recency_score)
        settled_amount = round(float(invoice["total_amount"]) * settled_ratio, 2)
        open_amount = round(float(invoice["total_amount"]) - settled_amount, 2)
        account_id = f"AP_{ap_seq:05d}"
        rows["fin_cuentas_pagar"].append(
            {
                "cuenta_pagar_id": account_id,
                "proveedor_id": invoice["proveedor_id"],
                "factura_compra_id": invoice["factura_compra_id"],
                "invoice_date": invoice["invoice_date"],
                "due_date": invoice["due_date"],
                "open_amount": open_amount,
                "status": _settlement_status(settled_ratio, closed_label="PAGADA"),
            }
        )

        if settled_amount > 0:
            payment_date = _settlement_date(
                rng,
                due_date=invoice["due_date"],
                recency_score=recency_score,
                flow="payable",
            )
            payment_id = f"PAG_{pay_seq:05d}"
            rows["fin_pagos"].append(
                {
                    "pago_id": payment_id,
                    "proveedor_id": invoice["proveedor_id"],
                    "cuenta_financiera_id": "BANK_0002",
                    "payment_date": payment_date,
                    "amount": settled_amount,
                    "currency_code": config.currency_code,
                }
            )
            rows["fin_pagos_aplicacion"].append(
                {
                    "pago_aplicacion_id": f"PAP_{pay_app_seq:05d}",
                    "pago_id": payment_id,
                    "cuenta_pagar_id": account_id,
                    "applied_amount": settled_amount,
                }
            )
            rows["fin_movimientos_tesoreria"].append(
                {
                    "mov_tesoreria_id": f"TES_{treasury_seq:05d}",
                    "cuenta_financiera_id": "BANK_0002",
                    "movement_date": payment_date,
                    "movement_type": "PAGO_PROVEEDOR",
                    "source_table": "fin_pagos",
                    "source_id": payment_id,
                    "amount": -settled_amount,
                }
            )
            pay_seq += 1
            pay_app_seq += 1
            treasury_seq += 1

        ap_seq += 1

    for _, invoice in sales_invoices.iterrows():
        recency_score = _recency_score(invoice["invoice_date"], sales_date_bounds)
        settled_ratio = _settlement_ratio(rng, flow="receivable", recency_score=recency_score)
        settled_amount = round(float(invoice["total_amount"]) * settled_ratio, 2)
        open_amount = round(float(invoice["total_amount"]) - settled_amount, 2)
        account_id = f"AR_{ar_seq:05d}"
        rows["fin_cuentas_cobrar"].append(
            {
                "cuenta_cobrar_id": account_id,
                "cliente_id": invoice["cliente_id"],
                "factura_venta_id": invoice["factura_venta_id"],
                "invoice_date": invoice["invoice_date"],
                "due_date": invoice["due_date"],
                "open_amount": open_amount,
                "status": _settlement_status(settled_ratio, closed_label="COBRADA"),
            }
        )

        if settled_amount > 0:
            collection_date = _settlement_date(
                rng,
                due_date=invoice["due_date"],
                recency_score=recency_score,
                flow="receivable",
            )
            collection_id = f"COB_{collection_seq:05d}"
            rows["fin_cobranzas"].append(
                {
                    "cobranza_id": collection_id,
                    "cliente_id": invoice["cliente_id"],
                    "cuenta_financiera_id": "BANK_0003",
                    "collection_date": collection_date,
                    "amount": settled_amount,
                    "currency_code": config.currency_code,
                }
            )
            rows["fin_cobranzas_aplicacion"].append(
                {
                    "cobranza_aplicacion_id": f"CAP_{collection_app_seq:05d}",
                    "cobranza_id": collection_id,
                    "cuenta_cobrar_id": account_id,
                    "applied_amount": settled_amount,
                }
            )
            rows["fin_movimientos_tesoreria"].append(
                {
                    "mov_tesoreria_id": f"TES_{treasury_seq:05d}",
                    "cuenta_financiera_id": "BANK_0003",
                    "movement_date": collection_date,
                    "movement_type": "COBRANZA_CLIENTE",
                    "source_table": "fin_cobranzas",
                    "source_id": collection_id,
                    "amount": settled_amount,
                }
            )
            collection_seq += 1
            collection_app_seq += 1
            treasury_seq += 1

        ar_seq += 1

    logistics_movements, treasury_seq = _build_logistics_cash_movements(
        rng=rng,
        logistics_trips=logistics_trips,
        starting_seq=treasury_seq,
    )
    rows["fin_movimientos_tesoreria"].extend(logistics_movements)

    payroll_grouped = payroll.groupby("pay_date").agg(
        net_salary=("net_salary", "sum"),
        employer_contrib=("employer_contrib", "sum"),
    )
    for pay_date, values in payroll_grouped.iterrows():
        payroll_amount = round(float(values["net_salary"]), 2)
        rows["fin_movimientos_tesoreria"].append(
            {
                "mov_tesoreria_id": f"TES_{treasury_seq:05d}",
                "cuenta_financiera_id": "BANK_0002",
                "movement_date": pd.Timestamp(pay_date).date(),
                "movement_type": "PAGO_NOMINA",
                "source_table": "rrhh_liquidaciones",
                "source_id": f"NOM_{pd.Timestamp(pay_date).strftime('%Y%m%d')}",
                "amount": -payroll_amount,
            }
        )
        treasury_seq += 1

    tax_lines, tax_positions = _build_tax_tables(config, purchase_invoices, sales_invoices, payroll)
    rows["tax_comprobantes_impuesto"].extend(tax_lines.to_dict("records"))
    rows["tax_posiciones_fiscales_periodo"].extend(tax_positions.to_dict("records"))

    for _, tax_position in tax_positions.iterrows():
        payment_amount = float(tax_position["payable_amount"])
        if payment_amount <= 0:
            continue
        payment_date = _next_tax_payment_date(str(tax_position["period_id"]))
        rows["fin_movimientos_tesoreria"].append(
            {
                "mov_tesoreria_id": f"TES_{treasury_seq:05d}",
                "cuenta_financiera_id": "BANK_0002",
                "movement_date": payment_date,
                "movement_type": "PAGO_IMPUESTO",
                "source_table": "tax_posiciones_fiscales_periodo",
                "source_id": tax_position["posicion_fiscal_id"],
                "amount": -payment_amount,
            }
        )
        treasury_seq += 1

    return {table_name: frame(data) for table_name, data in rows.items()}


def _settlement_ratio(rng: np.random.Generator, flow: str, recency_score: float) -> float:
    if flow == "receivable":
        if recency_score < 0.4:
            options = [1.0, 0.98, 0.95]
            probabilities = [0.90, 0.07, 0.03]
        elif recency_score < 0.78:
            options = [1.0, 0.97, 0.92, 0.85]
            probabilities = [0.72, 0.14, 0.09, 0.05]
        else:
            options = [1.0, 0.93, 0.82, 0.7, 0.5]
            probabilities = [0.08, 0.18, 0.28, 0.28, 0.18]
        return float(rng.choice(options, p=probabilities))

    if recency_score < 0.4:
        options = [1.0, 0.97, 0.92]
        probabilities = [0.88, 0.08, 0.04]
    elif recency_score < 0.75:
        options = [1.0, 0.95, 0.88, 0.78]
        probabilities = [0.68, 0.14, 0.11, 0.07]
    else:
        options = [1.0, 0.94, 0.84, 0.7, 0.5]
        probabilities = [0.14, 0.18, 0.24, 0.24, 0.20]
    return float(rng.choice(options, p=probabilities))


def _settlement_status(settled_ratio: float, closed_label: str) -> str:
    if settled_ratio >= 0.999:
        return closed_label
    if settled_ratio <= 0.001:
        return "ABIERTA"
    return "PARCIAL"


def _build_tax_tables(
    config: SimulationConfig,
    purchase_invoices: pd.DataFrame,
    sales_invoices: pd.DataFrame,
    payroll: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    lines: list[dict[str, object]] = []
    positions: list[dict[str, object]] = []

    line_seq = 1
    for _, invoice in purchase_invoices.iterrows():
        period_id = pd.Timestamp(invoice["invoice_date"]).strftime("%Y%m")
        lines.append(
            {
                "comp_impuesto_id": f"TCL_{line_seq:06d}",
                "tipo_impuesto_id": "TAX_0002",
                "source_table": "fin_facturas_compra",
                "source_id": invoice["factura_compra_id"],
                "period_id": period_id,
                "amount": round(float(invoice["vat_amount"]), 2),
            }
        )
        line_seq += 1
    for _, invoice in sales_invoices.iterrows():
        period_id = pd.Timestamp(invoice["invoice_date"]).strftime("%Y%m")
        lines.append(
            {
                "comp_impuesto_id": f"TCL_{line_seq:06d}",
                "tipo_impuesto_id": "TAX_0001",
                "source_table": "fin_facturas_venta",
                "source_id": invoice["factura_venta_id"],
                "period_id": period_id,
                "amount": round(float(invoice["vat_amount"]), 2),
            }
        )
        line_seq += 1
    payroll_grouped = payroll.groupby("period_id")["employer_contrib"].sum().reset_index()
    for _, payroll_row in payroll_grouped.iterrows():
        lines.append(
            {
                "comp_impuesto_id": f"TCL_{line_seq:06d}",
                "tipo_impuesto_id": "TAX_0003",
                "source_table": "rrhh_liquidaciones",
                "source_id": payroll_row["period_id"],
                "period_id": payroll_row["period_id"],
                "amount": round(float(payroll_row["employer_contrib"]), 2),
            }
        )
        line_seq += 1

    lines_df = frame(lines)
    for index, (period_id, period_df) in enumerate(lines_df.groupby("period_id"), start=1):
        iva_debito = float(period_df.loc[period_df["tipo_impuesto_id"] == "TAX_0001", "amount"].sum())
        iva_credito = float(period_df.loc[period_df["tipo_impuesto_id"] == "TAX_0002", "amount"].sum())
        cargas_sociales = float(period_df.loc[period_df["tipo_impuesto_id"] == "TAX_0003", "amount"].sum())
        payable_amount = round(max(iva_debito - iva_credito, 0.0) + cargas_sociales, 2)
        positions.append(
            {
                "posicion_fiscal_id": f"TFP_{index:05d}",
                "empresa_id": "EMP_0001",
                "period_id": period_id,
                "iva_debito": round(iva_debito, 2),
                "iva_credito": round(iva_credito, 2),
                "saldo_iva": round(iva_debito - iva_credito, 2),
                "cargas_sociales": round(cargas_sociales, 2),
                "payable_amount": payable_amount,
            }
        )

    return lines_df, frame(positions)


def _next_tax_payment_date(period_id: str) -> date:
    year = int(period_id[:4])
    month = int(period_id[4:])
    if month == 12:
        return date(year + 1, 1, 15)
    return date(year, month + 1, 15)


def _date_bounds(series: pd.Series) -> tuple[pd.Timestamp, pd.Timestamp]:
    parsed = pd.to_datetime(series, errors="coerce")
    return parsed.min(), parsed.max()


def _recency_score(value, bounds: tuple[pd.Timestamp, pd.Timestamp]) -> float:
    min_date, max_date = bounds
    current = pd.Timestamp(value)
    if pd.isna(min_date) or pd.isna(max_date) or min_date == max_date:
        return 1.0
    total_days = max((max_date - min_date).days, 1)
    elapsed_days = max((current - min_date).days, 0)
    return float(elapsed_days / total_days)


def _settlement_date(
    rng: np.random.Generator,
    due_date,
    recency_score: float,
    flow: str,
) -> date:
    due = pd.Timestamp(due_date).date()
    if flow == "receivable":
        lag = int(rng.integers(-6, 9)) if recency_score < 0.55 else int(rng.integers(4, 28))
    else:
        lag = int(rng.integers(-3, 12)) if recency_score < 0.55 else int(rng.integers(8, 35))
    return add_days(due, lag)


def _build_logistics_cash_movements(
    rng: np.random.Generator,
    logistics_trips: pd.DataFrame,
    starting_seq: int,
) -> tuple[list[dict[str, object]], int]:
    rows: list[dict[str, object]] = []
    seq = starting_seq

    third_party_trips = logistics_trips.loc[logistics_trips["mode"] == "TERCERO"].copy()
    if third_party_trips.empty:
        return rows, seq

    for _, trip in third_party_trips.iterrows():
        payment_date = add_days(pd.Timestamp(trip["delivery_date"]).date(), int(rng.integers(7, 24)))
        rows.append(
            {
                "mov_tesoreria_id": f"TES_{seq:05d}",
                "cuenta_financiera_id": "BANK_0002",
                "movement_date": payment_date,
                "movement_type": "PAGO_LOGISTICA",
                "source_table": "log_viajes",
                "source_id": trip["viaje_id"],
                "amount": -round(float(trip["total_cost"]), 2),
            }
        )
        seq += 1

    return rows, seq
