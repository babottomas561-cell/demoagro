import type { QueryFilters } from '@/hooks/usePageFilters'

export interface DrillDownFilterChip {
  label: string
  value: string
}

const FILTER_LABELS: Record<string, string> = {
  empresa_id: 'Empresa',
  campania_id: 'Campana',
  establecimiento_id: 'Establecimiento',
  campo_id: 'Campo',
  lote_id: 'Lote',
  variedad_id: 'Variedad',
  cliente_id: 'Cliente',
  mercado_id: 'Mercado',
  canal_id: 'Canal',
  packhouse_id: 'Packhouse',
  linea_id: 'Linea',
  turno_id: 'Turno',
  destino_id: 'Destino',
  calibre_id: 'Calibre',
  periodo: 'Periodo',
  from_date: 'Desde',
  to_date: 'Hasta',
  vista: 'Vista',
  cultivo_id: 'Cultivo',
}

function humanizeKey(key: string) {
  return key
    .replace(/_id$/, '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

export function buildAppliedFilters(filters: QueryFilters): DrillDownFilterChip[] {
  return Object.entries(filters)
    .filter(([, value]) => Boolean(value))
    .map(([key, value]) => ({
      label: FILTER_LABELS[key] || humanizeKey(key),
      value: String(value),
    }))
}
