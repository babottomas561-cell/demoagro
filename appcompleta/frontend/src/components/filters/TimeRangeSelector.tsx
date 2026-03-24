'use client'

import clsx from 'clsx'
import type { TimeRange } from '@/lib/time-series'
import { TIME_RANGE_OPTIONS } from '@/lib/time-series'

interface TimeRangeSelectorProps {
  value: TimeRange
  onChange: (value: TimeRange) => void
  className?: string
}

export function TimeRangeSelector({
  value,
  onChange,
  className,
}: TimeRangeSelectorProps) {
  return (
    <div
      className={clsx(
        'inline-flex max-w-full items-center gap-1 overflow-x-auto rounded-full border border-border/80 bg-[#f7f4ec] p-1 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden',
        className
      )}
    >
      {TIME_RANGE_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={clsx(
            'shrink-0 rounded-full px-3 py-1.5 text-[11px] font-semibold tracking-[0.08em] transition-colors',
            value === option.value
              ? 'bg-primary-600 text-white'
              : 'text-text-muted hover:bg-white hover:text-text'
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
