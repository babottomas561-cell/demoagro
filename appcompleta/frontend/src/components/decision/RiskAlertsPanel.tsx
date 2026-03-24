import { AlertPriorityList } from '@/components/decision/AlertPriorityList'

interface RiskAlertsPanelProps {
  alerts?: {
    titulo: string
    descripcion: string
    accion?: string
    severidad: 'info' | 'warning' | 'critical' | 'success'
    prioridad?: number
  }[]
  loading?: boolean
  emptyMessage?: string
}

export function RiskAlertsPanel({
  alerts,
  loading,
  emptyMessage,
}: RiskAlertsPanelProps) {
  return (
    <AlertPriorityList alerts={alerts} loading={loading} emptyMessage={emptyMessage} />
  )
}
