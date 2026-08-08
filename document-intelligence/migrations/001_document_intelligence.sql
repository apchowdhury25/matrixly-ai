-- =============================================================================
-- Matrixly Document Intelligence — multi-tenant foundation
-- PostgreSQL 16+ · pgvector · pure SQL (no Supabase Auth helpers)
--
-- Security model:
--   • Every row is scoped by tenant_id (UUID)
--   • Application sets: SET LOCAL app.current_tenant_id = '<uuid>';
--   • RLS + FORCE ROW LEVEL SECURITY enforces isolation for normal roles
--   • matrixly_service role has BYPASSRLS for workers / trusted backend only
--
-- Language note:
--   Database identifiers, status enums, and API-facing English labels stay
--   English. Front-end locale selection (en/es/fr/ar/bn/de/ms) is UI-only.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- Roles (idempotent)
-- authenticated: app users / API under RLS
-- matrixly_service: workers, migration runners, admin jobs (BYPASSRLS)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
    CREATE ROLE authenticated NOINHERIT;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'matrixly_service') THEN
    CREATE ROLE matrixly_service NOINHERIT BYPASSRLS;
  END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- Helper: current_tenant_id()
-- Reads session GUC set by the API on every request / job.
-- Raises if unset so queries never silently run without a tenant.
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.current_tenant_id()
RETURNS uuid
LANGUAGE plpgsql
STABLE
AS $$
DECLARE
  v text;
BEGIN
  v := nullif(current_setting('app.current_tenant_id', true), '');
  IF v IS NULL THEN
    RAISE EXCEPTION 'app.current_tenant_id is not set'
      USING ERRCODE = '42501';  -- insufficient_privilege
  END IF;
  RETURN v::uuid;
END;
$$;

COMMENT ON FUNCTION public.current_tenant_id() IS
  'Returns tenant UUID from SET app.current_tenant_id; errors if missing.';

-- ---------------------------------------------------------------------------
-- Enum: document processing lifecycle (English codes only)
-- ---------------------------------------------------------------------------
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'document_status') THEN
    CREATE TYPE document_status AS ENUM (
      'pending',      -- uploaded, not yet queued
      'queued',       -- accepted by worker
      'processing',   -- extract / chunk / embed in flight
      'ready',        -- searchable
      'failed',       -- terminal error; see metadata.error
      'deleted'       -- soft-deleted
    );
  END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- Table: documents
-- One row per uploaded file (or remote source) owned by a tenant.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.documents (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,

  -- Identity & storage
  title           text NOT NULL,
  filename        text,
  content_type    text,
  storage_uri     text,                    -- s3://, file://, or object key
  byte_size       bigint CHECK (byte_size IS NULL OR byte_size >= 0),
  checksum_sha256 text,

  -- Lifecycle
  status          document_status NOT NULL DEFAULT 'pending',
  error_message   text,

  -- Flexible SMB metadata: source, tags, agent_id, language (content language
  -- of the document itself — not UI locale), contract_type, etc.
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,

  -- Stats filled by workers
  chunk_count     integer NOT NULL DEFAULT 0 CHECK (chunk_count >= 0),
  page_count      integer,

  -- Audit
  created_by      text,                    -- user id or service principal (English id)
  created_at      timestamptz NOT NULL DEFAULT now(),
  updated_at      timestamptz NOT NULL DEFAULT now(),
  processed_at    timestamptz,
  deleted_at      timestamptz
);

COMMENT ON TABLE public.documents IS
  'Tenant-owned documents for agent RAG. Codes/status in English.';

CREATE INDEX IF NOT EXISTS documents_tenant_created_idx
  ON public.documents (tenant_id, created_at DESC);

CREATE INDEX IF NOT EXISTS documents_tenant_status_idx
  ON public.documents (tenant_id, status)
  WHERE status <> 'deleted';

CREATE INDEX IF NOT EXISTS documents_metadata_gin_idx
  ON public.documents USING gin (metadata jsonb_path_ops);

-- updated_at trigger
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS documents_set_updated_at ON public.documents;
CREATE TRIGGER documents_set_updated_at
  BEFORE UPDATE ON public.documents
  FOR EACH ROW EXECUTE PROCEDURE public.set_updated_at();

