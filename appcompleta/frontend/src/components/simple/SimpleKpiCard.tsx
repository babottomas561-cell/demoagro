import clsx from 'clsx'

type SimpleKpiTone = 'neutral' | 'positive' | 'warning' | 'danger'

interface SimpleKpiCardProps {
  label: string
  value: string
  delta?: string
  detail?: string
  tone?: SimpleKpiTone
}

const toneClass: Record<SimpleKpiTone, string> = {
  neutral: 'text-text-subtle',
  positive: 'text-primary-700',
  warning: 'text-warning',
  danger: 'text-danger',
}

const toneAccentClass: Record<SimpleKpiTone, string> = {
  neutral: 'bg-[#d9d1c3]',
  positive: 'bg-primary-600',
  warning: 'bg-[#d69f2f]',
  danger: 'bg-danger',
}

const toneBadgeClass: Record<SimpleKpiTone, string> = {
  neutral: 'border-[#e4dccf] bg-[#f6f1e8] text-text-subtle',
  positive: 'border-primary-200 bg-primary-50 text-primary-700',
  warning: 'border-[#ead39a] bg-[#fbf5e6] text-[#9b6b16]',
  danger: 'border-[#efc5bf] bg-[#fcf1ef] text-danger',
}

export function SimpleKpiCard({
  label,
  value,
  delta,
  detail,
  tone = 'neutral',
}: SimpleKpiCardProps) {
  return (
    <article className="relative flex min-h-[7.5rem] flex-col overflow-hidden rounded-[1.55rem] border border-[#e8dfd1] bg-[linear-gradient(180deg,rgba(255,253,249,0.98),rgba(249,245,238,0.96))] p-3.5 shadow-[0_1px_0_rgba(24,20,12,0.03)] sm:min-h-[8.5rem] sm:p-4">
      <div className={clsx('absolute inset-x-0 top-0 h-1', toneAccentClass[tone])} />
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <span className={clsx('h-2 w-2 rounded-full', toneAccentClass[tone])} />
          <p className="truncate text-[10px] font-bold uppercase tracking-[0.16em] text-text-subtle">{label}</p>
        </div>
        {delta ? (
          <span
            className={clsx(
              'max-w-[8.75rem] rounded-full border px-2.5 py-1 text-right text-[11px] font-semibold leading-4',
              toneBadgeClass[tone],
              toneClass[tone]
            )}
          >
            {delta}
          </span>
        ) : null}
      </div>
      <p className="mt-3.5 text-[1.75rem] font-extrabold leading-none tracking-[-0.06em] text-text sm:text-[2rem]">{value}</p>
      {detail ? <p className="mt-2.5 text-[11px] leading-5 text-text-muted">{detail}</p> : null}
    </article>
  )
}
