'use client'

import { startTransition, useMemo } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import type { TimeRange } from '@/lib/time-series'

const VALID_RANGES: TimeRange[] = ['7D', '30D', '90D', 'YTD', '12M', 'ALL']

export function useTimeRangeQuery(defaultRange: TimeRange = '90D') {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()

  const range = useMemo<TimeRange>(() => {
    const current = (searchParams.get('periodo') || '').toUpperCase() as TimeRange
    return VALID_RANGES.includes(current) ? current : defaultRange
  }, [defaultRange, searchParams])

  const setRange = (nextRange: TimeRange) => {
    const params = new URLSearchParams(searchParams.toString())
    if (nextRange === defaultRange) {
      params.delete('periodo')
    } else {
      params.set('periodo', nextRange)
    }

    const query = params.toString()
    startTransition(() => {
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
    })
  }

  return { range, setRange }
}

