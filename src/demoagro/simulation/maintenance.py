from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np
import pandas as pd

from demoagro.simulation.common import add_days, frame, month_starts


def simulate_maintenance(
    rng: np.random.Generator,
    masters: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    assets = masters["mnt_activos"]
    campaigns = masters["erp_campanias"]

    start_date = pd.Timestamp(campaigns["campaign_start_date"].min()).date()
    last_campaign_end = pd.Timestamp(campaigns["campaign_end_date"].max()).date()
    end_date = date(last_campaign_end.year, 12, 31)
    months = month_starts(start_date, end_date)

    rows = defaultdict(list)
    plan_seq = 1
    order_seq = 1
    order_det_seq = 1
    stop_seq = 1

    for _, asset in assets.iterrows():
        cycle_days = int(asset["maintenance_cycle_days"])
        rows["mnt_planes_preventivos"].append(
            {
                "plan_preventivo_id": f"MPL_{plan_seq:05d}",
                "activo_id": asset["activo_id"],
                "task_name": "Servicio preventivo",
                "cycle_days": cycle_days,
            }
        )
        plan_seq += 1

        preventive_months = months[:: max(1, cycle_days // 30)]
        for month in preventive_months:
            order_seq, order_det_seq = _append_work_order(
                rows=rows,
                order_seq=order_seq,
                order_det_seq=order_det_seq,
                asset=asset,
                order_date=add_days(month, int(rng.integers(0, 12))),
                work_type="PREVENTIVO",
                parts_mix=[("PROD_0013", 1), ("PROD_0015", 1)],
                rng=rng,
            )

        corrective_events = int(rng.integers(1, 4))
        for _ in range(corrective_events):
            event_date = add_days(start_date, int(rng.integers(45, (end_date - start_date).days)))
            order_seq, order_det_seq = _append_work_order(
                rows=rows,
                order_seq=order_seq,
                order_det_seq=order_det_seq,
                asset=asset,
                order_date=event_date,
                work_type="CORRECTIVO",
                parts_mix=[("PROD_0014", 1), ("PROD_0015", 1)],
                rng=rng,
            )
            rows["mnt_paradas_activo"].append(
                {
                    "parada_id": f"PRD_{stop_seq:05d}",
                    "activo_id": asset["activo_id"],
                    "start_date": event_date,
                    "end_date": add_days(event_date, int(rng.integers(1, 4))),
                    "downtime_hours": round(float(rng.uniform(8.0, 26.0)), 1),
                    "reason": "Falla mecanica",
                }
            )
            stop_seq += 1

    return {table_name: frame(data) for table_name, data in rows.items()}


def _append_work_order(
    rows: defaultdict[str, list[dict[str, object]]],
    order_seq: int,
    order_det_seq: int,
    asset: pd.Series,
    order_date,
    work_type: str,
    parts_mix: list[tuple[str, int]],
    rng: np.random.Generator,
) -> tuple[int, int]:
    order_id = f"MOT_{order_seq:05d}"
    labor_hours = round(float(rng.uniform(2.0, 8.0 if work_type == 'PREVENTIVO' else 14.0)), 2)
    internal_labor_cost = round(labor_hours * float(rng.uniform(22.0, 28.0)), 2)
    rows["mnt_ordenes_trabajo"].append(
        {
            "orden_trabajo_id": order_id,
            "activo_id": asset["activo_id"],
            "work_type": work_type,
            "order_date": order_date,
            "close_date": add_days(order_date, int(rng.integers(1, 4))),
            "labor_hours": labor_hours,
            "internal_labor_cost": internal_labor_cost,
            "status": "CERRADA",
        }
    )

    for product_id, base_qty in parts_mix:
        quantity = base_qty if work_type == "PREVENTIVO" else base_qty + int(rng.integers(0, 2))
        unit_cost = 15.0 if product_id == "PROD_0013" else 26.0 if product_id == "PROD_0015" else 42.0
        rows["mnt_ordenes_trabajo_det"].append(
            {
                "orden_trabajo_det_id": f"MOTD_{order_det_seq:05d}",
                "orden_trabajo_id": order_id,
                "producto_id": product_id,
                "quantity": quantity,
                "unit_cost": unit_cost,
                "total_cost": round(quantity * unit_cost, 2),
            }
        )
        order_det_seq += 1

    order_seq += 1
    return order_seq, order_det_seq
