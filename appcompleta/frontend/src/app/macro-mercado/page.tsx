'use client'

import { Suspense, useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { TrendingUp } from 'lucide-react'
import { BarChart } from '@/components/charts/BarChart'
import { LineChart } from '@/components/charts/LineChart'
import { ChartWithDrillDown } from '@/components/drilldown/ChartWithDrillDown'
import { TimeRangeSelector } from '@/components/filters/TimeRangeSelector'
import { MiniPieKpiCard } from '@/components/simple/MiniPieKpiCard'
import { SimpleChartCard } from '@/components/simple/SimpleChartCard'
import { OperationalFocusAlert } from '@/components/simple/OperationalFocusAlert'
import { SimpleKpiCard } from '@/components/simple/SimpleKpiCard'
import { Alert } from '@/components/ui/Alert'
import { DataSourceTag } from '@/components/ui/DataSourceTag'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { DashboardLead } from '@/components/dashboard-v3/DashboardLead'
import { useExecutiveScope } from '@/hooks/useExecutiveScope'
import { useMacroMercado } from '@/hooks/useMacroMercado'
import { usePageFilters } from '@/hooks/usePageFilters'
import { useTimeRangeQuery } from '@/hooks/useTimeRangeQuery'
import { buildAppliedFilters } from '@/lib/drilldown'
import { formatNumber, formatPercent } from '@/lib/formatters'
import { ensureMinimumSeriesPoints, filterSeriesByRange } from '@/lib/time-series'
import type { MacroMercadoRow, MacroSerieRow, MacroVariableRow } from '@/types/lemon-macro'

const SERIES_COLUMNS: ColDef<MacroSerieRow>[] = [
  { field: 'fecha', headerName: 'Semana', flex: 1.1 },
  { field: 'tc_exportacion', headerName: 'TC exportación', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 2) },
  { field: 'precio_exportacion_usd_tn', headerName: 'Precio export.', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}` },
  { field: 'flete_usd_tn', headerName: 'Flete', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}` },
]

