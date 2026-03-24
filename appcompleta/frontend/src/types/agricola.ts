export interface AgricolaFilters {
  empresa_id?: string
  campania_id?: string
  establecimiento_id?: string
  cultivo_id?: string
}

export interface AgricolaSummary {
  superficie_total: number
  sembrado: number
  cosechado: number
  rendimiento_promedio: number
  variabilidad_rinde_pct: number
  hectareas_fuera_ventana: number
  lotes_atrasados: number
  desvio_aplicacion_promedio: number
}

export interface AvanceCultivo {
  cultivo: string
  sembrado_ha: number
  total_ha: number
  porcentaje: number
}

export interface Lote {
  id: string
  nombre: string
  establecimiento: string
  cultivo: string
  hectareas: number
  estado: 'sembrado' | 'cosechado' | 'en_labores' | 'barbecho'
  fecha_siembra: string | null
  rendimiento_tn_ha: number | null
  costo_por_ha: number | null
}

export interface RendimientoCampania {
  campania: string
  soja: number | null
  maiz: number | null
  trigo: number | null
  girasol: number | null
}

export interface PlanVsActualItem {
  labor: string
  plan_ha: number
  real_ha: number
  pendiente_ha: number
  cumplimiento_pct: number
}

export interface LoteAtrasado {
  lote: string
  establecimiento: string
  cultivo: string
  labor: string
  pendiente_ha: number
  dias_atraso: number
  equipo?: string
}

export interface PendienteEstablecimiento {
  establecimiento: string
  labor: string
  pendiente_ha: number
  plan_ha: number
  pendiente_pct: number
}

export interface ProductividadRecurso {
  recurso: string
  tipo: 'equipo' | 'operador'
  hectareas: number
  horas: number
  ha_hora: number
}

export interface PerformanceLote {
  lote: string
  establecimiento: string
  cultivo: string
  margen_ha: number
  desvio_pct: number
}

export interface RendimientoAmbiente {
  lote: string
  establecimiento: string
  cultivo: string
  ambiente: string
  hectareas: number
  rendimiento_objetivo: number
  rendimiento_real: number
  desvio_pct: number
  margen_ha: number
}

export interface AplicacionDetalle {
  lote: string
  establecimiento: string
  cultivo: string
  producto: string
  ingrediente_activo: string
  dosis_objetivo: number
  dosis_real: number
  unidad: string
  desvio_pct: number
}

export interface NutrienteLote {
  lote: string
  establecimiento: string
  cultivo: string
  producto: string
  ingrediente_activo: string
  dosis_objetivo: number
  dosis_aplicada: number
  desvio_pct: number
}

export interface ObservacionCampo {
  lote: string
  establecimiento: string
  cultivo: string
  categoria: string
  severidad: 'alta' | 'media' | 'baja'
  ambiente: string
  descripcion: string
  accion_sugerida: string
}

export interface RecomendacionAgronomica {
  lote: string
  cultivo: string
  tipo_labor: string
  nutriente?: string | null
  ingrediente_activo?: string | null
  dosis_recomendada?: number | null
  dosis_aplicada?: number | null
  desvio_pct?: number | null
  prioridad: 'alta' | 'media' | 'baja'
  recomendacion: string
}

export interface AgricolaAlert {
  titulo: string
  descripcion: string
  accion?: string
  severidad: 'warning' | 'critical' | 'info' | 'success'
  prioridad?: number
}

export interface AgricolaAction {
  titulo: string
  descripcion: string
  owner: string
  impacto: string
  severity: 'warning' | 'critical'
}

export interface AgricolaData {
  summary: AgricolaSummary
  avance_cultivos: AvanceCultivo[]
  lotes: Lote[]
  rendimiento_historico: RendimientoCampania[]
  plan_vs_actual: PlanVsActualItem[]
  lotes_atrasados: LoteAtrasado[]
  pendientes_establecimiento: PendienteEstablecimiento[]
  productividad: ProductividadRecurso[]
  performance_lotes: PerformanceLote[]
  rendimiento_ambientes: RendimientoAmbiente[]
  aplicaciones: AplicacionDetalle[]
  nutrientes_lote: NutrienteLote[]
  observaciones: ObservacionCampo[]
  recomendaciones: RecomendacionAgronomica[]
  alerts: AgricolaAlert[]
  actions: AgricolaAction[]
  ultima_actualizacion: string
}
