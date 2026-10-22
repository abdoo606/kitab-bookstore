# Real historical sample data — provenance & limits

These files are **real historical market data snapshots** bundled so the
TradeAtlas methodology (signals, 100-attempt tests, forecast evaluation) can
be run on genuine prices instead of the synthetic demo generator. They are
**not live data**, they end years ago, and they are third-party samples:
always verify any series against your own broker/exchange feed before using
results for anything, and never treat backtest output as advice or as a
forecast of future prices.

## Files

- `aapl-daily-2015-2017.plotly.csv` — Apple Inc. (AAPL) **daily** OHLCV,
  2015-02-17 → 2017-02-16 (506 bars). Source: the public `plotly/datasets`
  GitHub repository, file `finance-charts-apple.csv` (blob SHA
  `7b1bab3953bb5cdf47e84de1048ca04b0c991987`), fetched 2026-10-21 via the
  GitHub API. Conversion: open/high/low were multiplied by each row's
  `Adjusted/Close` factor and close set to the Adjusted close (the standard
  dividend/split adjustment), columns renamed to TradeAtlas canonical form.
  Original columns also carried moving-average/Bollinger helper columns,
  which were dropped.
- `vega-{aapl,amzn,goog,ibm,msft}-monthly-2000-2010.csv` — **monthly**
  close-only series, Jan 2000 → Mar 2010 (GOOG from Aug 2004). Source: the
  public `vega/vega-datasets` GitHub repository, file `data/stocks.csv`
  (blob SHA `58e2ce1bed01eeebe29f5b4be32344aaec5532c0`), fetched 2026-10-21
  via the GitHub API. Conversion: split by symbol; open/high/low set equal
  to the monthly price (the source has no OHLC or volume), volume 0. Treat
  these as close-only research series — indicators that need intraday
  ranges (ATR/Stochastic/ADX) degenerate on them.

## Known caveats

- One stock / five large-cap survivors is a **biased, tiny universe**
  (survivorship bias). Results on these files say nothing about other
  symbols, other eras, or the future.
- The Plotly file's own upstream provenance is a charting-library sample
  dataset; treat it as *plausibly real, unverified tick-for-tick*. Spot
  checks match AAPL's known 2015–2017 pre-split price range.
- Monthly bars cannot support the intraday timeframe table (1m–4h); the
  daily file honestly supports only 1d/1w. Intraday validation still
  requires intraday files you supply yourself.
- Point-in-time corporate actions, delistings and index composition are not
  modelled anywhere in TradeAtlas.
