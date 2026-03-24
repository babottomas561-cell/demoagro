'use client'

import { useMemo, useState } from 'react'
import type { KeyboardEvent, ReactNode } from 'react'
import type { ColDef } from 'ag-grid-community'
import { ChevronRight, Eye } from 'lucide-react'
import clsx from 'clsx'
import { Badge } from '@/components/ui/Badge'
import { DataSourceTag } from '@/components/ui/DataSourceTag'
import { DrillDownModal, type DrillDownSummaryItem } from '@/components/drilldown/DrillDownModal'
import type { DrillDownFilterChip } from '@/lib/drilldown'

interface ChartWithDrillDownProps<T> {
  children: ReactNode
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
  footerNote?: string
  className?: string
  contentClassName?: string
  showInlineMetadata?: boolean
  openOnContentClick?: boolean
}

export function ChartWithDrillDown<T>({
  children,
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
  exportFilename,
  detailLabel,
  footerNote,
  className,
  contentClassName,
  showInlineMetadata = false,
  openOnContentClick = true,
}: ChartWithDrillDownProps<T>) {
  const [open, setOpen] = useState(false)
  const canOpen = useMemo(
    () => detailRows.length > 0 || Boolean(formula || source || filtersApplied?.length),
    [detailRows.length, filtersApplied?.length, formula, source]
  )

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!canOpen) return
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault()
      setOpen(true)
    }
  }

  return (
    <div className={clsx('space-y-3', className)}>
      <div
        role={canOpen && openOnContentClick ? 'button' : undefined}
        tabIndex={canOpen && openOnContentClick ? 0 : undefined}
        onClick={canOpen && openOnContentClick ? () => setOpen(true) : undefined}
        onKeyDown={openOnContentClick ? handleKeyDown : undefined}
        className={clsx(
          'rounded-2xl',
          canOpen && openOnContentClick && 'cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          contentClassName
        )}
      >
        {children}
      </div>

      <div className="flex flex-col gap-2 border-t border-border pt-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="neutral">{detailRows.length} registros</Badge>
          {showInlineMetadata && source && (
            <div className="rounded-full border border-border bg-surface px-2.5 py-1">
              <DataSourceTag fuente={source} ultimaActualizacion={lastUpdated} />
            </div>
          )}
          {footerNote && <p className="text-xs text-text-muted">{footerNote}</p>}
        </div>

        <button
          type="button"
          disabled={!canOpen}
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-text-muted transition-colors hover:text-text disabled:cursor-not-allowed disabled:text-text-subtle"
        >
          <Eye className="h-3.5 w-3.5" />
          Ver informe
          <ChevronRight className="h-3.5 w-3.5" />
        </button>
      </div>

      <DrillDownModal<T>
        open={open}
        onClose={() => setOpen(false)}
        title={title}
        description={description}
        formula={formula}
        summaryItems={summaryItems}
        contextText={contextText}
        source={source}
        lastUpdated={lastUpdated}
        filtersApplied={filtersApplied}
        detailRows={detailRows}
        detailColumns={detailColumns}
        exportFilename={exportFilename}
        detailLabel={detailLabel}
      />
    </div>
  )
}
