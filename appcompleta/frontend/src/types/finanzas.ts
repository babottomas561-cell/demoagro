export interface FinanzasFilters {
  empresa_id?: string
  campania_id?: string
}

export interface FinanzasSummary {
  capital_de_trabajo: number
  deuda_por_vencer: number
  cuentas_a_cobrar: number
  flujo_neto: number
  margen_bruto_total: number
  margen_por_ha: number
  desvio_presupuesto_pct: number
  costo_por_ha: number
  costo_por_tonelada: number
  capital_trabajo_comprometido: number
  deuda_corto_plazo: number
  riesgo_caja: 'bajo' | 'medio' | 'alto'
  ingresos_operativos: number
}

export interface FlujoCajaMes {
  mes: string
  ingresos: number
  egresos: number
  neto: number
  proyectado?: boolean
}

export interface CashProjectionItem extends FlujoCajaMes {
  saldo_acumulado: number
}

export interface CostBreakdownItem {
  label: string
  value: number
  kind: 'positive' | 'negative' | 'total'
}

export interface FlujoCajaCategoria {
  categoria: string
  tipo: 'ingreso' | 'egreso'
  enero: number
  febrero: number
  marzo: number
  abril: number
  mayo: number
  junio: number
  julio: number
  agosto: number
  septiembre: number
  octubre: number
  noviembre: number
  diciembre: number
  total: number
}

export interface ResultadoLote {
  lote: string
  establecimiento: string
  cultivo: string
  hectareas: number
  ingreso_total: number
  costo_total: number
  costo_ha: number
  costo_tonelada: number
  margen_ha: number
  margen_total: number
  desvio_pct: number
  rentabilidad_pct: number
}

export interface RentabilidadCultivo {
  cultivo: string
  ingreso_total: number
  costo_total: number
  margen_total: number
  margen_ha: number
  costo_ha: number
  costo_tonelada: number
  desvio_pct: number
}

export interface RentabilidadEstablecimiento {
  establecimiento: string
  ingreso_total: number
  costo_total: number
  margen_total: number
  margen_ha: number
  costo_tonelada: number
}

export interface SensitivityScenario {
  scenario: string
  margen_total: number
  delta_pct: number
}

export interface FinanzasAlert {
  titulo: string
  descripcion: string
  accion?: string
  severidad: 'warning' | 'critical' | 'info' | 'success'
  prioridad?: number
}

export interface FinanzasAction {
  titulo: string
  descripcion: string
  owner: string
  impacto: string
  severity: 'warning' | 'critical'
}

export interface FinanzasData {
  summary: FinanzasSummary
  flujo_mensual: FlujoCajaMes[]
  flujo_categorias: FlujoCajaCategoria[]
  cash_projection: CashProjectionItem[]
  cost_breakdown: CostBreakdownItem[]
  resultados_lote: ResultadoLote[]
  rentabilidad_cultivo: RentabilidadCultivo[]
  rentabilidad_establecimiento: RentabilidadEstablecimiento[]
  sensitivity: SensitivityScenario[]
  alerts: FinanzasAlert[]
  actions: FinanzasAction[]
  ultima_actualizacion: string
}
