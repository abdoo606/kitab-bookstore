# TradeAtlas — Genius Idea #14 (v15.0)

An **educational/research atlas** of the world's best-known trading strategies
and market-analysis methods, plus a bring-your-own-data **Market Lab**.
**v14 is minute-first:** its default research/bot path is the invented
**Atlas Minute Pulse** on real completed **1m** bars. **v15 adds a failure
memory:** every failed candidate is diagnosed, given an avoid-rule and an
implemented remedy, re-tested with that remedy, and either fixed (`resolved`),
retired with its reason (`retired`) or remembered so later runs skip it.
Python standard library only; zero subscriptions.

## ⚠️ Read this first

TradeAtlas is **educational/research software only. It is NOT financial advice.**

- Market Lab labels such as **LONG / buy-condition** and **SHORT / sell-condition**
  mean only that a mechanical indicator rule fired on completed bars. They are
  **not recommendations**.
- TradeAtlas bundles **no licensed live market data** and does not bypass paid,
  key-gated, login-gated, or CORS-protected feeds. Real-market tracking requires
  OHLCV data or a feed endpoint that you lawfully supply, or a public endpoint
  your own browser can lawfully reach.
- **Never send money or cryptocurrency to TradeAtlas.** Its wallet and bot
  are paper simulations only: no deposit address, custody, real conversion,
  withdrawal, leverage, broker account or order execution. Real USDT/BTC can
  only stay in the user's own licensed exchange/broker account; v14 may
  mirror a balance the user reports and generate manual checklist tickets,
  but it cannot access or verify that account.
- **80% accuracy is a project GOAL, not a reached result.** See `GOALS.md`
  and `GET /api/goals`. v14 adds the minute-data race and evidence gates
  needed to pursue it honestly; v15 adds the failure loop that refuses to
  repeat a measured mistake; neither declares 80% achieved.
- The **halal asset screen is not a fatwa or certification**. It only applies
  chosen thresholds/evidence rules to information you type in and stores the
  result with its source/expiry. Missing or expired evidence is
  `needs_review`, and the bot cannot open even a paper position unless the
  result is exactly `pass`.
- TradeAtlas is **not a bank, exchange, broker, money transmitter or crypto
  custodian**. It cannot accept deposits, convert real currency/crypto,
  process withdrawals, or place real-money orders. The full bot below is a
  private local **paper** platform; real market connections are data-only.
- It makes **no profit promises**. Most short-term traders lose money, and no
  strategy or backtest here changes that.
- Historical “accuracy” is not expected future accuracy. Review expectancy,
  costs, drawdown, liquidity, sample size and out-of-sample behavior together.
- Study, paper-trade, risk only money you can afford to lose, and consult a
  licensed financial professional for personal decisions.

## What is inside

### Atlas

- **16 strategies** across trend, mean-reversion, momentum, volatility,
  price-action, intraday, market-neutral, macro and investing families — each
  with textbook rules (education), why people like it, **how it fails**, and a
  risk note.
- **10 analysis methods** with tools and traps.
- **8 candlestick patterns illustrated** as inline SVG (invented example
  prices, shape teaching only).
- **3 risk calculators**: position size, risk:reward, expectancy in R.
- **8 risk rules + 12-term glossary**.

### Market Lab (v2.0, expanded in v3.0)

Bring real OHLCV bars and TradeAtlas will:

1. Validate and normalize CSV/JSON bars (timestamps may be Unix seconds,
   milliseconds, or ISO-8601).
2. Detect the base interval and honestly resample to every supported coarser
   timeframe: **1m, 5m, 15m, 1h, 4h, 1d, 1w**. Finer timeframes are reported as
   unavailable instead of being fabricated.
3. Compute SMA/EMA, RSI, MACD, Bollinger Bands, ATR, Stochastic, ADX, the
   v10 cycle/flow block (Aroon, Vortex, CMO, Fisher, RVI, Schaff, KST,
   Coppock, CMF/MFI, Force Index, rolling VWAP, Ulcer, SuperSmoother,
   permutation entropy, Signed Path Pressure and Entropy-Weighted Trend),
   and in v11 CCI, Williams %R, TSI, TRIX, Ultimate Oscillator, Parabolic
   SAR, Ichimoku, OBV slope, log-regression trend and a Kalman-style local
   trend filter; v12 adds Hull MA, Supertrend, Kaufman AMA, Haar wavelet
   trend and Donchian state. v13 also exposes bounded Aroon/TSI/TRIX/CMO/
   Ultimate/RVI/regression/Donchian/OBV/Coppock direct scores and three
   invented TradeAtlas scores: **Atlas Pressure Wave**, **Atlas Regime
   Compass** and **Atlas Phoenix Fusion**. v14 adds rolling VWAP(60),
   EMA-ribbon, RSI-2, UTC opening-range, Bollinger-squeeze, relative-volume
   and **Atlas Minute Pulse** state for minute bars.
4. Run one of **44** quantified engines: the classic EMA/MACD/breakout/RSI/
   Bollinger/pullback/consensus/Stochastic/ADX set, five v10 cycle/flow
   engines, six v11 engines, four v12 engines, thirteen v13 engines, and
   seven v14 minute engines (rolling-VWAP reversion, EMA ribbon, RSI-2
   snapback, UTC opening-range breakout, squeeze release, volume surge and
   **Atlas Minute Pulse**).
5. Historically test the **most recent 100 completed signals** by default:
   - signal known only after its bar closes;
   - entry at the **next bar open**;
   - exit after a configurable bar horizon;
   - round-trip cost/slippage deducted;
   - overlapping test trades blocked;
   - accuracy, win/loss/flat, average and median return, expectancy,
     profit factor, compounded test equity, maximum drawdown, best/worst and
     long/short splits reported — **plus equity-curve points (new in v3)**.
6. Optionally connect to real market data **from the user's browser**:
   Binance public spot klines, Kraken public OHLC, Stooq daily CSV, or a
   custom CORS-enabled JSON/CSV history URL. Binance/Kraken adapters drop the
   still-forming final candle. The TradeAtlas server never fetches arbitrary
   URLs, receives feed credentials, holds an exchange account or routes orders.

**New in v3.0:**

- **All-engine tournament per timeframe** (9 in v3; 14 in v10; 20 in v11; 24 in v12; 37 in v13; **44 in v14**) — every
  engine is tested on the same bars (same 100-signal/cost settings) and
  ranked by historical expectancy.
  The #1 row is the best fit to that sample and therefore the most over-fit
  row; the UI and JSON say so next to the table.
- **70/30 walk-forward split** — the same tested trades are split
  chronologically (earlier vs later) with a robustness verdict. In the
  synthetic sample, the 1w consensus headline (+1.12% expectancy) is flagged
  `degraded_later` because its later slice is negative — exactly the kind of
  fragility a single accuracy number hides.
- **Multi-symbol watchlist heatmap** (`POST /api/lab/watchlist`, UI card 4):
  upload one file per symbol — crypto, stocks, FX, futures, indices — and get
  the latest mechanical condition on every honest timeframe. Symbols are
  never ranked for you.
