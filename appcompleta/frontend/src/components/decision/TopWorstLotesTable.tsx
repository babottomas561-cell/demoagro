import { Badge } from '@/components/ui/Badge'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { formatCurrency, formatPercent } from '@/lib/formatters'

interface LotRow {
  lote: string
  establecimiento: string
  cultivo: string
  margen_ha: number
  margen_total?: number
  desvio_pct: number
}

interface TopWorstLotesTableProps {
  topItems?: LotRow[]
  bottomItems?: LotRow[]
  loading?: boolean
}

function LotSection({
  title,
  items,
  tone,
}: {
  title: string
  items: LotRow[]
  tone: 'success' | 'danger'
}) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-text">{title}</p>
        <Badge variant={tone}>{items.length}</Badge>
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <div key={`${title}-${item.lote}-${item.cultivo}`} className="rounded-xl border border-border bg-surface-2 p-3">
            <div className="mb-2 flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-text">{item.lote}</p>
                <p className="text-xs text-text-muted">{item.establecimiento} · {item.cultivo}</p>
              </div>
              <Badge variant={item.desvio_pct < 0 ? 'danger' : 'success'}>
                {formatPercent(item.desvio_pct)}
              </Badge>
            </div>
            <div className="flex items-center justify-between gap-3 text-sm">
              <span className="text-text-muted">{formatCurrency(item.margen_ha)}/ha</span>
              <span className="font-semibold text-text">{formatCurrency(item.margen_total ?? item.margen_ha)}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function TopWorstLotesTable({
  topItems,
  bottomItems,
  loading,
}: TopWorstLotesTableProps) {
  if (loading) {
    return <SkeletonBlock className="h-80 w-full" />
  }

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <LotSection title="Top lotes" items={topItems || []} tone="success" />
      <LotSection title="Bottom lotes" items={bottomItems || []} tone="danger" />
    </div>
  )
}
