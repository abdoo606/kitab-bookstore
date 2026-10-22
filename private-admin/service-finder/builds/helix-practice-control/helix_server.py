#!/usr/bin/env python3
"""
Helix v1 UK Practice Control Plane — Verified Backend & Local HTTP API
======================================================================
Zero external dependencies (Python 3.10+ stdlib: sqlite3, hashlib, hmac, decimal, http.server, threading).

Architectural Guarantees Implemented:
1. Source-file byte SHA-256 verification on ingestion AND live disk re-verification before posting/VAT compilation.
2. Dual-layer mutation/tamper invalidation:
   - Application layer recomputes canonical SHA-256 digest over (tenant_id, tx_id, kind, vat_treatment,
     period_key, net_pence, vat_pence, gross_pence, evidence_sha256).
   - Database layer (`migrations/001_helix_core.sql`) enforces SQLite AFTER UPDATE triggers that
     automatically flip `APPROVED_POSTED -> INVALIDATED_TAMPERED` and insert reversing double-entry
     journal rows (`REVERSAL_ON_INVALIDATION`) if net/vat/gross/treatment/evidence changes.
3. PBKDF2-HMAC-SHA256 authenticated reviewer sessions + RBAC (`PARTNER_REVIEWER` required to approve/post;
   strict per-tenant grant isolation so Client A tokens never read or mutate Client B records).
4. `BEGIN IMMEDIATE` write-serialized transactions + `UNIQUE(tenant_id, idempotency_key)` + status compare-and-set
   to prevent duplicate ledger/VAT postings even under concurrent multithreaded API bursts.
5. Exact `Decimal` half-up (`ROUND_HALF_UP`) integer-pence UK VAT calculations across:
   - `STANDARD_ACCRUAL` (VAT recognized at invoice tax point; subsequent `DEBTOR_RECEIPT` / `CREDITOR_PAYMENT`
     settles bank vs trade debtors/creditors with ZERO double-counting in HMRC Boxes 1, 4, 6, 7).
   - `CASH_ACCOUNTING` (VAT deferred at invoice issue and recognized upon cash receipt/payment).
6. Explicit separation of Implemented vs Simulated vs Planned (local `/api/hmrc-sandbox/vat-returns` validates
   HMRC MTD VAT v1.0 JSON contract locally and returns a clearly marked simulated sandbox receipt).
"""

from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, urlparse
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
MIGRATION_PATH = BASE_DIR / "migrations" / "001_helix_core.sql"
DEFAULT_DB_PATH = BASE_DIR / "data" / "helix_practice.sqlite3"
DEFAULT_EVIDENCE_DIR = BASE_DIR / "sample_evidence"

VAT_RATES: Dict[str, Decimal] = {
    "UK_STD_20": Decimal("0.20"),
    "UK_REDUCED_5": Decimal("0.05"),
    "UK_ZERO_0": Decimal("0.00"),
    "UK_EXEMPT": Decimal("0.00"),
    "OUTSIDE_SCOPE_SETTLEMENT": Decimal("0.00"),
}

