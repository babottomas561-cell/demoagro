import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import clsx from 'clsx'

interface KPICardProps {
  title: string
  value: string | number
  unit?: string
  delta?: number
  deltaLabel?: string
  icon?: LucideIcon
  iconColor?: 'green' | 'amber' | 'red' | 'blue'
  loading?: boolean
  description?: string
  // Extended props
  trend?: 'up' | 'down' | 'neutral'
  invertColor?: boolean
  className?: string
}

const iconBgs = {
  green: 'bg-primary-100 text-primary-600',
  amber: 'bg-amber-50 text-amber-600',
  red:   'bg-red-50 text-red-500',
  blue:  'bg-blue-50 text-blue-600',
}

function SkeletonKPI() {
  return (
    <div className="rounded-2xl border border-border bg-surface p-5">
      <div className="flex items-start justify-between mb-4">
        <div className="skeleton w-24 h-3 rounded" />
        <div className="skeleton w-9 h-9 rounded-lg" />
      </div>
      <div className="skeleton w-32 h-8 rounded mb-2" />
      <div className="skeleton w-20 h-3 rounded" />
    </div>
  )
}

export function KPICard({
  title, value, unit, delta, deltaLabel, icon: Icon,
  iconColor = 'green', loading, description, trend, invertColor, className,
}: KPICardProps) {
  if (loading) return <SkeletonKPI />
  const hasDelta = delta !== undefined && delta !== null
  // Use trend prop if provided, otherwise infer from delta
  const effectiveTrend = trend ?? (hasDelta ? (delta! > 0 ? 'up' : delta! < 0 ? 'down' : 'neutral') : 'neutral')
  const isUp   = invertColor ? effectiveTrend === 'down' : effectiveTrend === 'up'
  const isDown = invertColor ? effectiveTrend === 'up'   : effectiveTrend === 'down'
  const DeltaIcon = effectiveTrend === 'up' ? TrendingUp : effectiveTrend === 'down' ? TrendingDown : Minus

  return (
    <div className={clsx(
      'rounded-2xl border border-border bg-surface transition-colors duration-150 group',
      'p-4 sm:p-5',
      className
    )}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3 sm:mb-4">
        <p className="font-semibold uppercase text-text-subtle text-[10px] tracking-[0.16em] sm:text-[11px] sm:tracking-widest">
          {title}
        </p>
        {Icon && (
          <div className={clsx(
            'flex items-center justify-center rounded-lg shrink-0',
            'h-8 w-8 sm:h-9 sm:w-9',
            iconBgs[iconColor]
          )}>
            <Icon size={16} />
          </div>
        )}
      </div>

      {/* Value */}
      <div className="flex items-end gap-1.5 mb-1.5 sm:mb-2">
        <span className="font-bold text-text tabular-nums leading-none tracking-tight text-[1.8rem] sm:text-[2rem]">
          {typeof value === 'number' ? value.toLocaleString('es-AR') : value}
        </span>
        {unit && (
          <span className="font-medium text-text-muted mb-0.5 text-[12px] sm:text-sm">{unit}</span>
        )}
      </div>

      {/* Delta */}
      {hasDelta && (
        <div className={clsx(
          'font-medium',
          isUp ? 'text-primary-600' : isDown ? 'text-red-500' : 'text-text-muted'
        )}>
          <div className="flex items-center gap-1 text-[11px] sm:text-xs">
            <DeltaIcon size={12} />
            <span>{isUp ? '+' : ''}{delta?.toFixed(1)}%</span>
          </div>
          {deltaLabel && (
            <span className="font-normal text-text-subtle block sm:inline text-[11px] sm:text-xs mt-0.5 sm:mt-0 sm:ml-1">
              {deltaLabel}
            </span>
          )}
        </div>
      )}

      {/* Description */}
      {description && !hasDelta && (
        <p className="text-[11px] sm:text-xs text-text-muted">{description}</p>
      )}
    </div>
  )
}