-- ---------------------------------------------------------------------------
-- Table: document_chunks
-- Embedded segments for hybrid (vector + full-text) retrieval.
-- embedding dimension 1536 matches OpenAI text-embedding-3-small / ada-002;
-- swap provider by changing model + re-embedding (column size documented).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.document_chunks (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id       uuid NOT NULL,
  document_id     uuid NOT NULL REFERENCES public.documents (id) ON DELETE CASCADE,

  chunk_index     integer NOT NULL CHECK (chunk_index >= 0),
  content         text NOT NULL,
  token_count     integer,

  -- Vector embedding (cosine distance via HNSW)
  embedding       vector(1536),

  -- Full-text search vector (English config; content may be multi-language)
  content_tsv     tsvector GENERATED ALWAYS AS (
                    to_tsvector('english', coalesce(content, ''))
                  ) STORED,

  -- Chunk-level metadata: page, heading path, section, bbox, etc.
  metadata        jsonb NOT NULL DEFAULT '{}'::jsonb,

  created_at      timestamptz NOT NULL DEFAULT now(),

  UNIQUE (document_id, chunk_index)
);

COMMENT ON TABLE public.document_chunks IS
  'Embedded text chunks for hybrid semantic + FTS search per tenant.';

CREATE INDEX IF NOT EXISTS document_chunks_tenant_doc_idx
  ON public.document_chunks (tenant_id, document_id);

-- HNSW for approximate nearest-neighbor (cosine)
-- m/ef_construction tuned for SMB corpora; adjust at scale.
CREATE INDEX IF NOT EXISTS document_chunks_embedding_hnsw_idx
  ON public.document_chunks
  USING hnsw (embedding vector_cosine_ops)
  WITH (m = 16, ef_construction = 64);

-- Full-text GIN
CREATE INDEX IF NOT EXISTS document_chunks_content_tsv_gin_idx
  ON public.document_chunks USING gin (content_tsv);

CREATE INDEX IF NOT EXISTS document_chunks_metadata_gin_idx
  ON public.document_chunks USING gin (metadata jsonb_path_ops);

-- ---------------------------------------------------------------------------
-- Row Level Security
-- ---------------------------------------------------------------------------
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents FORCE ROW LEVEL SECURITY;

ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks FORCE ROW LEVEL SECURITY;

-- Drop policies if re-running migration in dev
DROP POLICY IF EXISTS documents_select_tenant ON public.documents;
DROP POLICY IF EXISTS documents_insert_tenant ON public.documents;
DROP POLICY IF EXISTS documents_update_tenant ON public.documents;
DROP POLICY IF EXISTS documents_delete_tenant ON public.documents;

DROP POLICY IF EXISTS document_chunks_select_tenant ON public.document_chunks;
DROP POLICY IF EXISTS document_chunks_insert_tenant ON public.document_chunks;
DROP POLICY IF EXISTS document_chunks_update_tenant ON public.document_chunks;
DROP POLICY IF EXISTS document_chunks_delete_tenant ON public.document_chunks;

-- documents policies
CREATE POLICY documents_select_tenant ON public.documents
  FOR SELECT
  USING (tenant_id = public.current_tenant_id());

CREATE POLICY documents_insert_tenant ON public.documents
  FOR INSERT
  WITH CHECK (tenant_id = public.current_tenant_id());

CREATE POLICY documents_update_tenant ON public.documents
  FOR UPDATE
  USING (tenant_id = public.current_tenant_id())
  WITH CHECK (tenant_id = public.current_tenant_id());

CREATE POLICY documents_delete_tenant ON public.documents
  FOR DELETE
  USING (tenant_id = public.current_tenant_id());

-- document_chunks policies
CREATE POLICY document_chunks_select_tenant ON public.document_chunks
  FOR SELECT
  USING (tenant_id = public.current_tenant_id());

CREATE POLICY document_chunks_insert_tenant ON public.document_chunks
  FOR INSERT
  WITH CHECK (tenant_id = public.current_tenant_id());

CREATE POLICY document_chunks_update_tenant ON public.document_chunks
  FOR UPDATE
  USING (tenant_id = public.current_tenant_id())
  WITH CHECK (tenant_id = public.current_tenant_id());

CREATE POLICY document_chunks_delete_tenant ON public.document_chunks
  FOR DELETE
  USING (tenant_id = public.current_tenant_id());

-- ---------------------------------------------------------------------------
-- Grants
-- authenticated: DML under RLS only
-- matrixly_service: full access (BYPASSRLS on role)
-- ---------------------------------------------------------------------------
GRANT USAGE ON SCHEMA public TO authenticated, matrixly_service;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.documents TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.document_chunks TO authenticated;

GRANT ALL ON public.documents TO matrixly_service;
GRANT ALL ON public.document_chunks TO matrixly_service;

GRANT EXECUTE ON FUNCTION public.current_tenant_id() TO authenticated, matrixly_service;

