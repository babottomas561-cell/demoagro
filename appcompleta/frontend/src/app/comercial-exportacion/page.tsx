'use client'

import { Suspense, useMemo } from 'react'
import type { ColDef } from 'ag-grid-community'
import { Ship } from 'lucide-react'
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
import { useComercialExportacion } from '@/hooks/useComercialExportacion'
import { usePageFilters } from '@/hooks/usePageFilters'
import { buildAppliedFilters } from '@/lib/drilldown'
import { formatCurrency, formatDate, formatNumber, formatToneladas } from '@/lib/formatters'
import { takeLastItems } from '@/lib/operational-dashboard'
import type { ComercialCanalRow, ComercialCobranzaClienteRow, ComercialMercadoRow, ComercialSerieRow } from '@/types/lemon-comercial'

type CommercialDailyDetailRow = ComercialSerieRow & { estado: string }
type CommercialMarketDetailRow = ComercialMercadoRow & { estado: string }
type CommercialChannelDetailRow = ComercialCanalRow & { estado: string }
type CommercialClientDetailRow = ComercialCobranzaClienteRow & { estado: string }

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

function ComercialExportacionPageContent() {
  const filters = usePageFilters([
    'empresa_id',
    'campania_id',
    'establecimiento_id',
    'campo_id',
    'lote_id',
    'variedad_id',
    'cliente_id',
    'mercado_id',
    'canal_id',
    'moneda',
  ])
  const { data, error, isLoading } = useComercialExportacion(filters)
  const executiveScope = useExecutiveScope(filters)
  const appliedFilters = useMemo(() => buildAppliedFilters(filters), [filters])

  const priceRows = useMemo(() => takeLastItems(data?.series.precio_diario || [], 30), [data?.series.precio_diario])
  const latestPriceRow = priceRows[priceRows.length - 1]
  const averagePrice = useMemo(() => {
    return data?.summary.precio_realizado_usd_tn || 0
  }, [data?.summary.precio_realizado_usd_tn])

  const dailyDetailRows = useMemo<CommercialDailyDetailRow[]>(
    () =>
      priceRows.map((row) => ({
        ...row,
        estado:
          (row.precio_realizado_usd_tn || row.precio_referencia_usd_tn) < averagePrice * 0.95
            ? 'Atencion'
            : 'Bien',
      })),
    [averagePrice, priceRows]
  )

  const marketRows = useMemo<CommercialMarketDetailRow[]>(
    () =>
      [...(data?.breakdown.mercados || [])]
        .sort((a, b) => b.toneladas - a.toneladas)
        .map((row) => ({
          ...row,
          estado: row.precio_promedio_usd_tn < (data?.summary.precio_objetivo_usd_tn || 0) ? 'Atencion' : 'Bien',
        })),
    [data?.breakdown.mercados, data?.summary.precio_objetivo_usd_tn]
  )

  const channelRows = useMemo<CommercialChannelDetailRow[]>(
    () =>
      [...(data?.breakdown.canales || [])]
        .sort((a, b) => b.toneladas - a.toneladas)
        .map((row) => ({
          ...row,
          estado: row.precio_promedio_usd_tn < row.precio_referencia_usd_tn * 0.97 ? 'Atencion' : 'Bien',
        })),
    [data?.breakdown.canales]
  )

  const clientRows = useMemo<CommercialClientDetailRow[]>(
    () =>
      [...(data?.breakdown.clientes_cobranza || [])]
        .sort((a, b) => b.saldo_abierto_ars - a.saldo_abierto_ars)
        .map((row) => ({
          ...row,
          estado: row.vencido_ars > 0 ? 'Critico' : 'Atencion',
        })),
    [data?.breakdown.clientes_cobranza]
  )

  const focusTone = useMemo<'success' | 'warning' | 'danger'>(() => {
    if ((clientRows[0]?.vencido_ars || 0) > 0 || (data?.summary.pendiente_entrega_tn || 0) > (data?.summary.ventas_hoy_tn || 0) * 3) return 'danger'
    if (((data?.summary.precio_hoy_realizado_usd_tn || data?.summary.precio_hoy_usd_tn || 0) < (data?.summary.precio_objetivo_usd_tn || 0))) return 'warning'
    return 'success'
  }, [
    clientRows,
    data?.summary.pendiente_entrega_tn,
    data?.summary.precio_hoy_realizado_usd_tn,
    data?.summary.precio_hoy_usd_tn,
    data?.summary.precio_objetivo_usd_tn,
    data?.summary.ventas_hoy_tn,
  ])

  const focusBullets = useMemo(() => {
    const topClient = clientRows[0]
    const topMarket = marketRows[0]
    const realizedToday = data?.summary.precio_hoy_realizado_usd_tn || data?.summary.precio_hoy_usd_tn || 0
    return [
      `El precio realizado del ultimo dia fue USD ${formatNumber(realizedToday, 2)}/tn frente a un objetivo de USD ${formatNumber(data?.summary.precio_objetivo_usd_tn || 0, 2)}/tn.`,
      topClient
        ? `${topClient.cliente} concentra hoy el mayor riesgo de cobranza, con ${formatCurrency(topClient.saldo_abierto_ars)} abiertos y ${formatCurrency(topClient.vencido_ars)} vencidos.`
        : '',
      topMarket
        ? `${topMarket.mercado} sigue siendo el mercado de mayor volumen, con ${formatToneladas(topMarket.toneladas, 1)}.`
        : '',
    ]
  }, [clientRows, data?.summary.precio_hoy_realizado_usd_tn, data?.summary.precio_hoy_usd_tn, data?.summary.precio_objetivo_usd_tn, marketRows])

  const dailyColumns = useMemo<ColDef<CommercialDailyDetailRow>[]>(
    () => [
      { field: 'fecha', headerName: 'Fecha', valueFormatter: ({ value }) => formatDate(String(value || '')) },
      { field: 'precio_realizado_usd_tn', headerName: 'Precio realizado', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}/tn` },
      { field: 'precio_referencia_usd_tn', headerName: 'Referencia', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}/tn` },
      { field: 'volumen_tn', headerName: 'Volumen', valueFormatter: ({ value }) => formatToneladas(Number(value || 0), 1) },
      { field: 'mercado', headerName: 'Mercado' },
      { field: 'canal', headerName: 'Canal' },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const marketColumns = useMemo<ColDef<CommercialMarketDetailRow>[]>(
    () => [
      { field: 'mercado', headerName: 'Mercado' },
      { field: 'toneladas', headerName: 'Tn', valueFormatter: ({ value }) => formatToneladas(Number(value || 0), 1) },
      { field: 'precio_promedio_usd_tn', headerName: 'Realizado', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}/tn` },
      { field: 'precio_referencia_usd_tn', headerName: 'Referencia', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}/tn` },
      { field: 'participacion_pct', headerName: 'Participacion %', valueFormatter: ({ value }) => `${formatNumber(Number(value || 0), 1)}%` },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const channelColumns = useMemo<ColDef<CommercialChannelDetailRow>[]>(
    () => [
      { field: 'canal', headerName: 'Canal' },
      { field: 'toneladas', headerName: 'Tn', valueFormatter: ({ value }) => formatToneladas(Number(value || 0), 1) },
      { field: 'precio_promedio_usd_tn', headerName: 'Realizado', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}/tn` },
      { field: 'precio_referencia_usd_tn', headerName: 'Referencia', valueFormatter: ({ value }) => `USD ${formatNumber(Number(value || 0), 2)}/tn` },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  const clientColumns = useMemo<ColDef<CommercialClientDetailRow>[]>(
    () => [
      { field: 'cliente', headerName: 'Cliente' },
      { field: 'saldo_abierto_ars', headerName: 'Saldo abierto', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'vencido_ars', headerName: 'Vencido', valueFormatter: ({ value }) => formatCurrency(Number(value || 0)) },
      { field: 'facturas_abiertas', headerName: 'Facturas', valueFormatter: ({ value }) => formatNumber(Number(value || 0), 0) },
      { field: 'estado', headerName: 'Estado' },
    ],
    []
  )

  if (error && !data) {
    return (
      <Alert variant="danger" title="No se pudo cargar Comercial / Exportacion">
        Revisa contratos, embarques, precios, liquidaciones y cobranzas del ERP limonero.
      </Alert>
    )
  }

  if (isLoading || !data) return <PageSkeleton />

  return (
    <div className="space-y-6">
      <DashboardLead
        title="Comercial / Exportacion"
        description="Control diario comercial para ver precio, volumen, cobranza y clientes en seguimiento."
        icon={Ship}
        label="Panel operativo diario"
        scopeLabel={executiveScope.label}
        scopeBadges={executiveScope.badges}
      />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SimpleKpiCard
          label="Precio hoy"
          value={`USD ${formatNumber(data.summary.precio_hoy_realizado_usd_tn || data.summary.precio_hoy_usd_tn, 2)}/tn`}
          delta={`${data.summary.precio_contexto_mercado} · ${data.summary.precio_contexto_canal}`}
          detail={`Promedio del ultimo dia con volumen. Base: ${formatToneladas(data.summary.precio_contexto_volumen_tn || 0, 1)}.`}
          tone={(data.summary.precio_hoy_realizado_usd_tn || data.summary.precio_hoy_usd_tn) >= data.summary.precio_objetivo_usd_tn ? 'positive' : 'warning'}
        />
        <SimpleKpiCard
          label="Ventas hoy"
          value={formatToneladas(data.summary.ventas_hoy_tn, 1)}
          delta="Ultimo dia operativo"
          detail="Volumen despachado para seguir ritmo comercial real."
          tone={data.summary.ventas_hoy_tn > 0 ? 'positive' : 'warning'}
        />
        <SimpleKpiCard
          label="Cumpl. contratos"
          value={`${formatNumber(data.summary.cumplimiento_contratos_pct, 1)}%`}
          delta={data.summary.cumplimiento_contratos_pct >= 90 ? 'En objetivo' : 'Bajo objetivo'}
          detail="Porcentaje de contratos de venta cumplidos sobre el total comprometido en la campaña."
          tone={data.summary.cumplimiento_contratos_pct >= 90 ? 'positive' : data.summary.cumplimiento_contratos_pct >= 75 ? 'warning' : 'danger'}
        />
        <SimpleKpiCard
          label="Días prom. cobro"
          value={data.summary.dias_promedio_cobro != null ? `${formatNumber(data.summary.dias_promedio_cobro, 0)} días` : 'Sin cobros'}
          delta={data.summary.dias_promedio_cobro != null ? (data.summary.dias_promedio_cobro > 75 ? 'Crítico · >75 días' : data.summary.dias_promedio_cobro > 45 ? 'Atención · >45 días' : 'OK · <45 días') : 'Sin cobros completos'}
          detail={data.summary.dias_promedio_cobro_detail || 'Días promedio entre emisión de factura y cobro. Con inflación argentina, cobrar tarde destruye margen real en ARS.'}
          tone={data.summary.dias_promedio_cobro == null ? 'neutral' : data.summary.dias_promedio_cobro > 75 ? 'danger' : data.summary.dias_promedio_cobro > 45 ? 'warning' : 'positive'}
        />
      </div>

      {/* KPI con torta — mercados, canales, contratos, cobranza */}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MiniPieKpiCard
          label="Mix de mercados"
          centerValue={`${formatNumber(marketRows[0]?.participacion_pct || 0, 0)}%`}
          centerSub={marketRows[0]?.mercado || ''}
          slices={marketRows.slice(0, 4).map((r) => ({
            label: r.mercado,
            value: Math.round(r.participacion_pct),
          }))}
          tone="neutral"
        />
        <MiniPieKpiCard
          label="Mix de canales"
          centerValue={`${formatToneladas(channelRows[0]?.toneladas || 0, 1)}`}
          centerSub={channelRows[0]?.canal || ''}
          slices={(() => {
            if (!channelRows.length) return [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]
            const total = channelRows.reduce((s, r) => s + r.toneladas, 0)
            return channelRows.slice(0, 4).map((r) => ({
              label: r.canal,
              value: total > 0 ? Math.round((r.toneladas / total) * 100) : 0,
            }))
          })()}
          tone="neutral"
        />
        <MiniPieKpiCard
          label="Cumplimiento contratos"
          centerValue={`${formatNumber(data.summary.cumplimiento_contratos_pct, 1)}%`}
          centerSub="Entregado"
          slices={[
            { label: 'Entregado', value: Math.round(data.summary.cumplimiento_contratos_pct), color: '#30945a' },
            { label: 'Pendiente', value: Math.round(Math.max(0, 100 - data.summary.cumplimiento_contratos_pct)), color: '#d8cbbb' },
          ]}
          tone={data.summary.cumplimiento_contratos_pct >= 90 ? 'positive' : data.summary.cumplimiento_contratos_pct >= 75 ? 'warning' : 'danger'}
        />
        <MiniPieKpiCard
          label="Cobranza por cliente"
          centerValue={(() => {
            const total = clientRows.reduce((s, r) => s + r.saldo_abierto_ars, 0)
            const top = clientRows[0]
            return top && total > 0 ? `${formatNumber((top.saldo_abierto_ars / total) * 100, 0)}%` : '-'
          })()}
          centerSub={clientRows[0]?.cliente || ''}
          slices={(() => {
            if (!clientRows.length) return [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]
            const total = clientRows.reduce((s, r) => s + r.saldo_abierto_ars, 0)
            return clientRows.slice(0, 4).map((r) => ({
              label: r.cliente,
              value: total > 0 ? Math.round((r.saldo_abierto_ars / total) * 100) : 0,
            }))
          })()}
          tone={!clientRows.length ? 'neutral' : (clientRows[0].vencido_ars || 0) > 0 ? 'danger' : 'warning'}
        />
      </div>

      <OperationalFocusAlert title="Foco operativo del dia" tone={focusTone} bullets={focusBullets} />

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartWithDrillDown<CommercialDailyDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Precio diario"
          description="Detalle diario de precio realizado, referencia y volumen."
          summaryItems={[
            { label: 'Realizado promedio', value: `USD ${formatNumber(data.summary.precio_realizado_usd_tn, 2)}/tn` },
            { label: 'Referencia promedio', value: `USD ${formatNumber(data.summary.precio_referencia_usd_tn, 2)}/tn` },
            { label: 'Ultimo realizado', value: `USD ${formatNumber(latestPriceRow?.precio_realizado_usd_tn || 0, 2)}/tn` },
            { label: 'Volumen 30 dias', value: formatToneladas(priceRows.reduce((acc, row) => acc + row.volumen_tn, 0), 1) },
            { label: 'Objetivo', value: `USD ${formatNumber(data.summary.precio_objetivo_usd_tn, 2)}/tn` },
          ]}
          contextText="El realizado sale de embarques del ERP y la referencia sale de precio_venta_fact; ambas curvas sirven para ver si el negocio va arriba o abajo de la referencia."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={dailyDetailRows}
          detailColumns={dailyColumns}
          exportFilename="comercial-precio-tiempo"
          detailLabel="Precio y volumen diario."
        >
          <SimpleChartCard
            title="Precio diario"
            description="Realizado solo en días con embarque (null en días sin despacho); referencia interna continua como contexto de mercado."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <LineChart
              height={320}
              showLegend
              connectGaps
              data={[
                {
                  x: priceRows.map((row) => row.fecha),
                  y: priceRows.map((row) => row.precio_realizado_usd_tn > 0 ? row.precio_realizado_usd_tn : null),
                  name: 'Realizado',
                  color: '#30945a',
                  mode: 'lines+markers',
                  hovertemplate: '%{x}<br>USD %{y:.2f}/tn<extra></extra>',
                },
                {
                  x: priceRows.map((row) => row.fecha),
                  y: priceRows.map((row) => row.precio_referencia_usd_tn > 0 ? row.precio_referencia_usd_tn : null),
                  name: 'Referencia',
                  color: '#b2a48f',
                  dashed: true,
                  hovertemplate: '%{x}<br>USD %{y:.2f}/tn<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<CommercialMarketDetailRow>
          title="Informe ERP · Volumen por mercado"
          description="Comparacion simple del volumen exportado por mercado."
          summaryItems={[
            { label: 'Mercados', value: formatNumber(marketRows.length, 0) },
            { label: 'Mayor volumen', value: marketRows[0]?.mercado || 'Sin dato' },
            { label: 'Toneladas', value: formatToneladas(marketRows[0]?.toneladas || 0, 1) },
            { label: 'Realizado', value: `USD ${formatNumber(marketRows[0]?.precio_promedio_usd_tn || 0, 2)}/tn` },
          ]}
          contextText="Permite ver rapido donde se concentra el volumen y comparar el precio realizado de cada mercado con su referencia."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={marketRows}
          detailColumns={marketColumns}
          exportFilename="comercial-mercados"
          detailLabel="Detalle por mercado."
        >
          <SimpleChartCard
            title="Volumen por mercado"
            description="Comparacion simple para ver donde se concentra la salida comercial."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              showLegend={false}
              data={[
                {
                  x: marketRows.map((row) => row.mercado),
                  y: marketRows.map((row) => row.toneladas),
                  name: 'Toneladas',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>%{y:,.1f} tn<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<CommercialChannelDetailRow>
          title="Informe ERP · Precio por canal"
          description="Comparacion simple de precio realizado y referencia por canal."
          summaryItems={[
            { label: 'Canales', value: formatNumber(channelRows.length, 0) },
            { label: 'Canal principal', value: channelRows[0]?.canal || 'Sin dato' },
            { label: 'Realizado', value: `USD ${formatNumber(channelRows[0]?.precio_promedio_usd_tn || 0, 2)}/tn` },
            { label: 'Referencia', value: `USD ${formatNumber(channelRows[0]?.precio_referencia_usd_tn || 0, 2)}/tn` },
          ]}
          contextText="Ayuda a comparar exportacion, local e industria sin esconder que cada canal tiene una logica de precio distinta."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={channelRows}
          detailColumns={channelColumns}
          exportFilename="comercial-precio-canal"
          detailLabel="Precios por canal con volumen y estado."
        >
          <SimpleChartCard
            title="Precio por canal"
            description="Comparacion simple para no hablar de un precio unico del limon."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={280}
              barmode="group"
              data={[
                {
                  x: channelRows.map((row) => row.canal),
                  y: channelRows.map((row) => row.precio_promedio_usd_tn),
                  name: 'Realizado',
                  color: '#30945a',
                  hovertemplate: '%{x}<br>USD %{y:.2f}/tn<extra></extra>',
                },
                {
                  x: channelRows.map((row) => row.canal),
                  y: channelRows.map((row) => row.precio_referencia_usd_tn),
                  name: 'Referencia',
                  color: '#b2a48f',
                  hovertemplate: '%{x}<br>USD %{y:.2f}/tn<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>

        <ChartWithDrillDown<CommercialClientDetailRow>
          className="xl:col-span-2"
          title="Informe ERP · Clientes con saldo"
          description="Ranking simple de clientes con saldo abierto."
          summaryItems={[
            { label: 'Clientes', value: formatNumber(clientRows.length, 0) },
            { label: 'Mayor saldo', value: clientRows[0]?.cliente || 'Sin dato' },
            { label: 'Saldo', value: formatCurrency(clientRows[0]?.saldo_abierto_ars || 0) },
            { label: 'Vencido', value: formatCurrency(clientRows[0]?.vencido_ars || 0) },
          ]}
          contextText="Sirve para ver rapido a que clientes conviene seguir primero por cobranza."
          source={data.meta.source}
          lastUpdated={data.meta.last_updated}
          filtersApplied={appliedFilters}
          detailRows={clientRows}
          detailColumns={clientColumns}
          exportFilename="comercial-clientes"
          detailLabel="Clientes con saldo abierto."
        >
          <SimpleChartCard
            title="Clientes con saldo"
            description="Comparacion simple para ver donde esta concentrado el riesgo de cobro."
            actions={<DataSourceTag fuente={data.meta.source} ultimaActualizacion={data.meta.last_updated} live />}
          >
            <BarChart
              height={300}
              horizontal
              showLegend={false}
              data={[
                {
                  x: clientRows.slice(0, 8).map((row) => row.cliente),
                  y: clientRows.slice(0, 8).map((row) => row.saldo_abierto_ars),
                  name: 'Saldo abierto',
                  color: '#cf6e63',
                  hovertemplate: '%{y}<br>%{x:,.0f}<extra></extra>',
                },
              ]}
            />
          </SimpleChartCard>
        </ChartWithDrillDown>
      </div>
    </div>
  )
}

export default function ComercialExportacionPage() {
  return (
    <Suspense fallback={<PageSkeleton />}>
      <ComercialExportacionPageContent />
    </Suspense>
  )
}
