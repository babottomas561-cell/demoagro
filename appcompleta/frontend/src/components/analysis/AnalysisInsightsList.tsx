import clsx from 'clsx'

interface AnalysisInsightsListProps {
  title?: string
  items: string[]
  className?: string
}

export function AnalysisInsightsList({
  title = 'Insights automáticos',
  items,
  className,
}: AnalysisInsightsListProps) {
  return (
    <div className={clsx('rounded-[1.35rem] border border-border/70 bg-[#fbf8f2] p-4', className)}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
        {title}
      </p>
      <div className="mt-3 space-y-2.5">
        {items.map((item) => (
          <div key={item} className="flex gap-2">
            <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary-600" />
            <p className="text-sm leading-5 text-text">{item}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

