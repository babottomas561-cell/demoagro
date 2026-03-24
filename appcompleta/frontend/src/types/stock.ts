export interface StockFilters {
  empresa_id?: string
  establecimiento_id?: string
  cultivo_id?: string
}

export interface StockSummary {
  stock_total_tn: number
  valor_stock: number
  unidades_alerta: number
  productos_criticos: number
  cobertura_promedio_dias: number
  costo_inventario_insumos: number
  necesidad_compra: number
  stock_inmovilizado: number
}

export interface StockItem {
  id: string
  cultivo: string
  establecimiento: string
  stock_disponible_tn: number
  vendido_tn: number
  comprometido_tn: number
  libre_tn: number
  libre_pct: number
  precio_referencia: number
  valor_estimado: number
  alerta: 'verde' | 'amarillo' | 'rojo'
}

export interface InsumoCoverageItem {
  insumo: string
  tipo: string
  unidad: string
  establecimiento: string
  stock_actual: number
  cobertura_dias: number
  cobertura_ha: number
  quiebre_en_dias: number | null
  compra_sugerida: number
  stock_inmovilizado: number
  costo_inventario: number
  consumo_plan_mes: number
  consumo_real_mes: number
  desvio_consumo_pct: number
  severidad: 'critical' | 'warning' | 'ok'
}

export interface ConsumoVsPlanItem {
  insumo: string
  consumo_plan_mes: number
  consumo_real_mes: number
  compra_sugerida: number
  desvio_pct: number
}

export interface StockAlert {
  id: string
  cultivo: string
  establecimiento: string
  mensaje: string
  severidad: 'warning' | 'critical' | 'info' | 'success'
}

export interface StockAction {
  titulo: string
  descripcion: string
  owner: string
  impacto: string
  severity: 'warning' | 'critical'
}

export interface StockData {
  summary: StockSummary
  items: StockItem[]
  insumos: InsumoCoverageItem[]
  consumo_vs_plan: ConsumoVsPlanItem[]
  alerts: StockAlert[]
  actions: StockAction[]
  ultima_actualizacion: string
}