- **Market presets**: per-asset-class cost/data-trap homework so the cost
  field starts from a researched range instead of a fantasy number.

The synthetic validation button uses deterministic invented prices solely to
prove that the timeframe pipelines can produce and score test cases. It is
**not** evidence about any real market. `sample-lab-validation.json` reports
the exact counts generated for the selected engine; tournament winners can
differ per timeframe, which is itself the lesson: the "best" engine is
sample-dependent.

**New in v15.0 — a failure memory that turns every failed test into a rule
for the next one (nothing in the 80% claim changes):**

- **An explicit cause library (21 named failure modes).** A failed candidate
  is never just "bad": it is diagnosed as too few attempts, coverage too low,
  a naive baseline winning, a gross edge eaten by costs, a single-horizon
  cherry, walk-forward decay, regime dependence, deep drawdown, selection
  bias, missing volume, a remedy that starved its own sample, and so on.
  Every cause carries a meaning, an **avoid-rule** for the next test and the
  remedy that is actually implemented.
- **A three-stage self-correcting loop** (`POST /api/lab/self-correct`):
  1. *screen* every method × horizon on completed bars only;
  2. *apply lessons* — the next round re-tests only what can still be saved,
     with that remedy in force (cost-aware trade filter, relaxed abstention
     floor, neighbouring-horizon agreement, recent-slice judging, regime
     stability, larger attempt budget);
  3. *validate* survivors on the recent 30% slice and, when supplied, a
     second symbol.
  A cause that disappears is marked **resolved** and its fix is re-applied in
  later runs. A cause that returns on a fair sample retires the candidate as
  `remedy_failed_twice`.
- **Starved samples cannot produce a verdict.** If a remedy leaves four
  attempts, the diagnosis stops at the sample-quality causes instead of
  printing "75% accuracy". That single rule removes the most common way a
  backtest lies to its author.
- **Durable memory in SQLite** (schema v2): `self_correction_runs`,
  `research_trials` and `research_lessons`, keyed by a stable lesson id.
  `GET /api/lessons` returns the ledger (observed / resolved / recurred /
  retired / escalated) with the cause tally; `POST /api/lessons/clear` forgets
  it, and the code says why you should almost never need to.
- **Carry-over avoidance:** a later run on the same symbol starts by
  excluding candidates its stored lessons already proved dead, and by
  pre-applying the patches of lessons that were resolved. The loop literally
  avoids what failed before.
- **Honest labels only:** `validated_on_supplied_data_still_needs_fresh_unseen_validation`,
  `survived_the_recent_slice_but_a_second_symbol_is_required`,
  `no_candidate_survived_validation`, `no_candidate_survived_the_failure_gates`,
  `all_candidates_excluded_by_prior_lessons`. `goal_80_established` stays
  **false** in every path, including when the target is lowered by request.
- **Bundled real AAPL daily (506 bars, 100 attempts, 10 bps, 35 candidates):**
  33 candidates retired because a naive baseline matched or beat them, 8 had
  no directional edge, 6 had negative expectancy, 21 breached the drawdown
  limit and 3 lost their gross edge to costs. One survivor reached validation
  and is labelled **single-symbol only** — not validated, because only one
  series was supplied. That is the product working as intended on real data.
- **Synthetic software check** (`python3 tradeatlas.py --demo`): two invented
  1m series produce 38 lessons, **3 resolved remedies** and 16 retirements
  across four rounds. `sample-self-correction.json`; never market evidence.
- **UI:** card **5C · Failure Memory** runs the loop on the current/pasted
  bars (optional second-symbol file), shows each round's candidates, causes,
  applied remedies, retirements and resolved fixes, and loads/clears the
  stored ledger.
- **Docs:** `FAILURE-MEMORY.md` explains the taxonomy, the remedy table, the
  resolution/retirement rules and the worked AAPL example.
- Tests: **65/65**, including causal score arrays, every diagnosis family,
  severity gating, patch application/relaxation, the resolution path,
  retirement reasons, carry-over avoidance, pre-applied resolved patches,
  single-symbol honesty, two-symbol validation, determinism, SQLite
  persistence/dedupe/clear and the HTTP endpoints.

**New in v14.0 — minute-first bot workflow, explicit 80% goal gate,
external-account USDT/BTC mirror and manual execution tickets (still no
custody or automatic live orders):**

- **Seven causal minute engines (44 total):**
  - `minute_vwap_reversion`: distance from a rolling 60-bar VWAP, normalized
    by trailing one-bar volatility; score fades the stretch.
  - `minute_ema_ribbon`: EMA 5/13/34 ordering plus volatility-normalized gaps.
  - `minute_rsi2_snapback`: hard +1/-1 after a complete RSI-2 oversold or
    overbought turn that agrees with the causal price side of SMA-50; zero
    means abstain.
  - `minute_orb_breakout`: first fully observed 15 one-minute bars of each
    UTC day form the range (only exact 60-second source bars); a break becomes
    a hard state and the opposite break flips it later.
  - `minute_squeeze_breakout`: Bollinger bandwidth in its trailing lowest
    quintile arms the setup; a band break releases a bounded score.
  - `minute_volume_surge`: candle pressure multiplied by a bounded real
    relative-volume surge; zero-volume series abstain rather than inventing
    flow.
  - **Atlas Minute Pulse (invented):** EMA ribbon 25%, Pressure Wave 25%,
    causal rolling-VWAP trend side 15%, ORB state 15%, volume surge 10% and
    squeeze release 10%, reduced 15% by permutation entropy. Missing
    constituents are renormalized; VWAP reversion and RSI-2 remain separate
    opposed hypotheses instead of being silently averaged into the trend side.
- **Minute Accuracy Race:** `POST /api/lab/minute-forecast` and UI card 5B
  hide future bars at horizons **1/3/5/15/30**, accept up to **5,000**
  attempts per horizon, and report attempts, hits, coverage, Wilson 95%
  intervals and mean net after 5/10/25 bps. A selective Pulse row uses a
  fixed |score| ≥ 0.45 threshold beside the full row. The 80% gate requires
  at least 1,000 attempts, positive 10-bps expectancy, at least 20% coverage
  for selective rows, and external multi-symbol/day validation; the API
  always keeps `goal_established=false` for a single supplied series.
- **Goals are explicit:** `GOALS.md`, `GET /api/goals` and
  `sample-project-goals.json` record minute focus, the unfinished 80%
  target, the manual-companion bot boundary, the own-account USDT/BTC rule
  and the halal gate. **80% remains unreached.** The prior real evidence is
  unchanged: 68% on one 100-attempt AAPL daily test and 63.077% pooled over
  260 bundled daily/monthly attempts. v14 adds no fake real-minute sample;
  `sample-minute-forecast-synthetic.json` is a software check only.
- **Integrated minute bot defaults:** new bots use Atlas Minute Pulse, 1m,
  5% allocation cap, 0.5% risk cap, 10 bps fee + 5 bps simulated slippage,
  at most 20 entries/UTC day, 30-bar maximum holding time, 3-bar cooldown,
  a 0.02% minimum-ATR filter, 2% daily-loss and 6% drawdown entry halts.
  Protective ATR stop/target/trailing exits and halal `pass` gating remain.
  Paper buys/exits generate a manual checklist ticket for the user's own
  licensed account; `real_order_sent` stays false and live execution is
  hard-disabled.
