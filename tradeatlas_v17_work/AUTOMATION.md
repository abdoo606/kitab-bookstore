# TradeAtlas — Automation, Storage and the Honest Road to 80% (v16)

> Research software only. Not financial advice. No broker, no custody, no
> deposit address, no order routing. **`goal_established` is false in every
> code path** — including this automation.

## The short answer about "raising accuracy to 80%"

Software can automate three things honestly:

1. **Getting more lawful data** (more symbols, more days, deeper history).
2. **Storing it reproducibly** with provenance and without duplicates.
3. **Measuring it without fooling itself** (holdout, costs, Wilson intervals,
   baselines, failure memory).

Software **cannot** make a losing signal win. If the honest measured rate on
real data is 63%, no redesign, no button and no parameter sweep raises it —
only new *out-of-sample* evidence can. This release therefore does not claim
80% and does not tune on the data it reports. What it does is build the only
legitimate road to that number and print the real distance to it, gate by
gate.

## 1. Two collectors, one allowlist

| Collector | Runs where | Use it when |
|---|---|---|
| **Server** (`python3 tradeatlas.py --collect`) | the TradeAtlas process | your machine has outbound network |
| **Browser** (card 6 button) | your browser | the server is sandboxed or blocked |

Both use the same **fixed host allowlist**:

```
binance -> api.binance.com, data-api.binance.vision   (/api/v3/klines)
kraken  -> api.kraken.com                             (/0/public/OHLC)
```

- No arbitrary URLs. `check_url()` refuses any other host, any non-http(s)
  scheme, and private addresses unless a test explicitly opts in.
- No API keys, secrets, logins or accounts. Public, keyless endpoints only.
- Read-only market data. Nothing here can place an order.
- The still-forming candle is always dropped (Binance by `closeTime <= now`,
  Kraken by discarding the last row), so no bar is ever "half-formed".

## 2. Incremental storage

`collect_series()` works in two steps:

1. fetch the **newest page** and keep only bars newer than the newest stored
   bar (this makes repeat runs cheap — and is what makes history grow);
2. if the stored bar count is still below the target, walk **backwards** with
   an end-time cursor and keep only bars older than the oldest stored bar.

Both write through `MarketDatabase.import_bars()`, whose primary key
`(symbol, timeframe, t)` makes duplicates impossible. Stored key format:

```
BINANCE.BTCUSDT.1m      KRAKEN.XBTUSD.5m
```

Each run writes a row to `collection_runs` with venue, requested bars,
inserted bars, previously stored, total stored, first/last bar (UTC), request
count, endpoints and errors. A failed venue is recorded as an error — it
never corrupts the store and never silently looks like success.

## 3. Holdout: the anti-self-deception device

The newest **20%** of every series is reserved:

- `split_holdout(bars)` returns `(tuning, holdout)`; the tuning loop and the
  failure memory only ever see `tuning`.
- `holdout_evaluation()` is the **only** reader of the reserved slice, and
  every single call writes a row to `holdout_runs`.
- `goal_progress()` requires a recorded holdout evaluation, and reports the
  number of reads. Re-reading turns the holdout into tuning data; the counter
  makes that visible instead of invisible.

This is the difference between "our accuracy went up" and "our accuracy went
up because we looked at the answers".

## 4. The gate-by-gate goal tracker

`goal_progress()` pools hidden-future attempts across **all** stored series and
checks nine gates:

| Gate | Requirement | Why |
|---|---|---|
| `attempts` | ≥ 1000 hidden-future attempts per candidate | small samples swing by chance |
| `accuracy` | ≥ 80% pooled direction accuracy | the stated target |
| `wilson_lower` | Wilson 95% lower bound ≥ 80% | a point estimate is not proof |
| `costs` | positive mean net after 10 bps | a gross edge is not tradable |
| `coverage` | ≥ 20% when the method can abstain | no tiny filtered subsets |
| `symbols` | ≥ 3 symbols | one symbol is a case study |
| `days` | ≥ 30 distinct UTC days | one day is noise |
| `holdout` | a recorded holdout evaluation | no peeking |
| `external` | fresh unseen validation outside this database | always `false` locally |

The report returns `gates_passed/gates_total`, the measured value of each
gate, `distance_to_target_points`, the pooled candidate table (with Wilson
intervals and coverage) and a status:

