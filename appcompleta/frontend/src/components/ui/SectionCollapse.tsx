'use client'

import { useState } from 'react'
import { ChevronDown } from 'lucide-react'
import clsx from 'clsx'

interface SectionCollapseProps {
  title: string
  badge?: string | number   // ej: "4 alertas"
  defaultOpen?: boolean
  children: React.ReactNode
  className?: string
}

/**
 * Sección colapsable para dashboards.
 * Permite al usuario minimizar bloques secundarios para
 * enfocarse en los KPIs principales (útil en mobile).
 */
export function SectionCollapse({
  title,
  badge,
  defaultOpen = true,
  children,
  className,
}: SectionCollapseProps) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <section className={clsx('space-y-3', className)}>
      <button
        onClick={() => setOpen(!open)}
        className="group flex w-full items-center gap-2 text-left"
        aria-expanded={open}
      >
        <span className="section-label flex-1">{title}</span>

        {badge !== undefined && !open && (
          <span className="badge badge-gray text-[10px]">{badge}</span>
        )}

        <ChevronDown
          size={12}
          className={clsx(
            'shrink-0 text-text-subtle transition-transform duration-200',
            open ? 'rotate-0' : '-rotate-90'
          )}
        />
      </button>

      <div
        className={clsx(
          'overflow-hidden transition-all duration-200 ease-in-out',
          open ? 'max-h-[2000px] opacity-100' : 'max-h-0 opacity-0'
        )}
      >
        {children}
      </div>
    </section>
  )
}
