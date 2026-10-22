# TradeAtlas — Failure Memory (v17 — 35 causes)

> Research software only. Not financial advice. No live orders, no custody,
> no deposit address, no profit promise. The 80% target remains **unreached**.

Most backtest tools answer one question: *what was the accuracy?* A failed
test then teaches nothing, and the next run repeats the same hidden mistake —
the same optimistic cost assumption, the same single cherry-picked horizon,
the same one-symbol sample, the same volume-less feed, the same tiny subset
reported without coverage.

TradeAtlas v15 adds a **failure memory**: a loop that names why a candidate
failed, records an avoid-rule, applies an implemented remedy in the next
round, and remembers the result so a later run never repeats a proven dead
end.

```
screen ──▶ diagnose ──▶ lesson (cause + avoid-rule + remedy)
   ▲                            │
   │                            ▼
   └──── validate ◀── re-test with the remedy applied
                        │
                        ├─ cause gone      → lesson RESOLVED (reusable fix)
                        └─ cause returned  → lesson RECURRED → candidate RETIRED
```

## Why a cause library instead of one score

A pass/fail bit hides the difference between *"this idea has no edge"* and
*"this idea has an edge that fees ate"* and *"I cannot tell, because the
remedy left four attempts"*. Those three demand completely different next
actions. v15 therefore ships an inspectable taxonomy (`selfcorrect.CAUSES`),
returned by `GET /api/lessons` and `GET /api/lab/spec`.

| Cause | Severity | What it means | What the next test must do |
|---|---|---|---|
| `no_evaluable_origins` | blocker | Series too short for warm-up + horizon | Get more lawful history; never shrink the warm-up |
| `short_history` | blocker | Fewer than 20 separated origins | Same |
| `all_scores_abstained` | blocker | The method never spoke | Relax the abstention floor once; else retire |
| `insufficient_attempts` | blocker | Fewer attempts than the screen minimum | Double the attempt budget; else retire |
| `coverage_too_low` | blocker | High rate on a tiny slice | Lower the score threshold and re-measure coverage |
| `cost_filter_starved_sample` | blocker | The cost filter removed too much data | Relax the filter to 1.0× cost; retire if still starved |
| `below_accuracy_target` | goal gap | Below 80% | Keep the gap visible — it is not a knob to tune |
| `no_directional_edge` | blocker | At or below a coin flip | Retire; renaming the method is not a fix |
| `baseline_not_beaten` | blocker | Always-up / momentum matched or won | Retire; the naive baseline is the reference |
| `cost_eaten_edge` | blocker | Gross positive, net negative | Trade only when the causal expected move ≥ 2× cost |
| `negative_net_after_costs` | blocker | Negative expectancy | Retire and report the loss |
| `overfit_single_horizon` | warning→blocker | One horizon cell, neighbours collapsed | Require neighbouring horizons within 8 points |
| `walk_forward_degraded` | warning→blocker | Later slice much worse than earlier | Judge the recent 30% slice only |
| `regime_dependence` | warning→blocker | One causal regime carried the result | Require both trend regimes to be non-losing |
| `drawdown_too_deep` | blocker | Net path fell past the limit | Skip thin-edge trades, re-measure the path |
| `wide_confidence_interval` | warning | Wilson interval spans both edge and no-edge | More attempts; else keep the label unproven |
| `single_symbol_only` | warning | One series | A second symbol is required for any upgrade |
| `selection_bias` | warning | Best of many raced candidates | Held-out slice + second symbol before a claim |
| `volume_missing` | blocker | Volume method on zero-volume bars | Retire the method; never invent volume |
| `cost_below_floor` | warning | Cost assumption under the research floor | Raise it to the floor and re-score |
| `remedy_failed_twice` | blocker | Remedy applied on a fair sample, cause returned | Retire permanently and keep the avoid-rule |

**Warnings become blockers only after their gate is switched on.** That is the
mechanism by which "avoid it next time" is enforced: round 1 observes
`regime_dependence`; the next round *requires* regime stability; if the
problem persists it now blocks the candidate and retires it.

## What a remedy actually changes

Only mechanisms that exist in the evaluator are allowed as remedies. Each
cause's `patch` is applied to the **next round's config**, and the report
shows exactly which knob moved:

