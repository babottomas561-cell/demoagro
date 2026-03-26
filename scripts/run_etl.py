from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from demoagro.db.sqlite import default_sqlite_path
from demoagro.etl.pipeline import run_etl


def main() -> None:
    result = run_etl()
    print("ETL completado.\n")
    print("Validaciones:")
    validation_report = result["validation_report"]
    if validation_report.empty:
        print("Sin observaciones.")
    else:
        print(validation_report.to_string(index=False))

    print("\nCarga a SQLite:")
    print(result["load_stats"].to_string(index=False))
    print(f"\nBase generada en: {default_sqlite_path()}")


if __name__ == "__main__":
    main()
