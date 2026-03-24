-- Script de inicialización PostgreSQL
-- Se ejecuta automáticamente en el primer arranque del container

-- Extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- para búsqueda de texto

-- Configuración de zona horaria
SET timezone = 'America/Argentina/Buenos_Aires';

-- Este script solo inicializa extensiones.
-- Las tablas son creadas por Alembic en el startup del backend.
