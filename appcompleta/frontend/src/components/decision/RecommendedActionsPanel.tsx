import clsx from 'clsx'
import { ArrowRight, Clock3 } from 'lucide-react'
import { Badge } from '@/components/ui/Badge'
import { SkeletonBlock } from '@/components/ui/Spinner'

interface RecommendedAction {
  titulo: string
  descripcion: string
  owner: string
  impacto: string
  due?: string
  severity: 'warning' | 'critical' | 'success'
}

interface RecommendedActionsPanelProps {
  actions?: RecommendedAction[]
  loading?: boolean
  emptyMessage?: string
}

export function RecommendedActionsPanel({
  actions,
  loading,
  emptyMessage = 'Sin acciones recomendadas por el momento.',
}: RecommendedActionsPanelProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="border-l border-border pl-4">
            <SkeletonBlock className="mb-2 h-3 w-2/3" />
            <SkeletonBlock className="mb-2 h-3 w-full" />
            <SkeletonBlock className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    )
  }

  if (!actions?.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-text-muted">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="space-y-0">
      {actions.map((action, index) => (
        <div
          key={`${action.titulo}-${index}`}
          className={clsx(
            'border-l-2 py-3 pl-4 pr-1',
            index !== actions.length - 1 && 'border-b border-border/70',
            {
              'border-l-[rgba(207,110,99,0.85)]': action.severity === 'critical',
              'border-l-[rgba(169,123,47,0.8)]': action.severity === 'warning',
              'border-l-primary-500': action.severity === 'success',
            }
          )}
        >
          <div className="mb-2 flex items-start justify-between gap-3">
            <p className="text-sm font-semibold text-text">{action.titulo}</p>
            <Badge variant={action.severity === 'critical' ? 'danger' : action.severity === 'success' ? 'success' : 'warning'}>
              {action.severity === 'critical' ? 'Ahora' : 'Próximo'}
            </Badge>
          </div>
          <p className="text-sm text-text-muted">{action.descripcion}</p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-subtle">
            <span className="inline-flex items-center gap-1">
              <ArrowRight className="h-3 w-3" />
              {action.owner}
            </span>
            <span>Impacto: {action.impacto}</span>
            {action.due && (
              <span className="inline-flex items-center gap-1">
                <Clock3 className="h-3 w-3" />
                {action.due}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}
