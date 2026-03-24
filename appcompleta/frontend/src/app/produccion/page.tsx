'use client'

import { Suspense, useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { Trees } from 'lucide-react'
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
import { usePageFilters } from '@/hooks/usePageFilters'
import { useProduccionCampo } from '@/hooks/useProduccionCampo'
import { buildAppliedFilters } from '@/lib/drilldown'
import { formatDate, formatNumber } from '@/lib/formatters'
import { formatPercentValue } from '@/lib/lemon-ui'
import { takeLastItems } from '@/lib/operational-dashboard'
import type { ProduccionLoteRow, ProduccionSerieRow, ProduccionVariedadEstRow } from '@/types/lemon-produccion'

type ProductionDailyDetailRow = ProduccionSerieRow & { estado: string }
type ProductionLotDetailRow = ProduccionLoteRow & { estado: string }
type ProductionEstablishmentRow = {
  establecimiento: string
  kg_cosechados_tn: number
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

function lotState(desvioPct: number) {
  if (desvioPct <= -15) return 'Critico'
  if (desvioPct < 0) return 'Atencion'
  return 'Bien'
}

function ProduccionPageContent() {
  const filters = usePageFilters(['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'])
  const { data, error, isLoading } = useProduccionCampo(filters)
  const executiveScope = useExecutiveScope(filters)
  const appliedFilters = useMemo(() => buildAppliedFilters(filters), [filters])

  const harvestRows = useMemo(() => takeLastItems(data?.series.cosecha_diaria || [], 14), [data?.series.cosecha_diaria])
  const latestHarvest = harvestRows[harvestRows.length - 1]
  const averageHarvest = useMemo(() => {
    if (!harvestRows.length) return 0
    return harvestRows.reduce((acc, row) => acc + row.kg_cosechados, 0) / harvestRows.length
  }, [harvestRows])

  const dailyDetailRows = useMemo<ProductionDailyDetailRow[]>(
    () =>
      harvestRows.map((row) => ({
        ...row,
        estado: row.kg_cosechados < averageHarvest * 0.8 ? 'Atencion' : 'Bien',
      })),
    [averageHarvest, harvestRows]
  )

  const yieldRows = useMemo<ProductionLotDetailRow[]>(
    () =>
      [...(data?.breakdown.rendimiento_lotes || [])]
        .sort((a, b) => b.kg_ha_proyectado - a.kg_ha_proyectado)
        .map((row) => ({
          ...row,
          estado: lotState(row.desvio_pct),
        })),
    [data?.breakdown.rendimiento_lotes]
  )

  const worstLots = useMemo<ProductionLotDetailRow[]>(
    () =>
      [...(data?.breakdown.ranking_bajo_rendimiento || [])]
        .sort((a, b) => a.desvio_pct - b.desvio_pct)
        .slice(0, 8)
        .map((row) => ({
          ...row,
          estado: lotState(row.desvio_pct),
        })),
    [data?.breakdown.ranking_bajo_rendimiento]
  )

  const productionByEstablishment = useMemo<ProductionEstablishmentRow[]>(() => {
    const grouped = new Map<string, number>()
    for (const row of data?.breakdown.produccion_variedad_establecimiento || []) {
      grouped.set(row.establecimiento, (grouped.get(row.establecimiento) || 0) + row.kg_cosechados_tn)
    }
    const rows = Array.from(grouped.entries()).map(([establecimiento, kg_cosechados_tn]) => ({
      establecimiento,
      kg_cosechados_tn,
      estado: 'Bien',
    }))
    const average = rows.length ? rows.reduce((acc, row) => acc + row.kg_cosechados_tn, 0) / rows.length : 0
    return rows
      .map((row) => ({
        ...row,
        estado: row.kg_cosechados_tn < average * 0.85 ? 'Atencion' : 'Bien',
      }))
      .sort((a, b) => b.kg_cosechados_tn - a.kg_cosechados_tn)
  }, [data?.breakdown.produccion_variedad_establecimiento])

  const focusTone = useMemo<'success' | 'warning' | 'danger'>(() => {
    if ((worstLots[0]?.desvio_pct || 0) <= -15 || (data?.summary.lotes_atrasados || 0) >= 3) return 'danger'
    if ((worstLots[0]?.desvio_pct || 0) < 0 || (data?.summary.lotes_atrasados || 0) > 0) return 'warning'
    return 'success'
  }, [data?.summary.lotes_atrasados, worstLots])

  const focusBullets = useMemo(() => {
    const worst = worstLots[0]
    const weakestEstablishment = productionByEstablishment[productionByEstablishment.length - 1]
    return [
      worst
        ? `${worst.codigo_lote || worst.lote} es hoy el lote mas comprometido, con ${formatNumber(worst.kg_ha_proyectado, 0)} kg/ha y ${formatNumber(worst.desvio_pct, 1)}% vs objetivo.`
        : '',
      weakestEstablishment
        ? `${weakestEstablishment.establecimiento} es el establecimiento con menor volumen del periodo reciente.`
        : '',
      (data?.summary.lotes_atrasados || 0) > 0
        ? `${formatNumber(data?.summary.lotes_atrasados || 0, 0)} lotes siguen atrasados y conviene priorizarlos antes de que el desvio se consolide.`
        : 'El avance de cosecha no muestra atrasos materiales en el scope actual.',
    ]
  }, [data?.summary.lotes_atrasados, productionByEstablishment, worstLots])

  const dailyColumns = useMemo<ColDef<ProductionDailyDetailRow>[]>(
    () => [
      { field: 'fecha', headerName: 'Fecha', valueFormatter: ({ value }) => formatDate(String(value || '')) },
      { field: 'kg_cosechados', headerName: 'Kg dia', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'kg_acumulados', headerName: 'Kg acumulados', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'desvio_acumulado_kg', headerName: 'Desvio', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const lotColumns = useMemo<ColDef<ProductionLotDetailRow>[]>(
    () => [
      { field: 'lote', headerName: 'Lote' },
      { field: 'establecimiento', headerName: 'Establecimiento' },
      { field: 'kg_ha_proyectado', headerName: 'Kg/ha', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'objetivo_kg_ha', headerName: 'Objetivo', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'desvio_pct', headerName: 'Desvio %', valueFormatter: ({ value }) => `${formatNumber(Number(value || 0), 1)}%` },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const establishmentColumns = useMemo<ColDef<ProductionEstablishmentRow>[]>(
    () => [
      { field: 'establecimiento', headerName: 'Establecimiento' },
      { field: 'kg_cosechados_tn', headerName: 'Tn', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 1) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  if (error && !data) {
    return (
      <Alert variant="danger" title="No se pudo cargar Produccion de Campo">
        Revisa el backend limonero o los hechos de cosecha y rendimiento.
      </Alert>
    )
  }

  if (isLoading || !data) return <PageSkeleton />

  return (
    <div className="space-y-6">
      <DashboardLead
        title="Produccion de Campo"
        description="Control diario de cosecha para ver ritmo, rinde y lotes atrasados."
        icon={Trees}
        label="Panel operativo diario"
        scopeLabel={executiveScope.label}
        scopeBadges={executiveScope.badges}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SimpleKpiCard
          label="Cosecha hoy"
          value={`${formatNumber(latestHarvest?.kg_cosechados || 0, 0)} kg`}
          delta={latestHarvest?.fecha ? formatDate(latestHarvest.fecha) : 'Ultimo dia'}
          detail="Volumen levantado en la ultima fecha operativa."
          tone={(latestHarvest?.kg_cosechados || 0) >= averageHarvest ? 'positive' : 'warning'}
        />
        <SimpleKpiCard
          label="kg por cosechero"
          value={`${formatNumber(data.summary.kg_jornalero, 0)} kg`}
          delta={data.summary.kg_jornalero_delta_pct !== 0 ? `${data.summary.kg_jornalero_delta_pct > 0 ? '+' : ''}${formatNumber(data.summary.kg_jornalero_delta_pct, 1)}%` : undefined}
          detail={data.summary.kg_jornalero_detail}
          tone={data.summary.kg_jornalero >= 2000 ? 'positive' : data.summary.kg_jornalero >= 1500 ? 'warning' : 'danger'}
        />
        <SimpleKpiCard
          label="Avance de cosecha"
          value={formatPercentValue(data.summary.avance_cosecha_pct)}
          delta={`${data.summary.avance_cosecha_delta_pct > 0 ? '+' : ''}${formatNumber(data.summary.avance_cosecha_delta_pct, 1)} pts`}
          detail="Permite ver si el operativo esta entrando en atraso."
          tone={data.summary.avance_cosecha_pct >= 85 ? 'positive' : data.summary.avance_cosecha_pct >= 70 ? 'warning' : 'danger'}
        />
        <SimpleKpiCard
          label="Rinde proyectado"
          value={`${formatNumber(data.summary.rendimiento_proyectado_kg_ha, 0)} kg/ha`}
          delta={data.summary.rendimiento_proyectado_delta_pct !== 0 ? `${data.summary.rendimiento_proyectado_delta_pct > 0 ? '+' : ''}${formatNumber(data.summary.rendimiento_proyectado_delta_pct, 1)}%` : undefined}
          detail={data.summary.rendimiento_proyectado_detail}
          tone={data.summary.rendimiento_proyectado_kg_ha >= 30000 ? 'positive' : data.summary.rendimiento_proyectado_kg_ha >= 22000 ? 'warning' : 'danger'}
        />
      </div>

      {/* KPI con torta — avance, lotes, establecimientos, variedades */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniPieKpiCard
          label="Avance de cosecha"
          centerValue={formatPercentValue(data.summary.avance_cosecha_pct)}
          centerSub="Cosechado"
          slices={[
            { label: 'Cosechado', value: Math.round(data.summary.avance_cosecha_pct), color: '#30945a' },
            { label: 'Pendiente', value: Math.round(Math.max(0, 100 - data.summary.avance_cosecha_pct)), color: '#d8cbbb' },
          ]}
          tone={data.summary.avance_cosecha_pct >= 85 ? 'positive' : data.summary.avance_cosecha_pct >= 70 ? 'warning' : 'danger'}
        />
        <MiniPieKpiCard
          label="Estado de lotes"
          centerValue={`${yieldRows.filter((r) => r.desvio_pct >= 0).length}`}
          centerSub="En objetivo"
          slices={[
            { label: 'En objetivo', value: yieldRows.filter((r) => r.desvio_pct >= 0).length, color: '#30945a' },
            { label: 'Atrasado', value: yieldRows.filter((r) => r.desvio_pct < 0 && r.desvio_pct > -15).length, color: '#d69f2f' },
            { label: 'Critico', value: yieldRows.filter((r) => r.desvio_pct <= -15).length, color: '#cf6e63' },
          ]}
          tone={yieldRows.filter((r) => r.desvio_pct <= -15).length > 0 ? 'danger' : yieldRows.filter((r) => r.desvio_pct < 0).length > 0 ? 'warning' : 'positive'}
        />
        <MiniPieKpiCard
          label="Volumen por establecimiento"
          centerValue={`${formatNumber(productionByEstablishment[0]?.kg_cosechados_tn || 0, 0)} tn`}
          centerSub={productionByEstablishment[0]?.establecimiento || ''}
          slices={(() => {
            if (!productionByEstablishment.length) return [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]
            const total = productionByEstablishment.reduce((s, r) => s + r.kg_cosechados_tn, 0)
            return productionByEstablishment.slice(0, 4).map((r) => ({
              label: r.establecimiento,
              value: total > 0 ? Math.round((r.kg_cosechados_tn / total) * 100) : 0,
            }))
          })()}
          tone="neutral"
        />
        <MiniPieKpiCard
          label="Lotes atrasados"
          centerValue={`${formatNumber(data.summary.lotes_atrasados, 0)}`}
          centerSub="Con atraso"
          slices={[
            { label: 'En plan', value: Math.max(0, yieldRows.length - data.summary.lotes_atrasados), color: '#30945a' },
            { label: 'Atrasados', value: data.summary.lotes_atrasados, color: '#cf6e63' },
          ]}
          tone={data.summary.lotes_atrasados >= 3 ? 'danger' : data.summary.lotes_atrasados > 0 ? 'warning' : 'positive'}
        />
      </div>

      <OperationalFocusAlert title="Foco operativo del dia" tone={focusTone} bullets={focusBullets} />

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartWithDrillDown<ProductionDailyDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Cosecha diaria"
          description="Detalle diario de cosecha y desvio acumulado."
          summaryItems={[
            { label: 'Total 14 dias', value: `${formatNumber(harvestRows.reduce((acc, row) => acc + row.kg_cosechados, 0), 0)} kg` },
            { label: 'Promedio diario', value: `${formatNumber(averageHarvest, 0)} kg` },
            { label: 'Ultimo dia', value: `${formatNumber(latestHarvest?.kg_cosechados || 0, 0)} kg` },
            { label: 'Ultimo desvio', value: `${formatNumber(harvestRows[harvestRows.length - 1]?.desvio_acumulado_kg || 0, 0)} kg` },
          ]}
          contextText="Sirve para ver si el ritmo reciente sostiene el plan o si la cosecha ya se esta atrasando."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={dailyDetailRows}
          detailColumns={dailyColumns}
          exportFilename="produccion-tiempo"
          detailLabel="Cosecha diaria del ERP."
        >
          <SimpleChartCard
            title="Cosecha diaria"
            description="Serie corta para ver si la cosecha acelera o pierde ritmo."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <LineChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: harvestRows.map((row) => row.fecha),
                  y: harvestRows.map((row) => row.kg_cosechados),
                  name: 'Kg',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>%{y:,.0f} kg<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<ProductionLotDetailRow>
          title="Informe ERP · Rinde por lote"
          description="Comparacion simple del rendimiento proyectado por lote."
          summaryItems={[
            { label: 'Lotes', value: formatNumber(yieldRows.length, 0) },
            { label: 'Mejor rinde', value: `${formatNumber(yieldRows[0]?.kg_ha_proyectado || 0, 0)} kg/ha` },
            { label: 'Peor rinde', value: `${formatNumber(yieldRows[yieldRows.length - 1]?.kg_ha_proyectado || 0, 0)} kg/ha` },
            { label: 'Bajo objetivo', value: formatNumber(yieldRows.filter((row) => row.desvio_pct < 0).length, 0) },
          ]}
          contextText="Permite ver rapido que lotes sostienen el volumen y cuales quedan cortos."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={yieldRows}
          detailColumns={lotColumns}
          exportFilename="produccion-rendimiento-lote"
          detailLabel="Rendimiento proyectado por lote."
        >
          <SimpleChartCard
            title="Rinde por lote"
            description="Comparacion simple para ver donde el rinde esta fuerte y donde no."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              showLegend={false}
              data={[
                {
                  x: yieldRows.slice(0, 10).map((row) => row.lote),
                  y: yieldRows.slice(0, 10).map((row) => row.kg_ha_proyectado),
                  name: 'Kg/ha',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>%{y:,.0f} kg/ha<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<ProductionEstablishmentRow>
          title="Informe ERP · Volumen por establecimiento"
          description="Volumen simple para ver que establecimiento esta empujando la campana."
          summaryItems={[
            { label: 'Establecimientos', value: formatNumber(productionByEstablishment.length, 0) },
            { label: 'Mayor volumen', value: `${formatNumber(productionByEstablishment[0]?.kg_cosechados_tn || 0, 1)} tn` },
            { label: 'Menor volumen', value: `${formatNumber(productionByEstablishment[productionByEstablishment.length - 1]?.kg_cosechados_tn || 0, 1)} tn` },
            { label: 'Total', value: `${formatNumber(productionByEstablishment.reduce((acc, row) => acc + row.kg_cosechados_tn, 0), 1)} tn` },
          ]}
          contextText="Ayuda a ver rapido que zona esta empujando volumen y cual viene retrasada."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={productionByEstablishment}
          detailColumns={establishmentColumns}
          exportFilename="produccion-establecimiento"
          detailLabel="Volumen agregado por establecimiento."
        >
          <SimpleChartCard
            title="Volumen por establecimiento"
            description="Comparacion clara entre zonas para ubicar rapido el foco."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              showLegend={false}
              data={[
                {
                  x: productionByEstablishment.map((row) => row.establecimiento),
                  y: productionByEstablishment.map((row) => row.kg_cosechados_tn),
                  name: 'Toneladas',
                  color: '#7d8f76',
                  hovertemplate: '%{x}<br>%{y:,.1f} tn<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<ProductionLotDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Lotes bajo objetivo"
          description="Ranking simple de lotes que hoy quedan mas abajo del objetivo."
          summaryItems={[
            { label: 'Lotes criticos', value: formatNumber(worstLots.length, 0) },
            { label: 'Peor desvio', value: `${formatNumber(worstLots[0]?.desvio_pct || 0, 1)}%` },
            { label: 'Peor rinde', value: `${formatNumber(worstLots[0]?.kg_ha_proyectado || 0, 0)} kg/ha` },
            { label: 'Objetivo', value: `${formatNumber(worstLots[0]?.objetivo_kg_ha || 0, 0)} kg/ha` },
          ]}
          contextText="Sirve para ver donde actuar primero cuando el rendimiento ya se esta desviando."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={worstLots}
          detailColumns={lotColumns}
          exportFilename="produccion-peores-lotes"
          detailLabel="Ranking de lotes bajo objetivo."
        >
          <SimpleChartCard
            title="Lotes bajo objetivo"
            description="Ranking directo para ver donde el operativo necesita intervencion primero."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={300}
              horizontal
              showLegend={false}
              data={[
                {
                  x: worstLots.map((row) => row.lote),
                  y: worstLots.map((row) => row.desvio_pct),
                  name: 'Desvio %',
                  color: '#cf6e63',
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

export default function ProduccionPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ProduccionPageContent />
    </Suspense>
  )
}
