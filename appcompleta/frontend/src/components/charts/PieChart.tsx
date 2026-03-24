'use client'

import dynamic from 'next/dynamic'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { PLOTLY_LAYOUT_BASE } from '@/lib/constants'

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <SkeletonBlock className="h-full w-full" />,
})

interface PieChartProps {
  labels: string[]
  values: number[]
  height?: number
  colors?: string[]
  hole?: number
  onClick?: () => void
}

export function PieChart({
  labels,
  values,
  height = 280,
  colors = ['#30945a', '#7d8f76', '#b2a48f', '#cf6e63', '#d8cbbb'],
  hole = 0.56,
  onClick,
}: PieChartProps) {
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const effectiveHeight = isMobile ? Math.round(height * 0.72) : height

  if (!labels.length || values.every((v) => v === 0)) {
    return (
      <div className="flex items-center justify-center rounded-xl bg-[#f8f4ee]/60" style={{ height: effectiveHeight }}>
        <span className="text-[13px] text-text-muted">Sin datos para el período seleccionado</span>
      </div>
    )
  }

  return (
    <Plot
      data={[
        {
          type: 'pie',
          labels,
          values,
          hole,
          textinfo: 'label+percent',
          textposition: 'inside',
          insidetextorientation: 'auto',
          textfont: { size: 11, color: '#1b1a17' },
          marker: {
            colors,
            line: { color: '#f5f1e9', width: 2 },
          },
          hovertemplate: '%{label}<br>%{value:,.0f}<br>%{percent}<extra></extra>',
          sort: false,
        },
      ]}
      layout={{
        ...PLOTLY_LAYOUT_BASE,
        height: effectiveHeight,
        showlegend: false,
        margin: { t: 20, r: 20, b: 20, l: 20, pad: 6 },
      }}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: '100%', height: `${effectiveHeight}px` }}
      onClick={onClick}
    />
  )
}
