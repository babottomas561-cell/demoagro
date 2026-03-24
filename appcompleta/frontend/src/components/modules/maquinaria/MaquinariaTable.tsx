'use client'

import { useMemo } from 'react'
import { Truck, Clock, DollarSign, Wrench } from 'lucide-react'
import type { ColDef } from 'ag-grid-community'
import { AgGridWrapper } from '@/components/tables/AgGrid'
import { Badge } from '@/components/ui/Badge'
import { KPICard } from '@/components/ui/KPICard'
import { formatCurrency, formatNumber } from '@/lib/formatters'
import type { MaquinariaData, Maquina } from '@/types/maquinaria'

interface MaquinariaTableProps {
  data?: MaquinariaData
  loading?: boolean
}

const estadoConfig: Record<string, 'success' | 'warning' | 'danger'> = {
  operativo: 'success',
  en_reparacion: 'warning',
  fuera_de_servicio: 'danger',
}

const estadoLabel: Record<string, string> = {
  operativo: 'Operativo',
  en_reparacion: 'En reparación',
  fuera_de_servicio: 'Fuera de servicio',
}

const alertaDias: Record<string, string> = {
  verde: 'text-accent',
  amarillo: 'text-warning',
  rojo: 'text-danger',
}

export function MaquinariaTable({ data, loading }: MaquinariaTableProps) {
  const columnDefs = useMemo<ColDef<Maquina>[]>(() => [
    {
      field: 'nombre',
      headerName: 'Equipo',
      flex: 1.5,
      minWidth: 150,
      cellStyle: { fontWeight: '500' },
    },
    {
      field: 'tipo',
      headerName: 'Tipo',
      flex: 1,
      minWidth: 100,
    },
    {
      field: 'marca',
      headerName: 'Marca / Modelo',
      flex: 1.3,
      minWidth: 130,
      valueGetter: (p) => `${p.data?.marca} ${p.data?.modelo}`,
    },
    {
      field: 'anio',
      headerName: 'Año',
      flex: 0.6,
      minWidth: 70,
    },
    {
      field: 'estado',
      headerName: 'Estado',
      flex: 1,
      minWidth: 120,
      cellRenderer: (p: { value: string }) => {
        const label = estadoLabel[p.value] || p.value
        return <Badge variant={estadoConfig[p.value] || 'warning'}>{label}</Badge>
      },
    },
    {
      field: 'horas_totales',
      headerName: 'Horas Totales',
      flex: 1,
      minWidth: 110,
      valueFormatter: (p) => p.value != null ? `${formatNumber(p.value, 0)} hs` : '—',
      type: 'numericColumn',
    },
    {
      field: 'proximo_service_horas',
      headerName: 'Próx. Service (hs)',
      flex: 1,
      minWidth: 130,
      valueFormatter: (p) => p.value != null ? `${formatNumber(p.value, 0)} hs` : '—',
      type: 'numericColumn',
    },
    {
      field: 'dias_para_service',
      headerName: 'Días p/ Service',
      flex: 0.9,
      minWidth: 110,
      cellRenderer: (p: { value: number; data: Maquina }) => {
        const colorClass = alertaDias[p.data?.alerta_service || 'verde']
        return <span className={`font-semibold tabular-nums ${colorClass}`}>{p.value ?? '—'} días</span>
      },
    },
    {
      field: 'costo_operativo_mes',
      headerName: 'Costo/Mes',
      flex: 1,
      minWidth: 110,
      valueFormatter: (p) => p.value != null ? formatCurrency(p.value) : '—',
      type: 'numericColumn',
    },
  ], [])

  return (
    <div className="space-y-4">
      {/* Summary cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KPICard
          title="Equipos Operativos"
          value={data?.summary.equipos_operativos ?? '—'}
          icon={Truck}
          loading={loading}
          trend="neutral"
          description="Disponibles para trabajo"
        />
        <KPICard
          title="Horas Promedio"
          value={data ? `${formatNumber(data.summary.horas_promedio, 0)}` : '—'}
          unit="hs"
          icon={Clock}
          loading={loading}
          trend="neutral"
          description="Promedio flota"
        />
        <KPICard
          title="Costo Operativo"
          value={data ? formatCurrency(data.summary.costo_operativo) : '—'}
          icon={DollarSign}
          loading={loading}
          trend="neutral"
          description="Mensual total"
        />
        <KPICard
          title="Próximos Services"
          value={data?.summary.proximos_services ?? '—'}
          icon={Wrench}
          loading={loading}
          trend={data && data.summary.proximos_services > 2 ? 'down' : 'neutral'}
          invertColor
          description="En los próximos 15 días"
        />
      </div>

      {/* Table */}
      <div className="rounded border border-border bg-surface p-5">
        <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <h3 className="text-sm font-semibold text-text">Flota de Maquinaria</h3>
          <div className="flex flex-wrap items-center gap-2 text-xs text-text-muted">
            <Badge variant="success">OK</Badge>
            <Badge variant="warning">Próximo service</Badge>
            <Badge variant="danger">Urgente</Badge>
          </div>
        </div>
        <div className="space-y-3 md:hidden">
          {(data?.maquinas || []).map((maquina) => (
            <div key={maquina.id} className="rounded-xl border border-border bg-surface-2 p-4">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-text">{maquina.nombre}</p>
                  <p className="text-xs text-text-muted">{maquina.tipo} · {maquina.anio}</p>
                </div>
                <Badge variant={estadoConfig[maquina.estado] || 'warning'}>
                  {estadoLabel[maquina.estado] || maquina.estado}
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-3 text-xs text-text-muted">
                <div>
                  <p className="text-text-subtle">Horas totales</p>
                  <p className="mt-1 font-medium text-text">{formatNumber(maquina.horas_totales, 0)} hs</p>
                </div>
                <div>
                  <p className="text-text-subtle">Próximo service</p>
                  <p className="mt-1 font-medium text-text">
                    {maquina.proximo_service_horas != null ? `${formatNumber(maquina.proximo_service_horas, 0)} hs` : '—'}
                  </p>
                </div>
                <div>
                  <p className="text-text-subtle">Días estimados</p>
                  <p className={`mt-1 font-medium ${alertaDias[maquina.alerta_service]}`}>{maquina.dias_para_service ?? '—'}</p>
                </div>
                <div>
                  <p className="text-text-subtle">Costo mensual</p>
                  <p className="mt-1 font-medium text-text">{formatCurrency(maquina.costo_operativo_mes)}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
        <div className="hidden md:block">
          <AgGridWrapper<Maquina>
            rowData={data?.maquinas || []}
            columnDefs={columnDefs}
            loading={loading}
            height={420}
            exportFilename="maquinaria"
          />
        </div>
      </div>
    </div>
  )
}
