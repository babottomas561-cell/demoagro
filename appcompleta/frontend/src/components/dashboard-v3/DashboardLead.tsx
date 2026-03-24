import type { LucideIcon } from 'lucide-react'

export function DashboardLead({
  title,
  description,
  icon: Icon,
  label = 'Decision Workspace',
  scopeLabel,
  scopeBadges = [],
}: {
  title: string
  description: string
  icon: LucideIcon
  label?: string
  scopeLabel?: string
  scopeBadges?: { label: string; value: string }[]
}) {
  return (
    <header className="relative overflow-hidden rounded-[2rem] border border-[#e8dfd1] bg-[radial-gradient(circle_at_top_left,rgba(255,254,250,0.98),rgba(247,241,231,0.94),rgba(242,236,226,0.96))] px-5 py-5 shadow-[0_1px_0_rgba(24,20,12,0.03)] sm:px-6 sm:py-6">
      <div className="pointer-events-none absolute inset-y-0 right-0 hidden w-1/3 bg-[radial-gradient(circle_at_top_right,rgba(48,148,90,0.10),transparent_58%)] xl:block" />
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[#e4dbc9] bg-[linear-gradient(180deg,#faf6ed,#f1e9db)] text-primary-700 shadow-[inset_0_1px_0_rgba(255,255,255,0.6)]">
              <Icon className="h-4 w-4" />
            </div>
            <p className="rounded-full border border-[#e7dece] bg-white/70 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-text-subtle">
              {label}
            </p>
          </div>
          <div className="mt-4 max-w-4xl">
            <h1 className="text-[2.05rem] font-extrabold tracking-[-0.04em] text-text sm:text-[2.35rem]">{title}</h1>
            <p className="mt-2.5 max-w-3xl text-sm leading-6 text-text-muted sm:text-[15px]">{description}</p>
            {scopeLabel ? <p className="mt-4 text-sm font-semibold text-text">{scopeLabel}</p> : null}
            {scopeBadges.length ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {scopeBadges.map((badge) => (
                  <span
                    key={`${badge.label}-${badge.value}`}
                    className="inline-flex items-center gap-1.5 rounded-full border border-[#e6ddcf] bg-white/75 px-2.5 py-1 text-[11px] text-text-muted"
                  >
                    <span className="font-semibold uppercase tracking-[0.12em] text-text-subtle">{badge.label}</span>
                    <span className="text-text">{badge.value}</span>
                  </span>
                ))}
              </div>
            ) : null}
          </div>
        </div>
        <div className="hidden min-w-[13rem] shrink-0 rounded-[1.4rem] border border-[#e6ddcf] bg-white/72 px-4 py-3 backdrop-blur-sm xl:block">
          <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle">Cómo leerlo</p>
          <p className="mt-2 text-sm leading-5 text-text-muted">
            Empezá por los KPIs, seguí la serie principal y cerrá con las dos aperturas comparativas.
          </p>
        </div>
      </div>
    </header>
  )
}
