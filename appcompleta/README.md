# Lemon BI — Plataforma BI para Negocio Limonero

> Plataforma de inteligencia operativa, comercial y financiera para una operación limonera del NOA argentino.
> Stack: **Next.js + FastAPI + SQLite/PostgreSQL** | Seed limonero denso + APIs externas para macro, clima y mercado.

---

## Estado actual

La app ya quedó reposicionada como producto **100% limón**.

Hoy el producto activo cubre:

- modelo de datos limonero con campañas históricas y campaña activa en curso
- seed denso y validado para visualización BI
- navegación y filtros gerenciales enfocados en limón
- ocho paneles ejecutivos simplificados para demo comercial
- backend y frontend alineados al dominio limonero

Módulos activos:

- Gerencia General
- Producción de Campo
- Calidad de Fruta
- Packhouse
- Comercial / Exportación
- Sanidad y Monitoreo
- Riego y Fertirriego
- Macro / Mercado

Nota de transición:

- el repositorio todavía conserva código legacy del dominio agro genérico, pero ya no se monta en la API activa
- la navegación activa, los catálogos y los paneles visibles ya responden al producto limonero actual
- algunos nombres técnicos internos como `demoagro.db`, `demoagro_network` o rutas legacy se conservan para no romper entornos locales ya montados
- las páginas legacy del frontend quedaron archivadas como redirects hacia los módulos limoneros activos

---

## Índice

