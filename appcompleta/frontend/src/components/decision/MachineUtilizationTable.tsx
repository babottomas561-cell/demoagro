import { Badge } from '@/components/ui/Badge'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { formatCurrency, formatNumber } from '@/lib/formatters'

interface MachineRow {
  nombre: string
  tipo: string
  establecimiento: string
  utilizacion_pct: number
  horas_improductivas: number
  costo_por_hora: number
  es_cuello_botella: boolean
}

interface MachineUtilizationTableProps {
  items?: MachineRow[]
  loading?: boolean
}

export function MachineUtilizationTable({
  items,
  loading,
}: MachineUtilizationTableProps) {
  if (loading) {
    return <SkeletonBlock className="h-80 w-full" />
  }

  const ranking = [...(items || [])].sort((a, b) => b.utilizacion_pct - a.utilizacion_pct)

  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-text">Utilización de flota</p>
        <Badge variant="neutral">{ranking.length}</Badge>
      </div>
      <div className="space-y-3">
        {ranking.slice(0, 8).map((item) => (
          <div key={item.nombre} className="rounded-xl border border-border bg-surface p-3">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-text">{item.nombre}</p>
                <p className="text-xs text-text-muted">{item.establecimiento} · {item.tipo}</p>
              </div>
              <Badge variant={item.es_cuello_botella ? 'danger' : 'success'}>
                {formatNumber(item.utilizacion_pct, 0)}%
              </Badge>
            </div>
            <div className="flex items-center justify-between gap-3 text-sm text-text-muted">
              <span>Downtime {formatNumber(item.horas_improductivas, 1)} hs</span>
              <span>{formatCurrency(item.costo_por_hora)}/h</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
