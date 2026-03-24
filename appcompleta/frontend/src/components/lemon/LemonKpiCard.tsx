import { Badge } from '@/components/ui/Badge'
import { ManagerExplanation, type ManagerExplanationMode } from '@/components/explanations/ManagerExplanation'

type LemonKpiStatus = 'success' | 'warning' | 'danger' | 'info' | 'neutral'

interface LemonKpiCardProps {
  label: string
  value: string
  delta?: string
  detail: string
  status?: LemonKpiStatus
  notes?: string[]
  mode?: ManagerExplanationMode
}

const badgeVariant: Record<LemonKpiStatus, 'success' | 'warning' | 'danger' | 'info' | 'neutral'> = {
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  info: 'info',
  neutral: 'neutral',
}

const statusLabel: Record<LemonKpiStatus, string> = {
  success: 'Estable',
  warning: 'Atención',
  danger: 'Crítico',
  info: 'Seguimiento',
  neutral: 'Referencia',
}

export function LemonKpiCard({
  label,
  value,
  delta,
  detail,
  status = 'neutral',
  notes,
  mode = 'metric',
}: LemonKpiCardProps) {
  return (
    <article className="flex h-full min-h-[15rem] flex-col rounded-[1.5rem] border border-border/60 bg-white/[0.84] p-4 text-left">
      <div className="flex items-start justify-between gap-3">
        <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
          {label}
        </p>
        <Badge variant={badgeVariant[status]} dot>
          {statusLabel[status]}
        </Badge>
      </div>
      <div className="mt-3 flex items-end gap-2">
        <p className="text-[1.9rem] font-semibold leading-none tracking-[-0.05em] text-text">
          {value}
        </p>
        {delta ? (
          <span
            className={`max-w-[11rem] pb-1 text-xs font-medium leading-4 ${
              status === 'danger'
                ? 'text-danger'
                : status === 'warning'
                ? 'text-warning'
                : status === 'success'
                ? 'text-primary-700'
                : 'text-text-subtle'
            }`}
          >
            {delta}
          </span>
        ) : null}
      </div>
      <p className="mt-2 min-h-[2.5rem] text-xs leading-5 text-text-muted">{detail}</p>
      <ManagerExplanation subject={label} mode={mode} items={notes} compact className="mt-auto" />
    </article>
  )
}
