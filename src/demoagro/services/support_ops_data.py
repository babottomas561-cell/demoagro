from __future__ import annotations

import pandas as pd


def build_support_overview(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, object]]:
    payroll = get_payroll_period(bundle, filters)
    maintenance = get_maintenance_period(bundle, filters)
    logistics = get_logistics_period(bundle, filters)

    payroll_total = float(payroll["payroll_total"].sum()) if not payroll.empty else 0.0
    extra_hours = float(payroll["extra_hours"].sum()) if not payroll.empty else 0.0
    maintenance_total = float(maintenance["total_cost"].sum()) if not maintenance.empty else 0.0
    downtime_hours = float(maintenance["downtime_hours"].sum()) if not maintenance.empty else 0.0
    logistics_cost = float(logistics["total_cost"].sum()) if not logistics.empty else 0.0
    third_party_share = _safe_divide(
        float(logistics["third_party_cost"].sum()) if not logistics.empty else 0.0,
        logistics_cost,
    )

    return [
        {
            "label": "Costo laboral total",
            "value": payroll_total,
            "format": "currency",
            "detail": "Sueldos brutos mas cargas patronales",
            "tone": "neutral",
        },
        {
            "label": "Horas extra",
            "value": extra_hours,
            "format": "number",
            "detail": "Novedades liquidadas en el periodo",
            "tone": "warning" if extra_hours > 220 else "neutral",
        },
        {
            "label": "Gasto mantenimiento",
            "value": maintenance_total,
            "format": "currency",
            "detail": "Labor interna mas repuestos/servicios",
            "tone": "warning" if maintenance_total > 25000 else "neutral",
        },
        {
            "label": "Horas de parada",
            "value": downtime_hours,
            "format": "number",
            "detail": "Downtime acumulado de activos",
            "tone": "danger" if downtime_hours > 70 else "warning" if downtime_hours > 35 else "neutral",
        },
        {
            "label": "Costo logistico",
            "value": logistics_cost,
            "format": "currency",
            "detail": "Costo total de viajes visibles",
            "tone": "neutral",
        },
        {
            "label": "Share tercerizado",
            "value": third_party_share,
            "format": "percent",
            "detail": "Participacion del costo tercerizado",
            "tone": "warning" if third_party_share > 0.7 else "neutral",
        },
    ]


