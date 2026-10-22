#!/usr/bin/env python3
"""Helix v1.1 test suite — stdlib unittest, no network, no fixtures outside tmp dirs."""
import json
import os
import sqlite3
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import app as api
from helix_core import HelixError, Store, sha256_bytes, sha256_file, vat_of


def fresh() -> tuple[Store, dict, dict, dict]:
    d = tempfile.mkdtemp()
    s = Store(os.path.join(d, "h.db"), hmac_key=b"test-key")
    s.add_client("acme", "Acme Ltd")
    s.add_client("beta", "Beta Ltd")
    s.add_user("u1", "acme", "Preparer", "preparer", "tok-prep")
    s.add_user("u2", "acme", "Approver", "approver", "tok-appr")
    s.add_user("u3", "beta", "Beta Admin", "admin", "tok-beta")
    return s, s.authenticate("tok-prep"), s.authenticate("tok-appr"), s.authenticate("tok-beta")


def mk(s, actor, number="INV-1", net=10000, rate=2000, kind="invoice", **kw):
    return s.create_transaction("acme", kind, number, "2026-10-05", net, rate, actor, **kw)


class TestMoney(unittest.TestCase):
    def test_01_vat_basic(self):
        self.assertEqual(vat_of(10000, 2000), 2000)

    def test_02_vat_rounds_half_up(self):
        self.assertEqual(vat_of(1999, 2000), 400)   # 399.8 -> 400
        self.assertEqual(vat_of(1, 2000), 0)        # 0.2 -> 0
        self.assertEqual(vat_of(3, 2000), 1)        # 0.6 -> 1

    def test_03_vat_zero_rate_and_negative(self):
        self.assertEqual(vat_of(5000, 0), 0)
        with self.assertRaises(ValueError):
            vat_of(-1, 2000)

    def test_04_gross_is_exact(self):
        s, p, _, _ = fresh()
        t = mk(s, p, net=12345, rate=1750)
        self.assertEqual(t["vat_pence"], 2160)      # 2160.375 -> 2160
        self.assertEqual(t["gross_pence"], 14505)


class TestHashing(unittest.TestCase):
    def test_05_file_hash_is_stable(self):
        p = tempfile.mktemp()
        open(p, "wb").write(b"evidence")
        self.assertEqual(sha256_file(p), sha256_bytes(b"evidence"))

    def test_06_evidence_change_changes_payload(self):
        s, prep, _, _ = fresh()
        a = mk(s, prep, "INV-9", evidence_bytes=b"one")
        b = mk(s, prep, "INV-10", evidence_bytes=b"two")
        self.assertNotEqual(a["payload_hash"], b["payload_hash"])

    def test_07_tamper_detected(self):
        s, prep, _, _ = fresh()
        t = mk(s, prep)
        s.conn.execute("UPDATE transactions SET net_pence=99999 WHERE id=?", (t["id"],))
        rep = s.verify()
        self.assertFalse(rep["ok"])
        self.assertIn("transaction_tampered", [x["type"] for x in rep["problems"]])

    def test_08_audit_chain_break_detected(self):
        s, prep, _, _ = fresh()
        mk(s, prep)
        s.conn.execute("UPDATE audit SET detail='{}' WHERE id=1")
        rep = s.verify()
        self.assertFalse(rep["ok"])
        self.assertIn("audit_hash_mismatch", [x["type"] for x in rep["problems"]])


