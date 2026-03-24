import { Badge } from '@/components/ui/Badge'

interface ResourceEfficiencyCardProps {
  title: string
  resource: string
  value: string
  benchmark?: string
  description: string
  tone?: 'success' | 'warning' | 'danger'
}

export function ResourceEfficiencyCard({
  title,
  resource,
  value,
  benchmark,
  description,
  tone = 'success',
}: ResourceEfficiencyCardProps) {
  return (
    <div className="rounded-2xl border border-border bg-surface p-4">
      <div className="mb-2 flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">{title}</p>
          <p className="mt-1 text-sm font-semibold text-text">{resource}</p>
        </div>
        <Badge variant={tone === 'danger' ? 'danger' : tone === 'warning' ? 'warning' : 'success'}>
          {value}
        </Badge>
      </div>
      {benchmark && <p className="text-xs text-text-subtle">{benchmark}</p>}
      <p className="mt-3 text-sm text-text-muted">{description}</p>
    </div>
  )
}
