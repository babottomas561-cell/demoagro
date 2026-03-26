from __future__ import annotations

from collections import defaultdict
from math import ceil

import numpy as np
import pandas as pd

from demoagro.config import CROP_LIBRARY, SimulationConfig
from demoagro.simulation.common import add_days, frame


def simulate_sales(
    config: SimulationConfig,
    rng: np.random.Generator,
    masters: dict[str, pd.DataFrame],
    production_data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    quality_lots = production_data["erp_lotes_calidad"].copy()
    harvests = production_data["erp_cosechas"].set_index("cosecha_id")
    clients = masters["erp_clientes"]
    products = masters["erp_productos"].set_index("producto_id")

    rows = defaultdict(list)
    order_seq = 1
    order_det_seq = 1
    dispatch_seq = 1
    dispatch_det_seq = 1
    invoice_seq = 1
    invoice_det_seq = 1

    for _, quality_lot in quality_lots.iterrows():
        product = products.loc[quality_lot["producto_id"]]
        product_code = str(product["product_code"])
        crop_code = product_code.replace("_GRANO", "")
        crop = CROP_LIBRARY[crop_code]
        harvest = harvests.loc[quality_lot["cosecha_id"]]
        sell_ratio = float(rng.uniform(config.sale_ratio_min, config.sale_ratio_max))
        sellable_tons = round(float(quality_lot["available_tons"]) * sell_ratio, 2)
        split_count = int(rng.choice([1, 2, 3], p=[0.35, 0.45, 0.20]))
        remaining_tons = sellable_tons

        for split_index in range(split_count):
            if split_index == split_count - 1:
                quantity = round(remaining_tons, 2)
            else:
                share = float(rng.uniform(0.25, 0.45))
                quantity = round(sellable_tons * share, 2)
                remaining_tons = round(remaining_tons - quantity, 2)
            if quantity <= 0:
                continue

            client = _pick_client(clients, product_code, rng)
            order_date = add_days(pd.Timestamp(harvest["fecha"]).date(), _sale_order_lag_days(rng, split_index, split_count))
            dispatch_date = add_days(order_date, int(rng.integers(1, 8)))
            invoice_date = add_days(dispatch_date, int(rng.integers(0, 3)))
            price = _sale_price(crop, float(quality_lot["bonus_castigo_unit"]), dispatch_date.month, rng)

            order_id = f"PV_{order_seq:05d}"
            order_det_id = f"PVD_{order_det_seq:05d}"
            dispatch_id = f"DESP_{dispatch_seq:05d}"
            dispatch_det_id = f"DESPD_{dispatch_det_seq:05d}"
            invoice_id = f"FV_{invoice_seq:05d}"
            invoice_det_id = f"FVD_{invoice_det_seq:05d}"

            net_amount = round(quantity * price, 2)
            vat_amount = round(net_amount * config.default_vat_rate, 2)

            rows["erp_pedidos_venta"].append(
                {
                    "pedido_venta_id": order_id,
                    "cliente_id": client["cliente_id"],
                    "order_date": order_date,
                    "status": "FACTURADO",
                }
            )
            rows["erp_pedidos_venta_det"].append(
                {
                    "pedido_venta_det_id": order_det_id,
                    "pedido_venta_id": order_id,
                    "producto_id": quality_lot["producto_id"],
                    "ordered_quantity": quantity,
                    "target_price": price,
                }
            )
            rows["erp_despachos_venta"].append(
                {
                    "despacho_venta_id": dispatch_id,
                    "cliente_id": client["cliente_id"],
                    "deposito_id": quality_lot["deposito_id"],
                    "dispatch_date": dispatch_date,
                    "status": "DESPACHADO",
                }
            )
            rows["erp_despachos_venta_det"].append(
                {
                    "despacho_venta_det_id": dispatch_det_id,
                    "despacho_venta_id": dispatch_id,
                    "producto_id": quality_lot["producto_id"],
                    "lote_calidad_id": quality_lot["lote_calidad_id"],
                    "quantity": quantity,
                    "cost_per_ton": quality_lot["base_cost_per_ton"],
                    "cost_total": round(quantity * float(quality_lot["base_cost_per_ton"]), 2),
                }
            )
            rows["fin_facturas_venta"].append(
                {
                    "factura_venta_id": invoice_id,
                    "cliente_id": client["cliente_id"],
                    "despacho_venta_id": dispatch_id,
                    "invoice_date": invoice_date,
                    "due_date": add_days(invoice_date, int(client["payment_term_days"])),
                    "currency_code": config.currency_code,
                    "net_amount": net_amount,
                    "vat_amount": vat_amount,
                    "total_amount": round(net_amount + vat_amount, 2),
                }
            )
            rows["fin_facturas_venta_det"].append(
                {
                    "factura_venta_det_id": invoice_det_id,
                    "factura_venta_id": invoice_id,
                    "producto_id": quality_lot["producto_id"],
                    "quantity": quantity,
                    "unit_price": price,
                    "net_amount": net_amount,
                    "vat_rate": config.default_vat_rate,
                }
            )

            order_seq += 1
            order_det_seq += 1
            dispatch_seq += 1
            dispatch_det_seq += 1
            invoice_seq += 1
            invoice_det_seq += 1

    return {table_name: frame(data) for table_name, data in rows.items()}


def _pick_client(clients: pd.DataFrame, product_code: str, rng: np.random.Generator) -> pd.Series:
    weights = np.where(clients["preferred_product_code"] == product_code, 4.0, 1.0)
    selected_index = int(rng.choice(clients.index.to_list(), p=weights / weights.sum()))
    return clients.loc[selected_index]


def _sale_price(
    crop: dict[str, object],
    quality_bonus_unit: float,
    month: int,
    rng: np.random.Generator,
) -> float:
    seasonality = {
        1: 1.01,
        2: 1.02,
        3: 0.99,
        4: 0.96,
        5: 0.97,
        6: 1.00,
        7: 1.03,
        8: 1.05,
        9: 1.06,
        10: 1.04,
        11: 1.03,
        12: 1.02,
    }
    return round(
        (float(crop["sale_price"]) * seasonality[month] * float(rng.uniform(0.96, 1.07))) + quality_bonus_unit,
        2,
    )


def _sale_order_lag_days(rng: np.random.Generator, split_index: int, split_count: int) -> int:
    if split_count == 1:
        sale_window = str(rng.choice(["spot", "stored"], p=[0.62, 0.38]))
    elif split_index == 0:
        sale_window = "spot"
    elif split_index == split_count - 1:
        sale_window = "late"
    else:
        sale_window = "stored"

    if sale_window == "spot":
        return int(rng.integers(10, 45))
    if sale_window == "stored":
        return int(rng.integers(50, 95))
    return int(rng.integers(95, 145))
