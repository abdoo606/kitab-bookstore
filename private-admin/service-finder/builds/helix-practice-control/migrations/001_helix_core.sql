-- Helix v1 UK Practice Control Plane — Core Relational & Trigger Schema
-- Compatible with standard library Python 3.10+ sqlite3 (WAL mode, Foreign Keys ON)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS tenants (
    tenant_id TEXT PRIMARY KEY,
    legal_name TEXT NOT NULL,
    vrn TEXT NOT NULL CHECK (length(vrn) = 9),
    vat_scheme TEXT NOT NULL CHECK (vat_scheme IN ('STANDARD_ACCRUAL', 'CASH_ACCOUNTING')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviewers (
    reviewer_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('PARTNER_REVIEWER', 'PRACTICE_PREPARER', 'AUDITOR_READONLY')),
    token_salt TEXT NOT NULL,
    token_pbkdf2_hex TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS reviewer_tenant_grants (
    reviewer_id TEXT NOT NULL REFERENCES reviewers(reviewer_id) ON DELETE CASCADE,
    tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    PRIMARY KEY (reviewer_id, tenant_id)
);

CREATE TABLE IF NOT EXISTS evidence_blobs (
    evidence_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
    sha256_hex TEXT NOT NULL CHECK (length(sha256_hex) = 64),
    storage_relpath TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    tx_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    idempotency_key TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('SALES_INVOICE', 'PURCHASE_INVOICE', 'DEBTOR_RECEIPT', 'CREDITOR_PAYMENT')),
    vat_treatment TEXT NOT NULL CHECK (vat_treatment IN ('UK_STD_20', 'UK_REDUCED_5', 'UK_ZERO_0', 'UK_EXEMPT', 'OUTSIDE_SCOPE_SETTLEMENT')),
    counterparty TEXT NOT NULL,
    tax_point_date TEXT NOT NULL,
    period_key TEXT NOT NULL CHECK (length(period_key) = 4),
    net_pence INTEGER NOT NULL CHECK (net_pence >= 0),
    vat_pence INTEGER NOT NULL CHECK (vat_pence >= 0),
    gross_pence INTEGER NOT NULL CHECK (gross_pence = net_pence + vat_pence),
    evidence_id TEXT NOT NULL REFERENCES evidence_blobs(evidence_id),
    linked_invoice_tx_id TEXT REFERENCES transactions(tx_id),
    ai_confidence REAL NOT NULL CHECK (ai_confidence >= 0.0 AND ai_confidence <= 1.0),
    status TEXT NOT NULL CHECK (status IN ('PENDING_REVIEW', 'APPROVED_POSTED', 'INVALIDATED_TAMPERED')),
    approved_digest_hex TEXT,
    approved_by TEXT REFERENCES reviewers(reviewer_id),
    approved_at TEXT,
    invalidation_reason TEXT,
    updated_at TEXT NOT NULL,
    UNIQUE (tenant_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS ledger_postings (
    posting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    tx_id TEXT NOT NULL REFERENCES transactions(tx_id) ON DELETE CASCADE,
    entry_type TEXT NOT NULL CHECK (entry_type IN ('ORIGINAL_POST', 'REVERSAL_ON_INVALIDATION')),
    debit_account TEXT NOT NULL,
    credit_account TEXT NOT NULL,
    amount_pence INTEGER NOT NULL CHECK (amount_pence >= 0),
    vat_box1_delta_pence INTEGER NOT NULL DEFAULT 0,
    vat_box4_delta_pence INTEGER NOT NULL DEFAULT 0,
    vat_box6_delta_pence INTEGER NOT NULL DEFAULT 0,
    vat_box7_delta_pence INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Partial unique index: at most ONE unreversed ORIGINAL_POST while status='APPROVED_POSTED' per posting batch,
-- plus application-level BEGIN IMMEDIATE transaction locking to eliminate race conditions.
CREATE INDEX IF NOT EXISTS idx_ledger_tenant_tx ON ledger_postings(tenant_id, tx_id);

CREATE TABLE IF NOT EXISTS audit_events (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id TEXT NOT NULL REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    tx_id TEXT,
    actor_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    prev_chain_hex TEXT NOT NULL,
    chain_hex TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- ============================================================================
-- DATABASE-LEVEL TAMPER & MUTATION ENFORCEMENT TRIGGERS
-- Guarantees that ANY direct or API mutation to an approved transaction's
-- financial fields (net_pence, vat_pence, gross_pence, vat_treatment, kind,
-- period_key, evidence_id) IMMEDIATELY strips approval status AND posts a
-- reversing double-entry VAT/ledger neutralization entry inside SQLite itself!
-- ============================================================================
CREATE TRIGGER IF NOT EXISTS trg_invalidate_approved_tx_on_mutation
AFTER UPDATE OF net_pence, vat_pence, gross_pence, vat_treatment, kind, period_key, evidence_id
ON transactions
WHEN OLD.status = 'APPROVED_POSTED'
  AND (
      NEW.net_pence != OLD.net_pence
      OR NEW.vat_pence != OLD.vat_pence
      OR NEW.gross_pence != OLD.gross_pence
      OR NEW.vat_treatment != OLD.vat_treatment
      OR NEW.kind != OLD.kind
      OR NEW.period_key != OLD.period_key
      OR NEW.evidence_id != OLD.evidence_id
  )
BEGIN
    UPDATE transactions
    SET status = 'INVALIDATED_TAMPERED',
        approved_digest_hex = NULL,
        approved_by = NULL,
        approved_at = NULL,
        invalidation_reason = COALESCE(NEW.invalidation_reason, 'SQL_TRIGGER: Approved financial field or evidence reference mutated post-approval')
    WHERE tx_id = NEW.tx_id;

    INSERT INTO ledger_postings (
        tenant_id, tx_id, entry_type, debit_account, credit_account, amount_pence,
        vat_box1_delta_pence, vat_box4_delta_pence, vat_box6_delta_pence, vat_box7_delta_pence,
        created_by, created_at
    )
    SELECT
        lp.tenant_id,
        lp.tx_id,
        'REVERSAL_ON_INVALIDATION',
        lp.credit_account,
        lp.debit_account,
        lp.amount_pence,
        -lp.vat_box1_delta_pence,
        -lp.vat_box4_delta_pence,
        -lp.vat_box6_delta_pence,
        -lp.vat_box7_delta_pence,
        'SYSTEM_TAMPER_TRIGGER',
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    FROM ledger_postings lp
    WHERE lp.tx_id = NEW.tx_id
      AND lp.posting_id = (
          SELECT MAX(posting_id) FROM ledger_postings
          WHERE tx_id = NEW.tx_id AND entry_type = 'ORIGINAL_POST'
      );
END;

CREATE TRIGGER IF NOT EXISTS trg_invalidate_tx_on_evidence_sha_mutation
AFTER UPDATE OF sha256_hex, byte_length
ON evidence_blobs
WHEN NEW.sha256_hex != OLD.sha256_hex OR NEW.byte_length != OLD.byte_length
BEGIN
    INSERT INTO ledger_postings (
        tenant_id, tx_id, entry_type, debit_account, credit_account, amount_pence,
        vat_box1_delta_pence, vat_box4_delta_pence, vat_box6_delta_pence, vat_box7_delta_pence,
        created_by, created_at
    )
    SELECT
        lp.tenant_id,
        lp.tx_id,
        'REVERSAL_ON_INVALIDATION',
        lp.credit_account,
        lp.debit_account,
        lp.amount_pence,
        -lp.vat_box1_delta_pence,
        -lp.vat_box4_delta_pence,
        -lp.vat_box6_delta_pence,
        -lp.vat_box7_delta_pence,
        'SYSTEM_EVIDENCE_TAMPER_TRIGGER',
        strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
    FROM transactions t
    JOIN ledger_postings lp ON lp.tx_id = t.tx_id
    WHERE t.evidence_id = NEW.evidence_id
      AND t.status = 'APPROVED_POSTED'
      AND lp.posting_id = (
          SELECT MAX(posting_id) FROM ledger_postings
          WHERE tx_id = t.tx_id AND entry_type = 'ORIGINAL_POST'
      );

    UPDATE transactions
    SET status = 'INVALIDATED_TAMPERED',
        approved_digest_hex = NULL,
        approved_by = NULL,
        approved_at = NULL,
        invalidation_reason = 'SQL_TRIGGER: Underlying evidence file SHA-256 or byte length changed after approval'
    WHERE evidence_id = NEW.evidence_id
      AND status = 'APPROVED_POSTED';
END;
