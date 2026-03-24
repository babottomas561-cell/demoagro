'use client'

import { Suspense, useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { ShieldCheck } from 'lucide-react'
import { BarChart } from '@/components/charts/BarChart'
import { LineChart } from '@/components/charts/LineChart'
import { PieChart } from '@/components/charts/PieChart'
import { DashboardLead } from '@/components/dashboard-v3/DashboardLead'
import { ChartWithDrillDown } from '@/components/drilldown/ChartWithDrillDown'
import { MiniPieKpiCard } from '@/components/simple/MiniPieKpiCard'
import { SimpleChartCard } from '@/components/simple/SimpleChartCard'
import { SimpleKpiCard } from '@/components/simple/SimpleKpiCard'
import { OperationalFocusAlert } from '@/components/simple/OperationalFocusAlert'
import { Alert } from '@/components/ui/Alert'
import { DataSourceTag } from '@/components/ui/DataSourceTag'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { useExecutiveScope } from '@/hooks/useExecutiveScope'
import { useCalidadFruta } from '@/hooks/useCalidadFruta'
import { usePageFilters } from '@/hooks/usePageFilters'
import { buildAppliedFilters } from '@/lib/drilldown'
import { formatDate, formatNumber } from '@/lib/formatters'
import { formatPercentValue } from '@/lib/lemon-ui'
import { takeLastItems } from '@/lib/operational-dashboard'
import type { CalidadDefectoRow, CalidadDestinoRow, CalidadLoteRow, CalidadSerieRow } from '@/types/lemon-calidad'

type QualityDailyDetailRow = CalidadSerieRow & { estado: string }
type QualityLotDetailRow = CalidadLoteRow & { estado: string }
type QualityDefectDetailRow = CalidadDefectoRow & { estado: string }
type QualityDestinationDetailRow = CalidadDestinoRow & { estado: string }

function PageSkeleton() {
  return (
    <div className="space-y-6">
      <SkeletonBlock className="h-24 w-full" />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <SkeletonBlock key={index} className="h-32 w-full" />
        ))}
      </div>
      <SkeletonBlock className="h-[22rem] w-full" />
      <div className="grid gap-4 xl:grid-cols-2">
        <SkeletonBlock className="h-[22rem] w-full" />
        <SkeletonBlock className="h-[22rem] w-full" />
      </div>
      <SkeletonBlock className="h-[20rem] w-full" />
    </div>
  )
}

function qualityState(packoutPct: number, target: number) {
  if (packoutPct < target - 5) return 'Critico'
  if (packoutPct < target) return 'Atencion'
  return 'Bien'
}

