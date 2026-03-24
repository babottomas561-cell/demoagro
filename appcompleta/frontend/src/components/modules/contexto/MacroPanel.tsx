'use client'

import { useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { Landmark } from 'lucide-react'
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
  buildSensitivityScenarios,
  computeDeviation,
  detectAnomalies,
  movingAverageProjection,
  type NumericPoint,
  type ProjectionPoint,
} from '@/lib/analysis'
import { formatCurrency, formatNumber, formatPercent } from '@/lib/formatters'
import { filterSeriesByRange } from '@/lib/time-series'
import type {
  MacroAlert,
  MacroCapitalImpactRow,
  MacroData,
  MacroFxPoint,
  MacroInflationPoint,
  MacroRatePoint,
} from '@/types/macro'

interface MacroPanelProps {
  data?: MacroData
  loading?: boolean
}

export function MacroPanel({ data, loading }: MacroPanelProps) {
  const { range, setRange } = useTimeRangeQuery('12M')
  const summary = data?.summary
  const fxRows = useMemo(
    () => filterSeriesByRange(data?.series.fx || [], range, (item) => item.fecha),
    [data?.series.fx, range]
  )
  const inflationRows = useMemo(
    () => filterSeriesByRange(data?.series.inflacion || [], range, (item) => item.fecha),
    [data?.series.inflacion, range]
  )
  const rateRows = useMemo(
    () => filterSeriesByRange(data?.series.tasa || [], range, (item) => item.fecha),
    [data?.series.tasa, range]
  )
  const capitalRows = data?.series.impacto_capital_trabajo || []
  const macroFilters = useMemo(
    () => [{ label: 'Periodo', value: range }],
    [range]
  )
  const fxPoints = useMemo<NumericPoint[]>(
    () =>
      fxRows
        .filter((item) => item.tipo_cambio_oficial != null)
        .map((item) => ({
          label: item.fecha,
          value: item.tipo_cambio_oficial || 0,
        })),
    [fxRows]
  )
  const fxProjection = useMemo<ProjectionPoint[]>(
    () => movingAverageProjection(fxPoints, 5, 5),
    [fxPoints]
  )
  const fxProjectionRows = useMemo(
    () =>
      fxProjection.map((item) => ({
        fecha: item.label,
        valor: item.value,
        tipo: item.projected ? 'Proyección' : 'Histórico',
      })),
    [fxProjection]
  )
  const financingDeviation = useMemo(
    () => computeDeviation(summary?.costo_financiero_90d_pct || 0, 5),
    [summary?.costo_financiero_90d_pct]
  )
  const inflationAnomalies = useMemo(() => {
    const points = inflationRows.map((item) => ({
      label: item.fecha,
      value: item.inflacion_mensual,
    }))
    const detected = detectAnomalies(points, 0.9)
    if (detected.length) return detected
    return [...points]
      .sort((a, b) => b.value - a.value)
      .slice(0, 3)
      .map((item) => ({ ...item, zScore: 0 }))
  }, [inflationRows])
  const financingSensitivity = useMemo(
    () =>
      buildSensitivityScenarios(capitalRows[0]?.costo_financiero_90d_ars || 0, [-0.15, -0.05, 0, 0.05, 0.15]).map((item) => ({
        ...item,
        label: `${item.label} tasa`,
      })),
    [capitalRows]
  )
  const macroInsights = useMemo(() => {
    const items: string[] = []
    const projectedFx = fxProjection.find((item) => item.projected)?.value
    if (projectedFx != null) {
      items.push(
        projectedFx > (fxPoints.at(-1)?.value || 0)
          ? 'El tipo de cambio oficial proyecta una deriva alcista de corto plazo.'
          : 'El tipo de cambio oficial se mantiene estable en el corto plazo.'
      )
    }
    if (financingDeviation.deltaPct > 5) {
      items.push(`El costo financiero está ${formatPercent(financingDeviation.deltaPct)} por encima del umbral gerencial.`)
    } else {
      items.push('El costo financiero se mantiene cerca del umbral esperado para capital de trabajo.')
    }
    if (inflationAnomalies[0]) {
      items.push(`${inflationAnomalies[0].label} quedó fuera del rango normal de inflación mensual.`)
    }
    if (summary?.recommendation) {
      items.push(summary.recommendation)
    }
    return items.slice(0, 4)
  }, [financingDeviation.deltaPct, fxPoints, fxProjection, inflationAnomalies, summary?.recommendation])

  const alertPie = useMemo(() => {
    const totals = { favorable: 0, warning: 0, critical: 0 }
    for (const item of data?.alerts || []) {
      if (item.severidad === 'critical') totals.critical += 1
      else if (item.severidad === 'warning') totals.warning += 1
      else totals.favorable += 1
    }
    return totals
  }, [data?.alerts])

  const fxColumns = useMemo<ColDef<MacroFxPoint>[]>(() => [
    { field: 'fecha', headerName: 'Fecha', minWidth: 110, flex: 0.9 },
    { field: 'tipo_cambio_oficial', headerName: 'TC oficial', minWidth: 110, flex: 0.9, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value) },
    { field: 'tipo_cambio_mayorista', headerName: 'TC mayorista', minWidth: 120, flex: 1, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value) },
    { field: 'spread_cambiario_pct', headerName: 'Spread', minWidth: 100, flex: 0.8, valueFormatter: (params) => formatPercent(params.value) },
  ], [])

  const inflationColumns = useMemo<ColDef<MacroInflationPoint>[]>(() => [
    { field: 'fecha', headerName: 'Fecha', minWidth: 110, flex: 0.9 },
    { field: 'inflacion_mensual', headerName: 'Inflación', minWidth: 110, flex: 0.9, type: 'numericColumn', valueFormatter: (params) => formatPercent(params.value) },
  ], [])

  const capitalColumns = useMemo<ColDef<MacroCapitalImpactRow>[]>(() => [
    { field: 'escenario', headerName: 'Escenario', minWidth: 170, flex: 1.2 },
    { field: 'capital_trabajo_ars', headerName: 'Capital', minWidth: 120, flex: 1, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value) },
    { field: 'costo_financiero_90d_pct', headerName: 'Costo 90d %', minWidth: 110, flex: 0.8, type: 'numericColumn', valueFormatter: (params) => formatPercent(params.value) },
    { field: 'costo_financiero_90d_ars', headerName: 'Costo 90d', minWidth: 120, flex: 1, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value) },
  ], [])

  const alertColumns = useMemo<ColDef<MacroAlert>[]>(() => [
    { field: 'titulo', headerName: 'Alerta', minWidth: 170, flex: 1.1 },
    { field: 'descripcion', headerName: 'Descripción', minWidth: 280, flex: 1.8 },
    { field: 'recommendation', headerName: 'Acción', minWidth: 220, flex: 1.3 },
    { field: 'severidad', headerName: 'Severidad', minWidth: 100, flex: 0.8 },
  ], [])
  const projectionColumns = useMemo<ColDef<{ fecha: string; valor: number; tipo: string }>[]>(() => [
    { field: 'fecha', headerName: 'Fecha', minWidth: 110, flex: 0.9 },
    {
      field: 'valor',
      headerName: 'TC oficial',
      minWidth: 120,
      flex: 1,
      type: 'numericColumn',
      valueFormatter: (params) => formatCurrency(params.value),
    },
    { field: 'tipo', headerName: 'Serie', minWidth: 110, flex: 0.8 },
  ], [])
  const anomalyColumns = useMemo<ColDef<{ label: string; value: number; zScore: number }>[]>(() => [
    { field: 'label', headerName: 'Mes', minWidth: 110, flex: 0.8 },
    {
      field: 'value',
      headerName: 'Inflación',
      minWidth: 110,
      flex: 0.9,
      type: 'numericColumn',
      valueFormatter: (params) => formatPercent(params.value),
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
      headerName: 'Costo 90d',
      minWidth: 120,
      flex: 1,
      type: 'numericColumn',
      valueFormatter: (params) => formatCurrency(params.value),
    },
  ], [])

  if (loading && !data) {
    return <SkeletonBlock className="h-[62rem] w-full rounded-[2rem]" />
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
        <div className="flex h-8 w-8 items-center justify-center rounded-2xl border border-border/70 bg-[#f7f3ea] text-primary-700">
          <Landmark className="h-4 w-4" />
        </div>
        Macro decision board
      </div>

      <ExecutiveSummarySection description="Síntesis macro para gerencia sobre dólar, inflación, tasas y costo financiero antes de bajar al detalle de impacto.">
        <ControlKpiStrip className="border-0 bg-transparent px-0 py-0">
        <ControlKpi label="TC oficial" value={summary ? formatCurrency(summary.tipo_cambio_oficial) : '—'} subtitle="Paridad oficial" delta={summary ? formatPercent(summary.tc_oficial_var_30d_pct) : undefined} tone="neutral" />
        <ControlKpi label="TC mayorista" value={summary ? formatCurrency(summary.tipo_cambio_mayorista) : '—'} subtitle="Paridad mayorista" delta={summary ? formatPercent(summary.tc_mayorista_var_30d_pct) : undefined} tone="neutral" />
        <ControlKpi label="Spread" value={summary ? formatPercent(summary.spread_cambiario_pct) : '—'} subtitle="Brecha oficial vs mayorista" tone={summary && summary.spread_cambiario_pct > 6 ? 'warning' : 'positive'} />
        <ControlKpi label="Inflación mensual" value={summary ? formatPercent(summary.inflacion_mensual) : '—'} subtitle={summary ? `${formatPercent(summary.inflacion_interanual)} interanual` : 'Inflación observada'} tone={summary && summary.inflacion_delta_vs_3m < 0 ? 'positive' : 'warning'} />
        <ControlKpi label="Tasa referencia" value={summary ? formatPercent(summary.tasa_politica_monetaria) : '—'} subtitle={summary ? `${formatPercent(summary.tasa_real_pct)} real` : 'Costo nominal del dinero'} tone={summary && summary.tasa_real_pct > 5 ? 'warning' : 'neutral'} />
        <ControlKpi label="Costo 90d" value={summary ? formatPercent(summary.costo_financiero_90d_pct) : '—'} subtitle={summary?.recommendation || 'Lectura financiera de campaña'} tone={summary && summary.recommendation_tag === 'riesgo' ? 'critical' : summary && summary.recommendation_tag === 'neutral' ? 'warning' : 'positive'} />
        </ControlKpiStrip>
      </ExecutiveSummarySection>

      <TimeSeriesSection
        description="Seguimiento temporal de dólar, inflación y tasa para ver si el contexto mejora o complica la campaña."
        actions={<TimeRangeSelector value={range} onChange={setRange} />}
      >
      <ControlMainGrid
        main={
          <ControlPanel
            title="Tipo de cambio"
            description="Serie base de oficial y mayorista para seguir estabilidad nominal y spread."
            meta={<DataSourceTag fuente={data?.fuente || 'Contexto macro'} ultimaActualizacion={data?.ultima_actualizacion} />}
          >
            <ChartWithDrillDown<MacroFxPoint>
              title="Tipo de cambio"
              description="Histórico reciente de tipo de cambio oficial, mayorista y spread."
              formula="spread = (tc_mayorista - tc_oficial) / tc_oficial"
              source={data?.fuente}
              lastUpdated={data?.ultima_actualizacion}
              filtersApplied={[{ label: 'Periodo', value: range }]}
              detailRows={fxRows}
              detailColumns={fxColumns}
              exportFilename="macro-fx"
            >
              <LineChart
                height={340}
                data={[
                  { x: fxRows.map((item) => item.fecha), y: fxRows.map((item) => item.tipo_cambio_oficial), name: 'Oficial', color: '#1f6b42' },
                  { x: fxRows.map((item) => item.fecha), y: fxRows.map((item) => item.tipo_cambio_mayorista), name: 'Mayorista', color: '#b6aa97' },
                ]}
                yAxisTitle="ARS/USD"
              />
            </ChartWithDrillDown>
          </ControlPanel>
        }
        rail={
          <ControlRail>
            <ControlRailMetric
              label="Costo financiero"
              value={summary ? formatPercent(summary.costo_financiero_90d_pct) : '—'}
              detail="Costo estimado de financiamiento a 90 días"
              tone={summary && summary.costo_financiero_90d_pct > 10 ? 'critical' : summary && summary.costo_financiero_90d_pct > 5 ? 'warning' : 'positive'}
              visual={<BulletChart value={summary?.costo_financiero_90d_pct || 0} target={5} max={15} label="umbral 5%" />}
            />
            <ControlRailMetric
              label="Tasa real"
              value={summary ? formatPercent(summary.tasa_real_pct) : '—'}
              detail={summary ? `${formatPercent(summary.inflacion_promedio_3m)} inflación promedio 3m` : 'Sin lectura'}
              tone={summary && summary.tasa_real_pct > 4 ? 'warning' : 'positive'}
            />
            <ControlRailMetric
              label="Reservas"
              value={summary ? `USD ${formatNumber(summary.reservas_internacionales / 1_000_000_000, 1)}B` : '—'}
              detail={summary ? `${formatPercent(summary.actividad_proxi_var_pct)} de actividad proxy` : 'Reservas internacionales'}
              tone="neutral"
            />
            <ControlRailMetric
              label="Lectura gerente"
              value={summary?.recommendation_tag || 'sin lectura'}
              detail={summary?.recommendation || 'Sin recomendación consolidada'}
              tone={summary?.recommendation_tag === 'riesgo' ? 'critical' : summary?.recommendation_tag === 'neutral' ? 'warning' : 'positive'}
            />
          </ControlRail>
        }
      />
      </TimeSeriesSection>

      <BreakdownSection description="Desagregación del contexto en inflación, semáforos e impacto económico sobre el capital de trabajo.">
        <div className="space-y-5">
      <ControlBottomGrid>
        <ControlPanel
          title="Inflación vs tasa"
          description="Lectura simple para entender si el costo financiero acompaña o supera la desaceleración de precios."
        >
          <ChartWithDrillDown<MacroInflationPoint>
            title="Inflación vs tasa"
            description="Inflación mensual y tasa de referencia."
            formula="Comparación simple entre inflación mensual y tasa de referencia"
            source={data?.fuente}
            lastUpdated={data?.ultima_actualizacion}
            filtersApplied={[{ label: 'Periodo', value: range }]}
            detailRows={inflationRows}
            detailColumns={inflationColumns}
            exportFilename="macro-inflacion-tasa"
          >
            <LineChart
              height={300}
              data={[
                { x: inflationRows.map((item) => item.fecha), y: inflationRows.map((item) => item.inflacion_mensual), name: 'Inflación', color: '#b6aa97' },
                { x: rateRows.map((item) => item.fecha), y: rateRows.map((item) => item.valor), name: 'Tasa', color: '#1f6b42' },
              ]}
              yAxisTitle="%"
            />
          </ChartWithDrillDown>
        </ControlPanel>

        <ControlPanel
          title="Semáforo macro"
          description="Distribución simple entre alertas favorables, en vigilancia y críticas."
        >
          <ChartWithDrillDown<MacroAlert>
            title="Semáforo macro"
            description="Detalle de alertas macro detrás de la lectura actual."
            formula="Conteo simple por severidad"
            source={data?.fuente}
            lastUpdated={data?.ultima_actualizacion}
            detailRows={data?.alerts || []}
            detailColumns={alertColumns}
            exportFilename="macro-alertas"
          >
            <PieChart
              height={300}
              labels={['Favorable', 'Vigilancia', 'Crítico']}
              values={[alertPie.favorable, alertPie.warning, alertPie.critical]}
              colors={['#2f8a57', '#b38a3d', '#cf6e63']}
            />
          </ChartWithDrillDown>
        </ControlPanel>
      </ControlBottomGrid>

      <ControlPanel
        title="Impacto sobre capital de trabajo"
        description="Escenarios de costo financiero ordenados por impacto económico."
        meta={<DataSourceTag fuente={data?.fuente || 'Contexto macro'} ultimaActualizacion={data?.ultima_actualizacion} />}
      >
        <ChartWithDrillDown<MacroCapitalImpactRow>
          title="Impacto sobre capital de trabajo"
          description="Escenarios de capital de trabajo y costo financiero a 90 días."
          formula="costo 90d = capital de trabajo * costo financiero 90d %"
          source={data?.fuente}
          lastUpdated={data?.ultima_actualizacion}
          detailRows={capitalRows}
          detailColumns={capitalColumns}
          exportFilename="macro-capital-impacto"
        >
          <BarChart
            height={320}
            horizontal
            showLegend={false}
            data={[
              {
                x: capitalRows.map((item) => item.escenario),
                y: capitalRows.map((item) => item.costo_financiero_90d_ars),
                name: 'Costo 90d',
                color: '#2f8a57',
              },
            ]}
            xAxisTitle="ARS"
          />
        </ChartWithDrillDown>
      </ControlPanel>
        </div>
      </BreakdownSection>

      <AnalysisSection description="Proyección simple de tipo de cambio, control de costo financiero, meses fuera de rango y sensibilidad del capital de trabajo frente a cambios de tasa.">
        <div className="space-y-5">
          <ControlMainGrid
            main={
              <ControlPanel
                title="Proyección de tipo de cambio oficial"
                description="Extiende la serie reciente para anticipar presión nominal de corto plazo."
                meta={<DataSourceTag fuente={data?.fuente || 'Contexto macro'} ultimaActualizacion={data?.ultima_actualizacion} />}
              >
                <ChartWithDrillDown<{ fecha: string; valor: number; tipo: string }>
                  title="Proyección de tipo de cambio"
                  description="Histórico y proyección simple del tipo de cambio oficial."
                  formula="Media móvil simple sobre la serie reciente"
                  source={data?.fuente}
                  lastUpdated={data?.ultima_actualizacion}
                  filtersApplied={macroFilters}
                  detailRows={fxProjectionRows}
                  detailColumns={projectionColumns}
                  exportFilename="macro-analisis-proyeccion"
                >
                  <LineChart
                    height={340}
                    data={[
                      {
                        x: fxProjection.filter((item) => !item.projected).map((item) => item.label),
                        y: fxProjection.filter((item) => !item.projected).map((item) => item.value),
                        name: 'Histórico',
                        color: '#1f6b42',
                      },
                      {
                        x: fxProjection.filter((item) => item.projected).map((item) => item.label),
                        y: fxProjection.filter((item) => item.projected).map((item) => item.value),
                        name: 'Proyección',
                        color: '#b6aa97',
                        dashed: true,
                      },
                    ]}
                    yAxisTitle="ARS/USD"
                  />
                </ChartWithDrillDown>
              </ControlPanel>
            }
            rail={
              <ControlRail className="grid-cols-1">
                <DeviationCard
                  label="Costo financiero vs umbral"
                  actualLabel="Actual"
                  expectedLabel="Umbral"
                  actual={formatPercent(financingDeviation.actual)}
                  expected={formatPercent(financingDeviation.expected)}
                  delta={formatPercent(financingDeviation.delta)}
                  deltaPct={financingDeviation.deltaPct}
                />
                <AnalysisInsightsList items={macroInsights} />
              </ControlRail>
            }
          />

          <ControlBottomGrid>
            <ControlPanel
              title="Meses fuera de rango"
              description="Lectura rápida de meses con inflación mensual anómala frente a la serie reciente."
            >
              <ChartWithDrillDown<{ label: string; value: number; zScore: number }>
                title="Anomalías inflacionarias"
                description="Meses con inflación fuera del rango esperado."
                formula="Detección simple por desvío estándar"
                source={data?.fuente}
                lastUpdated={data?.ultima_actualizacion}
                filtersApplied={macroFilters}
                detailRows={inflationAnomalies}
                detailColumns={anomalyColumns}
                exportFilename="macro-anomalias"
              >
                <BarChart
                  height={280}
                  showLegend={false}
                  data={[
                    {
                      x: inflationAnomalies.map((item) => item.label),
                      y: inflationAnomalies.map((item) => item.value),
                      name: 'Inflación',
                      color: '#cf6e63',
                    },
                  ]}
                  yAxisTitle="%"
                />
              </ChartWithDrillDown>
            </ControlPanel>

            <ControlPanel
              title="Sensibilidad del capital"
              description="Impacto del costo financiero si la tasa se mueve sobre el escenario base."
            >
              <ChartWithDrillDown<{ label: string; value: number }>
                title="Sensibilidad de tasa"
                description="Shock simple sobre el costo financiero a 90 días."
                formula="Shock simple sobre costo 90d base"
                source={data?.fuente}
                lastUpdated={data?.ultima_actualizacion}
                filtersApplied={macroFilters}
                detailRows={financingSensitivity}
                detailColumns={sensitivityColumns}
                exportFilename="macro-sensibilidad"
              >
                <BarChart
                  height={280}
                  showLegend={false}
                  data={[
                    {
                      x: financingSensitivity.map((item) => item.label),
                      y: financingSensitivity.map((item) => item.value),
                      name: 'Costo 90d',
                      color: '#2f8a57',
                    },
                  ]}
                  yAxisTitle="ARS"
                />
              </ChartWithDrillDown>
            </ControlPanel>
          </ControlBottomGrid>
        </div>
      </AnalysisSection>
    </div>
  )
}
