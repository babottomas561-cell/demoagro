'use client'

import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { SlidersHorizontal, X } from 'lucide-react'

export interface DrawerFilterOption {
  value: string
  label: string
}

export interface DrawerFilterConfig {
  key: string
  label: string
  options: DrawerFilterOption[]
}

interface MoreFiltersDrawerProps {
  open: boolean
  onClose: () => void
  values: Record<string, string>
  filters: DrawerFilterConfig[]
  onChange: (key: string, value: string) => void
  onClear?: (keys: string[]) => void
}

export function MoreFiltersDrawer({
  open,
  onClose,
  values,
  filters,
  onChange,
  onClear,
}: MoreFiltersDrawerProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  useEffect(() => {
    if (!open) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [open])

  if (!mounted || !open) return null

  return createPortal(
    <div className="fixed inset-0 z-[95]">
      <button
        type="button"
        aria-label="Cerrar más filtros"
        className="absolute inset-0 bg-[#1b1a17]/24 backdrop-blur-[2px]"
        onClick={onClose}
      />

      <div className="absolute inset-y-0 right-0 flex w-full justify-end sm:w-auto">
        <div className="flex h-full w-full max-w-md flex-col border-l border-border bg-background sm:bg-surface">
          <div className="flex items-start justify-between gap-4 border-b border-border px-4 py-4 sm:px-5">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
                Filtros
              </p>
              <h2 className="mt-1 text-lg font-semibold text-text">Más filtros</h2>
              <p className="mt-1 text-sm text-text-muted">
                Ajustá el contexto de lectura sin recargar la barra principal.
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-surface text-text-muted transition-colors hover:text-text"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-5 sm:px-5">
            {filters.map((filter) => (
              <div key={filter.key} className="space-y-2">
                <label className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
                  {filter.label}
                </label>
                <div className="relative">
                  <select
                    value={values[filter.key] ?? ''}
                    onChange={(event) => onChange(filter.key, event.target.value)}
                    className="min-h-11 w-full appearance-none rounded-xl border border-border bg-surface px-3 py-2 pr-10 text-sm text-text transition-colors hover:border-border-strong focus:border-primary-500 focus:outline-none"
                  >
                    <option value="">{filter.label}: Todos</option>
                    {filter.options.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                  <SlidersHorizontal className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-subtle" />
                </div>
              </div>
            ))}
          </div>
          <div className="flex items-center justify-between gap-3 border-t border-border bg-white/75 px-4 py-4 sm:px-5">
            <button
              type="button"
              onClick={() => onClear?.(filters.map((filter) => filter.key))}
              className="inline-flex h-10 items-center justify-center rounded-xl border border-border bg-surface px-4 text-sm font-medium text-text-muted transition-colors hover:border-border-strong hover:text-text"
            >
              Limpiar extras
            </button>
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-10 items-center justify-center rounded-xl bg-primary-600 px-4 text-sm font-semibold text-white transition-colors hover:bg-primary-700"
            >
              Aplicar filtros
            </button>
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}
