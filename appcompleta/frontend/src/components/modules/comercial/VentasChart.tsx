'use client'

import { useState } from 'react'
import { LineChart } from '@/components/charts/LineChart'
import { BarChart } from '@/components/charts/BarChart'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { CHART_COLORS } from '@/lib/constants'
import type { PrecioCultivo, VentaCliente } from '@/types/comercial'

interface VentasChartProps {
  precios?: PrecioCultivo[]
  ventasCliente?: VentaCliente[]
  loading?: boolean
}

type Tab = 'precios' | 'clientes'

export function VentasChart({ precios, ventasCliente, loading }: VentasChartProps) {
  const [tab, setTab] = useState<Tab>('precios')

  return (
    <div className="rounded border border-border bg-surface p-5">
      <div className="mb-4 flex items-center gap-4">
        <h3 className="text-sm font-semibold text-text">Análisis Comercial</h3>
        <div className="flex gap-1 rounded border border-border bg-surface-2 p-0.5">
          {(['precios', 'clientes'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`rounded px-3 py-1 text-xs font-medium transition-all ${
                tab === t
                  ? 'bg-surface-3 text-text'
                  : 'text-text-muted hover:text-text'
              }`}
            >
              {t === 'precios' ? 'Precios por Cultivo' : 'Ventas por Cliente'}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <SkeletonBlock className="h-64 w-full" />
      ) : tab === 'precios' && precios && precios.length > 0 ? (
        <LineChart
          data={[
            {
              x: precios.map((p) => p.fecha),
              y: precios.map((p) => p.soja ?? 0),
              name: 'Soja',
              color: CHART_COLORS.soja,
            },
            {
              x: precios.map((p) => p.fecha),
              y: precios.map((p) => p.maiz ?? 0),
              name: 'Maíz',
              color: CHART_COLORS.maiz,
            },
            {
              x: precios.map((p) => p.fecha),
              y: precios.map((p) => p.trigo ?? 0),
              name: 'Trigo',
              color: CHART_COLORS.trigo,
            },
          ]}
          height={280}
          yAxisTitle="ARS/tn"
        />
      ) : tab === 'clientes' && ventasCliente && ventasCliente.length > 0 ? (
        <BarChart
          data={[{
            x: ventasCliente.map((v) => v.cliente),
            y: ventasCliente.map((v) => v.valor),
            name: 'Ventas',
            color: '#4ade80',
          }]}
          height={280}
          yAxisTitle="ARS"
        />
      ) : (
        <div className="flex h-64 items-center justify-center text-sm text-text-subtle">
          Sin datos disponibles
        </div>
      )}
    </div>
  )
}
