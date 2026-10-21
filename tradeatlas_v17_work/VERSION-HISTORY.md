# TradeAtlas version and forecast-attempt history

**Purpose:** preserve the research trail version by version, including the
methods that failed. A method is not called “better” merely because a later
version added it; the table records what the same hidden-future tests
actually measured.

**Last updated:** 2026-10-21, TradeAtlas v16.0.

> **No version reached or proved a universal 80% direction rate.** The
> strongest current evidence is much narrower: 68% for one method on one
> 100-attempt AAPL daily sample, 60% on the 40-attempt MSFT monthly sample,
> and 63.077% for the best full-coverage method over a small 260-attempt
> bundled database pool. v14 makes 80% an explicit minute-trading goal and
> adds the race/gates needed to test it, but it bundles no real minute
> sample and therefore adds no real minute accuracy headline.

## How every forecast attempt works

1. Choose a historical **origin bar**.
2. Give the method only bars up to that origin.
3. Hide the following bars.
4. Record the method's up/down call.
5. Reveal the later bars only to score the call after the chosen horizon.
6. Repeat at separated origins (attempts).
7. Report direction accuracy **and** the number/coverage of attempts, a
   naïve momentum/always-up baseline where applicable, horizons, and mean
   net return after 10 and 25 basis points (bps) of round-trip cost.

Analog methods may use only earlier analog outcomes whose full future window
was already known before the origin. The adaptive selector, Atlas Meta Hedge
and Atlas Online Logistic likewise update only from fully revealed earlier
attempts. Future-mutation tests verify that changing later bars cannot change
origin-time scores/forecasts.

From v14, the dedicated minute race reports horizons 1/3/5/15/30 bars,
attempts/hits, coverage for abstaining methods, Wilson 95% intervals and
mean net after 5/10/25 bps. A future 80% candidate needs at least 1,000 real
hidden-future attempts, positive 10-bps expectancy and (for selective rows)
at least 20% coverage. A strong statistical claim additionally needs the
Wilson lower bound at 80%, followed by fresh validation across symbols/days.

“Best on this sample” is a **retrospective label**. Selecting the maximum
after racing more and more methods creates a selection/multiple-comparison
bias; pooled series, other horizons, costs and genuinely new data are the
better check.

## Primary real samples

| Sample | Data | Attempts | Main horizon | Baselines |
|---|---:|---:|---:|---:|
| AAPL daily | 506 real daily OHLCV bars, 2015–2017, bundled public sample | 100 | 5 bars | Always-up 56%; naïve 5-bar momentum 58% |
| MSFT monthly | 123 real monthly bars, 2000–2010; close-only conversion makes OHLC equal close and volume zero | 40 | 3 bars | Always-up 47.5%; naïve 5-bar momentum 55% |
| Bundled SQLite pool | 1,066 bars / 5 evaluable series; GOOG monthly is stored but its 68 bars are below the pooled minimum | 260 | AAPL 5d; monthly series 3mo | Compare full-coverage methods separately from filtered subsets |
| Real minute sample | **None bundled in v14**; import lawful completed 1m/5m/15m bars from a browser/user file | Goal gate requires ≥1,000 per candidate | 1/3/5/15/30 bars | Momentum baselines, coverage and 5/10/25-bps costs must be shown |

The samples are useful for falsification and software research, but they are
small, era-bound and partly survivor-biased. They do not represent “all
global markets”. Crypto/FX/commodity/index support means the software can
research lawful OHLCV from the browser or user files; it does not bundle
licensed histories for every market.

## Attempt development by version

### Before the hidden-future forecast race: v1–v3

- **v1–v2:** the educational atlas and first bring-your-own-data Market Lab.
- **v3:** multi-timeframe signal validation, engine tournaments,
  walk-forward splitting, watchlists and market-presets research.
- There was not yet a versioned **100-attempt hidden-future forecast race**;
  no forecast accuracy should be retrospectively invented for this era.

### v4.0 — first analog forecaster

- **Idea:** describe the current setup by 1/3/5/10/20-bar returns, RSI,
  distance from SMA-20 and volatility; find similar earlier setups and look
  at what they did next.
- **AAPL 100 attempts:** analog median **44.0%**, always-up 56.0%, naïve
  momentum 58.0%; Brier skill −0.13.
