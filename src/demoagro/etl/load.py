from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from demoagro.db.sqlite import connect_sqlite, default_sqlite_path
from demoagro.etl.catalog import LOAD_ORDER, TABLE_SPECS


def load_to_sqlite(
    tables: dict[str, pd.DataFrame],
    db_path: str | Path | None = None,
) -> pd.DataFrame:
    connection = connect_sqlite(db_path or default_sqlite_path(), foreign_keys=False)
    load_stats: list[dict[str, object]] = []
    try:
        for table_name in LOAD_ORDER:
            if table_name not in tables:
                continue
            dataframe = tables[table_name]
            dataframe.to_sql(table_name, connection, if_exists="replace", index=False)
            _create_indexes(connection, table_name)
            load_stats.append(
                {
                    "table_name": table_name,
                    "rows_loaded": len(dataframe),
                    "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )

        extra_tables = [name for name in tables if name not in LOAD_ORDER]
        for table_name in extra_tables:
            dataframe = tables[table_name]
            dataframe.to_sql(table_name, connection, if_exists="replace", index=False)
            _create_indexes(connection, table_name)
            load_stats.append(
                {
                    "table_name": table_name,
                    "rows_loaded": len(dataframe),
                    "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
                }
            )

        stats_df = pd.DataFrame(load_stats)
        stats_df.to_sql("etl_table_load_log", connection, if_exists="replace", index=False)
        connection.commit()
    finally:
        connection.close()

    return pd.DataFrame(load_stats)


def _create_indexes(connection, table_name: str) -> None:
    spec = TABLE_SPECS.get(table_name)
    if not spec:
        return

    if spec.primary_key:
        index_name = f"ux_{table_name}_{'_'.join(spec.primary_key)}"
        columns = ", ".join(spec.primary_key)
        connection.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" ({_quote_columns(spec.primary_key)});')

    for index, fk in enumerate(spec.foreign_keys, start=1):
        index_name = f"ix_{table_name}_fk_{index}"
        connection.execute(
            f'CREATE INDEX IF NOT EXISTS "{index_name}" ON "{table_name}" ({_quote_columns(fk.columns)});'
        )


def _quote_columns(columns: tuple[str, ...]) -> str:
    return ", ".join(f'"{column}"' for column in columns)
