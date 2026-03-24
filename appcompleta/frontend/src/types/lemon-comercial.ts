import type { LemonAlert, LemonFilters, LemonInsight, LemonModuleMeta } from '@/types/lemon-common'

export interface ComercialSummary {
  precio_hoy_usd_tn: number
  precio_hoy_realizado_usd_tn: number
  precio_hoy_referencia_usd_tn: number
  ventas_hoy_tn: number
  cobrado_hoy_ars: number
  precio_promedio_usd_tn: number
  precio_realizado_usd_tn: number
  precio_referencia_usd_tn: number
  precio_delta_pct: number
  precio_detail: string
  volumen_exportado_tn: number
  volumen_delta_pct: number
  volumen_detail: string
  pendiente_entrega_tn: number
  pendiente_delta_pct: number
  pendiente_detail: string
  cobrado_ars: number
  cobranza_abierta_ars: number
  cobranza_delta_pct: number
  cobranza_detail: string
  cumplimiento_contratos_pct: number
  precio_objetivo_usd_tn: number
  precio_contexto_mercado: string
  precio_contexto_canal: string
  precio_contexto_volumen_tn: number
  precio_tipo_hoy: string
  dias_promedio_cobro: number | null
  dias_promedio_cobro_detail: string
}

export interface ComercialSerieRow {
  fecha: string
  precio_promedio_usd_tn: number
  precio_realizado_usd_tn: number
  precio_referencia_usd_tn: number
  volumen_tn: number
  mercado: string
  canal: string
  tipo_precio: string
}

export interface ComercialMercadoRow {
  mercado: string
  toneladas: number
  participacion_pct: number
  precio_promedio_usd_tn: number
  precio_referencia_usd_tn?: number
  revenue_usd: number
}

export interface ComercialCanalRow {
  canal: string
  toneladas: number
  participacion_pct: number
  precio_promedio_usd_tn: number
  precio_referencia_usd_tn: number
}

export interface ComercialContratoRow {
  canal: string
  contratado_tn: number
  entregado_tn: number
  pendiente_tn: number
}

export interface ComercialClienteRow {
  cliente: string
  mercado: string
  toneladas: number
  precio_promedio_usd_tn: number
  revenue_usd: number
}

export interface ComercialCobranzaClienteRow {
  cliente: string
  saldo_abierto_ars: number
  vencido_ars: number
  facturas_abiertas: number
}

export interface ComercialMixRow {
  canal: string
  toneladas: number
  participacion_pct: number
}

export interface ComercialDeviationRow {
  mercado: string
  precio_promedio_usd_tn: number
  precio_objetivo_usd_tn: number
  desvio_pct: number
}

export interface ComercialProjectionRow {
  fecha: string
  precio_promedio_usd_tn: number
  tipo: 'historico' | 'proyeccion' | string
}

export interface ComercialSensitivityRow {
  escenario: string
  impacto_revenue_usd?: number
  impacto_tn?: number
}

export interface ComercialData {
  meta: LemonModuleMeta
  summary: ComercialSummary
  series: {
    precio_diario: ComercialSerieRow[]
    precio_volumen_semanal: ComercialSerieRow[]
  }
  breakdown: {
    mercados: ComercialMercadoRow[]
    canales: ComercialCanalRow[]
    estado_contratos: ComercialContratoRow[]
    ranking_clientes: ComercialClienteRow[]
    clientes_cobranza: ComercialCobranzaClienteRow[]
    mix_canal: ComercialMixRow[]
  }
  analysis: {
    proyeccion_precio: ComercialProjectionRow[]
    desvio_vs_objetivo: ComercialDeviationRow[]
    sensibilidad: ComercialSensitivityRow[]
    insights: LemonInsight[]
  }
  alerts: LemonAlert[]
}

export type ComercialFilters = LemonFilters
export type ComercialAlert = LemonAlert
