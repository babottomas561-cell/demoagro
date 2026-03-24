'use client'

import { useMemo } from 'react'
import { useCatalogFilters } from '@/hooks/useCatalogFilters'
import type { QueryFilters } from '@/hooks/usePageFilters'

interface ScopeBadge {
  label: string
  value: string
}

interface ExecutiveScope {
  label: string
  badges: ScopeBadge[]
}

const PERIOD_LABELS: Record<string, string> = {
  '7D': '7 días',
  '30D': '30 días',
  '90D': '90 días',
  YTD: 'YTD',
  '12M': '12 meses',
  ALL: 'Todo',
}

const VISTA_LABELS: Record<string, string> = {
  consolidada: 'Consolidado',
  detalle: 'Detalle',
}

export function useExecutiveScope(filters: QueryFilters): ExecutiveScope {
  const { data } = useCatalogFilters()

  return useMemo(() => {
    const empresa = data.empresas.find((item) => item.id === Number(filters.empresa_id))
    const campaniaSeleccionada = data.campanias.find((item) => item.id === Number(filters.campania_id))
    const campaniaActiva = data.campanias.find((item) => item.activa) ?? data.campanias[0]
    const campania = campaniaSeleccionada ?? campaniaActiva
    const establecimiento = data.establecimientos.find((item) => item.id === Number(filters.establecimiento_id))
    const campo = data.campos.find((item) => item.id === Number(filters.campo_id))
    const lote = data.lotes.find((item) => item.id === Number(filters.lote_id))
    const variedad = data.variedades.find((item) => item.id === Number(filters.variedad_id))
    const cliente = data.clientes.find((item) => item.id === Number(filters.cliente_id))
    const mercado = data.mercados.find((item) => item.id === Number(filters.mercado_id))
    const canal = data.canales.find((item) => item.id === Number(filters.canal_id))
    const packhouse = data.establecimientos.find((item) => item.id === Number(filters.packhouse_id))
    const linea = data.lineas.find((item) => item.id === Number(filters.linea_id))
    const turno = data.turnos.find((item) => item.id === Number(filters.turno_id))
    const destino = data.destinos.find((item) => item.id === Number(filters.destino_id))
    const calibre = data.calibres.find((item) => item.id === Number(filters.calibre_id))
    const moneda = data.monedas.find((item) => item.codigo === filters.moneda)

    const badges: ScopeBadge[] = []

    if (campania) badges.push({ label: 'Campaña', value: campania.nombre })
    if (empresa) badges.push({ label: 'Empresa', value: empresa.nombre })
    if (establecimiento) badges.push({ label: 'Establecimiento', value: establecimiento.nombre })
    if (campo) badges.push({ label: 'Campo', value: campo.nombre })
    if (lote) badges.push({ label: 'Lote', value: lote.nombre })
    if (variedad) badges.push({ label: 'Variedad', value: variedad.nombre })
    if (cliente) badges.push({ label: 'Cliente', value: cliente.nombre })
    if (mercado) badges.push({ label: 'Mercado', value: mercado.nombre })
    if (canal) badges.push({ label: 'Canal', value: canal.nombre })
    if (packhouse) badges.push({ label: 'Packhouse', value: packhouse.nombre })
    if (linea) badges.push({ label: 'Línea', value: linea.nombre })
    if (turno) badges.push({ label: 'Turno', value: turno.nombre })
    if (destino) badges.push({ label: 'Destino', value: destino.nombre })
    if (calibre) badges.push({ label: 'Calibre', value: calibre.nombre })
    if (filters.periodo) badges.push({ label: 'Período', value: PERIOD_LABELS[filters.periodo] ?? filters.periodo })
    if (filters.from_date) badges.push({ label: 'Desde', value: filters.from_date })
    if (filters.to_date) badges.push({ label: 'Hasta', value: filters.to_date })
    if (filters.vista) badges.push({ label: 'Vista', value: VISTA_LABELS[filters.vista] ?? filters.vista })
    if (moneda) badges.push({ label: 'Moneda', value: moneda.codigo })

    if (badges.length === 1 && campania) {
      badges.push({ label: 'Vista', value: 'Consolidado' })
    }

    let label = 'Vista consolidada del negocio limonero'
    if (lote) label = `Foco puntual en ${lote.nombre}`
    else if (campo) label = `Foco operativo en ${campo.nombre}`
    else if (establecimiento) label = `Foco en ${establecimiento.nombre}`
    else if (mercado) label = `Lectura enfocada en ${mercado.nombre}`
    else if (cliente) label = `Lectura enfocada en ${cliente.nombre}`

    if (campania) {
      label = `${label} · Campaña ${campania.nombre}`
    }

    return { label, badges }
  }, [data, filters])
}