- `no_evidence_yet`
- `below_target_on_local_data`
- `goal_evidence_ready_for_independent_review` — only if every measurable gate
  passes (the `external` gate still fails by construction, so this means
  "ready for someone independent to try to break it")

`goal_established` is **false** in all three. That is deliberate: a local
database cannot prove a universal rate.

## 5. Card 6 in the UI

- **Collect on the server** — runs `/api/pipeline/collect`.
- **Collect in my browser, then store in SQLite** — fetches each symbol
  browser-direct and posts `/api/pipeline/import`.
- **Grade everything stored** — `/api/lab/auto-research` pools evidence across
  stored series.
- **Evaluate the reserved holdout** — `/api/lab/holdout` (recorded).
- **Refresh 80% goal progress** — `/api/goal-progress`, drawn as a bar plus a
  gate table with pass/fail and the measured values.

## 6. CLI

```bash
# one incremental collection, then a goal report
python3 tradeatlas.py --collect --symbols BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT \
    --interval 1m --target-bars 5000 --db tradeatlas.db

# keep collecting and re-measuring (every 10 minutes, 6 cycles, 3 symbols)
python3 tradeatlas.py --auto --venue binance --symbols BTCUSDT,ETHUSDT,SOLUSDT \
    --interval 1m --target-bars 5000 --cycles 6 --sleep 600
```

Each cycle prints the collection result and the gate status, and stores a
`goal_reports` row so progress over time is auditable.

## 7. API

| Endpoint | Purpose |
|---|---|
| `POST /api/pipeline/collect` | server-side allowlisted collection (`venue`, `symbols`, `interval`, `target_bars`) |
| `POST /api/pipeline/import` | store browser-fetched `series[]` (`symbol`, `interval`, `bars`, `endpoint`) + `provenance` |
| `POST /api/lab/auto-research` | pooled evidence over everything stored |
| `POST /api/lab/holdout` | evaluate + record the reserved slice for one stored symbol |
| `GET /api/goal-progress` | gate-by-gate honest distance to 80% (stored in `goal_reports`) |
| `GET /api/pipeline/status` | collections, holdout count, goal history, DB stats, spec |

## 8. Storage schema (v3)

New tables: `collection_runs`, `holdout_runs`, `goal_reports` — alongside
`bars`, `instruments`, `research_runs`, `self_correction_runs`,
`research_trials`, `research_lessons`, `halal_*`, `bot_events`.

Nothing in the database contains credentials, payment instruments, deposits
or orders.

## 9. A realistic expectation

With four 1m symbols × 3,000 bars you have roughly 2 days of history and about
12,000 bars: plenty of attempts, but **1–2 distinct days** and only one venue
era. The tracker will typically report:

```
attempts    pass
accuracy    fail  (≈ 50–65% is the normal honest range)
wilson      fail
costs       fail or borderline at 12 bps
coverage    pass
symbols     pass (4)
days        fail (≈ 2 < 30)
holdout     pass after one recorded run
external    fail (always, locally)
→ below_target_on_local_data · goal_established = false
```

To move the `days` gate you must keep collecting across weeks (that is what
`--auto` is for), then validate survivors on symbols and days that were never
used for tuning. That is the whole honest program; anything faster is either
luck or a leak.

## 10. Tests

`test_tradeatlas.py` is now **77** tests. The v16 block proves, offline:

- the allowlist rejects arbitrary hosts, schemes and un-approved private
  addresses;
- parsers drop the forming candle and reject malformed payloads;
- backfill works, a repeat run adds nothing, and genuinely new bars are
  appended without duplicates;
- a broken venue is recorded as an error and leaves storage untouched;
- a multi-symbol plan collects every symbol;
- the holdout is the newest slice, is never touched by tuning, and every read
  increments a counter;
- pooled evidence returns consistent attempts/hits/Wilson bounds, an empty DB
  is honestly `no_evidence_yet`, and `goal_established` is false everywhere;
- the HTTP import → research → progress → holdout flow works, with 400s for
  bad input;
- the CLI exposes `--collect/--auto/--symbols/--interval/--cycles` and an
  unreachable venue fails visibly;
- the UI and specs expose automation without any banned profit language.
