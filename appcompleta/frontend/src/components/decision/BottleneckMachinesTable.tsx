import { Badge } from '@/components/ui/Badge'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { formatCurrency, formatNumber } from '@/lib/formatters'

interface BottleneckMachine {
  maquina: string
  tipo: string
  establecimiento: string
  utilizacion_pct: number
  downtime_horas: number
  combustible_ha: number
  costo_por_hora: number
  impacto_operativo_ha: number
  riesgo_si_falla: string
  severity: 'warning' | 'critical'
}

interface BottleneckMachinesTableProps {
  items?: BottleneckMachine[]
  loading?: boolean
}

export function BottleneckMachinesTable({
  items,
  loading,
}: BottleneckMachinesTableProps) {
  if (loading) {
    return <SkeletonBlock className="h-72 w-full" />
  }

  if (!items?.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-text-muted">
        No se detectaron cuellos de botella operativos.
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="hidden overflow-hidden rounded-2xl border border-border md:block">
        <table className="min-w-full divide-y divide-border text-sm">
          <thead className="bg-surface-2 text-left text-xs uppercase tracking-[0.16em] text-text-subtle">
            <tr>
              <th className="px-4 py-3">Equipo</th>
              <th className="px-4 py-3">Uso</th>
              <th className="px-4 py-3">Downtime</th>
              <th className="px-4 py-3">Costo/h</th>
              <th className="px-4 py-3">Impacto</th>
              <th className="px-4 py-3">Riesgo</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border bg-surface">
            {items.map((item) => (
              <tr key={item.maquina}>
                <td className="px-4 py-3">
                  <p className="font-semibold text-text">{item.maquina}</p>
                  <p className="text-xs text-text-muted">{item.establecimiento} · {item.tipo}</p>
                </td>
                <td className="px-4 py-3">{formatNumber(item.utilizacion_pct, 1)}%</td>
                <td className="px-4 py-3">{formatNumber(item.downtime_horas, 1)} hs</td>
                <td className="px-4 py-3">{formatCurrency(item.costo_por_hora)}</td>
                <td className="px-4 py-3">{formatNumber(item.impacto_operativo_ha, 0)} ha</td>
                <td className="px-4 py-3">
                  <Badge variant={item.severity === 'critical' ? 'danger' : 'warning'}>
                    {item.severity === 'critical' ? 'Crítico' : 'Atención'}
                  </Badge>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="space-y-3 md:hidden">
        {items.map((item) => (
          <div key={item.maquina} className="rounded-2xl border border-border bg-surface p-4">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-text">{item.maquina}</p>
                <p className="text-xs text-text-muted">{item.establecimiento} · {item.tipo}</p>
              </div>
              <Badge variant={item.severity === 'critical' ? 'danger' : 'warning'}>
                {item.severity === 'critical' ? 'Crítico' : 'Atención'}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-xs text-text-subtle">Utilización</p>
                <p className="font-medium text-text">{formatNumber(item.utilizacion_pct, 1)}%</p>
              </div>
              <div>
                <p className="text-xs text-text-subtle">Downtime</p>
                <p className="font-medium text-text">{formatNumber(item.downtime_horas, 1)} hs</p>
              </div>
              <div>
                <p className="text-xs text-text-subtle">Costo/h</p>
                <p className="font-medium text-text">{formatCurrency(item.costo_por_hora)}</p>
              </div>
              <div>
                <p className="text-xs text-text-subtle">Impacto</p>
                <p className="font-medium text-text">{formatNumber(item.impacto_operativo_ha, 0)} ha</p>
              </div>
            </div>
            <p className="mt-3 text-xs text-text-muted">{item.riesgo_si_falla}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
