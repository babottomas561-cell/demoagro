'use client'

import { BarChart } from '@/components/charts/BarChart'
import { SkeletonBlock } from '@/components/ui/Spinner'

interface CostBreakdownItem {
  label: string
  value: number
  kind: 'positive' | 'negative' | 'total'
}

interface CostBreakdownChartProps {
  items?: CostBreakdownItem[]
  loading?: boolean
}

export function CostBreakdownChart({
  items,
  loading,
}: CostBreakdownChartProps) {
  if (loading) {
    return <SkeletonBlock className="h-72 w-full" />
  }

  if (!items?.length) {
    return (
      <div className="flex h-72 items-center justify-center rounded-2xl border border-dashed border-border bg-surface text-sm text-text-muted">
        Sin breakdown de costos disponible.
      </div>
    )
  }

  return (
    <BarChart
      data={[
        {
          x: items.map((item) => item.label),
          y: items.map((item) => Math.abs(item.value)),
          name: 'Valor',
          color: '#30945a',
        },
      ]}
      height={280}
      showLegend={false}
      yAxisTitle="ARS"
    />
  )
}
