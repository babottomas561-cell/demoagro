'use client'

import dynamic from 'next/dynamic'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { PLOTLY_LAYOUT_BASE } from '@/lib/constants'

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <SkeletonBlock className="h-full w-full" />,
})

interface ScatterChartProps {
  data: {
    x: number[]
    y: number[]
    text?: string[]
    name: string
    color?: string
    hovertemplate?: string
  }[]
  height?: number
  showLegend?: boolean
  xAxisTitle?: string
  yAxisTitle?: string
  onClick?: () => void
}

export function ScatterChart({
  data,
  height = 280,
  showLegend = true,
  xAxisTitle,
  yAxisTitle,
  onClick,
}: ScatterChartProps) {
  // One-time read — no resize subscription, no cascade re-renders
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const legendHeight = showLegend && isMobile ? 42 : showLegend ? 14 : 0
  const traces = data.map((series) => ({
    type: 'scatter' as const,
    mode: 'markers' as const,
    name: series.name,
    x: series.x,
    y: series.y,
    text: series.text,
    marker: {
      color: series.color || '#30945a',
      size: isMobile ? 8 : 10,
      opacity: 0.78,
      line: {
        color: '#fffdf9',
        width: 1,
      },
    },
    hovertemplate:
      series.hovertemplate || '%{text}<br>X %{x:,.2f}<br>Y %{y:,.2f}<extra>%{fullData.name}</extra>',
  }))

  return (
    <Plot
      data={traces}
      layout={{
        ...PLOTLY_LAYOUT_BASE,
        height,
        showlegend: showLegend,
        font: {
          ...PLOTLY_LAYOUT_BASE.font,
          size: isMobile ? 10 : PLOTLY_LAYOUT_BASE.font.size,
        },
        margin: isMobile
          ? { t: 18 + legendHeight, r: 16, b: 46, l: 50, pad: 6 }
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
          tickangle: isMobile ? -20 : 0,
          title: !isMobile && xAxisTitle ? { text: xAxisTitle, font: { size: 11 } } : undefined,
        },
        yaxis: {
          ...PLOTLY_LAYOUT_BASE.yaxis,
          automargin: true,
          title: !isMobile && yAxisTitle ? { text: yAxisTitle, font: { size: 11 } } : undefined,
        },
      }}
      config={{ displayModeBar: false, responsive: true }}
      useResizeHandler
      style={{ width: '100%', height: `${height}px` }}
      onClick={onClick}
    />
  )
}
