import type { LemonAlert, LemonFilters, LemonInsight, LemonModuleMeta } from '@/types/lemon-common'

export interface MacroSummary {
  tc_exportacion: number
  tc_delta_pct: number
  tc_detail: string
  inflacion_mensual_pct: number
  inflacion_delta_pct: number
  inflacion_detail: string
  precio_exportacion_usd_tn: number
  precio_exportacion_delta_pct: number
  precio_exportacion_detail: string
  costo_flete_usd_tn: number
  costo_flete_delta_pct: number
  costo_flete_detail: string
  precio_jugo_usd_tn: number
  precio_jugo_delta_pct: number
  precio_jugo_detail: string
  presion_macro_pct: number
  costo_energia_ars_kwh: number
}

export interface MacroSerieRow {
  fecha: string
  tc_exportacion: number
  precio_exportacion_usd_tn: number
  flete_usd_tn: number
}

export interface MacroMercadoRow {
  mercado: string
  precio_exportacion_usd_tn: number
  flete_usd_tn: number
  margen_bruto_usd_tn: number
}

export interface MacroCostRow {
  rubro: string
  valor: number
}

export interface MacroVariableRow {
  variable: string
  valor: number
}

export interface MacroDeviationRow {
  mercado: string
  precio_exportacion_usd_tn: number
  promedio_referencia_usd_tn: number
  desvio_pct: number
}

export interface MacroProjectionRow {
  fecha: string
  precio_exportacion_usd_tn: number
  tipo: 'historico' | 'proyeccion' | string
}

export interface MacroSensitivityRow {
  escenario: string
  impacto_margen_pct: number
}

export interface MacroData {
  meta: LemonModuleMeta
  summary: MacroSummary
  series: {
    macro_semanal: MacroSerieRow[]
  }
  breakdown: {
    mercados: MacroMercadoRow[]
    costos_externos: MacroCostRow[]
    variables: MacroVariableRow[]
    ranking_mercados: MacroMercadoRow[]
  }
  analysis: {
    proyeccion_precio_exportacion: MacroProjectionRow[]
    desvio_vs_promedio: MacroDeviationRow[]
    sensibilidad: MacroSensitivityRow[]
    insights: LemonInsight[]
  }
  alerts: LemonAlert[]
}

export type MacroFilters = LemonFilters
export type MacroAlert = LemonAlert
