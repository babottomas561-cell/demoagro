import clsx from 'clsx'
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { SkeletonBlock } from '@/components/ui/Spinner'

type AlertSeverity = 'info' | 'warning' | 'critical' | 'success'

interface AlertItem {
  titulo: string
  descripcion: string
  severidad: AlertSeverity
  accion?: string
  prioridad?: string | number
}

interface AlertPriorityListProps {
  alerts?: AlertItem[]
  loading?: boolean
  emptyMessage?: string
}

const iconMap = {
  info: Info,
  warning: AlertTriangle,
  critical: AlertCircle,
  success: CheckCircle2,
}

const badgeMap = {
  info: 'info',
  warning: 'warning',
  critical: 'danger',
  success: 'success',
} as const

const containerMap = {
  info: 'border-[rgba(93,127,165,0.14)] bg-surface',
  warning: 'border-[rgba(169,123,47,0.14)] bg-surface',
  critical: 'border-[rgba(207,110,99,0.16)] bg-surface',
  success: 'border-primary-100 bg-surface',
}

export function AlertPriorityList({
  alerts,
  loading,
  emptyMessage = 'Sin alertas prioritarias.',
}: AlertPriorityListProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="border-l border-border pl-4">
            <SkeletonBlock className="mb-2 h-3 w-28" />
            <SkeletonBlock className="mb-2 h-3 w-full" />
            <SkeletonBlock className="h-3 w-3/4" />
          </div>
        ))}
      </div>
    )
  }

  if (!alerts?.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-text-muted">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {alerts.map((alert, index) => {
        const Icon = iconMap[alert.severidad]
        const priorityLabel =
          typeof alert.prioridad === 'number'
            ? `P${alert.prioridad}`
            : alert.prioridad
              ? String(alert.prioridad)
              : null
        return (
          <div
            key={`${alert.titulo}-${index}`}
            className={clsx(
              'border-l-2 py-3 pl-4 pr-1',
              index !== alerts.length - 1 && 'border-b border-border/70',
              {
                'border-l-[rgba(93,127,165,0.8)]': alert.severidad === 'info',
                'border-l-[rgba(169,123,47,0.8)]': alert.severidad === 'warning',
                'border-l-[rgba(207,110,99,0.85)]': alert.severidad === 'critical',
                'border-l-primary-500': alert.severidad === 'success',
              }
            )}
          >
            <div className="mb-1.5 flex items-start justify-between gap-3">
              <div className="flex items-start gap-2">
                <Icon className="mt-0.5 h-4 w-4 text-current opacity-70" />
                <div>
                  <p className="text-sm font-semibold text-text">{alert.titulo}</p>
                  <p className="mt-1 text-sm text-text-muted">{alert.descripcion}</p>
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-2">
                {priorityLabel ? (
                  <Badge variant="neutral">
                    {priorityLabel}
                  </Badge>
                ) : null}
                <Badge variant={badgeMap[alert.severidad]}>
                  {alert.severidad === 'critical' ? 'Crítica' : alert.severidad}
                </Badge>
              </div>
            </div>
            {alert.accion && (
              <p className="text-xs font-medium text-text">
                Acción: <span className="font-normal text-text-muted">{alert.accion}</span>
              </p>
            )}
          </div>
        )
      })}
    </div>
  )
}
