'use client'

import type { ColDef } from 'ag-grid-community'
import { useEffect, useMemo, useState } from 'react'
import { Coins } from 'lucide-react'
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
import { CHART_COLORS } from '@/lib/constants'
import {
  computeDeviation,
  detectAnomalies,
  movingAverageProjection,
  type NumericPoint,
  type ProjectionPoint,
} from '@/lib/analysis'
import {
  formatCurrency,
  formatNumber,
  formatPercent,
  formatToneladas,
} from '@/lib/formatters'
import { filterSeriesByRange } from '@/lib/time-series'
import type {
  CommoditiesData,
  CommodityComparisonRow,
  CommodityExposureRow,
  CommodityPrice,
  CommoditySeriesPoint,
} from '@/types/macro'

interface CommoditiesPanelProps {
  data?: CommoditiesData
  loading?: boolean
}

const cultivoColors: Record<string, string> = {
  soja: CHART_COLORS.soja,
  maiz: CHART_COLORS.maiz,
  trigo: CHART_COLORS.trigo,
  girasol: CHART_COLORS.girasol,
}

export function CommoditiesPanel({ data, loading }: CommoditiesPanelProps) {
  const { range, setRange } = useTimeRangeQuery('30D')
  const [selectedCrop, setSelectedCrop] = useState<string>('soja')

  useEffect(() => {
    if (!data?.precios?.length) return
    const nextCrop =
      data.precios.find((item) => item.nombre === data.summary.mejor_margen_cultivo)?.simbolo ||
      data.precios[0]?.simbolo ||
      'soja'
    setSelectedCrop((current) =>
      data.precios.some((item) => item.simbolo === current) ? current : nextCrop
    )
  }, [data])

  const selectedPrice = data?.precios.find((item) => item.simbolo === selectedCrop) || data?.precios?.[0]
  const selectedSeries = useMemo(
    () => filterSeriesByRange(data?.series_by_crop?.[selectedCrop] || [], range, (item) => item.fecha),
    [data?.series_by_crop, range, selectedCrop]
  )
  const analysisFilters = useMemo(
    () => [
      { label: 'Periodo', value: range },
      { label: 'Cultivo', value: selectedPrice?.nombre || selectedCrop },
    ],
    [range, selectedCrop, selectedPrice?.nombre]
  )
  const pricePoints = useMemo<NumericPoint[]>(
    () =>
      selectedSeries.map((item) => ({
        label: item.fecha,
        value: item.precio_usd_tn,
      })),
    [selectedSeries]
  )
  const priceProjection = useMemo<ProjectionPoint[]>(
    () => movingAverageProjection(pricePoints, 5, 5),
    [pricePoints]
  )
  const projectionRows = useMemo(
    () =>
      priceProjection.map((item) => ({
        fecha: item.label,
        precio_usd_tn: item.value,
        tipo: item.projected ? 'Proyección' : 'Histórico',
      })),
    [priceProjection]
  )
  const priceDeviation = useMemo(
    () => computeDeviation(selectedPrice?.precio_usd_tn || 0, selectedPrice?.breakeven_usd_tn || 0),
    [selectedPrice?.breakeven_usd_tn, selectedPrice?.precio_usd_tn]
  )
  const marginAnomalies = useMemo(() => {
    const points = (data?.comparador || []).map((item) => ({
      label: item.cultivo,
      value: item.margen_usd_tn,
    }))
    const detected = detectAnomalies(points, 0.8)
    if (detected.length) return detected
    return [...points]
      .sort((a, b) => a.value - b.value)
      .slice(0, Math.min(3, points.length))
      .map((item) => ({ ...item, zScore: 0 }))
  }, [data?.comparador])
  const marginSensitivity = useMemo(
    () =>
      [-0.2, -0.1, 0, 0.1, 0.2].map((shock) => ({
        label: `${shock > 0 ? '+' : ''}${Math.round(shock * 100)}% precio`,
        value: Number((((selectedPrice?.margen_usd_tn || 0) + (selectedPrice?.precio_usd_tn || 0) * shock)).toFixed(2)),
      })),
    [selectedPrice?.margen_usd_tn, selectedPrice?.precio_usd_tn]
  )
  const commodityInsights = useMemo(() => {
    const items: string[] = []
    const nextProjection = priceProjection.find((item) => item.projected)?.value
    if (nextProjection != null) {
      items.push(
        nextProjection > (selectedPrice?.precio_usd_tn || 0)
          ? `${selectedPrice?.nombre || 'El cultivo'} mantiene un sesgo alcista de corto plazo.`
          : `${selectedPrice?.nombre || 'El cultivo'} pierde inercia en la proyección de corto plazo.`
      )
    }
    if (priceDeviation.deltaPct > 0) {
      items.push(`El precio actual está ${formatPercent(priceDeviation.deltaPct)} por encima del break-even.`)
    } else {
      items.push(`El precio actual ya está ${formatPercent(Math.abs(priceDeviation.deltaPct))} por debajo del break-even.`)
    }
    if (marginAnomalies[0]) {
      items.push(`${marginAnomalies[0].label} quedó fuera del rango relativo de márgenes entre cultivos.`)
    }
    if (selectedPrice?.accion_sugerida) {
      items.push(selectedPrice.accion_sugerida)
    }
    return items.slice(0, 4)
  }, [marginAnomalies, priceDeviation.deltaPct, priceProjection, selectedPrice])

  const comparisonColumns = useMemo<ColDef<CommodityComparisonRow>[]>(() => [
    { field: 'ranking', headerName: 'Rank', minWidth: 70, flex: 0.6, type: 'numericColumn' },
    { field: 'cultivo', headerName: 'Cultivo', minWidth: 120, flex: 1 },
    { field: 'precio_usd_tn', headerName: 'Precio', minWidth: 100, flex: 0.8, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value, 'USD') },
    { field: 'costo_estimado_usd_tn', headerName: 'Costo', minWidth: 100, flex: 0.8, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value, 'USD') },
    { field: 'margen_usd_tn', headerName: 'Margen', minWidth: 100, flex: 0.8, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value, 'USD') },
    { field: 'margen_pct', headerName: 'Margen %', minWidth: 100, flex: 0.8, valueFormatter: (params) => formatPercent(params.value) },
    { field: 'recomendacion', headerName: 'Acción', minWidth: 120, flex: 0.9 },
  ], [])

  const seriesColumns = useMemo<ColDef<CommoditySeriesPoint>[]>(() => [
    { field: 'fecha', headerName: 'Fecha', minWidth: 110, flex: 0.9 },
    { field: 'precio_usd_tn', headerName: 'Precio', minWidth: 100, flex: 0.8, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value, 'USD') },
    { field: 'break_even_usd_tn', headerName: 'Break-even', minWidth: 110, flex: 0.9, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value, 'USD') },
    { field: 'margen_usd_tn', headerName: 'Margen', minWidth: 100, flex: 0.8, type: 'numericColumn', valueFormatter: (params) => formatCurrency(params.value, 'USD') },
    { field: 'source', headerName: 'Fuente', minWidth: 90, flex: 0.7 },
  ], [])

  const exposureColumns = useMemo<ColDef<CommodityExposureRow>[]>(() => [
    { field: 'cultivo', headerName: 'Cultivo', minWidth: 120, flex: 1 },
    { field: 'toneladas_producidas', headerName: 'Producidas', minWidth: 120, flex: 0.9, type: 'numericColumn', valueFormatter: (params) => formatToneladas(params.value, 0) },
    { field: 'toneladas_vendidas', headerName: 'Vendidas', minWidth: 110, flex: 0.9, type: 'numericColumn', valueFormatter: (params) => formatToneladas(params.value, 0) },
    { field: 'toneladas_sin_precio', headerName: 'Sin precio', minWidth: 120, flex: 0.9, type: 'numericColumn', valueFormatter: (params) => formatToneladas(params.value, 0) },
    { field: 'sin_cobertura_pct', headerName: 'Sin cobertura', minWidth: 120, flex: 0.9, valueFormatter: (params) => formatPercent(params.value) },
    { field: 'recomendacion', headerName: 'Acción', minWidth: 110, flex: 0.8 },
  ], [])
  const projectionColumns = useMemo<ColDef<{ fecha: string; precio_usd_tn: number; tipo: string }>[]>(() => [
    { field: 'fecha', headerName: 'Fecha', minWidth: 110, flex: 0.9 },
    {
      field: 'precio_usd_tn',
      headerName: 'Precio',
      minWidth: 110,
      flex: 0.9,
      type: 'numericColumn',
      valueFormatter: (params) => formatCurrency(params.value, 'USD'),
    },
    { field: 'tipo', headerName: 'Serie', minWidth: 110, flex: 0.8 },
  ], [])
  const anomalyColumns = useMemo<ColDef<{ label: string; value: number; zScore: number }>[]>(() => [
    { field: 'label', headerName: 'Cultivo', minWidth: 120, flex: 0.9 },
    {
      field: 'value',
      headerName: 'Margen',
      minWidth: 110,
      flex: 0.9,
      type: 'numericColumn',
      valueFormatter: (params) => formatCurrency(params.value, 'USD'),
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
      headerName: 'Margen',
      minWidth: 110,
      flex: 0.9,
      type: 'numericColumn',
      valueFormatter: (params) => formatCurrency(params.value, 'USD'),
    },
  ], [])

  if (loading && !data) {
    return <SkeletonBlock className="h-[62rem] w-full rounded-[2rem]" />
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
        <div className="flex h-8 w-8 items-center justify-center rounded-2xl border border-border/70 bg-[#f7f3ea] text-primary-700">
          <Coins className="h-4 w-4" />
        </div>
        Commodity decision board
      </div>

      <ExecutiveSummarySection description="Resumen ejecutivo de precios, márgenes y exposición comercial para decidir rápido si vender, esperar o cubrir.">
        <ControlKpiStrip className="border-0 bg-transparent px-0 py-0">
        <ControlKpi label="Mejor margen" value={data?.summary.mejor_margen_cultivo || '—'} subtitle={data ? `${formatCurrency(data.summary.mejor_margen_usd_tn, 'USD')} por tn` : 'Cultivo líder'} tone="positive" />
        <ControlKpi label="Margen líder" value={data ? formatPercent(data.summary.mejor_margen_pct) : '—'} subtitle="Rentabilidad relativa del líder" tone="positive" />
        <ControlKpi label="Sin cobertura" value={data ? formatPercent(data.summary.sin_cobertura_pct_total) : '—'} subtitle={data ? `${formatToneladas(data.summary.toneladas_sin_precio_total, 0)} sin precio` : 'Exposición comercial total'} tone={data && data.summary.sin_cobertura_pct_total > 35 ? 'critical' : 'warning'} />
        <ControlKpi label="Cultivo en riesgo" value={data?.summary.cultivo_mayor_riesgo || '—'} subtitle="Mayor exposición comercial" tone="warning" />
        <ControlKpi label="Precio actual" value={selectedPrice ? formatCurrency(selectedPrice.precio_usd_tn, 'USD') : '—'} subtitle={selectedPrice?.nombre || 'Cultivo seleccionado'} delta={selectedPrice ? formatPercent(selectedPrice.variacion_7d_pct) : undefined} tone={selectedPrice && selectedPrice.variacion_7d_pct < 0 ? 'warning' : 'positive'} />
        <ControlKpi label="Break-even" value={selectedPrice ? formatCurrency(selectedPrice.breakeven_usd_tn, 'USD') : '—'} subtitle={selectedPrice ? `${formatCurrency(selectedPrice.margen_usd_tn, 'USD')} de margen` : 'Piso económico'} tone={selectedPrice && selectedPrice.margen_usd_tn < 0 ? 'critical' : 'positive'} />
        </ControlKpiStrip>
      </ExecutiveSummarySection>

      <TimeSeriesSection
        description="Serie temporal del cultivo seleccionado para leer tendencia de precio contra break-even y definir la acción comercial."
        actions={<TimeRangeSelector value={range} onChange={setRange} />}
      >
      <ControlMainGrid
        main={
          <ControlPanel
            title="Precio vs break-even"
            description="Serie del cultivo seleccionado para decidir venta, espera o cobertura."
            meta={<DataSourceTag fuente={data?.fuente || 'Mercado'} ultimaActualizacion={data?.ultima_actualizacion} />}
          >
            <div className="mb-4 flex flex-wrap gap-2">
              {(data?.precios || []).map((item) => (
                <button
                  key={item.simbolo}
                  type="button"
                  onClick={() => setSelectedCrop(item.simbolo)}
                  className={`rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                    item.simbolo === selectedCrop
                      ? 'border-primary-300 bg-primary-50 text-primary-800'
                      : 'border-border bg-white text-text-muted hover:text-text'
                  }`}
                >
                  {item.nombre}
                </button>
              ))}
            </div>

            <ChartWithDrillDown<CommoditySeriesPoint>
              title={`Serie ${selectedPrice?.nombre || selectedCrop}`}
              description="Precio, break-even y margen histórico del cultivo seleccionado."
              formula="margen = precio - break_even"
              source={data?.fuente}
              lastUpdated={data?.ultima_actualizacion}
              filtersApplied={[{ label: 'Periodo', value: range }]}
              detailRows={selectedSeries}
              detailColumns={seriesColumns}
              exportFilename={`commodities-serie-${selectedCrop}`}
              footerNote={data?.historico_nota || undefined}
            >
              <LineChart
                height={340}
                data={[
                  {
                    x: selectedSeries.map((item) => item.fecha),
                    y: selectedSeries.map((item) => item.precio_usd_tn),
                    name: 'Precio',
                    color: cultivoColors[selectedCrop] || '#1f6b42',
                  },
                  {
                    x: selectedSeries.map((item) => item.fecha),
                    y: selectedSeries.map((item) => item.break_even_usd_tn),
                    name: 'Break-even',
                    color: '#b6aa97',
                    dashed: true,
                  },
                ]}
                yAxisTitle="USD/tn"
              />
            </ChartWithDrillDown>
          </ControlPanel>
        }
        rail={
          <ControlRail>
            <ControlRailMetric
              label="Margen actual"
              value={selectedPrice ? formatCurrency(selectedPrice.margen_usd_tn, 'USD') : '—'}
              detail={selectedPrice ? formatPercent(selectedPrice.margen_pct) : 'Sin lectura'}
              tone={selectedPrice && selectedPrice.margen_usd_tn < 0 ? 'critical' : 'positive'}
              visual={<BulletChart value={Math.max(selectedPrice?.precio_usd_tn || 0, 0)} target={selectedPrice?.breakeven_usd_tn || 0} max={(selectedPrice?.precio_max_reciente_usd_tn || 0) + 40} label="precio vs break-even" />}
            />
            <ControlRailMetric
              label="7 días"
              value={selectedPrice ? formatPercent(selectedPrice.variacion_7d_pct) : '—'}
              detail={selectedPrice ? `30 días ${formatPercent(selectedPrice.variacion_30d_pct)}` : 'Sin variación'}
              tone={selectedPrice && selectedPrice.variacion_7d_pct < 0 ? 'warning' : 'positive'}
            />
            <ControlRailMetric
              label="Sin precio"
              value={selectedPrice ? formatToneladas(selectedPrice.toneladas_sin_precio, 0) : '—'}
              detail={selectedPrice ? `${formatPercent(selectedPrice.sin_cobertura_pct)} sin cobertura` : 'Sin exposición'}
              tone={selectedPrice && selectedPrice.sin_cobertura_pct > 35 ? 'critical' : 'warning'}
            />
            <ControlRailMetric
              label="Qué hago"
              value={selectedPrice?.recomendacion || 'sin lectura'}
              detail={selectedPrice?.accion_sugerida || 'Sin recomendación operacional'}
              tone={selectedPrice?.severidad === 'critical' ? 'critical' : selectedPrice?.severidad === 'warning' ? 'warning' : 'positive'}
            />
          </ControlRail>
        }
      />
      </TimeSeriesSection>

      <BreakdownSection description="Apertura del contexto de commodities en comparador de cultivos, exposición comercial y ranking de márgenes.">
        <div className="space-y-5">
      <ControlBottomGrid>
        <ControlPanel
          title="Comparador de cultivos"
          description="Margen por tonelada para decidir qué cultivo priorizar en fijación o cobertura."
        >
          <ChartWithDrillDown<CommodityComparisonRow>
            title="Comparador de cultivos"
            description="Precio, costo y margen por cultivo."
            formula="margen_usd_tn = precio - costo_estimado"
            source={data?.fuente}
            lastUpdated={data?.ultima_actualizacion}
            detailRows={data?.comparador || []}
            detailColumns={comparisonColumns}
            exportFilename="commodities-comparador"
          >
            <BarChart
              height={300}
              showLegend={false}
              data={[
                {
                  x: (data?.comparador || []).map((item) => item.cultivo),
                  y: (data?.comparador || []).map((item) => item.margen_usd_tn),
                  name: 'Margen',
                  color: '#2f8a57',
                },
              ]}
              yAxisTitle="USD/tn"
            />
          </ChartWithDrillDown>
        </ControlPanel>

        <ControlPanel
          title="Exposición sin precio"
          description="Participación del volumen todavía abierto para ver dónde está el riesgo comercial."
        >
          <ChartWithDrillDown<CommodityExposureRow>
            title="Exposición sin precio"
            description="Participación de las toneladas sin precio por cultivo."
            formula="Participación relativa sobre toneladas sin precio"
            source={data?.fuente}
            lastUpdated={data?.ultima_actualizacion}
            detailRows={data?.exposicion_comercial || []}
            detailColumns={exposureColumns}
            exportFilename="commodities-exposicion"
          >
            <PieChart
              height={300}
              labels={(data?.exposicion_comercial || []).map((item) => item.cultivo)}
              values={(data?.exposicion_comercial || []).map((item) => item.toneladas_sin_precio)}
              colors={['#2f8a57', '#809176', '#b9ac97', '#d5c6b2']}
            />
          </ChartWithDrillDown>
        </ControlPanel>
      </ControlBottomGrid>

      <ControlPanel
        title="Ranking de margen por cultivo"
        description="Ordena los cultivos según margen por tonelada para priorizar venta o retención."
        meta={<DataSourceTag fuente={data?.fuente || 'Mercado'} ultimaActualizacion={data?.ultima_actualizacion} />}
      >
        <ChartWithDrillDown<CommodityComparisonRow>
          title="Ranking de margen"
          description="Comparador completo detrás del ranking."
          formula="Orden descendente por margen_usd_tn"
          source={data?.fuente}
          lastUpdated={data?.ultima_actualizacion}
          detailRows={data?.comparador || []}
          detailColumns={comparisonColumns}
          exportFilename="commodities-ranking"
        >
          <BarChart
            height={320}
            horizontal
            showLegend={false}
            data={[
              {
                x: (data?.comparador || []).map((item) => item.cultivo),
                y: (data?.comparador || []).map((item) => item.margen_usd_tn),
                name: 'Margen',
                color: '#2f8a57',
              },
            ]}
            xAxisTitle="USD/tn"
          />
        </ChartWithDrillDown>
      </ControlPanel>
        </div>
      </BreakdownSection>

      <AnalysisSection description="Proyección simple de precio, desvío contra break-even, cultivos fuera de rango y sensibilidad del margen a cambios de mercado.">
        <div className="space-y-5">
          <ControlMainGrid
            main={
              <ControlPanel
                title={`Proyección de ${selectedPrice?.nombre || selectedCrop}`}
                description="Extiende la serie reciente para anticipar el próximo movimiento del precio frente al break-even."
                meta={<DataSourceTag fuente={data?.fuente || 'Mercado'} ultimaActualizacion={data?.ultima_actualizacion} />}
              >
                <ChartWithDrillDown<{ fecha: string; precio_usd_tn: number; tipo: string }>
                  title={`Proyección ${selectedPrice?.nombre || selectedCrop}`}
                  description="Histórico y proyección simple del precio del cultivo seleccionado."
                  formula="Media móvil simple sobre precio diario"
                  source={data?.fuente}
                  lastUpdated={data?.ultima_actualizacion}
                  filtersApplied={analysisFilters}
                  detailRows={projectionRows}
                  detailColumns={projectionColumns}
                  exportFilename={`commodities-analisis-${selectedCrop}`}
                >
                  <LineChart
                    height={340}
                    data={[
                      {
                        x: priceProjection.filter((item) => !item.projected).map((item) => item.label),
                        y: priceProjection.filter((item) => !item.projected).map((item) => item.value),
                        name: 'Histórico',
                        color: cultivoColors[selectedCrop] || '#1f6b42',
                      },
                      {
                        x: priceProjection.filter((item) => item.projected).map((item) => item.label),
                        y: priceProjection.filter((item) => item.projected).map((item) => item.value),
                        name: 'Proyección',
                        color: '#b6aa97',
                        dashed: true,
                      },
                      {
                        x: projectionRows.map((item) => item.fecha),
                        y: projectionRows.map(() => selectedPrice?.breakeven_usd_tn || 0),
                        name: 'Break-even',
                        color: '#809176',
                        dashed: true,
                      },
                    ]}
                    yAxisTitle="USD/tn"
                  />
                </ChartWithDrillDown>
              </ControlPanel>
            }
            rail={
              <ControlRail className="grid-cols-1">
                <DeviationCard
                  label="Precio vs break-even"
                  actualLabel="Precio"
                  expectedLabel="Break-even"
                  actual={formatCurrency(priceDeviation.actual, 'USD')}
                  expected={formatCurrency(priceDeviation.expected, 'USD')}
                  delta={formatCurrency(priceDeviation.delta, 'USD')}
                  deltaPct={priceDeviation.deltaPct}
                />
                <AnalysisInsightsList items={commodityInsights} />
              </ControlRail>
            }
          />

          <ControlBottomGrid>
            <ControlPanel
              title="Cultivos fuera de rango"
              description="Margen relativo por cultivo para detectar oportunidades o riesgos extremos."
            >
              <ChartWithDrillDown<{ label: string; value: number; zScore: number }>
                title="Anomalías de margen"
                description="Cultivos con margen fuera del rango relativo esperado."
                formula="Detección simple por desvío estándar"
                source={data?.fuente}
                lastUpdated={data?.ultima_actualizacion}
                filtersApplied={analysisFilters}
                detailRows={marginAnomalies}
                detailColumns={anomalyColumns}
                exportFilename="commodities-anomalias"
              >
                <BarChart
                  height={280}
                  horizontal
                  showLegend={false}
                  data={[
                    {
                      x: marginAnomalies.map((item) => item.label),
                      y: marginAnomalies.map((item) => item.value),
                      name: 'Margen',
                      color: '#cf6e63',
                    },
                  ]}
                  xAxisTitle="USD/tn"
                />
              </ChartWithDrillDown>
            </ControlPanel>

            <ControlPanel
              title="Sensibilidad del margen"
              description="Impacto directo de un shock de precio sobre el margen por tonelada."
            >
              <ChartWithDrillDown<{ label: string; value: number }>
                title="Sensibilidad al precio"
                description="Escenarios simples de margen frente a cambios del precio actual."
                formula="margen ajustado = margen actual + precio * shock"
                source={data?.fuente}
                lastUpdated={data?.ultima_actualizacion}
                filtersApplied={analysisFilters}
                detailRows={marginSensitivity}
                detailColumns={sensitivityColumns}
                exportFilename={`commodities-sensibilidad-${selectedCrop}`}
              >
                <BarChart
                  height={280}
                  showLegend={false}
                  data={[
                    {
                      x: marginSensitivity.map((item) => item.label),
                      y: marginSensitivity.map((item) => item.value),
                      name: 'Margen',
                      color: '#2f8a57',
                    },
                  ]}
                  yAxisTitle="USD/tn"
                />
              </ChartWithDrillDown>
            </ControlPanel>
          </ControlBottomGrid>
        </div>
      </AnalysisSection>
    </div>
  )
}
