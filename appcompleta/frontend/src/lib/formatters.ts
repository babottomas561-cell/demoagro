import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { es } from 'date-fns/locale'

export const formatCurrency = (value: number, currency = 'ARS'): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'

  const absValue = Math.abs(value)
  let formatted: string
  let suffix = ''

  if (currency === 'ARS') {
    if (absValue >= 1_000_000_000) {
      formatted = (absValue / 1_000_000_000).toFixed(1)
      suffix = 'B'
    } else if (absValue >= 1_000_000) {
      formatted = (absValue / 1_000_000).toFixed(1)
      suffix = 'M'
    } else if (absValue >= 1_000) {
      formatted = (absValue / 1_000).toFixed(0)
      suffix = 'K'
    } else {
      formatted = absValue.toFixed(0)
    }
    return `${value < 0 ? '-' : ''}$${formatted}${suffix}`
  }

  if (absValue >= 1_000_000) {
    formatted = (absValue / 1_000_000).toFixed(2)
    suffix = 'M'
  } else if (absValue >= 1_000) {
    formatted = (absValue / 1_000).toFixed(1)
    suffix = 'K'
  } else {
    formatted = absValue.toFixed(2)
  }
  return `${value < 0 ? '-' : ''}USD ${formatted}${suffix}`
}

export const formatNumber = (value: number, decimals = 2): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'
  return new Intl.NumberFormat('es-AR', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value)
}

export const formatPercent = (value: number, decimals = 1): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'
  const sign = value > 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

export const formatDate = (date: string): string => {
  if (!date) return '-'
  try {
    return format(parseISO(date), "dd/MM/yyyy", { locale: es })
  } catch {
    return date
  }
}

export const formatDateTime = (date: string): string => {
  if (!date) return '-'
  try {
    return format(parseISO(date), "dd/MM/yyyy HH:mm", { locale: es })
  } catch {
    return date
  }
}

export const formatRelativeTime = (date: string): string => {
  if (!date) return '-'
  try {
    return formatDistanceToNow(parseISO(date), { addSuffix: true, locale: es })
  } catch {
    return date
  }
}

export const formatToneladas = (value: number, decimals = 1): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(decimals)}k tn`
  }
  return `${value.toFixed(decimals)} tn`
}

export const formatHectareas = (value: number): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'
  return `${formatNumber(value, 0)} ha`
}

export const formatKPI = (value: number, unit?: string): string => {
  if (value === null || value === undefined || isNaN(value)) return '-'
  const formatted = formatNumber(value, 0)
  return unit ? `${formatted} ${unit}` : formatted
}
