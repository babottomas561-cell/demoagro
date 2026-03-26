from __future__ import annotations

from pathlib import Path

import pandas as pd

from demoagro.db.sqlite import connect_sqlite, default_sqlite_path
from demoagro.marts.commercial import build_sales_customer, build_sales_period
from demoagro.marts.finance import build_finance_period, build_working_capital_snapshot
from demoagro.marts.inventory import build_stock_snapshot
from demoagro.marts.operations import build_operations_lot_campaign, build_operations_period
from demoagro.metrics.catalog import metrics_catalog_frame


SOURCE_TABLES = [
    "fin_facturas_compra",
    "fin_facturas_venta",
    "fin_facturas_venta_det",
    "erp_despachos_venta",
    "erp_despachos_venta_det",
    "rrhh_liquidaciones",
    "mnt_ordenes_trabajo",
    "mnt_ordenes_trabajo_det",
    "log_viajes",
    "tax_posiciones_fiscales_periodo",
    "fin_movimientos_tesoreria",
    "fin_cuentas_cobrar",
    "fin_cuentas_pagar",
    "erp_clientes",
    "erp_proveedores",
    "erp_productos",
    "erp_depositos",
    "erp_stock_actual",
    "erp_cosechas",
    "erp_lote_campania",
    "erp_lotes",
    "erp_campanias",
    "erp_rendimientos_objetivo",
]


def build_all_marts(db_path: str | Path | None = None) -> dict[str, pd.DataFrame]:
    resolved_db_path = db_path or default_sqlite_path()
    tables = _read_source_tables(resolved_db_path)

    working_capital = build_working_capital_snapshot(tables)
    marts = {
        "mart_finance_period": build_finance_period(tables),
        "mart_operations_lot_campaign": build_operations_lot_campaign(tables),
        "mart_operations_period": build_operations_period(tables),
        "mart_sales_period": build_sales_period(tables),
        "mart_sales_customer": build_sales_customer(tables),
        "mart_stock_snapshot": build_stock_snapshot(tables),
        "mart_metric_catalog": metrics_catalog_frame(),
        **working_capital,
    }
    _write_marts(resolved_db_path, marts)
    return marts


def _read_source_tables(db_path: str | Path) -> dict[str, pd.DataFrame]:
    connection = connect_sqlite(db_path)
    try:
        return {
            table_name: pd.read_sql_query(f'SELECT * FROM "{table_name}"', connection)
            for table_name in SOURCE_TABLES
        }
    finally:
        connection.close()


def _write_marts(db_path: str | Path, marts: dict[str, pd.DataFrame]) -> None:
    connection = connect_sqlite(db_path)
    try:
        for table_name, dataframe in marts.items():
            dataframe.to_sql(table_name, connection, if_exists="replace", index=False)
        connection.commit()
    finally:
        connection.close()