- **USDT/BTC workflow without custody:** Binance BTC/USDT and Kraken XBT/USD
  presets default to completed 1m market data. The wallet can record a
  user-reported external USDT/BTC/USDC/USD/ETH/SOL balance held in the
  user's own account. That mirror is unverified and excluded from paper
  equity. There is still no TradeAtlas deposit address, API-key field,
  blockchain transfer, conversion, withdrawal or automatic order.
- **SQLite minute research:** pooled research can request up to 1,000
  attempts and stores v14 minute-method rows for 1m/5m/15m series at horizon
  5, while keeping the old daily/monthly evidence and leaderboards separate.
- Tests: **49/49**, including future-mutation checks for every minute score,
  the synthetic goal-gate race, external-mirror non-inclusion in paper
  equity, slippage/manual tickets, maximum-holding/cooldown exits and HTTP
  goals/minute-race/bot flows.
- **No real-minute accuracy claim is made in v14.** To move toward the goal,
  import many lawful real 1m series/days, race them with full costs and
  validate survivors on later unseen symbols/dates.

**New in v13.0 — old + modern direct methods, invented Atlas scores,
causal online learners, one-click market presets and a demo e-wallet
(still paper-only):**

- **Thirteen more signal engines (37 total):** Aroon, TSI, TRIX, CMO,
  Ultimate Oscillator reversal, RVI, 20/60-bar log-regression fusion,
  Donchian state, OBV flow and Coppock join every honest timeframe
  tournament. Three are new TradeAtlas inventions:
  - **Atlas Pressure Wave:** a 15-bar exponentially weighted measure of
    candle close/body pressure, scaled by ATR range and relative *real*
    volume, fused with 3/10-bar volatility-normalized momentum. On
    close-only bars it honestly collapses to close-path pressure instead of
    inventing candle anatomy or volume.
  - **Atlas Regime Compass:** ADX and permutation entropy smoothly decide
    whether to trust Hull/multiscale trend evidence or Bollinger/RSI
    range-reversion evidence.
  - **Atlas Phoenix Fusion:** trend filters, momentum oscillators, price
    structure and OHLCV flow proxies are averaged *inside families first*,
    then fused 25/25/20/20 with the Compass at 10%, so five correlated
    cousins cannot pretend to be five independent witnesses.
- **Forecast race expansion:** the same hidden-future race now includes
  direct bounded signs for Aroon/TSI/TRIX/CMO/Ultimate/RVI/regression/
  Donchian/OBV/Coppock, the three invented scores, `majority_vote_v8`, and
  two genuinely causal online learners. **Atlas Meta Hedge** exponentially
  reweights 16 diversified contestants only after their full outcome window
  has revealed. **Atlas Online Logistic** performs one L2-regularized SGD
  update per revealed label over 15 bounded origin-time features. Neither
  learner can peek at an unfinished attempt; both can still overfit one era.
- **Real AAPL daily (100 attempts, horizon 5):** Ultimate **68.0%** is the
  new full-coverage sample best (Hull 67.0%, TSI 65.0%, Pressure Wave
  64.0%, Atlas Fusion v12 64.0%, Omni 64.0%, Compass/Phoenix 62.0%,
  Meta Hedge/Online Logistic/majority-v8 61.0%). Ultimate nets
  **+0.893%/trade at 10 bps** and +0.743% at 25 bps; TSI nets +1.071%.
  But Ultimate by horizon 1/3/5/10/20 is **55/62/68/59/58%**, and Pressure
  Wave is **54/57/64/57/51%** — one strong 5-bar cell is still not a law.
- **Real MSFT monthly (40 attempts, horizon 3):** Pressure Wave ties the
  best full-test accuracy at **60.0%** and nets **+3.431%/trade at 10 bps**
  (+3.281% at 25 bps), while Ultimate/Compass/Phoenix/Meta Hedge are
  55.0%, majority-v8 is 50.0%, and Online Logistic fails badly at **30.0%**
  (−6.527%/trade at 10 bps). Modern learning is therefore documented as a
  contestant that can lose, not marketed as magic.
- **Pooled SQLite research (260 attempts):** invented Pressure Wave is the
  best *full-coverage* pooled method at **63.077%** (+3.188%/trade at
  10 bps), narrowly above Atlas Fusion v12 and Ultimate at 62.692%. The
  coverage-limited `consensus_3plus` subset remains higher-looking at
  64.109% on only 83 attempts, so it is not crowned. Meta Hedge pools
  60.385%; Online Logistic only 46.923%. **No 80% universal accuracy was
  reached, proven or promised.** Full version-by-version evidence is in
  `VERSION-HISTORY.md` and machine-readable form in `version-history.json`.
- **Easier for a beginner:** a “Start here” 4-step card links the whole
  workflow; one-click presets fill Binance/Kraken crypto, Stooq US/UK/German
  stocks, a US ETF, the S&P 500 index and EURUSD; Forecast Lab can now run
  directly on the currently analyzed/pasted bars; bot controls explicitly
  say **Start / Resume / Pause / STOP**. Public connections remain
  browser-direct market-data adapters only, never order routing.
- **Demo e-wallet (simulation only):** hold imaginary USDT/USDC/BTC/ETH/SOL
  balances, convert an imaginary balance to PAPER_USD at a rate you type,
  simulate a withdrawal by removing imaginary units, and transfer PAPER_USD
  internally between the standalone demo wallet and the halal paper bot.
  There is still **no deposit address and no real crypto acceptance,
  conversion, custody, withdrawal, bank transfer or live execution**. A real
  deposit/conversion/trade must happen in the user's own licensed
  exchange/broker account outside TradeAtlas.
- Tests: **47/47**, including future-mutation checks for Pressure/Compass/
  Phoenix, all 37 engines, v13 race/meta-learner structure, pinned real
  AAPL/MSFT attempts and costs, demo-balance conversion/withdrawal/internal
  bot transfers, HTTP Start/Pause/Resume/STOP, and the prior SQLite/halal/
  private-token gates.

**New in v12.0 — SQLite market memory, all-asset halal evidence gate,
Hull/Kaufman/Haar/Markov race (still no real-money execution):**

- **Private SQLite database (`platformdb.py`, UI card 8):** tables for
  instruments, OHLCV bars, data imports, latest halal profiles, full screen
  history, research runs, method scores and bot events. It seeds the bundled
  real samples (**1,066 bars**: AAPL daily plus five monthly series), then
  grows whenever the browser imports lawful Stooq/custom/public-feed bars or
  files. It does not contain every licensed global market history; no honest
  zero-subscription package can. `TRADEATLAS_DB` chooses the file and
  `TRADEATLAS_ACCESS_TOKEN` can require an `X-TradeAtlas-Token` header on
  paper/bot/halal/database APIs for a private local deployment.
