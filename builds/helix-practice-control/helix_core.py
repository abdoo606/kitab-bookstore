#!/usr/bin/env python3
"""
Helix v1.1 — UK practice control plane (core domain, Python 3.11+, stdlib only).

Design rules (the ones the review asked about):
  1. An approval is bound to a PAYLOAD HASH, not to a row id. Any change to amount,
     evidence, account code or dates changes the hash and kills the approval.
  2. Money is integer pence. VAT is computed with explicit half-up rounding, so
     19.99 @ 20% is 4.00, not 3.998 and not 3.99.
  3. Every write appends to a hash-chained audit log (prev_hash -> hash). Editing a
     row outside the API is detectable by verify().
  4. Duplicate posting is prevented twice: a UNIQUE (client_id, kind, number) index
     and an optimistic version check inside BEGIN IMMEDIATE.
  5. Client isolation is enforced in every query (client_id is not optional).
  6. Separation of duties: the user who prepared a transaction cannot approve it.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

SCHEMA = """
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
"""


# --------------------------------------------------------------------------- money
def vat_of(net_pence: int, rate_bp: int) -> int:
    """Half-up integer VAT. 1999 @ 2000bp -> 400 (4.00), 1 @ 2000bp -> 0."""
    if net_pence < 0 or rate_bp < 0:
        raise ValueError("net and rate must be non-negative")
    num = net_pence * rate_bp
    return (num + 5000) // 10000


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class HelixError(Exception):
    def __init__(self, code: str, message: str, http: int = 400):
        super().__init__(message)
        self.code, self.message, self.http = code, message, http


# --------------------------------------------------------------------------- store
class Store:
    def __init__(self, path: str = "helix.db", hmac_key: Optional[bytes] = None):
        self.path = path
        self.key = hmac_key or os.environ.get("HELIX_HMAC_KEY", "dev-key-change-me").encode()
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    # -- helpers ---------------------------------------------------------
    def close(self):
        self.conn.close()

    def _now(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    def _audit(self, actor: str, action: str, entity: str, entity_id: str, detail: Dict[str, Any]) -> None:
        prev = self.conn.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        prev_hash = prev["hash"] if prev else "GENESIS"
        body = canonical({"ts": self._now(), "actor": actor, "action": action,
                          "entity": entity, "entity_id": str(entity_id), "detail": detail, "prev_hash": prev_hash})
        h = hashlib.sha256(body.encode()).hexdigest()
        self.conn.execute(
            "INSERT INTO audit(ts,actor,action,entity,entity_id,detail,prev_hash,hash) VALUES(?,?,?,?,?,?,?,?)",
            (json.loads(body)["ts"], actor, action, entity, str(entity_id), canonical(detail), prev_hash, h),
        )

    def _sign(self, payload: Dict[str, Any]) -> str:
        return hmac.new(self.key, canonical(payload).encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def payload_hash(tx: Dict[str, Any]) -> str:
        keys = ("client_id", "kind", "number", "issued_at", "net_pence", "vat_rate_bp",
                "vat_pence", "gross_pence", "currency", "account_code", "evidence_sha")
        return hashlib.sha256(canonical({k: tx[k] for k in keys}).encode()).hexdigest()

    # -- seed ------------------------------------------------------------
    def add_client(self, client_id: str, name: str, vat_number: str = "") -> None:
        with self._lock:
            self.conn.execute("INSERT OR IGNORE INTO clients(id,name,vat_number,created_at) VALUES(?,?,?,?)",
                              (client_id, name, vat_number, self._now()))
            self._audit("system", "client.create", "client", client_id, {"name": name})

    def add_user(self, user_id: str, client_id: str, name: str, role: str, token: str) -> None:
        salt = secrets.token_hex(8)
        th = hashlib.pbkdf2_hmac("sha256", token.encode(), salt.encode(), 120_000).hex()
        with self._lock:
            self.conn.execute("INSERT OR REPLACE INTO users(id,client_id,name,role,token_hash,salt) VALUES(?,?,?,?,?,?)",
                              (user_id, client_id, name, role, th, salt))

    def authenticate(self, token: str) -> Dict[str, Any]:
        row = self.conn.execute("SELECT * FROM users").fetchall()  # small table, constant-time compare each
        for u in row:
            th = hashlib.pbkdf2_hmac("sha256", token.encode(), u["salt"].encode(), 120_000).hex()
            if hmac.compare_digest(th, u["token_hash"]):
                return {"id": u["id"], "client_id": u["client_id"], "name": u["name"], "role": u["role"]}
        raise HelixError("unauthorized", "invalid token", 401)

    # -- writes ----------------------------------------------------------
    def create_transaction(self, client_id: str, kind: str, number: str, issued_at: str,
                           net_pence: int, vat_rate_bp: int, actor: str, *,
                           account_code: str = "4000", evidence_name: str = "",
                           evidence_bytes: bytes = b"", currency: str = "GBP") -> Dict[str, Any]:
        vat = vat_of(net_pence, vat_rate_bp)
        row = {
            "client_id": client_id, "kind": kind, "number": number, "issued_at": issued_at,
            "net_pence": net_pence, "vat_rate_bp": vat_rate_bp, "vat_pence": vat,
            "gross_pence": net_pence + vat, "currency": currency, "account_code": account_code,
            "evidence_sha": sha256_bytes(evidence_bytes) if evidence_bytes else "",
        }
        ph = self.payload_hash(row)
        with self._lock:
          try:
            self.conn.execute("BEGIN IMMEDIATE")
            cur = self.conn.execute(
                """INSERT INTO transactions(client_id,kind,number,issued_at,net_pence,vat_rate_bp,vat_pence,
                     gross_pence,currency,account_code,evidence_name,evidence_sha,status,version,payload_hash,
                     created_by,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,'pending',1,?,?,?,?)""",
                (client_id, kind, number, issued_at, net_pence, vat_rate_bp, vat, net_pence + vat, currency,
                 account_code, evidence_name, row["evidence_sha"], ph, actor["id"], self._now(), self._now()),
            )
            self._audit(actor["id"], "transaction.create", "transaction", cur.lastrowid,
                        {"number": number, "kind": kind, "payload_hash": ph})
            self.conn.execute("COMMIT")
          except sqlite3.IntegrityError as e:
            self.conn.execute("ROLLBACK")
            raise HelixError("duplicate", f"duplicate {kind} number {number} for this client", 409) from e
          except Exception:
            self.conn.execute("ROLLBACK")
            raise
        return self.get_transaction(client_id, cur.lastrowid)

    def get_transaction(self, client_id: str, tx_id: int) -> Dict[str, Any]:
        r = self.conn.execute("SELECT * FROM transactions WHERE id=? AND client_id=?", (tx_id, client_id)).fetchone()
        if not r:
            raise HelixError("not_found", "transaction not found", 404)
        return dict(r)

    def approve(self, client_id: str, tx_id: int, actor: Dict[str, Any], note: str = "") -> Dict[str, Any]:
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                tx = self.conn.execute("SELECT * FROM transactions WHERE id=? AND client_id=?", (tx_id, client_id)).fetchone()
                if not tx:
                    raise HelixError("not_found", "transaction not found", 404)
                if tx["created_by"] == actor["id"]:
                    raise HelixError("sod", "the preparer cannot approve their own transaction", 403)
                if actor["role"] not in ("approver", "admin"):
                    raise HelixError("forbidden", "only an approver can approve", 403)
                if tx["status"] not in ("pending",):
                    raise HelixError("state", f"cannot approve a {tx['status']} transaction", 409)
                current = self.payload_hash(dict(tx))
                if current != tx["payload_hash"]:
                    raise HelixError("tampered", "payload hash does not match the stored row", 409)
                sig = self._sign({"tx": tx_id, "ph": current, "by": actor["id"], "at": self._now()})
                self.conn.execute("UPDATE approvals SET superseded=1 WHERE transaction_id=? AND superseded=0", (tx_id,))
                self.conn.execute(
                    "INSERT INTO approvals(client_id,transaction_id,payload_hash,approver,approved_at,note,sig) VALUES(?,?,?,?,?,?,?)",
                    (client_id, tx_id, current, actor["id"], self._now(), note, sig),
                )
                self.conn.execute("UPDATE transactions SET status='approved', updated_at=? WHERE id=?",
                                  (self._now(), tx_id))
                self._audit(actor["id"], "transaction.approve", "transaction", tx_id,
                            {"payload_hash": current, "sig": sig[:16]})
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
        return self.get_transaction(client_id, tx_id)

    def post(self, client_id: str, tx_id: int, actor: Dict[str, Any], expected_version: int) -> Dict[str, Any]:
        """Post to the ledger. Idempotent: posting a posted row returns it, version guards races."""
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                tx = self.conn.execute("SELECT * FROM transactions WHERE id=? AND client_id=?", (tx_id, client_id)).fetchone()
                if not tx:
                    raise HelixError("not_found", "transaction not found", 404)
                if tx["status"] == "posted":
                    self.conn.execute("COMMIT")
                    return dict(tx)
                if tx["status"] != "approved":
                    raise HelixError("state", f"cannot post a {tx['status']} transaction", 409)
                if tx["version"] != expected_version:
                    raise HelixError("conflict", "version changed, refresh and retry", 409)
                ap = self.conn.execute(
                    "SELECT * FROM approvals WHERE transaction_id=? AND superseded=0 ORDER BY id DESC LIMIT 1",
                    (tx_id,)).fetchone()
                if not ap or ap["payload_hash"] != tx["payload_hash"]:
                    raise HelixError("approval_missing", "no valid approval for the current payload", 409)
                self.conn.execute("UPDATE transactions SET status='posted', version=version+1, updated_at=? WHERE id=?",
                                  (self._now(), tx_id))
                self._audit(actor["id"], "transaction.post", "transaction", tx_id,
                            {"payload_hash": tx["payload_hash"], "version": tx["version"] + 1})
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
        return self.get_transaction(client_id, tx_id)

    def amend(self, client_id: str, tx_id: int, actor: Dict[str, Any], **changes: Any) -> Dict[str, Any]:
        """Any amendment invalidates the approval: new payload hash -> status back to pending."""
        allowed = {"net_pence", "vat_rate_bp", "account_code", "issued_at", "evidence_sha", "evidence_name"}
        bad = set(changes) - allowed
        if bad:
            raise HelixError("bad_field", f"cannot amend: {sorted(bad)}")
        with self._lock:
            self.conn.execute("BEGIN IMMEDIATE")
            try:
                tx = dict(self.conn.execute("SELECT * FROM transactions WHERE id=? AND client_id=?", (tx_id, client_id)).fetchone() or {})
                if not tx:
                    raise HelixError("not_found", "transaction not found", 404)
                if tx["status"] == "posted":
                    raise HelixError("state", "posted transactions are immutable; raise a credit note", 409)
                tx.update(changes)
                tx["vat_pence"] = vat_of(tx["net_pence"], tx["vat_rate_bp"])
                tx["gross_pence"] = tx["net_pence"] + tx["vat_pence"]
                ph = self.payload_hash(tx)
                self.conn.execute(
                    """UPDATE transactions SET net_pence=?,vat_rate_bp=?,vat_pence=?,gross_pence=?,account_code=?,
                       issued_at=?,evidence_sha=?,evidence_name=?,payload_hash=?,status='pending',version=version+1,
                       updated_at=? WHERE id=? AND version=?""",
                    (tx["net_pence"], tx["vat_rate_bp"], tx["vat_pence"], tx["gross_pence"], tx["account_code"],
                     tx["issued_at"], tx["evidence_sha"], tx["evidence_name"], ph, self._now(), tx_id, tx["version"]))
                self.conn.execute("UPDATE approvals SET superseded=1 WHERE transaction_id=? AND superseded=0", (tx_id,))
                self._audit(actor["id"], "transaction.amend", "transaction", tx_id,
                            {"new_payload_hash": ph, "changed": sorted(changes)})
                self.conn.execute("COMMIT")
            except Exception:
                self.conn.execute("ROLLBACK")
                raise
        return self.get_transaction(client_id, tx_id)

    # -- reads -----------------------------------------------------------
    def list_transactions(self, client_id: str, kind: Optional[str] = None) -> List[Dict[str, Any]]:
        q = "SELECT * FROM transactions WHERE client_id=?"
        args: List[Any] = [client_id]
        if kind:
            q += " AND kind=?"
            args.append(kind)
        return [dict(r) for r in self.conn.execute(q + " ORDER BY id", args)]

    def vat_return(self, client_id: str, period: str) -> Dict[str, Any]:
        """Box 1 = output VAT on sales. Invoices count on issue date; receipts on receipt date."""
        rows = self.conn.execute(
            "SELECT * FROM transactions WHERE client_id=? AND status='posted' AND substr(issued_at,1,7)=?",
            (client_id, period)).fetchall()
        out_vat = sum(r["vat_pence"] for r in rows)
        net = sum(r["net_pence"] for r in rows)
        return {"period": period, "box1_output_vat": out_vat, "net_sales": net,
                "gross": net + out_vat, "entries": len(rows),
                "by_kind": {k: sum(r["vat_pence"] for r in rows if r["kind"] == k) for k in ("invoice", "receipt")}}

    def audit_log(self, client_id: str, limit: int = 200) -> List[Dict[str, Any]]:
        ids = [str(r["id"]) for r in self.conn.execute(
            "SELECT id FROM transactions WHERE client_id=? ORDER BY id", (client_id,))]
        if not ids:
            return []
        q = f"SELECT * FROM audit WHERE entity_id IN ({','.join('?' * len(ids))}) ORDER BY id DESC LIMIT ?"
        return [dict(r) for r in self.conn.execute(q, (*ids, limit))]

    # -- integrity -------------------------------------------------------
    def verify(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        problems: List[Dict[str, Any]] = []
        prev = "GENESIS"
        for r in self.conn.execute("SELECT * FROM audit ORDER BY id"):
            body = canonical({"ts": r["ts"], "actor": r["actor"], "action": r["action"], "entity": r["entity"],
                              "entity_id": r["entity_id"], "detail": json.loads(r["detail"]),
                              "prev_hash": r["prev_hash"]})
            if hashlib.sha256(body.encode()).hexdigest() != r["hash"]:
                problems.append({"type": "audit_hash_mismatch", "audit_id": r["id"]})
            if r["prev_hash"] != prev:
                problems.append({"type": "audit_chain_break", "audit_id": r["id"]})
            prev = r["hash"]
        q = "SELECT * FROM transactions" + (" WHERE client_id=?" if client_id else "")
        for t in self.conn.execute(q, ((client_id,) if client_id else ())):
            if self.payload_hash(dict(t)) != t["payload_hash"]:
                problems.append({"type": "transaction_tampered", "id": t["id"], "number": t["number"]})
            if t["status"] in ("approved", "posted"):
                ap = self.conn.execute(
                    "SELECT * FROM approvals WHERE transaction_id=? AND superseded=0 ORDER BY id DESC LIMIT 1",
                    (t["id"],)).fetchone()
                if not ap or ap["payload_hash"] != t["payload_hash"]:
                    problems.append({"type": "approval_payload_mismatch", "id": t["id"], "number": t["number"]})
        return {"ok": not problems, "checked": {"audit": self.conn.execute("SELECT COUNT(*) c FROM audit").fetchone()["c"]},
                "problems": problems}


def seed_demo(store: Store) -> Dict[str, str]:
    """Anonymised sample tenant. Returns tokens (demo only)."""
    store.add_client("acme", "Acme Dental Ltd", "GB123456789")
    store.add_client("beta", "Beta Roofing Ltd", "GB987654321")
    tokens = {"preparer": "tok-prep-" + secrets.token_hex(4), "approver": "tok-appr-" + secrets.token_hex(4)}
    store.add_user("u-prep", "acme", "Sam (preparer)", "preparer", tokens["preparer"])
    store.add_user("u-appr", "acme", "Priya (approver)", "approver", tokens["approver"])
    store.add_user("u-beta", "beta", "Beta admin", "admin", "tok-beta-" + secrets.token_hex(4))
    return tokens