class TestApproval(unittest.TestCase):
    def test_09_approval_binds_payload(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        a = s.approve("acme", t["id"], appr)
        self.assertEqual(a["status"], "approved")
        row = s.conn.execute("SELECT * FROM approvals WHERE transaction_id=?", (t["id"],)).fetchone()
        self.assertEqual(row["payload_hash"], t["payload_hash"])

    def test_10_amend_kills_approval(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        s.approve("acme", t["id"], appr)
        t2 = s.amend("acme", t["id"], prep, net_pence=50000)
        self.assertEqual(t2["status"], "pending")
        self.assertNotEqual(t2["payload_hash"], t["payload_hash"])
        sup = s.conn.execute("SELECT superseded FROM approvals WHERE transaction_id=?", (t["id"],)).fetchone()
        self.assertEqual(sup["superseded"], 1)
        with self.assertRaises(HelixError) as e:
            s.post("acme", t["id"], appr, t2["version"])
        self.assertEqual(e.exception.code, "state")

    def test_11_evidence_amend_kills_approval(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep, evidence_bytes=b"invoice.pdf")
        s.approve("acme", t["id"], appr)
        t2 = s.amend("acme", t["id"], prep, evidence_sha=sha256_bytes(b"forged.pdf"))
        self.assertEqual(t2["status"], "pending")
        with self.assertRaises(HelixError):
            s.post("acme", t["id"], appr, t2["version"])

    def test_12_separation_of_duties(self):
        s, prep, _, _ = fresh()
        t = mk(s, prep)
        with self.assertRaises(HelixError) as e:
            s.approve("acme", t["id"], prep)
        self.assertEqual(e.exception.code, "sod")

    def test_13_preparer_cannot_approve_even_if_role_allows(self):
        s, _, _, beta = fresh()
        s.add_user("u4", "acme", "Dual", "admin", "tok-admin")
        admin = s.authenticate("tok-admin")
        t = mk(s, admin)
        with self.assertRaises(HelixError):
            s.approve("acme", t["id"], admin)

    def test_14_unauthorized_token(self):
        s, _, _, _ = fresh()
        with self.assertRaises(HelixError) as e:
            s.authenticate("nope")
        self.assertEqual(e.exception.http, 401)

    def test_15_audit_history_written(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        s.approve("acme", t["id"], appr)
        s.post("acme", t["id"], appr, 1)
        acts = [r["action"] for r in s.audit_log("acme")]
        for a in ("transaction.post", "transaction.approve", "transaction.create"):
            self.assertIn(a, acts)


class TestPosting(unittest.TestCase):
    def test_16_post_requires_approval(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        with self.assertRaises(HelixError) as e:
            s.post("acme", t["id"], appr, 1)
        self.assertEqual(e.exception.code, "state")

    def test_17_post_is_idempotent(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        s.approve("acme", t["id"], appr)
        a = s.post("acme", t["id"], appr, 1)
        b = s.post("acme", t["id"], appr, 1)
        self.assertEqual(a["status"], b["status"])
        self.assertEqual(a["id"], b["id"])

    def test_18_stale_version_conflict(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        s.approve("acme", t["id"], appr)
        s.amend("acme", t["id"], prep, note=None) if False else None
        s.conn.execute("UPDATE transactions SET version=7 WHERE id=?", (t["id"],))
        with self.assertRaises(HelixError) as e:
            s.post("acme", t["id"], appr, 1)
        self.assertEqual(e.exception.code, "conflict")

    def test_19_posted_is_immutable(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        s.approve("acme", t["id"], appr)
        s.post("acme", t["id"], appr, 1)
        with self.assertRaises(HelixError):
            s.amend("acme", t["id"], prep, net_pence=1)

    def test_20_concurrent_posts_produce_one_audit_entry(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        s.approve("acme", t["id"], appr)
        errs = []

        def go():
            try:
                s.post("acme", t["id"], appr, 1)
            except Exception as e:  # noqa: BLE001
                errs.append(e)

        ths = [threading.Thread(target=go) for _ in range(8)]
        [x.start() for x in ths]
        [x.join() for x in ths]
        n = s.conn.execute("SELECT COUNT(*) c FROM audit WHERE action='transaction.post'").fetchone()["c"]
        self.assertEqual(n, 1)


class TestDuplicatesAndIsolation(unittest.TestCase):
    def test_21_duplicate_number_rejected(self):
        s, prep, _, _ = fresh()
        mk(s, prep, "INV-7")
        with self.assertRaises(HelixError) as e:
            mk(s, prep, "INV-7")
        self.assertEqual(e.exception.http, 409)

    def test_22_same_number_other_client_allowed(self):
        s, prep, _, _ = fresh()
        mk(s, prep, "INV-7")
        t = s.create_transaction("beta", "invoice", "INV-7", "2026-10-05", 100, 2000, s.authenticate("tok-beta"))
        self.assertEqual(t["client_id"], "beta")

    def test_23_concurrent_duplicate_creates_one(self):
        s, prep, _, _ = fresh()
        ok, bad = [], []

        def go(i):
            try:
                ok.append(mk(s, prep, "SAME-1"))
            except HelixError:
                bad.append(i)

        ths = [threading.Thread(target=go, args=(i,)) for i in range(6)]
        [x.start() for x in ths]
        [x.join() for x in ths]
        self.assertEqual(len(ok), 1)
        self.assertEqual(len(bad), 5)

    def test_24_client_isolation_read(self):
        s, prep, appr, beta = fresh()
        t = mk(s, prep)
        with self.assertRaises(HelixError) as e:
            s.get_transaction("beta", t["id"])
        self.assertEqual(e.exception.http, 404)

    def test_25_client_isolation_approve(self):
        s, prep, _, beta = fresh()
        t = mk(s, prep)
        with self.assertRaises(HelixError):
            s.approve("beta", t["id"], beta)

    def test_26_list_is_scoped(self):
        s, prep, _, beta = fresh()
        mk(s, prep)
        self.assertEqual(len(s.list_transactions("beta")), 0)


class TestVatReturnAndPersistence(unittest.TestCase):
    def test_27_vat_return_boxes(self):
        s, prep, appr, _ = fresh()
        t1 = mk(s, prep, "INV-1", net=10000)
        t2 = mk(s, prep, "INV-2", net=20000, kind="receipt")
        for t in (t1, t2):
            s.approve("acme", t["id"], appr)
            s.post("acme", t["id"], appr, 1)
        r = s.vat_return("acme", "2026-10")
        self.assertEqual(r["box1_output_vat"], 6000)
        self.assertEqual(r["by_kind"]["invoice"], 2000)
        self.assertEqual(r["by_kind"]["receipt"], 4000)

    def test_28_only_posted_counts(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep, "INV-3", net=10000)
        s.approve("acme", t["id"], appr)
        self.assertEqual(s.vat_return("acme", "2026-10")["box1_output_vat"], 0)

    def test_29_persistence_across_restart(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        s.approve("acme", t["id"], appr)
        path = s.path
        s.close()
        s2 = Store(path, hmac_key=b"test-key")
        self.assertEqual(s2.get_transaction("acme", t["id"])["status"], "approved")
        self.assertTrue(s2.verify()["ok"])

    def test_30_verify_clean_after_normal_flow(self):
        s, prep, appr, _ = fresh()
        t = mk(s, prep)
        s.approve("acme", t["id"], appr)
        s.post("acme", t["id"], appr, 1)
        self.assertTrue(s.verify()["ok"])


class TestHttpApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        d = tempfile.mkdtemp()
        api.DB_PATH = os.path.join(d, "api.db")
        api.STORE = Store(api.DB_PATH, hmac_key=b"api-key")
        api.STORE.add_client("acme", "Acme Ltd")
        api.STORE.add_user("u1", "acme", "P", "preparer", "tok-prep")
        api.STORE.add_user("u2", "acme", "A", "approver", "tok-appr")
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), api.H)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def call(self, path, body=None, token=None, method=None):
        url = f"http://127.0.0.1:{self.port}{path}"
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method or ("POST" if data else "GET"))
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")

    def test_31_health(self):
        code, body = self.call("/health")
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])

    def test_32_requires_token(self):
        code, body = self.call("/api/transactions")
        self.assertEqual(code, 401)
        self.assertEqual(body["error"], "unauthorized")

    def test_33_full_flow(self):
        code, tx = self.call("/api/transactions", {"kind": "invoice", "number": "H-1", "issued_at": "2026-10-05",
                                                   "net_pence": 10000, "vat_rate_bp": 2000}, "tok-prep")
        self.assertEqual(code, 201)
        code, a = self.call(f"/api/transactions/{tx['id']}/approve", {}, "tok-appr")
        self.assertEqual(code, 200)
        self.assertEqual(a["status"], "approved")
        code, p = self.call(f"/api/transactions/{tx['id']}/post", {"version": a["version"]}, "tok-appr")
        self.assertEqual(code, 200)
        self.assertEqual(p["status"], "posted")
        code, v = self.call("/api/verify")
        self.assertEqual(code, 200)
        self.assertTrue(v["ok"])

    def test_34_http_tamper_visible(self):
        api.STORE.conn.execute("UPDATE transactions SET net_pence=1 WHERE number='H-1'")
        code, v = self.call("/api/verify")
        self.assertFalse(v["ok"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
