import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import { buildFilterQueryString } from '@/lib/filter-query'
import type { ComercialData, ComercialFilters } from '@/types/lemon-comercial'

export function useComercialExportacion(filters: ComercialFilters = {}) {
  const params = buildFilterQueryString(filters, '30D')

  const { data, error, isLoading, mutate } = useSWR<ComercialData>(
    `/comercial/exportacion${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 3000, dedupingInterval: 2000, revalidateOnFocus: false }
  )

  return { data, error, isLoading, mutate }
}
