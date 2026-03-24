import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { ComercialData, ComercialFilters } from '@/types/comercial'

const MOCK_COMERCIAL: ComercialData = {
  summary: {
    volumen_vendido: 15_300,
    precio_promedio: 310_000,
    valor_total: 1_850_000_000,
    contratos_cerrados: 28,
    toneladas_producidas: 18_500,
    toneladas_comprometidas: 16_800,
    toneladas_fijadas: 15_300,
    toneladas_entregadas: 12_100,
    posicion_abierta_tn: 3_200,
    cobertura_promedio_pct: 82.7,
    desvio_precio_vs_referencia_pct: 3.2,
  },
  precios_historicos: [
    { fecha: '2023-04-01', soja: 158_000, maiz: 92_000, trigo: 118_000, girasol: 205_000 },
    { fecha: '2023-05-01', soja: 165_000, maiz: 96_000, trigo: 122_000, girasol: 212_000 },
    { fecha: '2023-06-01', soja: 172_000, maiz: 100_000, trigo: 126_000, girasol: 220_000 },
    { fecha: '2023-07-01', soja: 178_000, maiz: 104_000, trigo: 130_000, girasol: 228_000 },
    { fecha: '2023-08-01', soja: 225_000, maiz: 130_000, trigo: 162_000, girasol: 285_000 },
    { fecha: '2023-09-01', soja: 235_000, maiz: 135_000, trigo: 168_000, girasol: 295_000 },
    { fecha: '2023-10-01', soja: 242_000, maiz: 140_000, trigo: 174_000, girasol: 305_000 },
    { fecha: '2023-11-01', soja: 248_000, maiz: 144_000, trigo: 178_000, girasol: 312_000 },
    { fecha: '2023-12-01', soja: 480_000, maiz: 270_000, trigo: 340_000, girasol: 585_000 },
    { fecha: '2024-01-01', soja: 498_000, maiz: 280_000, trigo: 352_000, girasol: 605_000 },
    { fecha: '2024-02-01', soja: 512_000, maiz: 288_000, trigo: 362_000, girasol: 622_000 },
    { fecha: '2024-03-01', soja: 525_000, maiz: 295_000, trigo: 372_000, girasol: 638_000 },
    { fecha: '2024-04-01', soja: 265_000, maiz: 152_000, trigo: 190_000, girasol: 340_000 },
    { fecha: '2024-05-01', soja: 272_000, maiz: 158_000, trigo: 195_000, girasol: 348_000 },
    { fecha: '2024-06-01', soja: 268_000, maiz: 155_000, trigo: 198_000, girasol: 352_000 },
    { fecha: '2024-07-01', soja: 280_000, maiz: 162_000, trigo: 202_000, girasol: 360_000 },
    { fecha: '2024-08-01', soja: 285_000, maiz: 168_000, trigo: 208_000, girasol: 368_000 },
    { fecha: '2024-09-01', soja: 278_000, maiz: 165_000, trigo: 205_000, girasol: 362_000 },
    { fecha: '2024-10-01', soja: 290_000, maiz: 172_000, trigo: 212_000, girasol: 375_000 },
    { fecha: '2024-11-01', soja: 298_000, maiz: 178_000, trigo: 218_000, girasol: 382_000 },
    { fecha: '2024-12-01', soja: 302_000, maiz: 175_000, trigo: 215_000, girasol: 378_000 },
    { fecha: '2025-01-01', soja: 308_000, maiz: 182_000, trigo: 222_000, girasol: 388_000 },
    { fecha: '2025-02-01', soja: 315_000, maiz: 188_000, trigo: 228_000, girasol: 395_000 },
    { fecha: '2025-03-01', soja: 322_000, maiz: 192_000, trigo: 232_000, girasol: 402_000 },
  ],
  ventas_cliente: [
    { cliente: 'Oleaginosa Moreno', valor: 680_000_000, volumen: 5_200 },
    { cliente: 'Bunge Argentina', valor: 520_000_000, volumen: 4_100 },
    { cliente: 'Louis Dreyfus', valor: 380_000_000, volumen: 3_000 },
    { cliente: 'Cargill SA', valor: 270_000_000, volumen: 2_100 },
  ],
  operaciones: [
    { id: 'OP001', fecha: '2025-03-10', cultivo: 'Soja', cliente: 'Oleaginosa Moreno', volumen_tn: 1_200, precio_ars_tn: 322_000, valor_total_ars: 386_400_000, estado: 'confirmada', tipo_contrato: 'Disponible' },
    { id: 'OP002', fecha: '2025-03-05', cultivo: 'Maíz', cliente: 'Bunge Argentina', volumen_tn: 800, precio_ars_tn: 192_000, valor_total_ars: 153_600_000, estado: 'entregada', tipo_contrato: 'Forward' },
    { id: 'OP003', fecha: '2025-02-28', cultivo: 'Soja', cliente: 'Louis Dreyfus', volumen_tn: 950, precio_ars_tn: 315_000, valor_total_ars: 299_250_000, estado: 'confirmada', tipo_contrato: 'Disponible' },
    { id: 'OP004', fecha: '2025-02-15', cultivo: 'Trigo', cliente: 'Cargill SA', volumen_tn: 600, precio_ars_tn: 228_000, valor_total_ars: 136_800_000, estado: 'entregada', tipo_contrato: 'Disponible' },
    { id: 'OP005', fecha: '2025-01-20', cultivo: 'Girasol', cliente: 'Oleaginosa Moreno', volumen_tn: 280, precio_ars_tn: 395_000, valor_total_ars: 110_600_000, estado: 'pendiente', tipo_contrato: 'Forward' },
  ],
  posiciones: [
    { cultivo: 'Soja', toneladas_producidas: 8_200, toneladas_comprometidas: 7_400, toneladas_fijadas: 6_800, toneladas_entregadas: 5_200, stock_fisico: 3_000, abierta_tn: 1_400, pendiente_entrega_tn: 1_600, cobertura_pct: 82.9, compromiso_pct: 90.2, desvio_stock_cobertura_tn: -200, precio_referencia: 322_000, recomendacion: 'fijar', severidad: 'warning' },
    { cultivo: 'Maíz', toneladas_producidas: 6_800, toneladas_comprometidas: 6_200, toneladas_fijadas: 5_900, toneladas_entregadas: 4_800, stock_fisico: 2_000, abierta_tn: 900, pendiente_entrega_tn: 1_100, cobertura_pct: 86.8, compromiso_pct: 91.2, desvio_stock_cobertura_tn: -100, precio_referencia: 192_000, recomendacion: 'esperar', severidad: 'success' },
    { cultivo: 'Trigo', toneladas_producidas: 2_400, toneladas_comprometidas: 2_200, toneladas_fijadas: 2_100, toneladas_entregadas: 1_800, stock_fisico: 600, abierta_tn: 300, pendiente_entrega_tn: 300, cobertura_pct: 87.5, compromiso_pct: 91.7, desvio_stock_cobertura_tn: 0, precio_referencia: 228_000, recomendacion: 'esperar', severidad: 'success' },
    { cultivo: 'Girasol', toneladas_producidas: 900, toneladas_comprometidas: 720, toneladas_fijadas: 600, toneladas_entregadas: 420, stock_fisico: 480, abierta_tn: 300, pendiente_entrega_tn: 180, cobertura_pct: 66.7, compromiso_pct: 80.0, desvio_stock_cobertura_tn: 180, precio_referencia: 402_000, recomendacion: 'fijar', severidad: 'warning' },
  ],
  entregas: [
    { cultivo: 'Soja', cliente: 'Oleaginosa Moreno', fecha_programada: '2025-04-15', volumen_tn: 800, pendiente_tn: 800, estado: 'pendiente' },
    { cultivo: 'Maíz', cliente: 'Bunge Argentina', fecha_programada: '2025-04-10', volumen_tn: 600, pendiente_tn: 600, estado: 'pendiente' },
    { cultivo: 'Soja', cliente: 'Louis Dreyfus', fecha_programada: '2025-04-20', volumen_tn: 600, pendiente_tn: 400, estado: 'parcial' },
  ],
  proximos_vencer: [
    { id: 1, cultivo: 'Soja', cliente: 'Oleaginosa Moreno', volumen_tn: 800, fecha_entrega: '2025-04-15', dias_para_vencer: 26, estado: 'pendiente', precio_fijado: 322_000 },
    { id: 2, cultivo: 'Maíz', cliente: 'Bunge Argentina', volumen_tn: 600, fecha_entrega: '2025-04-10', dias_para_vencer: 21, estado: 'pendiente', precio_fijado: 192_000 },
    { id: 3, cultivo: 'Girasol', cliente: 'Oleaginosa Moreno', volumen_tn: 280, fecha_entrega: '2025-05-01', dias_para_vencer: 42, estado: 'pendiente', precio_fijado: 0 },
  ],
  alerts: [
    { titulo: '3.200 tn sin precio bajo contrato', descripcion: 'Con precio actual ARS 322.000/tn, potencial ingreso de $1.030M sin capturar.', accion: 'Evaluar fijación o apertura de forward antes del 15 de abril.', severidad: 'warning', prioridad: 1 },
    { titulo: 'Cobertura de girasol al 67%', descripcion: 'El girasol tiene la menor cobertura de la campaña. Precio en máximo de 12 meses.', accion: 'Fijar las 300tn abiertas antes del vencimiento de mayo.', severidad: 'warning', prioridad: 2 },
  ],
  actions: [
    { titulo: 'Fijar posición abierta de soja', descripcion: 'Con USD 272/tn en mercado disponible, la ventana de fijación es favorable.', owner: 'Gerencia Comercial', impacto: 'USD 870.400 adicionales al margen de campaña', severity: 'warning' },
    { titulo: 'Cubrir entrega maíz Bunge 21 días', descripcion: 'Contrato a 600tn con vencimiento en 21 días. Logística a confirmar.', owner: 'Operaciones', impacto: 'Evitar penalización contractual por demora', severity: 'warning' },
  ],
  ultima_actualizacion: new Date().toISOString(),
}

export function useComercial(filters: ComercialFilters = {}) {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][]
  ).toString()

  const { data, error, isLoading, mutate } = useSWR<ComercialData>(
    `/comercial/resumen${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 120000 }
  )

  return {
    data: data ?? (error ? MOCK_COMERCIAL : undefined),
    error,
    isLoading,
    mutate,
    isMockData: !data && !!error,
  }
}
