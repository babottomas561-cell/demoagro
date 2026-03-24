import useSWR from 'swr'
import { fetcher } from '@/lib/api'
import type { StockData, StockFilters } from '@/types/stock'

const MOCK_STOCK: StockData = {
  summary: {
    stock_total_tn: 6_380,
    valor_stock: 1_684_200_000,
    unidades_alerta: 3,
    productos_criticos: 4,
    cobertura_promedio_dias: 18,
    costo_inventario_insumos: 82_500_000,
    necesidad_compra: 35_800_000,
    stock_inmovilizado: 24_000_000,
  },
  items: [
    { id: 'S01', cultivo: 'Soja', establecimiento: 'La Primavera', stock_disponible_tn: 2_400, vendido_tn: 1_600, comprometido_tn: 600, libre_tn: 200, libre_pct: 8.3, precio_referencia: 322_000, valor_estimado: 772_800_000, alerta: 'verde' },
    { id: 'S02', cultivo: 'Maíz', establecimiento: 'El Ceibo', stock_disponible_tn: 2_100, vendido_tn: 1_400, comprometido_tn: 500, libre_tn: 200, libre_pct: 9.5, precio_referencia: 192_000, valor_estimado: 403_200_000, alerta: 'verde' },
    { id: 'S03', cultivo: 'Trigo', establecimiento: 'Santa Rosa', stock_disponible_tn: 1_280, vendido_tn: 900, comprometido_tn: 200, libre_tn: 180, libre_pct: 14.1, precio_referencia: 232_000, valor_estimado: 296_960_000, alerta: 'amarillo' },
    { id: 'S04', cultivo: 'Girasol', establecimiento: 'Los Alamos', stock_disponible_tn: 600, vendido_tn: 350, comprometido_tn: 150, libre_tn: 100, libre_pct: 16.7, precio_referencia: 402_000, valor_estimado: 241_200_000, alerta: 'amarillo' },
  ],
  insumos: [
    { insumo: 'Glifosato 48%', tipo: 'Herbicida', unidad: 'litro', establecimiento: 'La Primavera', stock_actual: 1_200, cobertura_dias: 8, cobertura_ha: 480, quiebre_en_dias: 8, compra_sugerida: 2_400, stock_inmovilizado: 4_320_000, costo_inventario: 4_320_000, consumo_plan_mes: 3_600, consumo_real_mes: 4_100, desvio_consumo_pct: 13.9, severidad: 'critical' },
    { insumo: 'Atrazina 90%', tipo: 'Herbicida', unidad: 'kg', establecimiento: 'El Ceibo', stock_actual: 850, cobertura_dias: 10, cobertura_ha: 566, quiebre_en_dias: 10, compra_sugerida: 1_500, stock_inmovilizado: 3_825_000, costo_inventario: 3_825_000, consumo_plan_mes: 2_400, consumo_real_mes: 2_550, desvio_consumo_pct: 6.3, severidad: 'critical' },
    { insumo: 'Urea granulada', tipo: 'Fertilizante', unidad: 'kg', establecimiento: 'La Primavera', stock_actual: 18_000, cobertura_dias: 15, cobertura_ha: 900, quiebre_en_dias: 15, compra_sugerida: 24_000, stock_inmovilizado: 14_400_000, costo_inventario: 14_400_000, consumo_plan_mes: 36_000, consumo_real_mes: 36_000, desvio_consumo_pct: 0, severidad: 'warning' },
    { insumo: 'Fosfato diamónico', tipo: 'Fertilizante', unidad: 'kg', establecimiento: 'El Ceibo', stock_actual: 12_000, cobertura_dias: 14, cobertura_ha: 600, quiebre_en_dias: 14, compra_sugerida: 18_000, stock_inmovilizado: 10_800_000, costo_inventario: 10_800_000, consumo_plan_mes: 25_000, consumo_real_mes: 25_714, desvio_consumo_pct: 2.9, severidad: 'warning' },
    { insumo: 'Insecticida clorpirifos', tipo: 'Insecticida', unidad: 'litro', establecimiento: 'Santa Rosa', stock_actual: 420, cobertura_dias: 22, cobertura_ha: 210, quiebre_en_dias: null, compra_sugerida: 0, stock_inmovilizado: 1_764_000, costo_inventario: 1_764_000, consumo_plan_mes: 600, consumo_real_mes: 571, desvio_consumo_pct: -4.8, severidad: 'ok' },
    { insumo: 'Fungicida trifloxistrobina', tipo: 'Fungicida', unidad: 'litro', establecimiento: 'La Primavera', stock_actual: 180, cobertura_dias: 25, cobertura_ha: 360, quiebre_en_dias: null, compra_sugerida: 0, stock_inmovilizado: 1_890_000, costo_inventario: 1_890_000, consumo_plan_mes: 210, consumo_real_mes: 216, desvio_consumo_pct: 2.9, severidad: 'ok' },
  ],
  consumo_vs_plan: [
    { insumo: 'Glifosato 48%', consumo_plan_mes: 3_600, consumo_real_mes: 4_100, compra_sugerida: 2_400, desvio_pct: 13.9 },
    { insumo: 'Atrazina 90%', consumo_plan_mes: 2_400, consumo_real_mes: 2_550, compra_sugerida: 1_500, desvio_pct: 6.3 },
    { insumo: 'Urea granulada', consumo_plan_mes: 36_000, consumo_real_mes: 36_000, compra_sugerida: 24_000, desvio_pct: 0 },
    { insumo: 'Fosfato diamónico', consumo_plan_mes: 25_000, consumo_real_mes: 25_714, compra_sugerida: 18_000, desvio_pct: 2.9 },
  ],
  alerts: [
    { id: 'ST01', cultivo: 'Soja', establecimiento: 'La Primavera', mensaje: 'La soja tiene 45 días hábiles para entregar contratos vigentes. Stock ajustado.', severidad: 'warning' },
    { id: 'ST02', cultivo: 'Maíz', establecimiento: 'El Ceibo', mensaje: 'El maíz muestra posición sobrevendida: 200tn comprometidas sin stock físico disponible.', severidad: 'critical' },
    { id: 'ST03', cultivo: '', establecimiento: 'La Primavera', mensaje: 'Glifosato 48% con cobertura crítica (8 días). Compra urgente de 2.400 litros.', severidad: 'critical' },
  ],
  actions: [
    { titulo: 'Compra urgente Glifosato 48%', descripcion: '8 días de cobertura. Quiebre operativo en cosecha si no se repone.', owner: 'Compras', impacto: '480ha sin posibilidad de fumigación', severity: 'critical' },
    { titulo: 'Resolver sobreposición maíz', descripcion: '200tn comprometidas sin stock disponible. Riesgo de incumplimiento contractual.', owner: 'Gerencia Comercial', impacto: 'Penalización por incumplimiento de entrega', severity: 'critical' },
  ],
  ultima_actualizacion: new Date().toISOString(),
}

export function useStock(filters: StockFilters = {}) {
  const params = new URLSearchParams(
    Object.entries(filters).filter(([, v]) => v) as [string, string][]
  ).toString()

  const { data, error, isLoading, mutate } = useSWR<StockData>(
    `/stock/resumen${params ? `?${params}` : ''}`,
    fetcher,
    { refreshInterval: 120000 }
  )

  return {
    data: data ?? (error ? MOCK_STOCK : undefined),
    error,
    isLoading,
    mutate,
    isMockData: !data && !!error,
  }
}
