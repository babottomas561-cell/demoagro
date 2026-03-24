export const CAMPANAS = [
  '2023/2024',
  '2022/2023',
  '2021/2022',
  '2020/2021',
]

export const CULTIVOS = [
  'Soja',
  'Maíz',
  'Trigo',
  'Girasol',
  'Sorgo',
  'Cebada',
]

export const EMPRESAS = [
  { id: '1', nombre: 'AgroNorte S.A.' },
  { id: '2', nombre: 'Campo Verde S.R.L.' },
  { id: '3', nombre: 'Los Pampas Agro' },
]

export const ESTABLECIMIENTOS = [
  { id: '1', nombre: 'La Primavera', empresa_id: '1' },
  { id: '2', nombre: 'El Ceibo', empresa_id: '1' },
  { id: '3', nombre: 'Santa Rosa', empresa_id: '2' },
  { id: '4', nombre: 'Los Alamos', empresa_id: '3' },
]

// Chart colors — light beige theme
export const CHART_COLORS = {
  soja: '#30945a',
  maiz: '#74866f',
  trigo: '#a79c89',
  girasol: '#c1b29a',
  ingresos: '#30945a',
  egresos: '#cf6e63',
  neutro: '#8f8576',
}

// Plotly layout — light beige theme
export const PLOTLY_LAYOUT_BASE = {
  autosize: true,
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { color: '#6f675b', family: 'Inter, system-ui, sans-serif', size: 11 },
  margin: { t: 22, r: 20, b: 42, l: 56, pad: 6 },
  hoverlabel: {
    bgcolor: '#fffdf9',
    bordercolor: '#e6dfd3',
    font: { color: '#1b1a17', family: 'Inter, system-ui, sans-serif', size: 11 },
  },
  xaxis: {
    showgrid: false,
    showline: false,
    zeroline: false,
    tickcolor: 'transparent',
    tickfont: { color: '#8f8576' },
  },
  yaxis: {
    showgrid: true,
    gridcolor: 'rgba(143,133,118,0.12)',
    showline: false,
    zeroline: false,
    tickcolor: 'transparent',
    tickfont: { color: '#8f8576' },
  },
  legend: {
    bgcolor: 'transparent',
    bordercolor: 'transparent',
    font: { color: '#6f675b', size: 11 },
  },
}

export const SEVERITY_CONFIG = {
  info: { color: 'text-info', bg: 'bg-blue-50', border: 'border-blue-200', dot: 'bg-info' },
  warning: { color: 'text-warning', bg: 'bg-amber-50', border: 'border-amber-200', dot: 'bg-warning' },
  critical: { color: 'text-danger', bg: 'bg-red-50', border: 'border-red-200', dot: 'bg-danger' },
  success: { color: 'text-primary-600', bg: 'bg-primary-50', border: 'border-primary-200', dot: 'bg-primary-500' },
}
