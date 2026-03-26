from __future__ import annotations

import pandas as pd

from demoagro.marts.common import safe_divide


def build_stock_snapshot(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    stock = tables["erp_stock_actual"].copy()
    products = tables["erp_productos"][["producto_id", "product_code", "product_name", "category_code"]].copy()
    deposits = tables["erp_depositos"][["deposito_id", "deposit_name", "deposit_type"]].copy()

    snapshot = stock.merge(products, on="producto_id", how="left").merge(deposits, on="deposito_id", how="left")
    snapshot["unit_value"] = safe_divide(snapshot["stock_value"], snapshot["quantity"])
    total_value = snapshot["stock_value"].sum()
    snapshot["stock_value_share_pct"] = safe_divide(snapshot["stock_value"], total_value)
    snapshot.insert(0, "mart_id", [f"MSTK_{index + 1:04d}" for index in range(len(snapshot))])
    return snapshot.sort_values("stock_value", ascending=False).reset_index(drop=True)
