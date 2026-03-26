from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from demoagro.etl.catalog import REQUIRED_RAW_TABLES, TABLE_SPECS, TableSpec


class ETLValidationError(Exception):
    """Raised when ETL validation fails."""


@dataclass(frozen=True)
class ValidationIssue:
    table_name: str
    severity: str
    message: str


def validate_tables(tables: dict[str, pd.DataFrame]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    issues.extend(_validate_required_tables(tables))
    for table_name, dataframe in tables.items():
        spec = TABLE_SPECS.get(table_name)
        if spec:
            issues.extend(_validate_required_columns(table_name, dataframe, spec))
            issues.extend(_validate_nulls(table_name, dataframe, spec))
            issues.extend(_validate_primary_key_duplicates(table_name, dataframe, spec))
            issues.extend(_validate_numeric_ranges(table_name, dataframe, spec))

    issues.extend(_validate_foreign_keys(tables))
    issues.extend(_validate_accounting_balance(tables))
    issues.extend(_validate_stock_not_negative(tables))
    issues.extend(_validate_sales_vs_quality_lots(tables))
    return issues


def raise_on_errors(issues: list[ValidationIssue]) -> None:
    errors = [issue for issue in issues if issue.severity == "error"]
    if errors:
        formatted = "\n".join(f"[{issue.table_name}] {issue.message}" for issue in errors)
        raise ETLValidationError(f"Fallaron validaciones ETL:\n{formatted}")


def validation_report(issues: list[ValidationIssue]) -> pd.DataFrame:
    return pd.DataFrame([issue.__dict__ for issue in issues])


def _validate_required_tables(tables: dict[str, pd.DataFrame]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for table_name in REQUIRED_RAW_TABLES:
        if table_name not in tables:
            issues.append(ValidationIssue(table_name, "error", "Tabla requerida no encontrada en raw."))
    return issues


def _validate_required_columns(table_name: str, dataframe: pd.DataFrame, spec: TableSpec) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    missing = [column for column in spec.required_columns if column not in dataframe.columns]
    if missing:
        issues.append(
            ValidationIssue(
                table_name,
                "error",
                f"Faltan columnas requeridas: {', '.join(missing)}.",
            )
        )
    return issues


def _validate_nulls(table_name: str, dataframe: pd.DataFrame, spec: TableSpec) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for column in spec.required_columns:
        if column not in dataframe.columns:
            continue
        null_count = int(dataframe[column].isna().sum())
        if null_count:
            issues.append(
                ValidationIssue(
                    table_name,
                    "error",
                    f"La columna requerida `{column}` tiene {null_count} nulos.",
                )
            )
    return issues


def _validate_primary_key_duplicates(table_name: str, dataframe: pd.DataFrame, spec: TableSpec) -> list[ValidationIssue]:
    if not spec.primary_key:
        return []
    if any(column not in dataframe.columns for column in spec.primary_key):
        return []
    duplicates = int(dataframe.duplicated(list(spec.primary_key)).sum())
    if duplicates:
        return [ValidationIssue(table_name, "error", f"Se encontraron {duplicates} duplicados de PK.")]
    return []


def _validate_numeric_ranges(table_name: str, dataframe: pd.DataFrame, spec: TableSpec) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for column, min_value in spec.numeric_min.items():
        if column not in dataframe.columns:
            continue
        series = pd.to_numeric(dataframe[column], errors="coerce")
        invalid = int((series < min_value).sum())
        if invalid:
            issues.append(
                ValidationIssue(
                    table_name,
                    "error",
                    f"La columna `{column}` tiene {invalid} valores menores a {min_value}.",
                )
            )
    return issues


def _validate_foreign_keys(tables: dict[str, pd.DataFrame]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for table_name, spec in TABLE_SPECS.items():
        if table_name not in tables:
            continue
        dataframe = tables[table_name]
        for fk in spec.foreign_keys:
            if fk.reference_table not in tables:
                issues.append(
                    ValidationIssue(
                        table_name,
                        "warning",
                        f"No se pudo validar FK hacia {fk.reference_table} porque esa tabla no esta cargada.",
                    )
                )
                continue
            if any(column not in dataframe.columns for column in fk.columns):
                continue
            reference = tables[fk.reference_table]
            if any(column not in reference.columns for column in fk.reference_columns):
                continue

            local = dataframe[list(fk.columns)].copy()
            if fk.nullable:
                local = local.dropna()
            ref = reference[list(fk.reference_columns)].drop_duplicates()
            merged = local.merge(
                ref,
                how="left",
                left_on=list(fk.columns),
                right_on=list(fk.reference_columns),
                indicator=True,
            )
            missing = int((merged["_merge"] == "left_only").sum())
            if missing:
                issues.append(
                    ValidationIssue(
                        table_name,
                        "error",
                        f"La FK {fk.columns} -> {fk.reference_table}{fk.reference_columns} tiene {missing} valores huerfanos.",
                    )
                )
    return issues


def _validate_accounting_balance(tables: dict[str, pd.DataFrame]) -> list[ValidationIssue]:
    if "cont_asientos_det" not in tables:
        return []
    lines = tables["cont_asientos_det"]
    if not {"asiento_id", "debit_amount", "credit_amount"}.issubset(lines.columns):
        return []
    grouped = lines.groupby("asiento_id").agg(
        debit=("debit_amount", "sum"),
        credit=("credit_amount", "sum"),
    )
    diff = (grouped["debit"] - grouped["credit"]).round(2)
    invalid = int((diff != 0).sum())
    if invalid:
        return [ValidationIssue("cont_asientos_det", "error", f"Hay {invalid} asientos desbalanceados.")]
    return []


def _validate_stock_not_negative(tables: dict[str, pd.DataFrame]) -> list[ValidationIssue]:
    if "erp_stock_actual" not in tables:
        return []
    stock = tables["erp_stock_actual"]
    if "quantity" not in stock.columns:
        return []
    invalid = int((pd.to_numeric(stock["quantity"], errors="coerce") < 0).sum())
    if invalid:
        return [ValidationIssue("erp_stock_actual", "error", f"Hay {invalid} saldos de stock negativos.")]
    return []


def _validate_sales_vs_quality_lots(tables: dict[str, pd.DataFrame]) -> list[ValidationIssue]:
    if "erp_lotes_calidad" not in tables or "erp_despachos_venta_det" not in tables:
        return []
    quality = tables["erp_lotes_calidad"][["lote_calidad_id", "available_tons"]]
    sales = tables["erp_despachos_venta_det"].groupby("lote_calidad_id", as_index=False)["quantity"].sum()
    merged = quality.merge(sales, on="lote_calidad_id", how="left").fillna({"quantity": 0})
    invalid = int((merged["quantity"] > merged["available_tons"] + 1e-9).sum())
    if invalid:
        return [ValidationIssue("erp_despachos_venta_det", "error", f"Hay {invalid} lotes de calidad sobrevendidos.")]
    return []
