'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { AgGridReact } from 'ag-grid-react'
import type { ColDef, GridReadyEvent } from 'ag-grid-community'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-alpine.css'
import { Download, Search } from 'lucide-react'
import clsx from 'clsx'

interface AgGridWrapperProps<T> {
  rowData: T[]
  columnDefs: ColDef[]
  height?: number | string
  loading?: boolean
  exportFilename?: string
  className?: string
  onRowClicked?: (row: T) => void
  pagination?: boolean
  pageSize?: number
}

export function AgGridWrapper<T>({
  rowData,
  columnDefs,
  height = 420,
  loading,
  exportFilename = 'export',
  className,
  onRowClicked,
  pagination = true,
  pageSize = 20,
}: AgGridWrapperProps<T>) {
  const gridRef = useRef<AgGridReact<T>>(null)
  const [quickFilter, setQuickFilter] = useState('')

  const onGridReady = useCallback((params: GridReadyEvent) => {
    params.api.setGridOption('quickFilterText', quickFilter)
    requestAnimationFrame(() => {
      params.api.sizeColumnsToFit()
    })
  }, [quickFilter])

  const handleExport = useCallback(() => {
    gridRef.current?.api?.exportDataAsCsv({
      fileName: `${exportFilename}.csv`,
    })
  }, [exportFilename])

  const defaultColDef: ColDef = {
    sortable: true,
    filter: true,
    resizable: true,
    suppressMovable: false,
    cellStyle: { display: 'flex', alignItems: 'center' },
  }

  useEffect(() => {
    const api = gridRef.current?.api
    if (!api) return

    api.setGridOption('quickFilterText', quickFilter)

    if (loading) {
      api.showLoadingOverlay()
      return
    }

    if (!rowData.length) {
      api.showNoRowsOverlay()
      return
    }

    api.hideOverlay()
  }, [loading, quickFilter, rowData])

  return (
    <div className={clsx('flex h-full flex-col gap-2', className)}>
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <label className="relative w-full sm:max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-subtle" />
          <input
            value={quickFilter}
            onChange={(event) => setQuickFilter(event.target.value)}
            placeholder="Buscar en tabla..."
            className="h-9 w-full rounded-lg border border-border bg-surface px-9 text-sm text-text outline-none transition-all placeholder:text-text-subtle focus:border-primary-300 focus:ring-2 focus:ring-primary-100"
          />
        </label>

        <button
          onClick={handleExport}
          className="flex items-center justify-center gap-1.5 rounded border border-border bg-surface-2 px-3 py-2 text-xs text-text-muted transition-all hover:border-border-strong hover:text-text"
        >
          <Download className="h-3.5 w-3.5" />
          Exportar CSV
        </button>
      </div>

      <div
        className="ag-theme-alpine ag-theme-agro min-h-0 flex-1"
        style={{ height, width: '100%' }}
      >
        <AgGridReact<T>
          ref={gridRef}
          rowData={rowData}
          columnDefs={columnDefs}
          defaultColDef={defaultColDef}
          onGridReady={onGridReady}
          pagination={pagination}
          paginationPageSize={pageSize}
          animateRows
          suppressCellFocus
          onRowClicked={onRowClicked ? (e) => e.data && onRowClicked(e.data) : undefined}
          overlayLoadingTemplate='<span class="text-text-muted text-sm">Cargando datos...</span>'
          overlayNoRowsTemplate='<span class="text-text-muted text-sm">Sin datos disponibles</span>'
        />
      </div>
    </div>
  )
}
