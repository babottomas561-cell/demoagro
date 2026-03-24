'use client'

import { startTransition, useEffect, useRef } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useSWRConfig } from 'swr'
import { Menu, RefreshCw, Minimize2, Maximize2 } from 'lucide-react'
import { GlobalFilterBar } from '@/components/filters/GlobalFilterBar'
import { useCatalogFilters } from '@/hooks/useCatalogFilters'
import { useLayout } from '@/context/LayoutContext'
import type { FilterKey } from '@/hooks/usePageFilters'

// ─────────────────────────────────────────────────────────────────
// Filtros disponibles por ruta
// ─────────────────────────────────────────────────────────────────
const ROUTE_FILTERS: Array<{ match: RegExp; keys: FilterKey[] }> = [
  { match: /^\/gerencia/, keys: ['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'] },
  { match: /^\/produccion/, keys: ['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'] },
  { match: /^\/calidad/, keys: ['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'] },
  { match: /^\/packhouse/, keys: ['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'] },
  { match: /^\/sanidad/, keys: ['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'] },
  { match: /^\/riego/, keys: ['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'] },
  { match: /^\/comercial-exportacion/, keys: ['empresa_id', 'campania_id', 'establecimiento_id', 'campo_id', 'lote_id', 'variedad_id'] },
  { match: /^\/macro-mercado/, keys: ['empresa_id', 'campania_id'] },
]

