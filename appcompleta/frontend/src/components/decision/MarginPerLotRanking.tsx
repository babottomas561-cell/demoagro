'use client'

import { BarChart } from '@/components/charts/BarChart'
import { SkeletonBlock } from '@/components/ui/Spinner'

interface MarginItem {
  lote: string
  margen_total?: number
  margen_ha: number
}

interface MarginPerLotRankingProps {
  items?: MarginItem[]
  loading?: boolean
  limit?: number
}

export function MarginPerLotRanking({
  items,
  loading,
  limit = 8,
}: MarginPerLotRankingProps) {
  if (loading) {
    return <SkeletonBlock className="h-72 w-full" />
  }

  if (!items?.length) {
    return (
      <div className="flex h-72 items-center justify-center rounded-2xl border border-dashed border-border bg-surface text-sm text-text-muted">
        Sin ranking de margen disponible.
      </div>
    )
  }

  const ranking = items.slice(0, limit)

  return (
    <BarChart
      data={[
        {
          x: ranking.map((item) => item.lote),
          y: ranking.map((item) => item.margen_total ?? item.margen_ha),
          name: 'Margen',
          color: '#30945a',
        },
      ]}
      horizontal
      height={320}
      showLegend={false}
      xAxisTitle="ARS"
    />
  )
}
