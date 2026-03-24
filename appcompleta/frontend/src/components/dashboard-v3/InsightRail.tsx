export type InsightTone = 'neutral' | 'positive' | 'warning' | 'critical'

const toneMap: Record<InsightTone, string> = {
  neutral: 'border-border/90',
  positive: 'border-primary-300/80',
  warning: 'border-[#d7bc82]/90',
  critical: 'border-[#e2b5af]/90',
}

export function InsightRail({
  sections,
}: {
  sections: Array<{
    title: string
    items: Array<{
      title: string
      description?: string
      tone?: string
      meta?: string
    }>
  }>
}) {
  return (
    <div className="space-y-5">
      {sections.map((section) => (
        <section key={section.title}>
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
            {section.title}
          </p>
          <div className="space-y-3">
            {section.items.length ? (
              section.items.map((item) => (
                <div
                  key={`${section.title}-${item.title}`}
                  className={`border-l-2 pl-4 ${
                    toneMap[
                      item.tone === 'critical'
                        ? 'critical'
                        : item.tone === 'warning'
                        ? 'warning'
                        : item.tone === 'positive'
                        ? 'positive'
                        : 'neutral'
                    ]
                  }`}
                >
                  <p className="text-sm font-semibold text-text">{item.title}</p>
                  {item.description ? <p className="mt-1 text-sm text-text-muted">{item.description}</p> : null}
                  {item.meta ? <p className="mt-2 text-xs font-medium text-text-subtle">{item.meta}</p> : null}
                </div>
              ))
            ) : (
              <p className="text-sm text-text-subtle">Sin señales activas.</p>
            )}
          </div>
        </section>
      ))}
    </div>
  )
}
