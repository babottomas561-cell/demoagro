from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

import numpy as np
import pandas as pd


def make_ids(prefix: str, count: int, start: int = 1) -> list[str]:
    return [f"{prefix}_{index:04d}" for index in range(start, start + count)]


def month_starts(start_date: date, end_date: date) -> list[date]:
    cursor = date(start_date.year, start_date.month, 1)
    months: list[date] = []
    while cursor <= end_date:
        months.append(cursor)
        if cursor.month == 12:
            cursor = date(cursor.year + 1, 1, 1)
        else:
            cursor = date(cursor.year, cursor.month + 1, 1)
    return months


def end_of_month(value: date) -> date:
    if value.month == 12:
        return date(value.year, 12, 31)
    return date(value.year, value.month + 1, 1) - timedelta(days=1)


def campaign_date(campaign_start_year: int, month: int, rng: np.random.Generator, day_low: int = 3, day_high: int = 24) -> date:
    year = campaign_start_year if month >= 7 else campaign_start_year + 1
    day = int(rng.integers(day_low, day_high + 1))
    return date(year, month, min(day, end_of_month(date(year, month, 1)).day))


def weighted_choice(values: Iterable[str], weights: Iterable[float], rng: np.random.Generator) -> str:
    population = list(values)
    probabilities = np.array(list(weights), dtype=float)
    probabilities = probabilities / probabilities.sum()
    return str(rng.choice(population, p=probabilities))


def frame(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def add_days(value: date, days: int) -> date:
    return value + timedelta(days=days)