function CalidadPageContent() {
  const filters = usePageFilters([
    'empresa_id',
    'campania_id',
    'establecimiento_id',
    'campo_id',
    'lote_id',
    'variedad_id',
    'destino_id',
    'calibre_id',
  ])
  const { data, error, isLoading } = useCalidadFruta(filters)
  const executiveScope = useExecutiveScope(filters)
  const appliedFilters = useMemo(() => buildAppliedFilters(filters), [filters])

  const qualityRows = useMemo(() => takeLastItems(data?.series.calidad_diaria || [], 14), [data?.series.calidad_diaria])

  const qualityDetailRows = useMemo<QualityDailyDetailRow[]>(
    () =>
      qualityRows.map((row) => ({
        ...row,
        estado: qualityState(row.packout_pct, data?.summary.packout_objetivo_pct || 0),
      })),
    [data?.summary.packout_objetivo_pct, qualityRows]
  )

  const defectRows = useMemo<QualityDefectDetailRow[]>(
    () =>
      [...(data?.breakdown.defectos_tipo || [])]
        .sort((a, b) => b.kg_rechazo - a.kg_rechazo)
        .map((row) => ({
          ...row,
          estado: row.participacion_pct >= 20 ? 'Critico' : row.participacion_pct >= 10 ? 'Atencion' : 'Bien',
        })),
    [data?.breakdown.defectos_tipo]
  )

  const destinationRows = useMemo<QualityDestinationDetailRow[]>(
    () =>
      [...(data?.breakdown.destino_fruta || [])].map((row) => ({
        ...row,
        estado: row.destino.toLowerCase().includes('descarte')
          ? 'Critico'
          : row.destino.toLowerCase().includes('industria')
            ? 'Atencion'
            : 'Bien',
      })),
    [data?.breakdown.destino_fruta]
  )

  const lotRows = useMemo<QualityLotDetailRow[]>(
    () =>
      [...(data?.breakdown.packout_lotes || [])]
        .sort((a, b) => a.packout_pct - b.packout_pct)
        .map((row) => ({
          ...row,
          estado: qualityState(row.packout_pct, row.objetivo_packout_pct),
        })),
    [data?.breakdown.packout_lotes]
  )

  const focusTone = useMemo<'success' | 'warning' | 'danger'>(() => {
    if ((data?.summary.packout_hoy_pct || 0) < (data?.summary.packout_objetivo_pct || 0) - 5 || (data?.summary.descarte_hoy_pct || 0) >= 10) return 'danger'
    if ((data?.summary.packout_hoy_pct || 0) < (data?.summary.packout_objetivo_pct || 0) || (data?.summary.rechazo_hoy_pct || 0) >= 8) return 'warning'
    return 'success'
  }, [
    data?.summary.descarte_hoy_pct,
    data?.summary.packout_hoy_pct,
    data?.summary.packout_objetivo_pct,
    data?.summary.rechazo_hoy_pct,
  ])

  const focusBullets = useMemo(() => {
    const worstLot = lotRows[0]
    const topDefect = defectRows[0]
    const latestQuality = qualityRows[qualityRows.length - 1]
    return [
      latestQuality
        ? `El ultimo dia operativo cerro con ${formatPercentValue(latestQuality.packout_pct)} de packout y ${formatPercentValue(latestQuality.rechazo_pct)} de rechazo.`
        : '',
      worstLot
        ? `${worstLot.codigo_lote || worstLot.lote} es hoy el lote mas comprometido, con ${formatPercentValue(worstLot.packout_pct)} de packout.`
        : '',
      topDefect
        ? `${topDefect.defecto} explica ${formatPercentValue(topDefect.participacion_pct)} del rechazo del periodo.`
        : '',
    ]
  }, [defectRows, lotRows, qualityRows])

  const dailyColumns = useMemo<ColDef<QualityDailyDetailRow>[]>(
    () => [
      { field: 'fecha', headerName: 'Fecha', valueFormatter: ({ value }) => formatDate(String(value || '')) },
      { field: 'kg_recibidos', headerName: 'Kg recibidos', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'packout_pct', headerName: 'Packout %', valueFormatter: ({ value }) => formatPercentValue(Number(value || 0)) },
      { field: 'rechazo_pct', headerName: 'Rechazo %', valueFormatter: ({ value }) => formatPercentValue(Number(value || 0)) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const defectColumns = useMemo<ColDef<QualityDefectDetailRow>[]>(
    () => [
      { field: 'defecto', headerName: 'Defecto' },
      { field: 'categoria', headerName: 'Categoria' },
      { field: 'kg_rechazo', headerName: 'Kg rechazo', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'participacion_pct', headerName: 'Participacion %', valueFormatter: ({ value }) => formatPercentValue(Number(value || 0)) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const destinationColumns = useMemo<ColDef<QualityDestinationDetailRow>[]>(
    () => [
      { field: 'destino', headerName: 'Destino' },
      { field: 'kg', headerName: 'Kg', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'participacion_pct', headerName: 'Participacion %', valueFormatter: ({ value }) => formatPercentValue(Number(value || 0)) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const lotColumns = useMemo<ColDef<QualityLotDetailRow>[]>(
    () => [
      { field: 'lote', headerName: 'Lote' },
      { field: 'establecimiento', headerName: 'Establecimiento' },
      { field: 'packout_pct', headerName: 'Packout %', valueFormatter: ({ value }) => formatPercentValue(Number(value || 0)) },
      { field: 'rechazo_pct', headerName: 'Rechazo %', valueFormatter: ({ value }) => formatPercentValue(Number(value || 0)) },
      { field: 'principal_defecto', headerName: 'Defecto principal' },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  if (error && !data) {
    return (
      <Alert variant="danger" title="No se pudo cargar Calidad de Fruta">
        Revisa recepcion, clasificacion, rechazo y packout del ERP limonero.
      </Alert>
    )
  }

  if (isLoading || !data) return <PageSkeleton />

  return (
    <div className="space-y-6">
      <DashboardLead
        title="Calidad de Fruta"
        description="Control diario de calidad para ver si la fruta sostiene salida comercial o se desvia a industria."
        icon={ShieldCheck}
        label="Panel operativo diario"
        scopeLabel={executiveScope.label}
        scopeBadges={executiveScope.badges}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SimpleKpiCard
          label="Packout hoy"
          value={formatPercentValue(data.summary.packout_hoy_pct)}
          delta="Ultimo dia operativo"
          detail="Mide la fruta util del dia para ver rapido si la condicion se sostiene."
          tone={data.summary.packout_hoy_pct >= data.summary.packout_objetivo_pct ? 'positive' : 'warning'}
        />
        <SimpleKpiCard
          label="Rechazo hoy"
          value={formatPercentValue(data.summary.rechazo_hoy_pct)}
          delta="Ultimo dia operativo"
          detail="Senala si los defectos ya estan creciendo por arriba de lo normal."
          tone={data.summary.rechazo_hoy_pct >= 8 ? 'warning' : 'positive'}
        />
        <SimpleKpiCard
          label="Lotes criticos"
          value={formatNumber(data.summary.lotes_criticos, 0)}
          delta={data.summary.lotes_criticos_delta_pct !== 0 ? `${data.summary.lotes_criticos_delta_pct > 0 ? '+' : ''}${formatNumber(data.summary.lotes_criticos_delta_pct, 1)}%` : 'Sin variacion'}
          detail="Lotes con packout 5 pts bajo objetivo o rechazo ≥ 10%. Indican calidad de campo comprometida que impacta directo en margen exportable."
          tone={data.summary.lotes_criticos >= 3 ? 'danger' : data.summary.lotes_criticos > 0 ? 'warning' : 'positive'}
        />
        <SimpleKpiCard
          label="Descarte hoy"
          value={formatPercentValue(data.summary.descarte_hoy_pct)}
          delta="Ultimo dia operativo"
          detail="Permite ver si la perdida directa ya es material. En limon, <3% es aceptable; 3–8% requiere atención; >8% es perdida severa."
          tone={data.summary.descarte_hoy_pct >= 8 ? 'danger' : data.summary.descarte_hoy_pct >= 3 ? 'warning' : 'positive'}
        />
      </div>

      {/* KPI con torta — destino de fruta y packout vs objetivo */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniPieKpiCard
          label="Destino de fruta"
          centerValue={formatPercentValue(data.summary.packout_hoy_pct)}
          centerSub="Fresco"
          slices={[
            { label: 'Fresco', value: Math.round(data.summary.packout_hoy_pct), color: '#30945a' },
            { label: 'Industria', value: Math.round(data.summary.industria_hoy_pct), color: '#7d8f76' },
            { label: 'Descarte', value: Math.round(data.summary.descarte_hoy_pct), color: '#cf6e63' },
          ]}
          tone={data.summary.packout_hoy_pct >= data.summary.packout_objetivo_pct ? 'positive' : 'warning'}
        />
        <MiniPieKpiCard
          label="Packout vs objetivo"
          centerValue={formatPercentValue(data.summary.packout_promedio_pct)}
          centerSub="Promedio"
          slices={[
            { label: 'Packout', value: Math.round(data.summary.packout_promedio_pct), color: '#30945a' },
            { label: 'Brecha obj.', value: Math.max(0, Math.round(data.summary.packout_objetivo_pct - data.summary.packout_promedio_pct)), color: '#d8cbbb' },
          ]}
          tone={data.summary.packout_promedio_pct >= data.summary.packout_objetivo_pct ? 'positive' : 'warning'}
        />
        <MiniPieKpiCard
          label="Defectos del periodo"
          centerValue={`${formatNumber(data.breakdown.defectos_tipo[0]?.participacion_pct || 0, 0)}%`}
          centerSub={data.breakdown.defectos_tipo[0]?.defecto || ''}
          slices={data.breakdown.defectos_tipo.length ? data.breakdown.defectos_tipo.slice(0, 4).map((d) => ({
            label: d.defecto,
            value: Math.round(d.participacion_pct),
          })) : [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]}
          tone={defectRows[0]?.participacion_pct >= 20 ? 'danger' : defectRows[0]?.participacion_pct >= 10 ? 'warning' : 'neutral'}
        />
        <MiniPieKpiCard
          label="Lotes por estado"
          centerValue={`${data.breakdown.packout_lotes.filter((l) => l.packout_pct >= l.objetivo_packout_pct).length}`}
          centerSub="En objetivo"
          slices={[
            { label: 'En objetivo', value: data.breakdown.packout_lotes.filter((l) => l.packout_pct >= l.objetivo_packout_pct).length, color: '#30945a' },
            { label: 'Bajo objetivo', value: data.breakdown.packout_lotes.filter((l) => l.packout_pct < l.objetivo_packout_pct).length, color: '#cf6e63' },
          ]}
          tone={!data.breakdown.packout_lotes.length ? 'neutral' : data.breakdown.packout_lotes.filter((l) => l.packout_pct >= l.objetivo_packout_pct).length > data.breakdown.packout_lotes.length / 2 ? 'positive' : 'danger'}
        />
      </div>

      <OperationalFocusAlert title="Foco operativo del dia" tone={focusTone} bullets={focusBullets} />

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartWithDrillDown<QualityDailyDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Calidad diaria"
          description="Detalle diario de calidad y fruta util."
          summaryItems={[
            { label: 'Packout promedio', value: formatPercentValue(data.summary.packout_promedio_pct) },
            { label: 'Rechazo promedio', value: formatPercentValue(data.summary.rechazo_pct) },
            { label: 'Ultimo packout', value: formatPercentValue(qualityRows[qualityRows.length - 1]?.packout_pct || 0) },
            { label: 'Ultimo recibido', value: `${formatNumber(qualityRows[qualityRows.length - 1]?.kg_recibidos || 0, 0)} kg` },
          ]}
          contextText="Sirve para ver si la calidad viene estable o si ya hay una caida visible en los ultimos dias."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={qualityDetailRows}
          detailColumns={dailyColumns}
          exportFilename="calidad-packout-tiempo"
          detailLabel="Recepcion y calidad diaria."
        >
          <SimpleChartCard
            title="Packout diario"
            description="Serie corta para ver si la calidad comercial mejora o cae."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <LineChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: qualityRows.map((row) => row.fecha),
                  y: qualityRows.map((row) => row.packout_pct),
                  name: 'Packout',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>%{y:.1f}%<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<QualityDefectDetailRow>
          title="Informe ERP · Defectos principales"
          description="Apertura simple del rechazo por tipo de defecto."
          summaryItems={[
            { label: 'Defectos', value: formatNumber(defectRows.length, 0) },
            { label: 'Principal defecto', value: defectRows[0]?.defecto || 'Sin dato' },
            { label: 'Kg afectados', value: `${formatNumber(defectRows[0]?.kg_rechazo || 0, 0)} kg` },
            { label: 'Participacion', value: formatPercentValue(defectRows[0]?.participacion_pct || 0) },
          ]}
          contextText="Permite ver rapido que defecto esta explicando la mayor parte del rechazo."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={defectRows}
          detailColumns={defectColumns}
          exportFilename="calidad-defectos"
          detailLabel="Detalle de defectos de rechazo."
        >
          <SimpleChartCard
            title="Defectos"
            description="Comparacion simple para ver que problema de calidad pesa mas."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              showLegend={false}
              data={[
                {
                  x: defectRows.slice(0, 8).map((row) => row.defecto),
                  y: defectRows.slice(0, 8).map((row) => row.kg_rechazo),
                  name: 'Kg rechazo',
                  color: '#cf6e63',
                  hovertemplate: '%{x}<br>%{y:,.0f} kg<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<QualityDestinationDetailRow>
          title="Informe ERP · Destino de fruta"
          description="Mix simple entre exportacion, industria y descarte."
          summaryItems={[
            { label: 'Destinos', value: formatNumber(destinationRows.length, 0) },
            { label: 'Principal destino', value: destinationRows[0]?.destino || 'Sin dato' },
            { label: 'Participacion', value: formatPercentValue(destinationRows[0]?.participacion_pct || 0) },
            { label: 'Kg', value: `${formatNumber(destinationRows[0]?.kg || 0, 0)} kg` },
          ]}
          contextText="Ayuda a ver cuanto de la fruta se sostiene en destino comercial y cuanto se desvía."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={destinationRows}
          detailColumns={destinationColumns}
          exportFilename="calidad-destino-fruta"
          detailLabel="Distribucion por destino de fruta."
        >
          <SimpleChartCard
            title="Destino fruta"
            description="Lectura rapida del mix de salida de la fruta procesada."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <PieChart
              height={280}
              labels={destinationRows.map((row) => row.destino)}
              values={destinationRows.map((row) => row.kg)}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<QualityLotDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Packout por lote"
          description="Comparacion simple del packout por lote."
          summaryItems={[
            { label: 'Lotes', value: formatNumber(lotRows.length, 0) },
            { label: 'Peor packout', value: formatPercentValue(lotRows[0]?.packout_pct || 0) },
            { label: 'Peor rechazo', value: formatPercentValue(lotRows[0]?.rechazo_pct || 0) },
            { label: 'Defecto principal', value: lotRows[0]?.principal_defecto || 'Sin dato' },
          ]}
          contextText="Sirve para ver rapido que lotes estan explicando la caida de calidad."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={lotRows}
          detailColumns={lotColumns}
          exportFilename="calidad-packout-lote"
          detailLabel="Packout resumido por lote."
        >
          <SimpleChartCard
            title="Packout por lote"
            description="Comparacion directa para ver rapido donde esta el problema."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={300}
              horizontal
              showLegend={false}
              data={[
                {
                  x: lotRows.slice(0, 10).map((row) => row.lote),
                  y: lotRows.slice(0, 10).map((row) => row.packout_pct),
                  name: 'Packout',
                  color: '#30945a',
                  hovertemplate: '%{y}<br>%{x:.1f}%<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>
      </div>
    </div>
  )
}

export default function CalidadPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <CalidadPageContent />
    </Suspense>
  )
}
