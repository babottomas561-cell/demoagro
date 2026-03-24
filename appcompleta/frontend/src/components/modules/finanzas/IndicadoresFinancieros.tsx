import { Wallet, AlertTriangle, Receipt, TrendingUp } from 'lucide-react'
import { KPICard } from '@/components/ui/KPICard'
import { formatCurrency } from '@/lib/formatters'
import type { FinanzasSummary } from '@/types/finanzas'

interface IndicadoresFinancierosProps {
  summary?: FinanzasSummary
  loading?: boolean
}

export function IndicadoresFinancieros({ summary, loading }: IndicadoresFinancierosProps) {
  const kpis = [
    {
      title: 'Capital de Trabajo',
      value: summary ? formatCurrency(summary.capital_de_trabajo) : '—',
      icon: Wallet,
      trend: (summary?.capital_de_trabajo ?? 0) >= 0 ? 'up' : 'down',
      description: 'Activo corriente neto',
    },
    {
      title: 'Compromisos 90 días',
      value: summary ? formatCurrency(summary.deuda_por_vencer) : '—',
      icon: AlertTriangle,
      trend: 'down' as const,
      invertColor: true,
      description: 'Egresos estimados',
    },
    {
      title: 'Cuentas a Cobrar',
      value: summary ? formatCurrency(summary.cuentas_a_cobrar) : '—',
      icon: Receipt,
      trend: 'neutral' as const,
      description: 'Pendiente de cobro',
    },
    {
      title: 'Flujo Neto',
      value: summary ? formatCurrency(summary.flujo_neto) : '—',
      icon: TrendingUp,
      trend: (summary?.flujo_neto ?? 0) >= 0 ? 'up' : 'down',
      description: 'Mes en curso',
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {kpis.map((kpi, i) => (
        <KPICard
          key={i}
          title={kpi.title}
          value={kpi.value}
          icon={kpi.icon}
          trend={kpi.trend as 'up' | 'down' | 'neutral'}
          description={kpi.description}
          loading={loading}
          invertColor={kpi.invertColor}
        />
      ))}
    </div>
  )
}
