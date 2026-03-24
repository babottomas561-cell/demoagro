import clsx from 'clsx'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { formatCurrency, formatPercent } from '@/lib/formatters'

interface LotItem {
  lote: string
  establecimiento: string
  cultivo: string
  margen_ha: number
  margen_total?: number
  desvio_pct: number
}

interface LotProfitabilityHeatmapProps {
  items?: LotItem[]
  loading?: boolean
}

export function LotProfitabilityHeatmap({
  items,
  loading,
}: LotProfitabilityHeatmapProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {Array.from({ length: 6 }).map((_, index) => (
          <SkeletonBlock key={index} className="h-28 w-full" />
        ))}
      </div>
    )
  }

  if (!items?.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-text-muted">
        Sin datos de rentabilidad por lote.
      </div>
    )
  }

  const maxMargin = Math.max(...items.map((item) => Math.abs(item.margen_ha)), 1)

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => {
        const intensity = Math.min(Math.abs(item.margen_ha) / maxMargin, 1)
        const positive = item.margen_ha >= 0
        return (
          <div
            key={`${item.lote}-${item.cultivo}`}
            className={clsx('rounded-2xl border p-4', {
              'border-primary-200': positive,
              'border-red-200': !positive,
            })}
            style={{
              backgroundColor: positive
                ? `rgba(48, 148, 90, ${0.08 + intensity * 0.18})`
                : `rgba(239, 68, 68, ${0.08 + intensity * 0.18})`,
            }}
          >
            <p className="text-sm font-semibold text-text">{item.lote}</p>
            <p className="mt-1 text-xs text-text-muted">{item.establecimiento} · {item.cultivo}</p>
            <p className="mt-4 text-2xl font-bold tracking-tight text-text">
              {formatCurrency(item.margen_total ?? item.margen_ha)}
            </p>
            <div className="mt-3 flex items-center justify-between text-xs text-text-muted">
              <span>{formatCurrency(item.margen_ha)}/ha</span>
              <span>{formatPercent(item.desvio_pct)}</span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