- **Pooled database research:** one run applies the full hidden-future race
  to every stored series and saves attempts/accuracy/10-25 bps means. On the
  bundled seed, five series are evaluable (GOOG monthly has only 68 bars).
  `atlas_fusion_v12` pools **62.692% over 260 attempts** (+2.712%/trade at
  10 bps); the coverage-limited `consensus_3plus` subset is 64.109% on only
  83 attempts and therefore is not treated as the universal winner. These
  series overlap in era and are survivor-biased, so pooled does not mean
  independent or guaranteed.
- **New methods/engines:** Hull MA trend, Supertrend(10,3), Kaufman AMA,
  Haar wavelet 4/8/16/32/64-bar trend, Donchian state, a causal Markov
  trend/volatility/RSI regime vote learned only from fully revealed prior
  attempts, `atlas_fusion_v12` (Hull+Kalman+Markov+Omni+multiscale) and
  `majority_vote_v7` — **24 signal engines** in every honest tournament.
- **Real AAPL daily (100 attempts, horizon 5):** Hull **67.0%**, Atlas
  Fusion 64.0%, Markov 63.0%, Kaufman 62.0%, Haar 56.0%, Supertrend 55.0%.
  Hull nets **+0.786%/trade at 10 bps** and +0.636% at 25 bps. But at
  horizons 1/3/5/10/20 Hull is **51/62/67/61/56%**, so the 67% is not a
  universal law. **Real MSFT monthly (40 attempts, horizon 3):** Supertrend
  and Kaufman 60.0%, Atlas Fusion 60.0%, Hull only 52.5%, Haar 42.5%.
  Nothing reaches or honestly supports an **80%** general direction rate.
- **How the bot “knows halal”:** it knows only the stored evidence and rules.
  Stocks use activity + debt/cash-securities/receivables/non-compliant
  income ratios. Crypto, currency, commodity, ETF and fund profiles require
  explicit user-reviewed spot/settlement evidence and explicit false flags
  for leverage, interest/swap and shorting (plus asset-specific fields).
  Profiles carry source and optional expiry; expired/missing evidence falls
  back to `needs_review`. This is a rule database, **not a fatwa**, and the
  bot still opens only long spot **paper** positions after `pass`.
- **Full paper platform:** $10,000 default imaginary balance, multi-asset
  registry, browser auto-cycles, ATR sizing, stop/target/trailing exits,
  daily/drawdown halts, Start/Pause/STOP, local bot-state persistence and
  database decision logging. Binance/Kraken/Stooq/custom connections remain
  browser-direct **market data only**. No real deposits, crypto conversion,
  withdrawals, custody, leverage, broker credentials or live orders exist.
- Tests: **44/44**, including v12 future-mutation checks, pinned real-sample
  results, SQLite seed (1,066 bars), pooled research storage, generic
  crypto halal pass/review gates, a paper bot buy, and private-token HTTP
  rejection/acceptance.

**New in v11.0 — Kalman/Omni direct race, rank fusion, and a halal-only
paper bot:**

- **New direct contestants:** a causal alpha-beta/Kalman-style local trend
  of log price; `omni_direct_consensus`, a fixed weighted fusion of
  multiscale trend, Kalman slope, horizon-matched trend, Parabolic SAR and
  a CCI/Williams/TSI/TRIX/Ultimate/CMO/Fisher/Schaff oscillator basket;
  rank-fusion neighbours that average distance ranks across all five analog
  families; and `majority_vote_v6`. Six matching signal engines join the
  tournament (20 total).
- **Real AAPL daily, exactly 100 hidden-future attempts (horizon 5):**
  Kalman **62.0%**, Omni **64.0%**, adaptive selector **61.0%**, multiscale
  60.0%, momentum 58.0%, rank fusion only 47.0%/48.0%. Omni is the full-test
  best label on this sample. After costs, Kalman nets **+0.846%/trade at
  10 bps** and +0.696% at 25 bps; Omni nets **+0.641% / +0.491%**.
- **Real MSFT monthly, 40 attempts (horizon 3):** Kalman **60.0%**, Omni
  57.5%, multiscale 57.5%, momentum 55.0%; rank fusion gets 28 attempts at
  46.4%/39.3%. Kalman nets **+2.307%/trade at 10 bps** (+2.157% at 25 bps),
  below multiscale's +2.850% despite the higher hit rate — direction and
  magnitude still tell different stories.
- **Plain truth about “+30%”:** Kalman versus the weak original analog is
  44% → 62% on AAPL (**+40.9% relative**) and 45% → 60% on MSFT (**+33.3%
  relative**). Against the stronger momentum baseline it is only **+6.9%**
  and **+9.1% relative**. At AAPL horizons 1/3/5/10/20, Kalman scores
  55/57/62/53/49% and Omni 54/55/64/57/52%, while always-up reaches 67–68%
  at long horizons. So v11 improves these two primary tests, but it does not
  prove a universal +30% forecasting power or a durable edge.
- **Halal-stock paper bot (UI card 7):** register each stock with business
  activity flags plus debt, interest-bearing cash/securities, receivables
  and non-compliant-income ratios from the company's latest filing. Two
  example presets are supplied (strict/balanced), but standards differ and
  this is **not a fatwa/certification**. Only `asset_type=stock` plus screen
  status `pass` can enter; crypto, FX, missing data, `needs_review` and
  `fail` are blocked. The bot is spot long-only on paper, sizes from ATR
  risk, obeys allocation/max-position caps, sets stop/target/trailing exits,
  halts new entries after daily-loss/drawdown limits, ignores duplicate
  bars, and has **Start / Pause / STOP / Reset risk** controls.
- **Automation boundary:** the browser fetches Stooq/public/custom market
  data and can call bot cycles automatically while the tab stays open; bot
  state is saved locally in `tradeatlas-bot-state.json`. The server holds no
  broker/exchange credentials, accepts no deposits, performs no real crypto
  conversion, and sends no real orders.
- **How to use it, in plain steps:** (1) reset the bot; (2) type one real
  company's latest filing figures and register it; only continue if the
  result says `pass`; (3) fetch/upload that stock's bars and analyze them;
  (4) choose `omni_consensus`, set the same symbol in the bot card, press
  **Start bot**; (5) run one cycle or Auto paper cycles; (6) press **STOP**
  to hard-stop entries. Repeat screening after new financial statements.
- Tests: **40/40**, including Kalman/rank-fusion future-mutation checks,
  pinned v11 AAPL/MSFT results, halal pass/review/fail gates, a simulated
  bot buy blocked for crypto, duplicate-bar protection, a crash-bar stop
  exit, and the bot HTTP endpoints.

**New in v10.0 — cycle/flow science, direct multiscale trend, public-data
adapters and a paper wallet (still no real-money path):**

- **Fifth analog coordinate system:** 18 origin-time cycle/flow features —
  Aroon oscillator, Vortex balance, CMO, Fisher, RVI, Schaff, volatility-
  normalized KST/Coppock, CMF, MFI, ATR/volume-normalized Force Index,
  rolling-VWAP distance, Ulcer, SuperSmoother slope, permutation-entropy
  score, overnight/intraday volatility balance, plus invented **Signed Path
  Pressure** (volume-adjusted close-location pressure accumulated along the
  path) and **Entropy-Weighted Trend**. It votes as
  `cycle_flow_analog_median` / `cycle_flow_analog_weighted`, exposes
  `cycle_analog_now`, and joins `majority_vote_v5` under the same strict
  candidate rule `j + horizon <= origin`.
