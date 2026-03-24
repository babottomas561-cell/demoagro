import type { ReactNode } from 'react'
import { PanelSection } from '@/components/panels/PanelSection'

interface AlertsSectionProps {
  description: string
  actions?: ReactNode
  children: ReactNode
}

export function AlertsSection({
  description,
  actions,
  children,
}: AlertsSectionProps) {
  return (
    <PanelSection
      index={5}
      title="Alertas"
      description={description}
      actions={actions}
    >
      {children}
    </PanelSection>
  )
}
