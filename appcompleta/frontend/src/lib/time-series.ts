export type TimeRange = '7D' | '30D' | '90D' | 'YTD' | '12M' | 'ALL'

export const TIME_RANGE_OPTIONS: { value: TimeRange; label: string }[] = [
  { value: '7D', label: '7D' },
  { value: '30D', label: '30D' },
  { value: '90D', label: '90D' },
  { value: 'YTD', label: 'YTD' },
  { value: '12M', label: '12M' },
  { value: 'ALL', label: 'Todo' },
]

function parseTemporalValue(value: unknown): Date | null {
  if (value == null) return null
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value

  const raw = String(value).trim()
  if (!raw) return null

  if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
    const parsed = new Date(raw)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }

  if (/^\d{4}-\d{2}$/.test(raw)) {
    const parsed = new Date(`${raw}-01T00:00:00`)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }

  if (/^\d{4}\/\d{2}$/.test(raw)) {
    const year = Number(raw.slice(0, 4))
    const parsed = new Date(year, 0, 1)
    return Number.isNaN(parsed.getTime()) ? null : parsed
  }

  const parsed = new Date(raw)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function cutoffFromRange(maxDate: Date, range: TimeRange): Date | null {
  const cutoff = new Date(maxDate)

  switch (range) {
    case '7D':
      cutoff.setDate(cutoff.getDate() - 6)
      return cutoff
    case '30D':
      cutoff.setDate(cutoff.getDate() - 29)
      return cutoff
    case '90D':
      cutoff.setDate(cutoff.getDate() - 89)
      return cutoff
    case 'YTD':
      return new Date(maxDate.getFullYear(), 0, 1)
    case '12M':
      cutoff.setMonth(cutoff.getMonth() - 11)
      return cutoff
    case 'ALL':
    default:
      return null
  }
}

const FALLBACK_POINTS: Record<TimeRange, number> = {
  '7D': 7,
  '30D': 6,
  '90D': 9,
  YTD: 12,
  '12M': 12,
  ALL: Number.POSITIVE_INFINITY,
}

export function filterSeriesByRange<T>(
  rows: T[],
  range: TimeRange,
  getTemporalValue: (row: T) => unknown
): T[] {
  if (!rows.length || range === 'ALL') {
    return rows
  }

  const datedRows = rows
    .map((row) => ({ row, date: parseTemporalValue(getTemporalValue(row)) }))
    .filter((entry) => entry.date)

  if (datedRows.length === rows.length && datedRows.length > 0) {
    const maxDate = datedRows.reduce((latest, entry) => {
      if (!latest) return entry.date
      return entry.date! > latest ? entry.date! : latest
    }, datedRows[0].date)

    const cutoff = cutoffFromRange(maxDate!, range)
    if (!cutoff) return rows

    return datedRows
      .filter((entry) => entry.date! >= cutoff)
      .map((entry) => entry.row)
  }

  const keep = FALLBACK_POINTS[range]
  if (!Number.isFinite(keep) || keep >= rows.length) {
    return rows
  }

  return rows.slice(-keep)
}

export function ensureMinimumSeriesPoints<T>(
  filteredRows: T[],
  allRows: T[],
  minPoints = 4
): T[] {
  if (filteredRows.length >= minPoints || allRows.length <= filteredRows.length) {
    return filteredRows
  }
  return allRows.slice(-Math.min(minPoints, allRows.length))
}