- **`multiscale_trend`:** a direct, non-neighbour contestant averaging
  `tanh(return / (10-bar volatility × √window))` over 3/5/10/20/60/120-bar
  windows. On bundled **real AAPL daily** (exactly 100 hidden-future
  attempts, horizon 5) it scores **60.0%**, versus original analog **44.0%**,
  always-up **56.0%** and naive momentum **58.0%**. It is the first
  full-coverage contestant here to outscore momentum, and it nets
  **+0.290%/trade after 10 bps** and **+0.140% after 25 bps** (momentum:
  +0.166% / +0.016%). `cycle_flow_analog_median` scores 52.0%, weighted
  47.0%, `majority_vote_v5` 55.0%; cycle calls still lose after costs
  (-0.238% / -0.555% at 10 bps).
- On close-only **real MSFT monthly** (40 attempts, horizon 3),
  `multiscale_trend` scores **57.5%** versus original analog **45.0%**,
  always-up **47.5%** and momentum **55.0%**, netting **+2.850%/trade at
  10 bps** and +2.700% at 25 bps. Cycle analogs get only 28 warm-up-eligible
  attempts (46.4% median / 39.3% weighted) and lose heavily after costs.
- **About the requested “+30% forecast” target:** relative to the original
  analog, multiscale is 44.0% → 60.0% on AAPL (**+36.4% relative**) but
  45.0% → 57.5% on MSFT (**+27.8% relative**). Against the stronger momentum
  baseline the gains are only **+3.4%** and **+4.5% relative**. AAPL horizons
  1/3/5/10/20 score **48/50/60/58/56%**, and AAPL's selective
  `|score| ≥ 0.5` row (75.6% on 45/100 attempts) reverses on MSFT (29.4% on
  17/40, -5.879%/trade at 10 bps). Therefore v10 does **not** claim a general
  +30% forecasting improvement or a durable edge; it reports a real
  sample-local improvement and the evidence against over-reading it.
- Expanding the adaptive selector's candidate pool and fallback to v5 makes
  that meta-method worse in the current race (AAPL 52.0%, -0.160%/trade at
  10 bps; MSFT 37.5%, -4.732%/trade), so the selector is not presented as the
  answer. Coverage-limited confidence rows remain ineligible for
  `best_method_on_this_sample`.
- **Real-market connection is market-data only:** browser-direct Binance and
  Kraken public candles (completed bars only), Stooq daily CSV where the
  browser/provider permits it, and the existing custom CORS feed. Symbols,
  adjustments, licensing, venue availability and data quality remain the
  user's homework. There is no server-side arbitrary URL fetcher and no API
  key collection.
- **Paper wallet:** reset an imaginary `PAPER_USD` balance, record a
  hypothetical crypto amount × user-typed USD rate as a simulated conversion,
  place simulated spot orders with fees/realized P&L, and use Follow/Pause/
  **STOP** plus one-bar-at-a-time follow steps. Following is spot long-only,
  capped at 25% of paper equity per new position, duplicate bars are ignored,
  and short conditions only exit paper holdings. **No crypto is accepted or
  converted, no deposit address exists, and no real order can be sent.**
- Tests: **36/36**, including future-mutation no-lookahead proof for the
  cycle vector/neighbours, range checks for the new indicators, all five new
  engines, close-only partial-warmup labelling, pinned AAPL/MSFT v10 results,
  paper-wallet arithmetic and HTTP boundary tests.

**New in v9.0 — path-geometry analog race + causal adaptive selector:**

- A fourth coordinate system describes the *shape of the journey*, not just
  endpoint returns, candle anatomy or indicator state: **16 origin-time
  path-geometry features** — 20/60-bar travel efficiency, volatility-
  normalized log-price trend slopes, 5-bar variance ratio, lag-1
  autocorrelation, realized skew and downside-variance share, drawdown from
  and run-up/range position inside the 60-bar excursion, 20-bar maximum
  drawdown, volatility and true-range compression, signed return streak, and
  real up/down volume balance. It votes as `path_analog_median` /
  `path_analog_weighted`, joins `majority_vote_v4`, and exposes the latest
  setup as `path_analog_now` under the same `j + horizon <= origin` rule.
- **`adaptive_selector`** is a full-coverage causal meta-method. It may follow
  a contestant only after that contestant has **20 fully revealed prior
  attempts**; an old attempt is revealed only when
  `old_origin + horizon <= current_origin`, so unfinished overlapping windows
  cannot teach it early. It ranks eligible contestants by the shrunken score
  `(revealed_hits + 5) / (revealed_attempts + 10)` and otherwise falls back
  to `majority_vote_v4`. Every choice, eligibility list and revealed count is
  published in `adaptive_selector.selection_log`.
- Bundled **real AAPL daily**, 100 hidden-future attempts at horizon 5:
  path median/weighted **47.0% / 47.0%**, `majority_vote_v4` **51.0%**, and
  `adaptive_selector` **54.0%** — better than v8's combined vote, still below
  naive momentum **58.0%**, which remains the full-test best label. The
  selector used fallback on **21** early attempts, then chose momentum 56
  times and path methods 21 times among its 100 calls. Direction was not
  enough: at 10 bps, path/v4/selector net **-0.186% / -0.130% / -0.191% per
  trade**; at 25 bps, **-0.336% / -0.280% / -0.341%**. No edge is claimed.
- On close-only **real MSFT monthly** (40 attempts, horizon 3), path geometry
  becomes available only after its 80-bar warm-up: **28 attempts**, median
  **42.9%**, weighted **28.6%**, v4 **42.9%**; the always-speaking selector
  scores **40.0% over 40** and nets **-4.417%/trade at 10 bps**. This is the
  other half of the lesson: a causal selector can still learn the wrong
  lesson from a small, old, survivor-biased sample.
- Tests: **32/32**, including future-mutation no-lookahead proof for the path
  vector/neighbours, a delayed-reveal audit proving unfinished attempts do
  not teach the selector, close-only partial-warmup labelling, and pinned
  AAPL v9 accuracy/cost results. The v4 analog definition and its pinned
  **44.0%** AAPL result remain untouched.

**New in v8.0 — indicator-regime analog race + stricter ensemble honesty:**

- A third coordinate system now describes each completed setup with **15
  origin-time indicator/regime features**: RSI-14 level and 3-bar slope,
  MACD line/histogram normalized by ATR, Bollinger %B and bandwidth,
  distance to SMA-20/SMA-50 in ATR units, SMA-20 slope, 20-bar Donchian
  position, Stochastic %K, ADX +DI/-DI balance and trend strength,
  realized volatility versus its trailing median, and volume surprise when
  real volume exists. The nearest 30 historical neighbours vote by median
  and distance weight under the same strict rule: candidate `j` is eligible
  only when `j + horizon <= origin`. The latest setup is exposed as
  `indicator_analog_now`; `majority_vote_v3` adds this family to the race.
