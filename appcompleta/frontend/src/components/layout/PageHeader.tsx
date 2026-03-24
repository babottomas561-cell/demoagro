import clsx from 'clsx'
import type { LucideIcon } from 'lucide-react'

interface PageHeaderProps {
  title: string
  description?: string
  subtitle?: string
  icon?: LucideIcon
  actions?: React.ReactNode
  className?: string
}

export function PageHeader({ title, description, subtitle, icon: Icon, actions, className }: PageHeaderProps) {
  const desc = description || subtitle
  return (
    <div className={clsx('flex flex-col gap-4 border-b border-border/70 pb-4 sm:flex-row sm:items-start sm:justify-between', className)}>
      <div className="flex items-start gap-3">
        {Icon && (
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-primary-100 bg-primary-50 text-primary-700">
            <Icon className="h-4 w-4" />
          </div>
        )}
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-text">{title}</h1>
          {desc && (
            <p className="mt-1 max-w-3xl text-sm text-text-muted">{desc}</p>
          )}
        </div>
      </div>
      {actions && <div className="flex items-center gap-2 self-start">{actions}</div>}
    </div>
  )
}
