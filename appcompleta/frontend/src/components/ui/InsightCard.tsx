import clsx from 'clsx'
import { AlertCircle, AlertTriangle, CheckCircle2, Info } from 'lucide-react'
import { formatRelativeTime } from '@/lib/formatters'
import type { ExecutiveInsight } from '@/types/dashboard'

interface InsightCardProps {
  insight: ExecutiveInsight
  className?: string
}

const config = {
  info: {
    icon: Info,
    border: 'border-info/20',
    bg: 'bg-info/5',
    iconColor: 'text-info',
    dot: 'bg-info',
  },
  warning: {
    icon: AlertTriangle,
    border: 'border-warning/20',
    bg: 'bg-warning/5',
    iconColor: 'text-warning',
    dot: 'bg-warning',
  },
  critical: {
    icon: AlertCircle,
    border: 'border-danger/20',
    bg: 'bg-danger/5',
    iconColor: 'text-danger',
    dot: 'bg-danger animate-pulse',
  },
  success: {
    icon: CheckCircle2,
    border: 'border-accent/20',
    bg: 'bg-accent/5',
    iconColor: 'text-accent',
    dot: 'bg-accent',
  },
}

/**
 * GenericInsightCard — standalone insight card that doesn't require an
 * ExecutiveInsight object. Use this in module panels where insights come
 * from hook data in a simpler shape.
 *
 * tipo mapping:
 *   'critico'  → red  (AlertCircle, pulsing dot)
 *   'alerta'   → amber (AlertTriangle)
 *   'positivo' → green (CheckCircle2)
 *   'neutro'   → sky  (Info)
 */
type GenericTipo = 'critico' | 'alerta' | 'positivo' | 'neutro'

const tipoToSeveridad: Record<GenericTipo, keyof typeof config> = {
  critico: 'critical',
  alerta: 'warning',
  positivo: 'success',
  neutro: 'info',
}

interface GenericInsightCardProps {
  titulo: string
  descripcion?: string
  tipo?: GenericTipo
  /** Fallback if you already have a severidad value */
  severidad?: keyof typeof config
  className?: string
}

export function GenericInsightCard({
  titulo,
  descripcion,
  tipo = 'neutro',
  severidad,
  className,
}: GenericInsightCardProps) {
  const key = severidad ?? tipoToSeveridad[tipo]
  const c = config[key]
  const Icon = c.icon

  return (
    <div className={clsx('rounded-2xl border p-4', c.border, c.bg, className)}>
      <div className="flex items-start gap-3">
        <Icon className={clsx('mt-0.5 h-4 w-4 flex-shrink-0', c.iconColor)} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text">{titulo}</p>
          {descripcion ? (
            <p className="mt-1 text-xs leading-5 text-text-muted">{descripcion}</p>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export function InsightCard({ insight, className }: InsightCardProps) {
  const c = config[insight.severidad]
  const Icon = c.icon

  return (
    <div
      className={clsx(
        'rounded-2xl border p-4',
        c.border,
        c.bg,
        className
      )}
    >
      <div className="flex items-start gap-3">
        <Icon className={clsx('mt-0.5 h-4 w-4 flex-shrink-0', c.iconColor)} />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text">{insight.titulo}</p>
          <p className="mt-1 text-xs text-text-muted">{insight.descripcion}</p>
          <div className="mt-2 flex items-center gap-2">
            <span className="text-2xs font-medium uppercase tracking-wide text-text-subtle">
              {insight.modulo}
            </span>
            <span className="text-text-subtle">·</span>
            <span className="text-2xs text-text-subtle">
              {formatRelativeTime(insight.timestamp)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
