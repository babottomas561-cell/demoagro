export interface MaquinariaFilters {
  empresa_id?: string
  establecimiento_id?: string
}

export interface MaquinariaSummary {
  equipos_operativos: number
  horas_promedio: number
  costo_operativo: number
  proximos_services: number
  utilizacion_promedio_pct: number
  downtime_horas: number
  combustible_promedio_ha: number
  equipos_cuello_botella: number
  impacto_operativo_ha: number
}

export interface Maquina {
  id: string
  nombre: string
  tipo: string
  marca: string
  modelo: string
  anio: number
  estado: 'operativo' | 'en_reparacion' | 'fuera_de_servicio'
  horas_totales: number
  horas_ultimo_service: number
  proximo_service_horas: number | null
  dias_para_service: number | null
  costo_operativo_mes: number
  alerta_service: 'verde' | 'amarillo' | 'rojo'
  establecimiento: string
  horas_productivas: number
  horas_improductivas: number
  utilizacion_pct: number
  combustible_ha: number
  costo_por_hora: number
  impacto_operativo_ha: number
  service_proximo?: string | null
  riesgo_si_falla?: string | null
  es_cuello_botella: boolean
}

export interface BottleneckMachine {
  maquina: string
  tipo: string
  establecimiento: string
  utilizacion_pct: number
  downtime_horas: number
  combustible_ha: number
  costo_por_hora: number
  impacto_operativo_ha: number
  riesgo_si_falla: string
  severity: 'warning' | 'critical'
}

export interface ServiceScheduleItem {
  maquina: string
  tipo: string
  fecha_programada: string
  dias_restantes: number
  tipo_service: string
  criticidad_operativa: string
  riesgo_si_falla: string
}

export interface MaquinariaAlert {
  id: string
  nombre: string
  mensaje: string
  severidad: 'warning' | 'critical' | 'info' | 'success'
}

export interface MaquinariaAction {
  titulo: string
  descripcion: string
  owner: string
  impacto: string
  severity: 'warning' | 'critical'
}

export interface MaquinariaSerie {
  mes: string
  horas_productivas: number
  downtime_horas: number
  combustible_litros: number
  disponibilidad_pct: number
}

export interface MaquinariaData {
  summary: MaquinariaSummary
  maquinas: Maquina[]
  series: MaquinariaSerie[]
  bottlenecks: BottleneckMachine[]
  service_schedule: ServiceScheduleItem[]
  alerts: MaquinariaAlert[]
  actions: MaquinariaAction[]
  ultima_actualizacion: string
}
