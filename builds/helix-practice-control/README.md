# Helix v1.1 — UK practice control plane (backend + tests)

This directory previously contained a browser-only HTML demo. The demo is still here
(`index.html`), but the approval/VAT logic now lives in a real Python + SQLite backend with
tests. Everything below is reproducible from a clean checkout.

## What is implemented

| Area | Status |
|---|---|
| Transactions: create / amend / approve / post | **Implemented** (`helix_core.py`) |
| Approval bound to a payload hash (amount + evidence + account + dates) | **Implemented** |
| Amendment invalidates the approval and returns the row to `pending` | **Implemented** |
| Separation of duties (preparer ≠ approver) | **Implemented** |
| Bearer-token auth, PBKDF2-SHA256 (120k iterations), per-tenant scoping | **Implemented** |
| Duplicate prevention: `UNIQUE(client_id, kind, number)` + `BEGIN IMMEDIATE` | **Implemented** |
| Concurrent posting: version check + idempotent `post` | **Implemented** |
| VAT: integer pence, half-up rounding, invoice vs receipt split | **Implemented** |
| Hash-chained audit log + `verify` (tamper detection) | **Implemented** |
| VAT return boxes (Box 1 output VAT) | **Implemented** |
| HMRC MTD VAT API / sandbox submission | **Not implemented** (planned; requires OAuth + fraud-prevention headers) |
| Document upload to object storage | **Simulated** — evidence is stored as a SHA-256 of the bytes |
| Multi-user UI | **Planned** — `index.html` is a single-page demo, not wired to the API yet |

## Why changing an approved amount no longer keeps the approval

Each transaction has `payload_hash = SHA-256(canonical(client_id, kind, number, issued_at,
net_pence, vat_rate_bp, vat_pence, gross_pence, currency, account_code, evidence_sha))`.

An approval row stores that exact hash plus an HMAC signature over `(tx id, payload_hash,
approver, timestamp)`. Three independent checks then apply:

1. `amend()` recomputes the hash, sets `status='pending'`, and marks every open approval
   `superseded=1`. `post()` refuses anything that is not `approved`.
2. `post()` re-loads the latest non-superseded approval and refuses if
   `approval.payload_hash != transaction.payload_hash`.
3. `verify()` recomputes every payload hash and every audit hash, so a direct SQL edit
   (bypassing the API entirely) is reported as `transaction_tampered`.

`test_10_amend_kills_approval` and `test_11_evidence_amend_kills_approval` exercise exactly
the case from the review: change the amount or the evidence string after approval, then try
to post.

## Setup (clean checkout)

Requires Python 3.11+ (tested on 3.12). **No third-party packages.**

```bash
cd builds/helix-practice-control
python3 --version                 # 3.11 or newer
python3 app.py --init --serve --port 8842
# prints two demo tokens: one preparer, one approver
```

In a second shell:

```bash
TOK_PREP=...   # from the previous step
TOK_APPR=...

# create
curl -s -X POST localhost:8842/api/transactions -H "Authorization: Bearer $TOK_PREP" \
  -H 'Content-Type: application/json' \
  -d '{"kind":"invoice","number":"INV-1001","issued_at":"2026-10-05","net_pence":1999,"vat_rate_bp":2000,"evidence_text":"signed timesheet"}'

# approve (approver identity, not the preparer)
curl -s -X POST localhost:8842/api/transactions/1/approve -H "Authorization: Bearer $TOK_APPR" -d '{}'

# post (version comes from the approve response)
curl -s -X POST localhost:8842/api/transactions/1/post -H "Authorization: Bearer $TOK_APPR" -d '{"version":2}'

# integrity + VAT
curl -s localhost:8842/api/verify
curl -s "localhost:8842/api/vat?period=2026-10" -H "Authorization: Bearer $TOK_APPR"
```

## Tests

```bash
cd builds/helix-practice-control
python3 -m unittest test_helix -v
```

34 tests, no network, no fixtures outside `tempfile` directories:

- money & VAT rounding (4)
- hashing / tamper detection (4)
- approval binding, SoD, audit history (7)
- posting, idempotency, version conflict, concurrency (5)
- duplicates & tenant isolation (6)
- VAT return, persistence across restart, clean verify (4)
- HTTP API: auth, full flow, tamper visibility (4)

## Schema and migrations

`schema.sql` is the complete schema (idempotent `CREATE TABLE IF NOT EXISTS`).
`Store.__init__` applies it on every start, so an empty file becomes a working database.
There is no migration framework yet; adding a column means a numbered migration file plus a
`user_version` bump — listed as planned work, not claimed.

## File map

```
helix_core.py   domain model, SQLite store, approval/VAT/audit logic
app.py          HTTP API (stdlib http.server) + CLI
schema.sql      full schema
test_helix.py   34 tests
index.html      the original browser demo (kept, not wired to the API)
```

## Known limits (stated, not hidden)

- No HMRC sandbox integration and no OAuth; VAT figures are computed, never submitted.
- Evidence files are hashed, not stored; a production build needs an object store.
- Single-writer SQLite with a process-level lock: correct for one practice, not for a cluster.
- The demo HTML is not connected to the API yet.
