'use client'

import { createContext, useCallback, useContext, useEffect, useState } from 'react'

interface LayoutContextValue {
  sidebarCollapsed: boolean      // Desktop: mini mode (solo iconos)
  sidebarOpen: boolean           // Mobile: drawer abierto
  compactMode: boolean           // Toda la app: padding reducido, fuente más pequeña
  toggleSidebarCollapsed: () => void
  openMobileSidebar: () => void
  closeMobileSidebar: () => void
  toggleCompactMode: () => void
}

const LayoutContext = createContext<LayoutContextValue | null>(null)

const STORAGE_KEYS = {
  sidebarCollapsed: 'agro:sidebar-collapsed',
  compactMode: 'agro:compact-mode',
} as const

export function LayoutProvider({ children }: { children: React.ReactNode }) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [compactMode, setCompactMode] = useState(false)
  const [hydrated, setHydrated] = useState(false)

  // Restore preferences from localStorage (only client-side)
  useEffect(() => {
    setSidebarCollapsed(localStorage.getItem(STORAGE_KEYS.sidebarCollapsed) === 'true')
    setCompactMode(localStorage.getItem(STORAGE_KEYS.compactMode) === 'true')
    setHydrated(true)
  }, [])

  // Apply compact mode to <html> so CSS can react
  useEffect(() => {
    if (!hydrated) return
    document.documentElement.classList.toggle('compact', compactMode)
  }, [compactMode, hydrated])

  const toggleSidebarCollapsed = useCallback(() => {
    setSidebarCollapsed((prev) => {
      const next = !prev
      localStorage.setItem(STORAGE_KEYS.sidebarCollapsed, String(next))
      return next
    })
  }, [])

  const openMobileSidebar = useCallback(() => setSidebarOpen(true), [])
  const closeMobileSidebar = useCallback(() => setSidebarOpen(false), [])

  const toggleCompactMode = useCallback(() => {
    setCompactMode((prev) => {
      const next = !prev
      localStorage.setItem(STORAGE_KEYS.compactMode, String(next))
      return next
    })
  }, [])

  return (
    <LayoutContext.Provider
      value={{
        sidebarCollapsed,
        sidebarOpen,
        compactMode,
        toggleSidebarCollapsed,
        openMobileSidebar,
        closeMobileSidebar,
        toggleCompactMode,
      }}
    >
      {children}
    </LayoutContext.Provider>
  )
}

// Defaults seguros para SSR / Fast Refresh — evita crash si el Provider
// no está montado todavía (puede ocurrir durante Hot Module Replacement)
const SAFE_DEFAULTS: LayoutContextValue = {
  sidebarCollapsed:        false,
  sidebarOpen:             false,
  compactMode:             false,
  toggleSidebarCollapsed:  () => {},
  openMobileSidebar:       () => {},
  closeMobileSidebar:      () => {},
  toggleCompactMode:       () => {},
}

export function useLayout(): LayoutContextValue {
  return useContext(LayoutContext) ?? SAFE_DEFAULTS
}
