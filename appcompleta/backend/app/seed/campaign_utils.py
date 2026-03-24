from datetime import date


def current_campaign_start_year(reference_date: date | None = None) -> int:
    current = reference_date or date.today()
    return current.year if current.month >= 7 else current.year - 1


def campaign_name(start_year: int) -> str:
    return f"{start_year}/{start_year + 1}"


def shift_date_years(value: date | None, years: int) -> date | None:
    if value is None:
        return None
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        # Handles leap-day edge cases without introducing month drift.
        return value.replace(month=2, day=28, year=value.year + years)


def build_campaign_template_map(reference_date: date | None = None) -> tuple[dict[str, str], int]:
    current_start = current_campaign_start_year(reference_date)
    template_map = {
        "2022/2023": campaign_name(current_start - 2),
        "2023/2024": campaign_name(current_start - 1),
        "2024/2025": campaign_name(current_start),
        "2025/2026": campaign_name(current_start + 1),
    }
    year_delta = current_start - 2024
    return template_map, year_delta
