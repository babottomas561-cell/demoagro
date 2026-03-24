'use client'

import { Suspense, useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { Factory } from 'lucide-react'
import { BarChart } from '@/components/charts/BarChart'
import { LineChart } from '@/components/charts/LineChart'
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
import { usePackhouseControl } from '@/hooks/usePackhouseControl'
import { usePageFilters } from '@/hooks/usePageFilters'
import { buildAppliedFilters } from '@/lib/drilldown'
import { formatCurrency, formatDate, formatNumber, formatToneladas } from '@/lib/formatters'
import { takeLastItems } from '@/lib/operational-dashboard'
import type { PackhouseDowntimeRow, PackhouseLineaRow, PackhouseRankingRow, PackhouseSerieRow } from '@/types/lemon-packhouse'

type PackhouseDailyDetailRow = PackhouseSerieRow & { estado: string }
type PackhouseLineDetailRow = PackhouseLineaRow & { estado: string }
type PackhouseDowntimeDetailRow = PackhouseDowntimeRow & { estado: string }
type PackhouseTimeRow = {
  linea: string
  horas_productivas: number
  horas_downtime: number
  estado: string
}

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

function throughputState(eficienciaPct: number, downtimePct: number) {
  if (downtimePct >= 18 || eficienciaPct < 70) return 'Critico'
  if (downtimePct >= 12 || eficienciaPct < 78) return 'Atencion'
  return 'Bien'
}

function weightedThroughput(rows: { tn_hora: number; kg_procesados_tn: number }[]) {
  const total = rows.reduce((acc, row) => acc + row.kg_procesados_tn, 0)
  if (!total) return 0
  return rows.reduce((acc, row) => acc + row.tn_hora * row.kg_procesados_tn, 0) / total
}

function PackhousePageContent() {
  const filters = usePageFilters([
    'empresa_id',
    'campania_id',
    'establecimiento_id',
    'campo_id',
    'lote_id',
    'variedad_id',
    'packhouse_id',
    'linea_id',
    'turno_id',
  ])
  const { data, error, isLoading } = usePackhouseControl(filters)
  const executiveScope = useExecutiveScope(filters)
  const appliedFilters = useMemo(() => buildAppliedFilters(filters), [filters])

  const processRows = useMemo(() => takeLastItems(data?.series.procesamiento_diario || [], 30), [data?.series.procesamiento_diario])
  const latestRow = processRows[processRows.length - 1]
  const frutaHora = useMemo(() => weightedThroughput(data?.breakdown.performance_linea || []), [data?.breakdown.performance_linea])

  const dailyRows = useMemo<PackhouseDailyDetailRow[]>(
    () =>
      processRows.map((row) => ({
        ...row,
        estado: throughputState(row.eficiencia_pct, row.downtime_pct),
      })),
    [processRows]
  )

  const lineRows = useMemo<PackhouseLineDetailRow[]>(
    () =>
      [...(data?.breakdown.performance_linea || [])]
        .sort((a, b) => b.eficiencia_pct - a.eficiencia_pct)
        .map((row) => ({
          ...row,
          estado: throughputState(row.eficiencia_pct, row.downtime_pct),
        })),
    [data?.breakdown.performance_linea]
  )

  const downtimeRows = useMemo<PackhouseDowntimeDetailRow[]>(
    () =>
      [...(data?.breakdown.downtime_motivos || [])]
        .sort((a, b) => b.minutos - a.minutos)
        .map((row) => ({
          ...row,
          estado: row.minutos >= 600 ? 'Critico' : row.minutos >= 300 ? 'Atencion' : 'Bien',
        })),
    [data?.breakdown.downtime_motivos]
  )

  const productiveVsStoppedRows = useMemo<PackhouseTimeRow[]>(
    () =>
      lineRows.map((row) => ({
        linea: row.linea,
        horas_productivas: row.horas_productivas,
        horas_downtime: row.horas_downtime,
        estado: row.estado,
      })),
    [lineRows]
  )

  const focusTone = useMemo<'success' | 'warning' | 'danger'>(() => {
    if ((lineRows[lineRows.length - 1]?.downtime_pct || 0) >= 18 || (lineRows[lineRows.length - 1]?.eficiencia_pct || 0) < 70) return 'danger'
    if ((data?.summary.lineas_criticas || 0) > 0 || (latestRow?.downtime_pct || 0) >= 12) return 'warning'
    return 'success'
  }, [data?.summary.lineas_criticas, latestRow?.downtime_pct, lineRows])

  const focusBullets = useMemo(() => {
    const worstLine = [...lineRows].sort((a, b) => a.eficiencia_pct - b.eficiencia_pct)[0]
    const topDowntime = downtimeRows[0]
    return [
      worstLine
        ? `${worstLine.linea} es hoy la linea mas fragil, con ${formatNumber(worstLine.eficiencia_pct, 1)}% de eficiencia y ${formatNumber(worstLine.downtime_pct, 1)}% de downtime.`
        : '',
      topDowntime
        ? `${topDowntime.motivo} es el principal motivo de parada, con ${formatNumber(topDowntime.minutos, 0)} minutos acumulados.`
        : '',
      (data?.summary.lineas_criticas || 0) > 0
        ? `${formatNumber(data?.summary.lineas_criticas || 0, 0)} lineas quedaron en zona critica dentro del periodo.`
        : 'No hay lineas en zona critica dentro del scope actual.',
    ]
  }, [data?.summary.lineas_criticas, downtimeRows, lineRows])

  const dailyColumns = useMemo<ColDef<PackhouseDailyDetailRow>[]>(
    () => [
      { field: 'fecha', headerName: 'Fecha', valueFormatter: ({ value }) => formatDate(String(value || '')) },
      { field: 'kg_procesados_tn', headerName: 'Tn', valueFormatter: ({ value }) => formatToneladas(Number(value || 0), 1) },
      { field: 'eficiencia_pct', headerName: 'Eficiencia %', valueFormatter: ({ value }) => `${formatNumber(Number(value || 0), 1)}%` },
      { field: 'downtime_pct', headerName: 'Downtime %', valueFormatter: ({ value }) => `${formatNumber(Number(value || 0), 1)}%` },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const lineColumns = useMemo<ColDef<PackhouseLineDetailRow>[]>(
    () => [
      { field: 'linea', headerName: 'Linea' },
      { field: 'kg_procesados_tn', headerName: 'Tn', valueFormatter: ({ value }) => formatToneladas(Number(value || 0), 1) },
      { field: 'tn_hora', headerName: 'Tn/h', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 2) },
      { field: 'eficiencia_pct', headerName: 'Eficiencia %', valueFormatter: ({ value }) => `${formatNumber(Number(value || 0), 1)}%` },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const downtimeColumns = useMemo<ColDef<PackhouseDowntimeDetailRow>[]>(
    () => [
      { field: 'motivo', headerName: 'Motivo' },
      { field: 'minutos', headerName: 'Minutos', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const timeColumns = useMemo<ColDef<PackhouseTimeRow>[]>(
    () => [
      { field: 'linea', headerName: 'Linea' },
      { field: 'horas_productivas', headerName: 'Horas productivas', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 1) },
      { field: 'horas_downtime', headerName: 'Horas paradas', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 1) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  if (error && !data) {
    return (
      <Alert variant="danger" title="No se pudo cargar Packhouse">
        Revisa turnos, costos, downtime y lineas de empaque del ERP limonero.
      </Alert>
    )
  }

  if (isLoading || !data) return <PageSkeleton />

  return (
    <div className="space-y-6">
      <DashboardLead
        title="Packhouse"
        description="Control diario de empaque para ver volumen, eficiencia y paradas por linea."
        icon={Factory}
        label="Panel operativo diario"
        scopeLabel={executiveScope.label}
        scopeBadges={executiveScope.badges}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SimpleKpiCard
          label="Procesado hoy"
          value={formatToneladas(latestRow?.kg_procesados_tn || 0, 1)}
          delta={latestRow?.fecha ? formatDate(latestRow.fecha) : 'Ultimo dia'}
          detail="Volumen procesado en la ultima jornada operativa."
          tone={(latestRow?.kg_procesados_tn || 0) > 0 ? 'positive' : 'warning'}
        />
        <SimpleKpiCard
          label="Fruta por hora"
          value={`${formatNumber(frutaHora, 2)} tn/h`}
          delta="Ritmo actual"
          detail="Permite ver si el packhouse esta sosteniendo throughput suficiente."
          tone={frutaHora >= 10 ? 'positive' : frutaHora >= 8 ? 'warning' : 'danger'}
        />
        <SimpleKpiCard
          label="Costo por tn"
          value={formatCurrency(data.summary.costo_tn_ars)}
          delta={data.summary.costo_tn_delta_pct !== 0 ? `${data.summary.costo_tn_delta_pct > 0 ? '+' : ''}${formatNumber(data.summary.costo_tn_delta_pct, 1)}% vs tramo anterior` : 'Sin variacion'}
          detail="Costo total de packhouse por tonelada procesada. Incluye mano de obra, insumos y mantenimiento."
          tone={data.summary.costo_tn_delta_pct > 10 ? 'danger' : data.summary.costo_tn_delta_pct > 0 ? 'warning' : data.summary.costo_tn_ars > 0 ? 'positive' : 'neutral'}
        />
        <SimpleKpiCard
          label="Eficiencia promedio"
          value={`${formatNumber(data.summary.eficiencia_promedio_pct || 0, 1)}%`}
          delta={data.summary.eficiencia_delta_pct !== 0 ? `${data.summary.eficiencia_delta_pct > 0 ? '+' : ''}${formatNumber(data.summary.eficiencia_delta_pct, 1)} pts` : 'Sin variacion'}
          detail={data.summary.eficiencia_detail}
          tone={(data.summary.eficiencia_promedio_pct || 0) >= 78 ? 'positive' : (data.summary.eficiencia_promedio_pct || 0) >= 70 ? 'warning' : 'danger'}
        />
      </div>

      {/* KPI con torta — lineas, tiempo, estado, paradas */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniPieKpiCard
          label="Volumen por linea"
          centerValue={`${formatNumber(lineRows[0]?.kg_procesados_tn || 0, 1)} tn`}
          centerSub={lineRows[0]?.linea || ''}
          slices={(() => {
            if (!lineRows.length) return [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]
            const total = lineRows.reduce((s, r) => s + r.kg_procesados_tn, 0)
            return lineRows.slice(0, 4).map((r) => ({
              label: r.linea,
              value: total > 0 ? Math.round((r.kg_procesados_tn / total) * 100) : 0,
            }))
          })()}
          tone="neutral"
        />
        <MiniPieKpiCard
          label="Tiempo productivo vs parado"
          centerValue={(() => {
            const prod = lineRows.reduce((s, r) => s + (r.horas_productivas || 0), 0)
            const total = prod + lineRows.reduce((s, r) => s + (r.horas_downtime || 0), 0)
            return `${formatNumber(total > 0 ? (prod / total) * 100 : 0, 0)}%`
          })()}
          centerSub="Productivo"
          slices={[
            { label: 'Productivo', value: lineRows.reduce((s, r) => s + (r.horas_productivas || 0), 0), color: '#30945a' },
            { label: 'Parado', value: lineRows.reduce((s, r) => s + (r.horas_downtime || 0), 0), color: '#cf6e63' },
          ]}
          tone={(() => {
            const downtime = lineRows.reduce((s, r) => s + (r.horas_downtime || 0), 0)
            const total = downtime + lineRows.reduce((s, r) => s + (r.horas_productivas || 0), 0)
            return total > 0 && downtime / total < 0.12 ? 'positive' : 'warning'
          })()}
        />
        <MiniPieKpiCard
          label="Estado de lineas"
          centerValue={`${lineRows.filter((r) => r.estado === 'Bien').length}`}
          centerSub="Lineas OK"
          slices={[
            { label: 'Bien', value: lineRows.filter((r) => r.estado === 'Bien').length, color: '#30945a' },
            { label: 'Atencion', value: lineRows.filter((r) => r.estado === 'Atencion').length, color: '#d69f2f' },
            { label: 'Critico', value: lineRows.filter((r) => r.estado === 'Critico').length, color: '#cf6e63' },
          ]}
          tone={!lineRows.length ? 'neutral' : lineRows.some((r) => r.estado === 'Critico') ? 'danger' : lineRows.some((r) => r.estado === 'Atencion') ? 'warning' : 'positive'}
        />
        <MiniPieKpiCard
          label="Paradas por motivo"
          centerValue={`${formatNumber(downtimeRows[0]?.minutos || 0, 0)} min`}
          centerSub={downtimeRows[0]?.motivo || ''}
          slices={downtimeRows.length ? downtimeRows.slice(0, 4).map((r) => ({
            label: r.motivo,
            value: r.minutos,
          })) : [{ label: 'Sin paradas', value: 1, color: '#d8cbbb' }]}
          tone={downtimeRows.length > 0 ? 'warning' : 'positive'}
        />
      </div>

      <OperationalFocusAlert title="Foco operativo del dia" tone={focusTone} bullets={focusBullets} />

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartWithDrillDown<PackhouseDailyDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Proceso diario"
          description="Detalle diario de volumen procesado, eficiencia y downtime."
          summaryItems={[
            { label: 'Tn 30 dias', value: formatToneladas(processRows.reduce((acc, row) => acc + row.kg_procesados_tn, 0), 1) },
            { label: 'Promedio diario', value: formatToneladas(processRows.length ? processRows.reduce((acc, row) => acc + row.kg_procesados_tn, 0) / processRows.length : 0, 1) },
            { label: 'Ultimo downtime', value: `${formatNumber(latestRow?.downtime_pct || 0, 1)}%` },
            { label: 'Ultima eficiencia', value: `${formatNumber(latestRow?.eficiencia_pct || 0, 1)}%` },
          ]}
          contextText="Sirve para ver si el empaque viene sosteniendo ritmo o si ya se freno en los ultimos dias."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={dailyRows}
          detailColumns={dailyColumns}
          exportFilename="packhouse-produccion-diaria"
          detailLabel="Detalle diario del packhouse."
        >
          <SimpleChartCard
            title="Proceso diario"
            description="Serie corta para ver si el proceso acelera o pierde capacidad."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <LineChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: processRows.map((row) => row.fecha),
                  y: processRows.map((row) => row.kg_procesados_tn),
                  name: 'Procesado',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>%{y:,.1f} tn<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<PackhouseLineDetailRow>
          title="Informe ERP · Eficiencia por linea"
          description="Comparacion simple de lineas para ver donde se sostiene el proceso."
          summaryItems={[
            { label: 'Lineas', value: formatNumber(lineRows.length, 0) },
            { label: 'Mejor eficiencia', value: `${formatNumber(lineRows[0]?.eficiencia_pct || 0, 1)}%` },
            { label: 'Peor eficiencia', value: `${formatNumber(lineRows[lineRows.length - 1]?.eficiencia_pct || 0, 1)}%` },
            { label: 'Fruta/hora', value: `${formatNumber(frutaHora, 2)} tn/h` },
          ]}
          contextText="Permite ver rapido que linea esta sosteniendo la operacion y cual necesita seguimiento."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={lineRows}
          detailColumns={lineColumns}
          exportFilename="packhouse-eficiencia-linea"
          detailLabel="Eficiencia resumida por linea."
        >
          <SimpleChartCard
            title="Eficiencia por linea"
            description="Comparacion simple para ubicar rapido donde mirar."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              showLegend={false}
              data={[
                {
                  x: lineRows.map((row) => row.linea),
                  y: lineRows.map((row) => row.eficiencia_pct),
                  name: 'Eficiencia',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>%{y:.1f}%<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<PackhouseDowntimeDetailRow>
          title="Informe ERP · Paradas por motivo"
          description="Apertura simple de las paradas por motivo."
          summaryItems={[
            { label: 'Motivos', value: formatNumber(downtimeRows.length, 0) },
            { label: 'Principal paro', value: downtimeRows[0]?.motivo || 'Sin dato' },
            { label: 'Minutos', value: formatNumber(downtimeRows[0]?.minutos || 0, 0) },
            { label: 'Lineas criticas', value: formatNumber(data.summary.lineas_criticas, 0) },
          ]}
          contextText="Ayuda a ver que tipo de parada esta explicando la mayor parte del tiempo perdido."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={downtimeRows}
          detailColumns={downtimeColumns}
          exportFilename="packhouse-downtime"
          detailLabel="Detalle de downtime por motivo."
        >
          <SimpleChartCard
            title="Paradas por motivo"
            description="Comparacion clara para ver que tipo de parada pesa mas."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              horizontal
              showLegend={false}
              data={[
                {
                  x: downtimeRows.slice(0, 8).map((row) => row.motivo),
                  y: downtimeRows.slice(0, 8).map((row) => row.minutos),
                  name: 'Minutos',
                  color: '#cf6e63',
                  hovertemplate: '%{y}<br>%{x:,.0f} min<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<PackhouseTimeRow>
          className="xl:col-span-2"
          title="Informe ERP · Tiempo productivo vs parado"
          description="Comparacion simple para ver cuanto tiempo util y parado tuvo cada linea."
          summaryItems={[
            { label: 'Horas productivas', value: formatNumber(productiveVsStoppedRows.reduce((acc, row) => acc + row.horas_productivas, 0), 1) },
            { label: 'Horas paradas', value: formatNumber(productiveVsStoppedRows.reduce((acc, row) => acc + row.horas_downtime, 0), 1) },
            { label: 'Linea mas afectada', value: [...productiveVsStoppedRows].sort((a, b) => b.horas_downtime - a.horas_downtime)[0]?.linea || 'Sin dato' },
            { label: 'Estado', value: productiveVsStoppedRows.some((row) => row.estado === 'Critico') ? 'Atencion' : 'Bien' },
          ]}
          contextText="Sirve para ver rapido si las horas paradas ya le estan ganando a las horas utiles en alguna linea."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={productiveVsStoppedRows}
          detailColumns={timeColumns}
          exportFilename="packhouse-tiempo-productivo"
          detailLabel="Horas productivas y paradas por linea."
        >
          <SimpleChartCard
            title="Tiempo productivo vs parado"
            description="Comparacion simple para ver donde se pierde capacidad."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={300}
              barmode="stack"
              data={[
                {
                  x: productiveVsStoppedRows.map((row) => row.linea),
                  y: productiveVsStoppedRows.map((row) => row.horas_productivas),
                  name: 'Productivo',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>Productivo %{y:,.1f} h<extra></extra>',
                },
                {
                  x: productiveVsStoppedRows.map((row) => row.linea),
                  y: productiveVsStoppedRows.map((row) => row.horas_downtime),
                  name: 'Parado',
                  color: '#cf6e63',
                  hovertemplate: '%{x}<br>Parado %{y:,.1f} h<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>
      </div>
    </div>
  )
}

export default function PackhousePage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <PackhousePageContent />
    </Suspense>
  )
}
