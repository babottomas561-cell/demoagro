import { formatPercent } from '@/lib/formatters'
import { ManagerExplanation } from '@/components/explanations/ManagerExplanation'

interface DeviationCardProps {
  label: string
  actualLabel?: string
  expectedLabel?: string
  actual: string
  expected: string
  delta: string
  deltaPct: number
}

export function DeviationCard({
  label,
  actualLabel = 'Real',
  expectedLabel = 'Esperado',
  actual,
  expected,
  delta,
  deltaPct,
}: DeviationCardProps) {
  const toneClass =
    deltaPct < -5
      ? 'text-danger'
      : deltaPct > 5
      ? 'text-[#9d7a36]'
      : 'text-primary-700'

  return (
    <div className="rounded-[1.35rem] border border-border/70 bg-[#fbf8f2] p-4">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
        {label}
      </p>
      <div className="mt-3 grid grid-cols-2 gap-3">
        <div>
          <p className="text-[11px] font-medium text-text-subtle">{actualLabel}</p>
          <p className="mt-1 text-lg font-semibold text-text">{actual}</p>
        </div>
        <div>
          <p className="text-[11px] font-medium text-text-subtle">{expectedLabel}</p>
          <p className="mt-1 text-lg font-semibold text-text">{expected}</p>
        </div>
      </div>
      <div className="mt-3 border-t border-border/70 pt-3">
        <p className="text-[11px] font-medium text-text-subtle">Desvío</p>
        <p className={`mt-1 text-sm font-semibold ${toneClass}`}>
          {delta} · {formatPercent(deltaPct)}
        </p>
      </div>
      <ManagerExplanation subject={label} mode="deviation" compact />
    </div>
  )
}
