import clsx from 'clsx'
import { formatNumber } from '@/lib/formatters'

interface CoverageGaugeProps {
  value: number
  min?: number
  max?: number
  label: string
  unit?: string
  thresholds?: {
    warning: number
    critical: number
  }
}

export function CoverageGauge({
  value,
  min = 0,
  max = 60,
  label,
  unit = 'días',
  thresholds = { warning: 25, critical: 10 },
}: CoverageGaugeProps) {
  const normalized = Math.max(min, Math.min(value, max))
  const pct = ((normalized - min) / (max - min)) * 100
  const tone =
    value <= thresholds.critical ? 'danger' : value <= thresholds.warning ? 'warning' : 'success'

  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-2 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-text">{label}</p>
        <p className="text-sm font-semibold text-text">
          {formatNumber(value, 0)} {unit}
        </p>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
        <div
          className={clsx('h-full rounded-full', {
            'bg-primary-500': tone === 'success',
            'bg-[rgba(169,123,47,0.8)]': tone === 'warning',
            'bg-[rgba(207,110,99,0.8)]': tone === 'danger',
          })}
          style={{ width: `${Math.max(pct, 8)}%` }}
        />
      </div>
      <p className="mt-2 text-xs text-text-muted">
        {tone === 'danger'
          ? 'Cobertura crítica'
          : tone === 'warning'
          ? 'Cobertura ajustada'
          : 'Cobertura saludable'}
      </p>
    </div>
  )
}
