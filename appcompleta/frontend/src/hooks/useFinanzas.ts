import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { FinanzasData, FinanzasFilters } from '@/types/finanzas'

const MOCK_FINANZAS: FinanzasData = {
  summary: {
    capital_de_trabajo: 380_000_000,
    deuda_por_vencer: 95_000_000,
    cuentas_a_cobrar: 128_000_000,
    flujo_neto: 48_000_000,
    margen_bruto_total: 580_000_000,
    margen_por_ha: 138_095,
    desvio_presupuesto_pct: -4.2,
    costo_por_ha: 302_381,
    costo_por_tonelada: 68_649,
    capital_trabajo_comprometido: 215_000_000,
    deuda_corto_plazo: 95_000_000,
    riesgo_caja: 'medio',
    ingresos_operativos: 1_850_000_000,
  },
  flujo_mensual: [
    { mes: '2023-04-01', ingresos: 98_000_000, egresos: 72_000_000, neto: 26_000_000 },
    { mes: '2023-05-01', ingresos: 115_000_000, egresos: 78_000_000, neto: 37_000_000 },
    { mes: '2023-06-01', ingresos: 105_000_000, egresos: 68_000_000, neto: 37_000_000 },
    { mes: '2023-07-01', ingresos: 88_000_000, egresos: 82_000_000, neto: 6_000_000 },
    { mes: '2023-08-01', ingresos: 72_000_000, egresos: 95_000_000, neto: -23_000_000 },
    { mes: '2023-09-01', ingresos: 68_000_000, egresos: 88_000_000, neto: -20_000_000 },
    { mes: '2023-10-01', ingresos: 82_000_000, egresos: 75_000_000, neto: 7_000_000 },
    { mes: '2023-11-01', ingresos: 95_000_000, egresos: 82_000_000, neto: 13_000_000 },
    { mes: '2023-12-01', ingresos: 125_000_000, egresos: 78_000_000, neto: 47_000_000 },
    { mes: '2024-01-01', ingresos: 132_000_000, egresos: 88_000_000, neto: 44_000_000 },
    { mes: '2024-02-01', ingresos: 140_000_000, egresos: 92_000_000, neto: 48_000_000 },
    { mes: '2024-03-01', ingresos: 138_000_000, egresos: 90_000_000, neto: 48_000_000 },
    { mes: '2024-04-01', ingresos: 145_000_000, egresos: 98_000_000, neto: 47_000_000 },
    { mes: '2024-05-01', ingresos: 162_000_000, egresos: 110_000_000, neto: 52_000_000 },
    { mes: '2024-06-01', ingresos: 138_000_000, egresos: 95_000_000, neto: 43_000_000 },
    { mes: '2024-07-01', ingresos: 175_000_000, egresos: 120_000_000, neto: 55_000_000 },
    { mes: '2024-08-01', ingresos: 190_000_000, egresos: 130_000_000, neto: 60_000_000 },
    { mes: '2024-09-01', ingresos: 168_000_000, egresos: 115_000_000, neto: 53_000_000 },
    { mes: '2024-10-01', ingresos: 155_000_000, egresos: 108_000_000, neto: 47_000_000 },
    { mes: '2024-11-01', ingresos: 182_000_000, egresos: 125_000_000, neto: 57_000_000 },
    { mes: '2024-12-01', ingresos: 148_000_000, egresos: 102_000_000, neto: 46_000_000 },
    { mes: '2025-01-01', ingresos: 163_000_000, egresos: 112_000_000, neto: 51_000_000 },
    { mes: '2025-02-01', ingresos: 171_000_000, egresos: 118_000_000, neto: 53_000_000 },
    { mes: '2025-03-01', ingresos: 180_000_000, egresos: 124_000_000, neto: 56_000_000 },
  ],
  flujo_categorias: [],
  cash_projection: [
    { mes: '2023-04-01', ingresos: 98_000_000, egresos: 72_000_000, neto: 26_000_000, saldo_acumulado: 26_000_000 },
    { mes: '2023-05-01', ingresos: 115_000_000, egresos: 78_000_000, neto: 37_000_000, saldo_acumulado: 63_000_000 },
    { mes: '2023-06-01', ingresos: 105_000_000, egresos: 68_000_000, neto: 37_000_000, saldo_acumulado: 100_000_000 },
    { mes: '2023-07-01', ingresos: 88_000_000, egresos: 82_000_000, neto: 6_000_000, saldo_acumulado: 106_000_000 },
    { mes: '2023-08-01', ingresos: 72_000_000, egresos: 95_000_000, neto: -23_000_000, saldo_acumulado: 83_000_000 },
    { mes: '2023-09-01', ingresos: 68_000_000, egresos: 88_000_000, neto: -20_000_000, saldo_acumulado: 63_000_000 },
    { mes: '2023-10-01', ingresos: 82_000_000, egresos: 75_000_000, neto: 7_000_000, saldo_acumulado: 70_000_000 },
    { mes: '2023-11-01', ingresos: 95_000_000, egresos: 82_000_000, neto: 13_000_000, saldo_acumulado: 83_000_000 },
    { mes: '2023-12-01', ingresos: 125_000_000, egresos: 78_000_000, neto: 47_000_000, saldo_acumulado: 130_000_000 },
    { mes: '2024-01-01', ingresos: 132_000_000, egresos: 88_000_000, neto: 44_000_000, saldo_acumulado: 174_000_000 },
    { mes: '2024-02-01', ingresos: 140_000_000, egresos: 92_000_000, neto: 48_000_000, saldo_acumulado: 222_000_000 },
    { mes: '2024-03-01', ingresos: 138_000_000, egresos: 90_000_000, neto: 48_000_000, saldo_acumulado: 270_000_000 },
    { mes: '2024-04-01', ingresos: 145_000_000, egresos: 98_000_000, neto: 47_000_000, saldo_acumulado: 317_000_000 },
    { mes: '2024-05-01', ingresos: 162_000_000, egresos: 110_000_000, neto: 52_000_000, saldo_acumulado: 369_000_000 },
    { mes: '2024-06-01', ingresos: 138_000_000, egresos: 95_000_000, neto: 43_000_000, saldo_acumulado: 412_000_000 },
    { mes: '2024-07-01', ingresos: 175_000_000, egresos: 120_000_000, neto: 55_000_000, saldo_acumulado: 467_000_000 },
    { mes: '2024-08-01', ingresos: 190_000_000, egresos: 130_000_000, neto: 60_000_000, saldo_acumulado: 527_000_000 },
    { mes: '2024-09-01', ingresos: 168_000_000, egresos: 115_000_000, neto: 53_000_000, saldo_acumulado: 580_000_000 },
    { mes: '2024-10-01', ingresos: 155_000_000, egresos: 108_000_000, neto: 47_000_000, saldo_acumulado: 627_000_000 },
    { mes: '2024-11-01', ingresos: 182_000_000, egresos: 125_000_000, neto: 57_000_000, saldo_acumulado: 684_000_000 },
    { mes: '2024-12-01', ingresos: 148_000_000, egresos: 102_000_000, neto: 46_000_000, saldo_acumulado: 730_000_000 },
    { mes: '2025-01-01', ingresos: 163_000_000, egresos: 112_000_000, neto: 51_000_000, saldo_acumulado: 781_000_000 },
    { mes: '2025-02-01', ingresos: 171_000_000, egresos: 118_000_000, neto: 53_000_000, saldo_acumulado: 834_000_000 },
    { mes: '2025-03-01', ingresos: 180_000_000, egresos: 124_000_000, neto: 56_000_000, saldo_acumulado: 890_000_000 },
  ],
  cost_breakdown: [
    { label: 'Insumos agropecuarios', value: 540_000_000, kind: 'negative' },
    { label: 'Labores y servicios', value: 320_000_000, kind: 'negative' },
    { label: 'Combustible', value: 128_000_000, kind: 'negative' },
    { label: 'Gastos administrativos', value: 95_000_000, kind: 'negative' },
    { label: 'Costo financiero', value: 75_000_000, kind: 'negative' },
    { label: 'Otros', value: 62_000_000, kind: 'negative' },
    { label: 'Ingresos operativos', value: 1_850_000_000, kind: 'positive' },
    { label: 'Margen bruto', value: 580_000_000, kind: 'total' },
  ],
  resultados_lote: [
    { lote: 'L-05 El Ceibo', establecimiento: 'El Ceibo', cultivo: 'Soja', hectareas: 180, ingreso_total: 57_960_000, costo_total: 25_200_000, costo_ha: 140_000, costo_tonelada: 35_897, margen_ha: 182_000, margen_total: 32_760_000, desvio_pct: 12.4, rentabilidad_pct: 56.5 },
    { lote: 'L-02 Centro', establecimiento: 'La Primavera', cultivo: 'Maíz', hectareas: 95, ingreso_total: 28_728_000, costo_total: 13_110_000, costo_ha: 138_000, costo_tonelada: 15_000, margen_ha: 165_000, margen_total: 15_675_000, desvio_pct: 8.1, rentabilidad_pct: 54.6 },
    { lote: 'L-08 Este', establecimiento: 'Santa Rosa', cultivo: 'Trigo', hectareas: 145, ingreso_total: 29_856_000, costo_total: 14_790_000, costo_ha: 102_000, costo_tonelada: 24_878, margen_ha: 145_000, margen_total: 21_025_000, desvio_pct: 5.6, rentabilidad_pct: 58.9 },
    { lote: 'L-18 Central', establecimiento: 'La Primavera', cultivo: 'Maíz', hectareas: 112, ingreso_total: 27_494_400, costo_total: 16_070_400, costo_ha: 143_500, costo_tonelada: 15_598, margen_ha: 102_000, margen_total: 11_424_000, desvio_pct: -12.2, rentabilidad_pct: 41.6 },
    { lote: 'L-31 Norte B', establecimiento: 'Los Alamos', cultivo: 'Girasol', hectareas: 65, ingreso_total: 9_230_000, costo_total: 3_055_000, costo_ha: 47_000, costo_tonelada: 20_459, margen_ha: 95_000, margen_total: 6_175_000, desvio_pct: -10.7, rentabilidad_pct: 66.9 },
    { lote: 'L-12 Oeste', establecimiento: 'El Ceibo', cultivo: 'Soja', hectareas: 88, ingreso_total: 22_041_600, costo_total: 14_289_600, costo_ha: 162_381, costo_tonelada: 55_997, margen_ha: 88_000, margen_total: 7_744_000, desvio_pct: -14.8, rentabilidad_pct: 35.1 },
  ],
  rentabilidad_cultivo: [
    { cultivo: 'Soja', ingreso_total: 985_000_000, costo_total: 540_000_000, margen_total: 445_000_000, margen_ha: 161_364, costo_ha: 196_364, costo_tonelada: 50_376, desvio_pct: 5.8 },
    { cultivo: 'Maíz', ingreso_total: 510_000_000, costo_total: 320_000_000, margen_total: 190_000_000, margen_ha: 98_958, costo_ha: 166_667, costo_tonelada: 18_120, desvio_pct: -3.4 },
    { cultivo: 'Trigo', ingreso_total: 220_000_000, costo_total: 115_000_000, margen_total: 105_000_000, margen_ha: 175_000, costo_ha: 191_667, costo_tonelada: 46_747, desvio_pct: 2.1 },
    { cultivo: 'Girasol', ingreso_total: 135_000_000, costo_total: 55_000_000, margen_total: 80_000_000, margen_ha: 200_000, costo_ha: 137_500, costo_tonelada: 61_111, desvio_pct: 7.3 },
  ],
  rentabilidad_establecimiento: [
    { establecimiento: 'La Primavera', ingreso_total: 780_000_000, costo_total: 430_000_000, margen_total: 350_000_000, margen_ha: 140_000, costo_tonelada: 57_333 },
    { establecimiento: 'El Ceibo', ingreso_total: 620_000_000, costo_total: 338_000_000, margen_total: 282_000_000, margen_ha: 135_577, costo_tonelada: 53_651 },
    { establecimiento: 'Santa Rosa', ingreso_total: 310_000_000, costo_total: 162_000_000, margen_total: 148_000_000, margen_ha: 148_000, costo_tonelada: 52_258 },
    { establecimiento: 'Los Alamos', ingreso_total: 140_000_000, costo_total: 70_000_000, margen_total: 70_000_000, margen_ha: 140_000, costo_tonelada: 46_667 },
  ],
  sensitivity: [
    { scenario: 'Precio soja -10%', margen_total: 481_800_000, delta_pct: -16.9 },
    { scenario: 'Precio soja -5%', margen_total: 530_900_000, delta_pct: -8.5 },
    { scenario: 'Escenario base', margen_total: 580_000_000, delta_pct: 0 },
    { scenario: 'Tipo de cambio +10%', margen_total: 621_600_000, delta_pct: 7.2 },
    { scenario: 'Rinde +5%', margen_total: 638_200_000, delta_pct: 10.0 },
  ],
  alerts: [
    { titulo: 'Insumos +23% vs campaña anterior', descripcion: 'Margen operativo se comprimió de 38% a 31%. La tendencia requiere revisión antes de la próxima campaña.', accion: 'Renegociar contratos de insumos para campaña 25/26', severidad: 'warning', prioridad: 1 },
    { titulo: 'Capital de trabajo 57% comprometido', descripcion: 'ARS 215M comprometidos sobre ARS 380M disponibles. Margen de maniobra reducido.', accion: 'Acelerar cobros pendientes y diferir gastos no urgentes', severidad: 'warning', prioridad: 2 },
  ],
  actions: [
    { titulo: 'Renegociar insumos campaña 25/26', descripcion: 'Costo de insumos sube 23% interanual. Ventana de negociación: próximas 8 semanas.', owner: 'Gerencia General', impacto: 'Recuperar 4-6% del margen operativo', severity: 'warning' },
    { titulo: 'Acelerar cobros pendientes', descripcion: 'ARS 128M en cuentas a cobrar. Negociar plazo reducido con principales clientes.', owner: 'Administración', impacto: 'Mejorar posición de caja de corto plazo', severity: 'warning' },
  ],
  ultima_actualizacion: new Date().toISOString(),
}

export function useFinanzas(filters: FinanzasFilters = {}) {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][]
  ).toString()

  const { data, error, isLoading, mutate } = useSWR<FinanzasData>(
    `/finanzas/resumen${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 120000 }
  )

  return {
    data: data ?? (error ? MOCK_FINANZAS : undefined),
    error,
    isLoading,
    mutate,
    isMockData: !data && !!error,
  }
}
