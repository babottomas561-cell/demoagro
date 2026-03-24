import clsx from 'clsx'
import type { ReactNode } from 'react'

export function DashboardHeroLayout({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(19rem,0.8fr)]', className)}>{children}</section>
}

export function DashboardHeroSide({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <div className={clsx('grid grid-cols-1 gap-4', className)}>{children}</div>
}

export function DashboardMainLayout({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.5fr)_minmax(20rem,0.75fr)]', className)}>{children}</section>
}

export function DashboardSplitRow({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('grid grid-cols-1 gap-6 xl:grid-cols-2', className)}>{children}</section>
}

export function DashboardSection({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <section className={clsx('space-y-4', className)}>{children}</section>
}

export function DashboardSectionHeader({
  title,
  description,
  aside,
  className,
}: {
  title: string
  description?: string
  aside?: ReactNode
  className?: string
}) {
  return (
    <div className={clsx('flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between', className)}>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold tracking-tight text-text">{title}</h3>
        {description && <p className="mt-1 text-sm text-text-muted">{description}</p>}
      </div>
      {aside && <div className="flex shrink-0 items-center gap-2">{aside}</div>}
    </div>
  )
}

export function DashboardRail({
  children,
  className,
}: {
  children: ReactNode
  className?: string
}) {
  return <aside className={clsx('space-y-5 xl:pl-2', className)}>{children}</aside>
}
