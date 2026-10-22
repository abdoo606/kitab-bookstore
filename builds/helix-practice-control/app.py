#!/usr/bin/env python3
"""
Helix v1.1 — HTTP API (stdlib only).

  python3 app.py --init --serve --port 8842      # first run: create DB + demo tenant
  python3 app.py --serve --port 8842             # subsequent runs

Auth:  Authorization: Bearer <token>   (or X-Helix-Token: <token>)
Roles: preparer (create/amend) · approver (approve) · admin (both)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from helix_core import HelixError, Store, seed_demo

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("HELIX_DB", os.path.join(HERE, "helix.db"))
STORE: Store | None = None


def store() -> Store:
    global STORE
    if STORE is None:
        STORE = Store(DB_PATH)
    return STORE


def public(tx: dict) -> dict:
    return {k: tx[k] for k in ("id", "client_id", "kind", "number", "issued_at", "net_pence", "vat_rate_bp",
                               "vat_pence", "gross_pence", "currency", "account_code", "status", "version",
                               "payload_hash", "created_by", "updated_at")}


class H(BaseHTTPRequestHandler):
    server_version = "Helix/1.1"

    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False, default=str).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError as e:
            raise HelixError("bad_json", str(e), 400)

    def _actor(self) -> dict:
        tok = self.headers.get("X-Helix-Token") or ""
        auth = self.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            tok = auth[7:]
        if not tok:
            raise HelixError("unauthorized", "missing token", 401)
        return store().authenticate(tok)

    def _guard(self, fn):
        try:
            return fn()
        except HelixError as e:
            return self._json(e.http, {"error": e.code, "message": e.message})
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"error": "internal", "message": str(e)})

    def do_GET(self):
        u = urlparse(self.path)

        def run():
            if u.path == "/health":
                return self._json(200, {"ok": True, "service": "helix", "version": "1.1"})
            if u.path == "/api/verify":
                return self._json(200, store().verify())
            if u.path == "/api/transactions":
                a = self._actor()
                return self._json(200, [public(t) for t in store().list_transactions(a["client_id"])])
            if u.path == "/api/vat":
                a = self._actor()
                period = (parse_qs(u.query).get("period") or [""])[0]
                if not re.fullmatch(r"\d{4}-\d{2}", period):
                    raise HelixError("bad_period", "period must be YYYY-MM")
                return self._json(200, store().vat_return(a["client_id"], period))
            if u.path == "/api/audit":
                a = self._actor()
                return self._json(200, store().audit_log(a["client_id"]))
            page = os.path.join(HERE, "index.html")
            if os.path.exists(page):
                html = open(page, "rb").read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
                return None
            return self._json(200, {"service": "helix", "version": "1.1",
                                    "endpoints": ["/api/transactions", "/api/verify", "/api/vat", "/api/audit"]})
        return self._guard(run)

    def do_POST(self):
        u = urlparse(self.path)
        m = re.fullmatch(r"/api/transactions/(\d+)/(approve|post|amend)", u.path)

        def run():
            a = self._actor()
            if u.path == "/api/transactions":
                b = self._body()
                tx = store().create_transaction(
                    a["client_id"], b.get("kind", "invoice"), b.get("number", ""), b.get("issued_at", ""),
                    int(b.get("net_pence", 0)), int(b.get("vat_rate_bp", 2000)), a,
                    account_code=b.get("account_code", "4000"),
                    evidence_name=b.get("evidence_name", ""),
                    evidence_bytes=(b.get("evidence_text") or "").encode())
                return self._json(201, public(tx))
            if not m:
                raise HelixError("not_found", "unknown endpoint", 404)
            tx_id, action = int(m.group(1)), m.group(2)
            if action == "approve":
                return self._json(200, public(store().approve(a["client_id"], tx_id, a, self._body().get("note", ""))))
            if action == "post":
                return self._json(200, public(store().post(a["client_id"], tx_id, a, int(self._body().get("version", 0)))))
            b = self._body()
            return self._json(200, public(store().amend(a["client_id"], tx_id, a, **b)))
        return self._guard(run)

    def log_message(self, *a):
        pass


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--init", action="store_true")
    ap.add_argument("--port", type=int, default=8842)
    ap.add_argument("--host", default="0.0.0.0")
    a = ap.parse_args(argv)
    if a.init:
        s = store()
        toks = seed_demo(s)
        print(json.dumps({"db": DB_PATH, "tokens": toks}, indent=1))
    if a.serve:
        s = store()
        print(f"Helix v1.1 on :{a.port}  db={DB_PATH}  verify={s.verify()['ok']}")
        ThreadingHTTPServer((a.host, a.port), H).serve_forever()
        return 0
    if not a.init:
        print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
