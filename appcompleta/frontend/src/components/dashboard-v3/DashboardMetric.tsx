import clsx from 'clsx'
import type { ReactNode } from 'react'

function MiniSparkline({
  values,
  tone,
}: {
  values?: number[]
  tone: 'neutral' | 'positive' | 'warning' | 'critical'
}) {
  if (!values?.length) {
    return <div className="h-12 w-full rounded-2xl bg-surface-2" />
  }

  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1

  const points = values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * 100
      const y = 100 - ((value - min) / span) * 100
      return `${x},${y}`
    })
    .join(' ')

  const color =
    tone === 'critical'
      ? '#cf6e63'
      : tone === 'warning'
      ? '#a97b2f'
      : tone === 'positive'
      ? '#2f8a57'
      : '#8a8274'

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="h-12 w-full">
      <polyline
        fill="none"
        stroke={color}
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
    </svg>
  )
}

const toneClasses = {
  neutral: 'border-border/80 bg-white/82',
  positive: 'border-primary-200/70 bg-[#f4fbf7]',
  warning: 'border-[#d7bc82]/70 bg-[#fcf7ee]',
  critical: 'border-[#e2b5af]/70 bg-[#fdf4f3]',
}

export function DashboardMetric({
  label,
  value,
  subtitle,
  helper,
  detailLines,
  trendLabel,
  trendDirection = 'flat',
  sparkline,
  visual,
  tone = 'neutral',
  emphasis = 'secondary',
  loading = false,
}: {
  label: string
  value: string
  subtitle: string
  helper?: string
  detailLines?: string[]
  trendLabel?: string
  trendDirection?: 'up' | 'down' | 'flat'
  sparkline?: number[]
  visual?: ReactNode
  tone?: 'neutral' | 'positive' | 'warning' | 'critical'
  emphasis?: 'primary' | 'secondary'
  loading?: boolean
}) {
  const trendText =
    trendDirection === 'up' ? 'text-primary-700' : trendDirection === 'down' ? 'text-danger' : 'text-text-subtle'

  return (
    <article
      className={clsx(
        'flex h-full min-h-[210px] flex-col justify-between rounded-[2rem] border p-5 sm:p-6',
        toneClasses[tone],
        emphasis === 'primary' ? 'xl:min-h-[270px]' : 'xl:min-h-[230px]'
      )}
    >
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-subtle">{label}</p>
          <span
            className={clsx(
              'rounded-full px-2.5 py-1 text-[11px] font-medium',
              tone === 'critical'
                ? 'bg-danger/10 text-danger'
                : tone === 'warning'
                ? 'bg-[#d7bc82]/20 text-[#8b6222]'
                : tone === 'positive'
                ? 'bg-primary-100 text-primary-800'
                : 'bg-surface-2 text-text-subtle'
            )}
          >
            {trendDirection === 'up' ? 'al alza' : trendDirection === 'down' ? 'bajo presión' : 'estable'}
          </span>
        </div>

        <div>
          {loading ? (
            <div className="h-12 w-2/3 rounded-2xl bg-surface-2" />
          ) : (
            <h2
              className={clsx(
                'font-semibold tracking-[-0.04em] text-text',
                emphasis === 'primary' ? 'text-[2.6rem] leading-none sm:text-[3rem]' : 'text-[2rem] leading-none'
              )}
            >
              {value}
            </h2>
          )}
          <p className="mt-2 text-sm font-medium text-text">{subtitle}</p>
          {helper ? <p className="mt-1 text-sm text-text-muted">{helper}</p> : null}
        </div>

        {detailLines?.length ? (
          <div className="space-y-2 pt-1">
            {detailLines.slice(0, 3).map((line) => (
              <p key={line} className="text-sm text-text-muted">
                {'\u2192'} {line}
              </p>
            ))}
          </div>
        ) : null}
      </div>

      <div className="space-y-2">
        {visual}
        <MiniSparkline values={sparkline} tone={tone} />
        {trendLabel ? <p className={clsx('text-xs font-medium', trendText)}>{trendLabel}</p> : null}
      </div>
    </article>
  )
}
