from __future__ import annotations

from pathlib import Path

import pandas as pd

from demoagro.db.sqlite import default_sqlite_path
from demoagro.etl.extract import read_raw_tables
from demoagro.etl.load import load_to_sqlite
from demoagro.etl.transform import export_staged_tables, transform_tables
from demoagro.etl.validate import raise_on_errors, validate_tables, validation_report


def run_etl(
    raw_dir: str | Path | None = None,
    staged_dir: str | Path | None = None,
    db_path: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    raw_tables = read_raw_tables(raw_dir)
    staged_tables = transform_tables(raw_tables)
    issues = validate_tables(staged_tables)
    raise_on_errors(issues)
    export_staged_tables(staged_tables, staged_dir)
    load_stats = load_to_sqlite(staged_tables, db_path or default_sqlite_path())

    return {
        "validation_report": validation_report(issues),
        "load_stats": load_stats,
    }
