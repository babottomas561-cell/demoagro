'use client'

import dynamic from 'next/dynamic'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { PLOTLY_LAYOUT_BASE } from '@/lib/constants'

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <SkeletonBlock className="h-full w-full" />,
})

interface GaugeChartProps {
  value: number
  min?: number
  max?: number
  title?: string
  unit?: string
  height?: number
  thresholds?: { value: number; color: string }[]
}

export function GaugeChart({
  value,
  min = 0,
  max = 100,
  title,
  unit = '%',
  height = 200,
  thresholds,
}: GaugeChartProps) {
  const defaultThresholds = [
    { value: 0.33, color: '#ef4444' },
    { value: 0.66, color: '#f59e0b' },
    { value: 1, color: '#4ade80' },
  ]

  const steps = (thresholds || defaultThresholds).map((t) => ({
    range: [min, t.value * max],
    color: `${t.color}20`,
  }))

  return (
    <Plot
      data={[
        {
          type: 'indicator',
          mode: 'gauge+number',
          value,
          number: {
            suffix: unit,
            font: { color: '#1b1a17', size: 24 },
          },
          title: title ? { text: title, font: { color: '#6f675b', size: 12 } } : undefined,
          gauge: {
            axis: {
              range: [min, max],
              tickcolor: 'transparent',
              tickfont: { color: '#8f8576', size: 10 },
            },
            bar: { color: '#30945a', thickness: 0.5 },
            bgcolor: '#f5f1e9',
            bordercolor: '#e6dfd3',
            borderwidth: 0,
            steps,
          },
        },
      ]}
      layout={{
        ...PLOTLY_LAYOUT_BASE,
        height,
        margin: { t: 16, r: 16, b: 8, l: 16, pad: 6 },
      }}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: '100%', height: `${height}px` }}
    />
  )
}
