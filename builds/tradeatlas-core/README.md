# TradeAtlas Core v42

Long-only spot backtest engine on **authentic** historical prices, with a proof that no
decision ever reads a future bar, a robustness layer that says how much of the result is
real, and — as of v42 — a published live signal, an execution-cost curve, and a correction
for the fact that we tried eighteen rules before picking one.

```bash
python3 app.py demo         # four windows × strategies
python3 app.py truncation   # the no-lookahead proof
python3 app.py research     # walk-forward, parameter stability, bootstrap, costs, deflated Sharpe
python3 app.py signal       # the position to hold next month, from the last complete bar
python3 app.py serve        # http://0.0.0.0:8820
python3 -m unittest test_engine test_analysis -v      # 73 tests
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

## The live signal (v42)

`app.py signal` answers the only question a subscriber asks: what do I hold next month, and why.

```
TradeAtlas signal for 2026-10  (data through 2026-09)
  position: IN
  - price 7,669.41 vs 10-month average 7,201.20 (+6.5%)
  - VIX 14.21 vs cap 30
  rule: hold equity while price > 10-month average AND VIX <= 30;
        otherwise cash; one switch costs 10 bps
```

Printed on 2026-10-22. The rule is the same `trend_vix(10, 30)` object the backtest uses — the
signal endpoint does not re-implement it, so the published number cannot drift from the tested
one. `GET /api/signal` returns the same payload plus the flip level (the 10-month average at
which the trend filter turns off).

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

## The VIX era, 1990-02 → 2023-06

The fear filter (`trend10vix`) holds only when price is above its 10-month average **and** the
month-end VIX is at or below 30. A month with no VIX observation is treated as not holdable.

| strategy | $1,000 becomes | CAGR | Sharpe | max DD | time in market |
|---|---|---|---|---|---|
| buy & hold | $25,112 | 10.40% | 0.87 | -49.04% | 100% |
| trend 10m | $23,948 | 10.24% | 1.17 | -19.00% | 75.4% |
| **trend 10m + VIX≤30** | **$28,709** | **10.85%** | **1.37** | **-11.09%** | 73.3% |

Four independent checks say this is not a curve fit.

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

**4. Deflated Sharpe ratio (new in v42).** The sweep above tried 18 rules. A maximum taken over
18 tries is biased upward by construction, so the honest question is not "Sharpe 1.37" but "how
surprising is 1.37 given that we looked at 18 things". Bailey & López de Prado's correction
answers exactly that:

```
winner Sharpe            1.37  (annualised)
expected max under null  0.22  (18 trials, same dispersion)
skew -0.08 · kurtosis 5.24 · z = +5.98 · P(true Sharpe > 0) ≈ 1
```

The winner clears its own search by a wide margin. Note the kurtosis of 5.24: the return series
has fat tails, and the correction divides by them rather than ignoring them.

## Execution cost (new in v42)

10 bps is the commission. Real fills also pay the spread and impact, so `cost_sensitivity()`
re-runs the winner at all-in cost levels and reports how much cost the rule can absorb:

| all-in cost per switch | $1,000 becomes | CAGR | Sharpe | max DD |
|---|---|---|---|---|
| 10 bps | $28,709 | 10.85% | 1.37 | -11.09% |
| 20 bps | $27,389 | 10.69% | 1.35 | -11.18% |
| 30 bps | $26,128 | 10.53% | 1.33 | -11.27% |
| 50 bps | $23,775 | 10.21% | 1.29 | -11.44% |
| 100 bps | $18,762 | 9.42% | 1.19 | -12.48% |

47 trades over 33 years is roughly one and a half a year: even a tenfold error in the cost
assumption leaves the CAGR above 9.4%. Cost is not what decides this strategy.

## The no-lookahead proof

`truncation_test` re-runs the engine on history truncated at 122 different dates and compares
each partial run with the full run at the same month:

```
trend10    122 cutoffs · mismatches 0 · max equity delta 0.000000 · clean
buyhold    122 cutoffs · mismatches 0 · max equity delta 0.000000 · clean
```

The same proof now runs with slippage switched on (`test_truncation_is_clean_with_slippage`), so
the cost layer cannot smuggle in a future read either.

The test is itself tested: `test_the_test_itself_detects_engine_level_leakage` plants an engine
that reads one bar ahead and asserts the harness reports mismatches. A proof that cannot fail
proves nothing.

## Why this is v42 and not a resume of v35

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
  version silently dropped the final month, which moved CAGR by 0.13 points;
* v42 splits commission (`fee_bps`) from execution shortfall (`slippage_bps`) so a run can be
  re-priced without touching the rule; default slippage is 0, which is why every v41 number
  above is unchanged to the cent.

## Limits, stated

* one index (S&P 500), not 684 series — the multi-asset atlas needs the v35 dataset;
* monthly bars, not daily, despite the VIX file being daily;
* cash earns 0%, correct for a spot-only halal mandate, conservative for a US cash account;
* one market, 33 years of VIX history: the walk-forward is strong evidence, not proof;
* the cost curve is a *model*: it re-prices the same trades, it does not simulate order books;
* the live signal inherits the dividend gap: it is a price-only trend rule, and it says so.