const MARKET_COLUMNS: ColDef<MacroMercadoRow>[] = [
  { field: 'mercado', headerName: 'Mercado', flex: 1.1 },
  { field: 'precio_exportacion_usd_tn', headerName: 'Precio', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}` },
  { field: 'flete_usd_tn', headerName: 'Flete', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}` },
  { field: 'margen_bruto_usd_tn', headerName: 'Margen', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}` },
]

const VARIABLE_COLUMNS: ColDef<MacroVariableRow>[] = [
  { field: 'variable', headerName: 'Variable', flex: 1.2 },
  { field: 'valor', headerName: 'Valor', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 2) },
]

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <SkeletonBlock className="h-24 w-full" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <SkeletonBlock key={index} className="h-32 w-full" />
        ))}
      </div>
      <SkeletonBlock className="h-[26rem] w-full" />
      <div className="grid gap-6 xl:grid-cols-2">
        <SkeletonBlock className="h-[22rem] w-full" />
        <SkeletonBlock className="h-[22rem] w-full" />
      </div>
    </div>
  )
}

function toneFromDelta(value: number) {
  if (value < 0) return 'danger' as const
  if (value > 0) return 'positive' as const
  return 'neutral' as const
}

function MacroMercadoPageContent() {
  const filters = usePageFilters([
    'empresa_id',
    'campania_id',
    'mercado_id',
  ])
  const { data, error, isLoading } = useMacroMercado(filters)
  const executiveScope = useExecutiveScope(filters)
  const appliedFilters = useMemo(() => buildAppliedFilters(filters), [filters])
  const { range, setRange } = useTimeRangeQuery('90D')

  const seriesRows = useMemo(() => {
    const allRows = data?.series.macro_semanal || []
    return ensureMinimumSeriesPoints(
      filterSeriesByRange(allRows, range, (item) => item.fecha),
      allRows,
      5
    )
  }, [data?.series.macro_semanal, range])

  if (error && !data) {
    return (
      <Alert variant="danger" title="No se pudo cargar Macro / Mercado">
        Revisá las series externas persistidas y el contexto de exportación limonero.
      </Alert>
    )
  }

  if (isLoading || !data) {
    return <PageSkeleton />
  }

  const leadMarket = data.breakdown.mercados[0]
  const focusTone =
    data.summary.precio_exportacion_delta_pct < 0 && data.summary.costo_flete_delta_pct > 0
      ? 'danger'
      : data.summary.inflacion_mensual_pct > 5.5 ||
          data.summary.precio_exportacion_delta_pct < 0 ||
          data.summary.costo_flete_delta_pct > 0
        ? 'warning'
        : 'success'
  const focusBullets = [
    `El precio exportado está en USD ${formatNumber(data.summary.precio_exportacion_usd_tn, 2)}/tn contra un flete de USD ${formatNumber(data.summary.costo_flete_usd_tn, 2)}/tn.`,
    leadMarket
      ? `${leadMarket.mercado} deja hoy el mejor margen bruto con USD ${formatNumber(leadMarket.margen_bruto_usd_tn, 2)}/tn.`
      : '',
    `La inflación mensual se ubica en ${formatNumber(data.summary.inflacion_mensual_pct, 1)}% y ${data.summary.precio_exportacion_delta_pct < 0 || data.summary.costo_flete_delta_pct > 0 ? 'presiona' : 'acompaña'} la rentabilidad exportadora.`,
  ]

  return (
    <div className="space-y-6">
      <DashboardLead
        title="Macro / Mercado"
        description="Contexto semanal para ver si tipo de cambio, precio y flete ayudan o presionan el negocio."
        icon={TrendingUp}
        label="Panel operativo diario"
        scopeLabel={executiveScope.label}
        scopeBadges={executiveScope.badges}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SimpleKpiCard
          label="Tipo de cambio"
          value={formatNumber(data.summary.tc_exportacion, 2)}
          delta={formatPercent(data.summary.tc_delta_pct)}
          detail={data.summary.tc_detail}
          tone={toneFromDelta(data.summary.tc_delta_pct)}
        />
        <SimpleKpiCard
          label="Inflación"
          value={`${formatNumber(data.summary.inflacion_mensual_pct, 1)}%`}
          delta={formatPercent(data.summary.inflacion_delta_pct)}
          detail={data.summary.inflacion_detail}
          tone={data.summary.inflacion_mensual_pct > 5.5 ? 'warning' : 'neutral'}
        />
        <SimpleKpiCard
          label="Precio exportacion"
          value={`USD ${formatNumber(data.summary.precio_exportacion_usd_tn, 2)}/tn`}
          delta={formatPercent(data.summary.precio_exportacion_delta_pct)}
          detail={data.summary.precio_exportacion_detail}
          tone={toneFromDelta(data.summary.precio_exportacion_delta_pct)}
        />
        <SimpleKpiCard
          label="Jugo concentrado"
          value={`USD ${formatNumber(data.summary.precio_jugo_usd_tn, 0)}/tn`}
          delta={data.summary.precio_jugo_delta_pct !== 0 ? `${data.summary.precio_jugo_delta_pct > 0 ? '+' : ''}${formatNumber(data.summary.precio_jugo_delta_pct, 1)}%` : 'Sin variación'}
          detail={data.summary.precio_jugo_detail}
          tone={data.summary.precio_jugo_usd_tn >= 2000 ? 'positive' : data.summary.precio_jugo_usd_tn >= 1600 ? 'warning' : 'danger'}
        />
      </div>

      {/* KPI con torta — mercados, precio vs flete, fresco vs jugo, atractivo */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniPieKpiCard
          label="Margen por mercado"
          centerValue={`USD ${formatNumber(data.breakdown.mercados[0]?.margen_bruto_usd_tn || 0, 0)}`}
          centerSub={data.breakdown.mercados[0]?.mercado || ''}
          slices={(() => {
            const positivos = data.breakdown.mercados.filter((r) => r.margen_bruto_usd_tn > 0)
            if (!positivos.length) return [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]
            const total = positivos.reduce((s, r) => s + r.margen_bruto_usd_tn, 0)
            return positivos.slice(0, 4).map((r) => ({
              label: r.mercado,
              value: total > 0 ? Math.round((r.margen_bruto_usd_tn / total) * 100) : 0,
            }))
          })()}
          tone={!data.breakdown.mercados.length ? 'neutral' : data.breakdown.mercados[0].margen_bruto_usd_tn > 0 ? 'positive' : 'danger'}
        />
        <MiniPieKpiCard
          label="Precio vs flete"
          centerValue={`${formatNumber(
            data.breakdown.mercados[0]
              ? Math.max(0, ((data.breakdown.mercados[0].precio_exportacion_usd_tn - data.breakdown.mercados[0].flete_usd_tn) / Math.max(1, data.breakdown.mercados[0].precio_exportacion_usd_tn)) * 100)
              : 0,
            0
          )}%`}
          centerSub="Neto"
          slices={(() => {
            const lead = data.breakdown.mercados[0]
            if (!lead) return [{ label: 'Sin datos', value: 100 }]
            const flete = lead.flete_usd_tn
            const neto = Math.max(0, lead.precio_exportacion_usd_tn - flete)
            const total = flete + neto
            return [
              { label: 'Precio neto', value: total > 0 ? Math.round((neto / total) * 100) : 0, color: '#30945a' },
              { label: 'Flete', value: total > 0 ? Math.round((flete / total) * 100) : 0, color: '#cf6e63' },
            ]
          })()}
          tone={data.summary.costo_flete_delta_pct > 0 ? 'danger' : 'neutral'}
        />
        <MiniPieKpiCard
          label="Fresco vs jugo"
          centerValue={`USD ${formatNumber(data.summary.precio_exportacion_usd_tn, 0)}/tn`}
          centerSub="Fresco export."
          slices={(() => {
            const fresco = data.summary.precio_exportacion_usd_tn
            const jugo = data.summary.precio_jugo_usd_tn
            const total = fresco + jugo
            return [
              { label: 'Fresco', value: total > 0 ? Math.round((fresco / total) * 100) : 0, color: '#30945a' },
              { label: 'Jugo', value: total > 0 ? Math.round((jugo / total) * 100) : 0, color: '#7d8f76' },
            ]
          })()}
          tone={data.summary.precio_exportacion_usd_tn >= data.summary.precio_jugo_usd_tn ? 'positive' : 'warning'}
        />
        <MiniPieKpiCard
          label="Mercados atractivos"
          centerValue={`${data.breakdown.mercados.filter((r) => r.margen_bruto_usd_tn > 0).length}`}
          centerSub="Con margen positivo"
          slices={[
            { label: 'Margen positivo', value: data.breakdown.mercados.filter((r) => r.margen_bruto_usd_tn > 0).length, color: '#30945a' },
            { label: 'Margen negativo', value: data.breakdown.mercados.filter((r) => r.margen_bruto_usd_tn <= 0).length, color: '#cf6e63' },
          ]}
          tone={!data.breakdown.mercados.length ? 'neutral' : data.breakdown.mercados.every((r) => r.margen_bruto_usd_tn > 0) ? 'positive' : data.breakdown.mercados.some((r) => r.margen_bruto_usd_tn > 0) ? 'warning' : 'danger'}
        />
      </div>

      <OperationalFocusAlert title="Foco operativo del dia" tone={focusTone} bullets={focusBullets} />

      <SimpleChartCard
        title="Precio exportacion semanal"
        description="Serie simple para ver si el mercado mejora o pierde atractivo."
        actions={
          <>
            <TimeRangeSelector value={range} onChange={setRange} />
            <DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />
          </>
        }
      >
        <ChartWithDrillDown<MacroSerieRow>
          title="Precio exportacion semanal"
          description="Serie semanal de precio exportado."
          formula="precio promedio exportado por semana"
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={seriesRows}
          detailColumns={SERIES_COLUMNS}
          exportFilename="macro-precio-tiempo"
          contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
        >
          <LineChart
            height={360}
            showLegend={false}
            data={[
              {
                x: seriesRows.map((row) => row.fecha),
                y: seriesRows.map((row) => row.precio_exportacion_usd_tn),
                name: 'Precio',
                color: '#30945a',
                hovertemplate: '%{x}<br>USD %{y:.2f}/tn<extra></extra>',
              },
            ]}
          />
        </ChartWithDrillDown>
      </SimpleChartCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SimpleChartCard
          title="Mercados"
          description="Comparación simple entre mercados por margen bruto."
        >
          <ChartWithDrillDown<MacroMercadoRow>
            title="Mercados"
            description="Margen bruto por mercado."
            formula="precio exportado - flete"
            source={data.meta.source}
            lastUpdated={data.meta.last_updated}
            filtersApplied={appliedFilters}
            detailRows={data.breakdown.mercados}
            detailColumns={MARKET_COLUMNS}
            exportFilename="macro-mercados"
            contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
          >
            <BarChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: data.breakdown.mercados.map((row) => row.mercado),
                  y: data.breakdown.mercados.map((row) => row.margen_bruto_usd_tn),
                  name: 'Margen bruto',
                  color: '#30945a',
                },
              ]}
            />
          </ChartWithDrillDown>
        </SimpleChartCard>

        <SimpleChartCard
          title="Variables de contexto"
          description="Resumen de las variables que mas mueven el contexto."
        >
          <ChartWithDrillDown<MacroVariableRow>
            title="Variables de contexto"
            description="Variables base del contexto."
            formula="últimos valores disponibles por variable"
            source={data.meta.source}
            lastUpdated={data.meta.last_updated}
            filtersApplied={appliedFilters}
            detailRows={data.breakdown.variables}
            detailColumns={VARIABLE_COLUMNS}
            exportFilename="macro-variables"
            contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
          >
            <BarChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: data.breakdown.variables.map((row) => row.variable),
                  y: data.breakdown.variables.map((row) => row.valor),
                  name: 'Valor',
                  color: '#c1b29a',
                },
              ]}
            />
          </ChartWithDrillDown>
        </SimpleChartCard>
      </div>
    </div>
  )
}

export default function MacroMercadoPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <MacroMercadoPageContent />
    </Suspense>
  )
}
