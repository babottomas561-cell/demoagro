'use client'

import { useMemo } from 'react'
import { useSearchParams } from 'next/navigation'

export const FILTER_KEYS = [
  'empresa_id',
  'campania_id',
  'establecimiento_id',
  'campo_id',
  'lote_id',
  'variedad_id',
  'cultivo_id',
  'periodo',
  'from_date',
  'to_date',
  'vista',
  'cliente_id',
  'mercado_id',
  'canal_id',
  'packhouse_id',
  'linea_id',
  'turno_id',
  'destino_id',
  'calibre_id',
  'moneda',
] as const

export type FilterKey = typeof FILTER_KEYS[number]
export type QueryFilters = Partial<Record<FilterKey, string>>

const CONTEXT_KEYS: readonly FilterKey[] = ['periodo', 'from_date', 'to_date', 'vista']

export function usePageFilters(allowedKeys: readonly FilterKey[]) {
  const searchParams = useSearchParams()
  const effectiveKeys = Array.from(new Set([...allowedKeys, ...CONTEXT_KEYS]))
  const allowedKey = effectiveKeys.join('|')

  return useMemo(() => {
    const filters: QueryFilters = {}
    for (const key of effectiveKeys) {
      const value = searchParams.get(key)
      if (value) {
        filters[key] = value
      }
    }
    return filters
  }, [allowedKey, searchParams])
}
