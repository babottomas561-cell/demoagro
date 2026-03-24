'use client'

import { useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import type { ColDef } from 'ag-grid-community'
import { Eye } from 'lucide-react'
import clsx from 'clsx'
import { Badge } from '@/components/ui/Badge'
import { DrillDownModal, type DrillDownSummaryItem } from '@/components/drilldown/DrillDownModal'
import type { DrillDownFilterChip } from '@/lib/drilldown'

interface MetricWithDrillDownProps<T> {
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
  className?: string
}

export function MetricWithDrillDown<T>({
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
  className,
}: MetricWithDrillDownProps<T>) {
  const [open, setOpen] = useState(false)
  const canOpen = useMemo(
    () => detailRows.length > 0 || Boolean(formula || source || filtersApplied?.length),
    [detailRows.length, filtersApplied?.length, formula, source]
  )

  return (
    <div className={clsx('flex h-full flex-col space-y-2', className)}>
      <button
        type="button"
        disabled={!canOpen}
        onClick={() => setOpen(true)}
        className={clsx(
          'block h-full w-full flex-1 rounded-[1.4rem] text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-300 focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          canOpen ? 'cursor-pointer' : 'cursor-default'
        )}
      >
        {children}
      </button>

      <div className="flex items-center justify-between gap-3 px-1">
        <Badge variant="neutral">{detailRows.length} registros</Badge>
        <button
          type="button"
          disabled={!canOpen}
          onClick={() => setOpen(true)}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-primary-700 transition-colors hover:text-primary-800 disabled:cursor-not-allowed disabled:text-text-subtle"
        >
          <Eye className="h-3.5 w-3.5" />
          Ver informe
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
