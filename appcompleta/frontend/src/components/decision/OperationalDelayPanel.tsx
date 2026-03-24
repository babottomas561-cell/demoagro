import { Badge } from '@/components/ui/Badge'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { formatHectareas } from '@/lib/formatters'

interface DelayLot {
  lote: string
  establecimiento: string
  labor: string
  pendiente_ha: number
  dias_atraso: number
}

interface DelayEst {
  establecimiento: string
  labor: string
  pendiente_ha: number
  pendiente_pct: number
}

interface OperationalDelayPanelProps {
  delayedLots?: DelayLot[]
  delayedByEst?: DelayEst[]
  loading?: boolean
}

export function OperationalDelayPanel({
  delayedLots,
  delayedByEst,
  loading,
}: OperationalDelayPanelProps) {
  if (loading) {
    return <SkeletonBlock className="h-80 w-full" />
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="rounded-2xl border border-border bg-surface p-4">
        <p className="mb-3 text-sm font-semibold text-text">Atraso por establecimiento</p>
        <div className="space-y-3">
          {(delayedByEst || []).slice(0, 5).map((item) => (
            <div key={`${item.establecimiento}-${item.labor}`} className="rounded-xl border border-border bg-surface-2 p-3">
              <div className="mb-2 flex items-center justify-between gap-3">
                <p className="text-sm font-semibold text-text">{item.establecimiento}</p>
                <Badge variant={item.pendiente_pct > 35 ? 'danger' : 'warning'}>
                  {item.pendiente_pct.toFixed(0)}%
                </Badge>
              </div>
              <p className="text-sm text-text-muted capitalize">
                {item.labor} · {formatHectareas(item.pendiente_ha)} pendientes
              </p>
            </div>
          ))}
        </div>
      </div>
      <div className="rounded-2xl border border-border bg-surface p-4">
        <p className="mb-3 text-sm font-semibold text-text">Lotes más atrasados</p>
        <div className="space-y-3">
          {(delayedLots || []).slice(0, 5).map((item) => (
            <div key={`${item.lote}-${item.labor}`} className="rounded-xl border border-border bg-surface-2 p-3">
              <div className="mb-2 flex items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-text">{item.lote}</p>
                  <p className="text-xs text-text-muted">{item.establecimiento} · {item.labor}</p>
                </div>
                <Badge variant={item.dias_atraso > 7 ? 'danger' : 'warning'}>
                  {item.dias_atraso} días
                </Badge>
              </div>
              <p className="text-sm text-text-muted">{formatHectareas(item.pendiente_ha)} pendientes</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
