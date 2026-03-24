'use client'

import dynamic from 'next/dynamic'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { PLOTLY_LAYOUT_BASE } from '@/lib/constants'

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <SkeletonBlock className="h-full w-full" />,
})

interface AreaChartProps {
  data: {
    x: string[]
    y: number[]
    name: string
    color?: string
    dashed?: boolean
    hovertemplate?: string
  }[]
  height?: number
  showLegend?: boolean
  stacked?: boolean
  yAxisTitle?: string
  xAxisTitle?: string
  onClick?: () => void
}

export function AreaChart({
  data,
  height = 280,
  showLegend = true,
  stacked = false,
  yAxisTitle,
  xAxisTitle,
  onClick,
}: AreaChartProps) {
  // One-time read — no resize subscription, no cascade re-renders
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const effectiveHeight = isMobile ? Math.round(height * 0.72) : height
  const legendHeight = showLegend && isMobile ? 42 : showLegend ? 14 : 0

  const traces = data.map((series) => ({
    type: 'scatter' as const,
    mode: 'lines' as const,
    name: series.name,
    x: series.x,
    y: series.y,
    fill: stacked ? ('tonexty' as const) : ('tozeroy' as const),
    line: {
      color: series.color || '#4ade80',
      width: 2,
      dash: series.dashed ? ('dot' as const) : ('solid' as const),
    },
    fillcolor: series.color
      ? `${series.color}12`
      : 'rgba(48,148,90,0.08)',
    hovertemplate: series.hovertemplate || '%{y:,.0f}<extra>%{fullData.name}</extra>',
  }))

  return (
    <Plot
      data={traces}
      layout={{
        ...PLOTLY_LAYOUT_BASE,
        height: effectiveHeight,
        showlegend: showLegend,
        font: {
          ...PLOTLY_LAYOUT_BASE.font,
          size: isMobile ? 10 : PLOTLY_LAYOUT_BASE.font.size,
        },
        margin: isMobile
          ? { t: 18 + legendHeight, r: 16, b: 46, l: 48, pad: 6 }
          : { ...PLOTLY_LAYOUT_BASE.margin, t: 22 + legendHeight, r: 20, b: 48, l: 58 },
        legend: {
          ...PLOTLY_LAYOUT_BASE.legend,
          orientation: isMobile ? 'h' : 'v',
          x: 0,
          y: isMobile ? 1.18 : 1,
          xanchor: 'left',
          yanchor: isMobile ? 'bottom' : 'top',
          font: {
            ...PLOTLY_LAYOUT_BASE.legend.font,
            size: isMobile ? 10 : undefined,
          },
        },
        xaxis: {
          ...PLOTLY_LAYOUT_BASE.xaxis,
          automargin: true,
          tickfont: {
            ...PLOTLY_LAYOUT_BASE.xaxis.tickfont,
            size: isMobile ? 10 : undefined,
          },
          tickangle: isMobile ? -28 : 0,
          title: !isMobile && xAxisTitle ? { text: xAxisTitle, font: { size: 11 } } : undefined,
        },
        yaxis: {
          ...PLOTLY_LAYOUT_BASE.yaxis,
          automargin: true,
          tickfont: {
            ...PLOTLY_LAYOUT_BASE.yaxis.tickfont,
            size: isMobile ? 10 : undefined,
          },
          title: !isMobile && yAxisTitle ? { text: yAxisTitle, font: { size: 11 } } : undefined,
        },
      }}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: '100%', height: `${effectiveHeight}px` }}
      onClick={onClick}
    />
  )
}
