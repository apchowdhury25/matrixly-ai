-- Bootstrap roles + database privileges for local docker-compose.
-- Runs once on empty data volume (Postgres docker-entrypoint-initdb.d).

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOINHERIT LOGIN PASSWORD 'authenticated';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'matrixly_app') THEN
    CREATE ROLE matrixly_app NOINHERIT LOGIN PASSWORD 'matrixly';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'matrixly_service') THEN
    CREATE ROLE matrixly_service NOINHERIT LOGIN PASSWORD 'matrixly_service' BYPASSRLS;
  END IF;
END
$$;

-- App role participates in authenticated policies via GRANT of table rights;
-- we use matrixly_app as the API DSN user and also grant it authenticated membership optionally.
GRANT authenticated TO matrixly_app;

GRANT CONNECT ON DATABASE matrixly TO matrixly_app, matrixly_service, authenticated;
GRANT USAGE ON SCHEMA public TO matrixly_app, matrixly_service, authenticated;
GRANT CREATE ON SCHEMA public TO matrixly_service;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO matrixly_app, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT ALL ON TABLES TO matrixly_service;
