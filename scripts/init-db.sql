-- Script di inizializzazione database PostgreSQL
-- Questo file viene eseguito automaticamente da PostgreSQL all'avvio

-- Crea database se non esiste (già gestito da POSTGRES_DB)
-- CREATE DATABASE IF NOT EXISTS polito_mensa;

-- Crea utente per l'applicazione (opzionale)
-- CREATE USER IF NOT EXISTS polito_app WITH ENCRYPTED PASSWORD 'polito_app_password';
-- GRANT ALL PRIVILEGES ON DATABASE polito_mensa TO polito_app;

-- Abilita estensioni utili
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";  -- Per UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";    -- Per similarity search
CREATE EXTENSION IF NOT EXISTS "unaccent";   -- Per ricerca text senza accenti

-- Log delle inizializzazioni
DO $$ 
BEGIN
    RAISE NOTICE 'Database polito_mensa inizializzato con estensioni uuid-ossp, pg_trgm, unaccent';
END $$;