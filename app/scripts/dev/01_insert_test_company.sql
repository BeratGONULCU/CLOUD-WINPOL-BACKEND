-- ===============================
-- TEST COMPANY INSERT
-- ===============================

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

INSERT INTO companies (
    id,
    company_code,
    name,
    status,
    status_message,
    created_at
)
VALUES (
    gen_random_uuid(),
    'TEST_FIRMA',
    'Test Firma',
    'ACTIVE',
    'Initial test company',
    NOW()
);

-- Kontrol
SELECT * FROM companies WHERE company_code = 'TEST_FIRMA';
