from __future__ import annotations

from collections import defaultdict

import pandas as pd

from demoagro.simulation.common import frame


def build_stock_ledger(
    masters: dict[str, pd.DataFrame],
    purchase_data: dict[str, pd.DataFrame],
    production_data: dict[str, pd.DataFrame],
    sales_data: dict[str, pd.DataFrame],
    maintenance_data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    products = masters["erp_productos"].set_index("producto_id")
    purchase_receipts = purchase_data["erp_recepciones_compra"].set_index("recepcion_compra_id")
    purchase_receipt_details = purchase_data["erp_recepciones_compra_det"]
    harvests = production_data["erp_cosechas"].set_index("cosecha_id")
    quality_lots = production_data["erp_lotes_calidad"].set_index("lote_calidad_id")
    consumption = production_data["erp_consumo_insumos"]
    labors = production_data["erp_labores"].set_index("labor_id")
    dispatches = sales_data["erp_despachos_venta"].set_index("despacho_venta_id")
    dispatch_details = sales_data["erp_despachos_venta_det"]
    work_orders = maintenance_data["mnt_ordenes_trabajo"].set_index("orden_trabajo_id")
    work_order_details = maintenance_data["mnt_ordenes_trabajo_det"]

    rows = []
    movement_seq = 1

    for _, receipt_det in purchase_receipt_details.iterrows():
        if str(products.loc[receipt_det["producto_id"], "category_code"]) == "SERVICIO":
            continue
        receipt = purchase_receipts.loc[receipt_det["recepcion_compra_id"]]
        rows.append(
            _stock_movement(
                movement_seq=movement_seq,
                movement_type="COMPRA_INGRESO",
                movement_date=receipt["receipt_date"],
                product_id=receipt_det["producto_id"],
                deposit_id=receipt["deposito_id"],
                quantity_in=float(receipt_det["received_quantity"]),
                quantity_out=0.0,
                unit_cost=float(receipt_det["unit_cost"]),
                source_table="erp_recepciones_compra_det",
                source_id=receipt_det["recepcion_compra_det_id"],
            )
        )
        movement_seq += 1

    for _, usage in consumption.iterrows():
        rows.append(
            _stock_movement(
                movement_seq=movement_seq,
                movement_type="CONSUMO_INSUMO",
                movement_date=labors.loc[usage["labor_id"], "fecha"],
                product_id=usage["producto_id"],
                deposit_id=usage["deposito_id"],
                quantity_in=0.0,
                quantity_out=float(usage["quantity"]),
                unit_cost=float(usage["unit_cost"]),
                source_table="erp_consumo_insumos",
                source_id=usage["consumo_id"],
            )
        )
        movement_seq += 1

    for _, quality_lot in quality_lots.reset_index().iterrows():
        harvest = harvests.loc[quality_lot["cosecha_id"]]
        rows.append(
            _stock_movement(
                movement_seq=movement_seq,
                movement_type="COSECHA_INGRESO",
                movement_date=harvest["fecha"],
                product_id=quality_lot["producto_id"],
                deposit_id=quality_lot["deposito_id"],
                quantity_in=float(quality_lot["available_tons"]),
                quantity_out=0.0,
                unit_cost=float(quality_lot["base_cost_per_ton"]),
                source_table="erp_lotes_calidad",
                source_id=quality_lot["lote_calidad_id"],
                lot_quality_id=quality_lot["lote_calidad_id"],
            )
        )
        movement_seq += 1

    for _, dispatch_det in dispatch_details.iterrows():
        dispatch = dispatches.loc[dispatch_det["despacho_venta_id"]]
        rows.append(
            _stock_movement(
                movement_seq=movement_seq,
                movement_type="VENTA_SALIDA",
                movement_date=dispatch["dispatch_date"],
                product_id=dispatch_det["producto_id"],
                deposit_id=dispatch["deposito_id"],
                quantity_in=0.0,
                quantity_out=float(dispatch_det["quantity"]),
                unit_cost=float(dispatch_det["cost_per_ton"]),
                source_table="erp_despachos_venta_det",
                source_id=dispatch_det["despacho_venta_det_id"],
                lot_quality_id=dispatch_det["lote_calidad_id"],
            )
        )
        movement_seq += 1

    for _, order_det in work_order_details.iterrows():
        order = work_orders.loc[order_det["orden_trabajo_id"]]
        rows.append(
            _stock_movement(
                movement_seq=movement_seq,
                movement_type="MANTENIMIENTO_SALIDA",
                movement_date=order["close_date"],
                product_id=order_det["producto_id"],
                deposit_id="DEP_0004",
                quantity_in=0.0,
                quantity_out=float(order_det["quantity"]),
                unit_cost=float(order_det["unit_cost"]),
                source_table="mnt_ordenes_trabajo_det",
                source_id=order_det["orden_trabajo_det_id"],
            )
        )
        movement_seq += 1

    movements = frame(rows).sort_values(["movement_date", "movimiento_stock_id"]).reset_index(drop=True)
    if movements.empty:
        stock_actual = pd.DataFrame()
    else:
        movements["net_quantity"] = movements["quantity_in"] - movements["quantity_out"]
        movements["net_value"] = movements["movement_value_in"] - movements["movement_value_out"]
        stock_actual = (
            movements.groupby(["product_id", "deposit_id", "lot_quality_id"], dropna=False)
            .agg(quantity=("net_quantity", "sum"), stock_value=("net_value", "sum"))
            .reset_index()
        )
        stock_actual["unit_value"] = stock_actual.apply(
            lambda row: round(row["stock_value"] / row["quantity"], 4) if row["quantity"] else 0.0,
            axis=1,
        )
        stock_actual["stock_actual_id"] = [f"STK_{index + 1:05d}" for index in range(len(stock_actual))]
        stock_actual.rename(
            columns={
                "product_id": "producto_id",
                "deposit_id": "deposito_id",
                "lot_quality_id": "lote_calidad_id",
            },
            inplace=True,
        )
        stock_actual = stock_actual[
            ["stock_actual_id", "producto_id", "deposito_id", "lote_calidad_id", "quantity", "stock_value", "unit_value"]
        ]

    return {
        "erp_movimientos_stock": movements,
        "erp_stock_actual": stock_actual,
        "erp_transferencias_stock": frame([]),
        "erp_ajustes_stock": frame([]),
    }


def _stock_movement(
    movement_seq: int,
    movement_type: str,
    movement_date,
    product_id: str,
    deposit_id: str,
    quantity_in: float,
    quantity_out: float,
    unit_cost: float,
    source_table: str,
    source_id: str,
    lot_quality_id: str | None = None,
) -> dict[str, object]:
    return {
        "movimiento_stock_id": f"MST_{movement_seq:06d}",
        "movement_type": movement_type,
        "movement_date": movement_date,
        "product_id": product_id,
        "deposit_id": deposit_id,
        "lot_quality_id": lot_quality_id,
        "quantity_in": round(quantity_in, 2),
        "quantity_out": round(quantity_out, 2),
        "unit_cost": round(unit_cost, 4),
        "movement_value_in": round(quantity_in * unit_cost, 2),
        "movement_value_out": round(quantity_out * unit_cost, 2),
        "source_table": source_table,
        "source_id": source_id,
    }
