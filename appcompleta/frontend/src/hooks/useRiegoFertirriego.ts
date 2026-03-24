import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import { buildFilterQueryString } from '@/lib/filter-query'
import type { RiegoData, RiegoFilters } from '@/types/lemon-riego'

export function useRiegoFertirriego(filters: RiegoFilters = {}) {
  const params = buildFilterQueryString(filters, '90D')

  const { data, error, isLoading, mutate } = useSWR<RiegoData>(
    `/riego/fertirriego${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 5000, dedupingInterval: 4000, revalidateOnFocus: false }
  )

  return { data, error, isLoading, mutate }
}
