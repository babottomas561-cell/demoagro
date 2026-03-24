'use client'

/**
 * DataTable
 *
 * Pre-configured AG Grid wrapper for the DemoAgro UI system.
 * Re-exports AgGridWrapper with agro-appropriate defaults and a
 * consistent import path from the `ui/` component layer.
 *
 * Usage:
 *   import { DataTable } from '@/components/ui/DataTable'
 *
 *   <DataTable
 *     rowData={lotesData}
 *     columnDefs={colDefs}
 *     exportFilename="lotes-campaña-2025"
 *   />
 */
export { AgGridWrapper as DataTable } from '@/components/tables/AgGrid'
// Re-export the AG Grid ColDef type so consumers only need one import
export type { ColDef } from 'ag-grid-community'
