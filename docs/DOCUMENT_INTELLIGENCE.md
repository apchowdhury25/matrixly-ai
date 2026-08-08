# Document Intelligence (backend)

Production foundation for multi-tenant document RAG lives in:

**[`document-intelligence/`](../document-intelligence/)**

- PostgreSQL 16 + **pgvector** + **RLS** (`app.current_tenant_id`)
- FastAPI + async SQLAlchemy 2 + asyncpg
- ARQ workers for extract → chunk → embed
- Hybrid search SQL function for agents

**Site / contact:** [matrixly.net](https://matrixly.net) · anwar.chowdhury@matrixly.net

**Locale note:** Six front-end languages (en, es, fr, ar, bn, de, ms) apply only to the marketing website. API, SQL, and status codes remain English.

See the service [README](../document-intelligence/README.md) for runbooks and tenant isolation tests.
