import type { LemonAlert, LemonFilters, LemonInsight, LemonModuleMeta } from '@/types/lemon-common'

export interface RiegoSummary {
  m3_aplicados: number
  m3_aplicados_delta_pct: number
  m3_aplicados_detail: string
  cumplimiento_hidrico_pct: number
  cumplimiento_delta_pct: number
  cumplimiento_detail: string
  lluvia_reciente_mm: number
  lluvia_delta_pct: number
  lluvia_detail: string
  productividad_agua_kg_m3: number
  productividad_delta_pct: number
  productividad_detail: string
  lotes_fuera_rango: number
  balance_total_m3: number
}

export interface RiegoSerieRow {
  fecha: string
  m3_riego: number
  m3_requeridos: number
  balance_hidrico_m3: number
  lluvia_mm: number
  et0_mm: number
}

export interface RiegoLoteRow {
  lote_campania_id: number
  lote: string
  codigo_lote: string
  campo: string
  establecimiento: string
  variedad: string
  superficie_ha: number
  m3_aplicados: number
  m3_ha: number
  m3_requeridos: number
  balance_hidrico_m3: number
  productividad_kg_m3: number
  fert_eventos: number
}

export interface RiegoDeviationRow {
  lote: string
  establecimiento: string
  m3_aplicados: number
  m3_requeridos: number
  desvio_pct: number
}

export interface RiegoProjectionRow {
  fecha: string
  balance_hidrico_m3: number
  tipo: 'historico' | 'proyeccion' | string
}

export interface RiegoSensitivityRow {
  escenario: string
  impacto_balance_m3: number
}

export interface RiegoData {
  meta: LemonModuleMeta
  summary: RiegoSummary
  series: {
    agua_semanal: RiegoSerieRow[]
  }
  breakdown: {
    m3_lote: RiegoLoteRow[]
    productividad_lote: RiegoLoteRow[]
    ranking_desvio: RiegoLoteRow[]
    fertirriego: RiegoLoteRow[]
  }
  analysis: {
    proyeccion_balance: RiegoProjectionRow[]
    desvio_vs_requerimiento: RiegoDeviationRow[]
    sensibilidad: RiegoSensitivityRow[]
    insights: LemonInsight[]
  }
  alerts: LemonAlert[]
}

export type RiegoFilters = LemonFilters
export type RiegoAlert = LemonAlert
