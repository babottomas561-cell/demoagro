export interface MacroAlert {
  id?: string
  titulo: string
  descripcion: string
  severidad: 'info' | 'warning' | 'critical' | 'success'
  recommendation?: string
  impacto?: string
}

export interface MacroRecommendation {
  titulo: string
  descripcion: string
  owner: string
  impacto: string
  due?: string
  severity: 'warning' | 'critical' | 'success'
}

export interface MacroSummary {
  tipo_cambio_oficial: number
  tipo_cambio_mayorista: number
  spread_cambiario_pct: number
  tc_oficial_var_7d_pct: number
  tc_oficial_var_30d_pct: number
  tc_mayorista_var_7d_pct: number
  tc_mayorista_var_30d_pct: number
  tc_oficial_min_30d: number
  tc_oficial_max_30d: number
  tc_mayorista_min_30d: number
  tc_mayorista_max_30d: number
  inflacion_mensual: number
  inflacion_interanual: number
  inflacion_promedio_3m: number
  inflacion_delta_vs_3m: number
  tasa_politica_monetaria: number
  tasa_real_pct: number
  costo_financiero_90d_pct: number
  actividad_proxi_var_pct: number
  reservas_internacionales: number
  recommendation: string
  recommendation_tag: 'favorable' | 'neutral' | 'riesgo' | string
  recommendation_severity: 'info' | 'warning' | 'critical' | 'success'
}

export interface MacroFxPoint {
  fecha: string
  tipo_cambio_oficial: number | null
  tipo_cambio_mayorista: number | null
  spread_cambiario_pct: number | null
}

export interface MacroInflationPoint {
  fecha: string
  inflacion_mensual: number
}

export interface MacroRatePoint {
  fecha: string
  valor: number
}

export interface MacroActivityPoint {
  fecha: string
  ventas_supermercados: number
}

export interface MacroCapitalImpactRow {
  escenario: string
  capital_trabajo_ars: number
  costo_financiero_90d_ars: number
  costo_financiero_90d_pct: number
}

export interface MacroData {
  summary: MacroSummary
  series: {
    fx: MacroFxPoint[]
    inflacion: MacroInflationPoint[]
    tasa: MacroRatePoint[]
    actividad: MacroActivityPoint[]
    impacto_capital_trabajo: MacroCapitalImpactRow[]
  }
  alerts: MacroAlert[]
  recommendations: MacroRecommendation[]
  insights: MacroInsight[]
  tipo_cambio_oficial: number
  tipo_cambio_mayorista: number
  tipo_cambio_historico: { fecha: string; valor: number }[]
  inflacion_mensual: number
  inflacion_interanual: number
  tasa_politica_monetaria: number
  reservas_internacionales: number
  fuente: string
  ultima_actualizacion: string
}

export interface CommodityPrice {
  nombre: string
  simbolo: string
  precio_usd_tn: number
  variacion_7d_pct: number
  variacion_30d_pct: number
  variacion_semanal: number
  variacion_pct: number
  precio_min_reciente_usd_tn: number
  precio_max_reciente_usd_tn: number
  costo_estimado_usd_tn: number
  breakeven_usd_tn: number
  margen_usd_tn: number
  margen_pct: number
  recomendacion: 'favorable venta' | 'neutral' | 'riesgo' | string
  severidad: 'success' | 'warning' | 'critical' | 'info'
  accion_sugerida: string
  historico_fallback: boolean
  toneladas_producidas: number
  toneladas_vendidas: number
  toneladas_sin_precio: number
  sin_cobertura_pct: number
  riesgo_caida_5pct_usd: number
}

export interface CommodityHistorico {
  fecha: string
  soja: number | null
  maiz: number | null
  trigo: number | null
  girasol: number | null
}

export interface CommoditySeriesPoint {
  fecha: string
  precio_usd_tn: number
  break_even_usd_tn: number
  margen_usd_tn: number
  rentable?: boolean
  source: 'real' | 'fallback' | 'ref'
}

