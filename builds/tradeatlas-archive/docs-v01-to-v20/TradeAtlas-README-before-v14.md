# TradeAtlas — Genius Idea #14 (v1.0)

An **educational atlas** of the world's best-known trading strategies and
market-analysis methods — Python stdlib only, zero subscriptions, no live data.

## ⚠️ Read this first

TradeAtlas is an **educational reference only. It is NOT financial advice.**
It contains no buy/sell signals, no live market data, no broker links, and no
profit promises. Most short-term traders lose money, and no strategy listed
here changes that. Study, paper-trade, risk only money you can afford to lose,
and consult a licensed financial professional for personal decisions.

## What is inside

- **16 strategies** across trend, mean-reversion, momentum, volatility,
  price-action, intraday, market-neutral, macro and investing families — each
  with the core idea, classic textbook entry/exit/stop rules (as education),
  why people like it, **how it fails**, and a risk note.
- **10 analysis methods** — price action, candlesticks, chart patterns,
  indicators, volume, order-flow basics, fundamentals, macro/sentiment,
  intermarket, and backtesting & journaling — with tools and traps.
- **8 candlestick patterns illustrated** as inline SVG (invented example
  prices, shape teaching only).
- **3 risk calculators** (arithmetic, never advice): position size,
  risk:reward with breakeven win-rate, and expectancy in R.
- **8 risk rules + 12-term glossary** — the part that actually keeps
  beginners alive.
- JSON API: `/api/strategies` (the whole atlas) and
  `/api/calc?kind=position&account=10000&risk_pct=1&entry=50&stop=47.5`.

## Run

```bash
python3 tradeatlas.py --serve --host 0.0.0.0 --port 8820   # web UI
python3 tradeatlas.py --demo                               # sample-home.html + sample-atlas.json
python3 -m unittest test_tradeatlas                        # 6 tests
```

Tests: 6/6 passing. No dependencies beyond the Python 3 standard library.