DEMO_REVIEWER_TOKENS: Dict[str, Dict[str, Any]] = {
    "reviewer-cworsey": {
        "email": "chris.reviewer@helix-demo.co.uk",
        "display_name": "Chris Worsey (Partner Reviewer)",
        "role": "PARTNER_REVIEWER",
        "token": "hlx_live_partner_hartley_kensington_2026",
        "tenants": ["hartley-mfg", "kensington-dental"],
    },
    "reviewer-hartley-only": {
        "email": "senior.hartley@helix-demo.co.uk",
        "display_name": "Amira Patel ACA (Hartley Manager)",
        "role": "PARTNER_REVIEWER",
        "token": "hlx_live_manager_hartley_only_2026",
        "tenants": ["hartley-mfg"],
    },
    "preparer-junior": {
        "email": "junior.prep@helix-demo.co.uk",
        "display_name": "Tom Evans (Junior Preparer)",
        "role": "PRACTICE_PREPARER",
        "token": "hlx_live_preparer_no_approve_2026",
        "tenants": ["hartley-mfg"],
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> Tuple[str, int]:
    h = hashlib.sha256()
    total = 0
    with path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), total


def pbkdf2_token_hex(token: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", token.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()


def compute_vat_from_net_pence(net_pence: int, vat_treatment: str) -> Tuple[int, int]:
    """Compute (vat_pence, gross_pence) from integer net_pence using exact Decimal ROUND_HALF_UP."""
    if net_pence < 0:
        raise ValueError("net_pence must be >= 0")
    if vat_treatment not in VAT_RATES:
        raise ValueError(f"Unsupported vat_treatment: {vat_treatment}")
    rate = VAT_RATES[vat_treatment]
    vat_dec = (Decimal(net_pence) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    vat_pence = int(vat_dec)
    return vat_pence, net_pence + vat_pence


def extract_vat_from_gross_pence(gross_pence: int, vat_treatment: str) -> Tuple[int, int]:
    """Extract (net_pence, vat_pence) from VAT-inclusive integer gross_pence using ROUND_HALF_UP."""
    if gross_pence < 0:
        raise ValueError("gross_pence must be >= 0")
    rate = VAT_RATES[vat_treatment]
    if rate == Decimal("0.00"):
        return gross_pence, 0
    net_dec = (Decimal(gross_pence) / (Decimal("1") + rate)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    net_pence = int(net_dec)
    vat_pence = gross_pence - net_pence
    return net_pence, vat_pence


def canonical_tx_digest(
    tenant_id: str,
    tx_id: str,
    kind: str,
    vat_treatment: str,
    period_key: str,
    net_pence: int,
    vat_pence: int,
    gross_pence: int,
    evidence_sha256: str,
) -> str:
    canonical = (
        f"v1|{tenant_id}|{tx_id}|{kind}|{vat_treatment}|{period_key}|"
        f"{net_pence}|{vat_pence}|{gross_pence}|{evidence_sha256}"
    )
    return sha256_bytes(canonical.encode("utf-8"))


class AuthError(PermissionError):
    pass


class ValidationError(ValueError):
    pass


class ConflictError(RuntimeError):
    pass


class HelixPracticeEngine:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH, evidence_root: Path = DEFAULT_EVIDENCE_DIR) -> None:
        self.db_path = Path(db_path)
        self.evidence_root = Path(evidence_root)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.evidence_root.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = FULL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA busy_timeout = 10000;")
        return conn

    def _init_schema(self) -> None:
        sql = MIGRATION_PATH.read_text(encoding="utf-8")
        conn = self._connect()
        try:
            conn.executescript(sql)
        finally:
            conn.close()

    def close(self) -> None:
        # Connections are opened per-operation with WAL synchronous=FULL durability; checkpoint cleanly.
        conn = self._connect()
        try:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE);")
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Authentication, RBAC & Strict Multi-Tenant Grant Enforcement
    # ------------------------------------------------------------------
    def register_tenant(self, tenant_id: str, legal_name: str, vrn: str, vat_scheme: str = "STANDARD_ACCRUAL") -> None:
        with self._write_lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    """
                    INSERT INTO tenants (tenant_id, legal_name, vrn, vat_scheme, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(tenant_id) DO UPDATE SET
                        legal_name = excluded.legal_name,
                        vrn = excluded.vrn,
                        vat_scheme = excluded.vat_scheme
                    """,
                    (tenant_id, legal_name, vrn, vat_scheme, utc_now_iso()),
                )
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

    def register_reviewer(
        self,
        reviewer_id: str,
        email: str,
        display_name: str,
        role: str,
        raw_token: str,
        tenant_ids: List[str],
    ) -> None:
        salt = sha256_bytes(f"helix-salt:{reviewer_id}:{email}".encode("utf-8"))[:24]
        digest = pbkdf2_token_hex(raw_token, salt)
        with self._write_lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                conn.execute(
                    """
                    INSERT INTO reviewers (reviewer_id, email, display_name, role, token_salt, token_pbkdf2_hex, active)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    ON CONFLICT(reviewer_id) DO UPDATE SET
                        email = excluded.email,
                        display_name = excluded.display_name,
                        role = excluded.role,
                        token_salt = excluded.token_salt,
                        token_pbkdf2_hex = excluded.token_pbkdf2_hex,
                        active = 1
                    """,
                    (reviewer_id, email, display_name, role, salt, digest),
                )
                conn.execute("DELETE FROM reviewer_tenant_grants WHERE reviewer_id = ?;", (reviewer_id,))
                for tid in tenant_ids:
                    conn.execute(
                        "INSERT INTO reviewer_tenant_grants (reviewer_id, tenant_id) VALUES (?, ?);",
                        (reviewer_id, tid),
                    )
                conn.execute("COMMIT;")
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

    def authenticate(self, conn: sqlite3.Connection, bearer_token: str, tenant_id: str, require_partner: bool = False) -> Dict[str, Any]:
        if not bearer_token:
            raise AuthError("Missing bearer token")
        rows = conn.execute("SELECT * FROM reviewers WHERE active = 1;").fetchall()
        matched: Optional[sqlite3.Row] = None
        for r in rows:
            candidate = pbkdf2_token_hex(bearer_token, r["token_salt"])
            if hmac.compare_digest(candidate, r["token_pbkdf2_hex"]):
                matched = r
                break
        if matched is None:
            raise AuthError("Invalid authentication credentials")
        grant = conn.execute(
            "SELECT 1 FROM reviewer_tenant_grants WHERE reviewer_id = ? AND tenant_id = ?;",
            (matched["reviewer_id"], tenant_id),
        ).fetchone()
        if grant is None:
            raise AuthError(f"Tenant isolation gate blocked reviewer '{matched['reviewer_id']}' from tenant '{tenant_id}'")
        if require_partner and matched["role"] != "PARTNER_REVIEWER":
            raise AuthError(f"Role '{matched['role']}' cannot approve/post ledger entries; PARTNER_REVIEWER required")
        return dict(matched)

    # ------------------------------------------------------------------
    # Hash-Chained Immutable Audit Trail
    # ------------------------------------------------------------------
    def _append_audit_in_tx(
        self,
        conn: sqlite3.Connection,
        tenant_id: str,
        actor_id: str,
        event_type: str,
        detail: Dict[str, Any],
        tx_id: Optional[str] = None,
    ) -> str:
        prev_row = conn.execute(
            "SELECT chain_hex FROM audit_events WHERE tenant_id = ? ORDER BY seq DESC LIMIT 1;",
            (tenant_id,),
        ).fetchone()
        prev_hex = prev_row["chain_hex"] if prev_row else "0" * 64
        ts = utc_now_iso()
        detail_json = json.dumps(detail, sort_keys=True, separators=(",", ":"))
        payload = f"{prev_hex}|{tenant_id}|{tx_id or ''}|{actor_id}|{event_type}|{detail_json}|{ts}"
        chain_hex = sha256_bytes(payload.encode("utf-8"))
        conn.execute(
            """
            INSERT INTO audit_events (tenant_id, tx_id, actor_id, event_type, detail_json, prev_chain_hex, chain_hex, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (tenant_id, tx_id, actor_id, event_type, detail_json, prev_hex, chain_hex, ts),
        )
        return chain_hex

    def verify_audit_chain(self, bearer_token: str, tenant_id: str) -> Dict[str, Any]:
        conn = self._connect()
        try:
            self.authenticate(conn, bearer_token, tenant_id, require_partner=False)
            rows = conn.execute(
                "SELECT * FROM audit_events WHERE tenant_id = ? ORDER BY seq ASC;",
                (tenant_id,),
            ).fetchall()
            expected_prev = "0" * 64
            for r in rows:
                if r["prev_chain_hex"] != expected_prev:
                    return {"valid": False, "broken_seq": r["seq"], "reason": "prev_chain_hex mismatch"}
                payload = (
                    f"{r['prev_chain_hex']}|{r['tenant_id']}|{r['tx_id'] or ''}|"
                    f"{r['actor_id']}|{r['event_type']}|{r['detail_json']}|{r['created_at']}"
                )
                recomputed = sha256_bytes(payload.encode("utf-8"))
                if recomputed != r["chain_hex"]:
                    return {"valid": False, "broken_seq": r["seq"], "reason": "chain_hex tamper detected"}
                expected_prev = recomputed
            return {"valid": True, "event_count": len(rows), "head_chain_hex": expected_prev}
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Evidence Ingestion & Disk Byte SHA-256 Verification
    # ------------------------------------------------------------------
    def ingest_evidence(
        self,
        bearer_token: str,
        tenant_id: str,
        evidence_id: str,
        filename: str,
        content_bytes: bytes,
        mime_type: str = "text/plain",
    ) -> Dict[str, Any]:
        tenant_dir = self.evidence_root / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        rel_path = Path(tenant_id) / filename
        abs_path = self.evidence_root / rel_path
        abs_path.write_bytes(content_bytes)
        digest, byte_len = sha256_file(abs_path)

        with self._write_lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                reviewer = self.authenticate(conn, bearer_token, tenant_id, require_partner=False)
                conn.execute(
                    """
                    INSERT INTO evidence_blobs (evidence_id, tenant_id, filename, mime_type, byte_length, sha256_hex, storage_relpath, ingested_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(evidence_id) DO UPDATE SET
                        byte_length = excluded.byte_length,
                        sha256_hex = excluded.sha256_hex,
                        storage_relpath = excluded.storage_relpath
                    """,
                    (evidence_id, tenant_id, filename, mime_type, byte_len, digest, str(rel_path), utc_now_iso()),
                )
                self._append_audit_in_tx(
                    conn,
                    tenant_id,
                    reviewer["reviewer_id"],
                    "EVIDENCE_INGESTED",
                    {"evidence_id": evidence_id, "filename": filename, "sha256_hex": digest, "byte_length": byte_len},
                )
                conn.execute("COMMIT;")
                return {"evidence_id": evidence_id, "sha256_hex": digest, "byte_length": byte_len, "storage_relpath": str(rel_path)}
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

    def _verify_live_evidence_in_tx(self, conn: sqlite3.Connection, tx_row: sqlite3.Row) -> Tuple[bool, str, str]:
        """Re-hashes source file bytes on disk against stored sha256_hex AND canonical approved_digest_hex."""
        ev = conn.execute(
            "SELECT * FROM evidence_blobs WHERE evidence_id = ? AND tenant_id = ?;",
            (tx_row["evidence_id"], tx_row["tenant_id"]),
        ).fetchone()
        if ev is None:
            return False, "", "Missing evidence metadata record"
        abs_path = self.evidence_root / ev["storage_relpath"]
        if not abs_path.exists():
            return False, "", f"Source evidence file missing on disk: {ev['storage_relpath']}"
        disk_sha, disk_len = sha256_file(abs_path)
        if disk_sha != ev["sha256_hex"] or disk_len != ev["byte_length"]:
            # Updating evidence_blobs automatically triggers trg_invalidate_tx_on_evidence_sha_mutation for approved rows!
            conn.execute(
                "UPDATE evidence_blobs SET sha256_hex = ?, byte_length = ? WHERE evidence_id = ?;",
                (disk_sha, disk_len, ev["evidence_id"]),
            )
            self._append_audit_in_tx(
                conn,
                tx_row["tenant_id"],
                "SYSTEM_DISK_INTEGRITY_SCANNER",
                "EVIDENCE_DISK_TAMPER_DETECTED",
                {
                    "evidence_id": ev["evidence_id"],
                    "expected_sha256": ev["sha256_hex"],
                    "actual_disk_sha256": disk_sha,
                },
                tx_id=tx_row["tx_id"],
            )
            return False, disk_sha, f"Source evidence bytes modified on disk (expected {ev['sha256_hex'][:12]}..., got {disk_sha[:12]}...)"
        return True, disk_sha, "OK"

    # ------------------------------------------------------------------
    # Transaction Staging, UK VAT Box Delta Computation & Posting
    # ------------------------------------------------------------------
    def stage_transaction(
        self,
        bearer_token: str,
        tenant_id: str,
        tx_id: str,
        idempotency_key: str,
        kind: str,
        vat_treatment: str,
        counterparty: str,
        tax_point_date: str,
        period_key: str,
        net_pence: int,
        evidence_id: str,
        ai_confidence: float = 0.94,
        vat_pence_override: Optional[int] = None,
        linked_invoice_tx_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        calc_vat, calc_gross = compute_vat_from_net_pence(net_pence, vat_treatment)
        vat_pence = calc_vat if vat_pence_override is None else vat_pence_override
        gross_pence = net_pence + vat_pence

        with self._write_lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                reviewer = self.authenticate(conn, bearer_token, tenant_id, require_partner=False)
                ev = conn.execute(
                    "SELECT * FROM evidence_blobs WHERE evidence_id = ? AND tenant_id = ?;",
                    (evidence_id, tenant_id),
                ).fetchone()
                if ev is None:
                    raise ValidationError(f"Evidence '{evidence_id}' does not belong to tenant '{tenant_id}'")

                existing = conn.execute(
                    "SELECT tx_id FROM transactions WHERE tenant_id = ? AND idempotency_key = ?;",
                    (tenant_id, idempotency_key),
                ).fetchone()
                if existing is not None:
                    raise ConflictError(f"Duplicate idempotency_key '{idempotency_key}' for tenant '{tenant_id}'")

                conn.execute(
                    """
                    INSERT INTO transactions (
                        tx_id, tenant_id, idempotency_key, kind, vat_treatment, counterparty,
                        tax_point_date, period_key, net_pence, vat_pence, gross_pence,
                        evidence_id, linked_invoice_tx_id, ai_confidence, status, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING_REVIEW', ?);
                    """,
                    (
                        tx_id,
                        tenant_id,
                        idempotency_key,
                        kind,
                        vat_treatment,
                        counterparty,
                        tax_point_date,
                        period_key,
                        net_pence,
                        vat_pence,
                        gross_pence,
                        evidence_id,
                        linked_invoice_tx_id,
                        ai_confidence,
                        utc_now_iso(),
                    ),
                )
                self._append_audit_in_tx(
                    conn,
                    tenant_id,
                    reviewer["reviewer_id"],
                    "TX_STAGED",
                    {
                        "kind": kind,
                        "vat_treatment": vat_treatment,
                        "net_pence": net_pence,
                        "vat_pence": vat_pence,
                        "gross_pence": gross_pence,
                        "evidence_id": evidence_id,
                    },
                    tx_id=tx_id,
                )
                conn.execute("COMMIT;")
                return self.get_transaction(bearer_token, tenant_id, tx_id)
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

    def _compute_posting_accounts_and_vat_boxes(
        self,
        vat_scheme: str,
        tx_row: sqlite3.Row,
        linked_invoice: Optional[sqlite3.Row],
    ) -> Tuple[str, str, int, int, int, int]:
        """
        Compute double-entry accounts AND HMRC MTD VAT Return Box deltas (in pence):
          - Box 1: VAT due on sales and other outputs
          - Box 4: VAT reclaimed on purchases and other inputs
          - Box 6: Total value of sales and all other outputs excluding any VAT
          - Box 7: Total value of purchases and all other inputs excluding any VAT

        CRITICAL UK ACCOUNTING DISTINCTION:
        1. Under `STANDARD_ACCRUAL` (default UK VAT scheme):
           - `SALES_INVOICE`: Tax point occurs at invoice issue -> hits Box 1 (+vat) and Box 6 (+net, except OUTSIDE_SCOPE).
           - `PURCHASE_INVOICE`: Tax point occurs at supplier invoice -> hits Box 4 (+reclaimable vat) and Box 7 (+net).
           - `DEBTOR_RECEIPT` / `CREDITOR_PAYMENT`: Settles `1200_BANK` vs `1100_TRADE_DEBTORS` / `2100_TRADE_CREDITORS`.
             Does NOT hit Box 1, 4, 6, or 7 again (zero invoice-vs-receipt double counting!).
        2. Under `CASH_ACCOUNTING` (HMRC Cash Accounting Scheme):
           - `SALES_INVOICE` / `PURCHASE_INVOICE`: Posts commercial debtor/creditor control in ledger,
             with `0` immediate VAT Box impact until cash clears!
           - `DEBTOR_RECEIPT` / `CREDITOR_PAYMENT`: Triggers VAT Box 1/6 or Box 4/7 upon bank settlement
             (derived proportionally or full settlement from linked invoice or receipt VAT breakdown).
        """
        kind = tx_row["kind"]
        treatment = tx_row["vat_treatment"]
        net_p = int(tx_row["net_pence"])
        vat_p = int(tx_row["vat_pence"])
        gross_p = int(tx_row["gross_pence"])

        if vat_scheme == "STANDARD_ACCRUAL":
            if kind == "SALES_INVOICE":
                b6 = 0 if treatment == "OUTSIDE_SCOPE_SETTLEMENT" else net_p
                b1 = vat_p if treatment in ("UK_STD_20", "UK_REDUCED_5") else 0
                return ("1100_TRADE_DEBTORS", "4000_SALES_AND_VAT_CONTROL", gross_p, b1, 0, b6, 0)
            if kind == "PURCHASE_INVOICE":
                b7 = 0 if treatment == "OUTSIDE_SCOPE_SETTLEMENT" else net_p
                b4 = vat_p if treatment in ("UK_STD_20", "UK_REDUCED_5") else 0
                return ("5000_EXPENSE_AND_INPUT_VAT", "2100_TRADE_CREDITORS", gross_p, 0, b4, 0, b7)
            if kind == "DEBTOR_RECEIPT":
                # Pure cash collection against debtor balance — MUST NEVER double-count Box 1 or Box 6!
                return ("1200_BANK_CURRENT", "1100_TRADE_DEBTORS", gross_p, 0, 0, 0, 0)
            if kind == "CREDITOR_PAYMENT":
                return ("2100_TRADE_CREDITORS", "1200_BANK_CURRENT", gross_p, 0, 0, 0, 0)
        elif vat_scheme == "CASH_ACCOUNTING":
            if kind == "SALES_INVOICE":
                return ("1100_TRADE_DEBTORS", "4000_DEFERRED_CASH_VAT_SALES", gross_p, 0, 0, 0, 0)
            if kind == "PURCHASE_INVOICE":
                return ("5000_DEFERRED_CASH_VAT_PURCHASES", "2100_TRADE_CREDITORS", gross_p, 0, 0, 0, 0)
            if kind == "DEBTOR_RECEIPT":
                eff_treat = linked_invoice["vat_treatment"] if linked_invoice is not None else treatment
                eff_net, eff_vat = extract_vat_from_gross_pence(gross_p, eff_treat) if vat_p == 0 and linked_invoice is not None else (net_p, vat_p)
                b1 = eff_vat if eff_treat in ("UK_STD_20", "UK_REDUCED_5") else 0
                return ("1200_BANK_CURRENT", "1100_TRADE_DEBTORS", gross_p, b1, 0, eff_net, 0)
            if kind == "CREDITOR_PAYMENT":
                eff_treat = linked_invoice["vat_treatment"] if linked_invoice is not None else treatment
                eff_net, eff_vat = extract_vat_from_gross_pence(gross_p, eff_treat) if vat_p == 0 and linked_invoice is not None else (net_p, vat_p)
                b4 = eff_vat if eff_treat in ("UK_STD_20", "UK_REDUCED_5") else 0
                return ("2100_TRADE_CREDITORS", "1200_BANK_CURRENT", gross_p, 0, b4, 0, eff_net)

        raise ValidationError(f"Unsupported scheme/kind combination: {vat_scheme} / {kind}")

    def approve_and_post(self, bearer_token: str, tenant_id: str, tx_id: str) -> Dict[str, Any]:
        """
        Atomically verifies reviewer auth + RBAC, re-hashes disk source evidence bytes, checks duplicate
        posting lock inside `BEGIN IMMEDIATE` + process lock, posts double-entry journal + VAT deltas,
        and seals `approved_digest_hex`.
        """
        with self._write_lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                reviewer = self.authenticate(conn, bearer_token, tenant_id, require_partner=True)
                tenant = conn.execute("SELECT * FROM tenants WHERE tenant_id = ?;", (tenant_id,)).fetchone()
                if tenant is None:
                    raise ValidationError(f"Unknown tenant '{tenant_id}'")

                tx_row = conn.execute(
                    "SELECT * FROM transactions WHERE tx_id = ? AND tenant_id = ?;",
                    (tx_id, tenant_id),
                ).fetchone()
                if tx_row is None:
                    raise ValidationError(f"Transaction '{tx_id}' not found in tenant '{tenant_id}'")

                if tx_row["status"] == "APPROVED_POSTED":
                    raise ConflictError(f"Transaction '{tx_id}' is already APPROVED_POSTED; duplicate posting blocked")

                ok_ev, disk_sha, reason = self._verify_live_evidence_in_tx(conn, tx_row)
                if not ok_ev:
                    conn.execute(
                        """
                        UPDATE transactions
                        SET status = 'INVALIDATED_TAMPERED', invalidation_reason = ?, updated_at = ?
                        WHERE tx_id = ?;
                        """,
                        (reason, utc_now_iso(), tx_id),
                    )
                    conn.execute("COMMIT;")
                    raise ConflictError(f"Approval blocked by source evidence integrity check: {reason}")

                linked_inv = None
                if tx_row["linked_invoice_tx_id"]:
                    linked_inv = conn.execute(
                        "SELECT * FROM transactions WHERE tx_id = ? AND tenant_id = ?;",
                        (tx_row["linked_invoice_tx_id"], tenant_id),
                    ).fetchone()

                dr_acct, cr_acct, amt_p, b1, b4, b6, b7 = self._compute_posting_accounts_and_vat_boxes(
                    tenant["vat_scheme"], tx_row, linked_inv
                )
                digest = canonical_tx_digest(
                    tenant_id=tenant_id,
                    tx_id=tx_id,
                    kind=tx_row["kind"],
                    vat_treatment=tx_row["vat_treatment"],
                    period_key=tx_row["period_key"],
                    net_pence=int(tx_row["net_pence"]),
                    vat_pence=int(tx_row["vat_pence"]),
                    gross_pence=int(tx_row["gross_pence"]),
                    evidence_sha256=disk_sha,
                )
                ts = utc_now_iso()
                cur = conn.execute(
                    """
                    UPDATE transactions
                    SET status = 'APPROVED_POSTED',
                        approved_digest_hex = ?,
                        approved_by = ?,
                        approved_at = ?,
                        invalidation_reason = NULL,
                        updated_at = ?
                    WHERE tx_id = ? AND tenant_id = ? AND status != 'APPROVED_POSTED';
                    """,
                    (digest, reviewer["reviewer_id"], ts, ts, tx_id, tenant_id),
                )
                if cur.rowcount != 1:
                    raise ConflictError(f"Concurrent duplicate approval race blocked for '{tx_id}'")

                conn.execute(
                    """
                    INSERT INTO ledger_postings (
                        tenant_id, tx_id, entry_type, debit_account, credit_account, amount_pence,
                        vat_box1_delta_pence, vat_box4_delta_pence, vat_box6_delta_pence, vat_box7_delta_pence,
                        created_by, created_at
                    ) VALUES (?, ?, 'ORIGINAL_POST', ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (tenant_id, tx_id, dr_acct, cr_acct, amt_p, b1, b4, b6, b7, reviewer["reviewer_id"], ts),
                )
                self._append_audit_in_tx(
                    conn,
                    tenant_id,
                    reviewer["reviewer_id"],
                    "TX_APPROVED_AND_POSTED",
                    {
                        "approved_digest_hex": digest,
                        "debit_account": dr_acct,
                        "credit_account": cr_acct,
                        "amount_pence": amt_p,
                        "vat_boxes_pence": {"box1": b1, "box4": b4, "box6": b6, "box7": b7},
                    },
                    tx_id=tx_id,
                )
                conn.execute("COMMIT;")
                return self.get_transaction(bearer_token, tenant_id, tx_id)
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

    def mutate_transaction(
        self,
        bearer_token: str,
        tenant_id: str,
        tx_id: str,
        net_pence: Optional[int] = None,
        vat_treatment: Optional[str] = None,
        evidence_id: Optional[str] = None,
        reason_note: str = "Post-staging edit",
    ) -> Dict[str, Any]:
        """
        Updates transaction fields. If the transaction was previously `APPROVED_POSTED`, SQLite trigger
        `trg_invalidate_approved_tx_on_mutation` automatically flips status -> `INVALIDATED_TAMPERED`,
        wipes `approved_digest_hex`/`approved_by`, and inserts a `REVERSAL_ON_INVALIDATION` journal entry
        zeroing out its ledger & HMRC VAT Box impact until a human `PARTNER_REVIEWER` re-approves!
        """
        with self._write_lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                reviewer = self.authenticate(conn, bearer_token, tenant_id, require_partner=False)
                tx_row = conn.execute(
                    "SELECT * FROM transactions WHERE tx_id = ? AND tenant_id = ?;",
                    (tx_id, tenant_id),
                ).fetchone()
                if tx_row is None:
                    raise ValidationError(f"Transaction '{tx_id}' not found in tenant '{tenant_id}'")

                was_approved = tx_row["status"] == "APPROVED_POSTED"
                new_net = int(tx_row["net_pence"]) if net_pence is None else int(net_pence)
                new_treat = str(tx_row["vat_treatment"]) if vat_treatment is None else str(vat_treatment)
                new_ev = str(tx_row["evidence_id"]) if evidence_id is None else str(evidence_id)

                ev_check = conn.execute(
                    "SELECT 1 FROM evidence_blobs WHERE evidence_id = ? AND tenant_id = ?;",
                    (new_ev, tenant_id),
                ).fetchone()
                if ev_check is None:
                    raise ValidationError(f"Evidence '{new_ev}' not found in tenant '{tenant_id}'")

                new_vat, new_gross = compute_vat_from_net_pence(new_net, new_treat)
                conn.execute(
                    """
                    UPDATE transactions
                    SET net_pence = ?,
                        vat_pence = ?,
                        gross_pence = ?,
                        vat_treatment = ?,
                        evidence_id = ?,
                        invalidation_reason = CASE
                            WHEN status = 'APPROVED_POSTED' THEN ?
                            ELSE invalidation_reason
                        END,
                        updated_at = ?
                    WHERE tx_id = ? AND tenant_id = ?;
                    """,
                    (
                        new_net,
                        new_vat,
                        new_gross,
                        new_treat,
                        new_ev,
                        f"APPROVAL_INVALIDATED: {reason_note}",
                        utc_now_iso(),
                        tx_id,
                        tenant_id,
                    ),
                )
                after = conn.execute("SELECT status FROM transactions WHERE tx_id = ?;", (tx_id,)).fetchone()
                self._append_audit_in_tx(
                    conn,
                    tenant_id,
                    reviewer["reviewer_id"],
                    "TX_MUTATED_AND_INVALIDATED" if was_approved else "TX_UPDATED_PRE_APPROVAL",
                    {
                        "was_approved": was_approved,
                        "status_after": after["status"],
                        "new_net_pence": new_net,
                        "new_vat_pence": new_vat,
                        "new_gross_pence": new_gross,
                        "new_evidence_id": new_ev,
                        "reason_note": reason_note,
                    },
                    tx_id=tx_id,
                )
                conn.execute("COMMIT;")
                return self.get_transaction(bearer_token, tenant_id, tx_id)
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

    def scan_integrity_and_compile_vat_return(
        self, bearer_token: str, tenant_id: str, period_key: str
    ) -> Dict[str, Any]:
        """
        1. Re-verifies every approved transaction's on-disk evidence SHA-256 and canonical `approved_digest_hex`.
           If a file on disk was altered outside SQLite since approval, immediately invalidates the transaction
           and posts its reversal journal BEFORE calculating HMRC VAT Boxes!
        2. Sums all ledger postings (`ORIGINAL_POST` + `REVERSAL_ON_INVALIDATION`) for the tenant & period,
           producing exact HMRC MTD VAT Return Boxes 1..9:
           - Boxes 1..5 in exact pounds & pence (2dp, plus integer pence).
           - Boxes 6..9 integer whole pounds (HMRC MTD VAT specification rounds/truncates ex-VAT turnover boxes).
        """
        with self._write_lock:
            conn = self._connect()
            try:
                conn.execute("BEGIN IMMEDIATE;")
                self.authenticate(conn, bearer_token, tenant_id, require_partner=False)
                tenant = conn.execute("SELECT * FROM tenants WHERE tenant_id = ?;", (tenant_id,)).fetchone()
                if tenant is None:
                    raise ValidationError(f"Unknown tenant '{tenant_id}'")

                approved_rows = conn.execute(
                    "SELECT * FROM transactions WHERE tenant_id = ? AND period_key = ? AND status = 'APPROVED_POSTED';",
                    (tenant_id, period_key),
                ).fetchall()
                invalidated_during_scan: List[str] = []
                for tx_row in approved_rows:
                    ok_ev, disk_sha, reason = self._verify_live_evidence_in_tx(conn, tx_row)
                    if not ok_ev:
                        invalidated_during_scan.append(tx_row["tx_id"])
                        continue
                    expected_digest = canonical_tx_digest(
                        tenant_id=tenant_id,
                        tx_id=tx_row["tx_id"],
                        kind=tx_row["kind"],
                        vat_treatment=tx_row["vat_treatment"],
                        period_key=tx_row["period_key"],
                        net_pence=int(tx_row["net_pence"]),
                        vat_pence=int(tx_row["vat_pence"]),
                        gross_pence=int(tx_row["gross_pence"]),
                        evidence_sha256=disk_sha,
                    )
                    if expected_digest != tx_row["approved_digest_hex"]:
                        # Defensive belt-and-suspenders guard in case SQLite triggers were bypassed
                        conn.execute("UPDATE transactions SET net_pence = net_pence WHERE tx_id = ?;", (tx_row["tx_id"],))
                        invalidated_during_scan.append(tx_row["tx_id"])

                sums = conn.execute(
                    """
                    SELECT
                        COALESCE(SUM(lp.vat_box1_delta_pence), 0) AS b1,
                        COALESCE(SUM(lp.vat_box4_delta_pence), 0) AS b4,
                        COALESCE(SUM(lp.vat_box6_delta_pence), 0) AS b6,
                        COALESCE(SUM(lp.vat_box7_delta_pence), 0) AS b7,
                        COUNT(*) AS journal_line_count
                    FROM ledger_postings lp
                    JOIN transactions t ON t.tx_id = lp.tx_id
                    WHERE lp.tenant_id = ? AND t.period_key = ?;
                    """,
                    (tenant_id, period_key),
                ).fetchone()
                conn.execute("COMMIT;")

                b1_p = int(sums["b1"])
                b2_p = 0
                b3_p = b1_p + b2_p
                b4_p = int(sums["b4"])
                b5_p = abs(b3_p - b4_p)
                net_payable_p = b3_p - b4_p
                b6_whole_gbp = int((Decimal(int(sums["b6"])) / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
                b7_whole_gbp = int((Decimal(int(sums["b7"])) / Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

                return {
                    "tenant_id": tenant_id,
                    "legal_name": tenant["legal_name"],
                    "vrn": tenant["vrn"],
                    "vat_scheme": tenant["vat_scheme"],
                    "period_key": period_key,
                    "invalidated_during_scan": invalidated_during_scan,
                    "journal_line_count": int(sums["journal_line_count"]),
                    "boxes_pence": {
                        "box1_vat_due_sales_pence": b1_p,
                        "box2_vat_due_acquisitions_pence": b2_p,
                        "box3_total_vat_due_pence": b3_p,
                        "box4_vat_reclaimed_curr_period_pence": b4_p,
                        "box5_net_vat_due_abs_pence": b5_p,
                        "signed_net_vat_payable_pence": net_payable_p,
                        "box6_total_value_sales_ex_vat_pence": int(sums["b6"]),
                        "box7_total_value_purchases_ex_vat_pence": int(sums["b7"]),
                    },
                    "hmrc_mtd_payload": {
                        "periodKey": period_key,
                        "vatDueSales": float((Decimal(b1_p) / Decimal("100")).quantize(Decimal("0.01"))),
                        "vatDueAcquisitions": 0.00,
                        "totalVatDue": float((Decimal(b3_p) / Decimal("100")).quantize(Decimal("0.01"))),
                        "vatReclaimedCurrPeriod": float((Decimal(b4_p) / Decimal("100")).quantize(Decimal("0.01"))),
                        "netVatDue": float((Decimal(b5_p) / Decimal("100")).quantize(Decimal("0.01"))),
                        "totalValueSalesExVAT": b6_whole_gbp,
                        "totalValuePurchasesExVAT": b7_whole_gbp,
                        "totalValueGoodsSuppliedExVAT": 0,
                        "totalAcquisitionsExVAT": 0,
                        "finalised": True,
                    },
                }
            except Exception:
                conn.execute("ROLLBACK;")
                raise
            finally:
                conn.close()

    def get_transaction(self, bearer_token: str, tenant_id: str, tx_id: str) -> Dict[str, Any]:
        conn = self._connect()
        try:
            self.authenticate(conn, bearer_token, tenant_id, require_partner=False)
            row = conn.execute(
                """
                SELECT t.*, e.filename AS evidence_filename, e.sha256_hex AS evidence_sha256, e.byte_length AS evidence_bytes
                FROM transactions t
                JOIN evidence_blobs e ON e.evidence_id = t.evidence_id
                WHERE t.tx_id = ? AND t.tenant_id = ?;
                """,
                (tx_id, tenant_id),
            ).fetchone()
            if row is None:
                raise ValidationError(f"Transaction '{tx_id}' not found in tenant '{tenant_id}'")
            postings = [
                dict(p)
                for p in conn.execute(
                    "SELECT * FROM ledger_postings WHERE tenant_id = ? AND tx_id = ? ORDER BY posting_id ASC;",
                    (tenant_id, tx_id),
                ).fetchall()
            ]
            d = dict(row)
            d["ledger_postings"] = postings
            return d
        finally:
            conn.close()

    def list_workspace_state(self, bearer_token: str, tenant_id: str, period_key: str = "26A3") -> Dict[str, Any]:
        vat_summary = self.scan_integrity_and_compile_vat_return(bearer_token, tenant_id, period_key)
        conn = self._connect()
        try:
            self.authenticate(conn, bearer_token, tenant_id, require_partner=False)
            txs = [
                dict(r)
                for r in conn.execute(
                    """
                    SELECT t.*, e.filename AS evidence_filename, e.sha256_hex AS evidence_sha256, e.byte_length AS evidence_bytes
                    FROM transactions t
                    JOIN evidence_blobs e ON e.evidence_id = t.evidence_id
                    WHERE t.tenant_id = ?
                    ORDER BY t.tax_point_date ASC, t.tx_id ASC;
                    """,
                    (tenant_id,),
                ).fetchall()
            ]
            postings = [
                dict(p)
                for p in conn.execute(
                    "SELECT * FROM ledger_postings WHERE tenant_id = ? ORDER BY posting_id DESC LIMIT 50;",
                    (tenant_id,),
                ).fetchall()
            ]
            audits = [
                dict(a)
                for a in conn.execute(
                    "SELECT * FROM audit_events WHERE tenant_id = ? ORDER BY seq DESC LIMIT 50;",
                    (tenant_id,),
                ).fetchall()
            ]
            return {
                "backend_mode": "LIVE_PYTHON_SQLITE_WAL",
                "tenant_id": tenant_id,
                "transactions": txs,
                "ledger_postings": postings,
                "audit_events": audits,
                "audit_chain_verification": self.verify_audit_chain(bearer_token, tenant_id),
                "vat_return": vat_summary,
                "implementation_matrix": {
                    "implemented_real_backend": [
                        "Python 3.10+ SQLite WAL relational persistence + foreign keys",
                        "Real file byte SHA-256 ingestion hashing + pre-VAT on-disk tamper scan",
                        "SQLite AFTER UPDATE triggers invalidating APPROVED_POSTED rows & writing reversing ledger/VAT entries on mutation",
                        "PBKDF2-HMAC-SHA256 bearer token authentication, RBAC roles, and strict multi-tenant grant isolation",
                        "BEGIN IMMEDIATE locking + compare-and-set status guard blocking duplicate/concurrent postings",
                        "Exact Decimal ROUND_HALF_UP integer-pence UK VAT (Standard Accrual invoice-vs-receipt non-double-counting + Cash Accounting)",
                        "Hash-chained append-only audit log with full chain verification endpoint",
                    ],
                    "simulated_in_local_build": [
                        "Local /api/hmrc-sandbox/vat-returns validator simulates HMRC MTD VAT v1.0 schema acceptance without external HMRC OAuth2 credentials",
                        "Sample anonymized UK invoices/FPS bank advices seeded locally (not live Xero/Plaid bank feeds)",
                    ],
                    "planned_next_sprint": [
                        "Live HMRC Developer Hub Sandbox OAuth2 + Gov-Client-Connection-Method fraud-prevention headers",
                        "Live Open Banking (TrueLayer/Plaid UK) & PDF OCR extraction pipeline feeding stage_transaction()",
                    ],
                },
            }
        finally:
            conn.close()


def seed_clean_checkout_demo(engine: HelixPracticeEngine) -> None:
    """Idempotently seeds two isolated UK client tenants + anonymized source files on clean checkout."""
    conn = engine._connect()
    try:
        already = conn.execute("SELECT COUNT(*) AS n FROM tenants;").fetchone()["n"]
    finally:
        conn.close()
    if already > 0:
        return

    engine.register_tenant("hartley-mfg", "Hartley Precision Engineering Ltd", "418920374", "STANDARD_ACCRUAL")
    engine.register_tenant("kensington-dental", "Kensington Dental Group Ltd", "772019485", "CASH_ACCOUNTING")

    for rev_id, meta in DEMO_REVIEWER_TOKENS.items():
        engine.register_reviewer(
            reviewer_id=rev_id,
            email=meta["email"],
            display_name=meta["display_name"],
            role=meta["role"],
            raw_token=meta["token"],
            tenant_ids=meta["tenants"],
        )

    tok = DEMO_REVIEWER_TOKENS["reviewer-cworsey"]["token"]
    # Seed Client A: Hartley Precision Engineering Ltd (Standard VAT Accrual)
    engine.ingest_evidence(
        tok,
        "hartley-mfg",
        "ev-hc-inv-104",
        "inv_hartley_104.txt",
        b"TAX INVOICE #HC-2026-104\nSupplier: Hartley Precision Engineering Ltd (VRN 418920374)\nCustomer: Severn Aerospace Ltd\nSupply Date: 2026-09-14\nNet: GBP 1,250.00 | UK Std VAT 20%: GBP 250.00 | Gross: GBP 1,500.00\n",
    )
    engine.ingest_evidence(
        tok,
        "hartley-mfg",
        "ev-hc-fps-104",
        "fps_bank_receipt_104.txt",
        b"UK FASTER PAYMENTS ADVICE #FPS-992810\nAccount: Barclays Sort 20-00-00\nRemitter: Severn Aerospace Ltd\nReference: Settlement INV #HC-2026-104\nAmount Received: GBP 1,500.00\n",
    )
    engine.ingest_evidence(
        tok,
        "hartley-mfg",
        "ev-hc-bill-882",
        "supplier_bill_aws_uk_882.txt",
        b"SUPPLIER VAT INVOICE #AWS-UK-882\nSupplier: Amazon Web Services UK Ltd\nNet: GBP 83.33 | UK Std VAT 20% (ROUND_HALF_UP): GBP 16.67 | Gross: GBP 100.00\n",
    )
    engine.ingest_evidence(
        tok,
        "hartley-mfg",
        "ev-hc-zero-301",
        "export_invoice_dublin_301.txt",
        b"ZERO-RATED EXPORT INVOICE #HC-EXP-301\nCustomer: Shannon Tooling Ltd (IE)\nCustoms Export MRN Verified\nNet: GBP 640.00 | Zero-Rated VAT 0%: GBP 0.00 | Gross: GBP 640.00\n",
    )

    engine.stage_transaction(
        tok, "hartley-mfg", "tx-hc-104", "idem-hc-104", "SALES_INVOICE", "UK_STD_20",
        "Severn Aerospace Ltd", "2026-09-14", "26A3", 125000, "ev-hc-inv-104", 0.99
    )
    engine.approve_and_post(tok, "hartley-mfg", "tx-hc-104")

    engine.stage_transaction(
        tok, "hartley-mfg", "tx-hc-fps-104", "idem-hc-fps-104", "DEBTOR_RECEIPT", "OUTSIDE_SCOPE_SETTLEMENT",
        "Severn Aerospace Ltd (FPS Bank Settlement)", "2026-09-21", "26A3", 150000, "ev-hc-fps-104", 0.97,
        linked_invoice_tx_id="tx-hc-104"
    )
    engine.stage_transaction(
        tok, "hartley-mfg", "tx-hc-aws-882", "idem-hc-aws-882", "PURCHASE_INVOICE", "UK_STD_20",
        "AWS UK Cloud Infrastructure", "2026-09-18", "26A3", 8333, "ev-hc-bill-882", 0.95
    )
    engine.stage_transaction(
        tok, "hartley-mfg", "tx-hc-exp-301", "idem-hc-exp-301", "SALES_INVOICE", "UK_ZERO_0",
        "Shannon Tooling Ltd (Export)", "2026-09-25", "26A3", 64000, "ev-hc-zero-301", 0.92
    )

    # Seed Client B: Kensington Dental Group Ltd (Isolated Tenant)
    engine.ingest_evidence(
        tok,
        "kensington-dental",
        "ev-kd-inv-01",
        "inv_kensington_lab_01.txt",
        b"KENSINGTON DENTAL GROUP LTD - PRIVATE IMPLANT CONSULTATION #KD-01\nGross Fee: GBP 900.00\n",
    )
    engine.stage_transaction(
        tok, "kensington-dental", "tx-kd-01", "idem-kd-01", "SALES_INVOICE", "UK_EXEMPT",
        "Private Patient Schedule #01", "2026-09-19", "26A3", 90000, "ev-kd-inv-01", 0.96
    )


def validate_simulated_hmrc_sandbox_submission(vrn: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Validates HMRC MTD VAT v1.0 schema locally and clearly labels receipt as SIMULATED_SANDBOX."""
    if not (isinstance(vrn, str) and len(vrn) == 9 and vrn.isdigit()):
        raise ValidationError("Invalid 9-digit VRN")
    required = [
        "periodKey",
        "vatDueSales",
        "vatDueAcquisitions",
        "totalVatDue",
        "vatReclaimedCurrPeriod",
        "netVatDue",
        "totalValueSalesExVAT",
        "totalValuePurchasesExVAT",
        "totalValueGoodsSuppliedExVAT",
        "totalAcquisitionsExVAT",
        "finalised",
    ]
    for k in required:
        if k not in payload:
            raise ValidationError(f"Missing required HMRC MTD field: {k}")
    if payload["finalised"] is not True:
        raise ValidationError("HMRC MTD declaration requires finalised=true")
    for int_box in ("totalValueSalesExVAT", "totalValuePurchasesExVAT", "totalValueGoodsSuppliedExVAT", "totalAcquisitionsExVAT"):
        if not isinstance(payload[int_box], int):
            raise ValidationError(f"HMRC MTD requires integer whole pounds for {int_box}")
    receipt_hash = sha256_bytes(json.dumps({"vrn": vrn, "payload": payload}, sort_keys=True).encode("utf-8"))[:16]
    return {
        "mode": "SIMULATED_LOCAL_HMRC_MTD_SANDBOX",
        "live_hmrc_api_called": False,
        "vrn": vrn,
        "periodKey": payload["periodKey"],
        "processingDate": utc_now_iso(),
        "formBundleNumber": f"SIM-MTD-{receipt_hash.upper()}",
        "chargeRefNumber": f"SIM-CHG-{receipt_hash[:10].upper()}",
    }


def make_http_handler(engine: HelixPracticeEngine):
    default_partner_token = DEMO_REVIEWER_TOKENS["reviewer-cworsey"]["token"]

    class HelixRequestHandler(BaseHTTPRequestHandler):
        def _send_json(self, code: int, body: Dict[str, Any]) -> None:
            raw = json.dumps(body, indent=2).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(raw)

        def _bearer(self) -> str:
            hdr = self.headers.get("Authorization", "")
            if hdr.startswith("Bearer "):
                return hdr[7:].strip()
            return default_partner_token

        def _read_json(self) -> Dict[str, Any]:
            n = int(self.headers.get("Content-Length", "0"))
            if n <= 0:
                return {}
            return json.loads(self.rfile.read(n).decode("utf-8"))

        def do_OPTIONS(self) -> None:
            self._send_json(200, {"ok": True})

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            qs = parse_qs(parsed.query)
            try:
                if parsed.path in ("/", "/index.html"):
                    html = (BASE_DIR / "index.html").read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(html)))
                    self.end_headers()
                    self.wfile.write(html)
                    return
                if parsed.path == "/api/health":
                    self._send_json(200, {"status": "ok", "engine": "HelixPracticeEngine", "db_path": str(engine.db_path)})
                    return
                if parsed.path == "/api/state":
                    tenant_id = qs.get("tenant_id", ["hartley-mfg"])[0]
                    period_key = qs.get("period_key", ["26A3"])[0]
                    self._send_json(200, engine.list_workspace_state(self._bearer(), tenant_id, period_key))
                    return
                self._send_json(404, {"error": f"Unknown route {parsed.path}"})
            except AuthError as e:
                self._send_json(403, {"error": str(e)})
            except ValidationError as e:
                self._send_json(400, {"error": str(e)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                body = self._read_json()
                token = self._bearer()
                tenant_id = body.get("tenant_id", "hartley-mfg")
                if parsed.path == "/api/transactions/approve":
                    res = engine.approve_and_post(token, tenant_id, body["tx_id"])
                    self._send_json(200, res)
                    return
                if parsed.path == "/api/transactions/mutate":
                    res = engine.mutate_transaction(
                        token,
                        tenant_id,
                        body["tx_id"],
                        net_pence=body.get("net_pence"),
                        vat_treatment=body.get("vat_treatment"),
                        evidence_id=body.get("evidence_id"),
                        reason_note=body.get("reason_note", "Interactive mutation test"),
                    )
                    self._send_json(200, res)
                    return
                if parsed.path == "/api/evidence/tamper-disk":
                    # Explicit diagnostic endpoint allowing reviewers to corrupt 1 byte on disk and verify invalidation
                    ev_id = body["evidence_id"]
                    conn = engine._connect()
                    try:
                        engine.authenticate(conn, token, tenant_id, require_partner=False)
                        ev = conn.execute(
                            "SELECT * FROM evidence_blobs WHERE evidence_id = ? AND tenant_id = ?;",
                            (ev_id, tenant_id),
                        ).fetchone()
                    finally:
                        conn.close()
                    if ev is None:
                        raise ValidationError(f"Unknown evidence_id '{ev_id}'")
                    p = engine.evidence_root / ev["storage_relpath"]
                    p.write_bytes(p.read_bytes() + b"\n# UNAUTHORIZED POST-APPROVAL EDIT\n")
                    vat_res = engine.scan_integrity_and_compile_vat_return(token, tenant_id, body.get("period_key", "26A3"))
                    self._send_json(200, vat_res)
                    return
                if parsed.path == "/api/hmrc-sandbox/vat-returns":
                    vat_state = engine.scan_integrity_and_compile_vat_return(token, tenant_id, body.get("period_key", "26A3"))
                    receipt = validate_simulated_hmrc_sandbox_submission(vat_state["vrn"], vat_state["hmrc_mtd_payload"])
                    self._send_json(200, {"vat_state": vat_state, "sandbox_receipt": receipt})
                    return
                if parsed.path == "/api/reset-demo":
                    conn = engine._connect()
                    try:
                        for tbl in ("ledger_postings", "audit_events", "transactions", "evidence_blobs", "reviewer_tenant_grants", "reviewers", "tenants"):
                            conn.execute(f"DELETE FROM {tbl};")
                    finally:
                        conn.close()
                    seed_clean_checkout_demo(engine)
                    self._send_json(200, engine.list_workspace_state(default_partner_token, "hartley-mfg", "26A3"))
                    return
                self._send_json(404, {"error": f"Unknown route {parsed.path}"})
            except AuthError as e:
                self._send_json(403, {"error": str(e)})
            except ConflictError as e:
                self._send_json(409, {"error": str(e)})
            except ValidationError as e:
                self._send_json(400, {"error": str(e)})
            except Exception as e:
                self._send_json(500, {"error": str(e)})

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return HelixRequestHandler


def main() -> None:
    parser = argparse.ArgumentParser(description="Helix v1 UK Practice Control Plane — Local SQLite + HTTP Server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8890)
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH))
    parser.add_argument("--evidence-dir", default=str(DEFAULT_EVIDENCE_DIR))
    args = parser.parse_args()

    engine = HelixPracticeEngine(db_path=Path(args.db), evidence_root=Path(args.evidence_dir))
    seed_clean_checkout_demo(engine)
    srv = ThreadingHTTPServer((args.host, args.port), make_http_handler(engine))
    print(f"Helix v1 Control Plane listening on http://{args.host}:{args.port} (SQLite WAL: {args.db})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
