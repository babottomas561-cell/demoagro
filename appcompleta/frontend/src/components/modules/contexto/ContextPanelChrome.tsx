import type { ReactNode } from 'react'
import clsx from 'clsx'
import { Badge } from '@/components/ui/Badge'
import { DataSourceTag } from '@/components/ui/DataSourceTag'

type ContextTone = 'macro' | 'market' | 'clima'

const toneMap: Record<ContextTone, { dot: string; text: string }> = {
  macro: { dot: 'bg-accent', text: 'text-accent' },
  market: { dot: 'bg-accent', text: 'text-accent' },
  clima: { dot: 'bg-info', text: 'text-info' },
}

interface ContextPanelBannerProps {
  label: string
  source?: string
  lastUpdated?: string
  tone?: ContextTone
  badges?: ReactNode
}

export function ContextPanelBanner({
  label,
  source,
  lastUpdated,
  tone = 'market',
  badges,
}: ContextPanelBannerProps) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 rounded-2xl border border-border bg-surface px-4 py-3">
      <span className={clsx('h-2 w-2 animate-pulse rounded-full', toneMap[tone].dot)} />
      <span className={clsx('text-[11px] font-semibold uppercase tracking-[0.18em]', toneMap[tone].text)}>
        {label}
      </span>
      {source && <DataSourceTag fuente={source} ultimaActualizacion={lastUpdated} live />}
      {badges}
    </div>
  )
}

interface ContextHeroProps {
  title: string
  description: string
  badges?: ReactNode
  eyebrow?: string
  className?: string
}

export function ContextHero({
  title,
  description,
  badges,
  eyebrow = 'Lectura Ejecutiva',
  className,
}: ContextHeroProps) {
  return (
    <div className={clsx('rounded-2xl border border-border bg-surface p-5', className)}>
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
            {eyebrow}
          </p>
          <h3 className="mt-2 text-lg font-semibold tracking-tight text-text">
            {title}
          </h3>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">
            {description}
          </p>
        </div>
        {badges && <div className="flex flex-wrap gap-2 lg:justify-end">{badges}</div>}
      </div>
    </div>
  )
}

interface ContextSectionHeaderProps {
  title: string
  description: string
  badges?: ReactNode
  className?: string
}

export function ContextSectionHeader({
  title,
  description,
  badges,
  className,
}: ContextSectionHeaderProps) {
  return (
    <div className={clsx('mb-4 flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between', className)}>
      <div className="min-w-0">
        <h3 className="text-sm font-semibold tracking-tight text-text">{title}</h3>
        <p className="mt-1 text-sm leading-6 text-text-muted">{description}</p>
      </div>
      {badges && <div className="flex flex-wrap items-center gap-2">{badges}</div>}
    </div>
  )
}

interface ContextHeroBadgeProps {
  children: ReactNode
  variant?: 'neutral' | 'warning' | 'danger' | 'success' | 'info'
}

export function ContextHeroBadge({
  children,
  variant = 'neutral',
}: ContextHeroBadgeProps) {
  return (
    <Badge variant={variant} size="md" className="whitespace-nowrap">
      {children}
    </Badge>
  )
}
