from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.errors import EmptyDataError

from demoagro.db.sqlite import project_root
from demoagro.etl.catalog import EMPTY_TABLE_COLUMNS, LOAD_ORDER


def default_raw_dir() -> Path:
    return project_root() / "data" / "raw"


def read_raw_tables(raw_dir: str | Path | None = None) -> dict[str, pd.DataFrame]:
    source_dir = Path(raw_dir) if raw_dir else default_raw_dir()
    if not source_dir.exists():
        raise FileNotFoundError(f"No existe el directorio raw: {source_dir}")

    tables: dict[str, pd.DataFrame] = {}
    for csv_path in sorted(source_dir.glob("*.csv")):
        try:
            tables[csv_path.stem] = pd.read_csv(csv_path)
        except EmptyDataError:
            columns = list(EMPTY_TABLE_COLUMNS.get(csv_path.stem, ()))
            tables[csv_path.stem] = pd.DataFrame(columns=columns)

    ordered_tables: dict[str, pd.DataFrame] = {}
    for table_name in LOAD_ORDER:
        if table_name in tables:
            ordered_tables[table_name] = tables[table_name]
    for table_name, dataframe in tables.items():
        if table_name not in ordered_tables:
            ordered_tables[table_name] = dataframe
    return ordered_tables