1. [Arquitectura](#arquitectura)
2. [Modelo de Datos ERP Limonero](#modelo-de-datos-erp-limonero)
3. [Qué datos son simulados y cuáles son reales](#qué-datos-son-simulados-y-cuáles-son-reales)
4. [Fuentes externas conectadas](#fuentes-externas-conectadas)
5. [Configuración de variables de entorno](#configuración-de-variables-de-entorno)
6. [Cómo correr con Docker Compose](#cómo-correr-con-docker-compose)
7. [Cómo correr en desarrollo local (sin Docker)](#cómo-correr-en-desarrollo-local-sin-docker)
8. [Cómo refrescar cache de APIs externas](#cómo-refrescar-cache-de-apis-externas)
9. [Cómo migrar de SQLite a PostgreSQL](#cómo-migrar-de-sqlite-a-postgresql)
10. [Cómo reemplazar datos ficticios por datos reales del ERP](#cómo-reemplazar-datos-ficticios-por-datos-reales-del-erp)
11. [Cómo agregar nuevas APIs externas](#cómo-agregar-nuevas-apis-externas)
12. [Limitaciones por fuente](#limitaciones-por-fuente)
13. [Sugerencias para producción](#sugerencias-para-producción)
14. [Módulos y endpoints](#módulos-y-endpoints)

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENTE (Browser)                        │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────────────┐
│                   Next.js Frontend (port 3000)                  │
│  - App Router + TypeScript                                      │
│  - Tailwind CSS + Plotly.js + AG Grid                           │
│  - SWR para data fetching con revalidación                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ REST API calls
┌────────────────────────▼────────────────────────────────────────┐
│                   FastAPI Backend (port 8000)                   │
│  - Routers por módulo                                           │
│  - Services: datos propios (DB) + datos externos (APIs)         │
│  - Swagger UI en /docs                                          │
└──────────┬─────────────────────────────┬───────────────────────┘
           │                             │
┌──────────▼──────────┐    ┌─────────────▼───────────────────────┐
│  PostgreSQL / SQLite │    │   Capa de Integraciones Externas    │
│  (ERP limonero BI)   │    │                                     │
│  - SQLAlchemy ORM    │    │  ┌──────────────────────────────┐   │
│  - Alembic migrations│    │  │  Cache Redis (TTL por fuente) │   │
│  - Seed limonero BI  │    │  └──────────┬───────────────────┘   │
└─────────────────────┘    │             │                        │
                           │  ┌──────────▼───────────────────┐   │
                           │  │  Clientes HTTP (httpx async)  │   │
                           │  │                               │   │
                           │  │  bcra_client.py      → BCRA   │   │
                           │  │  argentina_series.py  → API   │   │
                           │  │    Datos Argentina             │   │
                           │  │  weather_client.py   → Open-  │   │
                           │  │    Meteo                       │   │
                           │  │  usda_client.py      → USDA   │   │
                           │  │  commodities_client.py→ Yahoo │   │
                           │  │  bcr_client.py       → BCR    │   │
                           │  │    (modo degradado)            │   │
                           │  └──────────────────────────────┘   │
                           └─────────────────────────────────────┘
```

### Estructura de carpetas

```
demoagro/
├── frontend/                  # Next.js 14+ / TypeScript
│   ├── src/
│   │   ├── app/               # App Router (páginas)
│   │   ├── components/        # UI, charts, tables, layouts
│   │   ├── hooks/             # Custom hooks con SWR
│   │   ├── lib/               # api.ts, formatters, constants
│   │   └── types/             # Tipos TypeScript
│   ├── Dockerfile
│   └── package.json
│
├── backend/                   # FastAPI / Python 3.11+
│   ├── app/
│   │   ├── main.py            # App FastAPI + lifespan
│   │   ├── config.py          # Pydantic Settings
│   │   ├── database.py        # SQLAlchemy async engine
│   │   ├── models/            # ORM models (SQLAlchemy)
│   │   ├── schemas/           # Pydantic schemas (request/response)
│   │   ├── routers/           # Endpoints por módulo
│   │   ├── services/          # Business logic
│   │   ├── integrations/      # Clientes APIs externas
│   │   └── seed/              # Datos ficticios del negocio
│   ├── alembic/               # Migraciones DB
│   ├── requirements.txt
│   └── Dockerfile
│
├── scripts/                   # Utilidades
│   └── init_db.sql
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Modelo de Datos ERP Limonero

La base actual está organizada en tres capas:

1. **Maestras**: estructura estable del negocio limonero.
2. **Operativas / transaccionales**: registran cosecha, calidad, packhouse, comercialización, finanzas y contexto operativo.
3. **Analítica / compatibilidad**: sostiene los datasets consumidos por paneles BI y conserva compatibilidad con partes legacy del repo.

### Diagrama lógico resumido

```text
empresa
  └── establecimiento
      ├── campo
      │   └── lote (legacy / físico transicional)
      │       ├── ambiente
      │       └── lote_campania
      │           ├── plan_siembra / ejecucion_siembra
      │           ├── plan_fertilizacion / ejecucion_fertilizacion
      │           ├── plan_pulverizacion / ejecucion_pulverizacion
      │           ├── rendimientos_lote
      │           ├── monitoreos_plagas
      │           ├── consumos_insumos
      │           ├── costos_directos
      │           └── asignaciones_costos
      ├── depositos
      │   ├── stock_actual
      │   ├── movimientos_stock
      │   ├── ingresos_insumos / salidas_insumos
      │   └── transferencias_deposito
      ├── maquinarias
      │   ├── partes_trabajo / partes_maquinaria / horas_maquina
      │   ├── consumo_combustible / downtime_maquinaria
      │   ├── mantenimientos_preventivos / mantenimientos_correctivos
      │   └── disponibilidad_equipos
      └── centros_costos / empleados / contratistas / implementos

campania
  └── presupuestos_campania
      └── presupuestos_lote (capa analítica actual)

comercial
  ├── contratos_venta / contratos_compra
  ├── entregas / fijaciones / liquidaciones
  ├── posiciones_comerciales
  ├── cuentas_cobrar / cobranzas
  └── cuentas_pagar / pagos

contexto externo
  ├── clima_diario
  ├── commodities_precios
  ├── macro_series
  └── alertas_contexto
```

### Tablas maestras

- Core existente: `empresas`, `establecimientos`, `campanias`, `cultivos`, `clientes`, `proveedores`, `productos`, `insumos`, `maquinarias`, `usuarios`
- ERP nuevas: `unidades_negocio`, `campos`, `ambientes`, `variedades`, `depositos`, `centros_costos`, `monedas`, `unidades_medida`, `empleados`, `contratistas`, `implementos`, `categorias_producto`, `labores_tipos`

### Tablas operativas / transaccionales

- Planeamiento y agronomía: `lote_campania`, `plan_siembra`, `ejecucion_siembra`, `plan_fertilizacion`, `ejecucion_fertilizacion`, `plan_pulverizacion`, `ejecucion_pulverizacion`, `rendimientos_lote`, `monitoreos_plagas`, `consumos_insumos`, `partes_trabajo`
- Stock y abastecimiento: `stock_actual`, `movimientos_stock`, `ingresos_insumos`, `salidas_insumos`, `transferencias_deposito`, `pedidos_compra`, `ordenes_compra`, `remitos`
- Comercial: `contratos_venta`, `contratos_compra`, `entregas`, `fijaciones`, `liquidaciones`, `posiciones_comerciales`
- Finanzas: `presupuestos_campania`, `costos_directos`, `costos_indirectos`, `asignaciones_costos`, `cuentas_cobrar`, `cuentas_pagar`, `pagos`, `cobranzas`
- Flota: `partes_maquinaria`, `horas_maquina`, `mantenimientos_preventivos`, `mantenimientos_correctivos`, `disponibilidad_equipos`
- Contexto: `clima_diario`, `commodities_precios`, `macro_series`, `alertas_contexto`

### Capa analítica / compatibilidad

Los dashboards actuales siguen consumiendo tablas existentes como:

- `presupuestos_lote`
- `plan_labores`
- `ejecucion_labores`
- `observaciones_campo`
- `rendimiento_por_ambiente`
- `stock_proyectado`
- `posicion_comercial`
- `service_schedule`
- `desvio_plan_real`

Estas tablas no se eliminaron porque hoy funcionan como capa de compatibilidad para la app. El rediseño agregó debajo una base más cercana a ERP real sin romper routers, services ni el frontend existente.

### Seed ERP

El seed ya no arma solo datos “de dashboard”. Ahora genera:

- múltiples campañas, establecimientos, campos, depósitos y centros de costo
- más de 50 registros `lote_campania`
- planes y ejecuciones por tipo de labor
- documentos de compra, stock y comercialización
- costos directos e indirectos asignados
- cuentas a cobrar y pagar
- partes de maquinaria y disponibilidad diaria
- series externas persistidas para clima, macro y commodities

Archivos clave:

- `backend/app/seed/run_seed.py`
- `backend/app/seed/seed_empresas.py`
- `backend/app/seed/seed_agricola.py`
- `backend/app/seed/seed_comercial.py`
- `backend/app/seed/seed_finanzas.py`
- `backend/app/seed/seed_maquinaria.py`
- `backend/app/seed/seed_decisional.py`
- `backend/app/seed/seed_erp.py`

### Nota de transición

La tabla legacy `lotes` sigue existiendo por compatibilidad y hoy mezcla datos físicos y de campaña. La tabla nueva `lote_campania` pasa a ser la referencia operativa limpia para la capa ERP. En una migración a un ERP real, el siguiente paso natural es separar un `lote` físico puro y dejar `lote_campania` como hecho operativo por campaña.

---

## Qué datos son simulados y cuáles son reales

| Módulo | Fuente | Tipo |
|--------|--------|------|
| Dashboard KPIs | Base de datos propia | **Simulado** (realista) |
| Módulo Agrícola (lotes, siembra, cosecha) | Base de datos propia | **Simulado** (realista) |
| Módulo Comercial (ventas, contratos) | Base de datos propia | **Simulado** (realista) |
| Módulo Finanzas (flujo de caja) | Base de datos propia | **Simulado** (realista) |
| Módulo Stock e Insumos | Base de datos propia | **Simulado** (realista) |
| Módulo Maquinaria | Base de datos propia | **Simulado** (realista) |
| **Tipo de cambio (oficial/mayorista)** | **API BCRA** | **REAL** |
| **Inflación (IPC mensual/interanual)** | **API BCRA + Datos Argentina** | **REAL** |
| **Tasas de referencia** | **API BCRA** | **REAL** |
| **Reservas internacionales** | **API BCRA** | **REAL** |
| **Precios commodities (soja, maíz, trigo)** | **Yahoo Finance / USDA** | **REAL** |
| **Clima y pronóstico** | **Open-Meteo** | **REAL** |
| **Producción agrícola mundial** | **USDA PSD API** | **REAL** (requiere API key) |
| Precios pizarra BCR | BCR (modo degradado) | Referencia estática documentada |

---

## Fuentes externas conectadas

### 1. BCRA — Banco Central de la República Argentina
- **URL**: https://api.bcra.gob.ar
- **Autenticación**: Ninguna (API pública)
- **Datos**: Tipo de cambio, inflación, tasas, reservas, variables monetarias
- **TTL cache**: 15-60 minutos según variable
- **Docs**: https://www.bcra.gob.ar/BCRAyVos/catalogo-de-APIs-banco-central.asp
- **Limitación**: Certificado SSL ocasionalmente problemático. El cliente usa `verify=False` con advertencia.

### 2. API de Series de Tiempo — Datos Argentina
- **URL**: https://apis.datos.gob.ar/series/api/
- **Autenticación**: Ninguna (API pública)
- **Datos**: Series temporales oficiales, IPC, tipo de cambio histórico, PBI y más
- **TTL cache**: 24 horas
- **Docs**: https://apis.datos.gob.ar/series/api/

### 3. Open-Meteo — Clima
- **URL**: https://api.open-meteo.com
- **Autenticación**: Ninguna (gratuita sin límite razonable)
- **Datos**: Pronóstico 7 días, histórico, temperatura, precipitación, humedad, viento
- **TTL cache**: 1 hora
- **Docs**: https://open-meteo.com/en/docs

### 4. USDA PSD — Datos agropecuarios mundiales
- **URL**: https://apps.fas.usda.gov/psdonline/app
- **Autenticación**: API key gratuita (registro en apps.fas.usda.gov)
- **Datos**: Producción, oferta, demanda de granos por país y año
- **TTL cache**: 24 horas
- **Variable**: `USDA_API_KEY` en `.env`
- **Sin API key**: modo degradado con datos de referencia 2024

### 5. Yahoo Finance (commodities)
- **URL**: https://query1.finance.yahoo.com (endpoint JSON público)
- **Autenticación**: Ninguna
- **Datos**: Precios futuros ZS=F (soja), ZC=F (maíz), ZW=F (trigo)
- **TTL cache**: 30 minutos
- **Limitación**: No es una API oficial. Puede cambiar sin aviso. Para producción usar Quandl, Bloomberg o similar.

### 6. BCR — Bolsa de Comercio de Rosario
- **Estado**: Modo degradado (sin API pública estable)
- **Alternativa**: Datos de referencia actualizables manualmente o via MATBA-ROFEX con credenciales
- **Variable**: `BCR_API_KEY` preparada en `.env`

---

## Configuración de variables de entorno

```bash
# 1. Copiar el archivo de ejemplo
cp .env.example .env

# 2. Completar las variables
nano .env   # o tu editor preferido
```

Variables obligatorias para el modo mínimo (sin credenciales externas):
```
APP_SECRET_KEY=<string aleatorio 32+ chars>
JWT_SECRET_KEY=<string aleatorio 32+ chars>
# El resto funciona con valores por defecto para desarrollo local
```

Variables opcionales para habilitar fuentes adicionales:
```
USDA_API_KEY=<obtener en https://apps.fas.usda.gov/psdonline>
BCR_API_KEY=<obtener de BCR si está disponible>
```

---

## Cómo correr con Docker Compose

```bash
# 1. Clonar / posicionarse en el proyecto
cd demoagro

# 2. Copiar y editar variables de entorno
cp .env.example .env

# 3. Levantar todo (DB + Redis + Backend + Frontend)
docker-compose up --build

# 4. Primera vez — el backend ejecuta automáticamente:
#    - alembic upgrade head (crea tablas)
#    - python -m app.seed.run_seed (inserta datos ficticios)

# 5. Acceder a:
#    Frontend:    http://localhost:3000
#    API Docs:    http://localhost:8000/docs
#    Backend:     http://localhost:8000

# Para correr en background:
docker-compose up -d --build

# Ver logs:
docker-compose logs -f backend
docker-compose logs -f frontend

# Parar todo:
docker-compose down

# Parar y borrar datos (DB volume):
docker-compose down -v
```

---

## Cómo correr en desarrollo local (sin Docker)

### Backend

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp ../.env.example .env
# Editar .env — para desarrollo local usar SQLite:
# DATABASE_URL=sqlite+aiosqlite:///./demoagro.db

# Crear tablas
alembic upgrade head

# Insertar datos ficticios
python -m app.seed.run_seed

# Iniciar servidor
uvicorn app.main:app --reload --port 8000

# API disponible en: http://localhost:8000
# Swagger UI en:     http://localhost:8000/docs
```

### Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Variables de entorno
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Iniciar en desarrollo
npm run dev

# App disponible en: http://localhost:3000
```

---

## Cómo refrescar cache de APIs externas

### Via endpoint REST (recomendado)

```bash
# Refrescar todos los datos externos
curl -X POST http://localhost:8000/api/cache/refresh

# Refrescar una fuente específica
curl -X POST http://localhost:8000/api/cache/refresh/bcra
curl -X POST http://localhost:8000/api/cache/refresh/commodities
curl -X POST http://localhost:8000/api/cache/refresh/clima

# Ver estado del cache
curl http://localhost:8000/api/cache/status
```

### Via Redis CLI (acceso directo)

```bash
# Entrar al container Redis
docker-compose exec redis redis-cli

# Listar todas las claves
KEYS demoagro:*

# Borrar una clave específica (fuerza refresh al próximo request)
DEL demoagro:bcra:tipo_cambio

# Borrar todo el cache de APIs externas
KEYS demoagro:ext:* | xargs DEL
```

### TTLs configurados por fuente

| Fuente | Variable `.env` | TTL por defecto |
|--------|----------------|-----------------|
| BCRA tipo de cambio | `BCRA_CACHE_TTL` | 900s (15 min) |
| BCRA tasas | — | 3600s (1 hora) |
| BCRA inflación | — | 86400s (24 hs) |
| Datos Argentina series | `DATOS_ARG_CACHE_TTL` | 86400s (24 hs) |
| Clima pronóstico | `OPENMETEO_CACHE_TTL` | 3600s (1 hora) |
| Commodities precios | — | 1800s (30 min) |
| USDA | `USDA_CACHE_TTL` | 86400s (24 hs) |

---

## Cómo migrar de SQLite a PostgreSQL

```bash
# 1. En .env cambiar:
DATABASE_URL=postgresql+asyncpg://agro_user:agro_pass@localhost:5432/demoagro

# 2. Crear la base de datos en PostgreSQL
psql -U postgres -c "CREATE DATABASE demoagro;"
psql -U postgres -c "CREATE USER agro_user WITH PASSWORD 'agro_pass';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE demoagro TO agro_user;"

# 3. Aplicar migraciones
alembic upgrade head

# 4. Re-ejecutar seed
python -m app.seed.run_seed

# Con Docker Compose: simplemente cambiar DATABASE_URL en .env
# El servicio `db` (PostgreSQL) ya está configurado en docker-compose.yml
```

La arquitectura del ORM (SQLAlchemy async) es idéntica entre SQLite y PostgreSQL. Solo cambia la `DATABASE_URL`.

---

## Cómo reemplazar datos ficticios por datos reales del ERP

El seed ficticio vive en `backend/app/seed/`. Para conectar al ERP del cliente:

### Opción A — Migración directa de datos

```bash
# 1. Exportar datos del ERP a CSV
# 2. Usar el script de importación
python scripts/import_from_csv.py --source /path/to/erp_export.csv --table ventas

# Los scripts de importación respetan el mismo schema de base de datos
```

### Opción B — Conectar directamente a la DB del ERP

```python
# backend/app/services/erp_connector.py
# (crear este archivo)

# Para SAP:
import pyrfc  # SAP PyRFC
# Para Colppy, Tango, etc:
# Usar sus APIs REST o acceso directo a PostgreSQL/SQL Server
```

### Opción C — Cambiar la capa de servicio

Los services en `backend/app/services/` son la capa de abstracción.
Reemplazar las queries SQLAlchemy por llamadas al ERP manteniendo los mismos schemas de respuesta:

```python
# Ejemplo: dashboard_service.py
# Antes (datos ficticios):
async def get_kpis(db, filtros):
    return await db.execute(select(Venta)...)

# Después (ERP real):
async def get_kpis(db, filtros):
    return await erp_client.get_ventas(filtros)
    # El schema de respuesta es idéntico → el frontend no cambia
```

---

## Cómo agregar nuevas APIs externas

1. **Crear el cliente** en `backend/app/integrations/nueva_api_client.py`:

```python
from app.integrations.base_client import BaseAPIClient

class NuevaAPIClient(BaseAPIClient):
    BASE_URL = "https://api.nueva-fuente.com"

    async def get_datos(self) -> ExternalDataResponse:
        cache_key = "nueva_api:datos"
        cached = await self.cache.get(cache_key)
        if cached:
            return ExternalDataResponse(**cached, cache_hit=True)

        try:
            response = await self.http.get(f"{self.BASE_URL}/endpoint")
            data = response.json()
            result = ExternalDataResponse(
                data=data,
                source_name="Nueva API",
                source_url=self.BASE_URL,
                fetched_at=datetime.utcnow(),
                frequency="horaria",
                status="ok"
            )
            await self.cache.set(cache_key, result.dict(), ttl=3600)
            return result
        except Exception as e:
            return ExternalDataResponse(status="error", error_message=str(e), ...)
```

2. **Registrar en `external_data_service.py`**

3. **Agregar variables de entorno** en `.env.example`

4. **Crear el endpoint** en `backend/app/routers/`

5. **Consumir desde el frontend** agregando un hook en `frontend/src/hooks/`

---

## Limitaciones por fuente

| Fuente | Limitación | Workaround |
|--------|-----------|------------|
| BCRA | SSL cert ocasionalmente inválido | `verify=False` con advertencia en logs |
| BCRA | Latencia variable (1-5s) | Cache de 15-60 min |
| Datos Argentina | Algunos IDs de series cambian | Verificar IDs en `/api/series/search/` |
| Open-Meteo | Sin SLA comercial | Para prod: agregar Open-Meteo Pro o Tomorrow.io |
| Yahoo Finance | Endpoint no oficial, puede cambiar | Para prod: usar Quandl, Alpha Vantage, Bloomberg |
| USDA | Requiere API key (registro gratuito) | Modo degradado con datos 2024 hardcodeados |
| BCR | Sin API pública estable | MATBA-ROFEX API con credenciales, o datos manuales |
| MATBA-ROFEX | Requiere cuenta institucional | Documentado en `bcr_client.py` |

---

## Sugerencias para producción

### Infraestructura

```yaml
# Reemplazar en docker-compose.prod.yml:
- SQLite → PostgreSQL 16 con replicas de lectura
- Redis single → Redis Sentinel o Cluster
- uvicorn single → gunicorn + múltiples workers uvicorn
- npm run dev → next build + next start
- Variables de entorno → AWS Secrets Manager / Vault
```

### APIs externas

- **Clima**: Open-Meteo Pro ($) o Tomorrow.io / WeatherAPI con SLA
- **Commodities**: Quandl (Nasdaq Data Link), Bloomberg API, o Refinitiv Eikon
- **Tipo de cambio**: Dólar API con múltiples fuentes o acceso directo a BCRA
- **BCR**: Gestionar credenciales de acceso institucional a MATBA-ROFEX

### Seguridad

- Implementar autenticación completa (OAuth2 / SAML) para multitenancy
- Rate limiting en FastAPI (slowapi)
- HTTPS con certificado válido
- Auditoría de accesos a datos sensibles
- Roles y permisos granulares por empresa/establecimiento

### Observabilidad

- Logs estructurados con Loguru → enviar a ELK o Datadog
- Métricas de APIs externas (latencia, hit rate del cache, errores)
- Alertas cuando una fuente externa esté caída por más de N minutos
- Dashboard de salud de integraciones en `/api/health`

### Multitenancy

La arquitectura soporta múltiples empresas desde el modelo. Para SaaS completo:
- Agregar `tenant_id` a todos los modelos
- Middleware de resolución de tenant por subdominio o header
- Aislamiento de datos por tenant en queries (Row Level Security en PostgreSQL)

---

## Módulos y endpoints

### API Reference

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/health` | GET | Estado del sistema y dependencias |
| `/api/auth/login` | POST | Login con JWT |
| `/api/catalogos/filtros` | GET | Catálogos para filtros globales |
| `/api/dashboard/executive` | GET | KPIs ejecutivos consolidados |
| `/api/agricola/resumen` | GET | Resumen módulo agrícola |
| `/api/agricola/lotes` | GET | Tabla de lotes con filtros |
| `/api/comercial/resumen` | GET | Resumen comercial |
| `/api/comercial/operaciones` | GET | Ventas y contratos |
| `/api/finanzas/resumen` | GET | Indicadores financieros |
| `/api/finanzas/flujo` | GET | Serie temporal flujo de caja |
| `/api/stock/resumen` | GET | Stock por cultivo |
| `/api/stock/movimientos` | GET | Historial movimientos |
| `/api/maquinaria/resumen` | GET | Resumen flota |
| `/api/maquinaria/equipos` | GET | Tabla de equipos |
| `/api/macro/resumen` | GET | **Datos reales BCRA** |
| `/api/macro/series` | GET | **Series temporales reales** |
| `/api/mercado/commodities` | GET | **Precios reales commodities** |
| `/api/clima/resumen` | GET | **Clima real por establecimiento** |
| `/api/clima/pronostico` | GET | **Pronóstico 7 días real** |
| `/api/insights/ejecutivos` | GET | Insights automáticos combinados |
| `/api/cache/status` | GET | Estado del cache Redis |
| `/api/cache/refresh` | POST | Forzar refresh de cache |

Swagger UI completo disponible en: **http://localhost:8000/docs**

---

## Tecnologías utilizadas

| Componente | Tecnología |
|-----------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Gráficos | Plotly.js / react-plotly.js |
| Tablas | AG Grid Community |
| Data fetching | SWR |
| Backend | FastAPI, Python 3.11 |
| ORM | SQLAlchemy 2.0 async |
| Migraciones | Alembic |
| Cache | Redis 7 |
| DB desarrollo | SQLite + aiosqlite |
| DB producción | PostgreSQL 16 |
| Contenedores | Docker + Docker Compose |
| HTTP cliente | httpx (async) |

---

*AgroControl — Demo Comercial — v1.0.0*
*Construido con FastAPI + Next.js | Datos operativos ficticios + APIs externas reales*
