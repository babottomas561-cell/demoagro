'use client'

import { createPortal } from 'react-dom'
import { useState, useEffect, useCallback } from 'react'
import { Maximize2, Minimize2, X } from 'lucide-react'
import clsx from 'clsx'

interface FullscreenChartProps {
  title: string
  descripcion?: string
  children: React.ReactNode
  className?: string
}

/**
 * Wrapper de gráfico con botón de pantalla completa.
 * En fullscreen, el gráfico ocupa toda la pantalla via Portal.
 * Ideal para móvil donde los gráficos son pequeños.
 */
export function FullscreenChart({
  title,
  descripcion,
  children,
  className,
}: FullscreenChartProps) {
  const [fullscreen, setFullscreen] = useState(false)
  const [mounted, setMounted] = useState(false)

  useEffect(() => { setMounted(true) }, [])

  const open = useCallback(() => {
    setFullscreen(true)
    document.body.style.overflow = 'hidden'
  }, [])

  const close = useCallback(() => {
    setFullscreen(false)
    document.body.style.overflow = ''
  }, [])

  // Cerrar con Escape
  useEffect(() => {
    if (!fullscreen) return
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') close() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [fullscreen, close])

  const header = (
    <div className="flex items-start justify-between gap-3">
      <div className="min-w-0">
        <h3 className="text-sm font-semibold text-text truncate">{title}</h3>
        {descripcion && (
          <p className="mt-0.5 text-[11px] text-text-muted line-clamp-1">{descripcion}</p>
        )}
      </div>
      <button
        onClick={fullscreen ? close : open}
        title={fullscreen ? 'Salir de pantalla completa (Esc)' : 'Pantalla completa'}
        className="shrink-0 flex h-7 w-7 items-center justify-center rounded-md border border-border bg-surface-2 text-text-muted transition-colors hover:border-border-strong hover:text-text"
      >
        {fullscreen
          ? <Minimize2 size={12} />
          : <Maximize2 size={12} />
        }
      </button>
    </div>
  )

  // Vista normal (dentro del flujo)
  const normalView = (
    <div className={clsx('card p-4 flex flex-col gap-3', className)}>
      {header}
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  )

  // Vista fullscreen (portal al body)
  const fullscreenView = mounted && fullscreen
    ? createPortal(
        <div className="fixed inset-0 z-[100] flex flex-col bg-surface p-4 sm:p-6 animate-slide-up">
          {/* Header fullscreen */}
          <div className="flex items-start justify-between gap-4 mb-4 shrink-0">
            <div className="min-w-0">
              <p className="section-label mb-1">Gráfico expandido</p>
              <h2 className="text-lg font-semibold text-text">{title}</h2>
              {descripcion && (
                <p className="mt-1 text-sm text-text-muted">{descripcion}</p>
              )}
            </div>
            <button
              onClick={close}
              aria-label="Cerrar pantalla completa"
              className="shrink-0 flex h-9 w-9 items-center justify-center rounded-full border border-border bg-surface-2 text-text-muted transition-colors hover:text-text"
            >
              <X size={16} />
            </button>
          </div>

          {/* Gráfico ocupa el resto */}
          <div className="flex-1 min-h-0 card p-4">
            {children}
          </div>
        </div>,
        document.body
      )
    : null

  return (
    <>
      {normalView}
      {fullscreenView}
    </>
  )
}
