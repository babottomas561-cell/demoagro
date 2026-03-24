'use client'

import { AreaChart } from '@/components/charts/AreaChart'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { DataSourceTag } from '@/components/ui/DataSourceTag'
import { CHART_COLORS } from '@/lib/constants'
import type { FlujoCajaMes } from '@/types/finanzas'

interface FlujoCajaChartProps {
  datos?: FlujoCajaMes[]
  loading?: boolean
  ultimaActualizacion?: string
}

export function FlujoCajaChart({ datos, loading, ultimaActualizacion }: FlujoCajaChartProps) {
  const reales = datos?.filter((d) => !d.proyectado) ?? []
  const proyectados = datos?.filter((d) => d.proyectado) ?? []

  return (
    <div className="rounded border border-border bg-surface p-5">
      <div className="mb-1 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h3 className="text-sm font-semibold text-text">Flujo de Caja — 12 meses</h3>
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <span className="h-0.5 w-4 rounded-full" style={{ background: CHART_COLORS.ingresos }} />
            Ingresos
          </div>
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <span className="h-0.5 w-4 rounded-full" style={{ background: CHART_COLORS.egresos }} />
            Egresos
          </div>
          <div className="flex items-center gap-1.5 text-xs text-text-muted">
            <span className="h-0.5 w-4 rounded-full border-t-2 border-dashed" style={{ borderColor: CHART_COLORS.ingresos }} />
            Proyectado
          </div>
        </div>
      </div>

      {ultimaActualizacion && (
        <DataSourceTag fuente="Sistema ERP" ultimaActualizacion={ultimaActualizacion} className="mb-3" />
      )}

      {loading ? (
        <SkeletonBlock className="h-72 w-full" />
      ) : datos && datos.length > 0 ? (
        <AreaChart
          data={[
            {
              x: [...reales.map((d) => d.mes), ...proyectados.map((d) => d.mes)],
              y: [...reales.map((d) => d.ingresos), ...proyectados.map((d) => d.ingresos)],
              name: 'Ingresos',
              color: CHART_COLORS.ingresos,
            },
            {
              x: [...reales.map((d) => d.mes), ...proyectados.map((d) => d.mes)],
              y: [...reales.map((d) => d.egresos), ...proyectados.map((d) => d.egresos)],
              name: 'Egresos',
              color: CHART_COLORS.egresos,
            },
            {
              x: proyectados.map((d) => d.mes),
              y: proyectados.map((d) => d.neto),
              name: 'Neto proyectado',
              color: '#6b8f7a',
              dashed: true,
            },
          ]}
          height={280}
          yAxisTitle="ARS"
          stacked={false}
        />
      ) : (
        <div className="flex h-72 items-center justify-center text-sm text-text-subtle">
          Sin datos de flujo de caja
        </div>
      )}
    </div>
  )
}