- **Lesson:** look-alike history, unweighted, did not beat naïve rules.
- **Tests:** 18/18.

### v5.0 — horizons, regimes and a second real sample

- **Idea:** test the same forecaster at horizons 1/3/5/10/20, split results
  by causal trend/volatility regimes, and evaluate MSFT monthly.
- **AAPL analog by horizon:** 41/44/44/47/36%.
- **MSFT 40 attempts:** analog **45.0%** vs momentum 55.0%.
- **Lesson:** no hidden pocket of skill appeared; an isolated higher horizon
  cell was exposed as a likely multiple-comparison cherry.
- **Tests:** 20/20.

### v6.0 — ensembles and costs

- **Ideas:** distance-weighted analogs, majority vote, agreement-only subset,
  and scoring after 10/25 bps costs.
- **AAPL:** weighted 48.0%; majority 55.0%; agreement 56.0% on only 50%
  coverage. The best ensemble was approximately 0%/trade after 10 bps.
- **Improvement vs v4 analog:** majority was +11 percentage points
  (+25.0% relative), but still 3 points below naïve momentum.
- **Lesson:** ensembling partly recovered the gap, while costs erased the
  apparent value.
- **Tests:** 22/22.

### v7.0 — candle-structure neighbours

- **Ideas:** gap, range, body, upper/lower wicks, close location and volume
  shape joined the analog feature space.
- **AAPL:** candle methods 50.0%/49.0%; expanded combined vote 57.0% vs
  momentum 58.0%; combined +0.158%/trade at 10 bps and +0.008% at 25 bps.
- **Improvement vs v4 analog:** +13 percentage points (+29.5% relative),
  still 1 point below momentum on the same test.
- **Lesson:** a richer description of yesterday's candles did not reveal
  tomorrow.
- **Tests:** 25/25.

### v8.0 — indicator-regime neighbours

- **Ideas:** RSI/MACD/Bollinger/SMA/Donchian/Stochastic/ADX/volatility/volume
  coordinates; `majority_vote_v3`; filtered `consensus_3plus`.
- **AAPL:** indicator methods 49.0%/46.0%; `majority_vote_v3` 46.0% vs
  momentum 58.0%. Consensus reached 65.4% only on 26/100 attempts and lost
  after 25 bps.
- **Lesson:** correlated indicators can agree about the same past move.
  Filtered accuracy without coverage and costs is not evidence of a general
  65%—or 80%—forecaster.
- **Tests:** 28/28.

### v9.0 — path geometry and a causal adaptive selector

- **Ideas:** path efficiency, log-price slopes, variance ratio,
  autocorrelation, skew, excursion/drawdown, compression, streaks and volume
  balance; `majority_vote_v4`; a selector that learns which earlier method
  had been best only from already revealed attempts.
- **AAPL:** path methods 47.0%/47.0%; v4 vote 51.0%; selector 54.0% vs
  momentum 58.0%; selector −0.191%/trade at 10 bps (as originally measured
  with the v9 pool).
- **MSFT:** selector 40.0%, −4.417%/trade at 10 bps.
- **Lesson:** causal model selection prevents leakage, not loss. A selector
  cannot manufacture information absent from its contestants.
- **Tests:** 32/32.

### v10.0 — cycle/flow neighbours and direct multiscale trend

- **Ideas:** cycle/flow analogs; invented Signed Path Pressure and
  Entropy-Weighted Trend; direct 3/5/10/20/60/120-bar multiscale trend;
  `majority_vote_v5`; browser public market-data adapters; paper wallet.
- **AAPL:** multiscale **60.0%** vs momentum 58.0%; +0.290%/trade at
  10 bps and +0.140% at 25 bps.
- **MSFT:** multiscale **57.5%**, +2.850%/trade at 10 bps.
- **Improvement:** AAPL multiscale was +16 points / +36.4% relative to the
  original analog, but only +2 points / +3.4% relative to momentum. MSFT was
  +12.5 points / +27.8% relative to its original analog.
- **Lesson:** the first sample-local full-test win over momentum on both
  primary samples was real arithmetic, not yet a durable edge.
- **Tests:** 36/36. Signal engines: 14.

