# Helix v1 UK Practice Control Plane — Clean-Checkout Backend & Verification Suite

This directory (`private-admin/service-finder/builds/helix-practice-control`) contains the runnable Python + SQLite WAL backend, relational triggers, sample anonymized source evidence, browser UI, and automated test suite answering all points raised in technical review.

## 1. Runtime & Dependency Requirements
- **Python version:** Python `>= 3.10` (tested on Python `3.11` & `3.12`)
- **External `pip` packages required:** **None (`0` external dependencies)** — built deliberately on Python's standard library (`sqlite3` with WAL + `FOREIGN KEYS` + `AFTER UPDATE` triggers, `hashlib`, `hmac`, `decimal`, `http.server`, `threading`, `unittest`) so any clean checkout runs immediately without virtual-environment drift.

## 2. Clean-Checkout Verification Commands (< 5 Seconds)

```bash
git clone -b arena/3d819a49-kitab-bookstore https://github.com/abdoo606/kitab-bookstore.git
cd kitab-bookstore/private-admin/service-finder/builds/helix-practice-control

# 1. Run the automated verification suite (all 7 test groups)
python3 -m unittest test_helix_backend.py -v

# 2. Start the live Python + SQLite WAL server & open http://127.0.0.1:8890
python3 helix_server.py --port 8890
```

## 3. Exact Enforcement Against Post-Approval Amount or Evidence Mutation

In the initial static UI preview, mutating an approved item's amount or evidence string did **not** invalidate its `APPROVED` status, and an aged debtor receipt carried sales VAT rate metadata. Both defects are now fixed across **three independent layers**:

1. **SQLite Database Trigger Layer (`migrations/001_helix_core.sql`):**
   - `trg_invalidate_approved_tx_on_mutation` (`AFTER UPDATE OF net_pence, vat_pence, gross_pence, vat_treatment, kind, period_key, evidence_id ON transactions WHEN OLD.status = 'APPROVED_POSTED'`): immediately flips `status = 'INVALIDATED_TAMPERED'`, clears `approved_digest_hex` & `approved_by`, and inserts an immutable counter-entry (`entry_type = 'REVERSAL_ON_INVALIDATION'`) into `ledger_postings` negating the original debit/credit and `vat_box1..7` pence deltas.
   - `trg_invalidate_tx_on_evidence_sha_mutation` (`AFTER UPDATE OF sha256_hex, byte_length ON evidence_blobs`): automatically reverses ledger/VAT postings and invalidates every linked `APPROVED_POSTED` transaction whenever underlying evidence metadata mutates.
2. **Application Disk Byte Scanner (`helix_server.py -> _verify_live_evidence_in_tx` & `scan_integrity_and_compile_vat_return`):**
   - Before every approval **and** before every VAT Return compilation, the engine re-reads the raw source bytes on disk in 64 KiB chunks (`sha256_file`), compares against `evidence_blobs.sha256_hex` and `transactions.approved_digest_hex`, and automatically triggers invalidation + ledger reversal if even **1 byte** on disk changed outside SQLite.
3. **Frontend Dual-Mode Client (`index.html`):**
   - Connects automatically via `fetch('/api/...')` to `helix_server.py` when served locally (with interactive `Mutate +£100` and `Tamper File Byte` buttons), and enforces digest verification in static preview fallback mode as well.

## 4. Automated Test Coverage (`test_helix_backend.py`)

| Requirement | Test Method | What Is Verified |
|---|---|---|
| **(a) Source-file hashing & tamper detection** | `test_01_amount_mutation_immediately_invalidates_approval_and_reverses_vat` & `test_02_direct_sqlite_update_and_disk_byte_tamper_both_invalidate_approval` | SHA-256 ingestion digest, post-approval `net_pence` mutation auto-reversing Box 1 (`+20,000p -> 0p`), and 1-byte raw disk file corruption caught by `scan_integrity_and_compile_vat_return()`. |
| **(b) Authenticated approval & audit history** | `test_03_authenticated_rbac_blocks_preparer_and_verifies_hash_chain` | PBKDF2-HMAC-SHA256 bearer auth, `PRACTICE_PREPARER` blocked from `approve_and_post()`, `PARTNER_REVIEWER` accepted, and SHA-256 hash-chained `audit_events` verified end-to-end. |
| **(c) Persistence across restart** | `test_04_persistence_across_engine_close_and_cold_restart` | Full `engine.close()` WAL checkpoint + fresh `HelixPracticeEngine` instantiation preserving postings, VAT boxes, and audit chain. |
| **(d) Duplicate / concurrent posting protection** | `test_05_duplicate_and_16_thread_concurrent_posting_protection` | Rejects duplicate `(tenant_id, idempotency_key)` and fires a 16-thread `ThreadPoolExecutor` race against `approve_and_post()` — asserting **1 `POSTED`, 15 `CONFLICT_BLOCKED`, and exactly 1 ledger journal line**. |
| **(e) Multi-client isolation** | `test_06_multi_client_tenant_isolation` | Verifies Reviewer A (`client-alpha` grant) cannot read or approve `client-beta`, and cross-tenant `evidence_id` linkage raises `ValidationError`. |
| **(f) UK VAT math, integer-pence rounding & invoice-vs-receipt rules** | `test_07_uk_vat_rounding_and_standard_vs_cash_accounting_invoice_receipt_rules` | Tests `Decimal(..., ROUND_HALF_UP)` half-penny cases (`8333p @ 20% -> 1667p`, `2010p @ 5% -> 101p`), verifies `STANDARD_ACCRUAL` posts VAT on `SALES_INVOICE` and **£0 VAT / £0 Box 6** on `DEBTOR_RECEIPT` (zero double-counting), and verifies `CASH_ACCOUNTING` defers VAT on invoice and recognizes Box 1/6 upon `DEBTOR_RECEIPT`. |

## 5. Honest Breakdown: Implemented vs Simulated vs Planned

| Layer | Current Status | Notes |
|---|---|---|
| SQLite WAL schema, Foreign Keys & `AFTER UPDATE` invalidation triggers | **Implemented** (`migrations/001_helix_core.sql`) | Runs out of the box on clean checkout. |
| Disk byte SHA-256 ingestion & pre-VAT tamper scanner | **Implemented** (`helix_server.py`) | Streams raw files in 64 KiB chunks. |
| PBKDF2-HMAC-SHA256 auth, RBAC roles & tenant isolation | **Implemented** (`helix_server.py`) | Constant-time `hmac.compare_digest` verification + per-tenant grant join. |
| Double-entry ledger postings, reversals & UK VAT `STANDARD_ACCRUAL` + `CASH_ACCOUNTING` | **Implemented** (`helix_server.py`) | Integer pence throughout; zero float math. |
| `index.html` wired to backend HTTP API | **Implemented** (`index.html` -> `helix_server.py`) | Auto-connects to `/api/*` when run via `python3 helix_server.py --port 8890`; falls back cleanly if viewed statically. |
| HMRC MTD VAT submission endpoint | **Simulated Locally** (`/api/hmrc-sandbox/vat-returns`) | Validates HMRC MTD VAT v1.0 JSON schema, 9-digit VRN, and whole-pound Boxes 6–9 locally; returns `"live_hmrc_api_called": false`. |
| Live HMRC Developer Hub OAuth2 + Fraud Prevention Headers & Live Open Banking / OCR Ingestion | **Planned (Phase 2)** | Scoped for the next milestone using real HMRC sandbox client credentials and TrueLayer/Plaid UK webhooks. |
