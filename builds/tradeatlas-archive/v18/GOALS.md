# TradeAtlas project goals — v17.0

**Last updated:** 2026-10-21 — v18 Real Data Infusion

This file records requested goals separately from evidence. A goal is not a
result, a promise, or permission to trade real money.

## 1. Minute-timeframe focus — implemented in v14

**Goal:** make 1-minute bars the primary research and bot workflow, with
5m/15m aggregation only from finer source bars.

**v14 implementation**

- Seven causal minute engines: rolling-VWAP reversion, EMA ribbon,
  RSI-2 snapback, UTC opening-range breakout, Bollinger squeeze breakout,
  volume-surge pressure and the invented **Atlas Minute Pulse**.
- A hidden-future minute race at 1, 3, 5, 15 and 30 bars.
- BTC/USDT and XBT/USD public-data presets now default to **1m**.
- New paper bots default to `atlas_minute_pulse` on `1m`.
- Minute risk controls: simulated slippage, entries-per-day cap, maximum
  holding bars, post-exit cooldown, minimum-ATR filter, daily-loss and
  drawdown halts.

## 2. At least 80% accuracy — active goal, NOT reached

**Target:** at least **80% out-of-sample direction accuracy**.

**Current honest status:** **not reached or established.**

- Best bundled real result before v14: **68%** for Ultimate on 100 AAPL
  daily hidden-future attempts at horizon 5.
- Best bundled pooled full-coverage result: **63.077%** for Atlas Pressure
  Wave over 260 daily/monthly attempts.
- v14 does **not** bundle a real minute dataset. Its synthetic 1m file tests
  software only and is never evidence toward 80%.

### Minimum gate before any future 80% claim

A candidate is only a *sample-level research candidate* when, on real
1m/5m/15m bars, it has:

1. At least **1,000 hidden-future attempts**;
2. Direction accuracy at least **80%**;
3. Positive mean net per trade after **10 bps** costs;
4. Coverage of at least **20%** if the method can abstain;
5. Attempts, hits, horizon, symbol, date range, baseline, costs and a
   Wilson 95% confidence interval printed.

A strong statistical claim also requires the Wilson lower bound itself to
reach 80%. Even then, one series is insufficient: the project goal needs
fresh unseen validation across multiple symbols, days and market regimes.

### Development path toward the goal

1. Import lawful real 1m OHLCV from browser-direct public endpoints or user
   files; never invent minute bars from daily bars.
2. Store each symbol/timeframe in SQLite with its source and date range.
3. Run `POST /api/lab/minute-forecast` with 1,000–5,000 attempts and all
   1/3/5/15/30-bar horizons.
4. Reject candidates whose accuracy depends on tiny coverage, one horizon,
   one symbol/day, zero costs, or post-hoc parameter selection.
5. Validate survivors on later dates and other symbols that were not used
   during development.
6. Model live spread, fees, latency and partial fills separately; OHLCV does
   not contain the order book.

## 3. Integrated real bot — manual external-account companion only

**Goal:** a complete bot workflow for real markets.

**Implemented safely in v14**

- Real public market data can flow browser-direct into the lab and paper bot.
- The bot can run paper cycles, enforce halal-evidence and risk gates, and
  produce a **manual execution checklist ticket** for the user's own
  licensed exchange/broker account.
- Start, Resume, Pause, STOP, reset-risk and close-paper-positions controls
  remain explicit.

**Not implemented**

- No exchange/broker API keys or stored credentials.
- No automatic live order routing.
- No leverage, margin or short selling.
- `live_execution_enabled` is hard-coded to `false`.

Any future testnet integration must be a separately reviewed project using
the user's own licensed account, with security, legal, venue-rule and
halal-form review before live automation is even considered.

## 4. USDT / BTC funding — user account only

**Goal:** let the user trade from a USDT- or BTC-funded account.

**Safe rule:** real USDT/BTC remains only in the user's own licensed
exchange/broker account.

- TradeAtlas has **no deposit address**.
- TradeAtlas must never receive, hold, convert or withdraw real crypto.
- Funding must happen only through the official deposit screen inside the
  user's own account. TradeAtlas does not supply or verify that address.
- v14 can record an **external-account balance mirror** from numbers the user
  reports. The mirror is unverified and excluded from paper equity.

## 5. Collect and store data automatically — implemented in v16

**Goal:** let the software fetch its own lawful market data, store it
reproducibly, and measure progress toward the 80% target without deceiving
itself.

**Implemented in v16**

- Fixed allowlist collector (Binance spot, Kraken public OHLC) usable from the
  server CLI (`--collect`, `--auto`) or the browser (card 6). No arbitrary
  URLs, no keys, no accounts, read-only.
- Incremental SQLite storage with provenance (`collection_runs`), duplicate-free
  primary keys, and forming-candle rejection.
- A counted holdout (newest 20%) that the tuning loop never sees.
- Nine-gate goal tracking with Wilson intervals and a stored report history.

**What is not claimed:** automation increases sample size and honesty, not
accuracy. `goal_established` is false in every path; the strongest local
status is `goal_evidence_ready_for_independent_review`.

