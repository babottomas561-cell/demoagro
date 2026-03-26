from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from demoagro.db.sqlite import default_sqlite_path
from demoagro.marts.builder import build_all_marts


def main() -> None:
    marts = build_all_marts()
    for table_name, dataframe in marts.items():
        print(f"{table_name}: {len(dataframe)} filas")
    print(f"\nMarts materializados en: {default_sqlite_path()}")


if __name__ == "__main__":
    main()
