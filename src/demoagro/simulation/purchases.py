from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np
import pandas as pd

from demoagro.config import CROP_LIBRARY, SimulationConfig
from demoagro.simulation.common import add_days, campaign_date, frame


def simulate_purchases(
    config: SimulationConfig,
    rng: np.random.Generator,
    masters: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    products = masters["erp_productos"].set_index("product_code")
    lot_campaign = masters["erp_lote_campania"]
    campaigns = masters["erp_campanias"].set_index("campania_id")
    suppliers = masters["erp_proveedores"]

    purchase_orders: list[dict[str, object]] = []
    purchase_order_details: list[dict[str, object]] = []
    receipts: list[dict[str, object]] = []
    receipt_details: list[dict[str, object]] = []
    invoices: list[dict[str, object]] = []
    invoice_details: list[dict[str, object]] = []

    order_seq = 1
    order_det_seq = 1
    receipt_seq = 1
    receipt_det_seq = 1
    invoice_seq = 1
    invoice_det_seq = 1

    supplier_by_group = {
        group: group_df["proveedor_id"].tolist()
        for group, group_df in suppliers.groupby("supplier_group")
    }

    for _, assignment in lot_campaign.iterrows():
        campaign = campaigns.loc[assignment["campania_id"]]
        crop_code = assignment["crop_code"]
        crop = CROP_LIBRARY[crop_code]
        area = float(assignment["sown_hectares"])
        campaign_start_year = int(pd.Timestamp(campaign["campaign_start_date"]).year)

        order_lines = _build_crop_requirement_lines(
            crop_code=crop_code,
            crop=crop,
            area=area,
            products=products,
            rng=rng,
        )

        for line in order_lines:
            product = products.loc[line["product_code"]]
            supplier_id = _pick_supplier_for_product(product["category_code"], supplier_by_group, rng)
            order_date = _planned_order_date(campaign_start_year, crop, line["product_code"], rng)
            receipt_date = add_days(order_date, int(rng.integers(3, 9)))
            invoice_date = add_days(receipt_date, int(rng.integers(0, 4)))
            payment_term_days = int(
                suppliers.loc[suppliers["proveedor_id"] == supplier_id, "payment_term_days"].iloc[0]
            )

            order_id = f"OC_{order_seq:05d}"
            order_det_id = f"OCD_{order_det_seq:05d}"
            receipt_id = f"RC_{receipt_seq:05d}"
            receipt_det_id = f"RCD_{receipt_det_seq:05d}"
            invoice_id = f"FC_{invoice_seq:05d}"
            invoice_det_id = f"FCD_{invoice_det_seq:05d}"

            purchase_orders.append(
                {
                    "orden_compra_id": order_id,
                    "empresa_id": "EMP_0001",
                    "proveedor_id": supplier_id,
                    "order_date": order_date,
                    "currency_code": config.currency_code,
                    "status": "RECIBIDA",
                }
            )
            purchase_order_details.append(
                {
                    "orden_compra_det_id": order_det_id,
                    "orden_compra_id": order_id,
                    "producto_id": product["producto_id"],
                    "centro_costo_id": line["centro_costo_id"],
                    "ordered_quantity": line["ordered_quantity"],
                    "unit_price": line["unit_price"],
                    "line_total": round(line["ordered_quantity"] * line["unit_price"], 2),
                }
            )
            deposit_id = _deposit_for_category(str(product["category_code"]))
            receipts.append(
                {
                    "recepcion_compra_id": receipt_id,
                    "orden_compra_id": order_id,
                    "deposito_id": deposit_id,
                    "receipt_date": receipt_date,
                    "status": "CONFIRMADA",
                }
            )
            receipt_details.append(
                {
                    "recepcion_compra_det_id": receipt_det_id,
                    "recepcion_compra_id": receipt_id,
                    "producto_id": product["producto_id"],
                    "orden_compra_det_id": order_det_id,
                    "received_quantity": line["received_quantity"],
                    "unit_cost": line["unit_price"],
                    "line_total": round(line["received_quantity"] * line["unit_price"], 2),
                }
            )
            net_amount = round(line["received_quantity"] * line["unit_price"], 2)
            vat_amount = round(net_amount * config.default_vat_rate, 2)
            invoices.append(
                {
                    "factura_compra_id": invoice_id,
                    "proveedor_id": supplier_id,
                    "recepcion_compra_id": receipt_id,
                    "invoice_date": invoice_date,
                    "due_date": add_days(invoice_date, payment_term_days),
                    "currency_code": config.currency_code,
                    "net_amount": net_amount,
                    "vat_amount": vat_amount,
                    "total_amount": round(net_amount + vat_amount, 2),
                }
            )
            invoice_details.append(
                {
                    "factura_compra_det_id": invoice_det_id,
                    "factura_compra_id": invoice_id,
                    "producto_id": product["producto_id"],
                    "quantity": line["received_quantity"],
                    "unit_price": line["unit_price"],
                    "net_amount": net_amount,
                    "vat_rate": config.default_vat_rate,
                }
            )

            order_seq += 1
            order_det_seq += 1
            receipt_seq += 1
            receipt_det_seq += 1
            invoice_seq += 1
            invoice_det_seq += 1

    support_orders = _simulate_support_purchases(
        config=config,
        rng=rng,
        masters=masters,
        start_order_seq=order_seq,
        start_order_det_seq=order_det_seq,
        start_receipt_seq=receipt_seq,
        start_receipt_det_seq=receipt_det_seq,
        start_invoice_seq=invoice_seq,
        start_invoice_det_seq=invoice_det_seq,
    )
    purchase_orders.extend(support_orders["erp_ordenes_compra"].to_dict("records"))
    purchase_order_details.extend(support_orders["erp_ordenes_compra_det"].to_dict("records"))
    receipts.extend(support_orders["erp_recepciones_compra"].to_dict("records"))
    receipt_details.extend(support_orders["erp_recepciones_compra_det"].to_dict("records"))
    invoices.extend(support_orders["fin_facturas_compra"].to_dict("records"))
    invoice_details.extend(support_orders["fin_facturas_compra_det"].to_dict("records"))

    return {
        "erp_ordenes_compra": frame(purchase_orders),
        "erp_ordenes_compra_det": frame(purchase_order_details),
        "erp_recepciones_compra": frame(receipts),
        "erp_recepciones_compra_det": frame(receipt_details),
        "fin_facturas_compra": frame(invoices),
        "fin_facturas_compra_det": frame(invoice_details),
    }


def average_purchase_costs(purchase_data: dict[str, pd.DataFrame]) -> pd.Series:
    invoice_det = purchase_data["fin_facturas_compra_det"]
    grouped = invoice_det.groupby("producto_id").apply(
        lambda data: round(float(data["net_amount"].sum() / data["quantity"].sum()), 4)
    )
    return grouped


def _build_crop_requirement_lines(
    crop_code: str,
    crop: dict[str, object],
    area: float,
    products: pd.DataFrame,
    rng: np.random.Generator,
) -> list[dict[str, object]]:
    lines: list[dict[str, object]] = []
    for product_code, rate_per_ha in crop["input_rates"].items():
        product = products.loc[product_code]
        ordered_quantity = round(area * float(rate_per_ha) * float(rng.uniform(1.03, 1.11)), 2)
        received_quantity = round(ordered_quantity * float(rng.uniform(0.985, 1.0)), 2)
        unit_price = round(float(product["standard_cost"]) * float(rng.uniform(0.95, 1.12)), 4)
        lines.append(
            {
                "product_code": product_code,
                "ordered_quantity": ordered_quantity,
                "received_quantity": received_quantity,
                "unit_price": unit_price,
                "centro_costo_id": "CC_0001",
            }
        )

    fuel_liters = round(area * float(rng.uniform(18.0, 25.0)), 2)
    fuel_product = products.loc["GASOIL"]
    lines.append(
        {
            "product_code": "GASOIL",
            "ordered_quantity": fuel_liters,
            "received_quantity": round(fuel_liters * float(rng.uniform(0.99, 1.0)), 2),
            "unit_price": round(float(fuel_product["standard_cost"]) * float(rng.uniform(0.98, 1.1)), 4),
            "centro_costo_id": "CC_0001",
        }
    )
    return lines


def _simulate_support_purchases(
    config: SimulationConfig,
    rng: np.random.Generator,
    masters: dict[str, pd.DataFrame],
    start_order_seq: int,
    start_order_det_seq: int,
    start_receipt_seq: int,
    start_receipt_det_seq: int,
    start_invoice_seq: int,
    start_invoice_det_seq: int,
) -> dict[str, pd.DataFrame]:
    products = masters["erp_productos"].set_index("product_code")
    campaigns = masters["erp_campanias"]
    suppliers = masters["erp_proveedores"]
    supplier_terms = suppliers.set_index("proveedor_id")["payment_term_days"]

    order_seq = start_order_seq
    order_det_seq = start_order_det_seq
    receipt_seq = start_receipt_seq
    receipt_det_seq = start_receipt_det_seq
    invoice_seq = start_invoice_seq
    invoice_det_seq = start_invoice_det_seq

    rows = defaultdict(list)
    support_plan = [
        ("FILTRO_ACEITE", 95.0, "REPUESTO"),
        ("RODAMIENTO", 40.0, "REPUESTO"),
        ("CORREA", 105.0, "REPUESTO"),
    ]
    repuesto_suppliers = suppliers.loc[suppliers["supplier_group"] == "REPUESTO", "proveedor_id"].tolist()
    combustible_suppliers = suppliers.loc[suppliers["supplier_group"] == "COMBUSTIBLE", "proveedor_id"].tolist()
    service_suppliers = suppliers.loc[suppliers["supplier_group"] == "SERVICIO", "proveedor_id"].tolist()

    for _, campaign in campaigns.iterrows():
        campaign_start_year = int(pd.Timestamp(campaign["campaign_start_date"]).year)
        for product_code, base_qty, _ in support_plan:
            quantity = round(base_qty * float(rng.uniform(0.9, 1.2)), 2)
            product = products.loc[product_code]
            supplier_id = str(rng.choice(repuesto_suppliers))
            order_date = campaign_date(campaign_start_year, 8, rng)
            receipt_date = add_days(order_date, int(rng.integers(4, 11)))
            invoice_date = add_days(receipt_date, int(rng.integers(1, 5)))
            unit_price = round(float(product["standard_cost"]) * float(rng.uniform(0.94, 1.1)), 4)
            order_seq, order_det_seq, receipt_seq, receipt_det_seq, invoice_seq, invoice_det_seq = _append_purchase_document(
                rows=rows,
                config=config,
                supplier_terms=supplier_terms,
                product=product,
                supplier_id=supplier_id,
                deposit_id="DEP_0004",
                center_cost_id="CC_0003",
                order_date=order_date,
                receipt_date=receipt_date,
                invoice_date=invoice_date,
                quantity=quantity,
                unit_price=unit_price,
                order_seq=order_seq,
                order_det_seq=order_det_seq,
                receipt_seq=receipt_seq,
                receipt_det_seq=receipt_det_seq,
                invoice_seq=invoice_seq,
                invoice_det_seq=invoice_det_seq,
            )

    late_purchase_year = int(pd.to_datetime(campaigns["campaign_end_date"]).dt.year.max())
    for month in [7, 8, 9, 10, 11]:
        fuel_product = products.loc["GASOIL"]
        fuel_supplier_id = str(rng.choice(combustible_suppliers))
        fuel_order_date = campaign_date(late_purchase_year, month, rng)
        fuel_receipt_date = add_days(fuel_order_date, int(rng.integers(2, 6)))
        fuel_invoice_date = add_days(fuel_receipt_date, int(rng.integers(0, 3)))
        fuel_quantity = round(float(rng.uniform(3200.0, 6200.0)), 2)
        fuel_unit_price = round(float(fuel_product["standard_cost"]) * float(rng.uniform(0.98, 1.08)), 4)
        order_seq, order_det_seq, receipt_seq, receipt_det_seq, invoice_seq, invoice_det_seq = _append_purchase_document(
            rows=rows,
            config=config,
            supplier_terms=supplier_terms,
            product=fuel_product,
            supplier_id=fuel_supplier_id,
            deposit_id="DEP_0001",
            center_cost_id="CC_0001",
            order_date=fuel_order_date,
            receipt_date=fuel_receipt_date,
            invoice_date=fuel_invoice_date,
            quantity=fuel_quantity,
            unit_price=fuel_unit_price,
            order_seq=order_seq,
            order_det_seq=order_det_seq,
            receipt_seq=receipt_seq,
            receipt_det_seq=receipt_det_seq,
            invoice_seq=invoice_seq,
            invoice_det_seq=invoice_det_seq,
        )

        service_code = "FLETE_TERCERIZADO" if month in {8, 10, 11} else "SERV_TALLER"
        service_product = products.loc[service_code]
        service_supplier_id = str(rng.choice(service_suppliers))
        service_order_date = add_days(fuel_order_date, int(rng.integers(1, 9)))
        service_receipt_date = add_days(service_order_date, int(rng.integers(0, 2)))
        service_invoice_date = add_days(service_receipt_date, int(rng.integers(0, 5)))
        if service_code == "FLETE_TERCERIZADO":
            service_quantity = round(float(rng.uniform(220.0, 460.0)), 2)
            center_cost_id = "CC_0002"
            deposit_id = "DEP_0002"
        else:
            service_quantity = round(float(rng.uniform(22.0, 54.0)), 2)
            center_cost_id = "CC_0003"
            deposit_id = "DEP_0004"
        service_unit_price = round(float(service_product["standard_cost"]) * float(rng.uniform(0.97, 1.12)), 4)
        order_seq, order_det_seq, receipt_seq, receipt_det_seq, invoice_seq, invoice_det_seq = _append_purchase_document(
            rows=rows,
            config=config,
            supplier_terms=supplier_terms,
            product=service_product,
            supplier_id=service_supplier_id,
            deposit_id=deposit_id,
            center_cost_id=center_cost_id,
            order_date=service_order_date,
            receipt_date=service_receipt_date,
            invoice_date=service_invoice_date,
            quantity=service_quantity,
            unit_price=service_unit_price,
            order_seq=order_seq,
            order_det_seq=order_det_seq,
            receipt_seq=receipt_seq,
            receipt_det_seq=receipt_det_seq,
            invoice_seq=invoice_seq,
            invoice_det_seq=invoice_det_seq,
        )

        if month in {8, 10}:
            for spare_code, quantity_range in [("FILTRO_ACEITE", (24.0, 42.0)), ("CORREA", (22.0, 38.0))]:
                spare_product = products.loc[spare_code]
                spare_supplier_id = str(rng.choice(repuesto_suppliers))
                spare_order_date = add_days(fuel_order_date, int(rng.integers(3, 10)))
                spare_receipt_date = add_days(spare_order_date, int(rng.integers(2, 6)))
                spare_invoice_date = add_days(spare_receipt_date, int(rng.integers(0, 4)))
                spare_quantity = round(float(rng.uniform(*quantity_range)), 2)
                spare_unit_price = round(float(spare_product["standard_cost"]) * float(rng.uniform(0.95, 1.12)), 4)
                order_seq, order_det_seq, receipt_seq, receipt_det_seq, invoice_seq, invoice_det_seq = _append_purchase_document(
                    rows=rows,
                    config=config,
                    supplier_terms=supplier_terms,
                    product=spare_product,
                    supplier_id=spare_supplier_id,
                    deposit_id="DEP_0004",
                    center_cost_id="CC_0003",
                    order_date=spare_order_date,
                    receipt_date=spare_receipt_date,
                    invoice_date=spare_invoice_date,
                    quantity=spare_quantity,
                    unit_price=spare_unit_price,
                    order_seq=order_seq,
                    order_det_seq=order_det_seq,
                    receipt_seq=receipt_seq,
                    receipt_det_seq=receipt_det_seq,
                    invoice_seq=invoice_seq,
                    invoice_det_seq=invoice_det_seq,
                )

    return {table_name: frame(data) for table_name, data in rows.items()}


def _append_purchase_document(
    *,
    rows: defaultdict[str, list[dict[str, object]]],
    config: SimulationConfig,
    supplier_terms: pd.Series,
    product: pd.Series,
    supplier_id: str,
    deposit_id: str,
    center_cost_id: str,
    order_date,
    receipt_date,
    invoice_date,
    quantity: float,
    unit_price: float,
    order_seq: int,
    order_det_seq: int,
    receipt_seq: int,
    receipt_det_seq: int,
    invoice_seq: int,
    invoice_det_seq: int,
) -> tuple[int, int, int, int, int, int]:
    order_id = f"OC_{order_seq:05d}"
    order_det_id = f"OCD_{order_det_seq:05d}"
    receipt_id = f"RC_{receipt_seq:05d}"
    receipt_det_id = f"RCD_{receipt_det_seq:05d}"
    invoice_id = f"FC_{invoice_seq:05d}"
    invoice_det_id = f"FCD_{invoice_det_seq:05d}"
    payment_term_days = int(supplier_terms.loc[supplier_id])
    net_amount = round(quantity * unit_price, 2)
    vat_amount = round(net_amount * config.default_vat_rate, 2)

    rows["erp_ordenes_compra"].append(
        {
            "orden_compra_id": order_id,
            "empresa_id": "EMP_0001",
            "proveedor_id": supplier_id,
            "order_date": order_date,
            "currency_code": config.currency_code,
            "status": "RECIBIDA",
        }
    )
    rows["erp_ordenes_compra_det"].append(
        {
            "orden_compra_det_id": order_det_id,
            "orden_compra_id": order_id,
            "producto_id": product["producto_id"],
            "centro_costo_id": center_cost_id,
            "ordered_quantity": quantity,
            "unit_price": unit_price,
            "line_total": net_amount,
        }
    )
    rows["erp_recepciones_compra"].append(
        {
            "recepcion_compra_id": receipt_id,
            "orden_compra_id": order_id,
            "deposito_id": deposit_id,
            "receipt_date": receipt_date,
            "status": "CONFIRMADA",
        }
    )
    rows["erp_recepciones_compra_det"].append(
        {
            "recepcion_compra_det_id": receipt_det_id,
            "recepcion_compra_id": receipt_id,
            "producto_id": product["producto_id"],
            "orden_compra_det_id": order_det_id,
            "received_quantity": quantity,
            "unit_cost": unit_price,
            "line_total": net_amount,
        }
    )
    rows["fin_facturas_compra"].append(
        {
            "factura_compra_id": invoice_id,
            "proveedor_id": supplier_id,
            "recepcion_compra_id": receipt_id,
            "invoice_date": invoice_date,
            "due_date": add_days(invoice_date, payment_term_days),
            "currency_code": config.currency_code,
            "net_amount": net_amount,
            "vat_amount": vat_amount,
            "total_amount": round(net_amount + vat_amount, 2),
        }
    )
    rows["fin_facturas_compra_det"].append(
        {
            "factura_compra_det_id": invoice_det_id,
            "factura_compra_id": invoice_id,
            "producto_id": product["producto_id"],
            "quantity": quantity,
            "unit_price": unit_price,
            "net_amount": net_amount,
            "vat_rate": config.default_vat_rate,
        }
    )

    return (
        order_seq + 1,
        order_det_seq + 1,
        receipt_seq + 1,
        receipt_det_seq + 1,
        invoice_seq + 1,
        invoice_det_seq + 1,
    )


def _planned_order_date(
    campaign_start_year: int,
    crop: dict[str, object],
    product_code: str,
    rng: np.random.Generator,
) -> date:
    if product_code.startswith("SEM_"):
        month = _shift_month(int(crop["sow_month"]), -1)
    elif product_code in {"UREA", "MAP"}:
        month = _shift_month(int(crop["fert_month"]), -1)
    elif product_code in {"GLIFOSATO", "INSECTICIDA", "FUNGICIDA"}:
        month = _shift_month(int(crop["spray_months"][0]), -1)
    else:
        month = _shift_month(int(crop["sow_month"]), -1)
    return campaign_date(campaign_start_year, month, rng)


def _shift_month(month: int, delta: int) -> int:
    return ((month - 1 + delta) % 12) + 1


def _pick_supplier_for_product(
    category_code: str,
    supplier_by_group: dict[str, list[str]],
    rng: np.random.Generator,
) -> str:
    mapping = {
        "SEMILLA": "SEMILLA",
        "FERTILIZANTE": "FERTILIZANTE",
        "FITOSANITARIO": "FITOSANITARIO",
        "COMBUSTIBLE": "COMBUSTIBLE",
        "REPUESTO": "REPUESTO",
        "SERVICIO": "SERVICIO",
    }
    supplier_group = mapping[category_code]
    return str(rng.choice(supplier_by_group[supplier_group]))


def _deposit_for_category(category_code: str) -> str:
    if category_code == "REPUESTO":
        return "DEP_0004"
    return "DEP_0001"
