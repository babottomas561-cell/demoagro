'use client'

import { Database } from 'lucide-react'

interface MockDataBannerProps {
  className?: string
}

/**
 * Shown when backend is unreachable and mock/demo data is displayed.
 * Compact inline banner — does not block content.
 */
export function MockDataBanner({ className }: MockDataBannerProps) {
  return (
    <div
      className={`flex items-center gap-2 rounded-xl border border-amber-200/70 bg-amber-50/80 px-3.5 py-2.5 text-sm text-amber-800 ${className ?? ''}`}
      role="status"
    >
      <Database className="h-3.5 w-3.5 shrink-0 opacity-70" />
      <span className="text-xs font-medium">
        Backend no disponible — datos de demostración (mock)
      </span>
    </div>
  )
}
