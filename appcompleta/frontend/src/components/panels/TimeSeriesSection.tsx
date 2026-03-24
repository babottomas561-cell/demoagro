import type { ReactNode } from 'react'
import { PanelSection } from '@/components/panels/PanelSection'

interface TimeSeriesSectionProps {
  description: string
  actions?: ReactNode
  children: ReactNode
}

export function TimeSeriesSection({
  description,
  actions,
  children,
}: TimeSeriesSectionProps) {
  return (
    <PanelSection
      index={2}
      title="Series de Tiempo de Variables Clave"
      description={description}
      actions={actions}
    >
      {children}
    </PanelSection>
  )
}

