import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import { buildFilterQueryString } from '@/lib/filter-query'
import type { PackhouseData, PackhouseFilters } from '@/types/lemon-packhouse'

export function usePackhouseControl(filters: PackhouseFilters = {}) {
  const params = buildFilterQueryString(filters, '30D')

  const { data, error, isLoading, mutate } = useSWR<PackhouseData>(
    `/packhouse/control${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 3000, dedupingInterval: 2000, revalidateOnFocus: false }
  )

  return { data, error, isLoading, mutate }
}
