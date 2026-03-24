import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { CatalogosFiltros } from '@/types/catalogos'

const FALLBACK_CATALOG: CatalogosFiltros = {
  empresas: [
    {
      id: 1,
      codigo: 'LIMONNOA',
      nombre: 'Lemon Intelligence',
      razon_social: 'Lemon Intelligence SA',
      provincia_base: 'Tucumán',
    },
  ],
  campanias: [
    { id: 4, codigo: '2025_26', nombre: '2025/2026', fecha_inicio: '2025-07-01', fecha_fin: '2026-06-30', estado: 'activa', activa: true },
  ],
  establecimientos: [],
  campos: [],
  lotes: [],
  variedades: [],
  clientes: [],
  mercados: [],
  canales: [],
  lineas: [],
  turnos: [],
  destinos: [],
  calibres: [],
  monedas: [
    { id: 'ARS', codigo: 'ARS', nombre: 'Peso argentino' },
    { id: 'USD', codigo: 'USD', nombre: 'Dólar estadounidense' },
  ],
}

export function useCatalogFilters() {
  const { data, error, isLoading, mutate } = useSWR<CatalogosFiltros>(
    '/catalogos/filtros',
    fetcher,
    { refreshInterval: 300000 }
  )

  return {
    data: data ?? FALLBACK_CATALOG,
    error,
    isLoading,
    mutate,
    isMockData: !data && !!error,
  }
}
