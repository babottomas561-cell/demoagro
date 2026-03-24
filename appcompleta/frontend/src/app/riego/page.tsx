'use client'

import { Suspense, useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { Droplets } from 'lucide-react'
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
import { usePageFilters } from '@/hooks/usePageFilters'
import { useRiegoFertirriego } from '@/hooks/useRiegoFertirriego'
import { useTimeRangeQuery } from '@/hooks/useTimeRangeQuery'
import { buildAppliedFilters } from '@/lib/drilldown'
import { formatNumber, formatPercent } from '@/lib/formatters'
import { ensureMinimumSeriesPoints, filterSeriesByRange } from '@/lib/time-series'
import type { RiegoLoteRow, RiegoSerieRow } from '@/types/lemon-riego'

const SERIES_COLUMNS: ColDef<RiegoSerieRow>[] = [
  { field: 'fecha', headerName: 'Semana', flex: 1.1 },
  { field: 'm3_riego', headerName: 'Riego m3', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'm3_requeridos', headerName: 'Requeridos m3', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'balance_hidrico_m3', headerName: 'Balance', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
]

const LOT_COLUMNS: ColDef<RiegoLoteRow>[] = [
  { field: 'lote', headerName: 'Lote', flex: 1.1 },
  { field: 'establecimiento', headerName: 'Establecimiento', flex: 1.1 },
  { field: 'm3_aplicados', headerName: 'm3 aplicados', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'm3_requeridos', headerName: 'm3 requeridos', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'balance_hidrico_m3', headerName: 'Balance', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'productividad_kg_m3', headerName: 'Kg/m3', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 2) },
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

function RiegoPageContent() {
  const filters = usePageFilters([
    'empresa_id',
    'campania_id',
    'establecimiento_id',
    'campo_id',
    'lote_id',
    'variedad_id',
  ])
  const { data, error, isLoading } = useRiegoFertirriego(filters)
  const executiveScope = useExecutiveScope(filters)
  const appliedFilters = useMemo(() => buildAppliedFilters(filters), [filters])
  const { range, setRange } = useTimeRangeQuery('90D')

  const seriesRows = useMemo(() => {
    const allRows = data?.series.agua_semanal || []
    return ensureMinimumSeriesPoints(
      filterSeriesByRange(allRows, range, (item) => item.fecha),
      allRows,
      5
    )
  }, [data?.series.agua_semanal, range])

  if (error && !data) {
    return (
      <Alert variant="danger" title="No se pudo cargar Riego y Fertirriego">
        Revisá riego, fertirriego, requerimiento hídrico y clima del ERP limonero.
      </Alert>
    )
  }

  if (isLoading || !data) {
    return <PageSkeleton />
  }

  const worstBalance = data.breakdown.ranking_desvio[0]
  const worstBalanceAbs = Math.abs(worstBalance?.balance_hidrico_m3 || 0)
  const focusTone =
    data.summary.cumplimiento_hidrico_pct < 85
      ? 'danger'
      : data.summary.cumplimiento_hidrico_pct < 95 || worstBalanceAbs > 500
        ? 'warning'
        : 'success'
  const focusBullets = [
    `El cumplimiento hídrico del período está en ${formatNumber(data.summary.cumplimiento_hidrico_pct, 1)}% sobre el requerimiento estimado.`,
    worstBalance
      ? `${worstBalance.lote} muestra ${worstBalance.balance_hidrico_m3 < 0 ? 'déficit' : 'exceso'} de ${formatNumber(worstBalanceAbs, 0)} m3 frente a la necesidad del lote.`
      : '',
    `La productividad del agua se ubica en ${formatNumber(data.summary.productividad_agua_kg_m3, 2)} kg/m3 con ${formatNumber(data.summary.lluvia_reciente_mm, 1)} mm de lluvia reciente.`,
  ]

  return (
    <div className="space-y-6">
      <DashboardLead
        title="Riego y Fertirriego"
        description="Control semanal de agua para ver cumplimiento, balance y lotes fuera de rango."
        icon={Droplets}
        label="Panel operativo diario"
        scopeLabel={executiveScope.label}
        scopeBadges={executiveScope.badges}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SimpleKpiCard
          label="Agua aplicada"
          value={`${formatNumber(data.summary.m3_aplicados, 0)} m3`}
          delta={formatPercent(data.summary.m3_aplicados_delta_pct)}
          detail={data.summary.m3_aplicados_detail}
          tone={toneFromDelta(data.summary.m3_aplicados_delta_pct)}
        />
        <SimpleKpiCard
          label="Cumplimiento hidrico"
          value={`${formatNumber(data.summary.cumplimiento_hidrico_pct, 1)}%`}
          delta={formatPercent(data.summary.cumplimiento_delta_pct)}
          detail={data.summary.cumplimiento_detail}
          tone={data.summary.cumplimiento_hidrico_pct >= 95 ? 'positive' : data.summary.cumplimiento_hidrico_pct >= 85 ? 'warning' : 'danger'}
        />
        <SimpleKpiCard
          label="Lotes fuera de rango"
          value={formatNumber(data.summary.lotes_fuera_rango, 0)}
          delta={data.summary.lotes_fuera_rango > 0 ? 'Requieren atención' : 'Sin desvíos'}
          detail="Lotes con riego aplicado < 33% o > 115% del requerimiento. Déficit severo compromete cuaje; exceso favorece hongos y eleva costos."
          tone={data.summary.lotes_fuera_rango >= 5 ? 'danger' : data.summary.lotes_fuera_rango > 0 ? 'warning' : 'positive'}
        />
        <SimpleKpiCard
          label="Kg por m3"
          value={`${formatNumber(data.summary.productividad_agua_kg_m3, 2)} kg/m3`}
          delta={formatPercent(data.summary.productividad_delta_pct)}
          detail={data.summary.productividad_detail}
          tone={toneFromDelta(data.summary.productividad_delta_pct)}
        />
      </div>

      {/* KPI con torta — cumplimiento, balance lotes, agua por establecimiento, productividad */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniPieKpiCard
          label="Cumplimiento hidrico"
          centerValue={`${formatNumber(data.summary.cumplimiento_hidrico_pct, 1)}%`}
          centerSub="Cumplido"
          slices={[
            { label: 'Cumplido', value: Math.round(data.summary.cumplimiento_hidrico_pct), color: '#30945a' },
            { label: 'Deficit', value: Math.round(Math.max(0, 100 - data.summary.cumplimiento_hidrico_pct)), color: '#cf6e63' },
          ]}
          tone={data.summary.cumplimiento_hidrico_pct >= 95 ? 'positive' : data.summary.cumplimiento_hidrico_pct >= 85 ? 'warning' : 'danger'}
        />
        <MiniPieKpiCard
          label="Balance de lotes"
          centerValue={`${data.breakdown.ranking_desvio.filter((r) => r.balance_hidrico_m3 >= -100).length}`}
          centerSub="En balance"
          slices={[
            { label: 'Superavit', value: data.breakdown.ranking_desvio.filter((r) => r.balance_hidrico_m3 > 100).length, color: '#7d8f76' },
            { label: 'Equilibrio', value: data.breakdown.ranking_desvio.filter((r) => r.balance_hidrico_m3 >= -100 && r.balance_hidrico_m3 <= 100).length, color: '#30945a' },
            { label: 'Deficit', value: data.breakdown.ranking_desvio.filter((r) => r.balance_hidrico_m3 < -100).length, color: '#cf6e63' },
          ]}
          tone={data.breakdown.ranking_desvio.filter((r) => r.balance_hidrico_m3 < -100).length > 0 ? 'danger' : 'positive'}
        />
        <MiniPieKpiCard
          label="Agua por establecimiento"
          centerValue={`${formatNumber(data.breakdown.productividad_lote.reduce((s, r) => s + r.m3_aplicados, 0), 0)} m3`}
          centerSub="Total aplicado"
          slices={(() => {
            const grouped = new Map<string, number>()
            for (const r of data.breakdown.productividad_lote) {
              grouped.set(r.establecimiento, (grouped.get(r.establecimiento) || 0) + r.m3_aplicados)
            }
            if (!grouped.size) return [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]
            const total = Array.from(grouped.values()).reduce((s, v) => s + v, 0)
            return Array.from(grouped.entries()).slice(0, 4).map(([establecimiento, m3]) => ({
              label: establecimiento,
              value: total > 0 ? Math.round((m3 / total) * 100) : 0,
            }))
          })()}
          tone="neutral"
        />
        <MiniPieKpiCard
          label="Productividad del agua"
          centerValue={`${formatNumber(data.summary.productividad_agua_kg_m3, 2)} kg/m3`}
          centerSub="Promedio"
          slices={(() => {
            const avg = data.summary.productividad_agua_kg_m3
            if (!avg) return [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]
            return [
              { label: 'Alta (>110%)', value: data.breakdown.productividad_lote.filter((r) => r.productividad_kg_m3 >= avg * 1.1).length, color: '#30945a' },
              { label: 'Media (90-110%)', value: data.breakdown.productividad_lote.filter((r) => r.productividad_kg_m3 >= avg * 0.9 && r.productividad_kg_m3 < avg * 1.1).length, color: '#7d8f76' },
              { label: 'Baja (<90%)', value: data.breakdown.productividad_lote.filter((r) => r.productividad_kg_m3 < avg * 0.9).length, color: '#cf6e63' },
            ]
          })()}
          tone={data.summary.productividad_delta_pct > 0 ? 'positive' : 'warning'}
        />
      </div>

      <OperationalFocusAlert title="Foco operativo del dia" tone={focusTone} bullets={focusBullets} />

      <SimpleChartCard
        title="Balance semanal de agua"
        description="Comparacion simple entre riego aplicado y requerimiento."
        actions={
          <>
            <TimeRangeSelector value={range} onChange={setRange} />
            <DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />
          </>
        }
      >
        <ChartWithDrillDown<RiegoSerieRow>
          title="Balance semanal de agua"
          description="Riego y requerimiento semanal."
          formula="m3 aplicados vs m3 requeridos por semana"
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={seriesRows}
          detailColumns={SERIES_COLUMNS}
          exportFilename="riego-agua-semanal"
          contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
        >
          <LineChart
            height={360}
            data={[
              {
                x: seriesRows.map((row) => row.fecha),
                y: seriesRows.map((row) => row.m3_riego),
                name: 'Aplicado',
                color: '#30945a',
              },
              {
                x: seriesRows.map((row) => row.fecha),
                y: seriesRows.map((row) => row.m3_requeridos),
                name: 'Requerido',
                color: '#c1b29a',
              },
            ]}
          />
        </ChartWithDrillDown>
      </SimpleChartCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SimpleChartCard
          title="Kg por m3 por lote"
          description="Que lotes convierten mejor el agua en resultado."
        >
          <ChartWithDrillDown<RiegoLoteRow>
            title="Kg por m3 por lote"
            description="Kg por m3 por lote."
            formula="kg cosechados / m3 aplicados"
            source={data.meta.source}
            lastUpdated={data.meta.last_updated}
            filtersApplied={appliedFilters}
            detailRows={data.breakdown.productividad_lote}
            detailColumns={LOT_COLUMNS}
            exportFilename="riego-productividad-lote"
            contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
          >
            <BarChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: data.breakdown.productividad_lote.map((row) => row.lote),
                  y: data.breakdown.productividad_lote.map((row) => row.productividad_kg_m3),
                  name: 'Kg/m3',
                  color: '#30945a',
                },
              ]}
            />
          </ChartWithDrillDown>
        </SimpleChartCard>

        <SimpleChartCard
          title="Fuera de rango"
          description="Lotes con mayor desvío hídrico respecto del requerimiento."
        >
          <ChartWithDrillDown<RiegoLoteRow>
            title="Lotes fuera de rango"
            description="Ranking de balances hídricos."
            formula="desvío de agua aplicada vs requerida"
            source={data.meta.source}
            lastUpdated={data.meta.last_updated}
            filtersApplied={appliedFilters}
            detailRows={data.breakdown.ranking_desvio}
            detailColumns={LOT_COLUMNS}
            exportFilename="riego-fuera-rango"
            contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
          >
            <BarChart
              height={320}
              horizontal
              showLegend={false}
              data={[
                {
                  x: data.breakdown.ranking_desvio.map((row) => row.lote),
                  y: data.breakdown.ranking_desvio.map((row) => row.balance_hidrico_m3),
                  name: 'Balance',
                  color: '#cf6e63',
                },
              ]}
            />
          </ChartWithDrillDown>
        </SimpleChartCard>
      </div>
    </div>
  )
}

export default function RiegoPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <RiegoPageContent />
    </Suspense>
  )
}