### v11.0 — Kalman, Omni, rank fusion and the halal paper bot

- **Ideas:** alpha-beta/Kalman-style local log-price trend; Omni weighted
  direct consensus; rank-fusion neighbours; `majority_vote_v6`; six new
  engines; evidence-gated halal-stock paper bot.
- **AAPL:** Omni **64.0%**, Kalman 62.0%, multiscale 60.0%, momentum 58.0%,
  original analog 44.0%. Kalman +0.846%/trade and Omni +0.641% at 10 bps.
- **MSFT:** Kalman **60.0%**, multiscale/Omni 57.5%, momentum 55.0%.
- **Improvement:** Kalman vs original analog was +40.9% relative on AAPL and
  +33.3% on MSFT, but only +6.9%/+9.1% relative to momentum. Rank fusion
  lost.
- **Lesson:** classic filtering improved both primary tests, but did not
  establish a universal improvement or 80%.
- **Tests:** 40/40. Signal engines: 20.

### v12.0 — Hull/Kaufman/Haar/Markov, SQLite memory and evidence database

- **Ideas:** Hull MA, Supertrend, Kaufman AMA, Haar wavelet, Donchian state,
  causal Markov regime vote, `atlas_fusion_v12`, `majority_vote_v7`, a
  persistent SQLite market/halal/research database and pooled research.
- **AAPL:** Hull **67.0%**, Atlas Fusion 64.0%, Markov 63.0%, Kaufman 62.0%;
  Hull +0.786%/trade at 10 bps and +0.636% at 25 bps. Hull horizons
  1/3/5/10/20 were 51/62/67/61/56%.
- **MSFT:** Atlas Fusion, Supertrend and Kaufman tied Kalman at **60.0%**;
  Hull fell to 52.5%.
- **Bundled pool:** Atlas Fusion **62.692% over 260 attempts**
  (+2.712%/trade at 10 bps). `consensus_3plus` was 64.109% on only 83
  attempts and therefore was not called the full-coverage winner.
- **Improvement:** the retrospective AAPL maximum rose 64→67%. No durable
  claim followed because Hull reversed on MSFT and neighbouring horizons.
- **Lesson:** a database makes comparisons stronger; it does not turn
  correlated historical samples into prophecy.
- **Tests:** 44/44. Signal engines: 24.

### v13.0 — more classics, three invented scores, online learners, presets and demo wallet

#### What was added

1. **Classic direct scores/engines:** Aroon, TSI, TRIX, CMO, Ultimate
   Oscillator, RVI, 20/60-bar regression fusion, Donchian state, OBV flow
   and Coppock.
2. **Atlas Pressure Wave (invented):** ATR/range- and real-volume-aware
   exponentially weighted candle-pressure decay plus 3/10-bar
   volatility-normalized momentum. If volume/candle anatomy are absent, it
   collapses to an honestly labelled close-path variant.
3. **Atlas Regime Compass (invented):** ADX and permutation entropy create a
   smooth trend/range regime weight. High trend-regime weight favours
   Hull+multiscale evidence; low weight favours range-reversion evidence.
4. **Atlas Phoenix Fusion (invented):** family-first fusion of trend
   filters, momentum oscillators, price structure, OHLCV flow proxies and
   the Compass, preventing correlated indicators from voting many times.
5. **Atlas Meta Hedge:** delayed-label exponential Hedge over 16 diversified
   existing contestants (`loss = 1 − sign score × realized sign`).
6. **Atlas Online Logistic:** one L2-regularized stochastic-gradient update
   per revealed label over 15 bounded causal features.
7. **`majority_vote_v8`:** previous ensemble plus new direct/invented signs.
8. **Usability:** “Start here” four-step workflow, one-click Binance/
   Kraken/Stooq market presets, Forecast Lab on current bars, explicit
   Start/Resume/Pause/STOP labels.
9. **Demo e-wallet:** imaginary multi-asset balances, imaginary conversion
   to PAPER_USD, imaginary withdrawal removal, and internal PAPER_USD
   transfers between standalone wallet and paper bot. No real funds/crypto.

#### AAPL daily — 100 attempts, horizon 5

