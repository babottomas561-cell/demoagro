import type { ReactNode } from 'react'
import clsx from 'clsx'

interface SimpleChartCardProps {
  title: string
  description?: string
  actions?: ReactNode
  children: ReactNode
  className?: string
}

export function SimpleChartCard({
  title,
  description,
  actions,
  children,
  className,
}: SimpleChartCardProps) {
  return (
    <section
      className={clsx(
        'rounded-[1.7rem] border border-[#e8dfd1] bg-[linear-gradient(180deg,rgba(255,253,249,0.98),rgba(248,244,236,0.96))] p-3 shadow-[0_1px_0_rgba(24,20,12,0.03)] sm:p-4',
        className
      )}
    >
      <div className="mb-3 flex flex-col gap-2 border-b border-[#ece4d7] pb-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 sm:max-w-[70%]">
          <h2 className="text-[1.02rem] font-bold tracking-[-0.03em] text-text">{title}</h2>
          {description ? <p className="mt-1.5 text-[13px] leading-6 text-text-muted">{description}</p> : null}
        </div>
        {actions ? (
          <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-[#ece4d7] bg-[#fbf8f2]/90 p-1.5">
            {actions}
          </div>
        ) : null}
      </div>
      {children}
    </section>
  )
}