## 6. Learn from every failure — implemented in v15, massively expanded in v17

**Goal:** never repeat a measured research mistake. Every failed test must
name its cause, produce a rule that the next test honours, try a real remedy,
and remember the outcome so later runs avoid it.

**Implemented in v15 (21 causes) → v17 (35 causes)**

- A **35-cause library** (`selfcorrect.CAUSES` v17, `GET /api/lessons`), each with a
  meaning, an **avoid-rule**, an implemented remedy and a config patch. 14 new deep causes:
  autocorrelation_trap, volatility_regime_shift, liquidity_illusion, overparameterized_signal,
  multiple_testing_bias, non_stationary_drift, microstructure_noise, asymmetric_payoff_trap,
  tail_risk_hidden, correlation_breakdown, concept_drift, horizon_mismatch, threshold_overfit, sample_contamination.
- A three-stage loop: screen → apply lessons → validate (recent 30% slice and,
  when supplied, a second symbol).
- Lesson states `observed / resolved / recurred / retired / escalated`, plus
  `remedy_failed_twice` when a fix fails on a fair sample.
- A starved sample (too few attempts or coverage) can **never** produce a
  direction verdict; the diagnosis stops at sample quality.
- Persistent SQLite failure memory (`self_correction_runs`,
  `research_trials`, `research_lessons`) with carry-over: later runs exclude
  candidates proven dead and pre-apply patches that were resolved.
- **v17 additions:** bilingual diagnostics (Arabic/English), batch diagnosis, remedy verification,
  evolution tracker, predictive failure scoring (92% confidence for proven dead candidates).

**What is not claimed:** the loop improves the *research process*, not the
market. It cannot create an edge the sample does not contain, it never lowers
the 80% gates below, and `goal_80_established` stays false in every run.

**Today's market:** the UI fetches completed bars browser-direct (Binance spot
with a `data-api.binance.vision` fallback, or Kraken), drops the forming candle,
records provenance and stores the run. One day is never evidence of an edge.

**Bundled evidence:** real AAPL daily (506 bars, 100 attempts, 10 bps, 35
candidates) → 33 retired because a naive baseline matched or beat them, 8 with
no directional edge, 6 negative after costs, 21 over the drawdown limit, 3
cost-eaten; one survivor reached validation and is labelled **single-symbol
only**. Synthetic demo → 38 lessons, 3 resolved remedies, 16 retirements.

## 7. Halal gate — implemented rule database, not a fatwa

Bot entries require a registered asset whose current evidence screen is
exactly `pass`. Missing, failed or expired evidence blocks entry. The screen
is inspectable arithmetic over user-supplied evidence; it is not a fatwa or
halal certification.

## 8. Evolve forever — implemented in v17

**Goal:** كل مرة يفشل يحدد السبب، يتجنبه في الاختبار اللي بعده، ويلاقيلو حل — self-healing loop.

**Implemented in v17**

- **Evolution Tracker** (`evolution.py`): يتتبع الأجيال — `failure_cluster`, `predict_failure_probability`, `remedy_effectiveness`, `compute_evolution_metrics` مع resolved_rate وavoidance_efficiency.
- **Deep Diagnostics** (`diagnostics.py`): تشخيص ثنائي اللغة عربي/إنجليزي لكل سبب مع remedy_confidence وquantitative_context، و`diagnose_batch` يكشف النمط المنهجي، و`remedy_verification` يتأكد أن العلاج نجح.
- **Advanced Stats** (`marketlab.py` v17): bootstrap CI, permutation p-values, Bonferroni/FDR, Deflated Sharpe, tail risk (VaR/CVaR), autocorrelation, volatility regime, liquidity illusion, PBO.
- **Pipeline Health** (`pipeline.py` v17): health_check يكشف stale_data، adaptive_target_bars يوصي بالأعمدة، retry_collect_with_backoff بـexponential backoff.
- **SQLite v4:** جداول `evolution_generations`, `failure_clusters`, `remedy_verifications`, `diagnostic_reports`.
- **API الجديدة:** 10 endpoints جديدة ثنائية اللغة تشرح الفشل وتتجنبه في الجولة التالية.
- **143 اختبار:** كل اختبار يفشل → يشخص → يتجنب → يحل. loop حرفياً يتعلم.

**What is not claimed:** Evolution يحسن عملية البحث، ليس السوق. `goal_established` يبقى `false` دائماً.

## Machine-readable copy

- `GET /api/goals`
- `sample-project-goals.json` after `python3 tradeatlas.py --demo`
- `sample-self-correction.json` — the v15 failure-memory software check (now 35 causes)
- `sample-goal-progress.json` — the v16 gate report (goal never established)
- `sample-evolution.json` — v17 evolution tracker with cluster & remedy effectiveness
- `sample-diagnostics.json` — v17 bilingual diagnostics with batch diagnosis
- `sample-advanced-stats.json` — v17 advanced statistical honesty toolkit
- `project_goals` in `GET /api/lab/spec` and `GET /api/strategies`
