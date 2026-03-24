import clsx from 'clsx'
import type { ReactNode } from 'react'

export function DashboardHero({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={clsx(
        'grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.55fr)_minmax(16rem,0.72fr)_minmax(16rem,0.72fr)]',
        className
      )}
    >
      {children}
    </section>
  )
}

export function DashboardMainBlock({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={clsx(
        'grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(18rem,0.75fr)]',
        className
      )}
    >
      {children}
    </section>
  )
}

export function DashboardSecondaryBlock({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('grid grid-cols-1 gap-5 xl:grid-cols-2', className)}>{children}</section>
}

export function DashboardPanel({
  title,
  description,
  aside,
  children,
  className,
}: {
  title: string
  description?: string
  aside?: ReactNode
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={clsx(
        'rounded-[2rem] border border-border/80 bg-white/80 p-5 sm:p-6',
        className
      )}
    >
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
            Decision Layer
          </p>
          <h3 className="mt-1 text-lg font-semibold tracking-tight text-text">{title}</h3>
          {description ? <p className="mt-1 text-sm text-text-muted">{description}</p> : null}
        </div>
        {aside ? <div className="shrink-0">{aside}</div> : null}
      </div>
      {children}
    </section>
  )
}

export function DashboardRail({
  title,
  description,
  children,
  className,
}: {
  title: string
  description?: string
  children: ReactNode
  className?: string
}) {
  return (
    <aside
      className={clsx(
        'rounded-[2rem] border border-border/80 bg-[#f7f3ea]/88 p-5 sm:p-6',
        className
      )}
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">Focus Rail</p>
      <h3 className="mt-1 text-lg font-semibold tracking-tight text-text">{title}</h3>
      {description ? <p className="mt-1 text-sm text-text-muted">{description}</p> : null}
      <div className="mt-5 space-y-5">{children}</div>
    </aside>
  )
}

export function DashboardTableBlock({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('rounded-[2rem] border border-border/80 bg-white/80 p-5 sm:p-6', className)}>{children}</section>
}
