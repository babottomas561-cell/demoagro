export interface DashboardFilters {
  empresa_id?: string
  campania_id?: string
  cultivo_id?: string
}

export interface KPISummary {
  ventas_totales: number
  margen_bruto_pct: number
  rendimiento_promedio: number
  stock_valorizado: number
  ebitda_estimado: number
  flujo_neto_mensual: number
  costos_operativos: number
  variacion_campania_anterior: number
}

export interface DashboardExecutiveSummary {
  margen_bruto_total: number
  margen_por_ha: number
  desvio_presupuesto_pct: number
  hectareas_fuera_ventana: number
  toneladas_sin_fijar: number
  toneladas_producidas: number
  toneladas_fijadas: number
  stock_critico: number
  maquinas_criticas: number
}

export interface IngresoEgreso {
  mes: string
  ingresos: number
  egresos: number
}

export interface VentasCultivo {
  cultivo: string
  valor: number
  volumen: number
}

export interface ExecutiveInsight {
  id: string
  titulo: string
  descripcion: string
  severidad: 'info' | 'warning' | 'critical' | 'success'
  modulo: string
  timestamp: string
}

export interface LotProfitability {
  lote: string
  establecimiento: string
  cultivo: string
  margen_ha: number
  margen_total: number
  desvio_pct: number
  contribucion_pct: number
}

export interface ResultBridgeItem {
  label: string
  value: number
  kind: 'positive' | 'negative' | 'total'
}

export interface ExecutiveSemaphore {
  label: string
  status: 'success' | 'warning' | 'danger'
  detail: string
}

export interface ExecutiveAlert {
  id: string
  titulo: string
  descripcion: string
  severidad: 'info' | 'warning' | 'critical' | 'success'
  modulo: string
  accion?: string
  prioridad?: number
}

export interface ExecutiveAction {
  id?: string
  titulo: string
  descripcion: string
  owner: string
  impacto: string
  due?: string
  severity: 'warning' | 'critical' | 'success'
}

export interface DashboardData {
  kpis: KPISummary
  summary: DashboardExecutiveSummary
  ingresos_egresos: IngresoEgreso[]
  ventas_cultivo: VentasCultivo[]
  insights: ExecutiveInsight[]
  lot_profitability: LotProfitability[]
  top_lotes: LotProfitability[]
  bottom_lotes: LotProfitability[]
  result_bridge: ResultBridgeItem[]
  semaforos: ExecutiveSemaphore[]
  alerts: ExecutiveAlert[]
  actions: ExecutiveAction[]
  ultima_actualizacion: string
}
