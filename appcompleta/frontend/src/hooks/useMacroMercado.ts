import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import { buildFilterQueryString } from '@/lib/filter-query'
import type { MacroData, MacroFilters } from '@/types/lemon-macro'

export function useMacroMercado(filters: MacroFilters = {}) {
  const params = buildFilterQueryString(filters, '90D')

  const { data, error, isLoading, mutate } = useSWR<MacroData>(
    `/macro/mercado${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 15000, dedupingInterval: 10000, revalidateOnFocus: false }
  )

  return { data, error, isLoading, mutate }
}
