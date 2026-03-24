import clsx from 'clsx'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { formatCurrency } from '@/lib/formatters'

interface MarginWaterfallItem {
  label: string
  value: number
  kind: 'positive' | 'negative' | 'total'
}

interface MarginWaterfallProps {
  items?: MarginWaterfallItem[]
  loading?: boolean
}

export function MarginWaterfall({ items, loading }: MarginWaterfallProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 4 }).map((_, index) => (
          <SkeletonBlock key={index} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (!items?.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-text-muted">
        Sin datos para explicar el resultado.
      </div>
    )
  }

  const maxAbs = Math.max(...items.map((item) => Math.abs(item.value)), 1)

  return (
    <div className="space-y-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-2xl border border-border bg-surface p-4">
          <div className="mb-2 flex items-center justify-between gap-4">
            <p className="text-sm font-semibold text-text">{item.label}</p>
            <p
              className={clsx('text-sm font-semibold tabular-nums', {
                'text-primary-700': item.kind === 'positive',
                'text-danger': item.kind === 'negative',
                'text-text': item.kind === 'total',
              })}
            >
              {formatCurrency(item.value)}
            </p>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface-2">
            <div
              className={clsx('h-full rounded-full', {
                'bg-primary-500': item.kind === 'positive',
                'bg-red-400': item.kind === 'negative',
                'bg-text': item.kind === 'total',
              })}
              style={{ width: `${Math.max((Math.abs(item.value) / maxAbs) * 100, 12)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  )
}
