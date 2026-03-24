import type { LemonAlert, LemonFilters, LemonInsight, LemonModuleMeta } from '@/types/lemon-common'

export interface SanidadSummary {
  incidencia_promedio_pct: number
  incidencia_delta_pct: number
  incidencia_detail: string
  lotes_alerta: number
  lotes_alerta_delta_pct: number
  lotes_alerta_detail: string
  tratamientos_30d: number
  tratamientos_delta_pct: number
  tratamientos_detail: string
  lotes_riesgo_alto: number
  eventos_totales: number
  lotes_sin_tratamiento: number
  dias_sin_cobre: number
  dias_sin_cobre_detail: string
  diaphorina_capturas: number
  diaphorina_capturas_detail: string
}

export interface SanidadSerieRow {
  fecha: string
  eventos: number
  incidencia_promedio_pct: number
  alertas: number
  tratamientos: number
}

export interface SanidadLoteRow {
  lote_campania_id: number
  lote: string
  codigo_lote: string
  campo: string
  establecimiento: string
  variedad: string
  eventos: number
  incidencia_promedio_pct: number
  alertas: number
  tratamientos: number
}

export interface SanidadTipoRow {
  tipo: string
  categoria: string
  eventos: number
  incidencia_promedio_pct: number
}

export interface SanidadTratamientoRow {
  objetivo: string
  producto: string
  aplicaciones: number
  costo_promedio_ars_ha: number
}

export interface SanidadDeviationRow {
  lote: string
  establecimiento: string
  incidencia_promedio_pct: number
  umbral_pct: number
  desvio_pct: number
}

export interface SanidadProjectionRow {
  fecha: string
  incidencia_promedio_pct: number
  tipo: 'historico' | 'proyeccion' | string
}

export interface SanidadSensitivityRow {
  escenario: string
  impacto_riesgo_pct: number
}

export interface SanidadData {
  meta: LemonModuleMeta
  summary: SanidadSummary
  series: {
    sanidad_semanal: SanidadSerieRow[]
  }
  breakdown: {
    lotes_criticos: SanidadLoteRow[]
    incidencias_tipo: SanidadTipoRow[]
    tratamientos: SanidadTratamientoRow[]
    ranking_lotes: SanidadLoteRow[]
  }
  analysis: {
    proyeccion_incidencia: SanidadProjectionRow[]
    desvio_vs_umbral: SanidadDeviationRow[]
    sensibilidad: SanidadSensitivityRow[]
    insights: LemonInsight[]
  }
  alerts: LemonAlert[]
}

export type SanidadFilters = LemonFilters
export type SanidadAlert = LemonAlert
