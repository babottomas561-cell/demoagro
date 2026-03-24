import type { QueryFilters } from '@/hooks/usePageFilters'
import type { TimeRange } from '@/lib/time-series'

const VALID_RANGES: readonly TimeRange[] = ['7D', '30D', '90D', 'YTD', '12M', 'ALL']

function normalizeRange(value: string | undefined, fallback: TimeRange): TimeRange {
  const normalized = (value || '').toUpperCase() as TimeRange
  return VALID_RANGES.includes(normalized) ? normalized : fallback
}

function pad(value: number) {
  return String(value).padStart(2, '0')
}

function formatLocalDate(value: Date) {
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`
}

function subtractMonths(base: Date, months: number) {
  const copy = new Date(base)
  copy.setMonth(copy.getMonth() - months)
  return copy
}

export function resolveTimeQuery(filters: QueryFilters, fallbackRange: TimeRange = '90D') {
  const today = new Date()
  const periodo = normalizeRange(filters.periodo, fallbackRange)
  const toDate = filters.to_date || formatLocalDate(today)

  if (filters.from_date) {
    return {
      periodo,
      from_date: filters.from_date,
      to_date: toDate,
    }
  }

  const to = new Date(`${toDate}T00:00:00`)
  const from = new Date(to)

  switch (periodo) {
    case '7D':
      from.setDate(from.getDate() - 6)
      break
    case '30D':
      from.setDate(from.getDate() - 29)
      break
    case '90D':
      from.setDate(from.getDate() - 89)
      break
    case 'YTD':
      from.setMonth(0, 1)
      break
    case '12M':
      return {
        periodo,
        from_date: formatLocalDate(subtractMonths(to, 11)),
        to_date: toDate,
      }
    case 'ALL':
    default:
      return {
        periodo,
        from_date: '1900-01-01',
        to_date: toDate,
      }
  }

  return {
    periodo,
    from_date: formatLocalDate(from),
    to_date: toDate,
  }
}

export function buildFilterQueryString(filters: QueryFilters, fallbackRange: TimeRange = '90D') {
  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(filters)) {
    if (!value || key === 'from_date' || key === 'to_date' || key === 'periodo') {
      continue
    }
    params.set(key, value)
  }

  const timeQuery = resolveTimeQuery(filters, fallbackRange)
  params.set('periodo', timeQuery.periodo)
  params.set('from_date', timeQuery.from_date)
  params.set('to_date', timeQuery.to_date)

  return params.toString()
}
