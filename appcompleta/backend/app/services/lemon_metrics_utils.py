from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta


def safe_float(value: float | int | None) -> float:
    return float(value or 0)


def safe_pct(current: float, base: float) -> float:
    if not base:
        return 0.0
    return round(((current - base) / base) * 100, 2)


def ratio(value: float, base: float) -> float:
    if not base:
        return 0.0
    return value / base


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def daterange(start: date, end: date) -> Iterable[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def future_month_label(base_period: str, step: int) -> str:
    base_date = date.fromisoformat(f"{base_period}-01")
    return (base_date.replace(day=1) + timedelta(days=32 * step)).replace(day=1).strftime("%Y-%m")


def build_linear_projection_monthly(
    monthly_rows: list[dict],
    value_key: str,
    periods: int = 3,
) -> list[dict]:
    if not monthly_rows:
      return []
    observed = monthly_rows[-4:] if len(monthly_rows) >= 4 else monthly_rows
    projected = [{**row, "tipo": row.get("tipo", "historico")} for row in monthly_rows]
    if len(observed) < 2:
        return projected
    values = [safe_float(row[value_key]) for row in observed]
    slope = (values[-1] - values[0]) / max(len(values) - 1, 1)
    current_value = safe_float(monthly_rows[-1][value_key])
    current_period = str(monthly_rows[-1]["periodo"])
    for step in range(1, periods + 1):
        projected.append(
            {
                "periodo": future_month_label(current_period, step),
                value_key: round(current_value + slope * step, 2),
                "tipo": "proyeccion",
            }
        )
    return projected


def build_linear_projection_daily(
    daily_rows: list[dict],
    date_key: str,
    value_key: str,
    periods: int = 21,
) -> list[dict]:
    if not daily_rows:
        return []
    projected = [{**row, "tipo": row.get("tipo", "historico")} for row in daily_rows]
    observed = daily_rows[-14:] if len(daily_rows) >= 14 else daily_rows
    if len(observed) < 3:
        return projected
    values = [safe_float(row[value_key]) for row in observed]
    slope = (values[-1] - values[0]) / max(len(values) - 1, 1)
    current_date = date.fromisoformat(str(daily_rows[-1][date_key]))
    current_value = safe_float(daily_rows[-1][value_key])
    for step in range(1, periods + 1):
        projected.append(
            {
                date_key: (current_date + timedelta(days=step)).isoformat(),
                value_key: round(current_value + slope * step, 2),
                "tipo": "proyeccion",
            }
        )
    return projected


def build_linear_projection_weekly(
    weekly_rows: list[dict],
    date_key: str,
    value_key: str,
    periods: int = 6,
) -> list[dict]:
    if not weekly_rows:
        return []
    projected = [{**row, "tipo": row.get("tipo", "historico")} for row in weekly_rows]
    observed = weekly_rows[-10:] if len(weekly_rows) >= 10 else weekly_rows
    if len(observed) < 3:
        return projected
    values = [safe_float(row[value_key]) for row in observed]
    slope = (values[-1] - values[0]) / max(len(values) - 1, 1)
    current_date = date.fromisoformat(str(weekly_rows[-1][date_key]))
    current_value = safe_float(weekly_rows[-1][value_key])
    for step in range(1, periods + 1):
        projected.append(
            {
                date_key: (current_date + timedelta(days=7 * step)).isoformat(),
                value_key: round(current_value + slope * step, 2),
                "tipo": "proyeccion",
            }
        )
    return projected