- A **`consensus_3plus`** subset speaks only when at least
  three available family votes (return analog, momentum, candle, indicator)
  point the same way. It is useful as a research filter, but its rate is
  always published with attempts and coverage, and v8 also stops the
  `best_method_on_this_sample` label from crowning coverage-limited subsets:
  only full-test methods can win that label.
- Bundled **real AAPL daily**, 100 hidden-future attempts at horizon 5:
  indicator median **49.0%**, indicator weighted **46.0%**, and
  `majority_vote_v3` **46.0%** — all below naive momentum **58.0%** and
  below the v7 combined vote's 57.0%. After 10 bps round-trip costs they net
  **-0.167% / -0.323% / -0.265% per trade**; at 25 bps, **-0.317% / -0.473%
  / -0.415%**. The tempting `consensus_3plus` number is **65.4% on only 26
  of 100 attempts (26.0% coverage)** and already falls from **+0.022%/trade
  at 10 bps to -0.128% at 25 bps** — exactly why it is not crowned as best.
- Close-only series are labelled rather than rejected: on real MSFT monthly
  (40 attempts, horizon 3 months) the indicator family can run from the
  close path (median 47.5%, weighted 52.5%, v3 52.5%), while candle methods
  still correctly report unavailable because O=H=L=C contains no candle
  anatomy. Its consensus subset made only **5 calls**, so v8 suppresses its
  accuracy headline entirely. No real-data result demonstrates an edge.
- Tests: **28/28**, including future-mutation no-lookahead proof for the
  indicator vector/neighbours, close-only labelling, and pinned AAPL v8
  accuracy/cost results. The original v4 analog definition and its pinned
  **44.0%** AAPL result remain untouched.

**New in v7.0 — candle-structure analog race:**

- A genuinely different feature family joins the blind race: each completed
  candle is described by **gap, range, signed body and 3-bar body, close
  location, wick balance, range expansion versus 20 bars, and volume surprise
  versus its trailing median**. The 30 nearest candle-structure neighbours
  vote by median and by distance weight, and a `majority_vote_v2` adds the
  candle vote to the v6 ensemble. Same origins, same no-lookahead rule
  (candidate outcomes must end before the origin), same 10/25 bps cost rows,
  and every method now reports its own attempt count.
- On the bundled **real AAPL daily** 100-attempt test (horizon 5): candle
  median **50.0%**, candle weighted **49.0%**, combined vote **57.0%** —
  better than return-analog 44.0%, still below naive momentum **58.0%**.
  Standalone candle calls lose after costs (weighted: **−0.157%/trade at
  10 bps, −0.307% at 25 bps**). The combined vote's +0.158%/trade at 10 bps
  is effectively the always-long sample drift (+0.157%) and melts to
  **+0.008% at 25 bps**. Candle shape therefore adds information to measure,
  not a demonstrated tradable edge.
- Close-only files are handled honestly: the MSFT monthly sample has
  O=H=L=C, so candle methods report **unavailable / null with 0 attempts**
  instead of scoring invented candle anatomy; close-based methods continue
  unchanged.
- Tests: **25/25**, including a future-mutation no-lookahead test for candle
  neighbours, close-only unavailability, and pinned real-AAPL v7 results.

**New in v6.0 — ensemble race + cost-aware scoring:**

- **Ensemble evaluation**: five origin-time forecast variants race under the
  same hidden-future discipline — analog median (v4), distance-weighted
  analogs, naive momentum, a majority vote (weighted-analog + momentum +
  RSI-trend), and an agreement-only filter (accuracy always printed **with
  its coverage**; suppressed entirely below 10 filtered attempts).
- **Cost-aware re-scoring**: every variant's calls are re-scored as trades
  after 10/25 bps round-trip costs next to plain always-long — win rate
  after cost and mean net % per trade. On real AAPL this is where the story
  ends: majority vote's 55% direction nets **≈0.00%/trade at 10 bps and
  −0.15% at 25 bps**; even momentum's 58% melts from +0.17% to +0.02%/trade.
- Tests: 22/22 (including a test that higher costs can never raise a win
  rate, and the pinned v4 AAPL number surviving the refactor).

**Forecast-attempt evolution across versions (documented, warts and all):**
All rows are 100 hidden-future attempts on the bundled **real AAPL daily
2015–2017** file at horizon 5 unless noted; baselines: always-up 56.0%,
naive momentum 58.0%.

