from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from demoagro.simulation.orchestrator import export_datasets, run_simulation, simulation_summary


def main() -> None:
    datasets = run_simulation()
    output_dir = ROOT / "data" / "raw"
    export_datasets(output_dir, datasets)
    summary = simulation_summary(datasets)
    print(summary.to_string(index=False))
    print(f"\nCSV exportados en: {output_dir}")


if __name__ == "__main__":
    main()
