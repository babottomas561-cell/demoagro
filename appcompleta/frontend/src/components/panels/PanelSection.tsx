import clsx from 'clsx'
import type { ReactNode } from 'react'

interface PanelSectionProps {
  index: number
  title: string
  description: string
  actions?: ReactNode
  children: ReactNode
  className?: string
  bodyClassName?: string
}

export function PanelSection({
  index,
  title,
  description,
  actions,
  children,
  className,
  bodyClassName,
}: PanelSectionProps) {
  return (
    <section
      className={clsx(
        'rounded-[2rem] border border-border/60 bg-white/[0.8] px-4 py-4 sm:px-5 sm:py-5',
        className
      )}
    >
      <div className="flex flex-col gap-3 border-b border-border/70 pb-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-3">
            <div className="flex h-7 min-w-7 items-center justify-center rounded-full border border-border bg-[#fbf8f2] px-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
              {index}
            </div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
              Sección {index}
            </p>
          </div>
          <h2 className="mt-2 text-lg font-semibold tracking-[-0.03em] text-text">
            {title}
          </h2>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-text-muted">{description}</p>
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2 rounded-2xl bg-[#fbf8f2] p-1">{actions}</div> : null}
      </div>
      <div className={clsx('mt-4', bodyClassName)}>{children}</div>
    </section>
  )
}