// ─────────────────────────────────────────────────────────────────
// Acciones del Topbar (refresh + compacto + avatar)
// ─────────────────────────────────────────────────────────────────
function TopbarActions({ compact = false, onRefresh }: { compact?: boolean; onRefresh: () => void }) {
  const { compactMode, toggleCompactMode } = useLayout()

  return (
    <div className="flex items-center gap-1.5">
      {/* Indicador sincronizado (solo desktop) */}
      {!compact && (
        <div className="hidden items-center gap-1.5 rounded-xl border border-[#e6ddcf] bg-white/75 px-3 py-2 text-[11px] font-medium text-text-muted shadow-[0_1px_0_rgba(24,20,12,0.03)] sm:flex">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary-500" />
          Sincronizado
        </div>
      )}

      {/* Modo compacto toggle (solo desktop) */}
      {!compact && (
        <button
          onClick={toggleCompactMode}
          title={compactMode ? 'Vista normal' : 'Vista compacta'}
          className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#e6ddcf] bg-white/75 text-text-muted shadow-[0_1px_0_rgba(24,20,12,0.03)] transition-all hover:border-[#d8cebf] hover:text-text"
          aria-label={compactMode ? 'Vista normal' : 'Vista compacta'}
        >
          {compactMode ? <Maximize2 size={13} /> : <Minimize2 size={13} />}
        </button>
      )}

      {/* Refresh */}
      <button
        onClick={onRefresh}
        className="flex h-9 w-9 items-center justify-center rounded-xl border border-[#e6ddcf] bg-white/75 text-text-muted shadow-[0_1px_0_rgba(24,20,12,0.03)] transition-all hover:border-[#d8cebf] hover:text-text"
        aria-label="Actualizar datos"
      >
        <RefreshCw size={13} />
      </button>

      {/* Avatar */}
      <div className="flex h-9 w-9 items-center justify-center rounded-full border border-primary-200 bg-primary-50 text-xs font-bold text-primary-700 shadow-[0_1px_0_rgba(24,20,12,0.03)] select-none">
        LB
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────
// Badge de filtros activos
// ─────────────────────────────────────────────────────────────────
function ActiveFiltersBadge({ count }: { count: number }) {
  if (count === 0) return null
  return (
    <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-500 px-1.5 text-[10px] font-bold text-white">
      {count}
    </span>
  )
}

// ─────────────────────────────────────────────────────────────────
// Topbar principal
// ─────────────────────────────────────────────────────────────────
export function Topbar({ onOpenSidebar }: { onOpenSidebar?: () => void }) {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { mutate } = useSWRConfig()
  const { data } = useCatalogFilters()
  const autoCampaignPathRef = useRef<string | null>(null)

  const activeFilterKeys = ROUTE_FILTERS.find((r) => r.match.test(pathname))?.keys ?? []

  const campaniaId = searchParams.get('campania_id') ?? ''

  // Cuenta cuántos filtros tienen valor seleccionado
  const activeFilterCount = activeFilterKeys.filter((k) => !!searchParams.get(k)).length

  const updateParam = (key: FilterKey, value: string) => {
    const params = new URLSearchParams(searchParams.toString())
    if (value) params.set(key, value)
    else params.delete(key)
    if (key === 'campania_id') {
      ;[
        'campo_id',
        'lote_id',
        'cliente_id',
        'mercado_id',
        'canal_id',
        'packhouse_id',
        'linea_id',
        'turno_id',
        'destino_id',
        'calibre_id',
        'from_date',
        'to_date',
      ].forEach((filterKey) => params.delete(filterKey))
    }
    if (key === 'empresa_id') {
      params.delete('establecimiento_id')
      params.delete('campo_id')
      params.delete('lote_id')
      params.delete('packhouse_id')
      params.delete('linea_id')
    }
    if (key === 'establecimiento_id') {
      params.delete('campo_id')
      params.delete('lote_id')
    }
    if (key === 'campo_id') {
      params.delete('lote_id')
    }
    const query = params.toString()
    startTransition(() => {
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
    })
  }

  const handleRefresh = () => {
    mutate((key) => typeof key === 'string' && key.startsWith('/'))
  }

  // Auto-seleccionar campaña activa al entrar en rutas que la usan
  useEffect(() => {
    if (autoCampaignPathRef.current !== pathname) autoCampaignPathRef.current = null
    if (!activeFilterKeys.includes('campania_id')) return
    if (campaniaId) return
    if (autoCampaignPathRef.current === pathname) return

    const activeCampaign =
      data?.campanias?.find((c) => c.activa) ?? data?.campanias?.[0]
    if (!activeCampaign) return

    autoCampaignPathRef.current = pathname
    updateParam('campania_id', String(activeCampaign.id))
  }, [activeFilterKeys, campaniaId, data?.campanias, pathname])

  return (
    <div className="sticky top-0 z-40 border-b border-[#e6ddcf] bg-[rgba(255,253,249,0.82)] backdrop-blur-md shadow-[0_1px_0_rgba(0,0,0,0.04)]">
      <div className="mx-auto max-w-[1400px] px-3 py-2.5 sm:px-5">

        {/* ── Fila mobile: hamburger + badge + acciones ── */}
        <div className="flex items-center justify-between gap-2 lg:hidden">
          <div className="flex items-center gap-2">
            <button
              onClick={onOpenSidebar}
              aria-label="Abrir menú"
              className="inline-flex h-9 w-9 items-center justify-center rounded-xl border border-[#e6ddcf] bg-white/75 text-text shadow-[0_1px_0_rgba(24,20,12,0.03)]"
            >
              <Menu className="h-4 w-4" />
            </button>

            {/* Badge de filtros activos en mobile */}
            <div className="flex items-center gap-1.5">
              <span className="text-[12px] font-medium text-text-muted">Lemon BI</span>
              <ActiveFiltersBadge count={activeFilterCount} />
            </div>
          </div>

          <TopbarActions compact onRefresh={handleRefresh} />
        </div>

        {/* ── Filtros en mobile (debajo del hamburger) ── */}
        {activeFilterKeys.length > 0 && (
          <div className="mt-2.5 lg:hidden">
            <GlobalFilterBar filterKeys={activeFilterKeys} />
          </div>
        )}

        {/* ── Fila desktop: filtros + acciones en una línea ── */}
        <div className="hidden lg:flex lg:items-center lg:justify-between lg:gap-4">
          <div className="min-w-0 flex-1">
            <GlobalFilterBar filterKeys={activeFilterKeys} />
          </div>
          <div className="shrink-0">
            <TopbarActions onRefresh={handleRefresh} />
          </div>
        </div>
      </div>
    </div>
  )
}

export default Topbar
