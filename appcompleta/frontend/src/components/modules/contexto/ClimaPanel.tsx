'use client'

import { useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { CloudRain } from 'lucide-react'
import {
  ControlBottomGrid,
  ControlKpi,
  ControlKpiStrip,
  ControlMainGrid,
  ControlPanel,
  ControlRail,
  ControlRailMetric,
} from '@/components/dashboard-v3/ControlDashboardLayout'
import { BarChart } from '@/components/charts/BarChart'
import { BulletChart } from '@/components/charts/BulletChart'
import { LineChart } from '@/components/charts/LineChart'
import { PieChart } from '@/components/charts/PieChart'
import { ChartWithDrillDown } from '@/components/drilldown/ChartWithDrillDown'
import { TimeRangeSelector } from '@/components/filters/TimeRangeSelector'
import { AnalysisInsightsList } from '@/components/analysis/AnalysisInsightsList'
import { DeviationCard } from '@/components/analysis/DeviationCard'
import { AnalysisSection } from '@/components/panels/AnalysisSection'
import { BreakdownSection } from '@/components/panels/BreakdownSection'
import { ExecutiveSummarySection } from '@/components/panels/ExecutiveSummarySection'
import { TimeSeriesSection } from '@/components/panels/TimeSeriesSection'
import { DataSourceTag } from '@/components/ui/DataSourceTag'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { useTimeRangeQuery } from '@/hooks/useTimeRangeQuery'
import {
  computeDeviation,
  detectAnomalies,
  movingAverageProjection,
  type NumericPoint,
  type ProjectionPoint,
} from '@/lib/analysis'
import { formatNumber, formatPercent } from '@/lib/formatters'
import { filterSeriesByRange } from '@/lib/time-series'
import type {
  ClimaAlert,
  ClimaData,
  ClimaEstablecimiento,
  ClimaHistoricoDia,
  PronosticoDia,
} from '@/types/macro'

interface ClimaPanelProps {
  data?: ClimaData
  loading?: boolean
}

export function ClimaPanel({ data, loading }: ClimaPanelProps) {
  const { range, setRange } = useTimeRangeQuery('30D')
  const summary = data?.summary
  const forecast = data?.series.forecast_daily || []
  const history = useMemo(
    () => filterSeriesByRange(data?.series.historico_30d || [], range, (item) => item.fecha),
    [data?.series.historico_30d, range]
  )
  const establishments = data?.series.establecimientos || []
  const climateFilters = useMemo(
    () => [{ label: 'Periodo', value: range }],
    [range]
  )
  const rainPoints = useMemo<NumericPoint[]>(
    () =>
      history.map((item) => ({
        label: item.fecha,
        value: item.precipitacion_mm,
      })),
    [history]
  )
  const rainProjection = useMemo<ProjectionPoint[]>(
    () => movingAverageProjection(rainPoints, 5, 7),
    [rainPoints]
  )
  const rainProjectionRows = useMemo(
    () =>
      rainProjection.map((item) => ({
        fecha: item.label,
        precipitacion_mm: item.value,
        tipo: item.projected ? 'Proyección' : 'Histórico',
      })),
    [rainProjection]
  )
  const rainfallDeviation = useMemo(
    () => computeDeviation(summary?.lluvia_7d_mm || 0, summary?.lluvia_normal_7d_mm || 0),
    [summary?.lluvia_7d_mm, summary?.lluvia_normal_7d_mm]
  )
  const rainfallAnomalies = useMemo(() => {
    const points = establishments.map((item) => ({
      label: item.nombre,
      value: item.lluvia_7d_forecast_mm || 0,
    }))
    const detected = detectAnomalies(points, 0.8)
    if (detected.length) return detected
    return [...points]
      .sort((a, b) => b.value - a.value)
      .slice(0, Math.min(3, points.length))
      .map((item) => ({ ...item, zScore: 0 }))
  }, [establishments])
  const rainfallSensitivity = useMemo(
    () =>
      [-0.3, -0.15, 0, 0.15, 0.3].map((shock) => ({
        label: `${shock > 0 ? '+' : ''}${Math.round(shock * 100)}% lluvia`,
        value: Number((((summary?.lluvia_7d_mm || 0) * (1 + shock)) - (summary?.lluvia_normal_7d_mm || 0)).toFixed(1)),
      })),
    [summary?.lluvia_7d_mm, summary?.lluvia_normal_7d_mm]
  )
  const climateInsights = useMemo(() => {
    const items: string[] = []
    const nextProjection = rainProjection.find((item) => item.projected)?.value
    if (nextProjection != null) {
      items.push(
        nextProjection > (rainPoints.at(-1)?.value || 0)
          ? 'La lluvia proyectada sube y puede seguir recortando la ventana operativa.'
          : 'La lluvia proyectada afloja y mejora el margen de ejecución.'
      )
    }
    if (rainfallDeviation.deltaPct > 10) {
      items.push(`La lluvia esperada está ${formatPercent(rainfallDeviation.deltaPct)} por encima del patrón normal.`)
    } else if (rainfallDeviation.deltaPct < -10) {
      items.push(`La lluvia esperada está ${formatPercent(Math.abs(rainfallDeviation.deltaPct))} por debajo del patrón normal.`)
    } else {
      items.push('La lluvia esperada se mantiene cerca del patrón normal del período.')
    }
    if (rainfallAnomalies[0]) {
      items.push(`${rainfallAnomalies[0].label} aparece fuera del rango habitual de precipitación esperada.`)
    }
    if (summary?.recommendation) {
      items.push(summary.recommendation)
    }
    return items.slice(0, 4)
  }, [rainPoints, rainProjection, rainfallDeviation.deltaPct, rainfallAnomalies, summary?.recommendation])

  const statusPie = useMemo(() => {
    const totals = { favorable: 0, vigilancia: 0, adverso: 0 }
    for (const item of establishments) {
      const risk = (item.riesgo_operativo || '').toLowerCase()
      if (risk.includes('advers')) totals.adverso += 1
      else if (risk.includes('mixta') || risk.includes('déficit') || risk.includes('vigil')) totals.vigilancia += 1
      else totals.favorable += 1
    }
    return totals
  }, [establishments])

  const establishmentColumns = useMemo<ColDef<ClimaEstablecimiento>[]>(() => [
    { field: 'nombre', headerName: 'Establecimiento', minWidth: 150, flex: 1.1 },
    { field: 'provincia', headerName: 'Provincia', minWidth: 110, flex: 0.8 },
    { field: 'temperatura', headerName: 'Temp', minWidth: 90, flex: 0.7, type: 'numericColumn' },
    { field: 'humedad', headerName: 'Humedad', minWidth: 90, flex: 0.7, type: 'numericColumn' },
    { field: 'lluvia_30d_mm', headerName: 'Lluvia 30d', minWidth: 100, flex: 0.8, type: 'numericColumn' },
    { field: 'lluvia_7d_forecast_mm', headerName: 'Pronóstico 7d', minWidth: 110, flex: 0.8, type: 'numericColumn' },
    { field: 'ventana_operativa', headerName: 'Ventana', minWidth: 100, flex: 0.8 },
    { field: 'riesgo_operativo', headerName: 'Riesgo', minWidth: 100, flex: 0.8 },
  ], [])

  const forecastColumns = useMemo<ColDef<PronosticoDia>[]>(() => [
    { field: 'fecha', headerName: 'Fecha', minWidth: 120, flex: 0.9 },
    { field: 'condicion', headerName: 'Condición', minWidth: 140, flex: 1.1 },
    { field: 'temp_max', headerName: 'Temp. max', minWidth: 90, flex: 0.7, type: 'numericColumn' },
    { field: 'temp_min', headerName: 'Temp. min', minWidth: 90, flex: 0.7, type: 'numericColumn' },
    { field: 'humedad_promedio', headerName: 'Humedad', minWidth: 100, flex: 0.8, type: 'numericColumn' },
    { field: 'precipitacion_mm', headerName: 'Lluvia', minWidth: 90, flex: 0.7, type: 'numericColumn' },
    { field: 'ventana_operativa', headerName: 'Ventana', minWidth: 100, flex: 0.8 },
  ], [])

  const historyColumns = useMemo<ColDef<ClimaHistoricoDia>[]>(() => [
    { field: 'fecha', headerName: 'Fecha', minWidth: 120, flex: 0.9 },
    { field: 'precipitacion_mm', headerName: 'Lluvia', minWidth: 90, flex: 0.8, type: 'numericColumn' },
    { field: 'temp_max', headerName: 'Temp. max', minWidth: 90, flex: 0.8, type: 'numericColumn' },
    { field: 'temp_min', headerName: 'Temp. min', minWidth: 90, flex: 0.8, type: 'numericColumn' },
    { field: 'temp_media', headerName: 'Temp. media', minWidth: 100, flex: 0.8, type: 'numericColumn' },
  ], [])

  const alertColumns = useMemo<ColDef<ClimaAlert>[]>(() => [
    { field: 'tipo', headerName: 'Tipo', minWidth: 120, flex: 0.8 },
    { field: 'mensaje', headerName: 'Mensaje', minWidth: 280, flex: 1.8 },
    { field: 'severidad', headerName: 'Severidad', minWidth: 100, flex: 0.8 },
  ], [])
  const projectionColumns = useMemo<ColDef<{ fecha: string; precipitacion_mm: number; tipo: string }>[]>(() => [
    { field: 'fecha', headerName: 'Fecha', minWidth: 110, flex: 0.9 },
    {
      field: 'precipitacion_mm',
      headerName: 'Lluvia',
      minWidth: 100,
      flex: 0.9,
      type: 'numericColumn',
      valueFormatter: (params) => `${formatNumber(params.value, 1)} mm`,
    },
    { field: 'tipo', headerName: 'Serie', minWidth: 110, flex: 0.8 },
  ], [])
  const anomalyColumns = useMemo<ColDef<{ label: string; value: number; zScore: number }>[]>(() => [
    { field: 'label', headerName: 'Establecimiento', minWidth: 150, flex: 1.1 },
    {
      field: 'value',
      headerName: 'Lluvia 7d',
      minWidth: 110,
      flex: 0.9,
      type: 'numericColumn',
      valueFormatter: (params) => `${formatNumber(params.value, 1)} mm`,
    },
    {
      field: 'zScore',
      headerName: 'Desvío',
      minWidth: 100,
      flex: 0.8,
      type: 'numericColumn',
      valueFormatter: (params) => formatNumber(params.value, 2),
    },
  ], [])
  const sensitivityColumns = useMemo<ColDef<{ label: string; value: number }>[]>(() => [
    { field: 'label', headerName: 'Escenario', minWidth: 120, flex: 0.9 },
    {
      field: 'value',
      headerName: 'Vs normal',
      minWidth: 120,
      flex: 1,
      type: 'numericColumn',
      valueFormatter: (params) => `${formatNumber(params.value, 1)} mm`,
    },
  ], [])

  if (loading && !data) {
    return <SkeletonBlock className="h-[62rem] w-full rounded-[2rem]" />
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
        <div className="flex h-8 w-8 items-center justify-center rounded-2xl border border-border/70 bg-[#f7f3ea] text-primary-700">
          <CloudRain className="h-4 w-4" />
        </div>
        Climate decision board
      </div>

      <ExecutiveSummarySection description="Lectura ejecutiva del clima operativo para decidir ventanas de labor, riesgo de atraso y presión sobre rendimiento.">
        <ControlKpiStrip className="border-0 bg-transparent px-0 py-0">
        <ControlKpi label="Lluvia 72h" value={summary ? `${formatNumber(summary.lluvia_72h_mm, 0)} mm` : '—'} subtitle={summary?.establecimiento_referencia || 'Establecimiento de referencia'} tone={summary && summary.lluvia_72h_mm > 30 ? 'critical' : summary && summary.lluvia_72h_mm > 12 ? 'warning' : 'positive'} />
        <ControlKpi label="Lluvia 7d" value={summary ? `${formatNumber(summary.lluvia_7d_mm, 0)} mm` : '—'} subtitle={summary ? `${formatNumber(summary.lluvia_normal_7d_mm, 0)} mm normal` : 'Pronóstico acumulado'} tone="neutral" />
        <ControlKpi label="Lluvia 30d" value={summary ? `${formatNumber(summary.lluvia_30d_mm, 0)} mm` : '—'} subtitle="Histórico reciente" tone="neutral" />
        <ControlKpi label="Anomalía" value={summary ? formatPercent(summary.anomalia_lluvia_7d_pct) : '—'} subtitle="Vs patrón reciente" tone={summary && summary.anomalia_lluvia_7d_pct < -30 ? 'warning' : summary && summary.anomalia_lluvia_7d_pct > 45 ? 'critical' : 'positive'} />
        <ControlKpi label="Humedad" value={summary ? `${formatNumber(summary.humedad_promedio_pct, 0)}%` : '—'} subtitle={summary ? `${formatNumber(summary.temperatura_promedio_7d_c, 1)}°C promedio` : 'Condición ambiente'} tone="neutral" />
        <ControlKpi label="Riesgo operativo" value={summary?.riesgo_operativo || '—'} subtitle={summary?.recommendation || 'Lectura de labores'} tone={summary?.recommendation_severity === 'critical' ? 'critical' : summary?.recommendation_severity === 'warning' ? 'warning' : 'positive'} />
        </ControlKpiStrip>
      </ExecutiveSummarySection>

      <TimeSeriesSection
        description="Serie climática reciente para entender si lluvia y temperatura están habilitando o frenando la ejecución."
        actions={<TimeRangeSelector value={range} onChange={setRange} />}
      >
      <ControlMainGrid
        main={
          <ControlPanel
            title="Histórico climático 30 días"
            description="Lluvia y temperatura media para poner el pronóstico en contexto."
            meta={<DataSourceTag fuente={data?.fuente || 'Clima'} ultimaActualizacion={data?.ultima_actualizacion} />}
          >
            <ChartWithDrillDown<ClimaHistoricoDia>
              title="Histórico climático"
              description="Serie de lluvia y temperatura media de los últimos 30 días."
              formula="Agregación diaria por establecimiento de referencia"
              source={data?.fuente}
              lastUpdated={data?.ultima_actualizacion}
              filtersApplied={[{ label: 'Periodo', value: range }]}
              detailRows={history}
              detailColumns={historyColumns}
              exportFilename="clima-historico"
            >
              <LineChart
                height={340}
                data={[
                  { x: history.map((item) => item.fecha), y: history.map((item) => item.precipitacion_mm), name: 'Lluvia', color: '#1f6b42' },
                  { x: history.map((item) => item.fecha), y: history.map((item) => item.temp_media), name: 'Temp. media', color: '#b6aa97' },
                ]}
                yAxisTitle="nivel"
              />
            </ChartWithDrillDown>
          </ControlPanel>
        }
        rail={
          <ControlRail>
            <ControlRailMetric
              label="Ventana operativa"
              value={summary?.ventana_operativa || '—'}
              detail={summary?.ventana_detalle || 'Sin detalle'}
              tone={summary?.recommendation_severity === 'critical' ? 'critical' : summary?.recommendation_severity === 'warning' ? 'warning' : 'positive'}
              visual={<BulletChart value={Math.max(0, 100 - Math.abs(summary?.anomalia_lluvia_7d_pct || 0))} target={70} max={100} label="estabilidad operativa" />}
            />
            <ControlRailMetric
              label="Riesgo"
              value={summary?.riesgo_operativo || '—'}
              detail={summary?.riesgo_operativo_detalle || 'Sin lectura'}
              tone={summary?.recommendation_severity === 'critical' ? 'critical' : summary?.recommendation_severity === 'warning' ? 'warning' : 'positive'}
            />
            <ControlRailMetric
              label="Próximas 48h"
              value={`${formatNumber(forecast.slice(0, 2).reduce((acc, item) => acc + item.precipitacion_mm, 0), 0)} mm`}
              detail={forecast[0]?.ventana_operativa || 'Sin pronóstico operativo'}
              tone={forecast.slice(0, 2).reduce((acc, item) => acc + item.precipitacion_mm, 0) > 20 ? 'critical' : 'neutral'}
            />
            <ControlRailMetric
              label="Establecimientos con alerta"
              value={`${summary?.establecimientos_con_alerta || 0}`}
              detail={data?.alerts?.[0]?.mensaje || 'Sin alertas climáticas abiertas'}
              tone={(summary?.establecimientos_con_alerta || 0) > 1 ? 'warning' : 'positive'}
            />
          </ControlRail>
        }
      />
      </TimeSeriesSection>

      <BreakdownSection description="Apertura del frente climático en pronóstico, estado por establecimiento, ranking y alertas activas.">
        <div className="space-y-5">
      <ControlBottomGrid>
        <ControlPanel
          title="Pronóstico de precipitación"
          description="Lluvia diaria prevista para decidir siembra, tránsito o pulverización."
        >
          <ChartWithDrillDown<PronosticoDia>
            title="Pronóstico diario"
            description="Pronóstico diario con lluvia, temperatura y ventana."
            formula="Serie diaria provista por API climática"
            source={data?.fuente}
            lastUpdated={data?.ultima_actualizacion}
            detailRows={forecast}
            detailColumns={forecastColumns}
            exportFilename="clima-pronostico"
          >
            <BarChart
              height={300}
              showLegend={false}
              data={[
                {
                  x: forecast.map((item) => item.fecha),
                  y: forecast.map((item) => item.precipitacion_mm),
                  name: 'Lluvia',
                  color: '#2f8a57',
                },
              ]}
              yAxisTitle="mm"
            />
          </ChartWithDrillDown>
        </ControlPanel>

        <ControlPanel
          title="Estado por establecimiento"
          description="Distribución compacta de establecimientos favorables, en vigilancia y adversos."
        >
          <ChartWithDrillDown<ClimaEstablecimiento>
            title="Estado de establecimientos"
            description="Detalle por establecimiento y riesgo operativo."
            formula="Conteo simple por riesgo operativo"
            source={data?.fuente}
            lastUpdated={data?.ultima_actualizacion}
            detailRows={establishments}
            detailColumns={establishmentColumns}
            exportFilename="clima-establecimientos"
          >
            <PieChart
              height={300}
              labels={['Favorable', 'Vigilancia', 'Adverso']}
              values={[statusPie.favorable, statusPie.vigilancia, statusPie.adverso]}
              colors={['#2f8a57', '#b38a3d', '#cf6e63']}
            />
          </ChartWithDrillDown>
        </ControlPanel>
      </ControlBottomGrid>

      <ControlPanel
        title="Ranking por establecimiento"
        description="Pronóstico 7d por establecimiento para priorizar dónde puede frenarse la ejecución."
        meta={<DataSourceTag fuente={data?.fuente || 'Clima'} ultimaActualizacion={data?.ultima_actualizacion} />}
      >
        <ChartWithDrillDown<ClimaEstablecimiento>
          title="Ranking por establecimiento"
          description="Detalle de la lectura climática por establecimiento."
          formula="Orden descendente por lluvia pronosticada 7d"
          source={data?.fuente}
          lastUpdated={data?.ultima_actualizacion}
          detailRows={establishments}
          detailColumns={establishmentColumns}
          exportFilename="clima-ranking-establecimientos"
        >
          <BarChart
            height={320}
            horizontal
            showLegend={false}
            data={[
              {
                x: [...establishments].sort((a, b) => (b.lluvia_7d_forecast_mm || 0) - (a.lluvia_7d_forecast_mm || 0)).map((item) => item.nombre),
                y: [...establishments].sort((a, b) => (b.lluvia_7d_forecast_mm || 0) - (a.lluvia_7d_forecast_mm || 0)).map((item) => item.lluvia_7d_forecast_mm || 0),
                name: 'Pronóstico 7d',
                color: '#2f8a57',
              },
            ]}
            xAxisTitle="mm"
          />
        </ChartWithDrillDown>
      </ControlPanel>

      {data?.alerts?.length ? (
        <ControlPanel
          title="Alertas climáticas"
          description="Detalle corto del motor de alertas climáticas para auditar la lectura del tablero."
        >
          <ChartWithDrillDown<ClimaAlert>
            title="Alertas climáticas"
            description="Detalle de alertas activas del frente climático."
            formula="Priorización por severidad"
            source={data?.fuente}
            lastUpdated={data?.ultima_actualizacion}
            detailRows={data.alerts}
            detailColumns={alertColumns}
            exportFilename="clima-alertas"
            openOnContentClick={false}
          >
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {data.alerts.slice(0, 3).map((item) => (
                <div key={`${item.tipo}-${item.mensaje}`} className="rounded-[1.35rem] border border-border/70 bg-[#fbf8f2] p-4">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">{item.severidad}</p>
                  <p className="mt-2 text-sm font-semibold text-text">{item.tipo}</p>
                  <p className="mt-1 text-sm leading-5 text-text-muted">{item.mensaje}</p>
                </div>
              ))}
            </div>
          </ChartWithDrillDown>
        </ControlPanel>
      ) : null}
        </div>
      </BreakdownSection>

      <AnalysisSection description="Proyección simple de lluvia, desvío contra normal, focos fuera de rango y sensibilidad del frente hídrico sobre la operación.">
        <div className="space-y-5">
          <ControlMainGrid
            main={
              <ControlPanel
                title="Proyección de lluvia"
                description="Extiende el patrón reciente para anticipar si la ventana operativa mejora o empeora."
                meta={<DataSourceTag fuente={data?.fuente || 'Clima'} ultimaActualizacion={data?.ultima_actualizacion} />}
              >
                <ChartWithDrillDown<{ fecha: string; precipitacion_mm: number; tipo: string }>
                  title="Proyección de lluvia"
                  description="Histórico reciente y proyección simple de precipitación."
                  formula="Media móvil simple sobre precipitación diaria"
                  source={data?.fuente}
                  lastUpdated={data?.ultima_actualizacion}
                  filtersApplied={climateFilters}
                  detailRows={rainProjectionRows}
                  detailColumns={projectionColumns}
                  exportFilename="clima-analisis-proyeccion"
                >
                  <LineChart
                    height={340}
                    data={[
                      {
                        x: rainProjection.filter((item) => !item.projected).map((item) => item.label),
                        y: rainProjection.filter((item) => !item.projected).map((item) => item.value),
                        name: 'Histórico',
                        color: '#1f6b42',
                      },
                      {
                        x: rainProjection.filter((item) => item.projected).map((item) => item.label),
                        y: rainProjection.filter((item) => item.projected).map((item) => item.value),
                        name: 'Proyección',
                        color: '#b6aa97',
                        dashed: true,
                      },
                    ]}
                    yAxisTitle="mm"
                  />
                </ChartWithDrillDown>
              </ControlPanel>
            }
            rail={
              <ControlRail className="grid-cols-1">
                <DeviationCard
                  label="Lluvia vs normal"
                  actualLabel="Esperada 7d"
                  expectedLabel="Normal"
                  actual={`${formatNumber(rainfallDeviation.actual, 1)} mm`}
                  expected={`${formatNumber(rainfallDeviation.expected, 1)} mm`}
                  delta={`${formatNumber(rainfallDeviation.delta, 1)} mm`}
                  deltaPct={rainfallDeviation.deltaPct}
                />
                <AnalysisInsightsList items={climateInsights} />
              </ControlRail>
            }
          />

          <ControlBottomGrid>
            <ControlPanel
              title="Establecimientos fuera de rango"
              description="Pronóstico de lluvia 7d fuera del patrón relativo del resto de la red."
            >
              <ChartWithDrillDown<{ label: string; value: number; zScore: number }>
                title="Anomalías por establecimiento"
                description="Establecimientos con lluvia pronosticada fuera del rango esperado."
                formula="Detección simple por desvío estándar"
                source={data?.fuente}
                lastUpdated={data?.ultima_actualizacion}
                filtersApplied={climateFilters}
                detailRows={rainfallAnomalies}
                detailColumns={anomalyColumns}
                exportFilename="clima-anomalias"
              >
                <BarChart
                  height={280}
                  horizontal
                  showLegend={false}
                  data={[
                    {
                      x: rainfallAnomalies.map((item) => item.label),
                      y: rainfallAnomalies.map((item) => item.value),
                      name: 'Lluvia 7d',
                      color: '#cf6e63',
                    },
                  ]}
                  xAxisTitle="mm"
                />
              </ChartWithDrillDown>
            </ControlPanel>

            <ControlPanel
              title="Sensibilidad hídrica"
              description="Cómo cambia el exceso o déficit de lluvia si el frente se intensifica o afloja."
            >
              <ChartWithDrillDown<{ label: string; value: number }>
                title="Sensibilidad de lluvia"
                description="Shock simple de lluvia acumulada frente al patrón normal."
                formula="(lluvia 7d * shock) - lluvia normal"
                source={data?.fuente}
                lastUpdated={data?.ultima_actualizacion}
                filtersApplied={climateFilters}
                detailRows={rainfallSensitivity}
                detailColumns={sensitivityColumns}
                exportFilename="clima-sensibilidad"
              >
                <BarChart
                  height={280}
                  showLegend={false}
                  data={[
                    {
                      x: rainfallSensitivity.map((item) => item.label),
                      y: rainfallSensitivity.map((item) => item.value),
                      name: 'Vs normal',
                      color: '#2f8a57',
                    },
                  ]}
                  yAxisTitle="mm"
                />
              </ChartWithDrillDown>
            </ControlPanel>
          </ControlBottomGrid>
        </div>
      </AnalysisSection>
    </div>
  )
}
