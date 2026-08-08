# Matrixly Document Intelligence

Multi-tenant document upload, processing, and **hybrid (vector + full-text) search** for the Matrixly agent marketplace.

| | |
|---|---|
| **Site** | [https://matrixly.net](https://matrixly.net) |
| **Contact** | anwar.chowdhury@matrixly.net |
| **Stack** | PostgreSQL 16 + pgvector · FastAPI · async SQLAlchemy 2 · ARQ |

## Language / locale policy

| Layer | Language |
|--------|----------|
| **Database** (tables, enums, status codes, function names) | **English only** |
| **API** (paths, JSON field names, error codes) | **English only** |
| **Front-end website** (user-selected locale: en, es, fr, ar, bn, de, ms) | Runtime UI only — does **not** change API or DB |

Agents and workers always speak English contracts; the marketing site localizes presentation separately.

## Security model

1. Every row has `tenant_id`.
2. API sessions run as a non-bypass role and execute:
   `SET LOCAL app.current_tenant_id = '<uuid>';`
3. **RLS + FORCE RLS** on `documents` and `document_chunks`.
4. **`matrixly_service`** has `BYPASSRLS` for ARQ workers only — never ship that DSN to browsers or public agent sandboxes.
5. JWT claim `tenant_id` (or `tid`) is the source of truth for tenant context.

## Layout

```
document-intelligence/
  migrations/001_document_intelligence.sql
  app/
    main.py              # FastAPI app
    config.py
    db.py                # RLS + service engines
    deps.py              # CurrentTenant + session
    orm.py
    schemas.py           # Pydantic v2
    embeddings.py        # swappable providers
    chunking.py
    services/document_service.py
    routers/documents.py
    workers/             # ARQ tasks
  examples/agent_tool_search.py
  docker-compose.yml
  .env.example
```

## Quick start

### 1. Infrastructure

```bash
cd document-intelligence
cp .env.example .env
docker compose up -d postgres redis
```

### 2. Migrations

```bash
# requires psql client
export DATABASE_ADMIN_URL=postgresql://postgres:postgres@localhost:5432/matrixly
psql "$DATABASE_ADMIN_URL" -v ON_ERROR_STOP=1 -f migrations/001_document_intelligence.sql
# or: bash scripts/run_migrations.sh
```

### 3. Python env

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export PYTHONPATH=.
```

### 4. API

```bash
uvicorn app.main:app --reload --port 8080
# Health: http://localhost:8080/healthz
# OpenAPI: http://localhost:8080/docs
```

### 5. Worker

```bash
arq app.workers.worker.WorkerSettings
```

### 6. Mint a dev JWT & test

```bash
python scripts/mint_dev_jwt.py --tenant-id 11111111-1111-1111-1111-111111111111
export TOKEN=eyJ...   # printed token

# Upload a text SOP
curl -s -X POST "http://localhost:8080/api/v1/documents" \
  -H "Authorization: Bearer $TOKEN" \
  -F "title=Returns SOP" \
  -F "file=@./samples/returns.txt;type=text/plain"

# Queue processing (or wait for auto-inline in development)
curl -s -X POST "http://localhost:8080/api/v1/documents/<DOC_ID>/process" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'

# Hybrid search
curl -s -X POST "http://localhost:8080/api/v1/documents/search" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"how do we handle returns","limit":5}'
```

## Tenant isolation test

1. Mint JWT for **tenant A** and upload document A.  
2. Mint JWT for **tenant B** and list documents — must **not** see A.  
3. Search as B for text only present in A — empty hits.  
4. Confirm with SQL as `matrixly_app` without GUC → queries fail (`app.current_tenant_id is not set`).

```sql
-- As matrixly_app (no GUC): should error on SELECT
SELECT * FROM documents;

-- Correct pattern:
BEGIN;
SET LOCAL app.current_tenant_id = '11111111-1111-1111-1111-111111111111';
SELECT id, title, status FROM documents;
COMMIT;
```

## API surface (English paths)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/documents` | Multipart upload / register |
| POST | `/api/v1/documents/{id}/process` | Queue chunk + embed |
| POST | `/api/v1/documents/search` | Hybrid search |
| GET | `/api/v1/documents` | List |
| GET | `/api/v1/documents/{id}` | Get |
| DELETE | `/api/v1/documents/{id}` | Soft delete |

## Agent tool

See `examples/agent_tool_search.py` for an async helper and OpenAI-style tool schema that agents call with the tenant JWT.

## Swapping embedding providers

1. Set `EMBEDDING_PROVIDER=openai` and `OPENAI_API_KEY`.  
2. Keep `EMBEDDING_DIMENSIONS=1536` for the current column.  
3. For a new dimension: add `embedding_v2 vector(N)`, dual-write, backfill, then switch search.

## Production notes

- Use managed Postgres 16+ with the `vector` extension.  
- Rotate JWT secrets; prefer IdP-issued tokens with `tenant_id`.  
- Put object storage (S3) behind `storage_uri` instead of local disk.  
- Partition `document_chunks` by `tenant_id` when single-tenant tables exceed tens of millions of rows.  
- Point search-only traffic at a **read replica** DSN when ready (same schema, RLS still applies if GUC is set).

## Status codes (English)

`pending` → `queued` → `processing` → `ready` | `failed` | `deleted`
