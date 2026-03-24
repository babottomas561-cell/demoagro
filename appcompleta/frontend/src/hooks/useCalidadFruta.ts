import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import { buildFilterQueryString } from '@/lib/filter-query'
import type { CalidadData, CalidadFilters } from '@/types/lemon-calidad'

export function useCalidadFruta(filters: CalidadFilters = {}) {
  const params = buildFilterQueryString(filters, '30D')

  const { data, error, isLoading, mutate } = useSWR<CalidadData>(
    `/calidad/fruta${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 3000, dedupingInterval: 2000, revalidateOnFocus: false }
  )

  return { data, error, isLoading, mutate }
}
