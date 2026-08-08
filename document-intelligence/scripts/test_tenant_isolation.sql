-- Manual isolation checks (run as matrixly_app)
-- Expect ERROR without GUC:
-- SELECT count(*) FROM documents;

BEGIN;
SET LOCAL app.current_tenant_id = '11111111-1111-1111-1111-111111111111';
SELECT id, title, status, tenant_id FROM documents;
COMMIT;

BEGIN;
SET LOCAL app.current_tenant_id = '22222222-2222-2222-2222-222222222222';
SELECT id, title, status, tenant_id FROM documents;
COMMIT;