| Method | Direction | Mean net/trade @10 bps | Mean net/trade @25 bps |
|---|---:|---:|---:|
| `ultimate_trend` | **68.0%** | +0.893% | +0.743% |
| `hull_trend` | 67.0% | +0.786% | +0.636% |
| `tsi_momentum` | 65.0% | +1.071% | +0.921% |
| `omni_direct_consensus` | 64.0% | +0.641% | +0.491% |
| `atlas_fusion_v12` | 64.0% | +0.672% | +0.522% |
| `atlas_pressure_wave` | 64.0% | +0.635% | +0.485% |
| `adaptive_selector` (v13 pool) | 63.0% | +0.763% | +0.613% |
| `kalman_trend` | 62.0% | +0.846% | +0.696% |
| `atlas_regime_compass` | 62.0% | +0.516% | +0.366% |
| `atlas_phoenix_fusion` | 62.0% | +0.564% | +0.414% |
| `atlas_meta_hedge` | 61.0% | +0.492% | +0.342% |
| `atlas_online_logistic` | 61.0% | +0.397% | +0.247% |
| `majority_vote_v8` | 61.0% | +0.393% | +0.243% |
| `multiscale_trend` | 60.0% | +0.290% | +0.140% |
| `momentum_5bar` baseline | 58.0% | +0.166% | +0.016% |
| original `analog_median` | 44.0% | −0.988% | −1.138% |

Direct-method horizons on AAPL:

| Method | 1 bar | 3 bars | 5 bars | 10 bars | 20 bars |
|---|---:|---:|---:|---:|---:|
| Ultimate | 55% | 62% | **68%** | 59% | 58% |
| TSI | 56% | 62% | 65% | 53% | 52% |
| Pressure Wave | 54% | 57% | 64% | 57% | 51% |
| Regime Compass | 53% | 55% | 62% | 62% | 57% |
| Phoenix | 50% | 52% | 62% | 53% | 51% |

The 68% cell fades at 1, 10 and 20 bars. That horizon sensitivity is part of
the result, not an inconvenient footnote.

#### MSFT monthly — 40 attempts, horizon 3

| Method | Direction | Mean net/trade @10 bps | Mean net/trade @25 bps |
|---|---:|---:|---:|
| `atlas_pressure_wave` | **60.0%** | +3.431% | +3.281% |
| `atlas_fusion_v12` | 60.0% | +3.013% | +2.863% |
| `kalman_trend` | 60.0% | +2.307% | +2.157% |
| Supertrend/Kaufman | 60.0% | see full JSON | see full JSON |
| `multiscale_trend` / Omni / Markov | 57.5% | +2.850% / +2.080% / see JSON | see full JSON |
| `ultimate_trend` | 55.0% | +1.212% | +1.062% |
| `atlas_regime_compass` | 55.0% | +0.269% | +0.119% |
| `atlas_phoenix_fusion` | 55.0% | +0.937% | +0.787% |
| `atlas_meta_hedge` | 55.0% | +1.917% | +1.767% |
| `majority_vote_v8` | 50.0% | +0.548% | +0.398% |
| `atlas_online_logistic` | **30.0%** | −6.527% | −6.677% |
| `momentum_5bar` baseline | 55.0% | +2.472% | +2.322% |
| original `analog_median` | 45.0% | −0.787% | −0.937% |

Direct horizons:

| Method | 1 bar | 3 bars | 6 bars |
|---|---:|---:|---:|
| Ultimate | 55.0% | 55.0% | 55.0% |
| TSI | 60.0% | 52.5% | 47.5% |
| Pressure Wave | 60.0% | 60.0% | **62.5%** |
| Regime Compass | 60.0% | 55.0% | 60.0% |
| Phoenix | 60.0% | 55.0% | 52.5% |

#### Bundled SQLite pool — 260 attempts

