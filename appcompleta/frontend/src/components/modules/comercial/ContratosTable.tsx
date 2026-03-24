'use client'

import { useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { AgGridWrapper } from '@/components/tables/AgGrid'
import { formatDate, formatCurrency, formatNumber } from '@/lib/formatters'
import { Badge } from '@/components/ui/Badge'
import type { OperacionComercial } from '@/types/comercial'

interface ContratosTableProps {
  operaciones?: OperacionComercial[]
  loading?: boolean
}

const estadoLabels: Record<string, string> = {
  confirmada: 'Confirmada',
  pendiente: 'Pendiente',
  entregada: 'Entregada',
  cancelada: 'Cancelada',
}

const estadoVariant: Record<string, 'success' | 'warning' | 'info' | 'danger'> = {
  confirmada: 'success',
  pendiente: 'warning',
  entregada: 'info',
  cancelada: 'danger',
}

export function ContratosTable({ operaciones, loading }: ContratosTableProps) {
  const columnDefs = useMemo<ColDef<OperacionComercial>[]>(() => [
    {
      field: 'fecha',
      headerName: 'Fecha',
      flex: 0.9,
      minWidth: 100,
      valueFormatter: (p) => p.value ? formatDate(p.value) : '—',
    },
    {
      field: 'cultivo',
      headerName: 'Cultivo',
      flex: 0.8,
      minWidth: 90,
    },
    {
      field: 'cliente',
      headerName: 'Cliente',
      flex: 1.5,
      minWidth: 150,
    },
    {
      field: 'tipo_contrato',
      headerName: 'Tipo',
      flex: 0.9,
      minWidth: 90,
    },
    {
      field: 'volumen_tn',
      headerName: 'Volumen (tn)',
      flex: 1,
      minWidth: 110,
      valueFormatter: (p) => p.value != null ? formatNumber(p.value, 0) : '—',
      type: 'numericColumn',
    },
    {
      field: 'precio_ars_tn',
      headerName: 'Precio ARS/tn',
      flex: 1,
      minWidth: 120,
      valueFormatter: (p) => p.value != null ? formatCurrency(p.value) : '—',
      type: 'numericColumn',
    },
    {
      field: 'valor_total_ars',
      headerName: 'Valor Total',
      flex: 1.1,
      minWidth: 120,
      valueFormatter: (p) => p.value != null ? formatCurrency(p.value) : '—',
      type: 'numericColumn',
    },
    {
      field: 'estado',
      headerName: 'Estado',
      flex: 1,
      minWidth: 100,
      cellRenderer: (p: { value: string }) => {
        const label = estadoLabels[p.value] || p.value
        const variant = estadoVariant[p.value] || 'info'
        return <Badge variant={variant}>{label}</Badge>
      },
    },
  ], [])

  return (
    <div className="rounded border border-border bg-surface p-5">
      <div className="mb-4 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-text">Operaciones Comerciales</h3>
        {operaciones && (
          <span className="text-xs text-text-muted">{operaciones.length} operaciones</span>
        )}
      </div>
      <div className="space-y-3 md:hidden">
        {(operaciones || []).map((operacion) => (
          <div key={operacion.id} className="rounded-xl border border-border bg-surface-2 p-4">
            <div className="mb-3 flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-semibold text-text">{operacion.cliente}</p>
                <p className="text-xs text-text-muted">
                  {operacion.cultivo} · {operacion.fecha ? formatDate(operacion.fecha) : '—'}
                </p>
              </div>
              <Badge variant={estadoVariant[operacion.estado] || 'info'}>
                {estadoLabels[operacion.estado] || operacion.estado}
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-3 text-xs text-text-muted">
              <div>
                <p className="text-text-subtle">Tipo</p>
                <p className="mt-1 font-medium text-text">{operacion.tipo_contrato}</p>
              </div>
              <div>
                <p className="text-text-subtle">Volumen</p>
                <p className="mt-1 font-medium text-text">{formatNumber(operacion.volumen_tn, 0)} tn</p>
              </div>
              <div>
                <p className="text-text-subtle">Precio</p>
                <p className="mt-1 font-medium text-text">{formatCurrency(operacion.precio_ars_tn)}</p>
              </div>
              <div>
                <p className="text-text-subtle">Valor total</p>
                <p className="mt-1 font-medium text-text">{formatCurrency(operacion.valor_total_ars)}</p>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="hidden md:block">
        <AgGridWrapper<OperacionComercial>
          rowData={operaciones || []}
          columnDefs={columnDefs}
          loading={loading}
          height={400}
          exportFilename="operaciones-comerciales"
          pageSize={15}
        />
      </div>
    </div>
  )
}
