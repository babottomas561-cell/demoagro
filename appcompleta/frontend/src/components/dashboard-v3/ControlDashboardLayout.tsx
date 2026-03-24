import clsx from 'clsx'
import type { ReactNode } from 'react'
import {
  inferManagerExplanationMode,
  ManagerExplanation,
  type ManagerExplanationMode,
} from '@/components/explanations/ManagerExplanation'

export function ControlKpiStrip({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={clsx(
        'rounded-[1.75rem] border border-border/60 bg-white/[0.82] px-4 py-4 sm:px-5',
        className
      )}
    >
      <div className="grid grid-cols-2 gap-x-4 gap-y-5 lg:grid-cols-4 xl:grid-cols-6">
        {children}
      </div>
    </section>
  )
}

export function ControlKpi({
  label,
  value,
  subtitle,
  delta,
  tone = 'neutral',
  managerNotes,
  managerMode = 'metric',
}: {
  label: string
  value: string
  subtitle?: string
  delta?: string
  tone?: 'neutral' | 'positive' | 'warning' | 'critical'
  managerNotes?: string[]
  managerMode?: ManagerExplanationMode
}) {
  const deltaClass =
    tone === 'critical'
      ? 'text-danger'
      : tone === 'warning'
      ? 'text-[#9d7a36]'
      : tone === 'positive'
      ? 'text-primary-700'
      : 'text-text-subtle'

  return (
    <article className="min-w-0 border-l border-border/70 pl-4 first:border-l-0 first:pl-0 lg:first:pl-0">
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">{label}</p>
      <div className="mt-2 flex items-end gap-2">
        <h2 className="truncate text-[1.85rem] font-semibold leading-none tracking-[-0.05em] text-text sm:text-[2rem]">
          {value}
        </h2>
        {delta ? <span className={clsx('pb-1 text-xs font-medium', deltaClass)}>{delta}</span> : null}
      </div>
      {subtitle ? <p className="mt-1.5 text-xs leading-5 text-text-muted">{subtitle}</p> : null}
      <ManagerExplanation subject={label} mode={managerMode} items={managerNotes} compact />
    </article>
  )
}

export function ControlMainGrid({
  main,
  rail,
  className,
}: {
  main: ReactNode
  rail: ReactNode
  className?: string
}) {
  return (
    <section className={clsx('grid grid-cols-1 gap-5 xl:grid-cols-[minmax(0,1.7fr)_22rem]', className)}>
      <div className="min-w-0">{main}</div>
      <aside className="min-w-0">{rail}</aside>
    </section>
  )
}

export function ControlBottomGrid({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('grid grid-cols-1 gap-5 xl:grid-cols-2', className)}>{children}</section>
}

export function ControlPanel({
  title,
  description,
  meta,
  children,
  className,
  contentClassName,
  managerNotes,
  managerMode,
}: {
  title: string
  description?: string
  meta?: ReactNode
  children: ReactNode
  className?: string
  contentClassName?: string
  managerNotes?: string[]
  managerMode?: ManagerExplanationMode
}) {
  const explanationMode = managerMode || inferManagerExplanationMode(`${title} ${description || ''}`)

  return (
    <section className={clsx('rounded-[1.9rem] border border-border/60 bg-white/[0.84] p-4 sm:p-5', className)}>
      <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">Lectura ejecutiva</p>
          <h3 className="mt-1 text-lg font-semibold tracking-[-0.03em] text-text">{title}</h3>
          {description ? <p className="mt-1 text-sm leading-6 text-text-muted">{description}</p> : null}
        </div>
        {meta ? <div className="min-w-0 sm:max-w-[52%]">{meta}</div> : null}
      </div>
      <div className={clsx('min-w-0', contentClassName)}>{children}</div>
      <ManagerExplanation
        subject={title}
        mode={explanationMode}
        items={managerNotes}
      />
    </section>
  )
}

export function ControlRail({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={clsx('grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1', className)}>{children}</div>
}

export function ControlRailMetric({
  label,
  value,
  detail,
  visual,
  tone = 'neutral',
  managerNotes,
  managerMode = 'risk',
}: {
  label: string
  value: string
  detail?: string
  visual?: ReactNode
  tone?: 'neutral' | 'positive' | 'warning' | 'critical'
  managerNotes?: string[]
  managerMode?: ManagerExplanationMode
}) {
  const toneClass =
    tone === 'critical'
      ? 'border-[#e2b5af]/70 bg-[#fcf5f3]'
      : tone === 'warning'
      ? 'border-[#ddcba0]/70 bg-[#fbf7ef]'
      : tone === 'positive'
      ? 'border-primary-200/70 bg-[#f4faf6]'
      : 'border-border/70 bg-[#fbf8f2]'

  return (
    <article className={clsx('flex h-full flex-col rounded-[1.35rem] border p-3.5', toneClass)}>
      <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">{label}</p>
      <p className="mt-2 text-[1.45rem] font-semibold leading-none tracking-[-0.04em] text-text">{value}</p>
      {detail ? <p className="mt-1.5 text-xs leading-5 text-text-muted">{detail}</p> : null}
      {visual ? <div className="mt-3">{visual}</div> : null}
      <ManagerExplanation subject={label} mode={managerMode} items={managerNotes} compact className="mt-auto" />
    </article>
  )
}
