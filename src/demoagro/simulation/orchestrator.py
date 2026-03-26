from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from demoagro.config import SimulationConfig
from demoagro.simulation.accounting import simulate_accounting
from demoagro.simulation.finance import simulate_finance
from demoagro.simulation.logistics import simulate_logistics
from demoagro.simulation.maintenance import simulate_maintenance
from demoagro.simulation.masters import generate_master_data
from demoagro.simulation.payroll import simulate_payroll
from demoagro.simulation.production import simulate_operations
from demoagro.simulation.purchases import simulate_purchases
from demoagro.simulation.sales import simulate_sales
from demoagro.simulation.stock import build_stock_ledger


def run_simulation(config: SimulationConfig | None = None) -> dict[str, pd.DataFrame]:
    config = config or SimulationConfig()
    rng = np.random.default_rng(config.seed)

    masters = generate_master_data(config, rng)
    purchases = simulate_purchases(config, rng, masters)
    production = simulate_operations(config, rng, masters, purchases)
    sales = simulate_sales(config, rng, masters, production)
    logistics = simulate_logistics(rng, masters, sales)
    maintenance = simulate_maintenance(rng, masters)
    payroll = simulate_payroll(config, rng, masters)
    finance = simulate_finance(config, rng, masters, purchases, sales, payroll, logistics)
    stock = build_stock_ledger(masters, purchases, production, sales, maintenance)
    accounting = simulate_accounting(masters, purchases, sales, finance, payroll, maintenance, logistics)

    datasets: dict[str, pd.DataFrame] = {}
    for bundle in [masters, purchases, production, sales, logistics, maintenance, payroll, finance, stock, accounting]:
        datasets.update(bundle)
    return datasets


def export_datasets(output_dir: str | Path, datasets: dict[str, pd.DataFrame]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    for table_name, dataframe in datasets.items():
        dataframe.to_csv(output_path / f"{table_name}.csv", index=False)


def simulation_summary(datasets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "table_name": table_name,
                "rows": len(dataframe),
                "columns": len(dataframe.columns),
            }
            for table_name, dataframe in sorted(datasets.items())
        ]
    )
