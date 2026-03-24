import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import { buildFilterQueryString } from '@/lib/filter-query'
import type { SanidadData, SanidadFilters } from '@/types/lemon-sanidad'

export function useSanidadMonitoreo(filters: SanidadFilters = {}) {
  const params = buildFilterQueryString(filters, '90D')

  const { data, error, isLoading, mutate } = useSWR<SanidadData>(
    `/sanidad/monitoreo${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 5000, dedupingInterval: 4000, revalidateOnFocus: false }
  )

  return { data, error, isLoading, mutate }
}
