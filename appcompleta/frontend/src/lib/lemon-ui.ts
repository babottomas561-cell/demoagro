import { formatNumber } from '@/lib/formatters'

export function formatPercentValue(value: number, decimals = 1) {
  return `${formatNumber(value, decimals)}%`
}

export type AlertLike = {
  severidad?: string | null
  prioridad?: string | number | null
}

export function mapSeverity(value: string) {
  if (value === 'critical') return 'critical' as const
  if (value === 'warning') return 'warning' as const
  if (value === 'success') return 'success' as const
  return 'info' as const
}

const SEVERITY_WEIGHT: Record<string, number> = {
  critical: 0,
  warning: 1,
  info: 2,
  success: 3,
}

const PRIORITY_WEIGHT: Record<string, number> = {
  alta: 0,
  media: 1,
  baja: 2,
}

function normalizePriority(value: AlertLike['prioridad']) {
  if (typeof value === 'number') return value
  if (!value) return 99
  return PRIORITY_WEIGHT[String(value).trim().toLowerCase()] ?? 99
}

function normalizeSeverity(value: AlertLike['severidad']) {
  if (!value) return 99
  return SEVERITY_WEIGHT[String(value).trim().toLowerCase()] ?? 99
}

export function sortExecutiveAlerts<T extends AlertLike>(alerts: T[]) {
  return [...alerts].sort((a, b) => {
    const severityDiff = normalizeSeverity(a.severidad) - normalizeSeverity(b.severidad)
    if (severityDiff !== 0) return severityDiff

    const priorityDiff = normalizePriority(a.prioridad) - normalizePriority(b.prioridad)
    if (priorityDiff !== 0) return priorityDiff

    return 0
  })
}