| Method | Attempts | Weighted direction | Mean net/trade @10 bps | @25 bps |
|---|---:|---:|---:|---:|
| `consensus_3plus` (filtered subset) | 83 | 64.109% | +3.196% | +3.046% |
| **`atlas_pressure_wave` (full coverage)** | **260** | **63.077%** | **+3.188%** | **+3.038%** |
| `atlas_fusion_v12` | 260 | 62.692% | +2.712% | +2.562% |
| `ultimate_trend` | 260 | 62.692% | +1.567% | +1.417% |
| `markov_regime` | 260 | 61.538% | +2.490% | +2.340% |
| `kalman_trend` | 260 | 61.538% | +2.374% | +2.224% |
| `hull_trend` | 260 | 61.538% | +2.337% | +2.187% |
| `omni_direct_consensus` | 260 | 61.538% | +2.114% | +1.964% |
| `atlas_meta_hedge` | 260 | 60.385% | +2.400% | +2.250% |
| `multiscale_trend` | 260 | 60.385% | +2.366% | +2.216% |
| `atlas_regime_compass` | 260 | 59.615% | +1.559% | +1.409% |
| `tsi_momentum` | 260 | 59.231% | +1.405% | +1.255% |
| `atlas_phoenix_fusion` | 260 | 58.846% | +0.865% | +0.715% |
| `majority_vote_v8` | 260 | 58.462% | +1.196% | +1.046% |
| `momentum_5bar` | 260 | 57.692% | +1.332% | +1.182% |
| `adaptive_selector` | 260 | 57.692% | +0.682% | +0.532% |
| original `analog_median` | 260 | 51.154% | +2.828% | +2.678% |
| `aroon_trend` | 260 | 47.692% | −1.529% | −1.679% |
| `atlas_online_logistic` | 260 | 46.923% | −3.319% | −3.469% |
| `rvi_trend` | 260 | 45.000% | −4.520% | −4.670% |

Pressure Wave's pooled gain over v12 Atlas Fusion is only
**+0.385 percentage points**, equivalent to about one extra correct call in
260. That is an improvement on this exact pool, not proof that Pressure Wave
is universally superior.

#### What v13 improved—and what it did not

- AAPL retrospective full-coverage maximum: 67% (v12 Hull) → **68%**
  (v13 Ultimate), +1 point.
- AAPL vs original analog: Ultimate is +24 points (+54.5% relative).
- AAPL vs naïve momentum: Ultimate is +10 points (+17.2% relative).
- MSFT best full-coverage result stayed at **60%**; Pressure Wave joined the
  tie and had the highest listed mean net among the new methods.
- Full-coverage pooled leader: 62.692% → **63.077%**, +0.385 points.
- Meta Hedge was usable as a causal ensemble (61% AAPL, 55% MSFT, 60.385%
  pooled), but did not beat the best fixed methods.
- Online Logistic failed on MSFT (30%) and pooled (46.923%); it remains in
  the race as disclosed evidence that adaptive machine learning can chase a
  regime and lose.
- Aroon and RVI also pooled below 50%. Adding “every technique” is useful
  for falsification; it does not mean every technique deserves trading.
- **80% was not reached.** Claiming it from a subset, one horizon, or after
  looking at the answers would violate this project's methodology.

- **Tests:** 47/47. Signal engines: **37**.

### v14.0 — minute focus, 80% goal gate, external-account bot companion

#### What was added

1. **Seven minute engines (44 total):** rolling-VWAP reversion, EMA ribbon,
   RSI-2 snapback, UTC opening-range breakout, Bollinger squeeze release,
   volume-surge pressure and the invented **Atlas Minute Pulse**.
2. **Atlas Minute Pulse:** EMA ribbon 25%, Atlas Pressure Wave 25%, causal
   rolling-VWAP trend side 15%, ORB state 15%, volume surge 10% and squeeze
   release 10%, entropy-damped. Missing ingredients are renormalized.
3. **Minute hidden-future race:** horizons 1/3/5/15/30 bars and up to 5,000
   requested attempts per horizon, with coverage, Wilson 95% intervals and
   5/10/25-bps net means. RSI-2/ORB/squeeze/volume states can abstain; the
   full Pulse row and fixed |score| ≥ 0.45 selective row are printed apart.
4. **Explicit project goals:** `GOALS.md`, `GET /api/goals` and
   `sample-project-goals.json`. Accuracy status remains
   `active_target_not_reached`.
5. **Minute bot profile:** new paper bots default to Atlas Minute Pulse on
   1m with tighter allocation/risk, fee + simulated slippage, daily-entry,
   holding-time, cooldown, minimum-ATR, daily-loss and drawdown controls.
