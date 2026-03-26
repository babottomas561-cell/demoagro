from __future__ import annotations

import pandas as pd

from demoagro.marts.common import period_from_date, safe_divide


def build_operations_lot_campaign(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    lot_campaign = tables["erp_lote_campania"].copy()
    lots = tables["erp_lotes"][["lote_id", "lot_name", "establecimiento_id", "net_hectares"]].copy()
    campaigns = tables["erp_campanias"][["campania_id", "campaign_code"]].copy()
    products = tables["erp_productos"][["producto_id", "product_code", "product_name"]].copy()
    targets = tables["erp_rendimientos_objetivo"][["lote_campania_id", "target_tn_ha"]].copy()
    harvests = tables["erp_cosechas"][
        ["lote_campania_id", "fecha", "toneladas_brutas", "toneladas_netas", "merma_pct", "direct_cost_total", "cost_per_ton"]
    ].copy()

    lot_ops = (
        lot_campaign.merge(lots, on="lote_id", how="left")
        .merge(campaigns, on="campania_id", how="left")
        .merge(products, on="producto_id", how="left")
        .merge(targets, on="lote_campania_id", how="left")
        .merge(harvests, on="lote_campania_id", how="left")
    )
    lot_ops["actual_yield_tn_ha"] = safe_divide(lot_ops["toneladas_netas"], lot_ops["sown_hectares"])
    lot_ops["yield_vs_target_pct"] = safe_divide(lot_ops["actual_yield_tn_ha"], lot_ops["target_tn_ha"])
    lot_ops["direct_cost_per_ha"] = safe_divide(lot_ops["direct_cost_total"], lot_ops["sown_hectares"])
    lot_ops["gross_output_value"] = lot_ops["toneladas_netas"] * lot_ops["cost_per_ton"] * 1.35
    lot_ops.insert(0, "mart_id", [f"MOP_{index + 1:04d}" for index in range(len(lot_ops))])
    return lot_ops.sort_values(["campaign_code", "lot_name"]).reset_index(drop=True)


def build_operations_period(tables: dict[str, pd.DataFrame]) -> pd.DataFrame:
    harvests = tables["erp_cosechas"].copy()
    harvests["period_id"] = period_from_date(harvests["fecha"])
    lot_campaign = tables["erp_lote_campania"][["lote_campania_id", "crop_code", "sown_hectares"]].copy()
    operations = harvests.merge(lot_campaign, on="lote_campania_id", how="left")
    period_ops = operations.groupby(["period_id", "crop_code"], as_index=False).agg(
        production_tons=("toneladas_netas", "sum"),
        gross_tons=("toneladas_brutas", "sum"),
        sown_hectares=("sown_hectares", "sum"),
        direct_cost_total=("direct_cost_total", "sum"),
    )
    period_ops["yield_tn_ha"] = safe_divide(period_ops["production_tons"], period_ops["sown_hectares"])
    period_ops["shrink_pct"] = safe_divide(period_ops["gross_tons"] - period_ops["production_tons"], period_ops["gross_tons"])
    period_ops["direct_cost_per_ton"] = safe_divide(period_ops["direct_cost_total"], period_ops["production_tons"])
    period_ops.insert(0, "mart_id", [f"MOPP_{index + 1:04d}" for index in range(len(period_ops))])
    return period_ops.sort_values(["period_id", "crop_code"]).reset_index(drop=True)
