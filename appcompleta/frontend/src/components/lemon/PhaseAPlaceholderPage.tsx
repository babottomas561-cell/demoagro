'use client'

import { AlertCircle, ArrowRight } from 'lucide-react'
import { DashboardLead } from '@/components/dashboard-v3/DashboardLead'

interface PhaseAPlaceholderPageProps {
  title: string
  description: string
  label: string
  focus: string[]
}

const SECTIONS = [
  'Resumen ejecutivo',
  'Series de tiempo',
  'Apertura / explicación',
  'Análisis avanzado',
  'Alertas',
]

export function PhaseAPlaceholderPage({
  title,
  description,
  label,
  focus,
}: PhaseAPlaceholderPageProps) {
  return (
    <div className="page-inner animate-slide-up space-y-6">
      <DashboardLead
        title={title}
        description={description}
        label={label}
        icon={AlertCircle}
      />

      <section className="rounded-2xl border border-border bg-surface px-5 py-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
          <div className="space-y-1">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
              Fase A
            </p>
            <h2 className="text-lg font-semibold text-text">
              Base limonera, filtros y navegación en preparación
            </h2>
            <p className="max-w-3xl text-sm text-text-muted">
              Este módulo todavía no expone visualizaciones. En esta fase se prioriza la calidad de datos,
              la coherencia operativa y la estructura de filtros antes de construir los paneles.
            </p>
          </div>
          <div className="rounded-xl border border-border bg-background px-3 py-2 text-xs text-text-muted">
            Próxima construcción: FASE B / D
          </div>
        </div>

        <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {focus.map((item) => (
            <div key={item} className="rounded-xl border border-border bg-background px-4 py-3">
              <div className="flex items-start gap-2">
                <ArrowRight className="mt-0.5 h-4 w-4 text-primary-500" />
                <p className="text-sm text-text">{item}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <div className="grid gap-4 xl:grid-cols-2">
        {SECTIONS.map((section) => (
          <section key={section} className="rounded-2xl border border-dashed border-border bg-surface px-5 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-text-subtle">
              Estructura objetivo
            </p>
            <h3 className="mt-1 text-base font-semibold text-text">{section}</h3>
            <p className="mt-2 text-sm text-text-muted">
              Se habilita en la siguiente fase sobre datos limoneros validados y filtros ya operativos.
            </p>
          </section>
        ))}
      </div>
    </div>
  )
}
