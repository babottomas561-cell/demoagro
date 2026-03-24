'use client'

import { useEffect, useState } from 'react'
import clsx from 'clsx'

interface DataSourceTagProps {
  fuente: string
  ultimaActualizacion?: string
  live?: boolean
  className?: string
}

function useTickingAge(ultimaActualizacion?: string): string | null {
  const [label, setLabel] = useState<string | null>(null)

  useEffect(() => {
    if (!ultimaActualizacion) return

    const compute = () => {
      const ref = new Date(ultimaActualizacion).getTime()
      if (isNaN(ref)) return null
      const diffSec = Math.floor((Date.now() - ref) / 1000)
      if (diffSec < 5)  return 'ahora'
      if (diffSec < 60) return `hace ${diffSec}s`
      const diffMin = Math.floor(diffSec / 60)
      if (diffMin < 60) return `hace ${diffMin} min`
      const diffH = Math.floor(diffMin / 60)
      if (diffH < 24)   return `hace ${diffH} h`
      return `hace ${Math.floor(diffH / 24)} días`
    }

    setLabel(compute())
    const id = setInterval(() => setLabel(compute()), 1000)
    return () => clearInterval(id)
  }, [ultimaActualizacion])

  return label
}

export function DataSourceTag({ fuente, ultimaActualizacion, live = false, className }: DataSourceTagProps) {
  const age = useTickingAge(ultimaActualizacion)

  return (
    <div className={clsx('flex flex-wrap items-center gap-2 text-[11px] text-text-subtle', className)}>
      <span className="inline-flex items-center gap-1.5 rounded-full border border-[#e6ddcf] bg-white/75 px-2.5 py-1 shadow-[0_1px_0_rgba(24,20,12,0.03)]">
        <span
          className={clsx(
            'h-1.5 w-1.5 rounded-full',
            live ? 'animate-pulse bg-accent' : 'bg-text-subtle'
          )}
        />
        <span className="font-semibold uppercase tracking-[0.12em] text-text-subtle">{fuente}</span>
      </span>
      {age ? (
        <span className="inline-flex items-center rounded-full border border-[#e6ddcf] bg-[#fbf8f2]/80 px-2.5 py-1 text-text-muted">
          <span className="hidden sm:inline">Actualizado&nbsp;</span>
          {age}
        </span>
      ) : null}
    </div>
  )
}
