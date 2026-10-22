# TradeAtlas Core v41

Long-only spot backtest engine on **authentic** historical prices, with a proof that no
decision ever reads a future bar, and a robustness layer that says how much of the result is
real and how much is the particular order of months.

```bash
python3 app.py demo         # four windows × strategies
python3 app.py truncation   # the no-lookahead proof
python3 app.py research     # walk-forward, parameter stability, block bootstrap
python3 app.py serve        # http://0.0.0.0:8820
python3 -m unittest test_engine test_analysis -v      # 52 tests
```

No third-party packages. Both data files are vendored, so a run is reproducible offline.

## Data

| file | what | span | rows |
|---|---|---|---|
| `data/sp500_shiller.csv` | S&P 500 monthly: price, dividends (12-month total), CPI | 1871-01 → 2026-09 | 1,869 |
| `data/vix_daily.csv` | CBOE VIX daily close | 1990-01-02 → 2026-09-22 | 9,278 |

Rules enforced by tests, not by comments: the position for the next month is decided only from
data up to this month; the order fills at the next month; **10 bps per position change**; cash
earns **0%** (no interest, so the product stays long-only spot); no leverage, no shorting.

**Dividends stop being published in the Shiller file after 2023-06**, so any window that runs
past that date is computed on price alone and is labelled `price only` everywhere. Nothing is
interpolated to hide the gap.

## Main results (all measured by `app.py demo` on this machine)

| window | strategy | $1,000 becomes | CAGR | Sharpe | max DD | time in market |
|---|---|---|---|---|---|---|
| 1871-2023 | buy & hold | $586,006,107 | 9.15% | 0.69 | -81.76% | 100% |
| 1871-2023 | trend 10m | $576,978,680 | 9.14% | 0.97 | -46.48% | 63.3% |
| 1993-2023 | buy & hold | $16,341 | 9.87% | 0.81 | -49.04% | 100% |
| 1993-2023 | trend 10m | $17,784 | 10.19% | 1.14 | -19.00% | 73.8% |
| 2003-2023 | buy & hold | $6,028 | 9.56% | 0.79 | -49.04% | 100% |
| 2003-2023 | trend 10m | $5,914 | 9.46% | 1.06 | -19.00% | 76.2% |
| 2003-2026 | buy & hold | $10,640 | 10.87% | 0.90 | -49.04% | 100% |
| 2003-2026 | trend 10m | $10,189 | 10.66% | 1.17 | -19.00% | 78.8% |

## What v41 adds: the VIX era, 1990-02 → 2023-06

The fear filter (`trend10vix`) holds only when price is above its 10-month average **and** the
month-end VIX is at or below 30. A month with no VIX observation is treated as not holdable.

| strategy | $1,000 becomes | CAGR | Sharpe | max DD | time in market |
|---|---|---|---|---|---|
| buy & hold | $25,112 | 10.40% | 0.87 | -49.04% | 100% |
| trend 10m | $23,948 | 10.24% | 1.17 | -19.00% | 75.4% |
| **trend 10m + VIX≤30** | **$28,709** | **10.85%** | **1.37** | **-11.09%** | 73.3% |

Three independent checks say this is not a curve fit:

**1. Walk-forward.** Split at the end of 2006 and never look back.

| strategy | segment | CAGR | Sharpe | max DD |
|---|---|---|---|---|
| trend 10m | IS 1990-2006 | 10.46% | 1.31 | -11.62% |
| trend 10m | OOS 2007-2023 | 10.25% | 1.10 | -19.00% |
| trend 10m + VIX | IS 1990-2006 | 10.87% | 1.38 | -9.80% |
| **trend 10m + VIX** | **OOS 2007-2023** | **11.11%** | **1.41** | **-11.09%** |

Out of sample is not worse than in sample. That is the opposite of what a fitted strategy does.

**2. Parameter stability.** MA windows 6…14, with and without the VIX cap:

```
plain   CAGR min 9.18  median 10.24  max 10.66   (spread 1.48 points)
vix30   CAGR min 9.51  median 10.90  max 11.11   (spread 1.60 points)
```

A plateau, not a cliff: no single window is carrying the result, and the VIX cap improves every
window in the sweep, not just the chosen one.

**3. Block bootstrap.** 2,000 resampled paths, 12-month blocks (keeps local autocorrelation):

```
final equity   p05 $12,121   p50 $28,769   p95 $75,875
max drawdown   p05 -16.81%   p50 -11.09%   p95  -7.06%
```

## The no-lookahead proof

`truncation_test` re-runs the engine on history truncated at 122 different dates and compares
each partial run with the full run at the same month:

```
trend10    122 cutoffs · mismatches 0 · max equity delta 0.000000 · clean
buyhold    122 cutoffs · mismatches 0 · max equity delta 0.000000 · clean
```

The test is itself tested: `test_the_test_itself_detects_engine_level_leakage` plants an engine
that reads one bar ahead and asserts the harness reports mismatches. A proof that cannot fail
proves nothing.

## Why this is v41 and not a resume of v35

The v35 build (`TradeAtlas-Pro-v35.0-GoldHaven`, 24.8 MB) is in Google Drive. The sandbox that
produced it was reset, and the only channel back is the Drive connector, which returns contents
through the conversation — 24.8 MB of base64 cannot be written to a working directory that way.
Nothing was invented to paper over the gap: this build recomputes everything from public,
verifiable sources and prints what it measures. v35 is untouched in Drive and can be restored
on any machine with a browser in one download.

## What changed in the engine (found by these tests, not by reading the code)

* fees are charged at the moment of the trade instead of being subtracted from a past month —
  the old way made the equity curve depend on where the backtest stopped, and the truncation
  test caught it (10 cutoffs of 122 disagreed by exactly one fee);
* strategies are pure functions of `history`, so they cannot close over the future;
* `slice_window` is inclusive on both ends and accepts `YYYY-MM` or `YYYY-MM-DD`; the first
  version silently dropped the final month, which moved CAGR by 0.13 points.

## Limits, stated

* one index (S&P 500), not 684 series — the multi-asset atlas needs the v35 dataset;
* monthly bars, not daily, despite the VIX file being daily;
* no slippage model beyond the 10 bps fee;
* cash earns 0%, correct for a spot-only halal mandate, conservative for a US cash account;
* one market, 33 years of VIX history: the walk-forward is strong evidence, not proof.
