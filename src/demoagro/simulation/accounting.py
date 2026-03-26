from __future__ import annotations

from collections import defaultdict

import pandas as pd

from demoagro.simulation.common import frame


def simulate_accounting(
    masters: dict[str, pd.DataFrame],
    purchase_data: dict[str, pd.DataFrame],
    sales_data: dict[str, pd.DataFrame],
    finance_data: dict[str, pd.DataFrame],
    payroll_data: dict[str, pd.DataFrame],
    maintenance_data: dict[str, pd.DataFrame],
    logistics_data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    rows = defaultdict(list)
    asiento_seq = 1
    line_seq = 1

    purchase_invoices = purchase_data["fin_facturas_compra"]
    purchase_invoice_details = purchase_data["fin_facturas_compra_det"].copy()
    products = masters["erp_productos"][["producto_id", "category_code", "product_code"]].copy()
    purchase_invoice_details = purchase_invoice_details.merge(products, on="producto_id", how="left")
    sales_invoices = sales_data["fin_facturas_venta"]
    dispatch_details = sales_data["erp_despachos_venta_det"]
    payments = finance_data["fin_pagos"]
    collections = finance_data["fin_cobranzas"]
    treasury = finance_data["fin_movimientos_tesoreria"]
    tax_positions = finance_data["tax_posiciones_fiscales_periodo"]
    payroll = payroll_data["rrhh_liquidaciones"]
    maintenance_orders = maintenance_data["mnt_ordenes_trabajo"]
    maintenance_details = maintenance_data["mnt_ordenes_trabajo_det"]
    logistics_trips = logistics_data["log_viajes"].set_index("viaje_id")

    for _, invoice in purchase_invoices.iterrows():
        invoice_details = purchase_invoice_details.loc[
            purchase_invoice_details["factura_compra_id"] == invoice["factura_compra_id"]
        ].copy()
        inventory_amount = float(invoice_details.loc[invoice_details["category_code"] != "SERVICIO", "net_amount"].sum())
        logistics_service_amount = float(
            invoice_details.loc[invoice_details["product_code"] == "FLETE_TERCERIZADO", "net_amount"].sum()
        )
        maintenance_service_amount = float(
            invoice_details.loc[invoice_details["product_code"] == "SERV_TALLER", "net_amount"].sum()
        )
        admin_service_amount = max(
            float(invoice["net_amount"]) - inventory_amount - logistics_service_amount - maintenance_service_amount,
            0.0,
        )
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": invoice["invoice_date"],
                "entry_type": "FACTURA_COMPRA",
                "source_table": "fin_facturas_compra",
                "source_id": invoice["factura_compra_id"],
            }
        )
        lines: list[tuple[str, float, float, str]] = []
        if inventory_amount > 0:
            lines.append(("CTA_0004", inventory_amount, 0.0, "Inventario de insumos"))
        if logistics_service_amount > 0:
            lines.append(("CTA_0014", logistics_service_amount, 0.0, "Servicio logistico devengado"))
        if maintenance_service_amount > 0:
            lines.append(("CTA_0013", maintenance_service_amount, 0.0, "Servicio de taller devengado"))
        if admin_service_amount > 0:
            lines.append(("CTA_0015", admin_service_amount, 0.0, "Servicio administrativo devengado"))
        lines.extend(
            [
                ("CTA_0003", invoice["vat_amount"], 0.0, "IVA credito fiscal"),
                ("CTA_0006", 0.0, invoice["total_amount"], "Cuenta por pagar proveedor"),
            ]
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            lines,
        )
        asiento_seq += 1

    for _, invoice in sales_invoices.iterrows():
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": invoice["invoice_date"],
                "entry_type": "FACTURA_VENTA",
                "source_table": "fin_facturas_venta",
                "source_id": invoice["factura_venta_id"],
            }
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            [
                ("CTA_0002", invoice["total_amount"], 0.0, "Cuenta por cobrar cliente"),
                ("CTA_0010", 0.0, invoice["net_amount"], "Ingreso por venta"),
                ("CTA_0007", 0.0, invoice["vat_amount"], "IVA debito fiscal"),
            ],
        )
        asiento_seq += 1

    cogs_grouped = dispatch_details.groupby("despacho_venta_id")["cost_total"].sum().reset_index()
    for _, cogs_row in cogs_grouped.iterrows():
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": sales_data["erp_despachos_venta"]
                .set_index("despacho_venta_id")
                .loc[cogs_row["despacho_venta_id"], "dispatch_date"],
                "entry_type": "COSTO_VENTA",
                "source_table": "erp_despachos_venta",
                "source_id": cogs_row["despacho_venta_id"],
            }
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            [
                ("CTA_0011", cogs_row["cost_total"], 0.0, "Costo de venta"),
                ("CTA_0005", 0.0, cogs_row["cost_total"], "Salida de inventario de granos"),
            ],
        )
        asiento_seq += 1

    for _, collection in collections.iterrows():
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": collection["collection_date"],
                "entry_type": "COBRANZA",
                "source_table": "fin_cobranzas",
                "source_id": collection["cobranza_id"],
            }
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            [
                ("CTA_0001", collection["amount"], 0.0, "Ingreso a bancos"),
                ("CTA_0002", 0.0, collection["amount"], "Cancelacion cuenta por cobrar"),
            ],
        )
        asiento_seq += 1

    for _, payment in payments.iterrows():
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": payment["payment_date"],
                "entry_type": "PAGO_PROVEEDOR",
                "source_table": "fin_pagos",
                "source_id": payment["pago_id"],
            }
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            [
                ("CTA_0006", payment["amount"], 0.0, "Cancelacion cuenta por pagar"),
                ("CTA_0001", 0.0, payment["amount"], "Salida de bancos"),
            ],
        )
        asiento_seq += 1

    for _, liquidation in payroll.iterrows():
        withheld_amount = round(float(liquidation["gross_salary"]) - float(liquidation["net_salary"]), 2)
        social_security_total = round(withheld_amount + float(liquidation["employer_contrib"]), 2)
        gross_total = round(float(liquidation["gross_salary"]) + float(liquidation["employer_contrib"]), 2)

        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": liquidation["period_start"],
                "entry_type": "DEVENGO_NOMINA",
                "source_table": "rrhh_liquidaciones",
                "source_id": liquidation["liquidacion_id"],
            }
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            [
                ("CTA_0012", liquidation["gross_salary"], 0.0, "Gasto salarial"),
                ("CTA_0016", liquidation["employer_contrib"], 0.0, "Cargas patronales"),
                ("CTA_0008", 0.0, liquidation["net_salary"], "Sueldos a pagar"),
                ("CTA_0009", 0.0, social_security_total, "Obligaciones sociales"),
            ],
        )
        if round(gross_total, 2) != round(float(liquidation["net_salary"]) + social_security_total, 2):
            raise ValueError("Payroll accrual entry is unbalanced.")
        asiento_seq += 1

    payroll_payments = treasury.loc[treasury["movement_type"] == "PAGO_NOMINA"]
    for _, movement in payroll_payments.iterrows():
        amount = abs(float(movement["amount"]))
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": movement["movement_date"],
                "entry_type": "PAGO_NOMINA",
                "source_table": "fin_movimientos_tesoreria",
                "source_id": movement["mov_tesoreria_id"],
            }
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            [
                ("CTA_0008", amount, 0.0, "Cancelacion sueldos a pagar"),
                ("CTA_0001", 0.0, amount, "Salida bancos"),
            ],
        )
        asiento_seq += 1

    logistics_payments = treasury.loc[treasury["movement_type"] == "PAGO_LOGISTICA"]
    for _, movement in logistics_payments.iterrows():
        amount = abs(float(movement["amount"]))
        trip = logistics_trips.loc[movement["source_id"]]
        memo = f"Gasto logistico {trip['mode'].lower()}"
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": movement["movement_date"],
                "entry_type": "PAGO_LOGISTICA",
                "source_table": "fin_movimientos_tesoreria",
                "source_id": movement["mov_tesoreria_id"],
            }
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            [
                ("CTA_0014", amount, 0.0, memo),
                ("CTA_0001", 0.0, amount, "Salida bancos por logistica"),
            ],
        )
        asiento_seq += 1

    for _, tax_position in tax_positions.iterrows():
        iva_payable = max(float(tax_position["saldo_iva"]), 0.0)
        if iva_payable <= 0 and float(tax_position["cargas_sociales"]) <= 0:
            continue
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": _tax_entry_date(str(tax_position["period_id"])),
                "entry_type": "PAGO_IMPUESTOS",
                "source_table": "tax_posiciones_fiscales_periodo",
                "source_id": tax_position["posicion_fiscal_id"],
            }
        )
        lines = []
        if iva_payable > 0:
            lines.append(("CTA_0007", iva_payable, 0.0, "Cancelacion IVA debito"))
        if float(tax_position["cargas_sociales"]) > 0:
            lines.append(("CTA_0009", tax_position["cargas_sociales"], 0.0, "Cancelacion cargas sociales"))
        lines.append(("CTA_0001", 0.0, tax_position["payable_amount"], "Salida bancos por impuestos"))
        line_seq = _append_lines(rows, asiento_id, line_seq, lines)
        asiento_seq += 1

    maintenance_costs = maintenance_details.groupby("orden_trabajo_id")["total_cost"].sum().reset_index()
    maintenance_orders_map = maintenance_orders.set_index("orden_trabajo_id")
    for _, order_cost in maintenance_costs.iterrows():
        order = maintenance_orders_map.loc[order_cost["orden_trabajo_id"]]
        total_cost = round(float(order_cost["total_cost"]), 2)
        asiento_id = f"ASI_{asiento_seq:06d}"
        rows["cont_asientos"].append(
            {
                "asiento_id": asiento_id,
                "empresa_id": "EMP_0001",
                "entry_date": order["close_date"],
                "entry_type": "MANTENIMIENTO",
                "source_table": "mnt_ordenes_trabajo",
                "source_id": order_cost["orden_trabajo_id"],
            }
        )
        line_seq = _append_lines(
            rows,
            asiento_id,
            line_seq,
            [
                ("CTA_0013", total_cost, 0.0, "Gasto de mantenimiento"),
                ("CTA_0004", 0.0, total_cost, "Salida de inventario de repuestos"),
            ],
        )
        asiento_seq += 1

    rules = frame(
        [
            {"regla_asiento_id": "RGL_0001", "event_code": "FACTURA_COMPRA", "description": "Compra a proveedor"},
            {"regla_asiento_id": "RGL_0002", "event_code": "FACTURA_VENTA", "description": "Venta a cliente"},
            {"regla_asiento_id": "RGL_0003", "event_code": "COSTO_VENTA", "description": "Reconocimiento del costo"},
            {"regla_asiento_id": "RGL_0004", "event_code": "DEVENGO_NOMINA", "description": "Devengo de nomina"},
            {"regla_asiento_id": "RGL_0005", "event_code": "PAGO_IMPUESTOS", "description": "Cancelacion obligaciones fiscales"},
            {"regla_asiento_id": "RGL_0006", "event_code": "PAGO_LOGISTICA", "description": "Pago de servicio logistico tercerizado"},
        ]
    )

    return {
        "cont_asientos": frame(rows["cont_asientos"]),
        "cont_asientos_det": frame(rows["cont_asientos_det"]),
        "cont_reglas_asiento": rules,
    }


def _append_lines(
    rows: defaultdict[str, list[dict[str, object]]],
    asiento_id: str,
    line_seq: int,
    line_specs: list[tuple[str, float, float, str]],
) -> int:
    for account_id, debit, credit, memo in line_specs:
        rows["cont_asientos_det"].append(
            {
                "asiento_det_id": f"ASD_{line_seq:07d}",
                "asiento_id": asiento_id,
                "cuenta_contable_id": account_id,
                "centro_costo_id": None,
                "debit_amount": round(float(debit), 2),
                "credit_amount": round(float(credit), 2),
                "memo": memo,
            }
        )
        line_seq += 1
    return line_seq


def _tax_entry_date(period_id: str):
    year = int(period_id[:4])
    month = int(period_id[4:])
    if month == 12:
        return pd.Timestamp(year + 1, 1, 15).date()
    return pd.Timestamp(year, month + 1, 15).date()
