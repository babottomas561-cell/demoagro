from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from demoagro.config import CROP_LIBRARY, SimulationConfig
from demoagro.simulation.common import campaign_date, frame
from demoagro.simulation.purchases import average_purchase_costs


def simulate_operations(
    config: SimulationConfig,
    rng: np.random.Generator,
    masters: dict[str, pd.DataFrame],
    purchase_data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    lot_campaign = masters["erp_lote_campania"]
    campaigns = masters["erp_campanias"].set_index("campania_id")
    lots = masters["erp_lotes"].set_index("lote_id")
    products = masters["erp_productos"]
    product_map = products.set_index("product_code")
    purchase_costs = average_purchase_costs(purchase_data)

    rows = defaultdict(list)
    labor_seq = 1
    consumption_seq = 1
    harvest_seq = 1
    quality_lot_seq = 1
    quality_analysis_seq = 1
    target_seq = 1

    for _, assignment in lot_campaign.iterrows():
        campaign = campaigns.loc[assignment["campania_id"]]
        lot = lots.loc[assignment["lote_id"]]
        crop_code = assignment["crop_code"]
        crop = CROP_LIBRARY[crop_code]
        area = float(assignment["sown_hectares"])
        campaign_start_year = int(pd.Timestamp(campaign["campaign_start_date"]).year)
        deposit_id = "DEP_0002" if str(lot["establecimiento_id"]) == "EST_0001" else "DEP_0003"

        season_factor = float(campaign["campaign_weather_factor"]) * float(lot["soil_productivity_index"])
        direct_cost_total = 0.0

        rows["erp_rendimientos_objetivo"].append(
            {
                "rendimiento_objetivo_id": f"RYO_{target_seq:05d}",
                "lote_campania_id": assignment["lote_campania_id"],
                "target_tn_ha": round(float(assignment["expected_yield_tn_ha"]), 2),
            }
        )
        target_seq += 1

        spray_codes = [code for code in ["GLIFOSATO", "INSECTICIDA", "FUNGICIDA"] if code in crop["input_rates"]]
        spray_events = list(crop["spray_months"])

        labor_plan = [
            ("SIEMBRA", int(crop["sow_month"]), [crop["seed_code"]]),
            ("FERTILIZACION", int(crop["fert_month"]), [code for code in ["UREA", "MAP"] if code in crop["input_rates"]]),
        ] + [
            ("PULVERIZACION", int(month), [spray_codes[index]] if index < len(spray_codes) else [])
            for index, month in enumerate(spray_events)
        ]

        for labor_type_code, month, consumed_codes in labor_plan:
            labor_id = f"LAB_{labor_seq:05d}"
            labor_date = campaign_date(campaign_start_year, month, rng)
            per_ha_cost = float(crop["labor_costs"][labor_type_code]) * float(rng.uniform(0.96, 1.08))
            direct_cost = round(area * per_ha_cost, 2)
            direct_cost_total += direct_cost
            rows["erp_labores"].append(
                {
                    "labor_id": labor_id,
                    "lote_campania_id": assignment["lote_campania_id"],
                    "labor_tipo_id": _labor_type_id(labor_type_code),
                    "labor_type_code": labor_type_code,
                    "centro_costo_id": "CC_0001",
                    "fecha": labor_date,
                    "superficie_ha": area,
                    "horas_maquina": round(area * float(rng.uniform(0.4, 0.9)), 2),
                    "horas_hombre": round(area * float(rng.uniform(0.25, 0.5)), 2),
                    "costo_directo": direct_cost,
                }
            )

            for code in consumed_codes:
                if code not in crop["input_rates"]:
                    continue
                quantity = round(area * float(crop["input_rates"][code]), 2)
                product_id = str(product_map.loc[code, "producto_id"])
                unit_cost = float(purchase_costs.get(product_id, product_map.loc[code, "standard_cost"]))
                cost_total = round(quantity * unit_cost, 2)
                direct_cost_total += cost_total
                rows["erp_consumo_insumos"].append(
                    {
                        "consumo_id": f"CONS_{consumption_seq:05d}",
                        "labor_id": labor_id,
                        "producto_id": product_id,
                        "deposito_id": "DEP_0001",
                        "quantity": quantity,
                        "unit_cost": round(unit_cost, 4),
                        "total_cost": cost_total,
                    }
                )
                consumption_seq += 1

            labor_seq += 1

        harvest_labor_id = f"LAB_{labor_seq:05d}"
        harvest_date = campaign_date(campaign_start_year, int(crop["harvest_month"]), rng)
        harvest_direct_cost = round(area * float(crop["labor_costs"]["COSECHA"]) * float(rng.uniform(0.97, 1.1)), 2)
        direct_cost_total += harvest_direct_cost

        rows["erp_labores"].append(
            {
                "labor_id": harvest_labor_id,
                "lote_campania_id": assignment["lote_campania_id"],
                "labor_tipo_id": _labor_type_id("COSECHA"),
                "labor_type_code": "COSECHA",
                "centro_costo_id": "CC_0001",
                "fecha": harvest_date,
                "superficie_ha": area,
                "horas_maquina": round(area * float(rng.uniform(0.45, 0.85)), 2),
                "horas_hombre": round(area * float(rng.uniform(0.20, 0.35)), 2),
                "costo_directo": harvest_direct_cost,
            }
        )
        labor_seq += 1

        gross_yield = max(
            float(crop["yield_tn_ha"]) * season_factor * float(rng.normal(1.0, 0.08)),
            float(crop["yield_tn_ha"]) * 0.7,
        )
        gross_tons = round(area * gross_yield, 2)
        moisture_pct = round(_quality_metric(crop_code, "moisture", rng), 2)
        impurity_pct = round(_quality_metric(crop_code, "impurity", rng), 2)
        shrink_pct = round(float(rng.uniform(0.015, 0.045)), 4)
        net_tons = round(gross_tons * (1 - shrink_pct), 2)
        unit_cost_tn = round(direct_cost_total / max(net_tons, 1.0), 2)

        harvest_id = f"COS_{harvest_seq:05d}"
        rows["erp_cosechas"].append(
            {
                "cosecha_id": harvest_id,
                "lote_campania_id": assignment["lote_campania_id"],
                "labor_id": harvest_labor_id,
                "fecha": harvest_date,
                "toneladas_brutas": gross_tons,
                "humedad_pct": moisture_pct,
                "merma_pct": round(shrink_pct * 100, 2),
                "toneladas_netas": net_tons,
                "direct_cost_total": round(direct_cost_total, 2),
                "cost_per_ton": unit_cost_tn,
            }
        )

        quality_lot_id = f"QLT_{quality_lot_seq:05d}"
        quality_bonus = round(_quality_bonus(crop_code, moisture_pct, impurity_pct), 2)
        rows["erp_lotes_calidad"].append(
            {
                "lote_calidad_id": quality_lot_id,
                "producto_id": assignment["producto_id"],
                "deposito_id": deposit_id,
                "cosecha_id": harvest_id,
                "available_tons": net_tons,
                "base_cost_per_ton": unit_cost_tn,
                "bonus_castigo_unit": quality_bonus,
            }
        )
        rows["erp_analisis_calidad"].append(
            {
                "analisis_calidad_id": f"ANA_{quality_analysis_seq:05d}",
                "lote_calidad_id": quality_lot_id,
                "analysis_date": harvest_date,
                "humedad_pct": moisture_pct,
                "impurezas_pct": impurity_pct,
                "proteina_pct": round(_quality_metric(crop_code, "protein", rng), 2),
                "grado_comercial": _commercial_grade(moisture_pct, impurity_pct),
                "bonificacion_castigo_unit": quality_bonus,
            }
        )

        harvest_seq += 1
        quality_lot_seq += 1
        quality_analysis_seq += 1

    return {name: frame(data) for name, data in rows.items()}


def _labor_type_id(labor_type_code: str) -> str:
    mapping = {
        "SIEMBRA": "LABT_0001",
        "FERTILIZACION": "LABT_0002",
        "PULVERIZACION": "LABT_0003",
        "COSECHA": "LABT_0004",
    }
    return mapping[labor_type_code]


def _quality_metric(crop_code: str, metric: str, rng: np.random.Generator) -> float:
    params = {
        "MAIZ": {"moisture": (13.8, 1.0), "impurity": (1.8, 0.5), "protein": (8.4, 0.6)},
        "SOJA": {"moisture": (12.7, 0.8), "impurity": (1.6, 0.4), "protein": (35.5, 1.1)},
        "TRIGO": {"moisture": (12.9, 0.7), "impurity": (1.4, 0.4), "protein": (11.2, 0.8)},
    }
    mean, sd = params[crop_code][metric]
    return max(float(rng.normal(mean, sd)), 0.1)


def _quality_bonus(crop_code: str, moisture_pct: float, impurity_pct: float) -> float:
    moisture_penalty = max(0.0, moisture_pct - 13.5) * -1.2
    impurity_penalty = max(0.0, impurity_pct - 2.0) * -2.0
    crop_bonus = 3.0 if crop_code == "TRIGO" and moisture_pct < 12.5 else 0.0
    return moisture_penalty + impurity_penalty + crop_bonus


def _commercial_grade(moisture_pct: float, impurity_pct: float) -> str:
    if moisture_pct <= 13.5 and impurity_pct <= 2.0:
        return "GRADO_1"
    if moisture_pct <= 14.5 and impurity_pct <= 3.0:
        return "GRADO_2"
    return "FUERA_ESTANDAR"
