import { DollarSign, Percent, Package, TrendingUp, Activity, Wallet, Calculator, BarChart2 } from 'lucide-react'
import { KPICard } from '@/components/ui/KPICard'
import { formatCurrency, formatPercent, formatToneladas } from '@/lib/formatters'
import type { KPISummary } from '@/types/dashboard'

interface KPIGridProps {
  data?: KPISummary
  loading?: boolean
}

export function KPIGrid({ data, loading }: KPIGridProps) {
  const kpis = [
    {
      title: 'Ventas Totales',
      value: data ? formatCurrency(data.ventas_totales) : '—',
      icon: DollarSign,
      delta: data?.variacion_campania_anterior,
      deltaLabel: 'vs campaña anterior',
      trend: (data?.variacion_campania_anterior ?? 0) >= 0 ? 'up' : 'down',
    },
    {
      title: 'Margen Bruto',
      value: data ? `${data.margen_bruto_pct.toFixed(1)}%` : '—',
      icon: Percent,
      trend: (data?.margen_bruto_pct ?? 0) >= 30 ? 'up' : 'down',
      description: 'Sobre ventas netas',
    },
    {
      title: 'Rendimiento Promedio',
      value: data ? formatToneladas(data.rendimiento_promedio) : '—',
      unit: 'tn/ha',
      icon: BarChart2,
      trend: 'neutral' as const,
      description: 'Promedio todos los cultivos',
    },
    {
      title: 'Stock Valorizado',
      value: data ? formatCurrency(data.stock_valorizado) : '—',
      icon: Package,
      trend: 'neutral' as const,
      description: 'A precio de mercado',
    },
    {
      title: 'EBITDA Estimado',
      value: data ? formatCurrency(data.ebitda_estimado) : '—',
      icon: TrendingUp,
      trend: (data?.ebitda_estimado ?? 0) >= 0 ? 'up' : 'down',
      description: 'Campaña actual',
    },
    {
      title: 'Flujo Neto Mensual',
      value: data ? formatCurrency(data.flujo_neto_mensual) : '—',
      icon: Activity,
      trend: (data?.flujo_neto_mensual ?? 0) >= 0 ? 'up' : 'down',
      description: 'Promedio últimos 3 meses',
    },
    {
      title: 'Costos Operativos',
      value: data ? formatCurrency(data.costos_operativos) : '—',
      icon: Calculator,
      trend: 'neutral' as const,
      invertColor: true,
      description: 'Campaña acumulado',
    },
    {
      title: 'Var. vs Campaña Ant.',
      value: data ? formatPercent(data.variacion_campania_anterior) : '—',
      icon: Wallet,
      trend: (data?.variacion_campania_anterior ?? 0) >= 0 ? 'up' : 'down',
      description: 'Ingresos comparativos',
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {kpis.map((kpi, i) => (
        <KPICard
          key={i}
          title={kpi.title}
          value={kpi.value}
          unit={kpi.unit}
          icon={kpi.icon}
          delta={kpi.delta}
          deltaLabel={kpi.deltaLabel}
          trend={kpi.trend as 'up' | 'down' | 'neutral'}
          description={kpi.description}
          loading={loading}
          invertColor={kpi.invertColor}
        />
      ))}
    </div>
  )
}
