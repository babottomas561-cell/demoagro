'use client'

interface BulletChartProps {
  value: number
  target: number
  max?: number
  label?: string
}

export function BulletChart({
  value,
  target,
  max,
  label,
}: BulletChartProps) {
  const limit = max || Math.max(value, target, 1)
  const valuePct = Math.min((value / limit) * 100, 100)
  const targetPct = Math.min((target / limit) * 100, 100)
  const tone = value >= target ? 'bg-primary-700' : value >= target * 0.9 ? 'bg-[#9d7a36]' : 'bg-danger'

  return (
    <div className="space-y-1.5">
      {label ? <p className="text-[11px] font-medium text-text-subtle">{label}</p> : null}
      <div className="relative h-2.5 rounded-full bg-surface-2">
        <div className={`h-full rounded-full ${tone}`} style={{ width: `${valuePct}%` }} />
        <div
          className="absolute top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-full bg-text"
          style={{ left: `${targetPct}%` }}
        />
      </div>
    </div>
  )
}
