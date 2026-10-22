# TradeAtlas Core v40

Long-only spot backtest engine on **authentic** historical prices, with a proof that no
decision ever reads a future bar.

```bash
python3 app.py demo         # four windows × two strategies
python3 app.py truncation   # the no-lookahead proof
python3 app.py serve        # http://0.0.0.0:8820
python3 -m unittest test_engine -v      # 32 tests
```

No third-party packages. The data file is vendored, so a run is reproducible offline.

## Why this is v40 and not a resume of v35

The v35 build (`TradeAtlas-Pro-v35.0-GoldHaven`) is 24.8 MB and lives in Google Drive. The
sandbox that produced it was reset, and the only channel back into this session is the Drive
connector, which returns file contents through the conversation — 24.8 MB of base64 cannot be
written to a working directory that way. **Nothing was invented to paper over the gap.**
Instead of restating v35's numbers from its README, this build recomputes everything from a
public, verifiable source and prints what it measures.

Downloads of the old builds are untouched in Drive; restoring v35 on a machine with a browser
is one click: `TradeAtlas-Pro-v35.0-GoldHaven-1961505-USD.zip` (folder `17d6N0YLTQ...`).

## What is measured here

Data: Robert Shiller's monthly S&P 500 series, 1871-01 → 2026-09 (1,869 rows), vendored at
`data/sp500_shiller.csv`. `Dividend` is a 12-month moving total, so monthly income is `D/12`.

Rules enforced by tests: position next month is decided only from data up to this month; order
filled at the next month; **10 bps per position change**; cash earns **0%** (no interest, so the
product stays long-only spot); no leverage, no shorting.

| window | strategy | $1,000 becomes | CAGR | Sharpe | max DD | time in market |
|---|---|---|---|---|---|---|
| 1871-2023 (total return) | buy & hold | $586,006,107 | 9.15% | 0.69 | -81.76% | 100% |
| 1871-2023 (total return) | trend 10-month | $576,978,680 | 9.14% | **0.97** | **-46.48%** | 63.3% |
| 1993-2023 (total return) | buy & hold | $16,341 | 9.87% | 0.81 | -49.04% | 100% |
| 1993-2023 (total return) | trend 10-month | **$17,784** | **10.19%** | **1.14** | **-19.00%** | 73.8% |
| 2003-2023 (total return) | buy & hold | $6,028 | 9.56% | 0.79 | -49.04% | 100% |
| 2003-2023 (total return) | trend 10-month | $5,914 | 9.46% | 1.06 | -19.00% | 76.2% |
| 2003-2026 (price only) | buy & hold | $10,640 | 10.87% | 0.90 | -49.04% | 100% |
| 2003-2026 (price only) | trend 10-month | $10,189 | 10.66% | 1.17 | -19.00% | 78.8% |

**Dividends stop being published in this source after 2023-06**, so the `recent` window is
price-only and is labelled that way everywhere. The engine does not interpolate or estimate the
missing income — that would be synthetic data.

## The no-lookahead proof

`truncation_test` re-runs the whole engine on history truncated at 122 different dates and
compares each partial run against the full run at the same month:

```
trend10    122 cutoffs · mismatches 0 · max equity delta 0.000000 · clean
buyhold    122 cutoffs · mismatches 0 · max equity delta 0.000000 · clean
```

The test is itself tested: `test_the_test_itself_detects_engine_level_leakage` plants a variant
engine that reads one bar ahead and asserts the harness reports mismatches. A proof that cannot
fail proves nothing.

## What changed vs the earlier engine

* fees are charged at the moment of the trade instead of being subtracted from a past month
  (the old way made an equity curve depend on where the backtest stopped — the truncation test
  caught this, 10 cutoffs of 122 disagreed by exactly one fee);
* strategies are pure functions of `history`, so they cannot close over the future;
* every number above is produced by `app.py demo` on this machine, not copied from a README.

## Limits, stated

* one index (S&P 500), not 684 series — the multi-asset atlas needs the v35 dataset;
* monthly bars, not daily;
* no slippage model beyond the 10 bps fee;
* cash earns 0%, which is conservative for a US cash account and correct for a spot-only
  halal mandate.

## Where this file lives

Canonical build: this directory (`builds/tradeatlas-core/`) — it survives resets because it is
in git. Distribution copy: `TradeAtlas-Core-v40-authentic-32-tests.zip` in the TradeAtlas Drive
folder. The standalone runtime at `/home/user/tradeatlas` was a working copy and has been
removed to avoid two diverging trees.
