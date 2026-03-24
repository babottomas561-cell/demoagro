import { Alert } from '@/components/ui/Alert'

type FocusTone = 'info' | 'warning' | 'danger' | 'success'

interface OperationalFocusAlertProps {
  title?: string
  tone?: FocusTone
  bullets: string[]
}

export function OperationalFocusAlert({
  title = 'Foco operativo',
  tone = 'warning',
  bullets,
}: OperationalFocusAlertProps) {
  const visibleBullets = bullets.filter(Boolean).slice(0, 3)
  if (!visibleBullets.length) return null

  return (
    <Alert variant={tone} title={title}>
      <ul className="space-y-1">
        {visibleBullets.map((bullet) => (
          <li key={bullet}>• {bullet}</li>
        ))}
      </ul>
    </Alert>
  )
}
