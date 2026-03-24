'use client'

import { useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { AgGridWrapper } from '@/components/tables/AgGrid'
import { formatDate, formatNumber, formatCurrency } from '@/lib/formatters'
import { Badge } from '@/components/ui/Badge'
import type { Lote } from '@/types/agricola'

interface LotesTableProps {
  lotes?: Lote[]
  loading?: boolean
}

const estadoConfig: Record<string, { label: string; variant: 'success' | 'warning' | 'info' | 'neutral' }> = {
  sembrado: { label: 'Sembrado', variant: 'info' },
  cosechado: { label: 'Cosechado', variant: 'success' },
  en_labores: { label: 'En labores', variant: 'warning' },
  barbecho: { label: 'Barbecho', variant: 'neutral' },
}

export function LotesTable({ lotes, loading }: LotesTableProps) {
  const columnDefs = useMemo<ColDef<Lote>[]>(() => [
    {
      field: 'nombre',
      headerName: 'Lote',
      flex: 1.5,
      minWidth: 140,
      cellStyle: { fontWeight: '500' },
    },
    {
      field: 'establecimiento',
      headerName: 'Establecimiento',
      flex: 1.5,
      minWidth: 130,
    },
    {
      field: 'cultivo',
      headerName: 'Cultivo',
      flex: 1,
      minWidth: 100,
    },
    {
      field: 'hectareas',
      headerName: 'Ha',
      flex: 0.7,
      minWidth: 80,
      valueFormatter: (p) => p.value != null ? formatNumber(p.value, 0) : '—',
      type: 'numericColumn',
    },
    {
      field: 'estado',
      headerName: 'Estado',
      flex: 1,
      minWidth: 110,
      cellRenderer: (p: { value: string }) => {
        const cfg = estadoConfig[p.value] || { label: p.value, variant: 'neutral' }
        return <Badge variant={cfg.variant}>{cfg.label}</Badge>
      },
    },
    {
      field: 'fecha_siembra',
      headerName: 'F. Siembra',
      flex: 1,
      minWidth: 110,
      valueFormatter: (p) => p.value ? formatDate(p.value) : '—',
    },
    {
      field: 'rendimiento_tn_ha',
      headerName: 'Rend. (tn/ha)',
      flex: 1,
      minWidth: 110,
      valueFormatter: (p) => p.value != null ? formatNumber(p.value, 2) : '—',
      type: 'numericColumn',
    },
    {
      field: 'costo_por_ha',
      headerName: 'Costo/Ha',
      flex: 1,
      minWidth: 110,
      valueFormatter: (p) => p.value != null ? formatCurrency(p.value) : '—',
      type: 'numericColumn',
    },
  ], [])

  return (
    <div className="rounded border border-border bg-surface p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text">Lotes</h3>
        {lotes && (
          <span className="text-xs text-text-muted">{lotes.length} lotes</span>
        )}
      </div>
      <div className="md:hidden">
        <div className="space-y-3">
          {(lotes || []).map((lote) => {
            const estado = estadoConfig[lote.estado] || { label: lote.estado, variant: 'neutral' as const }
            return (
              <div key={lote.id} className="rounded-xl border border-border bg-surface-2 p-4">
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-text">{lote.nombre}</p>
                    <p className="text-xs text-text-muted">{lote.establecimiento}</p>
                  </div>
                  <Badge variant={estado.variant}>{estado.label}</Badge>
                </div>
                <div className="grid grid-cols-2 gap-3 text-xs text-text-muted">
                  <div>
                    <p className="text-text-subtle">Cultivo</p>
                    <p className="mt-1 font-medium text-text">{lote.cultivo}</p>
                  </div>
                  <div>
                    <p className="text-text-subtle">Superficie</p>
                    <p className="mt-1 font-medium text-text">{formatNumber(lote.hectareas, 0)} ha</p>
                  </div>
                  <div>
                    <p className="text-text-subtle">Siembra</p>
                    <p className="mt-1 font-medium text-text">{lote.fecha_siembra ? formatDate(lote.fecha_siembra) : '—'}</p>
                  </div>
                  <div>
                    <p className="text-text-subtle">Rendimiento</p>
                    <p className="mt-1 font-medium text-text">
                      {lote.rendimiento_tn_ha != null ? `${formatNumber(lote.rendimiento_tn_ha, 2)} tn/ha` : '—'}
                    </p>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>
      <div className="hidden md:block">
        <AgGridWrapper<Lote>
          rowData={lotes || []}
          columnDefs={columnDefs}
          loading={loading}
          height={400}
          exportFilename="lotes-agricola"
          pageSize={15}
        />
      </div>
    </div>
  )
}
