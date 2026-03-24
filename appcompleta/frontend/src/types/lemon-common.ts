export interface LemonModuleMeta {
  campania: string
  campania_id: number
  campania_comparada: string | null
  source: string
  last_updated: string
  scope_lotes?: number
  scope_superficie_ha?: number
  scope_lineas?: number
  scope_share_pct?: number
}

export interface LemonInsight {
  titulo: string
  descripcion: string
  severity: string
}

export interface LemonAlert {
  id: string
  prioridad: string
  severidad: string
  titulo: string
  impacto: string
  modulo: string
  detalle: string
  accion: string
}

export type LemonFilters = Record<string, string>
