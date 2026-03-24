import { Lightbulb } from 'lucide-react'
import { InsightCard } from '@/components/ui/InsightCard'
import { SkeletonBlock } from '@/components/ui/Spinner'
import type { ExecutiveInsight } from '@/types/dashboard'

interface ExecutiveInsightsProps {
  insights?: ExecutiveInsight[]
  loading?: boolean
}

export function ExecutiveInsights({ insights, loading }: ExecutiveInsightsProps) {
  return (
    <div className="rounded border border-border bg-surface p-5">
      <div className="mb-4 flex items-center gap-2">
        <Lightbulb className="h-4 w-4 text-warning" />
        <h3 className="text-sm font-semibold text-text">Insights Ejecutivos</h3>
        {insights && (
          <span className="ml-auto rounded bg-surface-2 px-2 py-0.5 text-2xs text-text-muted">
            {insights.length}
          </span>
        )}
      </div>

      <div className="space-y-3">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="rounded border border-border p-4">
              <SkeletonBlock className="mb-2 h-4 w-3/4" />
              <SkeletonBlock className="h-3 w-full" />
            </div>
          ))
        ) : insights && insights.length > 0 ? (
          insights.slice(0, 4).map((insight) => (
            <InsightCard key={insight.id} insight={insight} />
          ))
        ) : (
          <p className="py-4 text-center text-sm text-text-subtle">
            Sin insights disponibles
          </p>
        )}
      </div>
    </div>
  )
}
