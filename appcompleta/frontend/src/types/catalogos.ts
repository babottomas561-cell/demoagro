export interface CatalogEmpresa {
  id: number
  codigo: string
  nombre: string
  razon_social: string
  provincia_base: string
}

export interface CatalogCampania {
  id: number
  codigo: string
  nombre: string
  fecha_inicio: string
  fecha_fin: string
  estado: string
  activa: boolean
}

export interface CatalogEstablecimiento {
  id: number
  codigo: string
  nombre: string
  empresa_id: number
  provincia: string
  localidad: string | null
  superficie_total_ha: number
  packhouse_activo: boolean
  lat: number | null
  lon: number | null
}

export interface CatalogCampo {
  id: number
  codigo: string
  nombre: string
  establecimiento_id: number
  superficie_ha: number
}

export interface CatalogLote {
  id: number
  codigo: string
  nombre: string
  campo_id: number
  superficie_ha: number
  anio_plantacion: number
}

export interface CatalogVariedad {
  id: number
  codigo: string
  nombre: string
  grupo: string
  destino_preferido: string | null
}

export interface CatalogCliente {
  id: number
  codigo: string
  nombre: string
  tipo: string
  pais: string
  region: string | null
}

export interface CatalogMercado {
  id: number
  codigo: string
  nombre: string
  region: string
  moneda: string
}

export interface CatalogCanal {
  id: number
  codigo: string
  nombre: string
}

export interface CatalogLinea {
  id: number
  codigo: string
  nombre: string
  establecimiento_id: number
  capacidad_tn_hora: number
}

export interface CatalogTurno {
  id: number
  codigo: string
  nombre: string
}

export interface CatalogDestino {
  id: number
  codigo: string
  nombre: string
  es_comercial: boolean
}

export interface CatalogCalibre {
  id: number
  codigo: string
  nombre: string
  apto_exportacion: boolean
}

export interface CatalogMoneda {
  id: string
  codigo: string
  nombre: string
}

export interface CatalogosFiltros {
  empresas: CatalogEmpresa[]
  campanias: CatalogCampania[]
  establecimientos: CatalogEstablecimiento[]
  campos: CatalogCampo[]
  lotes: CatalogLote[]
  variedades: CatalogVariedad[]
  clientes: CatalogCliente[]
  mercados: CatalogMercado[]
  canales: CatalogCanal[]
  lineas: CatalogLinea[]
  turnos: CatalogTurno[]
  destinos: CatalogDestino[]
  calibres: CatalogCalibre[]
  monedas: CatalogMoneda[]
}
