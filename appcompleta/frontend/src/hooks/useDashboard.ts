import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { DashboardData, DashboardFilters } from '@/types/dashboard'

const MOCK_DASHBOARD: DashboardData = {
  kpis: {
    ventas_totales: 1_850_000_000,
    margen_bruto_pct: 32.4,
    rendimiento_promedio: 3.8,
    stock_valorizado: 420_000_000,
    ebitda_estimado: 580_000_000,
    flujo_neto_mensual: 48_000_000,
    costos_operativos: 1_270_000_000,
    variacion_campania_anterior: 6.2,
  },
  summary: {
    margen_bruto_total: 580_000_000,
    margen_por_ha: 145_000,
    desvio_presupuesto_pct: -4.2,
    hectareas_fuera_ventana: 280,
    toneladas_sin_fijar: 3_200,
    toneladas_producidas: 18_500,
    toneladas_fijadas: 15_300,
    stock_critico: 2,
    maquinas_criticas: 2,
  },
  ingresos_egresos: [
    { mes: 'Abr 2024', ingresos: 145_000_000, egresos: 98_000_000 },
    { mes: 'May 2024', ingresos: 162_000_000, egresos: 110_000_000 },
    { mes: 'Jun 2024', ingresos: 138_000_000, egresos: 95_000_000 },
    { mes: 'Jul 2024', ingresos: 175_000_000, egresos: 120_000_000 },
    { mes: 'Ago 2024', ingresos: 190_000_000, egresos: 130_000_000 },
    { mes: 'Sep 2024', ingresos: 168_000_000, egresos: 115_000_000 },
    { mes: 'Oct 2024', ingresos: 155_000_000, egresos: 108_000_000 },
    { mes: 'Nov 2024', ingresos: 182_000_000, egresos: 125_000_000 },
    { mes: 'Dic 2024', ingresos: 148_000_000, egresos: 102_000_000 },
    { mes: 'Ene 2025', ingresos: 163_000_000, egresos: 112_000_000 },
    { mes: 'Feb 2025', ingresos: 171_000_000, egresos: 118_000_000 },
    { mes: 'Mar 2025', ingresos: 180_000_000, egresos: 124_000_000 },
  ],
  ventas_cultivo: [
    { cultivo: 'Soja', valor: 985_000_000, volumen: 8_200 },
    { cultivo: 'Maíz', valor: 510_000_000, volumen: 6_800 },
    { cultivo: 'Trigo', valor: 220_000_000, volumen: 2_400 },
    { cultivo: 'Girasol', valor: 135_000_000, volumen: 900 },
  ],
  insights: [
    {
      id: '1',
      titulo: 'Soja representa el 58% del margen',
      descripcion: 'El maíz muestra desvío positivo de +8% vs campaña anterior.',
      severidad: 'success',
      modulo: 'comercial',
      timestamp: new Date().toISOString(),
    },
    {
      id: '2',
      titulo: 'Costos de insumos +23% interanual',
      descripcion: 'El margen operativo se comprimió de 38% a 31%.',
      severidad: 'warning',
      modulo: 'finanzas',
      timestamp: new Date().toISOString(),
    },
    {
      id: '3',
      titulo: '2 cosechadoras superan 3000hs',
      descripcion: 'Programar mantenimiento preventivo urgente.',
      severidad: 'critical',
      modulo: 'maquinaria',
      timestamp: new Date().toISOString(),
    },
  ],
  lot_profitability: [
    { lote: 'L-05 El Ceibo', establecimiento: 'El Ceibo', cultivo: 'Soja', margen_ha: 182_000, margen_total: 5_460_000, desvio_pct: 12.4, contribucion_pct: 18.2 },
    { lote: 'L-02 La Primavera', establecimiento: 'La Primavera', cultivo: 'Maíz', margen_ha: 165_000, margen_total: 4_125_000, desvio_pct: 8.1, contribucion_pct: 13.7 },
    { lote: 'L-08 Santa Rosa', establecimiento: 'Santa Rosa', cultivo: 'Soja', margen_ha: 158_000, margen_total: 3_950_000, desvio_pct: 5.6, contribucion_pct: 13.2 },
    { lote: 'L-12 El Ceibo', establecimiento: 'El Ceibo', cultivo: 'Trigo', margen_ha: 88_000, margen_total: 1_760_000, desvio_pct: -14.8, contribucion_pct: 5.9 },
    { lote: 'L-18 La Primavera', establecimiento: 'La Primavera', cultivo: 'Soja', margen_ha: 102_000, margen_total: 2_040_000, desvio_pct: -12.2, contribucion_pct: 6.8 },
    { lote: 'L-31 Los Alamos', establecimiento: 'Los Alamos', cultivo: 'Maíz', margen_ha: 95_000, margen_total: 2_375_000, desvio_pct: -10.7, contribucion_pct: 7.9 },
  ],
  top_lotes: [
    { lote: 'L-05 El Ceibo', establecimiento: 'El Ceibo', cultivo: 'Soja', margen_ha: 182_000, margen_total: 5_460_000, desvio_pct: 12.4, contribucion_pct: 18.2 },
    { lote: 'L-02 La Primavera', establecimiento: 'La Primavera', cultivo: 'Maíz', margen_ha: 165_000, margen_total: 4_125_000, desvio_pct: 8.1, contribucion_pct: 13.7 },
    { lote: 'L-08 Santa Rosa', establecimiento: 'Santa Rosa', cultivo: 'Soja', margen_ha: 158_000, margen_total: 3_950_000, desvio_pct: 5.6, contribucion_pct: 13.2 },
  ],
  bottom_lotes: [
    { lote: 'L-12 El Ceibo', establecimiento: 'El Ceibo', cultivo: 'Trigo', margen_ha: 88_000, margen_total: 1_760_000, desvio_pct: -14.8, contribucion_pct: 5.9 },
    { lote: 'L-18 La Primavera', establecimiento: 'La Primavera', cultivo: 'Soja', margen_ha: 102_000, margen_total: 2_040_000, desvio_pct: -12.2, contribucion_pct: 6.8 },
    { lote: 'L-31 Los Alamos', establecimiento: 'Los Alamos', cultivo: 'Maíz', margen_ha: 95_000, margen_total: 2_375_000, desvio_pct: -10.7, contribucion_pct: 7.9 },
  ],
  result_bridge: [
    { label: 'Ingresos brutos', value: 1_850_000_000, kind: 'positive' },
    { label: 'Insumos', value: -540_000_000, kind: 'negative' },
    { label: 'Labores', value: -320_000_000, kind: 'negative' },
    { label: 'Gastos admin', value: -95_000_000, kind: 'negative' },
    { label: 'Financiero', value: -75_000_000, kind: 'negative' },
    { label: 'Margen neto', value: 820_000_000, kind: 'total' },
  ],
  semaforos: [
    { label: 'Cobertura comercial', status: 'warning', detail: '68% vs objetivo 80%' },
    { label: 'Disponibilidad flota', status: 'success', detail: '82% operativa' },
    { label: 'Cobertura insumos', status: 'warning', detail: '14 días promedio' },
    { label: 'Avance siembra', status: 'success', detail: '94% completado' },
  ],
  alerts: [
    { id: 'a1', titulo: 'Cosechadoras sobre límite de hs', descripcion: '2 equipos superan 3000hs desde último service. Riesgo de parada en cosecha.', severidad: 'critical', modulo: 'maquinaria', accion: 'Programar service preventivo inmediato', prioridad: 1 },
    { id: 'a2', titulo: '3.200 tn soja sin precio', descripcion: 'Con precio actual USD 272, potencial ingreso de USD 870.400 sin capturar.', severidad: 'warning', modulo: 'comercial', accion: 'Evaluar fijación o contrato a término', prioridad: 2 },
    { id: 'a3', titulo: 'Insumos +23% vs campaña anterior', descripcion: 'Margen operativo comprimido de 38% a 31%. Revisar estructura de costos.', severidad: 'warning', modulo: 'finanzas', accion: 'Renegociar con proveedores clave', prioridad: 3 },
  ],
  actions: [
    { titulo: 'Programar service cosechadoras', descripcion: 'Dos equipos superan umbral de 3000hs. Ventana: próximas 2 semanas.', owner: 'Jefe de Maquinaria', impacto: 'Evitar parada no planificada en cosecha de soja', severity: 'critical' },
    { titulo: 'Fijar 3.200 tn soja abierta', descripcion: 'Precio actual favorable. Ventana de fijación estimada: próximos 15 días.', owner: 'Gerencia Comercial', impacto: 'USD 870.400 adicionales al margen', severity: 'warning' },
    { titulo: 'Revisar lotes con rinde bajo', descripcion: 'L-12, L-18 y L-31 muestran rinde 15% debajo de histórico.', owner: 'Ing. Agrónomo', impacto: 'Corrección agronómica antes de próxima campaña', severity: 'warning' },
  ],
  ultima_actualizacion: new Date().toISOString(),
}

export function useDashboard(filters: DashboardFilters = {}) {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][]
  ).toString()

  const { data, error, isLoading, mutate } = useSWR<DashboardData>(
    `/dashboard/executive${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 60000 }
  )

  return {
    data: data ?? (error ? MOCK_DASHBOARD : undefined),
    error,
    isLoading,
    mutate,
    isMockData: !data && !!error,
  }
}