def build_support_alerts(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> list[dict[str, str]]:
    payroll = get_payroll_period(bundle, filters)
    maintenance = get_maintenance_period(bundle, filters)
    logistics = get_logistics_period(bundle, filters)

    alerts: list[dict[str, str]] = []

    extra_hours = float(payroll["extra_hours"].sum()) if not payroll.empty else 0.0
    if extra_hours > 220:
        alerts.append(
            {
                "level": "warning",
                "title": "Carga extra relevante",
                "body": f"Las horas extra visibles suman {extra_hours:,.0f}; conviene revisar picos de campo y taller.",
            }
        )

    corrective_orders = float(maintenance["corrective_orders"].sum()) if not maintenance.empty else 0.0
    total_orders = float(maintenance["order_count"].sum()) if not maintenance.empty else 0.0
    corrective_share = _safe_divide(corrective_orders, total_orders)
    if corrective_share > 0.12:
        alerts.append(
            {
                "level": "warning",
                "title": "Mantenimiento mas reactivo",
                "body": f"El share correctivo visible esta en {corrective_share:.1%}; seria mejor bajarlo con mas preventivo.",
            }
        )

    downtime_hours = float(maintenance["downtime_hours"].sum()) if not maintenance.empty else 0.0
    if downtime_hours > 35:
        alerts.append(
            {
                "level": "danger" if downtime_hours > 70 else "warning",
                "title": "Paradas relevantes",
                "body": f"Las horas de parada suman {downtime_hours:,.1f}; revisar activos con mayor impacto.",
            }
        )

    third_party_share = _safe_divide(
        float(logistics["third_party_cost"].sum()) if not logistics.empty else 0.0,
        float(logistics["total_cost"].sum()) if not logistics.empty else 0.0,
    )
    if third_party_share > 0.7:
        alerts.append(
            {
                "level": "info",
                "title": "Dependencia logistica externa",
                "body": f"El costo tercerizado visible pesa {third_party_share:.1%}; hay poca capacidad propia relativa.",
            }
        )

    if not alerts:
        alerts.append(
            {
                "level": "success",
                "title": "Soporte operativo estable",
                "body": "RRHH, mantenimiento y logistica no muestran desvíos severos para el rango visible.",
            }
        )

    return alerts


def get_payroll_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    liquidations = bundle["rrhh_liquidaciones"].copy()
    novelties = bundle["rrhh_novedades"].copy()

    liquidations["period_id"] = pd.to_datetime(liquidations["period_start"], errors="coerce").dt.strftime("%Y-%m")
    liquidations = _apply_period_filter(liquidations, "period_id", filters)

    novelties["period_id"] = pd.to_datetime(novelties["period_id"].astype(str), format="%Y%m", errors="coerce").dt.strftime("%Y-%m")
    novelties = _apply_period_filter(novelties, "period_id", filters)

    if liquidations.empty:
        return pd.DataFrame(
            columns=[
                "period_id",
                "headcount",
                "gross_salary",
                "employer_contrib",
                "payroll_total",
                "net_salary",
                "extra_hours",
                "extra_amount",
                "bonus_amount",
            ]
        )

    period = liquidations.groupby("period_id", as_index=False).agg(
        headcount=("empleado_id", "nunique"),
        gross_salary=("gross_salary", "sum"),
        employer_contrib=("employer_contrib", "sum"),
        net_salary=("net_salary", "sum"),
    )
    period["payroll_total"] = period["gross_salary"] + period["employer_contrib"]

    extra_hours = _novelty_metric(novelties, "HORAS_EXTRA", "quantity", "extra_hours")
    extra_amount = _novelty_metric(novelties, "HORAS_EXTRA", "amount", "extra_amount")
    bonus_amount = _novelty_metric(novelties, "BONO", "amount", "bonus_amount")

    for novelty in [extra_hours, extra_amount, bonus_amount]:
        period = period.merge(novelty, on="period_id", how="left")
    return period.fillna(0.0).sort_values("period_id").reset_index(drop=True)


def build_payroll_center_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    liquidations = bundle["rrhh_liquidaciones"].copy()
    centers = bundle["erp_centros_costo"][["centro_costo_id", "center_name"]].copy()

    liquidations["period_id"] = pd.to_datetime(liquidations["period_start"], errors="coerce").dt.strftime("%Y-%m")
    liquidations = _apply_period_filter(liquidations, "period_id", filters)
    if liquidations.empty:
        return pd.DataFrame(columns=["center_name", "headcount", "payroll_total", "avg_net_salary"])

    liquidations = liquidations.merge(centers, on="centro_costo_id", how="left")
    summary = liquidations.groupby("center_name", as_index=False).agg(
        headcount=("empleado_id", "nunique"),
        gross_salary=("gross_salary", "sum"),
        employer_contrib=("employer_contrib", "sum"),
        net_salary=("net_salary", "sum"),
    )
    summary["payroll_total"] = summary["gross_salary"] + summary["employer_contrib"]
    summary["avg_net_salary"] = summary["net_salary"] / summary["headcount"].replace({0: pd.NA})
    return summary.fillna(0.0).sort_values("payroll_total", ascending=False).reset_index(drop=True)


def build_payroll_category_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    liquidations = bundle["rrhh_liquidaciones"].copy()
    employees = bundle["rrhh_empleados"][["empleado_id", "categoria_rrhh_id"]].copy()
    categories = bundle["rrhh_categorias"][["categoria_rrhh_id", "category_name"]].copy()
    novelties = bundle["rrhh_novedades"].copy()

    liquidations["period_id"] = pd.to_datetime(liquidations["period_start"], errors="coerce").dt.strftime("%Y-%m")
    liquidations = _apply_period_filter(liquidations, "period_id", filters)

    novelties["period_id"] = pd.to_datetime(novelties["period_id"].astype(str), format="%Y%m", errors="coerce").dt.strftime("%Y-%m")
    novelties = _apply_period_filter(novelties, "period_id", filters)
    overtime_by_employee = (
        novelties.loc[novelties["novelty_type"] == "HORAS_EXTRA"]
        .groupby("empleado_id", as_index=False)
        .agg(extra_hours=("quantity", "sum"))
    )

    if liquidations.empty:
        return pd.DataFrame(columns=["category_name", "headcount", "payroll_total", "avg_gross_salary", "extra_hours"])

    liquidations = liquidations.merge(employees, on="empleado_id", how="left").merge(categories, on="categoria_rrhh_id", how="left")
    summary = liquidations.groupby("category_name", as_index=False).agg(
        headcount=("empleado_id", "nunique"),
        gross_salary=("gross_salary", "sum"),
        employer_contrib=("employer_contrib", "sum"),
    )
    summary["payroll_total"] = summary["gross_salary"] + summary["employer_contrib"]
    summary["avg_gross_salary"] = summary["gross_salary"] / summary["headcount"].replace({0: pd.NA})

    employee_categories = liquidations[["empleado_id", "category_name"]].drop_duplicates()
    overtime_by_category = employee_categories.merge(overtime_by_employee, on="empleado_id", how="left")
    overtime_by_category = overtime_by_category.groupby("category_name", as_index=False).agg(extra_hours=("extra_hours", "sum"))
    summary = summary.merge(overtime_by_category, on="category_name", how="left")
    return summary.fillna(0.0).sort_values("payroll_total", ascending=False).reset_index(drop=True)


def get_maintenance_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    orders = bundle["mnt_ordenes_trabajo"].copy()
    details = bundle["mnt_ordenes_trabajo_det"].copy()
    downtime = bundle["mnt_paradas_activo"].copy()

    orders["period_id"] = pd.to_datetime(orders["close_date"], errors="coerce").dt.strftime("%Y-%m")
    orders = _apply_period_filter(orders, "period_id", filters)

    if orders.empty:
        return pd.DataFrame(
            columns=[
                "period_id",
                "order_count",
                "preventive_orders",
                "corrective_orders",
                "labor_hours",
                "internal_labor_cost",
                "parts_cost",
                "total_cost",
                "downtime_hours",
            ]
        )

    parts = details.groupby("orden_trabajo_id", as_index=False).agg(parts_cost=("total_cost", "sum"))
    orders = orders.merge(parts, on="orden_trabajo_id", how="left").fillna({"parts_cost": 0.0})
    orders["total_cost"] = orders["internal_labor_cost"] + orders["parts_cost"]

    period = orders.groupby("period_id", as_index=False).agg(
        order_count=("orden_trabajo_id", "nunique"),
        labor_hours=("labor_hours", "sum"),
        internal_labor_cost=("internal_labor_cost", "sum"),
        parts_cost=("parts_cost", "sum"),
        total_cost=("total_cost", "sum"),
    )
    work_type = orders.groupby("period_id", as_index=False).agg(
        preventive_orders=("work_type", lambda values: int((pd.Series(values) == "PREVENTIVO").sum())),
        corrective_orders=("work_type", lambda values: int((pd.Series(values) == "CORRECTIVO").sum())),
    )
    downtime["period_id"] = pd.to_datetime(downtime["end_date"], errors="coerce").dt.strftime("%Y-%m")
    downtime = _apply_period_filter(downtime, "period_id", filters)
    downtime_period = downtime.groupby("period_id", as_index=False).agg(downtime_hours=("downtime_hours", "sum"))

    period = period.merge(work_type, on="period_id", how="left").merge(downtime_period, on="period_id", how="left")
    return period.fillna(0.0).sort_values("period_id").reset_index(drop=True)


def build_maintenance_asset_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    orders = bundle["mnt_ordenes_trabajo"].copy()
    details = bundle["mnt_ordenes_trabajo_det"].copy()
    assets = bundle["mnt_activos"][["activo_id", "asset_name", "asset_type"]].copy()
    downtime = bundle["mnt_paradas_activo"].copy()

    orders["period_id"] = pd.to_datetime(orders["close_date"], errors="coerce").dt.strftime("%Y-%m")
    orders = _apply_period_filter(orders, "period_id", filters)
    if orders.empty:
        return pd.DataFrame(columns=["asset_name", "asset_type", "order_count", "corrective_orders", "total_cost", "downtime_hours"])

    parts = details.groupby("orden_trabajo_id", as_index=False).agg(parts_cost=("total_cost", "sum"))
    orders = orders.merge(parts, on="orden_trabajo_id", how="left").fillna({"parts_cost": 0.0})
    orders["total_cost"] = orders["internal_labor_cost"] + orders["parts_cost"]
    orders = orders.merge(assets, on="activo_id", how="left")

    summary = orders.groupby(["asset_name", "asset_type"], as_index=False).agg(
        order_count=("orden_trabajo_id", "nunique"),
        corrective_orders=("work_type", lambda values: int((pd.Series(values) == "CORRECTIVO").sum())),
        labor_hours=("labor_hours", "sum"),
        total_cost=("total_cost", "sum"),
    )

    downtime["period_id"] = pd.to_datetime(downtime["end_date"], errors="coerce").dt.strftime("%Y-%m")
    downtime = _apply_period_filter(downtime, "period_id", filters)
    downtime = downtime.merge(assets, on="activo_id", how="left")
    downtime_summary = downtime.groupby(["asset_name", "asset_type"], as_index=False).agg(
        downtime_hours=("downtime_hours", "sum"),
        stop_count=("parada_id", "count"),
    )

    summary = summary.merge(downtime_summary, on=["asset_name", "asset_type"], how="left")
    return summary.fillna(0.0).sort_values(["total_cost", "downtime_hours"], ascending=[False, False]).reset_index(drop=True)


def get_logistics_period(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    trips = _logistics_trip_base(bundle)
    trips = _apply_period_filter(trips, "period_id", filters)
    if trips.empty:
        return pd.DataFrame(
            columns=[
                "period_id",
                "trip_count",
                "tons_moved",
                "total_cost",
                "third_party_cost",
                "own_cost",
                "third_party_share",
                "avg_distance_km",
            ]
        )

    period = trips.groupby("period_id", as_index=False).agg(
        trip_count=("viaje_id", "nunique"),
        tons_moved=("tons_moved", "sum"),
        total_cost=("total_cost", "sum"),
        avg_distance_km=("distance_km", "mean"),
    )
    trips["third_party_cost"] = trips["total_cost"].where(trips["mode"] == "TERCERO", 0.0)
    trips["own_cost"] = trips["total_cost"].where(trips["mode"] == "PROPIO", 0.0)
    mode_cost = trips.groupby("period_id", as_index=False).agg(
        third_party_cost=("third_party_cost", "sum"),
        own_cost=("own_cost", "sum"),
    )
    period = period.merge(mode_cost, on="period_id", how="left").fillna(0.0)
    period["cost_per_ton"] = period["total_cost"] / period["tons_moved"].replace({0: pd.NA})
    period["third_party_share"] = period["third_party_cost"] / period["total_cost"].replace({0: pd.NA})
    return period.fillna(0.0).sort_values("period_id").reset_index(drop=True)


def build_logistics_mode_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    trips = _logistics_trip_base(bundle)
    trips = _apply_period_filter(trips, "period_id", filters)
    if trips.empty:
        return pd.DataFrame(columns=["mode", "trip_count", "tons_moved", "total_cost", "cost_per_ton"])

    summary = trips.groupby("mode", as_index=False).agg(
        trip_count=("viaje_id", "nunique"),
        tons_moved=("tons_moved", "sum"),
        total_cost=("total_cost", "sum"),
        avg_distance_km=("distance_km", "mean"),
    )
    summary["cost_per_ton"] = summary["total_cost"] / summary["tons_moved"].replace({0: pd.NA})
    return summary.fillna(0.0).sort_values("total_cost", ascending=False).reset_index(drop=True)


def build_transporter_summary(
    bundle: dict[str, pd.DataFrame],
    filters: dict[str, object],
) -> pd.DataFrame:
    trips = _logistics_trip_base(bundle)
    trips = _apply_period_filter(trips, "period_id", filters)
    if trips.empty:
        return pd.DataFrame(columns=["transporter_name", "mode", "trip_count", "tons_moved", "total_cost", "cost_per_ton"])

    summary = trips.groupby(["transporter_name", "mode"], as_index=False).agg(
        trip_count=("viaje_id", "nunique"),
        tons_moved=("tons_moved", "sum"),
        total_cost=("total_cost", "sum"),
        avg_distance_km=("distance_km", "mean"),
    )
    summary["cost_per_ton"] = summary["total_cost"] / summary["tons_moved"].replace({0: pd.NA})
    return summary.fillna(0.0).sort_values("total_cost", ascending=False).reset_index(drop=True)


def _logistics_trip_base(bundle: dict[str, pd.DataFrame]) -> pd.DataFrame:
    trips = bundle["log_viajes"].copy()
    details = bundle["log_viajes_det"].copy()
    transporters = bundle["log_transportistas"][["transportista_id", "transporter_name"]].copy()

    trip_detail = details.groupby("viaje_id", as_index=False).agg(
        tons_moved=("quantity", "sum"),
        cost_per_ton=("cost_per_ton", "mean"),
    )
    trips = trips.merge(trip_detail, on="viaje_id", how="left").merge(transporters, on="transportista_id", how="left")
    trips["period_id"] = pd.to_datetime(trips["dispatch_date"], errors="coerce").dt.strftime("%Y-%m")
    trips["transporter_name"] = trips["transporter_name"].fillna("Flota Propia")
    return trips.fillna({"tons_moved": 0.0, "cost_per_ton": 0.0})


def _novelty_metric(
    novelties: pd.DataFrame,
    novelty_type: str,
    source_column: str,
    metric_name: str,
) -> pd.DataFrame:
    filtered = novelties.loc[novelties["novelty_type"] == novelty_type]
    if filtered.empty:
        return pd.DataFrame(columns=["period_id", metric_name])
    return filtered.groupby("period_id", as_index=False).agg(**{metric_name: (source_column, "sum")})


def _apply_period_filter(
    dataframe: pd.DataFrame,
    period_column: str,
    filters: dict[str, object],
) -> pd.DataFrame:
    if dataframe.empty or period_column not in dataframe.columns:
        return dataframe

    start = filters.get("period_start")
    end = filters.get("period_end")
    result = dataframe.copy()
    result[period_column] = result[period_column].astype(str)
    if start:
        result = result[result[period_column] >= str(start)]
    if end:
        result = result[result[period_column] <= str(end)]
    return result


def _safe_divide(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator
