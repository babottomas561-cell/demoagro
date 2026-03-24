'use client'

import dynamic from 'next/dynamic'
import clsx from 'clsx'
import { SkeletonBlock } from '@/components/ui/Spinner'

const Plot = dynamic(() => import('react-plotly.js'), {
  ssr: false,
  loading: () => <SkeletonBlock className="h-full w-full" />,
})

interface MiniPieSlice {
  label: string
  value: number
  color?: string
}

interface MiniPieKpiCardProps {
  label: string
  centerValue: string
  centerSub?: string
  slices: MiniPieSlice[]
  tone?: 'neutral' | 'positive' | 'warning' | 'danger'
}

const DEFAULT_COLORS = ['#30945a', '#7d8f76', '#b2a48f', '#cf6e63', '#d8cbbb']

const toneAccentClass: Record<string, string> = {
  neutral: 'bg-[#d9d1c3]',
  positive: 'bg-primary-600',
  warning: 'bg-[#d69f2f]',
  danger: 'bg-danger',
}

const NO_DATA_SLICE: MiniPieSlice[] = [{ label: 'Sin datos', value: 1, color: '#d8cbbb' }]

export function MiniPieKpiCard({
  label,
  centerValue,
  centerSub,
  slices,
  tone = 'neutral',
}: MiniPieKpiCardProps) {
  const isMobile = typeof window !== 'undefined' && window.innerWidth < 768
  const chartSize = isMobile ? 110 : 130

  const isEmpty = !slices.length || slices.every((s) => s.value === 0)
  const effectiveSlices = isEmpty ? NO_DATA_SLICE : slices
  const colors = effectiveSlices.map((s, i) => s.color ?? DEFAULT_COLORS[i % DEFAULT_COLORS.length])

  return (
    <article className="relative flex min-h-[7.5rem] flex-col overflow-hidden rounded-[1.55rem] border border-[#e8dfd1] bg-[linear-gradient(180deg,rgba(255,253,249,0.98),rgba(249,245,238,0.96))] p-3.5 shadow-[0_1px_0_rgba(24,20,12,0.03)] sm:min-h-[8.5rem] sm:p-4">
      <div className={clsx('absolute inset-x-0 top-0 h-1', toneAccentClass[tone])} />

      {/* Label */}
      <div className="flex items-center gap-2">
        <span className={clsx('h-2 w-2 rounded-full', toneAccentClass[tone])} />
        <p className="truncate text-[10px] font-bold uppercase tracking-[0.16em] text-text-subtle">{label}</p>
      </div>

      <div className="mt-1 flex items-center gap-2">
        {/* Donut */}
        <div className="relative shrink-0" style={{ width: chartSize, height: chartSize }}>
          <Plot
            data={[
              {
                type: 'pie',
                labels: effectiveSlices.map((s) => s.label),
                values: effectiveSlices.map((s) => s.value),
                hole: 0.62,
                textinfo: 'none',
                hovertemplate: '%{label}: %{percent}<extra></extra>',
                marker: { colors, line: { color: '#f5f1e9', width: 1.5 } },
                sort: false,
              },
            ]}
            layout={{
              height: chartSize,
              width: chartSize,
              margin: { t: 0, r: 0, b: 0, l: 0, pad: 0 },
              showlegend: false,
              paper_bgcolor: 'rgba(0,0,0,0)',
              plot_bgcolor: 'rgba(0,0,0,0)',
            }}
            config={{ displayModeBar: false, responsive: false }}
            style={{ width: chartSize, height: chartSize }}
          />
          {/* Center text */}
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-[1.05rem] font-extrabold leading-none tracking-[-0.04em] text-text">{centerValue}</span>
            {centerSub ? <span className="mt-0.5 text-[9px] font-semibold uppercase tracking-wider text-text-muted">{centerSub}</span> : null}
          </div>
        </div>

        {/* Legend */}
        <ul className="flex min-w-0 flex-col gap-1">
          {isEmpty ? (
            <li className="flex items-center gap-1.5">
              <span className="h-2 w-2 shrink-0 rounded-full bg-[#d8cbbb]" />
              <span className="text-[10px] text-text-muted">Sin datos</span>
            </li>
          ) : slices.map((s, i) => (
            <li key={s.label} className="flex items-center gap-1.5 min-w-0">
              <span
                className="h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: colors[i] }}
              />
              <span className="truncate text-[10px] text-text-muted">{s.label}</span>
              <span className="ml-auto shrink-0 text-[10px] font-semibold text-text">{s.value}%</span>
            </li>
          ))}
        </ul>
      </div>
    </article>
  )
}
