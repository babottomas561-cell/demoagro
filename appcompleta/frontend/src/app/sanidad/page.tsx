'use client'

import { Suspense, useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { ShieldAlert } from 'lucide-react'
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
import { useSanidadMonitoreo } from '@/hooks/useSanidadMonitoreo'
import { useTimeRangeQuery } from '@/hooks/useTimeRangeQuery'
import { buildAppliedFilters } from '@/lib/drilldown'
import { formatCurrency, formatNumber, formatPercent } from '@/lib/formatters'
import { ensureMinimumSeriesPoints, filterSeriesByRange } from '@/lib/time-series'
import type {
  SanidadLoteRow,
  SanidadSerieRow,
  SanidadTipoRow,
  SanidadTratamientoRow,
} from '@/types/lemon-sanidad'

const SERIES_COLUMNS: ColDef<SanidadSerieRow>[] = [
  { field: 'fecha', headerName: 'Semana', flex: 1.1 },
  { field: 'eventos', headerName: 'Eventos', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'incidencia_promedio_pct', headerName: 'Incidencia', valueFormatter: ({ value }) => formatPercent(Number(value || 0)) },
  { field: 'alertas', headerName: 'Alertas', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'tratamientos', headerName: 'Tratamientos', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
]

const TYPE_COLUMNS: ColDef<SanidadTipoRow>[] = [
  { field: 'tipo', headerName: 'Evento', flex: 1.2 },
  { field: 'categoria', headerName: 'Categoría', flex: 1 },
  { field: 'eventos', headerName: 'Eventos', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'incidencia_promedio_pct', headerName: 'Incidencia', valueFormatter: ({ value }) => formatPercent(Number(value || 0)) },
]

const TREATMENT_COLUMNS: ColDef<SanidadTratamientoRow>[] = [
  { field: 'objetivo', headerName: 'Objetivo', flex: 1.1 },
  { field: 'producto', headerName: 'Producto', flex: 1.2 },
  { field: 'aplicaciones', headerName: 'Aplicaciones', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'costo_promedio_ars_ha', headerName: 'Costo/ha', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
]

const LOT_COLUMNS: ColDef<SanidadLoteRow>[] = [
  { field: 'lote', headerName: 'Lote', flex: 1.1 },
  { field: 'establecimiento', headerName: 'Establecimiento', flex: 1.1 },
  { field: 'incidencia_promedio_pct', headerName: 'Incidencia', valueFormatter: ({ value }) => formatPercent(Number(value || 0)) },
  { field: 'alertas', headerName: 'Alertas', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
  { field: 'tratamientos', headerName: 'Tratamientos', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
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
  if (value < 0) return 'positive' as const
  if (value > 0) return 'danger' as const
  return 'neutral' as const
}

function SanidadPageContent() {
  const filters = usePageFilters([
    'empresa_id',
    'campania_id',
    'establecimiento_id',
    'campo_id',
    'lote_id',
    'variedad_id',
  ])
  const { data, error, isLoading } = useSanidadMonitoreo(filters)
  const executiveScope = useExecutiveScope(filters)
  const appliedFilters = useMemo(() => buildAppliedFilters(filters), [filters])
  const { range, setRange } = useTimeRangeQuery('90D')

  const seriesRows = useMemo(() => {
    const allRows = data?.series.sanidad_semanal || []
    return ensureMinimumSeriesPoints(
      filterSeriesByRange(allRows, range, (item) => item.fecha),
      allRows,
      5
    )
  }, [data?.series.sanidad_semanal, range])

  if (error && !data) {
    return (
      <Alert variant="danger" title="No se pudo cargar Sanidad y Monitoreo">
        Revisá scouting y aplicaciones fitosanitarias del ERP limonero.
      </Alert>
    )
  }

  if (isLoading || !data) {
    return <PageSkeleton />
  }

  const mainIssue = data.breakdown.incidencias_tipo[0]
  const focusTone =
    data.summary.lotes_riesgo_alto > 0 || data.summary.lotes_sin_tratamiento > 0
      ? 'danger'
      : data.summary.lotes_alerta > 0 || data.summary.incidencia_delta_pct > 0
        ? 'warning'
        : 'success'
  const focusBullets = [
    `La incidencia promedio del período está en ${formatNumber(data.summary.incidencia_promedio_pct, 1)}% y ${data.summary.incidencia_delta_pct > 0 ? 'sube' : data.summary.incidencia_delta_pct < 0 ? 'baja' : 'se mantiene'} contra el tramo anterior.`,
    mainIssue
      ? `${mainIssue.tipo} concentra hoy la mayor presión sanitaria con ${formatNumber(mainIssue.eventos, 0)} eventos observados.`
      : '',
    `${formatNumber(data.summary.lotes_riesgo_alto, 0)} lotes están en riesgo alto y ${formatNumber(data.summary.lotes_sin_tratamiento, 0)} siguen sin tratamiento activo.`,
  ]

  return (
    <div className="space-y-6">
      <DashboardLead
        title="Sanidad y Monitoreo"
        description="Control sanitario semanal para ver presion, lotes en alerta y respuesta fitosanitaria."
        icon={ShieldAlert}
        label="Panel operativo diario"
        scopeLabel={executiveScope.label}
        scopeBadges={executiveScope.badges}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SimpleKpiCard
          label="Tratamientos 30d"
          value={formatNumber(data.summary.tratamientos_30d, 0)}
          delta={data.summary.tratamientos_delta_pct !== 0 ? `${data.summary.tratamientos_delta_pct > 0 ? '+' : ''}${formatNumber(data.summary.tratamientos_delta_pct, 1)}%` : 'Sin variacion'}
          detail={data.summary.tratamientos_detail}
          tone={data.summary.tratamientos_30d > 0 ? 'positive' : data.summary.lotes_alerta > 0 ? 'danger' : 'neutral'}
        />
        <SimpleKpiCard
          label="Lotes en alerta"
          value={formatNumber(data.summary.lotes_alerta, 0)}
          delta={formatPercent(data.summary.lotes_alerta_delta_pct)}
          detail={data.summary.lotes_alerta_detail}
          tone={data.summary.lotes_alerta > 0 ? 'warning' : 'positive'}
        />
        <SimpleKpiCard
          label="Días sin cobre"
          value={`${data.summary.dias_sin_cobre} días`}
          delta={data.summary.dias_sin_cobre <= 21 ? 'Dentro del intervalo' : 'Fuera de intervalo'}
          detail={data.summary.dias_sin_cobre_detail}
          tone={data.summary.dias_sin_cobre <= 14 ? 'positive' : data.summary.dias_sin_cobre <= 21 ? 'warning' : 'danger'}
        />
        <SimpleKpiCard
          label="Diaphorina citri"
          value={`${data.summary.diaphorina_capturas} capturas`}
          delta={data.summary.diaphorina_capturas === 0 ? 'Sin detecciones' : '⚠ Protocolo activo'}
          detail={data.summary.diaphorina_capturas_detail}
          tone={data.summary.diaphorina_capturas === 0 ? 'positive' : 'danger'}
        />
      </div>

      {/* KPI con torta — estado lotes, eventos, aplicaciones, categorias */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniPieKpiCard
          label="Estado de lotes"
          centerValue={`${formatNumber(data.summary.lotes_riesgo_alto, 0)}`}
          centerSub="Riesgo alto"
          slices={[
            { label: 'Riesgo alto', value: data.summary.lotes_riesgo_alto, color: '#cf6e63' },
            { label: 'En alerta', value: Math.max(0, data.summary.lotes_alerta - data.summary.lotes_riesgo_alto), color: '#d69f2f' },
            { label: 'Sin tratamiento', value: data.summary.lotes_sin_tratamiento, color: '#b2a48f' },
          ]}
          tone={data.summary.lotes_riesgo_alto > 0 ? 'danger' : data.summary.lotes_alerta > 0 ? 'warning' : 'positive'}
        />
        <MiniPieKpiCard
          label="Eventos por tipo"
          centerValue={`${formatNumber(data.breakdown.incidencias_tipo[0]?.eventos || 0, 0)}`}
          centerSub={data.breakdown.incidencias_tipo[0]?.tipo || ''}
          slices={data.breakdown.incidencias_tipo.length ? data.breakdown.incidencias_tipo.slice(0, 4).map((r) => ({
            label: r.tipo,
            value: r.eventos,
          })) : [{ label: 'Sin eventos', value: 1, color: '#d8cbbb' }]}
          tone={data.summary.lotes_riesgo_alto > 0 ? 'danger' : 'neutral'}
        />
        <MiniPieKpiCard
          label="Aplicaciones por objetivo"
          centerValue={`${formatNumber(data.breakdown.tratamientos[0]?.aplicaciones || 0, 0)}`}
          centerSub={data.breakdown.tratamientos[0]?.objetivo || ''}
          slices={data.breakdown.tratamientos.length ? data.breakdown.tratamientos.slice(0, 4).map((r) => ({
            label: r.objetivo,
            value: r.aplicaciones,
          })) : [{ label: 'Sin aplicaciones', value: 1, color: '#d8cbbb' }]}
          tone="neutral"
        />
        <MiniPieKpiCard
          label="Eventos por categoria"
          centerValue={`${formatNumber(data.breakdown.incidencias_tipo.reduce((s, r) => s + r.eventos, 0), 0)}`}
          centerSub="Total eventos"
          slices={(() => {
            const grouped = new Map<string, number>()
            for (const r of data.breakdown.incidencias_tipo) {
              grouped.set(r.categoria, (grouped.get(r.categoria) || 0) + r.eventos)
            }
            const entries = Array.from(grouped.entries()).slice(0, 4).map(([categoria, eventos]) => ({
              label: categoria,
              value: eventos,
            }))
            return entries.length ? entries : [{ label: 'Sin categorias', value: 1, color: '#d8cbbb' }]
          })()}
          tone={data.summary.incidencia_delta_pct > 0 ? 'warning' : 'neutral'}
        />
      </div>

      <OperationalFocusAlert title="Foco operativo del dia" tone={focusTone} bullets={focusBullets} />

      <SimpleChartCard
        title="Presion sanitaria semanal"
        description="Evolucion simple de la presion sanitaria para seguir la tendencia."
        actions={
          <>
            <TimeRangeSelector value={range} onChange={setRange} />
            <DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />
          </>
        }
      >
        <ChartWithDrillDown<SanidadSerieRow>
          title="Presion sanitaria semanal"
          description="Serie semanal de incidencia promedio."
          formula="promedio de incidencias observadas por semana"
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={seriesRows}
          detailColumns={SERIES_COLUMNS}
          exportFilename="sanidad-incidencia-semanal"
          contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
        >
          <LineChart
            height={360}
            showLegend={false}
            data={[
              {
                x: seriesRows.map((row) => row.fecha),
                y: seriesRows.map((row) => row.incidencia_promedio_pct),
                name: 'Incidencia',
                color: '#cf6e63',
                hovertemplate: '%{x}<br>%{y:.1f}%<extra></extra>',
              },
            ]}
          />
        </ChartWithDrillDown>
      </SimpleChartCard>

      <div className="grid gap-6 xl:grid-cols-2">
        <SimpleChartCard
          title="Eventos sanitarios"
          description="Qué tipo de evento explica más presión sanitaria."
        >
          <ChartWithDrillDown<SanidadTipoRow>
            title="Eventos sanitarios"
            description="Eventos por tipo."
            formula="conteo de eventos por tipo"
            source={data.meta.source}
            lastUpdated={data.meta.last_updated}
            filtersApplied={appliedFilters}
            detailRows={data.breakdown.incidencias_tipo}
            detailColumns={TYPE_COLUMNS}
            exportFilename="sanidad-eventos-tipo"
            contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
          >
            <BarChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: data.breakdown.incidencias_tipo.map((row) => row.tipo),
                  y: data.breakdown.incidencias_tipo.map((row) => row.eventos),
                  name: 'Eventos',
                  color: '#cf6e63',
                },
              ]}
            />
          </ChartWithDrillDown>
        </SimpleChartCard>

        <SimpleChartCard
          title="Tratamientos activos"
          description="Donde se concentra hoy la respuesta fitosanitaria."
        >
          <ChartWithDrillDown<SanidadTratamientoRow>
            title="Tratamientos activos"
            description="Aplicaciones por objetivo."
            formula="conteo de aplicaciones por objetivo"
            source={data.meta.source}
            lastUpdated={data.meta.last_updated}
            filtersApplied={appliedFilters}
            detailRows={data.breakdown.tratamientos}
            detailColumns={TREATMENT_COLUMNS}
            exportFilename="sanidad-tratamientos"
            contentClassName="rounded-[1.25rem] bg-[#fcfaf5]"
          >
            <BarChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: data.breakdown.tratamientos.map((row) => row.objetivo),
                  y: data.breakdown.tratamientos.map((row) => row.aplicaciones),
                  name: 'Aplicaciones',
                  color: '#30945a',
                },
              ]}
            />
          </ChartWithDrillDown>
        </SimpleChartCard>
      </div>
    </div>
  )
}

export default function SanidadPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <SanidadPageContent />
    </Suspense>
  )
}
