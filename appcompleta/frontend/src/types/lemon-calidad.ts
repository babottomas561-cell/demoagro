import type { LemonAlert, LemonFilters, LemonInsight, LemonModuleMeta } from '@/types/lemon-common'

export interface CalidadSummary {
  packout_hoy_pct: number
  rechazo_hoy_pct: number
  industria_hoy_pct: number
  descarte_hoy_pct: number
  packout_promedio_pct: number
  packout_promedio_delta_pct: number
  packout_promedio_status: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  packout_promedio_detail: string
  rechazo_pct: number
  rechazo_delta_pct: number
  rechazo_detail: string
  exportacion_share_pct: number
  exportacion_delta_pct: number
  exportacion_detail: string
  industria_share_pct: number
  descarte_share_pct: number
  lotes_criticos: number
  lotes_criticos_delta_pct: number
  packout_objetivo_pct: number
}

export interface CalidadSerieRow {
  fecha: string
  kg_recibidos: number
  kg_comerciales: number
  packout_pct: number
  rechazo_pct: number
  industria_pct?: number
  descarte_pct?: number
}

export interface CalidadLoteRow {
  lote_campania_id: number
  lote: string
  codigo_lote: string
  campo: string
  establecimiento: string
  variedad: string
  superficie_ha: number
  kg_recibidos: number
  kg_comerciales: number
  packout_pct: number
  rechazo_pct: number
  objetivo_packout_pct: number
  kg_exportacion: number
  kg_industria: number
  kg_descarte: number
  principal_defecto: string
  principal_defecto_kg: number
}

export interface CalidadDestinoRow {
  destino: string
  kg: number
  participacion_pct: number
}

export interface CalidadDefectoRow {
  defecto: string
  categoria: string
  kg_rechazo: number
  participacion_pct: number
}

export interface CalidadDeviationRow {
  lote: string
  establecimiento: string
  packout_pct: number
  objetivo_packout_pct: number
  desvio_pct: number
}

export interface CalidadProjectionRow {
  fecha: string
  packout_pct: number
  tipo: 'historico' | 'proyeccion' | string
}

export interface CalidadSensitivityRow {
  escenario: string
  impacto_tn_utiles?: number
  impacto_tn_exportables?: number
}

export interface CalidadData {
  meta: LemonModuleMeta
  summary: CalidadSummary
  series: {
    calidad_diaria: CalidadSerieRow[]
  }
  breakdown: {
    packout_lotes: CalidadLoteRow[]
    destino_fruta: CalidadDestinoRow[]
    defectos_tipo: CalidadDefectoRow[]
    ranking_rechazo: CalidadLoteRow[]
  }
  analysis: {
    proyeccion_packout: CalidadProjectionRow[]
    desvio_vs_objetivo: CalidadDeviationRow[]
    sensibilidad: CalidadSensitivityRow[]
    insights: LemonInsight[]
  }
  alerts: LemonAlert[]
}

export type CalidadFilters = LemonFilters
export type CalidadAlert = LemonAlert