| Version | What was tried | Result on real data | What it taught |
|---|---|---|---|
| v4.0 | Analog (nearest-neighbour) forecaster | **44.0%** direction, Brier skill −0.13 | Look-alike setups, unweighted, do not beat naive rules here. |
| v5.0 | Same test at 5 horizons; trend/vol regimes; 2nd real sample (MSFT monthly) | 41/44/44/47/36% by horizon; loses all 4 regimes; MSFT 45.0% | No hidden pocket of skill; the one shiny cell (MSFT 6-month 60%) is a multiple-comparison cherry. |
| v6.0 | Distance weighting, majority vote, agreement filter; cost-aware scoring | Weighted 48.0%, majority 55.0%, agreement 56.0% @ 50% coverage — but **≈0%/trade after 10 bps** for the best ensemble | Ensembling recovers part of the gap to momentum yet costs erase it. "More accurate" ≠ "worth trading", and the honest frontier on this sample remains: no demonstrated edge. |
| v7.0 | Candle-structure neighbours (gap/range/body/wicks/close location/volume) + expanded majority vote | Candle 50.0%/49.0%; combined 57.0% vs momentum 58.0%; combined nets +0.158%/trade @10 bps (≈ always-long +0.157%) and +0.008% @25 bps | A different description of old candles still does not reveal the rest. The improvement over 44% is real arithmetic on this sample, but standalone candle calls lose after costs and the combined vote does not beat naïve momentum. |
| v8.0 | Indicator-regime neighbours (RSI/MACD/Bollinger/SMA/Donchian/Stochastic/ADX/volatility/volume) + majority_vote_v3 + consensus_3plus subset | Indicator 49.0%/46.0%; v3 46.0% vs momentum 58.0%; all lose after 10/25 bps costs. Consensus subset 65.4% but only 26/100 coverage and -0.128%/trade @25 bps | A richer coordinate system made the measurement stronger, not the forecast true. Correlated indicators can unanimously describe the same past move; subset accuracy without coverage and costs is marketing, not evidence. |
| v9.0 | Path-geometry neighbours (efficiency, slopes, variance ratio, autocorrelation, skew, excursion/drawdown, compression, streaks, volume balance) + majority_vote_v4 + delayed-reveal adaptive selector | Path 47.0%/47.0%; v4 51.0%; selector 54.0% vs momentum 58.0%; selector nets -0.191%/trade @10 bps and -0.341% @25 bps. MSFT monthly selector: 40.0% and -4.417%/trade @10 bps | Even choosing among methods strictly out-of-sample cannot manufacture information the contestants do not have. The selector mostly rediscovered momentum too late and with worse magnitudes; causal selection prevents leakage, not loss. |
| v10.0 | Cycle/flow neighbours (18 features incl. invented Signed Path Pressure + Entropy-Weighted Trend) + direct 3/5/10/20/60/120-bar multiscale trend + majority_vote_v5 | Cycle 52.0%/47.0%; v5 55.0%; **multiscale 60.0%** vs momentum 58.0%, nets +0.290%/trade @10 bps and +0.140% @25 bps. MSFT monthly multiscale 57.5% (40 attempts), +2.850% @10 bps | The first full-test sample-local win over momentum on both bundled real samples, but horizons 1/3 are 48/50% on AAPL and selective confidence reverses on MSFT. Relative gain vs original analog is +36.4% AAPL / +27.8% MSFT; no universal +30% or durable edge is claimed. |
| v11.0 | Kalman local trend + Omni direct consensus + rank-fusion neighbours + majority_vote_v6; halal-screened paper bot | Kalman 62.0%; **Omni 64.0%** vs momentum 58.0%; Kalman +0.846%/trade and Omni +0.641% @10 bps. MSFT monthly Kalman 60.0% (40 attempts), +2.307% @10 bps; rank fusion loses | More classic/modern direct methods raised the two primary full-test scores, and Kalman is >30% relative to the original analog on both. It is still only +6.9%/+9.1% relative to momentum, neighbours/long horizons remain fragile, and no durable edge is claimed. |
| v12.0 | Hull + Supertrend + Kaufman + Haar + causal Markov regime + Atlas Fusion; SQLite pooled research; all-asset halal evidence database | **Hull 67.0%** on AAPL (+0.786%/trade @10 bps); MSFT Hull only 52.5%, Atlas/Supertrend/Kaufman 60.0%. Bundled DB pool: Atlas 62.692% over 260 attempts | A bigger memory makes weak/strong methods easier to compare across series, but correlated survivor samples cannot create an 80% law. Hull's AAPL win reverses on MSFT; database scale helps measurement, not prophecy. |
| v13.0 | Aroon/TSI/TRIX/CMO/Ultimate/RVI/regression/Donchian/OBV/Coppock + invented Pressure Wave/Regime Compass/Phoenix + delayed-label Meta Hedge and online logistic learning; 37 engines; market presets; demo e-wallet | **Ultimate 68.0%** on AAPL (+0.893%/trade @10 bps); Pressure 64.0%; Phoenix/Compass 62.0%; Meta/Logistic 61.0%. MSFT Pressure 60.0% (+3.431%) but Logistic 30.0%. Full-coverage DB pool: **Pressure 63.077% over 260** | The best single-sample number rose 67→68% and the pooled leader rose 62.692→63.077%, but neighbouring horizons and MSFT expose fragility and the fanciest learner can be the worst. More old/modern machinery improves comparison, not certainty; 80% remains unproven. |
| v14.0 | Seven causal minute engines + Atlas Minute Pulse; 1/3/5/15/30-bar hidden-future race to 5,000 attempts; Wilson intervals/coverage/costs; explicit 80% goal gate; 1m bot risk profile; external-account mirror and manual tickets | No new bundled real minute sample, so no new real accuracy headline. Prior real best remains 68% (one AAPL daily test) and 63.077% pooled. Synthetic 1m output is software validation only | v14 builds the minute measurement and operating workflow needed to pursue 80% honestly; it does not convert a synthetic run or one future series into proof. Real funds remain in the user's own account and automatic live execution remains disabled. |

The lab's improvement across versions is in **measurement strength**, not in
manufactured accuracy: each version makes it harder for a weak method (or a
hopeful human) to fool itself.

**New in v5.0 — deeper honesty for the Forecast Lab:**

- **Multi-horizon evaluation**: the 100-attempt hidden-future test now runs at
  1/3/5/10/20 bars side by side, because an "edge" living at exactly one
  horizon is usually a cherry. On real AAPL daily: analog accuracy
  41/44/44/47/36% — no edge at *any* horizon.
- **Regime-split accuracy**: each attempt is bucketed by origin-time facts only
  (price vs causal SMA-20; 10-bar volatility vs its trailing-100 median) and
  scored against always-up *inside the same bucket*. On real AAPL the analog
  loses in all four buckets (e.g. above-SMA20: 44.3% vs 65.6% always-up).
- **Analog path simulation**: bootstrap over the *real* forward paths of
  look-alike setups (seeded, reproducible) → terminal-return percentiles and
  worst-dip (max-drawdown) percentiles over 20 bars. Real AAPL latest setup:
  terminal p5 −15.1%, median +0.4%, p95 +7.7%; median worst dip 5.7%, p95
  16.5% — a dispersion picture of history, never a promise.
- **Second real sample evaluated** (`sample-forecast-real-msft-monthly.json`):
  MSFT monthly 2000–2010 (123 bars, close-only) via the new `min_history`
  knob → analog 45.0% vs always-up 47.5% / momentum 55.0% → same verdict.
  Its tempting 60% at the 6-month horizon is precisely what neighbouring
  horizons (47.5% / 45.0%) expose as noise.
- **Performance**: feature vectors are precomputed once per evaluation
  instead of per origin (the v4 recomputation was the bottleneck); a test
  pins the AAPL verdict numbers so the cache provably changes nothing.
- Tests: 20/20.

**New in v4.0 — Forecast Lab + real historical samples:**

- **Historical-analog lookup** (`POST /api/lab/forecast`, UI card 5): for the
  latest bar, the lab finds the 30 most similar past setups (1/3/5/10/20-bar
  returns, RSI-14, SMA-20 distance, 10-bar volatility) and reports what those
  setups *actually did next* in your data (median, 25th/75th percentiles,
  share that rose, worst/best) at horizons 1–20 bars. It is a conditional
  histogram of your own file's history — **not a price forecast**.
- **The 100-attempt hidden-future test**: the same analog method is replayed
  out-of-sample — hide the future, forecast, uncover, score — and forced to
  compete with always-up, naive-momentum and mean-reversion baselines, with
  a Brier skill score. Analogs may only use outcomes fully known before each
  origin (no lookahead, enforced in code and pinned by a test).
- **Real data, honestly labelled** (`real-data/` + `REAL-DATA-NOTICE.md`):
  AAPL daily OHLCV 2015–2017 (506 bars, public Plotly sample, dividend/split
  adjusted) and five monthly 2000–2010 series (public Vega sample), with
  blob SHAs and conversion notes. Headline result on the **real** AAPL file:
  exactly **100 out-of-sample attempts → analog direction accuracy 44.0%**
  vs always-up 56.0% and naive momentum 58.0%; Brier skill −0.13; verdict
  `no_edge_over_baselines_on_this_sample`. In other words: fed old candles
  and asked to "know the rest", the analog forecaster demonstrably could not
  beat a coin-flip dressed as a baseline — and now the tool proves that
  instead of pretending otherwise. The signal lab on the same real file
  honestly supports only 1d/1w (intraday cannot be invented from daily bars)
  and finds just 19 candidate consensus events in two years — which is why
  the rolling forecast test, not signal counting, carries the 100 attempts.
- **Data guide** in `/api/lab/spec`: how to export real bars you have a right
  to use, adjusted-vs-raw discipline, and judge-forecasters-out-of-sample
  methodology.

