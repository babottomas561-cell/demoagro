import { RecommendedActionsPanel } from '@/components/decision/RecommendedActionsPanel'

interface ActionRecommendationsProps {
  actions?: {
    titulo: string
    descripcion: string
    owner: string
    impacto: string
    due?: string
    severity: 'warning' | 'critical' | 'success'
  }[]
  loading?: boolean
  emptyMessage?: string
}

export function ActionRecommendations({
  actions,
  loading,
  emptyMessage,
}: ActionRecommendationsProps) {
  return (
    <RecommendedActionsPanel actions={actions} loading={loading} emptyMessage={emptyMessage} />
  )
}
