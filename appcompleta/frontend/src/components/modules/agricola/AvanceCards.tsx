import clsx from 'clsx'
import { Crop, MapPin, Tractor, BarChart3 } from 'lucide-react'
import { KPICard } from '@/components/ui/KPICard'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { formatHectareas, formatToneladas } from '@/lib/formatters'
import type { AgricolaSummary, AvanceCultivo } from '@/types/agricola'

interface AvanceCardsProps {
  summary?: AgricolaSummary
  avance?: AvanceCultivo[]
  loading?: boolean
}

function ProgressBar({ label, value, max, color = '#4ade80' }: {
  label: string
  value: number
  max: number
  color?: string
}) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium text-text">{label}</span>
        <div className="flex items-center gap-2">
          <span className="text-xs tabular-nums text-text-muted">
            {value.toLocaleString('es-AR', { maximumFractionDigits: 0 })} ha
          </span>
          <span className="text-xs font-semibold text-text" style={{ color }}>
            {pct.toFixed(0)}%
          </span>
        </div>
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-surface-2">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

const cultivoColors: Record<string, string> = {
  soja: '#4ade80',
  maiz: '#f59e0b',
  trigo: '#fbbf24',
  girasol: '#fb923c',
  sorgo: '#a78bfa',
  cebada: '#60a5fa',
}

export function AvanceCards({ summary, avance, loading }: AvanceCardsProps) {
  return (
    <div className="space-y-4">
      {/* Summary KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPICard
          title="Superficie Total"
          value={summary ? formatHectareas(summary.superficie_total) : '—'}
          icon={MapPin}
          loading={loading}
          trend="neutral"
        />
        <KPICard
          title="Sembrado"
          value={summary ? formatHectareas(summary.sembrado) : '—'}
          icon={Crop}
          loading={loading}
          trend="up"
          description={summary ? `${((summary.sembrado / summary.superficie_total) * 100).toFixed(0)}% del total` : undefined}
        />
        <KPICard
          title="Cosechado"
          value={summary ? formatHectareas(summary.cosechado) : '—'}
          icon={Tractor}
          loading={loading}
          trend="neutral"
        />
        <KPICard
          title="Rendimiento Promedio"
          value={summary ? `${summary.rendimiento_promedio.toFixed(2)}` : '—'}
          unit="tn/ha"
          icon={BarChart3}
          loading={loading}
          trend="up"
        />
      </div>

      {/* Progress bars */}
      <div className="rounded border border-border bg-surface p-5">
        <h3 className="mb-4 text-sm font-semibold text-text">Avance de Siembra por Cultivo</h3>
        {loading ? (
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-1.5">
                <SkeletonBlock className="h-3 w-24" />
                <SkeletonBlock className="h-1.5 w-full" />
              </div>
            ))}
          </div>
        ) : avance && avance.length > 0 ? (
          <div className="space-y-4">
            {avance.map((a) => (
              <ProgressBar
                key={a.cultivo}
                label={a.cultivo}
                value={a.sembrado_ha}
                max={a.total_ha}
                color={cultivoColors[a.cultivo.toLowerCase()] || '#6b8f7a'}
              />
            ))}
          </div>
        ) : (
          <p className="text-sm text-text-subtle">Sin datos de avance</p>
        )}
      </div>
    </div>
  )
}