-- ---------------------------------------------------------------------------
-- Hybrid search: vector cosine + full-text rank, RRF-style fusion
-- Called with tenant context already set (or as service with explicit filter).
-- ---------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.search_documents_hybrid(
  p_query_text     text,
  p_query_embedding vector(1536),
  p_limit          integer DEFAULT 10,
  p_vector_weight  float DEFAULT 0.7,
  p_fts_weight     float DEFAULT 0.3,
  p_document_id    uuid DEFAULT NULL,
  p_min_similarity float DEFAULT 0.0
)
RETURNS TABLE (
  chunk_id      uuid,
  document_id   uuid,
  chunk_index   integer,
  content       text,
  metadata      jsonb,
  document_title text,
  vector_score  float,
  fts_score     float,
  hybrid_score  float
)
LANGUAGE sql
STABLE
AS $$
  WITH
  q AS (
    SELECT
      plainto_tsquery('english', coalesce(p_query_text, '')) AS tsq,
      p_query_embedding AS emb
  ),
  vector_hits AS (
    SELECT
      c.id AS chunk_id,
      c.document_id,
      c.chunk_index,
      c.content,
      c.metadata,
      d.title AS document_title,
      (1.0 - (c.embedding <=> (SELECT emb FROM q)))::float AS vector_score,
      0.0::float AS fts_score
    FROM public.document_chunks c
    JOIN public.documents d ON d.id = c.document_id
    WHERE c.embedding IS NOT NULL
      AND d.status = 'ready'
      AND d.deleted_at IS NULL
      AND (p_document_id IS NULL OR c.document_id = p_document_id)
      AND (1.0 - (c.embedding <=> (SELECT emb FROM q))) >= p_min_similarity
    ORDER BY c.embedding <=> (SELECT emb FROM q)
    LIMIT greatest(p_limit * 4, 40)
  ),
  fts_hits AS (
    SELECT
      c.id AS chunk_id,
      c.document_id,
      c.chunk_index,
      c.content,
      c.metadata,
      d.title AS document_title,
      0.0::float AS vector_score,
      ts_rank_cd(c.content_tsv, (SELECT tsq FROM q))::float AS fts_score
    FROM public.document_chunks c
    JOIN public.documents d ON d.id = c.document_id
    CROSS JOIN q
    WHERE d.status = 'ready'
      AND d.deleted_at IS NULL
      AND (p_document_id IS NULL OR c.document_id = p_document_id)
      AND p_query_text IS NOT NULL
      AND p_query_text <> ''
      AND c.content_tsv @@ q.tsq
    ORDER BY fts_score DESC
    LIMIT greatest(p_limit * 4, 40)
  ),
  combined AS (
    SELECT * FROM vector_hits
    UNION ALL
    SELECT * FROM fts_hits
  ),
  scored AS (
    SELECT
      chunk_id,
      document_id,
      chunk_index,
      content,
      metadata,
      document_title,
      max(vector_score) AS vector_score,
      max(fts_score) AS fts_score,
      (
        p_vector_weight * max(vector_score)
        + p_fts_weight * least(max(fts_score) / NULLIF(
            (SELECT max(fts_score) FROM fts_hits), 0
          ), 1.0)
      )::float AS hybrid_score
    FROM combined
    GROUP BY chunk_id, document_id, chunk_index, content, metadata, document_title
  )
  SELECT
    chunk_id,
    document_id,
    chunk_index,
    content,
    metadata,
    document_title,
    vector_score,
    fts_score,
    coalesce(hybrid_score, vector_score) AS hybrid_score
  FROM scored
  ORDER BY hybrid_score DESC NULLS LAST
  LIMIT p_limit;
$$;

COMMENT ON FUNCTION public.search_documents_hybrid IS
  'Hybrid vector + FTS retrieval. Requires app.current_tenant_id (RLS) or service role.';

GRANT EXECUTE ON FUNCTION public.search_documents_hybrid(
  text, vector, integer, float, float, uuid, float
) TO authenticated, matrixly_service;

-- Optional app login role used by docker-compose DSN (matrixly_app)
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'matrixly_app') THEN
    GRANT USAGE ON SCHEMA public TO matrixly_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON public.documents TO matrixly_app;
    GRANT SELECT, INSERT, UPDATE, DELETE ON public.document_chunks TO matrixly_app;
    GRANT EXECUTE ON FUNCTION public.current_tenant_id() TO matrixly_app;
    GRANT EXECUTE ON FUNCTION public.search_documents_hybrid(
      text, vector, integer, float, float, uuid, float
    ) TO matrixly_app;
  END IF;
END
$$;

-- ---------------------------------------------------------------------------
-- Future-proofing notes (comments only — apply when needed):
--   • Partition documents / document_chunks BY LIST (tenant_id) or HASH
--   • Read replicas: run search against replica DSN; writes on primary
--   • Embedding dim change: add embedding_v2 vector(N) + dual-write, then swap
-- ---------------------------------------------------------------------------

COMMIT;
