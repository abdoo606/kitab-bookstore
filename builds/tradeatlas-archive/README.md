# TradeAtlas — Complete Version Archive & Architecture Map (`v1.0` → `v42.0`)

This directory preserves **every historical version, engine iteration, documentation trail, and Core patch** of **TradeAtlas (Genius Idea #14)** in Git so Google Drive retains **only** the verified full baseline package:

- **Google Drive Canonical Baseline (Kept):** `TradeAtlas-Pro-v35.0-GoldHaven-1961505-USD.zip` (`24.8 MB`, `172/172` unit & zero-lookahead tests passing)
- **Git Full Working Tree Baseline:** [`../tradeatlas-pro-v35/`](../tradeatlas-pro-v35/) (`131` files including `33` verified real market CSVs, `v21`–`v35` engines, UI server on `:8820`, and `172/172` tests)

---

## Directory Layout & Verified Test Suites

| Path | Version Scope | Verified Tests | Notes |
|---|---|---:|---|
| [`../tradeatlas-pro-v35/`](../tradeatlas-pro-v35/) | **`v35.0 GoldHaven` (Full Canonical Build + `v21`–`v34` Engines)** | **`172 / 172` OK** | Complete standalone platform + all `README-v21.md`..`README-v33.md`, `quant_shield_v24.py` through `halal_gold_haven_compounder_v35.py`, and all 33 real datasets |
| [`./v42-core-73tests/`](./v42-core-73tests/) | **`TradeAtlas Core v42`** | **`73 / 73` OK** | Live `/api/signal` endpoint, execution-cost curve, Deflated Sharpe Ratio (multiple-testing correction), separate slippage cost line |
| [`./v41-core-52tests/`](./v41-core-52tests/) | **`TradeAtlas Core v41`** | **`52 / 52` OK** | VIX fear filter, out-of-sample walk-forward split, 9-window stability sweep, 2,000-path block bootstrap |
| [`./v40-core-32tests/`](./v40-core-32tests/) | **`TradeAtlas Core v40`** | **`32 / 32` OK** | Authentic Shiller data backtest, trade-time fee deduction, 0-lookahead proof across 122 cutoffs |
| [`./v18/`](./v18/) | **`TradeAtlas v18.0` — Real Data Infusion** | `152` tests | 10 bundled real datasets, 52 causal engines, `realdata.py` |
| [`./v17/`](./v17/) | **`TradeAtlas v17.0` — Evolution Revolution** | `143` tests | `diagnostics.py`, `evolution.py`, 35 failure causes & self-healing loop |
| [`./v16/`](./v16/) | **`TradeAtlas v16.0` — Autonomous Collector** | `100+` tests | `pipeline.py`, counted holdout & 9-gate 80% tracker |
| [`./v15/`](./v15/) | **`TradeAtlas v15.0` — Self-Correcting Loop** | `80+` tests | `selfcorrect.py` + `FAILURE-MEMORY.md` |
| [`./docs-v01-to-v20/`](./docs-v01-to-v20/) | **`v1.0` → `v14.0` & `v20.0` Specs & Milestones** | `6` → `160` tests | Early architecture (`v1`–`v13`), `v14` minute-first goals JSON/Markdown, and `v20` Quantum Institutional specs |

---

## Quick Verification Commands

```bash
# 1. Run canonical full build (v35.0 GoldHaven — 172 tests)
(cd builds/tradeatlas-pro-v35 && python3 -m unittest discover)

# 2. Run Core v40 / v41 / v42 test suites (32 / 52 / 73 tests)
(cd builds/tradeatlas-archive/v40-core-32tests && python3 -m unittest discover)
(cd builds/tradeatlas-archive/v41-core-52tests && python3 -m unittest discover)
(cd builds/tradeatlas-archive/v42-core-73tests && python3 -m unittest discover)
```