6. **External-account funding workflow:** user-reported USDT/BTC balances can
   be mirrored for accounting, and simulated entries/exits can create manual
   checklist tickets for the user's own licensed account. TradeAtlas still
   has no deposit address, credential field, custody, blockchain transfer or
   automatic order routing; live execution is hard-disabled.
7. **SQLite minute research:** stored 1m/5m/15m series also produce
   horizon-5 minute-method leaderboard rows.

#### What did **not** change in the real evidence

- No bundled real minute dataset was added, so v14 has **no real minute
  accuracy number** and cannot honestly move the real-evidence ladder.
- AAPL daily best remains **68.0%** over 100 attempts; MSFT monthly best
  remains **60.0%** over 40; pooled full-coverage best remains **63.077%**
  over 260.
- `sample-minute-forecast-synthetic.json` uses deterministic invented 1m
  bars. It verifies code paths and goal-gate arithmetic only; it is excluded
  from accuracy evidence.
- Minute OHLCV alone still omits bid/ask spread history, depth, queue
  position, latency and partial fills. A future high minute score must model
  those separately before anyone treats it as tradable.

#### Development rule from v14 onward

Do not tune against the final validation set. Import many real minute
series, race all fixed methods/horizons with costs, preserve failures, and
only promote candidates that survive later unseen symbols/days. The target
is at least 80%, but the label changes only when the gates in `GOALS.md`
are met.

- **Tests:** 49/49. Signal engines: **44**.

### v15.0 — failure memory: diagnose, avoid, remedy, remember

#### What was added

1. **A 21-cause diagnosis library** (`selfcorrect.CAUSES`): insufficient
   attempts, low coverage, cost-starved sample, baseline not beaten,
   cost-eaten edge, single-horizon overfit, walk-forward decay, regime
   dependence, deep drawdown, wide confidence interval, single symbol,
   selection bias, missing volume, short history, below-floor costs,
   abstention, no edge, negative expectancy and `remedy_failed_twice`.
