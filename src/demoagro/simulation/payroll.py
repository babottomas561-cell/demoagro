from __future__ import annotations

from collections import defaultdict
from datetime import date

import numpy as np
import pandas as pd

from demoagro.config import SimulationConfig
from demoagro.simulation.common import add_days, frame, month_starts


def simulate_payroll(
    config: SimulationConfig,
    rng: np.random.Generator,
    masters: dict[str, pd.DataFrame],
) -> dict[str, pd.DataFrame]:
    employees = masters["rrhh_empleados"]
    categories = masters["rrhh_categorias"].set_index("category_code")
    campaigns = masters["erp_campanias"]

    start_date = pd.Timestamp(campaigns["campaign_start_date"].min()).date()
    last_campaign_end = pd.Timestamp(campaigns["campaign_end_date"].max()).date()
    end_date = date(last_campaign_end.year, 12, 1)
    periods = month_starts(start_date, end_date)

    rows = defaultdict(list)
    nov_seq = 1
    liquidation_seq = 1
    liquidation_det_seq = 1

    peak_months = {4, 5, 11, 12}

    for period_start in periods:
        period_id = f"{period_start.year}{period_start.month:02d}"
        for _, employee in employees.iterrows():
            category = categories.loc[employee["category_code"]]
            base_salary = float(category["base_salary"]) * float(rng.uniform(0.98, 1.04))
            overtime = 0.0
            bonus = 0.0
            if employee["category_code"] in {"OPER_CAMPO", "CHOFER", "SUPERVISOR"} and period_start.month in peak_months:
                overtime_hours = int(rng.integers(6, 24))
                overtime = round(overtime_hours * float(rng.uniform(9.0, 12.5)), 2)
                rows["rrhh_novedades"].append(
                    {
                        "novedad_id": f"NOV_{nov_seq:05d}",
                        "empleado_id": employee["empleado_id"],
                        "period_id": period_id,
                        "novelty_type": "HORAS_EXTRA",
                        "quantity": overtime_hours,
                        "amount": overtime,
                    }
                )
                nov_seq += 1
            if employee["category_code"] in {"COMERCIAL", "SUPERVISOR"} and period_start.month in {6, 12}:
                bonus = round(float(rng.uniform(80.0, 220.0)), 2)
                rows["rrhh_novedades"].append(
                    {
                        "novedad_id": f"NOV_{nov_seq:05d}",
                        "empleado_id": employee["empleado_id"],
                        "period_id": period_id,
                        "novelty_type": "BONO",
                        "quantity": 1,
                        "amount": bonus,
                    }
                )
                nov_seq += 1

            gross_salary = round(base_salary + overtime + bonus, 2)
            employee_deductions = round(gross_salary * config.employee_deduction_rate, 2)
            employer_contrib = round(gross_salary * config.employer_contrib_rate, 2)
            net_salary = round(gross_salary - employee_deductions, 2)

            liquidation_id = f"LIQ_{liquidation_seq:06d}"
            pay_date = add_days(period_start, 35)
            rows["rrhh_liquidaciones"].append(
                {
                    "liquidacion_id": liquidation_id,
                    "empleado_id": employee["empleado_id"],
                    "period_id": period_id,
                    "period_start": period_start,
                    "pay_date": pay_date,
                    "gross_salary": gross_salary,
                    "employee_deductions": employee_deductions,
                    "employer_contrib": employer_contrib,
                    "net_salary": net_salary,
                    "centro_costo_id": employee["centro_costo_id"],
                }
            )

            detail_rows = [
                ("BASICO", 1, round(base_salary, 2), True, False),
                ("DESCUENTOS", 1, -employee_deductions, False, False),
                ("CARGAS_SOCIALES", 1, employer_contrib, False, True),
            ]
            if overtime > 0:
                detail_rows.append(("HORAS_EXTRA", 1, overtime, True, False))
            if bonus > 0:
                detail_rows.append(("BONO", 1, bonus, True, False))

            for concept_code, quantity, amount, remunerative_flag, employer_flag in detail_rows:
                rows["rrhh_liquidaciones_det"].append(
                    {
                        "liquidacion_det_id": f"LIQD_{liquidation_det_seq:06d}",
                        "liquidacion_id": liquidation_id,
                        "concept_code": concept_code,
                        "quantity": quantity,
                        "amount": amount,
                        "remunerative_flag": remunerative_flag,
                        "employer_flag": employer_flag,
                    }
                )
                liquidation_det_seq += 1

            liquidation_seq += 1

    return {table_name: frame(data) for table_name, data in rows.items()}
