-- Helix v1.1 schema (SQLite 3.35+)
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS clients (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    vat_number  TEXT,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id          TEXT PRIMARY KEY,
    client_id   TEXT NOT NULL REFERENCES clients(id),
    name        TEXT NOT NULL,
    role        TEXT NOT NULL CHECK (role IN ('preparer','approver','admin')),
    token_hash  TEXT NOT NULL,
    salt        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id     TEXT NOT NULL REFERENCES clients(id),
    kind          TEXT NOT NULL CHECK (kind IN ('invoice','receipt')),
    number        TEXT NOT NULL,
    issued_at     TEXT NOT NULL,          -- YYYY-MM-DD
    net_pence     INTEGER NOT NULL CHECK (net_pence >= 0),
    vat_rate_bp   INTEGER NOT NULL CHECK (vat_rate_bp >= 0),
    vat_pence     INTEGER NOT NULL,
    gross_pence   INTEGER NOT NULL,
    currency      TEXT NOT NULL DEFAULT 'GBP',
    account_code  TEXT NOT NULL DEFAULT '4000',
    evidence_name TEXT NOT NULL DEFAULT '',
    evidence_sha  TEXT NOT NULL DEFAULT '',
    status        TEXT NOT NULL CHECK (status IN ('draft','pending','approved','posted','void')),
    version       INTEGER NOT NULL DEFAULT 1,
    payload_hash  TEXT NOT NULL,
    created_by    TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    UNIQUE (client_id, kind, number)
);

CREATE TABLE IF NOT EXISTS approvals (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id      TEXT NOT NULL,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
    payload_hash   TEXT NOT NULL,
    approver       TEXT NOT NULL,
    approved_at    TEXT NOT NULL,
    note           TEXT NOT NULL DEFAULT '',
    sig            TEXT NOT NULL,
    superseded     INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS audit (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    actor     TEXT NOT NULL,
    action    TEXT NOT NULL,
    entity    TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    detail    TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    hash      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tx_client ON transactions(client_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit(entity, entity_id);
