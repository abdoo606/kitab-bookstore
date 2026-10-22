# R49 — four client backends (built, tested, private until M1)

Four paid-outreach clients from round 49. Each folder has the code that was described in the
outreach email, its tests, and the exact prices. **Nothing here is a promise of future work:
all four run today with the Python standard library only.**

| # | Client | Folder | Backend entry point | Tests |
|---|--------|--------|--------------------|-------|
| 78 | Enveritas | `enveritas/` | `backend/app.py` → `eudr_core.py` | 34 |
| 79 | Cable Energy | `cable-energy/` | `backend/app.py` → `billing_core.py` | 36 |
| 80 | VLM Run | `vlm-run/` | `backend/app.py` → `release_gate.py` | 35 |
| 81 | Komodo Health | `komodo-health/` | `backend/app.py` → `annex_core.py` | 36 |
| | | | **total** | **141** |

## Run everything

```bash
cd clients/r49
bash run_all_tests.sh          # enveritas OK 34 / cable-energy OK 36 / vlm-run OK 35 / komodo-health OK 36
cd enveritas && python3 backend/app.py demo
```

Each `app.py` takes `demo` (one command, prints a real artefact), plus its own verbs
(`assess` / `verify`, `invoice` / `reconcile` / `drill`, `gate` / `diff`, `classify` / `annex`).

## Why the code is not in this repository

`clients/*/*/backend/` is in `.gitignore` by standing rule: **backends stay private until M1 is
paid**. What is public is the README and the prices — the client sees what the thing does and
what it costs, not the implementation.

## Where the code is stored so it is never lost

Encrypted container in Google Drive, password `1903`:

- folder: `00 — مركز القيادة المنظم` → `🔒-باك-اند-٤-عملاء-R49-كلمة-سر-1903`
- file: `باك-اند-4-عملاء-R49-141-اختبار-1903.zip` (44 109 B, 21 entries, AES-256)

Restore and verify (this is the whole recovery procedure):

```bash
unzip باك-اند-4-عملاء-R49-141-اختبار-1903.zip -d r49     # password 1903
cd r49 && bash run_all_tests.sh                          # must print 141 tests, all OK
```

The recovery was executed once from the archive before it was uploaded: 4 suites, 141 tests,
all OK. A local snapshot also exists at `_versions/20261022-145922-round49-followup.tar.gz`
(241 files, hash-verified).

## Prices

Unchanged and explicit in every folder's `PRICING.md`: turnkey + M1 + M2 + M3 + monthly.
Payment is crypto only (USDT TRC-20 `TVDjBzZuHu3drJ1H4jbanLyNb9Ss3uMBNy`); no bank, no IBAN.
