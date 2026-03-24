import clsx from 'clsx'

type OperationalTone = 'neutral' | 'positive' | 'warning' | 'danger'

export interface OperationalListItem {
  title: string
  subtitle?: string
  value?: string
  meta?: string
  tone?: OperationalTone
}

interface OperationalListCardProps {
  title: string
  description?: string
  items: OperationalListItem[]
  emptyMessage?: string
}

const toneClass: Record<OperationalTone, string> = {
  neutral: 'text-text-subtle',
  positive: 'text-primary-700',
  warning: 'text-warning',
  danger: 'text-danger',
}

export function OperationalListCard({
  title,
  description,
  items,
  emptyMessage = 'Sin elementos para mostrar.',
}: OperationalListCardProps) {
  return (
    <section className="rounded-[1.5rem] border border-border/60 bg-white/[0.9] p-4 sm:p-5">
      <div className="mb-4 border-b border-border/70 pb-4">
        <h2 className="text-base font-semibold tracking-[-0.03em] text-text">{title}</h2>
        {description ? <p className="mt-1 text-sm leading-6 text-text-muted">{description}</p> : null}
      </div>

      {!items.length ? (
        <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-text-muted">
          {emptyMessage}
        </div>
      ) : (
        <div className="space-y-0">
          {items.map((item, index) => (
            <div
              key={`${item.title}-${index}`}
              className={clsx(
                'flex items-start justify-between gap-3 py-3',
                index !== items.length - 1 && 'border-b border-border/70'
              )}
            >
              <div className="min-w-0">
                <p className="text-sm font-semibold text-text">{item.title}</p>
                {item.subtitle ? <p className="mt-1 text-sm text-text-muted">{item.subtitle}</p> : null}
              </div>
              <div className="shrink-0 text-right">
                {item.value ? (
                  <p className={clsx('text-sm font-semibold', toneClass[item.tone || 'neutral'])}>{item.value}</p>
                ) : null}
                {item.meta ? <p className="mt-1 text-xs text-text-subtle">{item.meta}</p> : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}
