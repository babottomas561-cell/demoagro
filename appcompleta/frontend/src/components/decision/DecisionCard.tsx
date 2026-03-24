import clsx from 'clsx'
import { ArrowDownRight, ArrowUpRight, LucideIcon, Minus } from 'lucide-react'
import { SkeletonBlock } from '@/components/ui/Spinner'

interface DecisionCardProps {
  title: string
  value: string
  subtitle?: string
  helper?: string
  tone?: 'neutral' | 'success' | 'warning' | 'danger'
  icon?: LucideIcon
  loading?: boolean
  className?: string
  size?: 'hero' | 'default' | 'compact'
  details?: string[]
  trendLabel?: string
  trendDirection?: 'up' | 'down' | 'flat'
  sparkline?: number[]
  progress?: {
    value: number
    max: number
    label?: string
  }
}

const toneStyles = {
  neutral: 'border-border bg-surface',
  success: 'border-primary-100 bg-surface',
  warning: 'border-[rgba(169,123,47,0.14)] bg-surface',
  danger: 'border-[rgba(207,110,99,0.16)] bg-surface',
}

export function DecisionCard({
  title,
  value,
  subtitle,
  helper,
  tone = 'neutral',
  icon: Icon,
  loading,
  className,
  size = 'default',
  details,
  trendLabel,
  trendDirection,
  sparkline,
  progress,
}: DecisionCardProps) {
  if (loading) {
    return (
      <div className="rounded-2xl border border-border bg-surface p-5 shadow-card">
        <SkeletonBlock className="mb-3 h-3 w-24" />
        <SkeletonBlock className="mb-2 h-8 w-32" />
        <SkeletonBlock className="mb-3 h-3 w-28" />
        <SkeletonBlock className="h-10 w-full" />
      </div>
    )
  }

  const trendIcon =
    trendDirection === 'up' ? ArrowUpRight : trendDirection === 'down' ? ArrowDownRight : Minus
  const trendStyles =
    trendDirection === 'up'
      ? 'bg-primary-100 text-primary-800'
      : trendDirection === 'down'
      ? 'bg-red-100 text-red-700'
      : 'bg-stone-100 text-text-muted'
  const TrendIcon = trendIcon
  const sparklinePoints = sparkline?.filter((point) => Number.isFinite(point)) || []
  const sparkMin = sparklinePoints.length ? Math.min(...sparklinePoints) : 0
  const sparkMax = sparklinePoints.length ? Math.max(...sparklinePoints) : 0
  const sparkRange = sparkMax - sparkMin || 1
  const sparklinePath =
    sparklinePoints.length > 1
      ? sparklinePoints
          .slice(-12)
          .map((point, index, array) => {
            const x = array.length === 1 ? 0 : (index / (array.length - 1)) * 100
            const y = 100 - ((point - sparkMin) / sparkRange) * 100
            return `${index === 0 ? 'M' : 'L'} ${x} ${Number.isFinite(y) ? y : 50}`
          })
          .join(' ')
      : ''
  const progressPct = progress ? Math.max(0, Math.min((progress.value / Math.max(progress.max, 1)) * 100, 100)) : 0
  const accentColor =
    tone === 'danger'
      ? '#cf6e63'
      : tone === 'warning'
      ? '#a97b2f'
      : '#30945a'

  return (
    <div
      className={clsx(
        'flex h-full flex-col rounded-[18px] border p-5',
        {
          'min-h-[14.5rem] xl:min-h-[16.5rem]': size === 'hero',
          'min-h-[11.5rem] xl:min-h-[13.5rem]': size === 'default',
          'min-h-[9.5rem] xl:min-h-[10.5rem]': size === 'compact',
        },
        toneStyles[tone],
        className
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
            {title}
          </p>
          {subtitle && <p className="mt-1 text-[12px] font-medium leading-5 text-text-muted">{subtitle}</p>}
        </div>
        {Icon && (
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border bg-surface-2 text-text-muted">
            <Icon size={15} />
          </div>
        )}
      </div>
      <div className="mt-auto">
        <p
          className={clsx('font-semibold tracking-tight text-text', {
            'text-[2.5rem]': size === 'hero',
            'text-[2rem]': size === 'default',
            'text-[1.75rem]': size === 'compact',
          })}
        >
          {value}
        </p>
        {(trendLabel || progress || sparklinePoints.length > 1) && (
          <div className="mt-3 space-y-2.5">
            {(trendLabel || progress) && (
              <div className="flex flex-wrap items-center justify-between gap-2">
                {trendLabel ? (
                  <span className={clsx('inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium', trendStyles)}>
                    <TrendIcon size={12} />
                    {trendLabel}
                  </span>
                ) : (
                  <span />
                )}
                {progress && (
                  <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-text-subtle">
                    {progress.label || `${Math.round(progressPct)}%`}
                  </span>
                )}
              </div>
            )}
            {sparklinePoints.length > 1 && (
              <div className="rounded-2xl border border-border/70 bg-surface-2/80 px-2 py-2">
                <svg viewBox="0 0 100 24" preserveAspectRatio="none" className="h-7 w-full">
                  <path
                    d={sparklinePath}
                    fill="none"
                    stroke={accentColor}
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
            )}
            {progress && (
              <div className="space-y-1">
                <div className="h-1 overflow-hidden rounded-full bg-surface-3">
                  <div
                    className={clsx('h-full rounded-full', {
                      'bg-primary-500': tone === 'neutral' || tone === 'success',
                      'bg-[rgba(169,123,47,0.8)]': tone === 'warning',
                      'bg-[rgba(207,110,99,0.8)]': tone === 'danger',
                    })}
                    style={{ width: `${progressPct}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        )}
        {!!details?.length && (
          <div className="mt-4 space-y-2 border-t border-border/70 pt-3">
            {details.slice(0, size === 'hero' ? 3 : 2).map((detail, index) => (
              <p key={`${title}-detail-${index}`} className="text-[12px] leading-5 text-text-muted">
                {detail}
              </p>
            ))}
          </div>
        )}
        {helper && <p className="mt-3 text-[12px] leading-5 text-text-muted">{helper}</p>}
      </div>
    </div>
  )
}
