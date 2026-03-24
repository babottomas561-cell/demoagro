'use client'

import { useMemo } from 'react'
import { Package, DollarSign, AlertTriangle } from 'lucide-react'
import type { ColDef } from 'ag-grid-community'
import { AgGridWrapper } from '@/components/tables/AgGrid'
import { Badge } from '@/components/ui/Badge'
import { KPICard } from '@/components/ui/KPICard'
import { formatCurrency, formatToneladas, formatNumber } from '@/lib/formatters'
import type { StockData, StockItem } from '@/types/stock'

interface StockTableProps {
  data?: StockData
  loading?: boolean
}

const alertaConfig = {
  verde: { label: 'Libre', variant: 'success' as const, class: 'text-accent' },
  amarillo: { label: 'Ajustado', variant: 'warning' as const, class: 'text-warning' },
  rojo: { label: 'Crítico', variant: 'danger' as const, class: 'text-danger' },
}

export function StockTable({ data, loading }: StockTableProps) {
  const columnDefs = useMemo<ColDef<StockItem>[]>(() => [
    {
      field: 'cultivo',
      headerName: 'Cultivo',
      flex: 1,
      minWidth: 100,
      cellStyle: { fontWeight: '500' },
    },
    {
      field: 'establecimiento',
      headerName: 'Establecimiento',
      flex: 1.5,
      minWidth: 140,
    },
    {
      field: 'stock_disponible_tn',
      headerName: 'Stock Total (tn)',
      flex: 1,
      minWidth: 120,
      valueFormatter: (p) => p.value != null ? formatNumber(p.value, 0) : '—',
      type: 'numericColumn',
    },
    {
      field: 'vendido_tn',
      headerName: 'Vendido (tn)',
      flex: 1,
      minWidth: 110,
      valueFormatter: (p) => p.value != null ? formatNumber(p.value, 0) : '—',
      type: 'numericColumn',
    },
    {
      field: 'comprometido_tn',
      headerName: 'Comprometido (tn)',
      flex: 1,
      minWidth: 140,
      valueFormatter: (p) => p.value != null ? formatNumber(p.value, 0) : '—',
      type: 'numericColumn',
    },
    {
      field: 'libre_tn',
      headerName: 'Libre (tn)',
      flex: 1,
      minWidth: 100,
      valueFormatter: (p) => p.value != null ? formatNumber(p.value, 0) : '—',
      type: 'numericColumn',
    },
    {
      field: 'libre_pct',
      headerName: '% Libre',
      flex: 0.8,
      minWidth: 90,
      cellRenderer: (p: { value: number; data: StockItem }) => {
        const cfg = alertaConfig[p.data?.alerta || 'verde']
        return <span className={`${cfg.class} font-medium tabular-nums`}>{formatNumber(p.value ?? 0, 0)}%</span>
      },
    },
    {
      field: 'valor_estimado',
      headerName: 'Valor Est.',
      flex: 1,
      minWidth: 110,
      valueFormatter: (p) => p.value != null ? formatCurrency(p.value) : '—',
      type: 'numericColumn',
    },
  ], [])

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <KPICard
          title="Stock Total"
          value={data ? formatToneladas(data.summary.stock_total_tn) : '—'}
          icon={Package}
          loading={loading}
          trend="neutral"
        />
        <KPICard
          title="Valor Stock"
          value={data ? formatCurrency(data.summary.valor_stock) : '—'}
          icon={DollarSign}
          loading={loading}
          trend="neutral"
        />
        <KPICard
          title="Alertas Activas"
          value={data?.summary.unidades_alerta ?? '—'}
          icon={AlertTriangle}
          loading={loading}
          trend={data && data.summary.unidades_alerta > 0 ? 'down' : 'up'}
          invertColor
          description="Unidades con stock bajo"
        />
      </div>

      {/* Table */}
      <div className="rounded border border-border bg-surface p-5">
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="text-sm font-semibold text-text">Inventario Detallado</h3>
          <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
            <Badge variant="success">Libre</Badge>
            <Badge variant="warning">Ajustado</Badge>
            <Badge variant="danger">Crítico</Badge>
          </div>
        </div>
        <div className="space-y-3 md:hidden">
          {(data?.items || []).map((item) => (
            <div key={item.id} className="rounded-xl border border-border bg-surface-2 p-4">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-text">{item.cultivo}</p>
                  <p className="text-xs text-text-muted">{item.establecimiento}</p>
                </div>
                <Badge variant={alertaConfig[item.alerta].variant}>{alertaConfig[item.alerta].label}</Badge>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs text-text-muted">
                <div>
                  <p className="text-text-subtle">Stock disponible</p>
                  <p className="mt-1 font-medium text-text">{formatNumber(item.stock_disponible_tn, 0)} tn</p>
                </div>
                <div>
                  <p className="text-text-subtle">Libre</p>
                  <p className="mt-1 font-medium text-text">{formatNumber(item.libre_tn, 0)} tn</p>
                </div>
                <div>
                  <p className="text-text-subtle">% libre</p>
                  <p className="mt-1 font-medium text-text">{formatNumber(item.libre_pct, 0)}%</p>
                </div>
                <div>
                  <p className="text-text-subtle">Valor estimado</p>
                  <p className="mt-1 font-medium text-text">{formatCurrency(item.valor_estimado)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="hidden md:block">
          <AgGridWrapper<StockItem>
            rowData={data?.items || []}
            columnDefs={columnDefs}
            loading={loading}
            height={400}
            exportFilename="stock-inventario"
          />
        </div>
      </div>
    </div>
  )
}
