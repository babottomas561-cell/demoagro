'use client'

import { BarChart } from '@/components/charts/BarChart'
import { SkeletonBlock } from '@/components/ui/Spinner'

interface PlanVsRealItem {
  label: string
  plan: number
  real: number
}

interface PlanVsRealChartProps {
  items?: PlanVsRealItem[]
  loading?: boolean
  yAxisTitle?: string
  height?: number
}

export function PlanVsRealChart({
  items,
  loading,
  yAxisTitle,
  height = 280,
}: PlanVsRealChartProps) {
  if (loading) {
    return <SkeletonBlock className="h-72 w-full" />
  }

  if (!items?.length) {
    return (
      <div className="flex h-72 items-center justify-center rounded-2xl border border-dashed border-border bg-surface text-sm text-text-muted">
        Sin datos plan vs real.
      </div>
    )
  }

  return (
    <BarChart
      data={[
        {
          x: items.map((item) => item.label),
          y: items.map((item) => item.plan),
          name: 'Plan',
          color: '#d6c7ad',
        },
        {
          x: items.map((item) => item.label),
          y: items.map((item) => item.real),
          name: 'Real',
          color: '#30945a',
        },
      ]}
      height={height}
      barmode="group"
      yAxisTitle={yAxisTitle}
    />
  )
}
