import { Badge } from '@/components/ui/Badge'
import { SkeletonBlock } from '@/components/ui/Spinner'

interface CriticalTask {
  titulo: string
  descripcion: string
  owner?: string
  impacto?: string
  due?: string
  severity?: 'warning' | 'critical' | 'success'
}

interface CriticalTasksBoardProps {
  tasks?: CriticalTask[]
  loading?: boolean
  emptyMessage?: string
}

export function CriticalTasksBoard({
  tasks,
  loading,
  emptyMessage = 'No hay tareas críticas abiertas.',
}: CriticalTasksBoardProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, index) => (
          <div key={index} className="rounded-2xl border border-border bg-surface p-4">
            <SkeletonBlock className="mb-2 h-3 w-2/3" />
            <SkeletonBlock className="mb-2 h-3 w-full" />
            <SkeletonBlock className="h-3 w-1/2" />
          </div>
        ))}
      </div>
    )
  }

  if (!tasks?.length) {
    return (
      <div className="rounded-2xl border border-dashed border-border bg-surface p-5 text-sm text-text-muted">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {tasks.map((task, index) => (
        <div key={`${task.titulo}-${index}`} className="rounded-2xl border border-border bg-surface p-4">
          <div className="mb-2 flex items-start justify-between gap-3">
            <p className="text-sm font-semibold text-text">{task.titulo}</p>
            {task.severity && (
              <Badge variant={task.severity === 'critical' ? 'danger' : task.severity === 'success' ? 'success' : 'warning'}>
                {task.severity === 'critical' ? 'Crítica' : task.severity}
              </Badge>
            )}
          </div>
          <p className="text-sm text-text-muted">{task.descripcion}</p>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-subtle">
            {task.owner && <span>Responsable: {task.owner}</span>}
            {task.impacto && <span>Impacto: {task.impacto}</span>}
            {task.due && <span>Plazo: {task.due}</span>}
          </div>
        </div>
      ))}
    </div>
  )
}
