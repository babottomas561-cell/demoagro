'use client'

import { Suspense, useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { LayoutDashboard } from 'lucide-react'
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
import { useGerenciaGeneral } from '@/hooks/useGerenciaGeneral'
import { usePageFilters } from '@/hooks/usePageFilters'
import { buildAppliedFilters } from '@/lib/drilldown'
import { formatCurrency, formatDate, formatNumber } from '@/lib/formatters'
import { takeLastItems } from '@/lib/operational-dashboard'
import type { GerenciaEstablecimientoRow, GerenciaSerieRow } from '@/types/lemon-gerencia'

type MarginDetailRow = GerenciaSerieRow & { estado: string }
type EstablishmentDetailRow = GerenciaEstablecimientoRow & { estado: string }
type CashDetailRow = {
  concepto: string
  monto_ars: number
  referencia: string
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

function buildMarginState(margin: number, average: number) {
  if (margin < 0) return 'Critico'
  if (margin < average * 0.85) return 'Atencion'
  return 'Bien'
}

function buildCashState(cobranzas: number, ventas: number, saldoAbierto: number) {
  if (saldoAbierto > ventas && ventas > 0) return 'Critico'
  if (cobranzas < ventas * 0.75) return 'Atencion'
  return 'Bien'
}

function GerenciaPageContent() {
  const filters = usePageFilters(['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'])
  const { data, error, isLoading } = useGerenciaGeneral(filters)
  const executiveScope = useExecutiveScope(filters)
  const appliedFilters = useMemo(() => buildAppliedFilters(filters), [filters])

  const marginRows = useMemo(() => takeLastItems(data?.series.resultado_diario || [], 30), [data?.series.resultado_diario])
  const latestRow = marginRows[marginRows.length - 1]

  const averageMargin = useMemo(() => {
    if (!marginRows.length) return 0
    return marginRows.reduce((acc, row) => acc + row.margen_ars, 0) / marginRows.length
  }, [marginRows])

  const marginDetailRows = useMemo<MarginDetailRow[]>(
    () =>
      marginRows.map((row) => ({
        ...row,
        estado: buildMarginState(row.margen_ars, averageMargin),
      })),
    [averageMargin, marginRows]
  )

  const establishmentRows = useMemo<EstablishmentDetailRow[]>(() => {
    const rows = [...(data?.breakdown.margen_establecimiento || [])]
    const averageMarginHa = rows.length ? rows.reduce((acc, row) => acc + row.margen_ha_ars, 0) / rows.length : 0
    return rows
      .sort((a, b) => b.margen_ars - a.margen_ars)
      .map((row) => ({
        ...row,
        estado: row.margen_ars < 0 ? 'Critico' : row.margen_ha_ars < averageMarginHa ? 'Atencion' : 'Bien',
      }))
  }, [data?.breakdown.margen_establecimiento])

  const cashRows = useMemo<CashDetailRow[]>(
    () => [
      {
        concepto: 'Ventas del dia',
        monto_ars: data?.summary.ventas_hoy_ars || 0,
        referencia: 'Facturacion operativa del ultimo dia',
        estado: (data?.summary.ventas_hoy_ars || 0) > 0 ? 'Bien' : 'Atencion',
      },
      {
        concepto: 'Cobranzas del dia',
        monto_ars: data?.summary.cobranzas_hoy_ars || 0,
        referencia: 'Caja ingresada por clientes',
        estado: buildCashState(
          data?.summary.cobranzas_hoy_ars || 0,
          data?.summary.ventas_hoy_ars || 0,
          data?.summary.cobranza_abierta_ars || 0
        ),
      },
      {
        concepto: 'Saldo abierto',
        monto_ars: data?.summary.cobranza_abierta_ars || 0,
        referencia: 'Pendiente de cobro acumulado',
        estado: (data?.summary.cobranza_abierta_ars || 0) > (data?.summary.ingresos_acumulados_ars || 0) * 0.35 ? 'Critico' : 'Atencion',
      },
    ],
    [data?.summary.cobranza_abierta_ars, data?.summary.cobranzas_hoy_ars, data?.summary.ingresos_acumulados_ars, data?.summary.ventas_hoy_ars]
  )

  const marginColumns = useMemo<ColDef<MarginDetailRow>[]>(
    () => [
      { field: 'fecha', headerName: 'Fecha', valueFormatter: ({ value }) => formatDate(String(value || '')) },
      { field: 'ingresos_ars', headerName: 'Ingresos', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'costos_ars', headerName: 'Costos', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'margen_ars', headerName: 'Margen', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const establishmentColumns = useMemo<ColDef<EstablishmentDetailRow>[]>(
    () => [
      { field: 'establecimiento', headerName: 'Establecimiento' },
      { field: 'superficie_ha', headerName: 'Ha', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'ingresos_ars', headerName: 'Ingresos', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'costos_ars', headerName: 'Costos', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'margen_ars', headerName: 'Margen', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const cashColumns = useMemo<ColDef<CashDetailRow>[]>(
    () => [
      { field: 'concepto', headerName: 'Concepto' },
      { field: 'monto_ars', headerName: 'Monto', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'referencia', headerName: 'Referencia' },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const dailySummaryItems = useMemo(() => {
    const totalMargin = marginRows.reduce((acc, row) => acc + row.margen_ars, 0)
    const bestDay = marginRows.length ? Math.max(...marginRows.map((row) => row.margen_ars)) : 0
    const worstDay = marginRows.length ? Math.min(...marginRows.map((row) => row.margen_ars)) : 0
    return [
      { label: 'Promedio diario', value: formatCurrency(averageMargin) },
      { label: 'Mejor dia', value: formatCurrency(bestDay) },
      { label: 'Peor dia', value: formatCurrency(worstDay) },
      { label: 'Margen 30 dias', value: formatCurrency(totalMargin) },
    ]
  }, [averageMargin, marginRows])

  const establishmentSummaryItems = useMemo(() => {
    const totalMargin = establishmentRows.reduce((acc, row) => acc + row.margen_ars, 0)
    return [
      { label: 'Establecimientos', value: formatNumber(establishmentRows.length, 0) },
      { label: 'Mejor margen', value: formatCurrency(establishmentRows[0]?.margen_ars || 0) },
      { label: 'Peor margen', value: formatCurrency(establishmentRows[establishmentRows.length - 1]?.margen_ars || 0) },
      { label: 'Margen total', value: formatCurrency(totalMargin) },
    ]
  }, [establishmentRows])

  const focusTone = useMemo<'success' | 'warning' | 'danger'>(() => {
    if ((latestRow?.margen_ars || data?.summary.margen_hoy_ars || 0) < 0 || (data?.summary.cobranza_abierta_ars || 0) > (data?.summary.ingresos_acumulados_ars || 0) * 0.18) {
      return 'danger'
    }
    if ((latestRow?.margen_ars || data?.summary.margen_hoy_ars || 0) < averageMargin) {
      return 'warning'
    }
    return 'success'
  }, [
    averageMargin,
    data?.summary.cobranza_abierta_ars,
    data?.summary.ingresos_acumulados_ars,
    data?.summary.margen_hoy_ars,
    latestRow?.margen_ars,
  ])

  const focusBullets = useMemo(() => {
    const worstEstablishment = establishmentRows[establishmentRows.length - 1]
    const latestMargin = latestRow?.margen_ars || data?.summary.margen_hoy_ars || 0
    const marginGapPct = averageMargin ? (latestMargin - averageMargin) / averageMargin * 100 : 0
    return [
      `El margen del ultimo dia viene ${marginGapPct < 0 ? `${formatNumber(Math.abs(marginGapPct), 1)}% abajo` : `${formatNumber(marginGapPct, 1)}% arriba`} del promedio reciente.`,
      worstEstablishment
        ? `${worstEstablishment.establecimiento} es hoy el establecimiento mas fragil, con ${formatCurrency(worstEstablishment.margen_ars)} de margen.`
        : '',
      (data?.summary.cobranza_abierta_ars || 0) > 0
        ? `La cobranza abierta suma ${formatCurrency(data?.summary.cobranza_abierta_ars || 0)} y ya merece seguimiento comercial.`
        : '',
    ]
  }, [
    averageMargin,
    data?.summary.cobranza_abierta_ars,
    data?.summary.margen_hoy_ars,
    establishmentRows,
    latestRow?.margen_ars,
  ])

  if (error && !data) {
    return (
      <Alert variant="danger" title="No se pudo cargar Gerencia General">
        Revisa el backend limonero o las tablas base del modulo.
      </Alert>
    )
  }

  if (isLoading || !data) return <PageSkeleton />

  return (
    <div className="space-y-6">
      <DashboardLead
        title="Gerencia General"
        description="Control diario del negocio para ver en segundos resultado, caja y establecimientos bajo presion."
        icon={LayoutDashboard}
        label="Panel operativo diario"
        scopeLabel={executiveScope.label}
        scopeBadges={executiveScope.badges}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SimpleKpiCard
          label="Margen hoy"
          value={formatCurrency(latestRow?.margen_ars || data.summary.margen_hoy_ars)}
          delta={latestRow?.fecha ? formatDate(latestRow.fecha) : 'Ultimo dia'}
          detail="Muestra si el negocio cerro bien o mal en la ultima jornada registrada."
          tone={(latestRow?.margen_ars || data.summary.margen_hoy_ars) >= 0 ? 'positive' : 'danger'}
        />
        <SimpleKpiCard
          label="Ventas hoy"
          value={formatCurrency(latestRow?.ingresos_ars || data.summary.ventas_hoy_ars)}
          delta="Ultimo dia operativo"
          detail="Ayuda a ver si la actividad comercial viene sosteniendo ritmo."
          tone={(latestRow?.ingresos_ars || data.summary.ventas_hoy_ars) > 0 ? 'positive' : 'warning'}
        />
        <SimpleKpiCard
          label="Packout fresco"
          value={`${formatNumber(data.summary.packout_comercial_pct, 1)}%`}
          delta={data.summary.packout_comercial_pct >= data.summary.packout_objetivo_pct ? `Obj. ${formatNumber(data.summary.packout_objetivo_pct, 0)}% ✓` : `Obj. ${formatNumber(data.summary.packout_objetivo_pct, 0)}% — bajo`}
          detail="Porcentaje de fruta cosechada que sale como producto fresco exportable. Driver central del margen en USD."
          tone={data.summary.packout_comercial_pct >= data.summary.packout_objetivo_pct ? 'positive' : data.summary.packout_comercial_pct >= data.summary.packout_objetivo_pct * 0.9 ? 'warning' : 'danger'}
        />
        <SimpleKpiCard
          label="Costo / tn USD"
          value={data.summary.costo_tn_usd > 0 ? `USD ${formatNumber(data.summary.costo_tn_usd, 1)}/tn` : 'Sin dato'}
          delta={data.summary.costo_tn_usd_detail || 'Benchmark regional: USD 80-130/tn'}
          detail="Costo total de producción por tonelada convertido a USD. Driver clave de competitividad exportadora frente a Sudáfrica y España."
          tone={data.summary.costo_tn_usd <= 0 ? 'neutral' : data.summary.costo_tn_usd < 90 ? 'positive' : data.summary.costo_tn_usd < 130 ? 'warning' : 'danger'}
        />
      </div>

      {/* KPI con torta — mix de canal y packout */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniPieKpiCard
          label="Mix de canal"
          centerValue={`${formatNumber(data.breakdown.ingresos_costos_canal[0]?.participacion_pct || 0, 0)}%`}
          centerSub={data.breakdown.ingresos_costos_canal[0]?.canal || ''}
          slices={data.breakdown.ingresos_costos_canal.length ? data.breakdown.ingresos_costos_canal.slice(0, 4).map((c) => ({
            label: c.canal,
            value: Math.round(c.participacion_pct),
          })) : [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]}
          tone="neutral"
        />
        <MiniPieKpiCard
          label="Packout vs objetivo"
          centerValue={`${formatNumber(data.summary.packout_comercial_pct, 1)}%`}
          centerSub="Packout"
          slices={[
            { label: 'Packout', value: Math.round(data.summary.packout_comercial_pct), color: '#30945a' },
            { label: 'Objetivo', value: Math.round(Math.max(0, data.summary.packout_objetivo_pct - data.summary.packout_comercial_pct)), color: '#d8cbbb' },
          ]}
          tone={data.summary.packout_comercial_pct >= data.summary.packout_objetivo_pct ? 'positive' : 'warning'}
        />
        <MiniPieKpiCard
          label="Días promedio cobro"
          centerValue={data.summary.dias_promedio_cobro != null ? `${formatNumber(data.summary.dias_promedio_cobro, 0)} días` : 'S/D'}
          centerSub="Cobro"
          slices={(() => {
            const dias = data.summary.dias_promedio_cobro || 0
            const target = 45
            const enRango = dias > 0 ? Math.min(100, Math.round((target / Math.max(dias, 1)) * 100)) : 100
            return [
              { label: '<45 días', value: enRango, color: enRango >= 80 ? '#30945a' : enRango >= 60 ? '#d69f2f' : '#cf6e63' },
              { label: 'Demora', value: Math.max(0, 100 - enRango), color: '#d8cbbb' },
            ]
          })()}
          tone={data.summary.dias_promedio_cobro == null ? 'neutral' : data.summary.dias_promedio_cobro > 75 ? 'danger' : data.summary.dias_promedio_cobro > 45 ? 'warning' : 'positive'}
        />
        <MiniPieKpiCard
          label="Costos por categoria"
          centerValue={(() => {
            const top = data.breakdown.costos_categoria[0]
            const total = data.breakdown.costos_categoria.reduce((s, c) => s + c.monto_ars, 0)
            return top && total > 0 ? `${formatNumber(top.monto_ars / total * 100, 0)}%` : '-'
          })()}
          centerSub={data.breakdown.costos_categoria[0]?.categoria || ''}
          slices={(() => {
            if (!data.breakdown.costos_categoria.length) return [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]
            const total = data.breakdown.costos_categoria.reduce((s, c) => s + c.monto_ars, 0)
            return data.breakdown.costos_categoria.slice(0, 4).map((c) => ({
              label: c.categoria,
              value: total > 0 ? Math.round(c.monto_ars / total * 100) : 0,
            }))
          })()}
          tone="neutral"
        />
      </div>

      <OperationalFocusAlert title="Foco operativo del dia" tone={focusTone} bullets={focusBullets} />

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartWithDrillDown<MarginDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Resultado diario"
          description="Detalle diario de ingresos, costos y margen operativo."
          summaryItems={dailySummaryItems}
          contextText="Sirve para ver si el resultado reciente mejora o se deteriora respecto del promedio del periodo."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={marginDetailRows}
          detailColumns={marginColumns}
          exportFilename="gerencia-margen-tiempo"
          detailLabel="Movimientos diarios consolidados."
        >
          <SimpleChartCard
            title="Margen diario"
            description="Serie corta para ver si el resultado diario mejora o se aprieta."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <LineChart
              height={320}
              showLegend={false}
              data={[
                {
                  x: marginRows.map((row) => row.fecha),
                  y: marginRows.map((row) => row.margen_ars),
                  name: 'Margen',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>Margen %{y:,.0f}<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<EstablishmentDetailRow>
          title="Informe ERP · Resultado por establecimiento"
          description="Comparacion simple del margen por establecimiento."
          summaryItems={establishmentSummaryItems}
          contextText="Permite ver rapido que establecimiento empuja el resultado y cual lo esta frenando."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={establishmentRows}
          detailColumns={establishmentColumns}
          exportFilename="gerencia-margen-establecimiento"
          detailLabel="Resultado resumido por establecimiento."
        >
          <SimpleChartCard
            title="Resultado por establecimiento"
            description="Comparacion directa para detectar rapido donde mirar primero."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              horizontal
              showLegend={false}
              data={[
                {
                  x: establishmentRows.map((row) => row.establecimiento),
                  y: establishmentRows.map((row) => row.margen_ars),
                  name: 'Margen',
                  color: '#30945a',
                  hovertemplate: '%{y}<br>Margen %{x:,.0f}<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<EstablishmentDetailRow>
          title="Informe ERP · Ingreso vs costo"
          description="Apertura simple para entender si el problema esta en ingreso o en costo."
          summaryItems={establishmentSummaryItems}
          contextText="Sirve para ver que establecimientos sostienen ingresos y cuales ya muestran costos pesados."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={establishmentRows}
          detailColumns={establishmentColumns}
          exportFilename="gerencia-ingresos-costos"
          detailLabel="Ingresos y costos por establecimiento."
        >
          <SimpleChartCard
            title="Ingreso vs costo"
            description="Comparacion simple para ver que parte del negocio esta apretando el resultado."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              barmode="group"
              data={[
                {
                  x: establishmentRows.map((row) => row.establecimiento),
                  y: establishmentRows.map((row) => row.ingresos_ars),
                  name: 'Ingresos',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>Ingresos %{y:,.0f}<extra></extra>',
                },
                {
                  x: establishmentRows.map((row) => row.establecimiento),
                  y: establishmentRows.map((row) => row.costos_ars),
                  name: 'Costos',
                  color: '#b2a48f',
                  hovertemplate: '%{x}<br>Costos %{y:,.0f}<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<CashDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Caja vs facturacion"
          description="Comparacion simple entre movimiento comercial y caja."
          summaryItems={[
            { label: 'Ventas dia', value: formatCurrency(data.summary.ventas_hoy_ars) },
            { label: 'Cobrado dia', value: formatCurrency(data.summary.cobranzas_hoy_ars) },
            { label: 'Saldo abierto', value: formatCurrency(data.summary.cobranza_abierta_ars) },
            { label: 'Estado', value: buildCashState(data.summary.cobranzas_hoy_ars, data.summary.ventas_hoy_ars, data.summary.cobranza_abierta_ars) },
          ]}
          contextText="Ayuda a ver si lo comercial se esta convirtiendo en caja o si el saldo abierto ya merece seguimiento."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={cashRows}
          detailColumns={cashColumns}
          exportFilename="gerencia-cobranzas-ventas"
          detailLabel="Resumen simple de ventas, cobranzas y saldo."
        >
          <SimpleChartCard
            title="Caja vs facturacion"
            description="Comparacion directa para ver si la caja acompana el ritmo comercial."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={260}
              showLegend={false}
              data={[
                {
                  x: cashRows.map((row) => row.concepto),
                  y: cashRows.map((row) => row.monto_ars),
                  name: 'Monto',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>%{y:,.0f}<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>
      </div>
    </div>
  )
}

export default function GerenciaPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <GerenciaPageContent />
    </Suspense>
  )
}
