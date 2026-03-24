import type { LemonAlert, LemonFilters, LemonInsight, LemonModuleMeta } from '@/types/lemon-common'

export interface PackhouseSummary {
  tn_procesadas: number
  tn_procesadas_delta_pct: number
  tn_procesadas_detail: string
  eficiencia_promedio_pct: number
  eficiencia_delta_pct: number
  eficiencia_detail: string
  downtime_pct: number
  downtime_delta_pct: number
  downtime_detail: string
  costo_tn_ars: number
  costo_tn_delta_pct: number
  costo_tn_detail: string
  lineas_criticas: number
  paradas_criticas: number
}

export interface PackhouseSerieRow {
  fecha: string
  kg_procesados_tn: number
  eficiencia_pct: number
  downtime_pct: number
  costo_ars_tn: number
}

export interface PackhouseLineaRow {
  linea: string
  kg_procesados_tn: number
  eficiencia_pct: number
  horas_productivas: number
  horas_downtime: number
  tn_hora: number
  capacidad_tn_hora: number
  downtime_pct: number
}

export interface PackhouseCostRow {
  rubro: string
  costo_ars: number
  participacion_pct: number
}

export interface PackhouseDowntimeRow {
  motivo: string
  minutos: number
}

export interface PackhouseRankingRow {
  linea: string
  turno: string
  kg_procesados_tn: number
  eficiencia_pct: number
  downtime_pct: number
}

export interface PackhouseDeviationRow {
  linea: string
  tn_hora: number
  capacidad_tn_hora: number
  desvio_pct: number
}

export interface PackhouseProjectionRow {
  fecha: string
  kg_procesados_tn: number
  tipo: 'historico' | 'proyeccion' | string
}

export interface PackhouseSensitivityRow {
  escenario: string
  impacto_costo_tn_ars: number
}

export interface PackhouseData {
  meta: LemonModuleMeta
  summary: PackhouseSummary
  series: {
    procesamiento_diario: PackhouseSerieRow[]
  }
  breakdown: {
    performance_linea: PackhouseLineaRow[]
    costos_rubro: PackhouseCostRow[]
    downtime_motivos: PackhouseDowntimeRow[]
    ranking_lineas: PackhouseRankingRow[]
  }
  analysis: {
    proyeccion_proceso: PackhouseProjectionRow[]
    desvio_vs_capacidad: PackhouseDeviationRow[]
    sensibilidad: PackhouseSensitivityRow[]
    insights: LemonInsight[]
  }
  alerts: LemonAlert[]
}

export type PackhouseFilters = LemonFilters
export type PackhouseAlert = LemonAlert