| Lesson | Config change |
|---|---|
| sample too small | `attempts` × 2 |
| coverage too low | `threshold_scale` → 0 (accept any non-zero score) |
| cost ate the edge | `cost_multiple` = 2.0 (skip trades whose causal expected move cannot pay twice the round-trip cost) |
| remedy starved the sample | `cost_multiple` relaxed to 1.0 |
| single-horizon overfit | `require_neighbor_support` = true |
| walk-forward decay | `require_walk_forward_ok` + `late_slice_only` |
| regime dependence | `require_regime_stability` = true |
| deep drawdown | `cost_multiple` = 1.5 |
| too many contestants | `require_second_symbol` = true |
| cost below floor | `cost_bps` = 10 |

A **starved** sample never produces a direction verdict: with four attempts,
"75% accuracy" is noise, so `diagnose` stops after the sample-quality causes
instead of reporting a headline rate.

## Resolved, recurred, retired

- **resolved** — the cause disappeared after its remedy. The lesson keeps the
  fix and is re-applied automatically in later runs on the same symbol.
- **recurred** — the same cause returned on a *fair* sample (enough attempts
  and coverage). The candidate is retired with the evidence.
- **retired** — no honest parameter change remains (no edge, baseline wins,
  negative expectancy, no volume, too little history). A retired candidate is
  a **measured negative result**, not a bug.
- **escalated** — the same cause returned after its own remedy had a fair
  sample to work with; recorded as `remedy_failed_twice`.

Carried-over lessons change the next run before it starts:

- `recurred` / `retired` / `escalated` → the candidate is **excluded** (with
  the lesson id and the reason printed in `retired_candidates`).
- `resolved` → its patch is **pre-applied**, so the same trap is not stepped
  in again.

## Validation is deliberately stingy

Promising candidates are re-tested on the **recent 30% slice** of the screen
series and, when supplied, on a **second symbol**. Outcomes are labelled:

| Verdict | Meaning |
|---|---|
| `validated_on_supplied_data_still_needs_fresh_unseen_validation` | survived screen + recent slice + second symbol on the supplied data |
| `survived_the_recent_slice_but_a_second_symbol_is_required` | one series only — a case study, not a law |
| `no_candidate_survived_validation` | nothing held up out of sample |
| `no_candidate_survived_the_failure_gates` | every candidate failed a blocker and was retired with its reason |
| `all_candidates_excluded_by_prior_lessons` | the failure memory already proved every requested candidate dead |

`goal_80_established` is **always false**. Passing this loop cannot establish
the project target: that needs ≥ 1,000 real hidden-future attempts per
candidate, positive net after 10 bps, a Wilson lower bound at the target, and
fresh validation on unseen symbols and days (see `GOALS.md`).

## Running it on today's real market

The failure loop is only as honest as its data. Two facts decide the design:

1. **This server never fetches an exchange.** TradeAtlas ships no feed proxy
   on purpose: no SSRF surface, no API keys, no hidden data licensing.
2. **Your browser fetches the bars**, from public keyless endpoints, and posts
   them to `/api/lab/self-correct`.

Card **5C · Failure Memory** therefore has a *Real market test for today*
block:

| Step | What happens |
|---|---|
| Venue | Binance spot public klines (`data-api.binance.vision` first, then `api.binance.com`) or Kraken public OHLC |
| Symbols | primary **and** a second symbol, so the validation round has an independent sample |
| Bars | 405–1000 most recent **completed** bars (the still-forming candle is dropped, for Binance by `closeTime <= now`, for Kraken by `slice(0, -1)`) |
| Costs | default **12 bps** round trip (Binance spot taker is roughly 7.5–10 bps per side depending on tier — raise it, never lower it to make a result look better) |
| Loop | screen → apply lessons → validate, `attempts = 150`, horizons 3/5/15 |
| Provenance | venue, endpoint URL, primary/validation symbols, bar counts, first and last **completed** bar in UTC, fetch time, `forming_candle_dropped: true`, and the server receipt time |
| Storage | the run, its trials and its lessons go to SQLite; `GET /api/lessons` shows the latest run with its provenance |

Opening the app with `?today=1` runs the same test automatically.

