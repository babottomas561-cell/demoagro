from __future__ import annotations

from collections import defaultdict
from math import ceil

import numpy as np
import pandas as pd

from demoagro.simulation.common import add_days, frame


def simulate_logistics(
    rng: np.random.Generator,
    masters: dict[str, pd.DataFrame],
    sales_data: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    dispatches = sales_data["erp_despachos_venta"].set_index("despacho_venta_id")
    dispatch_details = sales_data["erp_despachos_venta_det"]
    transporters = masters["log_transportistas"]

    rows = defaultdict(list)
    trip_seq = 1
    trip_det_seq = 1

    for _, dispatch_det in dispatch_details.iterrows():
        dispatch = dispatches.loc[dispatch_det["despacho_venta_id"]]
        quantity = float(dispatch_det["quantity"])
        trip_count = max(1, ceil(quantity / 28.0))
        third_party = bool(rng.choice([True, False], p=[0.68, 0.32]))
        transporter_mode = "TERCERO" if third_party else "PROPIO"
        transporter = transporters.loc[transporters["mode"] == transporter_mode].sample(
            n=1, random_state=int(rng.integers(1, 1_000_000))
        ).iloc[0]

        for trip_number in range(trip_count):
            trip_id = f"VIA_{trip_seq:05d}"
            trip_det_id = f"VDE_{trip_det_seq:05d}"
            trip_quantity = round(quantity / trip_count, 2)
            distance_km = int(rng.integers(55, 280))
            cost_per_ton = float(rng.uniform(9.0, 14.5)) if third_party else float(rng.uniform(5.5, 8.0))
            rows["log_viajes"].append(
                {
                    "viaje_id": trip_id,
                    "transportista_id": transporter["transportista_id"],
                    "vehiculo_id": None if third_party else "ACT_0006",
                    "dispatch_date": dispatch["dispatch_date"],
                    "delivery_date": add_days(pd.Timestamp(dispatch["dispatch_date"]).date(), int(rng.integers(1, 3))),
                    "distance_km": distance_km,
                    "mode": transporter_mode,
                    "total_cost": round(trip_quantity * cost_per_ton, 2),
                }
            )
            rows["log_viajes_det"].append(
                {
                    "viaje_det_id": trip_det_id,
                    "viaje_id": trip_id,
                    "despacho_venta_id": dispatch_det["despacho_venta_id"],
                    "quantity": trip_quantity,
                    "cost_per_ton": round(cost_per_ton, 2),
                }
            )
            trip_seq += 1
            trip_det_seq += 1

    return {table_name: frame(data) for table_name, data in rows.items()}
