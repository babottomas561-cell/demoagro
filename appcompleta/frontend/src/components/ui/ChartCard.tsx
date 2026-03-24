'use client'

import type { ReactNode } from 'react'
import clsx from 'clsx'

interface ChartCardProps {
  /** Card heading shown above the chart */
  title: string
  /** Optional secondary line under the title */
  description?: string
  /** Small pill badge shown beside the title (e.g. "YTD", "BCRA") */
  badge?: string
  /** Content area — typically a chart component */
  children: ReactNode
  /** Extra slot rendered to the right of the title row (filters, toggles, etc.) */
  toolbar?: ReactNode
  /** When true, renders a skeleton placeholder instead of children */
  loading?: boolean
  /** Skeleton height in px when loading (default 260) */
  skeletonHeight?: number
  className?: string
  bodyClassName?: string
}

/**
 * ChartCard
 *
 * Uniform card shell for every Plotly chart in the app.
 * Handles title, description, badge, optional toolbar slot, and loading state.
 *
 * Usage:
 *   <ChartCard title="Ingresos vs. Egresos" badge="12 meses" loading={isLoading}>
 *     <BarChart data={...} />
 *   </ChartCard>
 */
export function ChartCard({
  title,
  description,
  badge,
  children,
  toolbar,
  loading,
  skeletonHeight = 260,
  className,
  bodyClassName,
}: ChartCardProps) {
  return (
    <div
      className={clsx(
        'rounded-[1.5rem] border border-border/70 bg-white/80 px-4 py-4 sm:px-5 sm:py-5',
        className
      )}
    >
      {/* Header row */}
      <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold tracking-[-0.02em] text-text">{title}</h3>
            {badge ? (
              <span className="rounded-full border border-border/60 bg-surface-2 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-text-subtle">
                {badge}
              </span>
            ) : null}
          </div>
          {description ? (
            <p className="mt-0.5 text-xs text-text-muted">{description}</p>
          ) : null}
        </div>
        {toolbar ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{toolbar}</div>
        ) : null}
      </div>

      {/* Body */}
      <div className={clsx('overflow-hidden', bodyClassName)}>
        {loading ? (
          <div
            className="animate-pulse rounded-xl bg-surface-2 w-full"
            style={{ height: skeletonHeight }}
          />
        ) : (
          children
        )}
      </div>
    </div>
  )
}
