'use client'

import dynamic from 'next/dynamic'
import { SkeletonBlock } from '@/components/ui/Spinner'
import { PLOTLY_LAYOUT_BASE } from '@/lib/constants'

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <SkeletonBlock className="h-full w-full" />,
})

interface BarChartProps {
  data: {
    x: Array<string | number>
    y: Array<string | number>
    name: string
    color?: string
    hovertemplate?: string
  }[]
  height?: number
  horizontal?: boolean
  showLegend?: boolean
  barmode?: 'group' | 'stack' | 'overlay'
  yAxisTitle?: string
  xAxisTitle?: string
  onClick?: () => void
}

export function BarChart({
  data,
  height = 280,
  horizontal = false,
  showLegend = true,
  barmode = 'group',
  yAxisTitle,
  xAxisTitle,
  onClick,
}: BarChartProps) {
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

  const traces = data.map((series, i) => {
    const defaultColors = ['#30945a', '#74866f', '#a79c89', '#cf6e63', '#c1b29a']
    return {
      type: 'bar' as const,
      name: series.name,
      x: horizontal ? series.y : series.x,
      y: horizontal ? series.x : series.y,
      orientation: horizontal ? ('h' as const) : ('v' as const),
      marker: {
        color: series.color || defaultColors[i % defaultColors.length],
        opacity: 0.82,
      },
      hovertemplate:
        series.hovertemplate ||
        (horizontal
          ? '%{y}<br>%{x:,.0f}<extra>%{fullData.name}</extra>'
          : '%{x}<br>%{y:,.0f}<extra>%{fullData.name}</extra>'),
    }
  })

  return (
    <Plot
      data={traces}
      layout={{
        ...PLOTLY_LAYOUT_BASE,
        height: effectiveHeight,
        barmode,
        showlegend: showLegend,
        bargap: 0.3,
        bargroupgap: 0.1,
        font: {
          ...PLOTLY_LAYOUT_BASE.font,
          size: isMobile ? 10 : PLOTLY_LAYOUT_BASE.font.size,
        },
        margin: isMobile
          ? { t: 18 + legendHeight, r: 16, b: horizontal ? 32 : 52, l: horizontal ? 112 : 50, pad: 6 }
          : {
              ...PLOTLY_LAYOUT_BASE.margin,
              t: 22 + legendHeight,
              r: 22,
              b: horizontal ? 34 : 52,
              l: horizontal ? 132 : 58,
            },
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
          tickangle: !horizontal && isMobile ? -28 : 0,
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
