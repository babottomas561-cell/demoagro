'use client'

import { BarChart } from '@/components/charts/BarChart'
import { SkeletonBlock } from '@/components/ui/Spinner'

interface PlanVsActualItem {
  labor: string
  plan_ha: number
  real_ha: number
}

interface PlanVsActualChartProps {
  items?: PlanVsActualItem[]
  loading?: boolean
  height?: number
}

export function PlanVsActualChart({
  items,
  loading,
  height = 280,
}: PlanVsActualChartProps) {
  if (loading) {
    return <SkeletonBlock className="h-72 w-full" />
  }

  if (!items?.length) {
    return (
      <div className="flex h-72 items-center justify-center rounded-2xl border border-dashed border-border bg-surface text-sm text-text-muted">
        Sin datos de avance planificado.
      </div>
    )
  }

  return (
    <BarChart
      data={[
        {
          x: items.map((item) => item.labor),
          y: items.map((item) => item.plan_ha),
          name: 'Plan',
          color: '#d6c7ad',
        },
        {
          x: items.map((item) => item.labor),
          y: items.map((item) => item.real_ha),
          name: 'Real',
          color: '#30945a',
        },
      ]}
      height={height}
      barmode="group"
      yAxisTitle="ha"
    />
  )
}
