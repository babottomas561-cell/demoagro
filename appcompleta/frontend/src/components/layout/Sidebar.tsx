'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  LayoutDashboard, Trees, ShieldCheck, Factory,
  Bug, Droplets, Ship, Globe, Leaf, Building2, ChevronLeft,
} from 'lucide-react'
import clsx from 'clsx'
import { useLayout } from '@/context/LayoutContext'

const navItems = [
  { href: '/gerencia', label: 'Gerencia General', icon: LayoutDashboard },
  { href: '/produccion', label: 'Producción de Campo', icon: Trees },
  { href: '/calidad', label: 'Calidad de Fruta', icon: ShieldCheck },
  { href: '/packhouse', label: 'Packhouse', icon: Factory },
  { href: '/sanidad', label: 'Sanidad y Monitoreo', icon: Bug },
  { href: '/riego', label: 'Riego y Fertirriego', icon: Droplets },
  { href: '/comercial-exportacion', label: 'Comercial / Exportación', icon: Ship },
  { href: '/macro-mercado', label: 'Macro / Mercado', icon: Globe },
]

interface SidebarProps {
  onNavigate?: () => void
  forceExpanded?: boolean  // Mobile drawer: siempre expandido
}

export function Sidebar({ onNavigate, forceExpanded }: SidebarProps) {
  const pathname = usePathname()
  const { sidebarCollapsed, toggleSidebarCollapsed } = useLayout()

  const collapsed = forceExpanded ? false : sidebarCollapsed

  return (
    <aside
      className="flex flex-col h-full overflow-hidden"
      style={{ background: 'linear-gradient(180deg, #183626 0%, #12291d 52%, #102319 100%)' }}
    >
      {/* ── Logo ────────────────────────────────────────── */}
      <div className={clsx(
        'flex items-center border-b border-white/[0.07] shrink-0',
        collapsed ? 'justify-center px-0 py-4' : 'gap-3 px-5 py-4'
      )}>
        <div
          className="flex items-center justify-center w-8 h-8 rounded-lg shrink-0"
          style={{ background: 'rgba(255,255,255,0.09)' }}
        >
          <Leaf size={16} className="text-green-300" />
        </div>
        {!collapsed && (
          <div className="min-w-0 overflow-hidden">
            <p className="text-sm font-semibold text-white tracking-tight truncate">Lemon BI</p>
            <p className="text-[10px] text-green-300/55 font-medium truncate">Operación limonera diaria</p>
          </div>
        )}
      </div>

      {/* ── Nav ─────────────────────────────────────────── */}
      <nav className={clsx(
        'flex-1 py-4 space-y-0.5 overflow-y-auto overflow-x-hidden',
        collapsed ? 'px-1.5' : 'px-3'
      )}>
        {!collapsed && (
          <p className="px-2 mb-3 text-[9px] font-bold uppercase tracking-[0.14em] text-green-300/38 whitespace-nowrap">
            Módulos
          </p>
        )}

        {navItems.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href || pathname.startsWith(href + '/')
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              title={collapsed ? label : undefined}
              className={clsx(
                'group flex items-center rounded-lg text-[13px] font-medium',
                'transition-all duration-100',
                collapsed
                  ? 'justify-center h-10 w-full'
                  : 'gap-2.5 px-3 py-2.5',
                isActive
                  ? 'text-white'
                  : 'text-green-100/55 hover:text-green-50/90 hover:bg-white/[0.05]'
              )}
              style={isActive ? { background: 'linear-gradient(90deg, rgba(255,255,255,0.12), rgba(255,255,255,0.08))', boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' } : {}}
            >
              <Icon
                size={collapsed ? 18 : 15}
            className={clsx(
              'shrink-0 transition-colors',
              isActive ? 'text-green-300' : 'text-green-400/45 group-hover:text-green-300/70'
            )}
          />
              {!collapsed && <span className="flex-1 truncate">{label}</span>}
            </Link>
          )
        })}
      </nav>

      {/* ── Footer ──────────────────────────────────────── */}
      <div className={clsx(
        'shrink-0 border-t border-white/[0.08]',
        collapsed ? 'px-1.5 py-3' : 'px-3 py-4'
      )}>
        {!collapsed && (
          <div
            className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg mb-2"
            style={{ background: 'rgba(255,255,255,0.06)' }}
          >
            <div
              className="flex items-center justify-center w-7 h-7 rounded-md shrink-0"
              style={{ background: 'rgba(255,255,255,0.08)' }}
            >
              <Building2 size={13} className="text-green-300/70" />
            </div>
            <div className="min-w-0">
              <p className="text-[12px] font-medium text-white/85 truncate">Lemon Intelligence SA</p>
              <p className="text-[10px] text-green-300/52 truncate">Campaña activa 2025/2026</p>
            </div>
          </div>
        )}

        {/* Botón colapsar — solo en desktop (forceExpanded = mobile) */}
        {!forceExpanded && (
          <button
            onClick={toggleSidebarCollapsed}
            title={collapsed ? 'Expandir menú' : 'Colapsar menú'}
            className={clsx(
              'flex items-center justify-center w-full rounded-lg transition-all duration-100',
              'text-green-300/40 hover:text-green-300/80 hover:bg-white/[0.06]',
              collapsed ? 'h-9' : 'h-8 gap-2 px-3'
            )}
          >
            <ChevronLeft
              size={14}
              className={clsx(
                'shrink-0 transition-transform duration-200',
                collapsed && 'rotate-180'
              )}
            />
            {!collapsed && (
              <span className="text-[11px] font-medium">Colapsar</span>
            )}
          </button>
        )}
      </div>
    </aside>
  )
}

export default Sidebar