export interface CommodityComparisonRow {
  cultivo: string
  simbolo: string
  precio_usd_tn: number
  costo_estimado_usd_tn: number
  margen_usd_tn: number
  margen_pct: number
  recomendacion: string
  severidad: 'success' | 'warning' | 'critical' | 'info'
  ranking: number
}

export interface CommodityExposureRow {
  cultivo: string
  simbolo: string
  toneladas_producidas: number
  toneladas_vendidas: number
  toneladas_sin_precio: number
  sin_cobertura_pct: number
  riesgo_caida_5pct_usd: number
  recomendacion: string
  severidad: 'success' | 'warning' | 'critical' | 'info'
}

export interface CommoditiesSummary {
  mejor_margen_cultivo: string | null
  mejor_margen_pct: number
  mejor_margen_usd_tn: number
  sin_cobertura_pct_total: number
  toneladas_sin_precio_total: number
  cultivo_mayor_riesgo: string | null
}

export interface CommoditiesData {
  precios: CommodityPrice[]
  historico_30d: CommodityHistorico[]
  series_by_crop: Record<string, CommoditySeriesPoint[]>
  comparador: CommodityComparisonRow[]
  exposicion_comercial: CommodityExposureRow[]
  insights: MacroInsight[]
  summary: CommoditiesSummary
  historico_nota?: string | null
  historico_cultivos_fallback?: string[]
  fuente: string
  ultima_actualizacion: string
}

export interface ClimaEstablecimiento {
  nombre: string
  provincia?: string
  temperatura: number | null
  sensacion_termica: number | null
  humedad: number | null
  precipitacion_mm: number | null
  condicion: string
  condicion_codigo: number
  viento_kmh: number | null
  alertas: string[]
  lluvia_30d_mm?: number
  lluvia_7d_forecast_mm?: number
  riesgo_operativo?: string
  riesgo_operativo_detalle?: string
  ventana_operativa?: string
  status?: string
}

export interface PronosticoDia {
  fecha: string
  temp_max: number
  temp_min: number
  temp_media?: number
  precipitacion_mm: number
  precipitacion_acumulada_mm?: number
  humedad_promedio?: number
  condicion: string
  condicion_codigo: number
  viento_kmh?: number
  ventana_operativa?: string
  ventana_severidad?: 'info' | 'warning' | 'critical' | 'success' | string
  riesgo_operativo?: string
  riesgo_detalle?: string
}

export interface ClimaHistoricoDia {
  fecha: string
  precipitacion_mm: number
  temp_max: number
  temp_min: number
  temp_media: number
}

export interface ClimaSummary {
  lluvia_72h_mm: number
  lluvia_7d_mm: number
  lluvia_30d_mm: number
  lluvia_normal_7d_mm: number
  anomalia_lluvia_7d_pct: number
  humedad_promedio_pct: number
  temperatura_promedio_7d_c: number
  ventana_operativa: string
  ventana_detalle: string
  riesgo_operativo: string
  riesgo_operativo_detalle: string
  establecimientos_con_alerta: number
  establecimiento_referencia: string
  recommendation: string
  recommendation_severity: 'info' | 'warning' | 'critical' | 'success'
}

export interface ClimaAlert {
  tipo: string
  mensaje: string
  severidad: 'info' | 'warning' | 'critical'
}

export interface ClimaData {
  summary: ClimaSummary
  series: {
    forecast_daily: PronosticoDia[]
    historico_30d: ClimaHistoricoDia[]
    establecimientos: ClimaEstablecimiento[]
  }
  alerts: ClimaAlert[]
  recommendations: MacroRecommendation[]
  insights: MacroInsight[]
  establecimientos: ClimaEstablecimiento[]
  pronostico_7d: PronosticoDia[]
  historico_30d: ClimaHistoricoDia[]
  alertas_activas: ClimaAlert[]
  selected_establecimiento?: {
    nombre: string
    provincia?: string
  }
  fuente: string
  ultima_actualizacion: string
}

export interface MacroInsight {
  id: string
  titulo: string
  descripcion: string
  severidad: 'info' | 'warning' | 'critical' | 'success'
  tab: 'macro' | 'commodities' | 'clima'
  timestamp: string
}
