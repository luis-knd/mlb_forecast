-- Script de inicialización para la base de datos MLB Forecast
-- Se ejecuta automáticamente cuando se crea el contenedor de PostgreSQL

-- Crear extensiones útiles
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Crear índices adicionales para optimización de consultas
-- (Los índices principales se crean en los modelos SQLAlchemy)

-- Función para actualizar timestamp automáticamente
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Configuración de timezone
SET timezone TO 'UTC';

-- Configuraciones de rendimiento
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;
ALTER SYSTEM SET random_page_cost = 1.1;
ALTER SYSTEM SET effective_io_concurrency = 200;

-- Configuración para mejor rendimiento de queries analíticos
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET max_parallel_workers_per_gather = 2;
ALTER SYSTEM SET max_parallel_workers = 8;
ALTER SYSTEM SET max_worker_processes = 8;

-- Logging para debugging (opcional, solo en desarrollo)
-- ALTER SYSTEM SET log_statement = 'all';
-- ALTER SYSTEM SET log_duration = on;

-- Configurar búsqueda full-text (para futuras extensiones)
CREATE TEXT SEARCH CONFIGURATION mlb_search (COPY = english);

-- Comentarios informativos
COMMENT ON DATABASE mlb_forecast IS 'Base de datos para el sistema de pronósticos MLB';

-- Crear roles adicionales si es necesario
-- CREATE ROLE mlb_readonly;
-- GRANT CONNECT ON DATABASE mlb_forecast TO mlb_readonly;
-- GRANT USAGE ON SCHEMA public TO mlb_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO mlb_readonly;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mlb_readonly;

-- Mensaje de confirmación
DO $$
BEGIN
    RAISE NOTICE 'Base de datos MLB Forecast inicializada correctamente';
END $$;
