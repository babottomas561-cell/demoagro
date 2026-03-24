import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { AgricolaData, AgricolaFilters } from '@/types/agricola'

const MOCK_AGRICOLA: AgricolaData = {
  summary: {
    superficie_total: 4_200,
    sembrado: 3_948,
    cosechado: 2_856,
    rendimiento_promedio: 3.82,
    variabilidad_rinde_pct: 14.2,
    hectareas_fuera_ventana: 280,
    lotes_atrasados: 4,
    desvio_aplicacion_promedio: -6.8,
  },
  avance_cultivos: [
    { cultivo: 'Soja', sembrado_ha: 1_850, total_ha: 2_000, porcentaje: 92.5 },
    { cultivo: 'Maíz', sembrado_ha: 1_280, total_ha: 1_400, porcentaje: 91.4 },
    { cultivo: 'Trigo', sembrado_ha: 548, total_ha: 600, porcentaje: 91.3 },
    { cultivo: 'Girasol', sembrado_ha: 270, total_ha: 200, porcentaje: 100 },
  ],
  lotes: [
    { id: 'L01', nombre: 'L-01 Norte', establecimiento: 'La Primavera', cultivo: 'Soja', hectareas: 120, estado: 'cosechado', fecha_siembra: '2024-10-15', rendimiento_tn_ha: 3.9, costo_por_ha: 320_000 },
    { id: 'L02', nombre: 'L-02 Centro', establecimiento: 'La Primavera', cultivo: 'Maíz', hectareas: 95, estado: 'cosechado', fecha_siembra: '2024-09-20', rendimiento_tn_ha: 9.2, costo_por_ha: 480_000 },
    { id: 'L05', nombre: 'L-05 Sur', establecimiento: 'El Ceibo', cultivo: 'Soja', hectareas: 180, estado: 'sembrado', fecha_siembra: '2024-11-05', rendimiento_tn_ha: null, costo_por_ha: 310_000 },
    { id: 'L08', nombre: 'L-08 Este', establecimiento: 'Santa Rosa', cultivo: 'Trigo', hectareas: 145, estado: 'cosechado', fecha_siembra: '2024-06-10', rendimiento_tn_ha: 4.1, costo_por_ha: 280_000 },
    { id: 'L12', nombre: 'L-12 Oeste', establecimiento: 'El Ceibo', cultivo: 'Soja', hectareas: 88, estado: 'en_labores', fecha_siembra: '2024-11-20', rendimiento_tn_ha: null, costo_por_ha: 335_000 },
    { id: 'L18', nombre: 'L-18 Central', establecimiento: 'La Primavera', cultivo: 'Maíz', hectareas: 112, estado: 'sembrado', fecha_siembra: '2024-09-28', rendimiento_tn_ha: null, costo_por_ha: 495_000 },
    { id: 'L31', nombre: 'L-31 Norte B', establecimiento: 'Los Alamos', cultivo: 'Girasol', hectareas: 65, estado: 'barbecho', fecha_siembra: null, rendimiento_tn_ha: null, costo_por_ha: null },
  ],
  rendimiento_historico: [
    { campania: '2020/2021', soja: 3.2, maiz: 8.4, trigo: 3.6, girasol: 2.1 },
    { campania: '2021/2022', soja: 3.5, maiz: 9.0, trigo: 3.9, girasol: 2.3 },
    { campania: '2022/2023', soja: 3.1, maiz: 8.1, trigo: 3.4, girasol: 2.0 },
    { campania: '2023/2024', soja: 3.7, maiz: 9.4, trigo: 4.2, girasol: 2.4 },
    { campania: '2024/2025', soja: 3.9, maiz: 9.2, trigo: 4.1, girasol: 2.5 },
  ],
  plan_vs_actual: [
    { labor: 'Preparación suelo', plan_ha: 4_200, real_ha: 4_080, pendiente_ha: 120, cumplimiento_pct: 97.1 },
    { labor: 'Siembra', plan_ha: 4_200, real_ha: 3_948, pendiente_ha: 252, cumplimiento_pct: 94.0 },
    { labor: 'Fumigación 1era', plan_ha: 3_948, real_ha: 3_720, pendiente_ha: 228, cumplimiento_pct: 94.2 },
    { labor: 'Fertilización', plan_ha: 3_948, real_ha: 3_580, pendiente_ha: 368, cumplimiento_pct: 90.7 },
    { labor: 'Cosecha', plan_ha: 3_948, real_ha: 2_856, pendiente_ha: 1_092, cumplimiento_pct: 72.3 },
  ],
  lotes_atrasados: [
    { lote: 'L-12 Oeste', establecimiento: 'El Ceibo', cultivo: 'Soja', labor: 'Fumigación', pendiente_ha: 88, dias_atraso: 12 },
    { lote: 'L-18 Central', establecimiento: 'La Primavera', cultivo: 'Maíz', labor: 'Fertilización', pendiente_ha: 112, dias_atraso: 8 },
    { lote: 'L-31 Norte B', establecimiento: 'Los Alamos', cultivo: 'Girasol', labor: 'Preparación', pendiente_ha: 65, dias_atraso: 18 },
    { lote: 'L-24 Este', establecimiento: 'Santa Rosa', cultivo: 'Trigo', labor: 'Cosecha', pendiente_ha: 78, dias_atraso: 5 },
  ],
  pendientes_establecimiento: [
    { establecimiento: 'La Primavera', labor: 'Cosecha', pendiente_ha: 420, plan_ha: 650, pendiente_pct: 64.6 },
    { establecimiento: 'El Ceibo', labor: 'Cosecha', pendiente_ha: 380, plan_ha: 620, pendiente_pct: 61.3 },
    { establecimiento: 'Santa Rosa', labor: 'Cosecha', pendiente_ha: 292, plan_ha: 480, pendiente_pct: 60.8 },
  ],
  productividad: [
    { recurso: 'John Deere S760', tipo: 'equipo', hectareas: 480, horas: 96, ha_hora: 5.0 },
    { recurso: 'CR9080 Case', tipo: 'equipo', hectareas: 420, horas: 90, ha_hora: 4.67 },
    { recurso: 'Operador A', tipo: 'operador', hectareas: 320, horas: 72, ha_hora: 4.44 },
  ],
  performance_lotes: [
    { lote: 'L-05 El Ceibo', establecimiento: 'El Ceibo', cultivo: 'Soja', margen_ha: 182_000, desvio_pct: 12.4 },
    { lote: 'L-02 Centro', establecimiento: 'La Primavera', cultivo: 'Maíz', margen_ha: 165_000, desvio_pct: 8.1 },
    { lote: 'L-08 Este', establecimiento: 'Santa Rosa', cultivo: 'Trigo', margen_ha: 145_000, desvio_pct: 5.6 },
    { lote: 'L-18 Central', establecimiento: 'La Primavera', cultivo: 'Maíz', margen_ha: 102_000, desvio_pct: -12.2 },
    { lote: 'L-31 Norte B', establecimiento: 'Los Alamos', cultivo: 'Girasol', margen_ha: 95_000, desvio_pct: -10.7 },
    { lote: 'L-12 Oeste', establecimiento: 'El Ceibo', cultivo: 'Soja', margen_ha: 88_000, desvio_pct: -14.8 },
  ],
  rendimiento_ambientes: [
    { lote: 'L-12 Oeste', establecimiento: 'El Ceibo', cultivo: 'Soja', ambiente: 'bajo', hectareas: 25, rendimiento_objetivo: 3.8, rendimiento_real: 2.9, desvio_pct: -23.7, margen_ha: 88_000 },
    { lote: 'L-18 Central', establecimiento: 'La Primavera', cultivo: 'Maíz', ambiente: 'bajo', hectareas: 30, rendimiento_objetivo: 9.0, rendimiento_real: 7.2, desvio_pct: -20.0, margen_ha: 102_000 },
    { lote: 'L-31 Norte B', establecimiento: 'Los Alamos', cultivo: 'Girasol', ambiente: 'medio', hectareas: 65, rendimiento_objetivo: 2.8, rendimiento_real: 2.3, desvio_pct: -17.9, margen_ha: 95_000 },
  ],
  aplicaciones: [
    { lote: 'L-12 Oeste', establecimiento: 'El Ceibo', cultivo: 'Soja', producto: 'Glifosato 48%', ingrediente_activo: 'Glifosato', dosis_objetivo: 2.5, dosis_real: 2.1, unidad: 'l/ha', desvio_pct: -16.0 },
    { lote: 'L-18 Central', establecimiento: 'La Primavera', cultivo: 'Maíz', producto: 'Atrazina 90%', ingrediente_activo: 'Atrazina', dosis_objetivo: 1.5, dosis_real: 1.2, unidad: 'kg/ha', desvio_pct: -20.0 },
  ],
  nutrientes_lote: [
    { lote: 'L-12 Oeste', establecimiento: 'El Ceibo', cultivo: 'Soja', producto: 'Urea', ingrediente_activo: 'N', dosis_objetivo: 80, dosis_aplicada: 65, desvio_pct: -18.8 },
  ],
  observaciones: [
    { lote: 'L-12 Oeste', establecimiento: 'El Ceibo', cultivo: 'Soja', categoria: 'Malezas', severidad: 'alta', ambiente: 'bajo', descripcion: 'Alta presencia de sorgo de Alepo resistente. Más del 30% de cobertura.', accion_sugerida: 'Aplicación de graminicida de alta eficacia en los próximos 5 días.' },
    { lote: 'L-18 Central', establecimiento: 'La Primavera', cultivo: 'Maíz', categoria: 'Plagas', severidad: 'media', ambiente: 'medio', descripcion: 'Chicharrita (Dalbulus maidis) detectada en 4 plantas cada 100. Monitoreo estricto.', accion_sugerida: 'Aplicar insecticida sistémico preventivo si supera umbral de 5 pl/100.' },
    { lote: 'L-31 Norte B', establecimiento: 'Los Alamos', cultivo: 'Girasol', categoria: 'Nutrición', severidad: 'media', ambiente: 'alto', descripcion: 'Deficiencia de boro en plantas. Hoja nueva presenta clorosis internerval.', accion_sugerida: 'Aplicación foliar de boro quelado (200 g/ha) en emergencia.' },
    { lote: 'L-08 Este', establecimiento: 'Santa Rosa', cultivo: 'Trigo', categoria: 'Enfermedades', severidad: 'baja', ambiente: 'alto', descripcion: 'Roya amarilla incipiente en 2% de plantas. Condición climática favorable para avance.', accion_sugerida: 'Monitoreo diario. Tratar si supera 5% de severidad.' },
  ],
  recomendaciones: [
    { lote: 'L-12 Oeste', cultivo: 'Soja', tipo_labor: 'Fumigación', prioridad: 'alta', recomendacion: 'Aplicar graminicida de rescate (haloxifop 104 g/l) en los próximos 3 días para controlar sorgo de Alepo.', desvio_pct: -16.0 },
    { lote: 'L-18 Central', cultivo: 'Maíz', tipo_labor: 'Monitoreo', prioridad: 'media', recomendacion: 'Incrementar frecuencia de scouting a dos veces por semana por presión de chicharrita.', desvio_pct: null },
    { lote: 'L-31 Norte B', cultivo: 'Girasol', tipo_labor: 'Fertilización foliar', prioridad: 'media', recomendacion: 'Aplicar Boro 200 g/ha en V4-V6 para corregir deficiencia detectada.', desvio_pct: null },
    { lote: 'L-05 Sur', cultivo: 'Soja', tipo_labor: 'Seguimiento', prioridad: 'baja', recomendacion: 'Lote en buen estado. Mantener monitoreo rutinario quincenal.', desvio_pct: null },
  ],
  alerts: [
    { titulo: '3 lotes con rinde debajo del histórico', descripcion: 'L-12, L-18 y L-31 muestran rendimiento 15% por debajo del promedio histórico.', accion: 'Revisar aplicaciones y condición de suelo', severidad: 'warning', prioridad: 1 },
    { titulo: '280ha fuera de ventana óptima', descripcion: 'La siembra tardía compromete potencial de rindes en la campaña actual.', accion: 'Priorizar insumos y recursos en lotes con ventana abierta', severidad: 'warning', prioridad: 2 },
  ],
  actions: [
    { titulo: 'Aplicar graminicida en L-12', descripcion: 'Presencia crítica de sorgo resistente. Ventana de aplicación: 3 días.', owner: 'Ing. Agrónomo', impacto: '88ha con rendimiento comprometido', severity: 'critical' },
    { titulo: 'Completar fertilización pendiente', descripcion: '368ha sin fertilización según plan. Impacto directo en rendimiento.', owner: 'Jefe de campo', impacto: '7-10% del rinde potencial', severity: 'warning' },
  ],
  ultima_actualizacion: new Date().toISOString(),
}

export function useAgricola(filters: AgricolaFilters = {}) {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][]
  ).toString()

  const { data, error, isLoading, mutate } = useSWR<AgricolaData>(
    `/agricola/resumen${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 120000 }
  )

  return {
    data: data ?? (error ? MOCK_AGRICOLA : undefined),
    error,
    isLoading,
    mutate,
    isMockData: !data && !!error,
  }
}
