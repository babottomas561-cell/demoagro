import type { ReactNode } from 'react'
import { PanelSection } from '@/components/panels/PanelSection'

interface BreakdownSectionProps {
  description: string
  actions?: ReactNode
  children: ReactNode
}

export function BreakdownSection({
  description,
  actions,
  children,
}: BreakdownSectionProps) {
  return (
    <PanelSection
      index={3}
      title="Apertura / Explicación del Resultado"
      description={description}
      actions={actions}
    >
      {children}
    </PanelSection>
  )
}

