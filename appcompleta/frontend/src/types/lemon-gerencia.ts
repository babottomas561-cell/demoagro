export interface GerenciaMeta {
  campania: string
  campania_id: number
  campania_comparada: string | null
  scope_lotes: number
  scope_superficie_ha: number
  source: string
  last_updated: string
}

export interface GerenciaSummary {
  margen_hoy_ars: number
  ventas_hoy_ars: number
  cobranzas_hoy_ars: number
  margen_operativo_ars: number
  margen_operativo_delta_pct: number
  margen_operativo_status: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  margen_operativo_detail: string
  margen_por_ha_ars: number
  margen_por_ha_delta_pct: number
  margen_por_ha_status: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  margen_por_ha_detail: string
  ingresos_acumulados_ars: number
  ingresos_acumulados_delta_pct: number
  ingresos_acumulados_status: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  ingresos_acumulados_detail: string
  desvio_presupuesto_pct: number
  desvio_presupuesto_delta_pct: number
  desvio_presupuesto_status: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  desvio_presupuesto_detail: string
  packout_comercial_pct: number
  packout_comercial_delta_pct: number
  packout_comercial_status: 'success' | 'warning' | 'danger' | 'info' | 'neutral'
  packout_comercial_detail: string
  packout_objetivo_pct: number
  cobranza_abierta_ars: number
  toneladas_pendientes_contrato: number
  stock_disponible_tn: number
  dias_promedio_cobro: number | null
  dias_promedio_cobro_detail: string
  costo_tn_usd: number
  costo_tn_usd_detail: string
}

export interface GerenciaSerieRow {
  fecha: string
  ingresos_ars: number
  costos_ars: number
  margen_ars: number
}

export interface GerenciaEstablecimientoRow {
  establecimiento: string
  ingresos_ars: number
  costos_ars: number
  margen_ars: number
  margen_ha_ars: number
  superficie_ha: number
}

export interface GerenciaCanalRow {
  canal: string
  ingresos_ars: number
  costos_ars: number
  margen_ars: number
  participacion_pct: number
  toneladas: number
}

export interface GerenciaLoteRow {
  lote_campania_id: number
  lote: string
  codigo_lote: string
  campo: string
  establecimiento: string
  variedad: string
  superficie_ha: number
  ingresos_ars: number
  costos_directos_ars: number
  costos_indirectos_ars: number
  margen_ars: number
  margen_ha_ars: number
  desvio_presupuesto_pct: number
  packout_pct: number
  objetivo_packout_pct: number
  objetivo_margen_ha: number
}

export interface GerenciaCostCategoryRow {
  categoria: string
  monto_ars: number
}

export interface GerenciaProjectionRow {
  periodo: string
  margen_ars: number
  tipo: 'historico' | 'proyeccion' | string
}

export interface GerenciaBudgetRow {
  concepto: string
  real_ars: number
  presupuesto_ars: number
  desvio_ars: number
  desvio_pct: number
}

export interface GerenciaSensitivityRow {
  escenario: string
  margen_ars: number
}

export interface GerenciaInsight {
  titulo: string
  descripcion: string
  severity: string
}

export interface GerenciaAlert {
  id: string
  prioridad: string
  severidad: string
  titulo: string
  impacto: string
  modulo: string
  detalle: string
  accion: string
}

export interface GerenciaData {
  meta: GerenciaMeta
  summary: GerenciaSummary
  series: {
    resultado_diario: GerenciaSerieRow[]
  }
  breakdown: {
    margen_establecimiento: GerenciaEstablecimientoRow[]
    ingresos_costos_canal: GerenciaCanalRow[]
    ranking_lotes: GerenciaLoteRow[]
    costos_categoria: GerenciaCostCategoryRow[]
  }
  analysis: {
    proyeccion_margen: GerenciaProjectionRow[]
    presupuesto_vs_real: GerenciaBudgetRow[]
    sensibilidad: GerenciaSensitivityRow[]
    insights: GerenciaInsight[]
  }
  alerts: GerenciaAlert[]
}

export type GerenciaFilters = Record<string, string>
