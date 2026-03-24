'use client'

import { startTransition, useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { ChevronDown, SlidersHorizontal } from 'lucide-react'
import clsx from 'clsx'
import { MoreFiltersDrawer, type DrawerFilterConfig } from '@/components/filters/MoreFiltersDrawer'
import { useCatalogFilters } from '@/hooks/useCatalogFilters'
import type { FilterKey } from '@/hooks/usePageFilters'

interface GlobalFilterBarProps {
  filterKeys: FilterKey[]
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: string
  options: { value: string; label: string }[]
  onChange: (value: string) => void
}) {
  const hasSelectedOption = !value || options.some((option) => option.value === value)

  return (
    <div className="relative min-w-[148px] max-w-[212px] shrink-0">
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className={clsx(
          'h-10 w-full appearance-none rounded-xl border border-[#e5dccd] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(248,244,236,0.94))] px-3 py-0 pr-8 text-xs font-medium text-text-muted shadow-[0_1px_0_rgba(24,20,12,0.02)] transition-colors',
          'hover:border-[#d9cfbf] hover:text-text focus:border-primary-500 focus:outline-none',
          value && 'border-primary-300/70 text-text'
        )}
      >
        <option value="">{label}: Todos</option>
        {!hasSelectedOption && <option value={value}>{label}: Seleccionado</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <ChevronDown className="pointer-events-none absolute right-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-subtle" />
    </div>
  )
}

export function GlobalFilterBar({ filterKeys }: GlobalFilterBarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const { data } = useCatalogFilters()
  const [drawerOpen, setDrawerOpen] = useState(false)

  const values = Object.fromEntries(filterKeys.map((key) => [key, searchParams.get(key) ?? ''])) as Record<string, string>

  const empresaId = values.empresa_id ?? ''
  const establecimientoId = values.establecimiento_id ?? ''
  const campoId = values.campo_id ?? ''
  const packhouseId = values.packhouse_id ?? ''

  const establecimientos = useMemo(
    () =>
      (data?.establecimientos ?? []).filter((item) => {
        if (!empresaId) return true
        return item.empresa_id === Number(empresaId)
      }),
    [data?.establecimientos, empresaId]
  )

  const campos = useMemo(
    () =>
      (data?.campos ?? []).filter((item) => {
        if (!establecimientoId) return true
        return item.establecimiento_id === Number(establecimientoId)
      }),
    [data?.campos, establecimientoId]
  )

  const lotes = useMemo(
    () =>
      (data?.lotes ?? []).filter((item) => {
        if (!campoId) return true
        return item.campo_id === Number(campoId)
      }),
    [data?.lotes, campoId]
  )

  const packhouses = useMemo(
    () => (data?.establecimientos ?? []).filter((item) => item.packhouse_activo),
    [data?.establecimientos]
  )

  const lineas = useMemo(
    () =>
      (data?.lineas ?? []).filter((item) => {
        if (!packhouseId) return true
        return item.establecimiento_id === Number(packhouseId)
      }),
    [data?.lineas, packhouseId]
  )

  const updateParam = (key: string, value: string) => {
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
    if (key === 'packhouse_id') {
      params.delete('linea_id')
    }

    const query = params.toString()
    startTransition(() => {
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
    })
  }

  const clearParams = (keys: string[]) => {
    const params = new URLSearchParams(searchParams.toString())
    keys.forEach((key) => params.delete(key))
    const query = params.toString()
    startTransition(() => {
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
    })
  }

  const extraFilters: DrawerFilterConfig[] = useMemo(
    () => [
      {
        key: 'periodo',
        label: 'Período',
        options: [
          { value: '7D', label: '7 días' },
          { value: '30D', label: '30 días' },
          { value: '90D', label: '90 días' },
          { value: 'YTD', label: 'Año actual' },
          { value: '12M', label: '12 meses' },
          { value: 'ALL', label: 'Todo' },
        ],
      },
      {
        key: 'vista',
        label: 'Vista',
        options: [
          { value: 'consolidada', label: 'Consolidada' },
          { value: 'detalle', label: 'Detalle' },
        ],
      },
      {
        key: 'cliente_id',
        label: 'Cliente',
        options: (data?.clientes ?? []).map((item) => ({ value: String(item.id), label: item.nombre })),
      },
      {
        key: 'mercado_id',
        label: 'Mercado',
        options: (data?.mercados ?? []).map((item) => ({ value: String(item.id), label: item.nombre })),
      },
      {
        key: 'canal_id',
        label: 'Canal',
        options: (data?.canales ?? []).map((item) => ({ value: String(item.id), label: item.nombre })),
      },
      {
        key: 'packhouse_id',
        label: 'Packhouse',
        options: packhouses.map((item) => ({ value: String(item.id), label: item.nombre })),
      },
      {
        key: 'linea_id',
        label: 'Línea',
        options: lineas.map((item) => ({ value: String(item.id), label: item.nombre })),
      },
      {
        key: 'turno_id',
        label: 'Turno',
        options: (data?.turnos ?? []).map((item) => ({ value: String(item.id), label: item.nombre })),
      },
      {
        key: 'destino_id',
        label: 'Destino fruta',
        options: (data?.destinos ?? []).map((item) => ({ value: String(item.id), label: item.nombre })),
      },
      {
        key: 'calibre_id',
        label: 'Calibre',
        options: (data?.calibres ?? []).map((item) => ({ value: String(item.id), label: item.nombre })),
      },
      {
        key: 'moneda',
        label: 'Moneda',
        options: (data?.monedas ?? []).map((item) => ({ value: item.codigo, label: item.nombre })),
      },
    ],
    [data?.calibres, data?.canales, data?.clientes, data?.destinos, data?.mercados, data?.monedas, data?.turnos, lineas, packhouses]
  )

  const extraFilterCount = extraFilters.filter((filter) => !!values[filter.key]).length

  return (
    <>
      <div className="flex items-center gap-2 overflow-x-auto rounded-[1.35rem] border border-[#e8dfd1] bg-white/65 p-2 shadow-[0_1px_0_rgba(24,20,12,0.03)] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
        {filterKeys.includes('empresa_id') && (
          <FilterSelect
            label="Empresa"
            value={values.empresa_id ?? ''}
            options={(data?.empresas ?? []).map((item) => ({ value: String(item.id), label: item.nombre }))}
            onChange={(value) => updateParam('empresa_id', value)}
          />
        )}

        {filterKeys.includes('campania_id') && (
          <FilterSelect
            label="Campaña"
            value={values.campania_id ?? ''}
            options={(data?.campanias ?? []).map((item) => ({ value: String(item.id), label: item.nombre }))}
            onChange={(value) => updateParam('campania_id', value)}
          />
        )}

        {filterKeys.includes('establecimiento_id') && (
          <FilterSelect
            label="Establecimiento"
            value={values.establecimiento_id ?? ''}
            options={establecimientos.map((item) => ({ value: String(item.id), label: item.nombre }))}
            onChange={(value) => updateParam('establecimiento_id', value)}
          />
        )}

        {filterKeys.includes('campo_id') && (
          <FilterSelect
            label="Campo"
            value={values.campo_id ?? ''}
            options={campos.map((item) => ({ value: String(item.id), label: item.nombre }))}
            onChange={(value) => updateParam('campo_id', value)}
          />
        )}

        {filterKeys.includes('lote_id') && (
          <FilterSelect
            label="Lote"
            value={values.lote_id ?? ''}
            options={lotes.map((item) => ({ value: String(item.id), label: item.nombre }))}
            onChange={(value) => updateParam('lote_id', value)}
          />
        )}

        {filterKeys.includes('variedad_id') && (
          <FilterSelect
            label="Variedad"
            value={values.variedad_id ?? ''}
            options={(data?.variedades ?? []).map((item) => ({ value: String(item.id), label: item.nombre }))}
            onChange={(value) => updateParam('variedad_id', value)}
          />
        )}

        <button
          type="button"
          onClick={() => setDrawerOpen(true)}
          title="Más filtros"
          className={clsx(
            'inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-xl border border-[#e5dccd] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(248,244,236,0.94))] px-3',
            'text-text-muted shadow-[0_1px_0_rgba(24,20,12,0.02)] transition-colors hover:border-[#d9cfbf] hover:text-text'
          )}
        >
          <SlidersHorizontal className="h-3.5 w-3.5" />
          <span className="hidden text-xs font-medium sm:inline">Más filtros</span>
          {extraFilterCount > 0 ? (
            <span className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary-600 px-1.5 text-[10px] font-bold text-white">
              {extraFilterCount}
            </span>
          ) : null}
        </button>
      </div>

      <MoreFiltersDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        values={values}
        filters={extraFilters}
        onChange={updateParam}
        onClear={clearParams}
      />
    </>
  )
}