2. **A three-stage self-correcting loop:** screen (method × horizon on
   completed bars) → apply lessons (each blocker's patch changes the next
   round's config) → validate (recent 30% slice + optional second symbol).
3. **Only implemented remedies are allowed:** cost-aware trade filtering
   (expected causal move ≥ N× round-trip cost), threshold relaxation for
   coverage, larger attempt budgets, neighbouring-horizon agreement,
   recent-slice judging, regime-stability gating and second-symbol gating.
4. **Lesson states:** `resolved` (fix worked, patch re-applied later),
   `recurred` (returned on a fair sample), `retired` (measured negative
   result), `escalated` (`remedy_failed_twice`).
5. **Starved samples cannot produce a verdict.** With too few attempts or
   coverage the diagnosis stops at sample-quality causes; it never prints an
   accuracy that four attempts happened to produce.
6. **SQLite schema v2 failure memory:** `self_correction_runs`,
   `research_trials`, `research_lessons`, keyed by a stable lesson id, with
   `GET /api/lessons`, `GET /api/failure-memory` and
   `POST /api/lessons/clear`.
7. **Carry-over avoidance:** a later run on the same symbol excludes
   candidates already proven dead and pre-applies resolved patches.
8. **UI card 5C · Failure Memory**, `FAILURE-MEMORY.md`, and
   `sample-self-correction.json`.

#### Results

- **Bundled real AAPL daily** (506 bars, 100 attempts, 10 bps, 7 methods ×
  horizons 1/3/5/10/20 = 35 candidates): round 1 retired **33** candidates
  because a naive baseline was at least as good, 8 had no directional edge, 6
  had negative expectancy, 21 breached the 20→25-point drawdown gate and 3
  lost their gross edge to costs. Round 2 removed one more for a recurring
  drawdown. Round 4 produced **one survivor** (`multiscale_trend` @3 bars)
  labelled `sample_local_only_single_symbol` — **not validated**, because
  only one symbol was supplied. Verdict:
  `survived_the_recent_slice_but_a_second_symbol_is_required`.
- **Synthetic software check** (two invented 1m series, seeds 15/27, 6
  methods × horizons 3/5/15): 4 rounds, **38 lessons, 3 resolved remedies,
  16 retirements**; verdict `validated_on_supplied_data_still_needs_fresh_unseen_validation`
  *for the supplied synthetic data only*, with `goal_established=false`.
- **Deterministic reproducibility:** the loop is a pure function of the bars
  and config; two identical runs produce identical lessons and tallies.
- **No accuracy headline is created by v15.** `goal_80_established` is false
  in every path, including when a caller lowers `target_accuracy_pct`.

#### Lesson

Teaching software to *diagnose its own failures* changed what the project
reports far more than adding another indicator did: the most common real
outcome is now "a naive baseline matched this method, so it is retired and
remembered", which is the honest result the 80% target always needed.

- **Tests:** 65/65. Signal engines: **44** (unchanged); failure causes: **21**.


### v16.0 — autonomous collector, counted holdout and the honest 80% tracker

#### What was added

1. **Guarded collector (`pipeline.py`).** Fetches completed bars from a fixed
   allowlist (`api.binance.com`, `data-api.binance.vision`, `api.kraken.com`).
   Arbitrary hosts, other schemes and unapproved private addresses are refused;
   there are no keys, logins or credentials, and the still-forming candle is
   dropped. Usable from the server CLI (`--collect`, `--auto`) or the browser
   (card 6), which matters when the server is sandboxed.
2. **Incremental, duplicate-free storage.** Series are keyed
   `VENUE.SYMBOL.interval`; the newest page is fetched first and only bars newer
   than the newest stored bar are kept, then older history is backfilled to the
   target. `(symbol,timeframe,t)` makes duplicates impossible, and every run
   writes a `collection_runs` provenance row (venue, counts, first/last bar UTC,
   requests, endpoints, errors).
3. **Counted holdout.** The newest 20% of every series is reserved and never
   used for tuning; every read goes to `holdout_runs` and is reported.
4. **Nine-gate goal tracker.** `GET /api/goal-progress` pools hidden-future
   attempts across stored series and checks attempts, pooled accuracy, Wilson
   lower bound, net after 10 bps, coverage, symbols, distinct days, a recorded
   holdout and fresh external validation. Each gate reports its measured value
   and the report stores a history row.
5. **Unattended loop.** `--auto --cycles N --sleep S` collects, grades and stores
   a goal report per cycle, so multi-week sample growth is one background
   command.
6. **UI card 6** — Auto-Collect & Goal Progress: collect (server or browser),
   grade everything stored, run the recorded holdout, and read a progress bar
   with a pass/fail gate table.

#### Results

- **Synthetic gate report** (`sample-goal-progress.json`; three deterministic
  1m series): best pooled candidate **60.556%**, **2/9 gates**,
  `goal_established=false`, `below_target_on_local_data`. A software check of
  the arithmetic, never market evidence.
- **Offline collector proof:** against a local fake venue, the collector
  backfilled 600 bars in one run, added **0** on a repeat run, appended exactly
  the **100** genuinely new bars on a later run, and left storage untouched when
  the venue was unreachable (the failure was recorded as an error).
- **No accuracy claim is added.** Automation raises sample size and honesty; it
  cannot raise the measured rate.

#### Lesson

The temptation with "make it fetch data and store it" is to imply the stored
volume itself is progress. It is not: a bigger sample mostly makes the honest
number *worse*, because it shrinks the confidence interval around a mediocre
rate. The gates and the counted holdout are what make the larger sample useful
rather than flattering.

- **Tests:** 77/77. Signal engines: **44**; failure causes: **21**; goal gates: **9**.

## Retrospective “best full-coverage label” on AAPL

This sequence is included because users naturally ask “how much did it
improve?” It must be read with the selection-bias warning above: each later
version raced more contestants, so the maximum is expected to creep upward by
chance even without durable predictive power.

| Version | Retrospective AAPL full-coverage best/new headline | vs v4 analog (44%) | vs momentum (58%) |
|---|---|---:|---:|
| v4 | Analog 44% | — | −14 points |
| v6 | Majority 55% | +11 points / +25.0% relative | −3 points |
| v7 | Combined 57% | +13 points / +29.5% | −1 point |
| v10 | Multiscale 60% | +16 points / +36.4% | +2 points / +3.4% |
| v11 | Omni 64% | +20 points / +45.5% | +6 points / +10.3% |
| v12 | Hull 67% | +23 points / +52.3% | +9 points / +15.5% |
| v13 | Ultimate 68% | +24 points / +54.5% | +10 points / +17.2% |

v5, v8 and v9 are deliberately absent from this “best” ladder because their
contribution was stronger measurement/falsification and their new full-test
headlines did not beat the momentum baseline. Their exact results remain in
the detailed sections above.

## Files that reproduce the current numbers

- `sample-forecast-real-aapl.json` — full AAPL race, horizons and costs.
- `sample-forecast-real-msft-monthly.json` — full MSFT race.
- `sample-database-research.json` — bundled SQLite seed and pooled leaderboard.
- `sample-lab-validation.json` — synthetic 44-engine/timeframe software check
  (not real-market evidence).
- `sample-minute-forecast-synthetic.json` — synthetic 1m race output for
  software/goal-gate validation only.
- `sample-project-goals.json` and `GOALS.md` — goals and evidence gates.
- `test_tradeatlas.py` — pins key real-sample values and no-lookahead rules.
- `version-history.json` — machine-readable companion to this file.

## Safety and product-history note

Across all versions, TradeAtlas remains research/paper software. “Connected
to real markets” means browser-direct public/custom **market-data** adapters
for stocks, crypto, currencies/forex, commodities, ETFs/funds, indices and
custom OHLCV. It has never routed a real broker/exchange order. In v14 the
bot can mirror a user-reported external balance and print manual checklist
tickets, but real USDT/BTC remains only in the user's own licensed account.
The bot and e-wallet are simulations; halal screening is an inspectable
evidence/rule workflow, not a fatwa or certification.

### v17.0 — Evolution Revolution (طوره كثييير)

- **Idea:** كل اختبار يفشل → يشخص السبب بدقة (35 سبباً) → يتجنبه في الاختبار اللي بعده → يلاقيلو حل ويتحقق منه. Self-healing loop حرفياً.
- **35-cause library:** 14 سبباً جديداً (autocorrelation, volatility regime, liquidity illusion, overparam, multiple testing, non-stationary, microstructure noise, asymmetric payoff, tail risk, correlation breakdown, concept drift, horizon mismatch, threshold overfit, sample contamination) مع patch لكل واحد.
- **Evolution Tracker:** `evolution.py` يحسب resolved_rate, avoidance_efficiency, failure_cluster, prediction (92% confidence), remedy_effectiveness. `pipeline.py` يضيف health_check + adaptive + retry.
- **Deep Diagnostics:** `diagnostics.py` ثنائي اللغة (عربي/إنجليزي) مع explain_failure, diagnose_batch, remedy_verification.
- **Advanced Stats:** 11 دالة إحصائية جديدة في `marketlab.py` (bootstrap, permutation, Bonferroni/FDR, Deflated Sharpe, tail, autocorr, vol regime, liquidity, PBO).
- **SQLite v4:** 4 جداول جديدة (evolution_generations, failure_clusters, remedy_verifications, diagnostic_reports) + stats evolution.
- **API:** 10 endpoints جديدة (evolution, diagnostics, health, advanced-stats, predict-failure, remedy-verify, bootstrap, permutation, evolution/record, diagnostics/explain).
- **Docs:** README v17, GOALS v17 (goal 8), EVOLUTION.md, DIAGNOSTICS.md, AUTOMATION v17, FAILURE-MEMORY v17.
- **Samples:** `sample-evolution.json`, `sample-diagnostics.json`, `sample-advanced-stats.json` + 143 tests.
- **Bundled evidence:** AAPL 68% و MSFT 60% لم يتغيرا — v17 يحسن التشخيص، لا يخترع حافة.
- **Tests:** **143/143**. Failure causes: **35**; goal gates: **9**; signal engines: **44**; stdlib only.

#### Lesson

الفرق بين "77 اختباراً يتحققون من أن الدقة ليست 80%" و "143 اختباراً كل واحد يفشل → يشخص → يتجنب → يحل" هو الفرق بين مقياس حرارة وطبيب. v16 كان يقيس المسافة إلى 80%؛ v17 يبني طبيباً يتذكر كل مريض مات ولماذا، ويتأكد ألا يموت التالي لنفس السبب. التطور لا يصنع حافة في السوق، لكنه يمنعنا من الكذب على أنفسنا 143 مرة مختلفة.

