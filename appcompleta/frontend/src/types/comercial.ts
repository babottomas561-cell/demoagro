export interface ComercialFilters {
  empresa_id?: string
  campania_id?: string
  cultivo_id?: string
}

export interface ComercialSummary {
  volumen_vendido: number
  precio_promedio: number
  valor_total: number
  contratos_cerrados: number
  toneladas_producidas: number
  toneladas_comprometidas: number
  toneladas_fijadas: number
  toneladas_entregadas: number
  posicion_abierta_tn: number
  cobertura_promedio_pct: number
  desvio_precio_vs_referencia_pct: number
}

export interface PrecioCultivo {
  fecha: string
  soja: number | null
  maiz: number | null
  trigo: number | null
  girasol: number | null
}

export interface VentaCliente {
  cliente: string
  valor: number
  volumen: number
}

export interface OperacionComercial {
  id: string
  fecha: string | null
  cultivo: string
  cliente: string
  volumen_tn: number
  precio_ars_tn: number
  valor_total_ars: number
  estado: 'confirmada' | 'pendiente' | 'entregada' | 'cancelada'
  tipo_contrato: string
}

export interface PosicionComercialItem {
  cultivo: string
  toneladas_producidas: number
  toneladas_comprometidas: number
  toneladas_fijadas: number
  toneladas_entregadas: number
  stock_fisico: number
  abierta_tn: number
  pendiente_entrega_tn: number
  cobertura_pct: number
  compromiso_pct: number
  desvio_stock_cobertura_tn: number
  precio_referencia: number
  recomendacion: 'fijar' | 'cubrir' | 'esperar' | string
  severidad: 'success' | 'warning' | 'critical'
}

export interface EntregaProgramada {
  cultivo: string
  cliente: string
  fecha_programada: string
  fecha_entrega?: string | null
  volumen_tn: number
  pendiente_tn: number
  estado: string
}

export interface ContratoProximo {
  id: number
  cultivo: string
  cliente: string
  volumen_tn: number
  fecha_entrega: string
  dias_para_vencer: number
  estado: string
  precio_fijado: number
}

export interface ComercialAlert {
  titulo: string
  descripcion: string
  accion?: string
  severidad: 'warning' | 'critical' | 'info' | 'success'
  prioridad?: number
}

export interface ComercialAction {
  titulo: string
  descripcion: string
  owner: string
  impacto: string
  severity: 'warning' | 'critical'
}

export interface ComercialData {
  summary: ComercialSummary
  precios_historicos: PrecioCultivo[]
  ventas_cliente: VentaCliente[]
  operaciones: OperacionComercial[]
  posiciones: PosicionComercialItem[]
  entregas: EntregaProgramada[]
  proximos_vencer: ContratoProximo[]
  alerts: ComercialAlert[]
  actions: ComercialAction[]
  ultima_actualizacion: string
}
