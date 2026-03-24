import type { ReactNode } from 'react'
import { PanelSection } from '@/components/panels/PanelSection'

interface ExecutiveSummarySectionProps {
  description: string
  actions?: ReactNode
  children: ReactNode
}

export function ExecutiveSummarySection({
  description,
  actions,
  children,
}: ExecutiveSummarySectionProps) {
  return (
    <PanelSection
      index={1}
      title="Resumen Ejecutivo"
      description={description}
      actions={actions}
    >
      {children}
    </PanelSection>
  )
}