If the venue is blocked in your region or a browser extension breaks CORS, the
UI says so. Export the bars yourself and use the paste/upload path in card 5C —
the analysis is identical, and the provenance then becomes *your* file.

**What a same-day run can and cannot say.** A single day of 1m bars is a very
short sample: the loop will usually retire most candidates for `baseline_not_beaten`
or `cost_eaten_edge`, and it may find one that survives the recent slice. Even
a two-symbol survivor is labelled
`validated_on_supplied_data_still_needs_fresh_unseen_validation` — days, not
minutes, are needed before anything resembles an edge. `goal_80_established`
stays false, always.

## Worked example — bundled real AAPL daily

`real-data/aapl-daily-2015-2017.plotly.csv`, 506 real daily bars, 100 attempts,
10 bps, seven methods × horizons (1, 3, 5, 10, 20):

- **Round 1 (screen, 35 candidates):** 33 retired immediately because a naive
  baseline was at least as good (`baseline_not_beaten`), 8 had no directional
  edge, 6 had negative expectancy, 21 breached the drawdown limit, 3 lost
  their gross edge to costs.
- **Round 2 (apply lessons):** the two survivors faced the drawdown remedy;
  one was retired (`drawdown_too_deep` recurred).
- **Round 3 (apply lessons):** one candidate remained.
- **Round 4 (validation):** no second symbol was supplied, so the survivor is
  labelled `sample_local_only_single_symbol` — **not** validated.

Verdict: `survived_the_recent_slice_but_a_second_symbol_is_required`.

That is the intended product: on this sample the honest conclusion is that
most classic signals do not beat naive momentum after costs, one candidate is
a single-symbol curiosity, and the 80% goal is untouched.

## Worked example — synthetic software check

`python3 tradeatlas.py --demo` (or the UI button) runs the loop on two
deterministic invented 1m series. It produces **38 lessons, 3 resolved
remedies, 16 retirements over 4 rounds**, and proves the code path — never
market evidence. The file is `sample-self-correction.json`.

## API

| Endpoint | Purpose |
|---|---|
| `POST /api/lab/self-correct` | run the loop (`bars`/`csv_text`; optional `second_bars`/`second_csv_text`; optional `provenance` object echoed and stored) |
| `GET /api/lessons?symbol=&status=` | the persisted lesson ledger + cause tally + cause library |
| `GET /api/failure-memory` | tally, latest run, recent lessons, loop spec |
| `POST /api/lessons/clear` | forget lessons (`{symbol}` optional) — only with genuinely new data or methods |

Request keys: `methods`, `horizons`, `attempts`, `cost_bps`, `rounds`,
`symbol`, `remember` (default true), `use_saved_lessons` (default true).

## Storage

SQLite (`tradeatlas.db`, schema v2) gains three tables:

- `self_correction_runs` — one row per run with its verdict and summary,
- `research_trials` — per-round cause tallies and retirements,
- `research_lessons` — the durable lesson ledger, keyed by
  `(lesson_uid, symbol_key)` so the same failure keeps one identity and can be
  upgraded to `resolved` instead of duplicated.

No broker credentials, payment instruments, deposits or orders are stored.

## Tests

`test_tradeatlas.py` grows from 49 to **67** tests; the v15 block covers the
cause library, causal score arrays, each diagnosis family, severity gating,
lesson stability and avoid-rules, patch application and relaxation, the
resolution path, retirement reasons, carry-over avoidance, pre-applied
resolved patches, the single-symbol honesty rule, the two-symbol validation
path, determinism, input rejection, SQLite persistence/deduplication/
clearing, HTTP endpoints, the browser-fetched today-market payload with its
provenance round-trip, the provenance-aware UI wiring, and the "no shortcut to
80%" rule.

## Limits

- The loop improves the **research process**, not the market. It cannot
  manufacture an edge the sample does not contain.
- Regime labels are causal (trailing medians) so no regime is chosen after
  seeing the result.
- The cost filter is a crude expected-move proxy; it does not model the order
  book, spread history, latency, queue position or partial fills.
- Synthetic series validate software only. Every real number stays attached to
  its symbol, date range, attempts, coverage, horizon and costs.
