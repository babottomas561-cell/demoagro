import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import { buildFilterQueryString } from '@/lib/filter-query'
import type { GerenciaData, GerenciaFilters } from '@/types/lemon-gerencia'

export function useGerenciaGeneral(filters: GerenciaFilters = {}) {
  const params = buildFilterQueryString(filters, '30D')

  const { data, error, isLoading, mutate } = useSWR<GerenciaData>(
    `/gerencia/general${params ? `?${params}` : ''}`,
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
