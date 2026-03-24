import { mapSeverity, sortExecutiveAlerts } from '@/lib/lemon-ui'

type AlertInput = {
  titulo: string
  impacto: string
  detalle: string
  accion: string
  severidad: string
  prioridad: string
}

export function takeLastItems<T>(rows: T[], count: number) {
  if (rows.length <= count) return rows
  return rows.slice(rows.length - count)
}

export function sumValues<T>(rows: T[], selector: (row: T) => number) {
  return rows.reduce((acc, row) => acc + selector(row), 0)
}

export function buildOperationalAlerts<T extends AlertInput>(alerts: T[]) {
  return sortExecutiveAlerts(alerts).slice(0, 4).map((alert) => ({
    titulo: alert.titulo,
    descripcion: [alert.impacto, alert.detalle].filter(Boolean).join(' '),
    accion: alert.accion,
    prioridad: alert.prioridad,
    severidad: mapSeverity(alert.severidad),
  }))
}
