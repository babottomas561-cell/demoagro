import { Badge } from '@/components/ui/Badge'
import { formatCurrency, formatNumber, formatToneladas } from '@/lib/formatters'

interface PositionItem {
  cultivo: string
  toneladas_producidas: number
  toneladas_comprometidas: number
  toneladas_fijadas: number
  toneladas_entregadas: number
  abierta_tn: number
  cobertura_pct: number
  precio_referencia: number
  recomendacion: string
  severidad: 'success' | 'warning' | 'critical'
}

interface CommercialExposureCardProps {
  item: PositionItem
}

export function CommercialExposureCard({ item }: CommercialExposureCardProps) {
  const badgeVariant =
    item.severidad === 'critical' ? 'danger' : item.severidad === 'warning' ? 'warning' : 'success'

  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text">{item.cultivo}</p>
          <p className="text-xs text-text-muted">
            Cobertura {formatNumber(item.cobertura_pct, 0)}% · Ref. {formatCurrency(item.precio_referencia)}
          </p>
        </div>
        <Badge variant={badgeVariant}>
          {item.recomendacion}
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-text-subtle">Producidas</p>
          <p className="font-medium text-text">{formatToneladas(item.toneladas_producidas, 0)}</p>
        </div>
        <div>
          <p className="text-xs text-text-subtle">Comprometidas</p>
          <p className="font-medium text-text">{formatToneladas(item.toneladas_comprometidas, 0)}</p>
        </div>
        <div>
          <p className="text-xs text-text-subtle">Fijadas</p>
          <p className="font-medium text-text">{formatToneladas(item.toneladas_fijadas, 0)}</p>
        </div>
        <div>
          <p className="text-xs text-text-subtle">Abiertas</p>
          <p className="font-medium text-text">{formatToneladas(item.abierta_tn, 0)}</p>
        </div>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-surface-2">
        <div className="h-full rounded-full bg-primary-500" style={{ width: `${Math.max(item.cobertura_pct, 6)}%` }} />
      </div>
    </div>
  )
}
