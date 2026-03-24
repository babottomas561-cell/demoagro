import clsx from 'clsx'

export type ManagerExplanationMode =
  | 'metric'
  | 'trend'
  | 'comparison'
  | 'composition'
  | 'ranking'
  | 'projection'
  | 'deviation'
  | 'alerts'
  | 'risk'

interface ManagerExplanationProps {
  subject: string
  mode?: ManagerExplanationMode
  items?: string[]
  className?: string
  compact?: boolean
}

function normalizeSubject(subject: string) {
  return subject.trim().toLowerCase()
}

function buildDefaultItems(
  subject: string,
  mode: ManagerExplanationMode
) {
  const normalizedSubject = normalizeSubject(subject)

  switch (mode) {
    case 'trend':
      return [
        `Permite seguir si ${normalizedSubject} mejora o se deteriora.`,
        'Conviene mirar cambios de ritmo y quiebres de tendencia.',
        'Sirve para anticipar ajustes antes de que el impacto sea mayor.',
      ]
    case 'comparison':
      return [
        `Permite comparar dónde ${normalizedSubject} rinde mejor o peor.`,
        'Conviene mirar brechas entre categorías o unidades.',
        'Sirve para reasignar foco, recursos o cobertura.',
      ]
    case 'composition':
      return [
        `Permite ver qué parte de ${normalizedSubject} explica más el resultado.`,
        'Conviene mirar concentraciones y pesos relativos.',
        'Sirve para atacar primero la causa principal.',
      ]
    case 'ranking':
      return [
        `Permite identificar rápido qué empuja y qué frena ${normalizedSubject}.`,
        'Conviene mirar los extremos antes que el promedio.',
        'Sirve para priorizar seguimiento y decisiones concretas.',
      ]
    case 'projection':
      return [
        `Permite anticipar cómo puede moverse ${normalizedSubject} en el próximo tramo.`,
        'Conviene mirar si la proyección se aleja del objetivo.',
        'Sirve para corregir antes de que el desvío se consolide.',
      ]
    case 'deviation':
      return [
        `Permite controlar si ${normalizedSubject} está dentro o fuera del plan.`,
        'Conviene mirar magnitud y dirección del desvío.',
        'Sirve para decidir ajuste inmediato o seguimiento.',
      ]
    case 'alerts':
      return [
        `Permite ver dónde ${normalizedSubject} concentra el riesgo más urgente.`,
        'Conviene mirar severidad y proximidad del problema.',
        'Sirve para ordenar prioridades sin perder foco.',
      ]
    case 'risk':
      return [
        `Permite leer rápido el nivel de riesgo sobre ${normalizedSubject}.`,
        'Conviene mirar si el indicador se acerca a zona crítica.',
        'Sirve para anticipar contingencias y priorizar acción.',
      ]
    case 'metric':
    default:
      return [
        `Permite ver rápido cómo viene ${normalizedSubject}.`,
        'Conviene mirar el cambio reciente y el nivel actual.',
        'Sirve para decidir si hay que profundizar o corregir.',
      ]
  }
}

export function inferManagerExplanationMode(text: string): ManagerExplanationMode {
  const value = text.toLowerCase()

  if (
    value.includes('proyección') ||
    value.includes('pronóstico') ||
    value.includes('sensibilidad') ||
    value.includes('proyect')
  ) {
    return 'projection'
  }
  if (value.includes('ranking') || value.includes('top ') || value.includes('bottom')) {
    return 'ranking'
  }
  if (
    value.includes('composición') ||
    value.includes('participación') ||
    value.includes('distribución') ||
    value.includes('mix') ||
    value.includes('estado de') ||
    value.includes('estado por') ||
    value.includes('semáforo') ||
    value.includes('exposición')
  ) {
    return 'composition'
  }
  if (
    value.includes('histórico') ||
    value.includes('evolución') ||
    value.includes('serie') ||
    value.includes('flujo') ||
    value.includes('precio vs') ||
    value.includes('tipo de cambio') ||
    value.includes('avance')
  ) {
    return 'trend'
  }
  if (
    value.includes('comparador') ||
    value.includes('impacto') ||
    value.includes('vs ') ||
    value.includes('por cultivo') ||
    value.includes('por lote') ||
    value.includes('por establecimiento') ||
    value.includes('por equipo')
  ) {
    return 'comparison'
  }
  if (
    value.includes('alerta') ||
    value.includes('service') ||
    value.includes('riesgo')
  ) {
    return 'alerts'
  }

  return 'metric'
}

export function ManagerExplanation({
  subject,
  mode = 'metric',
  items,
  className,
  compact = false,
}: ManagerExplanationProps) {
  const rows = (items && items.length ? items : buildDefaultItems(subject, mode)).slice(0, 3)

  return (
    <div
      className={clsx(
        'mt-3 border-t border-border/60 pt-3 text-text-muted',
        compact ? 'text-[11px]' : 'text-xs',
        className
      )}
    >
      <p className={clsx('mb-2 font-semibold uppercase tracking-[0.14em] text-text-subtle', compact ? 'text-[9px]' : 'text-[10px]')}>
        Qué mirar
      </p>
      <div className="space-y-1.5">
        {rows.map((item) => (
          <div key={item} className="flex gap-2">
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-text-subtle/70" />
            <p className={clsx('leading-4', compact ? 'text-[11px]' : 'text-xs leading-5')}>
              {item}
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}
