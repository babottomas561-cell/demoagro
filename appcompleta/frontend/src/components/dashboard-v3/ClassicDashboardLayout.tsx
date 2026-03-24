import clsx from 'clsx'
import type { ReactNode } from 'react'

export function ClassicKpiRow({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4', className)}>{children}</section>
}

export function ClassicChartRow({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('grid grid-cols-1 gap-5 xl:grid-cols-2', className)}>{children}</section>
}

export function ClassicChartCard({
  title,
  description,
  aside,
  children,
}: {
  title: string
  description?: string
  aside?: ReactNode
  children: ReactNode
}) {
  return (
    <section className="rounded-[1.8rem] border border-border/80 bg-white/82 p-5 sm:p-6">
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">Classic View</p>
          <h3 className="mt-1 text-lg font-semibold tracking-tight text-text">{title}</h3>
          {description ? <p className="mt-1 text-sm text-text-muted">{description}</p> : null}
        </div>
        {aside ? <div className="min-w-0 sm:max-w-full">{aside}</div> : null}
      </div>
      {children}
    </section>
  )
}
