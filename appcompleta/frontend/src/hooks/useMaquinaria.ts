import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { MaquinariaData, MaquinariaFilters } from '@/types/maquinaria'

const MOCK_MAQUINARIA: MaquinariaData = {
  summary: {
    equipos_operativos: 14,
    horas_promedio: 312,
    costo_operativo: 48_500_000,
    proximos_services: 3,
    utilizacion_promedio_pct: 72.4,
    downtime_horas: 42.5,
    combustible_promedio_ha: 12.8,
    equipos_cuello_botella: 2,
    impacto_operativo_ha: 480,
  },
  maquinas: [
    { id: 'M01', nombre: 'Cosechadora JD S760 #1', tipo: 'Cosechadora', marca: 'John Deere', modelo: 'S760', anio: 2020, estado: 'operativo', horas_totales: 3_420, horas_ultimo_service: 2_980, proximo_service_horas: 3_500, dias_para_service: 8, costo_operativo_mes: 8_200_000, alerta_service: 'rojo', establecimiento: 'La Primavera', horas_productivas: 280, horas_improductivas: 18, utilizacion_pct: 93.9, combustible_ha: 14.2, costo_por_hora: 29_286, impacto_operativo_ha: 240, service_proximo: '2025-03-28', riesgo_si_falla: 'Detención total de cosecha en La Primavera', es_cuello_botella: true },
    { id: 'M02', nombre: 'Cosechadora Case CR9080', tipo: 'Cosechadora', marca: 'Case', modelo: 'CR9080', anio: 2019, estado: 'operativo', horas_totales: 3_180, horas_ultimo_service: 2_820, proximo_service_horas: 3_250, dias_para_service: 12, costo_operativo_mes: 7_800_000, alerta_service: 'rojo', establecimiento: 'El Ceibo', horas_productivas: 265, horas_improductivas: 14, utilizacion_pct: 95.0, combustible_ha: 13.8, costo_por_hora: 29_434, impacto_operativo_ha: 240, service_proximo: '2025-04-01', riesgo_si_falla: 'Detención de cosecha en El Ceibo', es_cuello_botella: true },
    { id: 'M03', nombre: 'Tractor NH TM190 #1', tipo: 'Tractor', marca: 'New Holland', modelo: 'TM190', anio: 2021, estado: 'operativo', horas_totales: 1_850, horas_ultimo_service: 1_780, proximo_service_horas: 2_000, dias_para_service: 45, costo_operativo_mes: 3_200_000, alerta_service: 'amarillo', establecimiento: 'La Primavera', horas_productivas: 195, horas_improductivas: 5, utilizacion_pct: 97.5, combustible_ha: 12.0, costo_por_hora: 16_410, impacto_operativo_ha: 80, service_proximo: '2025-05-04', riesgo_si_falla: 'Demora en labores de preparación', es_cuello_botella: false },
    { id: 'M04', nombre: 'Tractor JD 6130J', tipo: 'Tractor', marca: 'John Deere', modelo: '6130J', anio: 2022, estado: 'operativo', horas_totales: 1_240, horas_ultimo_service: 1_200, proximo_service_horas: 1_500, dias_para_service: 80, costo_operativo_mes: 2_800_000, alerta_service: 'verde', establecimiento: 'El Ceibo', horas_productivas: 168, horas_improductivas: 4, utilizacion_pct: 97.7, combustible_ha: 11.5, costo_por_hora: 16_667, impacto_operativo_ha: 60, service_proximo: null, riesgo_si_falla: null, es_cuello_botella: false },
    { id: 'M05', nombre: 'Pulverizadora Pla 4000', tipo: 'Pulverizadora', marca: 'Pla', modelo: '4000 P', anio: 2021, estado: 'en_reparacion', horas_totales: 2_100, horas_ultimo_service: 1_980, proximo_service_horas: 2_200, dias_para_service: null, costo_operativo_mes: 1_500_000, alerta_service: 'amarillo', establecimiento: 'Santa Rosa', horas_productivas: 0, horas_improductivas: 85, utilizacion_pct: 0, combustible_ha: 0, costo_por_hora: 0, impacto_operativo_ha: 120, service_proximo: null, riesgo_si_falla: 'Retraso en aplicaciones de fungicida en Santa Rosa', es_cuello_botella: false },
    { id: 'M06', nombre: 'Sembradora Agrometal MXR', tipo: 'Sembradora', marca: 'Agrometal', modelo: 'MXR 16-35', anio: 2020, estado: 'operativo', horas_totales: 980, horas_ultimo_service: 920, proximo_service_horas: 1_200, dias_para_service: 120, costo_operativo_mes: 1_200_000, alerta_service: 'verde', establecimiento: 'Los Alamos', horas_productivas: 142, horas_improductivas: 3, utilizacion_pct: 97.9, combustible_ha: 8.5, costo_por_hora: 8_451, impacto_operativo_ha: 180, service_proximo: null, riesgo_si_falla: null, es_cuello_botella: false },
  ],
  series: [
    { mes: '2023-04-01', horas_productivas: 2_100, downtime_horas: 88, combustible_litros: 28_200, disponibilidad_pct: 96.0 },
    { mes: '2023-05-01', horas_productivas: 2_350, downtime_horas: 102, combustible_litros: 31_800, disponibilidad_pct: 95.8 },
    { mes: '2023-06-01', horas_productivas: 1_950, downtime_horas: 145, combustible_litros: 26_400, disponibilidad_pct: 93.1 },
    { mes: '2023-07-01', horas_productivas: 1_680, downtime_horas: 72, combustible_litros: 22_500, disponibilidad_pct: 95.9 },
    { mes: '2023-08-01', horas_productivas: 1_820, downtime_horas: 85, combustible_litros: 24_600, disponibilidad_pct: 95.5 },
    { mes: '2023-09-01', horas_productivas: 2_480, downtime_horas: 120, combustible_litros: 33_600, disponibilidad_pct: 95.4 },
    { mes: '2023-10-01', horas_productivas: 2_980, downtime_horas: 175, combustible_litros: 40_200, disponibilidad_pct: 94.5 },
    { mes: '2023-11-01', horas_productivas: 3_250, downtime_horas: 220, combustible_litros: 44_000, disponibilidad_pct: 93.7 },
    { mes: '2023-12-01', horas_productivas: 2_800, downtime_horas: 155, combustible_litros: 37_800, disponibilidad_pct: 94.8 },
    { mes: '2024-01-01', horas_productivas: 2_250, downtime_horas: 108, combustible_litros: 30_400, disponibilidad_pct: 95.4 },
    { mes: '2024-02-01', horas_productivas: 2_400, downtime_horas: 130, combustible_litros: 32_400, disponibilidad_pct: 94.9 },
    { mes: '2024-03-01', horas_productivas: 2_550, downtime_horas: 142, combustible_litros: 34_400, disponibilidad_pct: 94.7 },
    { mes: '2024-04-01', horas_productivas: 2_850, downtime_horas: 120, combustible_litros: 38_400, disponibilidad_pct: 95.9 },
    { mes: '2024-05-01', horas_productivas: 3_100, downtime_horas: 145, combustible_litros: 42_800, disponibilidad_pct: 95.5 },
    { mes: '2024-06-01', horas_productivas: 2_600, downtime_horas: 180, combustible_litros: 35_200, disponibilidad_pct: 93.5 },
    { mes: '2024-07-01', horas_productivas: 2_200, downtime_horas: 95, combustible_litros: 29_800, disponibilidad_pct: 95.8 },
    { mes: '2024-08-01', horas_productivas: 2_450, downtime_horas: 110, combustible_litros: 33_200, disponibilidad_pct: 95.7 },
    { mes: '2024-09-01', horas_productivas: 3_200, downtime_horas: 160, combustible_litros: 44_800, disponibilidad_pct: 95.2 },
    { mes: '2024-10-01', horas_productivas: 3_800, downtime_horas: 220, combustible_litros: 52_800, disponibilidad_pct: 94.5 },
    { mes: '2024-11-01', horas_productivas: 4_100, downtime_horas: 280, combustible_litros: 58_400, disponibilidad_pct: 93.6 },
    { mes: '2024-12-01', horas_productivas: 3_600, downtime_horas: 195, combustible_litros: 48_800, disponibilidad_pct: 94.9 },
    { mes: '2025-01-01', horas_productivas: 2_900, downtime_horas: 142, combustible_litros: 39_200, disponibilidad_pct: 95.3 },
    { mes: '2025-02-01', horas_productivas: 3_050, downtime_horas: 168, combustible_litros: 41_600, disponibilidad_pct: 94.8 },
    { mes: '2025-03-01', horas_productivas: 3_280, downtime_horas: 185, combustible_litros: 44_800, disponibilidad_pct: 94.7 },
  ],
  bottlenecks: [
    { maquina: 'Cosechadora JD S760 #1', tipo: 'Cosechadora', establecimiento: 'La Primavera', utilizacion_pct: 93.9, downtime_horas: 18, combustible_ha: 14.2, costo_por_hora: 29_286, impacto_operativo_ha: 240, riesgo_si_falla: 'Detención total de cosecha. La Primavera: 240ha sin cosechar.', severity: 'critical' },
    { maquina: 'Cosechadora Case CR9080', tipo: 'Cosechadora', establecimiento: 'El Ceibo', utilizacion_pct: 95.0, downtime_horas: 14, combustible_ha: 13.8, costo_por_hora: 29_434, impacto_operativo_ha: 240, riesgo_si_falla: 'Detención de cosecha en El Ceibo. 240ha comprometidas.', severity: 'critical' },
    { maquina: 'Pulverizadora Pla 4000', tipo: 'Pulverizadora', establecimiento: 'Santa Rosa', utilizacion_pct: 0, downtime_horas: 85, combustible_ha: 0, costo_por_hora: 0, impacto_operativo_ha: 120, riesgo_si_falla: 'Retraso en aplicaciones críticas en Santa Rosa (fungicida, herbicida).', severity: 'warning' },
  ],
  service_schedule: [
    { maquina: 'Cosechadora JD S760 #1', tipo: 'Cosechadora', fecha_programada: '2025-03-28', dias_restantes: 8, tipo_service: 'Service mayor 3500hs', criticidad_operativa: 'Alta — en plena cosecha de soja', riesgo_si_falla: 'Parada no planificada en ventana de cosecha crítica' },
    { maquina: 'Cosechadora Case CR9080', tipo: 'Cosechadora', fecha_programada: '2025-04-01', dias_restantes: 12, tipo_service: 'Service mayor 3250hs', criticidad_operativa: 'Alta — solapado con cosecha El Ceibo', riesgo_si_falla: 'Retraso de 5-7 días en cosecha de El Ceibo' },
    { maquina: 'Tractor NH TM190 #1', tipo: 'Tractor', fecha_programada: '2025-05-04', dias_restantes: 45, tipo_service: 'Service regular 2000hs', criticidad_operativa: 'Media — preparación suelos post-cosecha', riesgo_si_falla: 'Demora en inicio de campaña trigo 25' },
  ],
  alerts: [
    { id: 'MA01', nombre: 'Cosechadora JD S760 #1', mensaje: 'Supera 3000hs desde último service con service programado en 8 días. Riesgo de parada no planificada en cosecha de soja.', severidad: 'critical' },
    { id: 'MA02', nombre: 'Cosechadora Case CR9080', mensaje: 'Supera 3000hs desde último service. Service en 12 días. Monitorizar consumo de aceite diariamente.', severidad: 'critical' },
    { id: 'MA03', nombre: 'Pulverizadora Pla 4000', mensaje: 'En reparación por falla hidráulica. 85hs de downtime acumulado. ETA retorno: 5 días.', severidad: 'warning' },
  ],
  actions: [
    { titulo: 'Programar service cosechadora JD S760', descripcion: 'Service mayor en 8 días. Reservar repuestos y turno con el concesionario YA.', owner: 'Jefe de Maquinaria', impacto: 'Evitar parada en cosecha de soja (240ha en riesgo)', severity: 'critical' },
    { titulo: 'Atención urgente Pla 4000', descripcion: 'Pulverizadora fuera de servicio 85hs. Evaluar alquiler transitorio.', owner: 'Jefe de Maquinaria', impacto: '120ha de Santa Rosa sin posibilidad de fumigación', severity: 'warning' },
  ],
  ultima_actualizacion: new Date().toISOString(),
}

export function useMaquinaria(filters: MaquinariaFilters = {}) {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][]
  ).toString()

  const { data, error, isLoading, mutate } = useSWR<MaquinariaData>(
    `/maquinaria/resumen${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 300000 }
  )

  return {
    data: data ?? (error ? MOCK_MAQUINARIA : undefined),
    error,
    isLoading,
    mutate,
    isMockData: !data && !!error,
  }
}
