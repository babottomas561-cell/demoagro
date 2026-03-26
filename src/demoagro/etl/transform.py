from __future__ import annotations

from pathlib import Path

import pandas as pd

from demoagro.db.sqlite import project_root
from demoagro.etl.catalog import DATE_COLUMNS, EMPTY_TABLE_COLUMNS, LOAD_ORDER, TABLE_SPECS


TEXT_KEEP_PATTERNS = (
    "id",
    "code",
    "name",
    "type",
    "status",
    "mode",
    "memo",
    "reason",
    "currency",
    "country",
    "group",
    "region",
)


def default_staged_dir() -> Path:
    return project_root() / "data" / "staged"


def transform_tables(raw_tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    staged_tables: dict[str, pd.DataFrame] = {}
    for table_name, dataframe in raw_tables.items():
        staged_tables[table_name] = transform_table(table_name, dataframe)

    ordered_tables: dict[str, pd.DataFrame] = {}
    for table_name in LOAD_ORDER:
        if table_name in staged_tables:
            ordered_tables[table_name] = staged_tables[table_name]
    for table_name, dataframe in staged_tables.items():
        if table_name not in ordered_tables:
            ordered_tables[table_name] = dataframe
    return ordered_tables


def transform_table(table_name: str, dataframe: pd.DataFrame) -> pd.DataFrame:
    if dataframe.empty and len(dataframe.columns) == 0 and table_name in EMPTY_TABLE_COLUMNS:
        dataframe = pd.DataFrame(columns=list(EMPTY_TABLE_COLUMNS[table_name]))
    else:
        dataframe = dataframe.copy()

    dataframe.columns = [column.strip() for column in dataframe.columns]
    dataframe = dataframe.loc[:, ~dataframe.columns.duplicated()]

    for column in dataframe.columns:
        if pd.api.types.is_object_dtype(dataframe[column]):
            normalized = dataframe[column].map(lambda value: value.strip() if isinstance(value, str) else value)
            normalized = normalized.replace({"": None, "nan": None, "None": None})
            dataframe[column] = normalized

    dataframe = _cast_dates(dataframe)
    dataframe = _cast_booleans(dataframe)
    dataframe = _cast_numeric_candidates(dataframe)
    dataframe = _order_columns(table_name, dataframe)
    return dataframe


def export_staged_tables(
    staged_tables: dict[str, pd.DataFrame],
    staged_dir: str | Path | None = None,
) -> None:
    target_dir = Path(staged_dir) if staged_dir else default_staged_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    for table_name, dataframe in staged_tables.items():
        dataframe.to_csv(target_dir / f"{table_name}.csv", index=False)


def _cast_dates(dataframe: pd.DataFrame) -> pd.DataFrame:
    for column in dataframe.columns:
        if column in DATE_COLUMNS or column.endswith("_date"):
            parsed = pd.to_datetime(dataframe[column], errors="coerce")
            if parsed.notna().sum() or dataframe[column].isna().all():
                dataframe[column] = parsed.dt.date.astype("string")
                dataframe[column] = dataframe[column].replace("<NA>", None)
    return dataframe


def _cast_booleans(dataframe: pd.DataFrame) -> pd.DataFrame:
    for column in dataframe.columns:
        if not pd.api.types.is_object_dtype(dataframe[column]):
            continue
        non_null = dataframe[column].dropna()
        if non_null.empty:
            continue
        normalized = non_null.astype(str).str.lower().unique().tolist()
        if set(normalized).issubset({"true", "false"}):
            dataframe[column] = dataframe[column].map(
                lambda value: None if pd.isna(value) else 1 if str(value).lower() == "true" else 0
            )
    return dataframe


def _cast_numeric_candidates(dataframe: pd.DataFrame) -> pd.DataFrame:
    for column in dataframe.columns:
        if column in DATE_COLUMNS or column.endswith("_date"):
            continue
        if _looks_like_textual_column(column):
            continue
        if not pd.api.types.is_object_dtype(dataframe[column]):
            continue

        original = dataframe[column]
        non_null = original.dropna()
        if non_null.empty:
            continue

        parsed = pd.to_numeric(non_null, errors="coerce")
        if len(parsed) and (parsed.notna().sum() / len(parsed)) >= 0.95:
            dataframe[column] = pd.to_numeric(original, errors="coerce")
    return dataframe


def _looks_like_textual_column(column_name: str) -> bool:
    return any(token in column_name.lower() for token in TEXT_KEEP_PATTERNS)


def _order_columns(table_name: str, dataframe: pd.DataFrame) -> pd.DataFrame:
    spec = TABLE_SPECS.get(table_name)
    if not spec or not spec.columns:
        return dataframe
    ordered = [column for column in spec.columns if column in dataframe.columns]
    extras = [column for column in dataframe.columns if column not in ordered]
    return dataframe[ordered + extras]
