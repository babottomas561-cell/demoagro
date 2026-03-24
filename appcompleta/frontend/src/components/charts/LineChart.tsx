'use client'

import dynamic from 'next/dynamic'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { PLOTLY_LAYOUT_BASE } from '@/lib/constants'

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <SkeletonBlock className="h-full w-full" />,
})

interface LineChartProps {
  data: {
    x: string[]
    y: (number | null)[]
    name: string
    color?: string
    dashed?: boolean
    fill?: 'tozeroy' | 'tonexty' | 'none'
    opacity?: number
    mode?: 'lines' | 'lines+markers'
    hovertemplate?: string
  }[]
  height?: number
  showLegend?: boolean
  yAxisTitle?: string
  xAxisTitle?: string
  connectGaps?: boolean
  onClick?: () => void
}

export function LineChart({
  data,
  height = 280,
  showLegend = true,
  yAxisTitle,
  xAxisTitle,
  connectGaps = false,
  onClick,
}: LineChartProps) {
  const defaultColors = ['#30945a', '#74866f', '#a79c89', '#cf6e63', '#c1b29a']
  // One-time read — no resize subscription, no cascade re-renders
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const effectiveHeight = isMobile ? Math.round(height * 0.72) : height

  if (data.every((series) => series.x.length === 0)) {
    return (
      <div className="flex items-center justify-center rounded-xl bg-[#f8f4ee]/60" style={{ height: effectiveHeight }}>
        <span className="text-[13px] text-text-muted">Sin datos para el período seleccionado</span>
      </div>
    )
  }
  const legendHeight = showLegend && isMobile ? 42 : showLegend ? 14 : 0

  const traces = data.map((series, i) => ({
    type: 'scatter' as const,
    mode: series.mode || ('lines+markers' as const),
    name: series.name,
    x: series.x,
    y: series.y,
    connectgaps: connectGaps,
    fill: series.fill,
    fillcolor: series.fill && series.fill !== 'none'
      ? `${series.color || defaultColors[i % defaultColors.length]}22`
      : undefined,
    opacity: series.opacity ?? 1,
      line: {
        color: series.color || defaultColors[i % defaultColors.length],
        width: 2,
        dash: series.dashed ? ('dot' as const) : ('solid' as const),
      },
      marker: {
        size: isMobile ? 2.5 : 3.5,
        color: series.color || defaultColors[i % defaultColors.length],
      },
    hovertemplate: series.hovertemplate || '%{y:,.2f}<extra>%{fullData.name}</extra>',
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
