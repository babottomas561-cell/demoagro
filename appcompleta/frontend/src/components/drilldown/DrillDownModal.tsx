'use client'

import { useEffect, useId, useState } from 'react'
import { createPortal } from 'react-dom'
import type { ColDef } from 'ag-grid-community'
import { Database, Filter, Table2, X } from 'lucide-react'
import { AgGridWrapper } from '@/components/tables/AgGrid'
import { Badge } from '@/components/ui/Badge'
import { DataSourceTag } from '@/components/ui/DataSourceTag'
import type { DrillDownFilterChip } from '@/lib/drilldown'

export interface DrillDownSummaryItem {
  label: string
  value: string
  detail?: string
}

interface DrillDownModalProps<T> {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  formula?: string
  summaryItems?: DrillDownSummaryItem[]
  contextText?: string
  source?: string
  lastUpdated?: string
  filtersApplied?: DrillDownFilterChip[]
  detailRows?: T[]
  detailColumns: ColDef<T>[]
  exportFilename?: string
  detailLabel?: string
}

export function DrillDownModal<T>({
  open,
  onClose,
  title,
  description,
  formula,
  summaryItems,
  contextText,
  source,
  lastUpdated,
  filtersApplied,
  detailRows = [],
  detailColumns,
  exportFilename = 'detalle-dashboard',
  detailLabel = 'Datos base utilizados para este resumen',
}: DrillDownModalProps<T>) {
  const [mounted, setMounted] = useState(false)
  const titleId = useId()

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

  useEffect(() => {
    if (!open) return

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose, open])

  if (!mounted || !open) {
    return null
  }

  return createPortal(
    <div className="fixed inset-0 z-[90]">
      <button
        type="button"
        aria-label="Cerrar detalle"
        className="absolute inset-0 bg-[#1b1a17]/24 backdrop-blur-[2px]"
        onClick={onClose}
      />

      <div className="absolute inset-0 md:flex md:items-center md:justify-center md:p-6">
        <div className="relative flex h-full w-full flex-col overflow-hidden bg-background md:max-h-[88vh] md:max-w-6xl md:rounded-[28px] md:border md:border-border md:bg-surface">
          <div className="border-b border-border bg-surface px-4 py-4 md:px-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
                  Informe ERP
                </p>
                <h2 id={titleId} className="text-xl font-semibold text-text">
                  {title}
                </h2>
                {description && (
                  <p className="mt-1 text-sm text-text-muted">{description}</p>
                )}
              </div>

              <button
                type="button"
                onClick={onClose}
                className="inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-surface text-text-muted transition-all hover:border-border-strong hover:text-text"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2">
              <Badge variant="neutral" dot>
                {detailRows.length} registros
              </Badge>
              {source && (
                <div className="rounded-full border border-border bg-surface px-2.5 py-1">
                  <DataSourceTag fuente={source} ultimaActualizacion={lastUpdated} />
                </div>
              )}
            </div>

            {summaryItems?.length ? (
              <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
                {summaryItems.map((item) => (
                  <div key={`${item.label}-${item.value}`} className="rounded-2xl border border-border bg-surface p-4">
                    <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">{item.label}</p>
                    <p className="mt-2 text-xl font-semibold tracking-[-0.04em] text-text">{item.value}</p>
                    {item.detail ? <p className="mt-1 text-xs leading-5 text-text-muted">{item.detail}</p> : null}
                  </div>
                ))}
              </div>
            ) : null}

            <div className="mt-4 rounded-2xl border border-border bg-surface p-4">
              <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
                <Table2 className="h-3.5 w-3.5" />
                Contexto del informe
              </div>
              <p className="text-sm text-text-muted">
                {contextText || description || detailLabel || formula || 'Detalle tabular del ERP para revisar el dato, sus variaciones y su base operativa.'}
              </p>
            </div>

            {!!filtersApplied?.length && (
              <div className="mt-3 rounded-2xl border border-border bg-surface p-4">
                <div className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
                  <Filter className="h-3.5 w-3.5" />
                  Filtros aplicados
                </div>
                <div className="flex flex-wrap gap-2">
                  {filtersApplied.map((filter) => (
                    <Badge key={`${filter.label}-${filter.value}`} variant="neutral">
                      {filter.label}: {filter.value}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div className="flex-1 min-h-0 px-4 py-4 md:px-6 md:py-5">
            <div className="mb-3 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
              <Database className="h-3.5 w-3.5" />
              Tabla principal
            </div>
            <AgGridWrapper<T>
              rowData={detailRows}
              columnDefs={detailColumns}
              height="100%"
              className="h-full"
              exportFilename={exportFilename}
              pageSize={12}
            />
          </div>
        </div>
      </div>
    </div>,
    document.body
  )
}
