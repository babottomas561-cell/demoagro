export interface ProduccionMeta {
  campania: string
  campania_id: number
  campania_comparada: string | null
  scope_lotes: number
  scope_superficie_ha: number
  source: string
  last_updated: string
}

export interface ProduccionSummary {
  kg_cosechados: number
  kg_cosechados_delta_pct: number
  kg_cosechados_detail: string
  avance_cosecha_pct: number
  avance_cosecha_delta_pct: number
  avance_cosecha_detail: string
  rendimiento_proyectado_kg_ha: number
  rendimiento_proyectado_delta_pct: number
  rendimiento_proyectado_detail: string
  packout_promedio_pct: number
  packout_objetivo_pct: number
  packout_promedio_delta_pct: number
  packout_promedio_detail: string
  lotes_bajo_objetivo: number
  lotes_bajo_objetivo_delta_pct: number
  lotes_bajo_objetivo_detail: string
  lotes_atrasados: number
  lotes_riesgo_hidrico: number
  plan_kg: number
  kg_jornalero: number
  kg_jornalero_delta_pct: number
  kg_jornalero_detail: string
  costo_kg_ars: number
  costo_kg_ars_delta_pct: number
  costo_kg_ars_detail: string
}

export interface ProduccionSerieRow {
  fecha: string
  kg_cosechados: number
  kg_acumulados: number
  kg_plan_acumulado: number
  desvio_acumulado_kg: number
}

export interface ProduccionLoteRow {
  lote_campania_id: number
  lote: string
  codigo_lote: string
  campo: string
  establecimiento: string
  variedad: string
  superficie_ha: number
  kg_cosechados: number
  kg_cosechados_tn: number
  kg_ha_actual: number
  kg_ha_proyectado: number
  objetivo_kg_ha: number
  desvio_pct: number
  packout_pct: number
  impacto_margen_ars: number
}

export interface ProduccionVariedadEstRow {
  establecimiento: string
  variedad: string
  kg_cosechados_tn: number
  kg_plan_tn: number
}

export interface ProduccionProjectionRow {
  fecha: string
  kg_acumulados: number
  tipo: 'historico' | 'proyeccion' | string
}

export interface ProduccionDeviationRow {
  lote: string
  establecimiento: string
  kg_ha_proyectado: number
  objetivo_kg_ha: number
  desvio_pct: number
}

export interface ProduccionSensitivityRow {
  escenario: string
  impacto_margen_ars: number
}

export interface ProduccionInsight {
  titulo: string
  descripcion: string
  severity: string
}

export interface ProduccionAlert {
  id: string
  prioridad: string
  severidad: string
  titulo: string
  impacto: string
  modulo: string
  detalle: string
  accion: string
}

export interface ProduccionData {
  meta: ProduccionMeta
  summary: ProduccionSummary
  series: {
    cosecha_diaria: ProduccionSerieRow[]
  }
  breakdown: {
    rendimiento_lotes: ProduccionLoteRow[]
    produccion_variedad_establecimiento: ProduccionVariedadEstRow[]
    ranking_bajo_rendimiento: ProduccionLoteRow[]
    heatmap_rendimiento: ProduccionLoteRow[]
  }
  analysis: {
    proyeccion_cosecha: ProduccionProjectionRow[]
    desvio_vs_objetivo: ProduccionDeviationRow[]
    sensibilidad: ProduccionSensitivityRow[]
    insights: ProduccionInsight[]
  }
  alerts: ProduccionAlert[]
}

export type ProduccionFilters = Record<string, string>