Tests: **18/18 passing** (including a no-lookahead structure test and a test
that pins the real-AAPL no-edge verdict so it can never be quietly dressed up).

## Data formats

CSV:

```csv
timestamp,open,high,low,close,volume
1767225600,100,101,99,100.7,12345
```

JSON:

```json
{"bars":[{"t":1767225600,"o":100,"h":101,"l":99,"c":100.7,"v":12345}]}
```

For a meaningful 100-signal test, supply as many clean base bars as possible;
hundreds may be enough for indicators, but thousands are usually needed for
100 completed non-overlapping signals. The result states the exact number
actually tested.

## APIs

- `GET /api/strategies` — atlas + Market Lab specification.
- `GET /api/goals` — machine-readable project goals and the unfinished 80%
  gate (also in `GOALS.md`).
- `GET /api/lab/spec` — timeframes, strategy engines and feed format.
- `GET /api/lab/demo?strategy=atlas_minute_pulse&max_signals=100&horizon_bars=5&round_trip_cost_bps=10`
  — deterministic synthetic software validation.
- `POST /api/lab/analyze` — JSON body containing `bars[]` or `csv_text`, plus
  `strategy`, `max_signals`, `horizon_bars`, and `round_trip_cost_bps`. Each
  timeframe returns `snapshot`, `latest_signal`, `historical_validation`
  (with `equity_curve`), `walk_forward`, and `strategy_tournament`.
- `POST /api/lab/watchlist` — `{"symbols": {"BTC": [...bars...], "EURUSD":
  {"csv": "..."}}, "strategy": "consensus"}` → latest-condition heatmap.
- `POST /api/lab/minute-forecast` — same `bars[]`/`csv_text` body plus
  `attempts` (10–5000) and `horizons` such as `[1,3,5,15,30]` → causal
  minute-method attempts/coverage/Wilson intervals/5-10-25 bps means and a
  `goal_80_assessment` that never treats one series as project proof.
- `POST /api/lab/self-correct` — the v15 failure loop. Body: `bars[]` or
  `csv_text`, optional `second_bars`/`second_csv_text` (validation symbol),
  `methods`, `horizons`, `attempts`, `cost_bps`, `rounds`, `remember`
  (default true) and `use_saved_lessons` (default true). Returns `rounds`
  (candidates, causes, applied remedies, retirements), `lessons` with
  `resolved`/`recurred`/`retired` status, `failure_tally`,
  `resolved_lessons`, `retired_candidates`, `verdict` and a `goal_80` block
  whose `goal_established` is always false. `{"demo": true}` runs the
  synthetic software check.
- `GET /api/lessons?symbol=&status=` — the persisted failure memory: lesson
  ledger, cause tally, cause library and the latest run.
- `GET /api/failure-memory` — tally + recent lessons + loop specification.
- `POST /api/lessons/clear` — forget lessons (`{"symbol": "..."}` optional);
  only sensible with genuinely new data or methods.
- `POST /api/lab/forecast` — same `bars[]`/`csv_text` body plus `attempts`
  (default 100), `horizon`, `top_n` → `analog_now` distributions and the
  `rolling_eval` hidden-future verdict vs baselines, plus `candle_analog_now`
  and candle rows inside `ensemble_eval` when real OHLC ranges exist, plus
  `indicator_analog_now` and indicator/`majority_vote_v3`/`consensus_3plus`
  rows in the same blind race, plus `path_analog_now` and
  path/`majority_vote_v4`/`adaptive_selector` rows with a per-attempt
  delayed-reveal selection log, plus `cycle_analog_now`,
  `multiscale_trend_now`, `multiscale_trend_eval`, cycle/`majority_vote_v5`
  rows and coverage-labelled multiscale confidence diagnostics, plus
  `rank_fusion_analog_now`, `kalman_trend_now`, `omni_direct_now`,
  `direct_method_eval`, and Kalman/Omni/rank-fusion/`majority_vote_v6` rows,
  plus `hull_trend_now` and Hull/Supertrend/Kaufman/Haar/Markov/
  `atlas_fusion_v12`/`majority_vote_v7` rows, plus
  `atlas_pressure_wave_now`, `atlas_regime_compass_now`, `atlas_phoenix_now`
  and Aroon/TSI/TRIX/CMO/Ultimate/RVI/regression/Donchian/OBV/Coppock/
  Pressure/Compass/Phoenix/`majority_vote_v8`/`atlas_meta_hedge`/
  `atlas_online_logistic` rows with `v13_direct_methods` and
  `v13_meta_learners` metadata.
- SQLite database: `GET /api/db/stats`, `GET /api/db/series`,
  `GET /api/db/bars`, `GET /api/db/leaderboard`, `GET /api/db/halal`,
  `POST /api/db/seed`, `POST /api/db/import-current`,
  `POST /api/db/research`, and `POST /api/db/halal-profile`.
- Halal paper bot (simulation only): `POST /api/halal/screen` (stocks and
  explicit-evidence crypto/currency/commodity/ETF/fund profiles),
  `GET /api/bot`, `POST /api/bot/reset`, `POST /api/bot/register-stock`,
  `POST /api/bot/status` (`start`, `resume`, `pause`, `stop`, `reset_risk`),
  `POST /api/bot/settings`, `POST /api/bot/step`, `POST /api/bot/stop`, and
  `POST /api/bot/sync-halal-db`. Bot entries require a registered asset
  whose current user-supplied evidence screen returns exactly `pass`; this
  is not certification.
- Demo e-wallet (simulation only): `GET /api/paper/wallet`,
  `POST /api/paper/reset`, `POST /api/paper/external-balance` (records a
  user-reported balance in the user's own external account; no transfer or
  verification), legacy `POST /api/paper/deposit-simulated`,
  `POST /api/paper/deposit-balance-simulated`,
  `POST /api/paper/convert-balance-simulated`,
  `POST /api/paper/withdraw-simulated`,
  `POST /api/paper/transfer-bot-simulated`, `POST /api/paper/order`,
  `POST /api/paper/follow`, `POST /api/paper/stop`, and
  `POST /api/paper/follow-step`. Despite the endpoint names containing
  “simulated”, these endpoints never accept, convert, withdraw or transfer
  real funds and never send real orders.
- `GET /api/calc?kind=position&account=10000&risk_pct=1&entry=50&stop=47.5`.

## Run

```bash
python3 tradeatlas.py --serve --host 127.0.0.1 --port 8820   # private local web UI
TRADEATLAS_ACCESS_TOKEN='choose-a-long-secret' python3 tradeatlas.py --serve --host 127.0.0.1 --port 8820
python3 tradeatlas.py --demo   # samples incl. sample-database-research.json
python3 -m unittest test_tradeatlas                        # 49 tests
```

Tests: **65/65 passing**. No dependencies beyond Python 3 standard library.
Private runtime files `tradeatlas.db` and `tradeatlas-bot-state.json` are
created beside the code (or at `TRADEATLAS_DB` / `TRADEATLAS_BOT_STATE`);
they are user data, not source samples.

## Who it is for

Learners and researchers who want to understand famous strategies, feed in
their own historical data, and measure what a precisely-defined rule actually
did — including when the honest result is weak — before risking real money.
