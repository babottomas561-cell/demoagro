import type { ReactNode } from 'react'
import { PanelSection } from '@/components/panels/PanelSection'

interface AnalysisSectionProps {
  description: string
  actions?: ReactNode
  children: ReactNode
}

export function AnalysisSection({
  description,
  actions,
  children,
}: AnalysisSectionProps) {
  return (
    <PanelSection
      index={4}
      title="Análisis Avanzado"
      description={description}
      actions={actions}
    >
      {children}
    </PanelSection>
  )
}

