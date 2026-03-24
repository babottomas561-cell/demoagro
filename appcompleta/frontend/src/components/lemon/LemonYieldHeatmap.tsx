import clsx from 'clsx'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { formatNumber, formatPercent } from '@/lib/formatters'

interface YieldHeatItem {
  lote: string
  establecimiento: string
  variedad: string
  kg_ha_proyectado: number
  objetivo_kg_ha: number
  desvio_pct: number
}

interface LemonYieldHeatmapProps {
  items?: YieldHeatItem[]
  loading?: boolean
}

export function LemonYieldHeatmap({
  items,
  loading,
}: LemonYieldHeatmapProps) {
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
        Sin datos suficientes para el mapa de rendimiento.
      </div>
    )
  }

  const maxDeviation = Math.max(...items.map((item) => Math.abs(item.desvio_pct)), 1)

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {items.map((item) => {
        const intensity = Math.min(Math.abs(item.desvio_pct) / maxDeviation, 1)
        const positive = item.desvio_pct >= -5
        return (
          <article
            key={`${item.lote}-${item.variedad}`}
            className={clsx('rounded-[1.3rem] border p-4', {
              'border-primary-200': positive,
              'border-[#e2b5af]/80': !positive,
            })}
            style={{
              backgroundColor: positive
                ? `rgba(48,148,90,${0.07 + intensity * 0.18})`
                : `rgba(207,110,99,${0.07 + intensity * 0.18})`,
            }}
          >
            <p className="text-sm font-semibold text-text">{item.lote}</p>
            <p className="mt-1 text-xs text-text-muted">
              {item.establecimiento} · {item.variedad}
            </p>
            <p className="mt-4 text-2xl font-semibold tracking-tight text-text">
              {formatNumber(item.kg_ha_proyectado, 0)} kg/ha
            </p>
            <div className="mt-3 flex items-center justify-between text-xs text-text-muted">
              <span>Objetivo {formatNumber(item.objetivo_kg_ha, 0)}</span>
              <span>{formatPercent(item.desvio_pct)}</span>
            </div>
          </article>
        )
      })}
    </div>
  )
}
