'use client'

import { Suspense, useEffect } from 'react'
import { usePathname } from 'next/navigation'
import { Sidebar } from '@/components/layout/Sidebar'
import { Topbar } from '@/components/layout/Topbar'
import { LayoutProvider, useLayout } from '@/context/LayoutContext'

// ─────────────────────────────────────────────────────────────────
// Inner shell — necesita LayoutContext
// ─────────────────────────────────────────────────────────────────
function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  const { sidebarCollapsed, sidebarOpen, openMobileSidebar, closeMobileSidebar } = useLayout()

  useEffect(() => { closeMobileSidebar() }, [pathname, closeMobileSidebar])

  return (
    // CSS custom property controla el offset en desktop
    <div
      className="min-h-screen bg-background"
      style={{ '--sidebar-w': sidebarCollapsed ? '60px' : '224px' } as React.CSSProperties}
    >

      {/* Desktop sidebar — fija, ancho transicionable */}
      <aside className="sidebar-desktop">
        <Sidebar />
      </aside>

      {/* Área de contenido — se desplaza según sidebar */}
      <div className="content-wrap">
        <div className="sticky top-0 z-40">
          <Suspense fallback={<div className="h-14 border-b border-border bg-surface" />}>
            <Topbar onOpenSidebar={openMobileSidebar} />
          </Suspense>
        </div>
        <main>{children}</main>
      </div>

      {/* Mobile overlay */}
      <div
        aria-hidden="true"
        onClick={closeMobileSidebar}
        className={[
          'fixed inset-0 z-40 bg-[#1c1c18]/35 backdrop-blur-[1px]',
          'transition-opacity duration-200 lg:hidden',
          sidebarOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none',
        ].join(' ')}
      />

      {/* Mobile drawer */}
      <aside
        aria-label="Menú de navegación"
        className={[
          'fixed inset-y-0 left-0 z-50 w-[17rem] max-w-[85vw]',
          'transform transition-transform duration-200 ease-out lg:hidden',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        ].join(' ')}
      >
        <Sidebar onNavigate={closeMobileSidebar} forceExpanded />
      </aside>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────
// Public export — envuelve en Provider
// ─────────────────────────────────────────────────────────────────
export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <LayoutProvider>
      <Shell>{children}</Shell>
    </LayoutProvider>
  )
}
