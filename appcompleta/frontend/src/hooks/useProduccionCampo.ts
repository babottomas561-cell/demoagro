import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import { buildFilterQueryString } from '@/lib/filter-query'
import type { ProduccionData, ProduccionFilters } from '@/types/lemon-produccion'

export function useProduccionCampo(filters: ProduccionFilters = {}) {
  const params = buildFilterQueryString(filters, '30D')

  const { data, error, isLoading, mutate } = useSWR<ProduccionData>(
    `/produccion/campo${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 3000, dedupingInterval: 2000, revalidateOnFocus: false }
  )

  return {
    data,
    error,
    isLoading,
    mutate,
  }
}
