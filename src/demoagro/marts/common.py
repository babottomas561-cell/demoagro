from __future__ import annotations

from pathlib import Path

import pandas as pd

from demoagro.db.sqlite import connect_sqlite, default_sqlite_path


def read_table(table_name: str, db_path: str | Path | None = None) -> pd.DataFrame:
    connection = connect_sqlite(db_path or default_sqlite_path())
    try:
        return pd.read_sql_query(f'SELECT * FROM "{table_name}"', connection)
    finally:
        connection.close()


def materialize_table(
    table_name: str,
    dataframe: pd.DataFrame,
    db_path: str | Path | None = None,
) -> None:
    connection = connect_sqlite(db_path or default_sqlite_path())
    try:
        dataframe.to_sql(table_name, connection, if_exists="replace", index=False)
        connection.commit()
    finally:
        connection.close()


def period_from_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m")


def aging_bucket(days_value: float) -> str:
    if pd.isna(days_value):
        return "Sin vencimiento"
    if days_value <= 0:
        return "Al dia"
    if days_value <= 30:
        return "1-30"
    if days_value <= 60:
        return "31-60"
    if days_value <= 90:
        return "61-90"
    return "90+"


def latest_date(series_list: list[pd.Series]) -> pd.Timestamp:
    max_values: list[pd.Timestamp] = []
    for series in series_list:
        parsed = pd.to_datetime(series, errors="coerce")
        if parsed.notna().any():
            max_values.append(parsed.max())
    if not max_values:
        raise ValueError("No hay fechas disponibles para calcular snapshot.")
    return max(max_values)


def safe_divide(numerator: pd.Series | float, denominator: pd.Series | float) -> pd.Series | float:
    if isinstance(numerator, pd.Series) and isinstance(denominator, pd.Series):
        denominator_series = denominator.replace({0: pd.NA})
        return numerator.divide(denominator_series).fillna(0.0)
    if isinstance(numerator, pd.Series):
        if denominator == 0:
            return pd.Series(0.0, index=numerator.index)
        return numerator.divide(float(denominator)).fillna(0.0)
    if isinstance(denominator, pd.Series):
        denominator_series = denominator.replace({0: pd.NA})
        return pd.Series(float(numerator), index=denominator.index).divide(denominator_series).fillna(0.0)
    if denominator == 0:
        return 0.0
    return numerator / denominator
