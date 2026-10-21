#!/usr/bin/env python3
"""
TradeAtlas — Genius Idea #14 (stdlib only, zero subscriptions).

An EDUCATIONAL atlas of the world's well-known trading strategies and
market-analysis methods, with illustrated candlestick patterns,
risk-management calculators, and a bring-your-own-data Market Lab.

What this tool IS:
  - A structured reference: 16 classic strategies, 10 analysis methods,
    8 candlestick patterns (illustrated with invented example prices),
    position-size / risk-reward / expectancy calculators, and the risk
    rules every textbook repeats.
  - A study aid for people learning HOW the field thinks.

What this tool is NOT (by design):
  - NOT financial advice and not a recommendation engine. Market Lab labels
    are mechanical indicator conditions, not instructions to trade.
  - It bundles no licensed live market feed or broker integration. Real
    market analysis requires lawful user-supplied OHLCV data or a
    browser-polled feed endpoint supplied by the user.
  - No profit promises — most short-term traders lose money, and no
    strategy or backtest in this atlas changes that statistic.
  - Nothing here knows the future. Markets are uncertain; every entry
    describes a historical idea together with how it fails.

Run:
  python3 tradeatlas.py --serve --host 0.0.0.0 --port 8820
  python3 tradeatlas.py --demo   # writes sample-home.html
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
import time
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import marketlab as ml
import pipeline as pl
import selfcorrect as sc
import evolution as evo
import diagnostics as diag
from platformdb import MarketDatabase

VERSION = "17.0"
PAPER_WALLET = ml.new_paper_wallet()
PAPER_WALLET_LOCK = threading.Lock()
BOT_STATE_PATH = os.environ.get(
    "TRADEATLAS_BOT_STATE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "tradeatlas-bot-state.json"))


def _load_halal_bot() -> dict:
    try:
        with open(BOT_STATE_PATH, encoding="utf-8") as handle:
            return ml.halal_bot_import_state(json.load(handle))
    except Exception:
        return ml.new_halal_paper_bot()


HALAL_BOT = _load_halal_bot()
HALAL_BOT_LOCK = threading.Lock()


MARKET_DB_PATH = os.environ.get(
    "TRADEATLAS_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "tradeatlas.db"))
ACCESS_TOKEN = os.environ.get("TRADEATLAS_ACCESS_TOKEN", "")
MARKET_DB = None
MARKET_DB_LOCK = threading.Lock()


def _market_db() -> MarketDatabase:
    global MARKET_DB
    if MARKET_DB is None:
        MARKET_DB = MarketDatabase(MARKET_DB_PATH)
        if MARKET_DB.stats()["counts"]["bars"] == 0:
            MARKET_DB.seed_bundled_data(os.path.dirname(os.path.abspath(__file__)))
    return MARKET_DB


def _private_request_ok(headers, path: str) -> bool:
    if not ACCESS_TOKEN:
        return True
    if not path.startswith(("/api/paper/", "/api/bot", "/api/halal/", "/api/db/")):
        return True
    return headers.get("X-TradeAtlas-Token") == ACCESS_TOKEN


def _save_halal_bot() -> bool:
    try:
        temporary = BOT_STATE_PATH + ".tmp"
        with open(temporary, "w", encoding="utf-8") as handle:
            json.dump(HALAL_BOT, handle, ensure_ascii=False, indent=1)
        os.replace(temporary, BOT_STATE_PATH)
        return True
    except OSError:
        return False
DISCLAIMER = (
    "TradeAtlas is educational/research software only. It is NOT financial advice. "
    "Market Lab long/short (buy/sell-condition) labels are mechanical indicator "
    "states, not recommendations. TradeAtlas bundles no licensed live market data; "
    "real-market tracking uses only OHLCV data or a feed endpoint that you supply "
    "and have the right to use. Its wallet is a paper simulation only: never send "
    "money or cryptocurrency to TradeAtlas; it has no deposit address, custody, "
    "conversion, withdrawal or broker execution. Its halal-stock screen is transparent "
    "arithmetic on evidence you supply, not a fatwa or certification, and its bot is paper-only. "
    "It makes no profit promises. Most short-term "
    "traders lose money. Study the ideas, paper-trade first, risk only money you "
    "can afford to lose, and consult a licensed financial professional for "
    "personal decisions."
)

# ---------------------------------------------------------------------------
# DATA — the atlas itself. Every rule below is the generic textbook version,
# stated as education. None of it is a recommendation.
# ---------------------------------------------------------------------------
STRATEGIES = [
    {"id": "trend-following", "name": "Trend following", "family": "Trend",
     "markets": "Stocks, futures, forex, crypto", "timeframes": "Daily / weekly",
     "difficulty": "Beginner",
     "idea": "Prices that have been rising tend to keep rising for a while ('the trend is your friend'). The strategy rides established directional moves instead of predicting reversals.",
     "rules": {"entry": "Join the existing direction: e.g., buy when price holds above a rising long-term moving average after a pullback.",
               "exit": "Trail the stop behind the trend and let winners run; exit when the trend breaks (e.g., close below the trend line / average).",
               "stop": "Below the most recent swing low (long) or a volatility-based distance such as 2x ATR."},
     "pros": "Simple, captures the biggest moves, works across many markets.",
     "fails": "Sideways/ranging markets cause repeated small losses ('whipsaws'); late entries when the trend is exhausted.",
     "risk": "Expect many small losses between a few large wins — psychology, not math, is the hard part."},
    {"id": "breakout", "name": "Breakout trading", "family": "Trend",
     "markets": "All liquid markets", "timeframes": "Hourly to daily",
     "difficulty": "Beginner",
     "idea": "When price escapes a well-defined range or level (support/resistance, prior high/low), stored energy releases and a new move often begins.",
     "rules": {"entry": "Enter after a close beyond the level, ideally with above-average volume confirming.",
               "exit": "Target measured moves (e.g., range height projected from the breakout) or trail the stop.",
               "stop": "Just back inside the broken range — if price returns, the breakout failed."},
     "pros": "Clear levels, clear invalidation; catches moves early.",
     "fails": "False breakouts ('fakeouts') are common, especially on low volume or into news.",
     "risk": "Chasing extended breakouts without waiting for the close is the classic beginner trap."},
    {"id": "pullback-retest", "name": "Pullback / retest entries", "family": "Trend",
     "markets": "All liquid markets", "timeframes": "Hourly to weekly",
     "difficulty": "Beginner",
     "idea": "Instead of chasing, wait for a trending market to dip to a known level (old resistance turns support, a rising moving average) and enter there at a better price with a closer stop.",
     "rules": {"entry": "After the pullback reaches the level and shows rejection (e.g., a bullish candle at support in an uptrend).",
               "exit": "Previous swing high first, then trail the stop under rising swing lows.",
               "stop": "Beyond the level being tested — if it gives way, the idea is wrong."},
     "pros": "Better prices and tighter, logical stops than chasing.",
     "fails": "Strong trends sometimes never pull back; weak trends 'pull back' all the way into reversal.",
     "risk": "Distinguishing a healthy pullback from the start of a reversal is judgment, not certainty."},
    {"id": "range-mean-reversion", "name": "Range trading & mean reversion", "family": "Mean reversion",
     "markets": "Sideways stocks, forex pairs, indices", "timeframes": "Hourly to daily",
     "difficulty": "Intermediate",
     "idea": "In a sideways market, price oscillates between support and resistance and tends to return toward its average. Buy near support, sell near resistance, fade extremes.",
     "rules": {"entry": "At the range edges with confirmation (rejection candle, oscillator extreme).",
               "exit": "Mid-range (the mean) first, opposite edge second.",
               "stop": "Outside the range — a close beyond it means the regime changed."},
     "pros": "Frequent, well-defined setups; clear levels both ways.",
     "fails": "Ranges eventually break — one breakout against you can erase many small range wins.",
     "risk": "Never 'average down' a broken range without a predefined maximum loss."},
    {"id": "rsi-momentum", "name": "RSI momentum & extremes", "family": "Momentum",
     "markets": "All liquid markets", "timeframes": "Hourly to daily",
     "difficulty": "Beginner",
     "idea": "The Relative Strength Index (0-100) measures speed of recent gains vs losses. Readings above 70 / below 30 flag stretched conditions; in trends, pullbacks to RSI 40-50 (uptrend) mark continuation zones.",
     "rules": {"entry": "Two textbook styles: (a) fade extremes only inside ranges; (b) in trends, enter when RSI resets to mid-zone and turns back with price.",
               "exit": "Opposite extreme, or price-based targets (prior swing).",
               "stop": "Beyond the swing that created the RSI signal."},
     "pros": "Objective overbought/oversold gauge; divergence warns of weakening moves.",
     "fails": "In strong trends RSI can stay 'overbought' for weeks — fading it blindly is expensive.",
     "risk": "RSI is a thermometer, not a steering wheel: it describes, it does not predict."},
    {"id": "macd-crossover", "name": "MACD crossover & histogram", "family": "Momentum",
     "markets": "All liquid markets", "timeframes": "Daily / 4-hour",
     "difficulty": "Beginner",
     "idea": "MACD compares two exponential moving averages (12 vs 26). Crossovers of the MACD line and its 9-period signal line mark momentum shifts; the histogram visualizes their distance.",
     "rules": {"entry": "Long when MACD crosses up through the signal line (stronger below/near the zero line in an uptrend context).",
               "exit": "Opposite crossover, histogram shrinking after extension, or price targets.",
               "stop": "Beyond the swing low/high preceding the crossover."},
     "pros": "Combines trend + momentum in one panel; divergence is a useful warning.",
     "fails": "Lagging and noisy in ranges — crossovers whipsaw sideways markets.",
     "risk": "Because it is built from averages, MACD always confirms AFTER price has moved."},
    {"id": "bollinger-squeeze", "name": "Bollinger Band squeeze", "family": "Volatility",
     "markets": "All liquid markets", "timeframes": "Daily / 4-hour",
     "difficulty": "Intermediate",
     "idea": "Bollinger Bands (20-period average ±2 standard deviations) widen with volatility and contract in quiet markets. Extreme contraction ('the squeeze') often precedes an expansion move — direction unknown.",
     "rules": {"entry": "Wait for the expansion: a strong close outside the band after a squeeze, trade in that direction.",
               "exit": "Ride while closes stay outside/near the band ('walking the band'); exit when momentum closes back inside.",
               "stop": "Middle band (the 20-period average) or the squeeze's opposite edge."},
     "pros": "Objective volatility regime detector; adapts to market speed.",
     "fails": "The squeeze says 'something is coming', never which way; first expansion can reverse violently.",
     "risk": "Touching a band is not by itself a reversal signal — in trends price hugs bands."},
    {"id": "ma-cross", "name": "Moving-average cross (golden / death cross)", "family": "Trend",
     "markets": "Indices, large stocks, forex", "timeframes": "Daily / weekly",
     "difficulty": "Beginner",
     "idea": "A faster average (e.g., 50-day) crossing above a slower one (200-day) is called a golden cross; below, a death cross. A slow regime filter more than a precise trigger.",
     "rules": {"entry": "Favor longs while price and the fast average sit above the slow average; favor defense/cash below.",
               "exit": "Opposite cross, or use crosses only as a bias filter for other entries.",
               "stop": "System-level: the opposite cross IS the exit — per-trade stops still apply."},
     "pros": "Keeps you on the right side of major trends; trivially backtestable.",
     "fails": "Very lagging — by the cross, much of the move happened; sideways years whipsaw it.",
     "risk": "A filter reduces (never removes) drawdowns; past index behavior is not a guarantee."},
    {"id": "sr-bounce", "name": "Support & resistance (horizontal levels)", "family": "Price action",
     "markets": "All markets", "timeframes": "All",
     "difficulty": "Beginner",
     "idea": "Markets remember levels where price previously reversed or stalled. Those zones attract orders again, so trades are planned around them rather than in empty space.",
     "rules": {"entry": "Buy support / sell resistance with a confirmation candle, or trade the break-and-retest.",
               "exit": "The next opposing level.",
               "stop": "Just beyond the level — beyond it, the level failed."},
     "pros": "The foundation under almost every other strategy; no indicators needed.",
     "fails": "Levels are zones, not laser lines; they weaken with each test and break without warning.",
     "risk": "Drawing a level does not obligate the market to respect it."},
    {"id": "fibonacci", "name": "Fibonacci retracement", "family": "Price action",
     "markets": "All markets", "timeframes": "Hourly to weekly",
     "difficulty": "Intermediate",
     "idea": "After an impulse move, pullbacks often pause near 38.2%, 50%, or 61.8% of that move. Traders watch those proportional zones for trend-continuation entries.",
     "rules": {"entry": "In the 50-61.8% zone ('golden pocket') when it aligns with structure (old level, average) and a rejection appears.",
               "exit": "Prior swing extreme, then extension levels (127%, 161.8%).",
               "stop": "Beyond the next retracement level or the impulse origin."},
     "pros": "Gives planned, proportional entry zones instead of chasing.",
     "fails": "Self-fulfilling at best; weak trends retrace 100%+. Three zones means one usually 'works' — selection bias.",
     "risk": "Ratios are conventions, not physics. Confluence with structure matters more than the decimal."},
    {"id": "vwap-intraday", "name": "VWAP intraday", "family": "Intraday",
     "markets": "Stocks, futures (intraday)", "timeframes": "1-15 minute",
     "difficulty": "Intermediate",
     "idea": "VWAP is the day's volume-weighted average price — the level institutions benchmark fills against. Intraday traders use it as a fair-value magnet and bias line.",
     "rules": {"entry": "Trend day: buy pullbacks to a rising VWAP. Range day: fade moves 2+ standard-deviation bands away from VWAP back toward it.",
               "exit": "VWAP itself (mean trades) or band extensions (trend trades). Flat by the close.",
               "stop": "Beyond the band/level that defined the setup; time-based exit before close."},
     "pros": "Objective, widely watched intraday reference; resets daily so no stale levels.",
     "fails": "Requires volume data and screen time; news days ignore VWAP entirely.",
     "risk": "Intraday trading has the highest cost drag (spread+fees) — most day traders lose."},
    {"id": "gap-and-go", "name": "Gap-and-go (opening momentum)", "family": "Intraday",
     "markets": "Stocks with overnight news", "timeframes": "First 30-90 minutes",
     "difficulty": "Advanced",
     "idea": "A stock gapping on real news with heavy pre-market volume sometimes continues in the gap direction during the opening range as institutions reposition.",
     "rules": {"entry": "After the first minutes form an opening range; enter on its break in the gap direction with volume surging.",
               "exit": "Fast, into opening momentum; most gap trades are done within the first hour.",
               "stop": "Opening-range opposite edge — gaps that fill immediately are failed ideas."},
     "pros": "Concentrated opportunity window; news provides a genuine catalyst.",
     "fails": "Many gaps fade and fill; spreads and slippage are widest exactly then.",
     "risk": "Fastest way for a beginner to lose: emotional, leveraged, wide spreads. Paper-trade extensively."},
    {"id": "pairs-statarb", "name": "Pairs trading (statistical basics)", "family": "Market-neutral",
     "markets": "Related stocks, ETFs, futures spreads", "timeframes": "Daily",
     "difficulty": "Advanced",
     "idea": "Two historically related instruments (e.g., two banks) tend to keep a stable price relationship. When the spread stretches far from its average, buy the laggard and short the leader, betting on the relationship — not direction.",
     "rules": {"entry": "When the spread's z-score exceeds a threshold (textbooks use ±2) after checking the pair is still fundamentally linked.",
               "exit": "Spread returns toward its mean (z near 0).",
               "stop": "A wider z (e.g., ±3-4) or any fundamental break in one leg (earnings disaster, merger)."},
     "pros": "Market-direction neutral in theory; the rationale is statistical, testable.",
     "fails": "Relationships break permanently ('the spread can stay irrational longer…'); borrow costs on the short leg.",
     "risk": "Correlation is not a contract. Cointegration can vanish exactly when you size up."},
    {"id": "carry", "name": "Forex carry basics", "family": "Macro",
     "markets": "Forex (major pairs)", "timeframes": "Weeks to months",
     "difficulty": "Advanced",
     "idea": "Borrow a low-interest currency, hold a higher-interest one, and earn the rate difference ('swap'). The return is the interest — the risk is the exchange rate moving against you more than the carry earned.",
     "rules": {"entry": "Textbook version pairs the carry with a supportive trend/risk environment and modest leverage.",
               "exit": "When rate differentials shrink, volatility spikes, or the trend breaks.",
               "stop": "Position-level risk limits; carry trades historically unwind violently in crises."},
     "pros": "A real, well-documented long-term factor in currency markets.",
     "fails": "'Picking up pennies in front of a steamroller': calm gains, sudden crash losses (2008, 2020).",
     "risk": "Leverage turns a slow interest trickle into a fast margin call. This is a professional strategy."},
    {"id": "dca-value", "name": "Dollar-cost averaging & value averaging", "family": "Investing",
     "markets": "Broad index funds, diversified portfolios", "timeframes": "Monthly, years",
     "difficulty": "Beginner",
     "idea": "Invest a fixed amount on a fixed schedule regardless of market noise. You automatically buy more units when prices are low and fewer when high, removing timing decisions.",
     "rules": {"entry": "Automatic fixed contributions (e.g., monthly) into diversified holdings.",
               "exit": "Goal-based (retirement, house deposit), with periodic rebalancing — not headlines.",
               "stop": "None per-trade; risk is managed by diversification, horizon, and keeping an emergency fund outside the market."},
     "pros": "The approach with the strongest evidence for ordinary savers; behaviorally robust.",
     "fails": "Sitting through -30% drawdowns is emotionally hard; single-stock DCA can ride a failing company to zero.",
     "risk": "Still not a guarantee: markets can fall for years. Diversification and horizon do the heavy lifting."},
    {"id": "catalyst-momentum", "name": "Catalyst / earnings momentum", "family": "Momentum",
     "markets": "Stocks (earnings, guidance, approvals)", "timeframes": "Days to weeks",
     "difficulty": "Intermediate",
     "idea": "Genuine news (earnings beats, raised guidance, regulatory approvals) re-prices a stock, and the repricing often drifts over days/weeks ('post-earnings-announcement drift', a documented academic effect).",
     "rules": {"entry": "After the initial reaction day, on strength in the news direction once a base/pullback forms — not into the first chaotic spike.",
               "exit": "As volume and momentum normalize, or at predefined targets.",
               "stop": "Below the post-news base; if the market rejects the news, leave."},
     "pros": "Grounded in a real, studied market phenomenon; news gives a 'why'.",
     "fails": "'Buy the rumor, sell the news' — good news already priced in gets sold into.",
     "risk": "Event risk cuts both ways: secondary offerings, lawsuits, or guidance cuts can gap through stops."},
]

METHODS = [
    {"id": "price-action", "name": "Price action & market structure",
     "summary": "Reading raw price: higher highs/lows (uptrend), lower highs/lows (downtrend), breaks of structure, and reactions at prior swing points. The grammar every other method annotates.",
     "tools": "Swing points, trend lines, horizontal levels, candlestick rejection wicks.",
     "watch_out": "Structure is fractal — an uptrend on 5-minutes can sit inside a weekly downtrend. State your timeframe or fool yourself."},
    {"id": "candlesticks", "name": "Candlestick patterns",
     "summary": "Single- and multi-candle shapes (engulfing, pin bar, doji, morning star…) that summarize who won the session's battle between buyers and sellers.",
     "tools": "The illustrated patterns in this atlas; always read location (at support/resistance) over shape alone.",
     "watch_out": "A pattern in the middle of nowhere means little; the same candle at a major level means more. Context first, names second."},
    {"id": "chart-patterns", "name": "Chart patterns",
     "summary": "Larger formations — triangles, flags, head-and-shoulders, double tops/bottoms, wedges — that frame consolidation vs continuation and give measured-move targets.",
     "tools": "Trend lines, necklines, measured moves (pattern height projected from the break).",
     "watch_out": "Patterns are in the eye of the beholder until they break; trade the break + retest, not the hope."},
    {"id": "indicators", "name": "Indicator analysis",
     "summary": "Mathematical transformations of price/volume: moving averages (trend), RSI/Stochastic (momentum), MACD (both), ATR (volatility for stops/position sizing), Bollinger Bands (volatility envelope).",
     "tools": "One tool per job: trend filter, timing aid, volatility gauge. Fewer, understood deeply, beat ten stacked randomly.",
     "watch_out": "Every indicator is derived from price — it cannot know more than price. Lag is the price of smoothness."},
    {"id": "volume", "name": "Volume analysis",
     "summary": "Volume shows conviction: breakouts on expanding volume, pullbacks on shrinking volume, climax volume at exhaustions, and volume profile (where most trading actually happened).",
     "tools": "Volume bars vs their average, OBV, VWAP, volume-profile high/low volume nodes.",
     "watch_out": "Forex 'volume' from a broker is tick count, not true volume; crypto volume varies wildly by exchange."},
    {"id": "order-flow", "name": "Order-flow basics",
     "summary": "Watching the actual bid/ask battle: order book (Level 2), time & sales, and footprint/delta concepts used by futures day traders.",
     "tools": "Depth of market, tape speed, cumulative delta. Mostly an intraday, futures-centric craft.",
     "watch_out": "Spoofing and hidden iceberg orders mean the book can lie; tools and data feeds for this usually cost money."},
    {"id": "fundamental", "name": "Fundamental analysis",
     "summary": "Valuing the underlying business/economy: revenue growth, margins, cash flow, debt, moat, management; for macro assets: rates, inflation, growth, central-bank policy.",
     "tools": "Income statement, balance sheet, cash-flow statement; ratios (P/E, ROE, debt/equity); earnings quality checks.",
     "watch_out": "A great company can be a terrible stock if the price already assumes perfection. Value and price are different questions."},
    {"id": "macro-sentiment", "name": "Macro & sentiment analysis",
     "summary": "Positioning and mood: interest-rate expectations, fear/greed gauges, put/call ratios, COT reports, fund flows. Extremes of one-sided positioning precede reversals — timing them is the art.",
     "tools": "Central-bank calendars, CPI/jobs releases, VIX, COT (Commitment of Traders) data.",
     "watch_out": "Sentiment can stay extreme far longer than a leveraged account can stay solvent. Extremes warn; price confirms."},
    {"id": "intermarket", "name": "Intermarket analysis",
     "summary": "Markets move in families: dollar vs commodities, yields vs growth stocks, risk-on vs risk-off currencies, credit spreads vs equities. Cross-checking relatives confirms or questions a move.",
     "tools": "Correlation checks across DXY, yields, gold, oil, major indices before committing to a narrative.",
     "watch_out": "Correlations are regime-dependent; in panics, 'everything correlates to 1' — diversification fails exactly when wanted most."},
    {"id": "backtesting-journaling", "name": "Backtesting & trade journaling",
     "summary": "The scientific layer: test a rule-set on historical data (including costs), then journal live trades — setup, size, exit, emotion — and review expectancy per setup, not per opinion.",
     "tools": "Spreadsheet or code backtests, walk-forward checks, a trade journal with expectancy = win% × avg win − loss% × avg loss.",
     "watch_out": "Overfitting: tuning rules until history looks perfect guarantees the future disappoints. Out-of-sample honesty or it didn't happen."},
]

# Candlestick patterns with INVENTED example prices (shape teaching only).
# Each bar: (open, high, low, close)
PATTERNS = [
    {"id": "bullish-engulfing", "name": "Bullish engulfing", "signal": "Potential reversal up (at support)",
     "bars": [(10.6, 10.7, 9.9, 10.0), (9.95, 11.0, 9.9, 10.85)],
     "read": "A red candle followed by a green candle whose body completely covers the prior body: buyers overwhelmed sellers in one session."},
    {"id": "bearish-engulfing", "name": "Bearish engulfing", "signal": "Potential reversal down (at resistance)",
     "bars": [(10.0, 10.75, 9.95, 10.65), (10.7, 10.75, 9.75, 9.85)],
     "read": "A green candle engulfed by a red one: sellers took the session back. Most meaningful after a run-up into resistance."},
    {"id": "hammer", "name": "Hammer (pin bar at lows)", "signal": "Rejection of lower prices",
     "bars": [(10.4, 10.45, 9.7, 9.8), (9.8, 10.15, 9.05, 10.05)],
     "read": "Price plunged intraday but closed near the open, leaving a long lower wick: the dip was bought. At support after a decline, it warns sellers are tiring."},
    {"id": "shooting-star", "name": "Shooting star", "signal": "Rejection of higher prices",
     "bars": [(10.0, 10.6, 9.95, 10.55), (10.55, 11.5, 10.35, 10.45)],
     "read": "A long upper wick after an advance: buyers pushed up, sellers pushed it all back by the close. The mirror image of the hammer."},
    {"id": "doji", "name": "Doji", "signal": "Indecision / balance",
     "bars": [(10.0, 10.55, 9.45, 10.02)],
     "read": "Open and close nearly equal despite a wide range: neither side won. After a long trend it hints momentum is stalling — it is a question, not an answer."},
    {"id": "morning-star", "name": "Morning star (3-candle)", "signal": "Potential bottoming reversal",
     "bars": [(11.0, 11.05, 10.1, 10.2), (10.1, 10.25, 9.95, 10.15), (10.2, 11.1, 10.15, 11.0)],
     "read": "Strong red candle, small indecisive candle, strong green candle closing deep into the first: a three-act handover from sellers to buyers."},
    {"id": "evening-star", "name": "Evening star (3-candle)", "signal": "Potential topping reversal",
     "bars": [(10.0, 11.0, 9.95, 10.9), (10.95, 11.15, 10.85, 10.9), (10.85, 10.9, 9.85, 9.95)],
     "read": "The morning star inverted: strong advance, pause, then a strong red candle. A handover from buyers to sellers at highs."},
    {"id": "inside-bar", "name": "Inside bar", "signal": "Compression / pending expansion",
     "bars": [(10.0, 11.2, 9.6, 11.0), (10.7, 10.95, 10.25, 10.45)],
     "read": "A candle fully inside the previous candle's range: volatility contracted. Traders watch which side of the mother bar breaks first — with the trend preferred."},
]

RISK_RULES = [
    ("Risk a tiny fixed fraction per trade", "Textbooks suggest risking about 0.5-2% of the account per idea, so a losing streak is survivable math, not ruin. Position size is derived FROM the stop distance — never the other way around."),
    ("The stop is part of the idea", "Decide before entry where you are proven wrong. A stop that gets moved 'just a bit further' is not risk management; it is hope with extra steps."),
    ("Expectancy over win-rate", "A system can win 40% of the time and profit (big wins, small losses) or win 80% and lose (tiny wins, rare disasters). Track expectancy in R: (win% × avg win) − (loss% × avg loss)."),
    ("Costs are a strategy filter", "Spread + commission + slippage tax every trade. Hyperactive strategies must overcome a wall of friction before any edge shows."),
    ("Leverage multiplies everything", "Leverage scales gains, losses, AND the speed of ruin. Liquidation math does not care about your analysis being eventually right."),
    ("Correlation is hidden size", "Five positions that all move together are one big position. Cap total open risk, not just per-trade risk."),
    ("Drawdowns are the real exam", "Every strategy in this atlas has losing stretches. If a -20% equity dip would make you abandon or revenge-trade, the size was already too big."),
    ("Journal or it didn't happen", "Memory edits history. A written journal (setup, size, exit reason, screenshot) is how 'experience' becomes measurable instead of anecdotal."),
]

GLOSSARY = [
    ("ATR", "Average True Range — typical bar size over N periods; used to set volatility-aware stops and sizes."),
    ("Backtest", "Applying fixed rules to historical data to see how they would have behaved — then distrusting the result appropriately."),
    ("Bid / Ask / Spread", "What buyers offer / sellers ask / the gap between them — the first cost of every trade."),
    ("Drawdown", "Peak-to-trough decline of an account or strategy; the pain metric that ends most trading careers."),
    ("Expectancy", "Average profit per trade over many trades: (win% × avg win) − (loss% × avg loss). Positive or the rest is decoration."),
    ("Liquidity", "How easily size trades without moving the price. Illiquid = wide spreads and exits that vanish in stress."),
    ("R (R-multiple)", "Profit/loss measured in units of initial risk. A +2R win made twice what was risked."),
    ("Risk:Reward", "Distance to stop vs distance to target. 1:2 means risking 1 to aim for 2 — before costs and reality."),
    ("Slippage", "Difference between expected and actual fill price, worst in fast markets and around news."),
    ("Stop-loss", "A predefined exit that limits loss when the idea is wrong. Gaps can jump through stops — they limit, not guarantee."),
    ("Support / Resistance", "Zones where price previously paused or reversed and where resting orders cluster."),
    ("Volatility", "How much price moves. High volatility = opportunity and danger in equal measure; position size must shrink as it rises."),
]

FAMILIES = ("Trend", "Mean reversion", "Momentum", "Volatility", "Price action",
            "Intraday", "Market-neutral", "Macro", "Investing")

# ---------------------------------------------------------------------------
# CALCULATORS — pure functions, validated. These compute arithmetic only;
# they cannot tell anyone whether a trade is a good idea.
# ---------------------------------------------------------------------------

def _pos(name: str, value: float) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number")
    if v <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return v


def position_size(account, risk_pct, entry, stop) -> dict:
    """Units so that (entry - stop) distance risks risk_pct of the account."""
    account = _pos("account", account)
    risk_pct = _pos("risk_pct", risk_pct)
    entry = _pos("entry", entry)
    stop = _pos("stop", stop)
    if risk_pct > 100:
        raise ValueError("risk_pct cannot exceed 100")
    per_unit = abs(entry - stop)
    if per_unit == 0:
        raise ValueError("entry and stop must differ — a zero-distance stop risks everything")
    risk_amount = account * risk_pct / 100.0
    units = risk_amount / per_unit
    return {"direction": "long" if entry > stop else "short",
            "risk_amount": round(risk_amount, 2),
            "per_unit_risk": round(per_unit, 6),
            "units": round(units, 4),
            "position_value": round(units * entry, 2),
            "pct_of_account": round(units * entry / account * 100, 2)}


def risk_reward(entry, stop, target) -> dict:
    entry = _pos("entry", entry)
    stop = _pos("stop", stop)
    target = _pos("target", target)
    risk = abs(entry - stop)
    reward = abs(target - entry)
    if risk == 0:
        raise ValueError("entry and stop must differ")
    if reward == 0:
        raise ValueError("target must differ from entry")
    long = entry > stop
    if long and target < entry:
        raise ValueError("for a long setup the target should be above entry")
    if not long and target > entry:
        raise ValueError("for a short setup the target should be below entry")
    return {"direction": "long" if long else "short",
            "risk_per_unit": round(risk, 6),
            "reward_per_unit": round(reward, 6),
            "ratio": round(reward / risk, 2),
            "breakeven_winrate_pct": round(100.0 / (1 + reward / risk), 1)}


def expectancy(winrate_pct, avg_win_r, avg_loss_r) -> dict:
    wr = _pos("winrate_pct", winrate_pct)
    aw = _pos("avg_win_r", avg_win_r)
    al = _pos("avg_loss_r", avg_loss_r)
    if wr >= 100:
        raise ValueError("winrate_pct must be below 100 — no strategy wins every trade")
    exp_r = (wr / 100.0) * aw - (1 - wr / 100.0) * al
    breakeven = 100.0 * al / (aw + al)
    return {"expectancy_r": round(exp_r, 3),
            "breakeven_winrate_pct": round(breakeven, 1),
            "verdict": ("Positive expectancy on these inputs (before costs)."
                        if exp_r > 0 else
                        "Negative expectancy on these inputs — this combination loses on average, before costs.")}


CALCS = {"position": (position_size, ("account", "risk_pct", "entry", "stop")),
         "riskreward": (risk_reward, ("entry", "stop", "target")),
         "expectancy": (expectancy, ("winrate_pct", "avg_win_r", "avg_loss_r"))}

# ---------------------------------------------------------------------------
# ILLUSTRATION — inline SVG candlesticks from invented example bars.
# ---------------------------------------------------------------------------

def svg_candles(bars, w=360, h=200) -> str:
    if not bars:
        return ""
    hi = max(b[1] for b in bars)
    lo = min(b[2] for b in bars)
    span = (hi - lo) or 1.0
    pad = span * 0.08
    hi += pad
    lo -= pad
    span = hi - lo

    def y(price):
        return 8 + (hi - price) / span * (h - 16)

    n = len(bars)
    slot = (w - 16) / n
    bw = max(10.0, slot * 0.55)
    out = [f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" '
           f'aria-label="Candlestick illustration" style="max-width:100%;background:#0b1220;border-radius:10px">']
    for i, (o, hgh, low, c) in enumerate(bars):
        cx = 8 + slot * i + slot / 2
        up = c >= o
        color = "#22c55e" if up else "#ef4444"
        out.append(f'<line x1="{cx:.1f}" y1="{y(hgh):.1f}" x2="{cx:.1f}" y2="{y(low):.1f}" '
                   f'stroke="{color}" stroke-width="2"/>')
        top = y(max(o, c))
        height = max(2.0, abs(y(o) - y(c)))
        out.append(f'<rect x="{cx - bw / 2:.1f}" y="{top:.1f}" width="{bw:.1f}" height="{height:.1f}" '
                   f'fill="{color}" rx="2"/>')
    out.append("</svg>")
    return "".join(out)

# ---------------------------------------------------------------------------
# WEB UI
# ---------------------------------------------------------------------------

def _strategy_card(s: dict) -> str:
    r = s["rules"]
    return (
        f'<article class="card"><h3>{html.escape(s["name"])}</h3>'
        f'<p class="tags"><span>{html.escape(s["family"])}</span><span>{html.escape(s["difficulty"])}</span>'
        f'<span>{html.escape(s["timeframes"])}</span><span>{html.escape(s["markets"])}</span></p>'
        f'<p><b>The idea:</b> {html.escape(s["idea"])}</p>'
        f'<p><b>Classic textbook rules</b> (education, not a recommendation):<br>'
        f'▸ <b>Entry:</b> {html.escape(r["entry"])}<br>'
        f'▸ <b>Exit:</b> {html.escape(r["exit"])}<br>'
        f'▸ <b>Stop / invalidation:</b> {html.escape(r["stop"])}</p>'
        f'<p><b>Why people like it:</b> {html.escape(s["pros"])}</p>'
        f'<p><b>How it fails:</b> {html.escape(s["fails"])}</p>'
        f'<p class="warn"><b>Risk note:</b> {html.escape(s["risk"])}</p></article>')


LAB_JS = r"""
let liveTimer = null;
let liveBars = new Map();
let currentLabPayload = null;
let botTimer = null;
function labParams() {
  return {
    strategy: document.getElementById('lab_strategy').value,
    max_signals: parseInt(document.getElementById('lab_max_signals').value || '100', 10),
    horizon_bars: parseInt(document.getElementById('lab_horizon').value || '5', 10),
    round_trip_cost_bps: parseFloat(document.getElementById('lab_cost').value || '10')
  };
}
function fmtLab(v, suffix) {
  if (v === null || v === undefined) return 'n/a';
  return String(v) + (suffix || '');
}
function conditionLabel(sig) {
  if (!sig) return 'No data';
  if (sig.condition === 'long_condition') return 'LONG · buy-condition (mechanical)';
  if (sig.condition === 'short_condition') return 'SHORT · sell-condition (mechanical)';
  return 'No fresh trigger · ' + sig.bias.replaceAll('_', ' ');
}
function equitySpark(curve) {
  if (!curve || curve.length < 2) return 'n/a';
  const w = 120, h = 34;
  const vals = curve.map(function(p) { return p.equity; });
  const lo = Math.min.apply(null, vals), hi = Math.max.apply(null, vals);
  const span = (hi - lo) || 1;
  const pts = curve.map(function(p, i) {
    const x = (i / (curve.length - 1)) * w;
    const y = 3 + (hi - p.equity) / span * (h - 6);
    return x.toFixed(1) + ',' + y.toFixed(1);
  }).join(' ');
  const last = vals[vals.length - 1];
  const color = last >= 1 ? '#22c55e' : '#ef4444';
  return '<svg width="' + w + '" height="' + h + '" viewBox="0 0 ' + w + ' ' + h + '" role="img" aria-label="Backtest equity curve">' +
    '<polyline fill="none" stroke="' + color + '" stroke-width="2" points="' + pts + '"/></svg><br><small>×' + last + '</small>';
}
function showLab(data) {
  const summary = document.getElementById('lab_summary');
  const table = document.getElementById('lab_table');
  summary.textContent = '';
  table.textContent = '';
  if (data.error) { summary.textContent = 'Error: ' + data.error; return; }
  const title = document.createElement('p');
  title.textContent = 'Source: ' + data.source + ' · Strategy: ' + data.strategy_detail.name +
    (data.source_is_synthetic ? ' · SYNTHETIC validation data — not a real market' : ' · user-supplied market data');
  summary.appendChild(title);
  const note = document.createElement('p');
  note.className = 'warn';
  note.textContent = 'Mechanical indicator states only — not financial advice. Accuracy is historical, after the selected cost, with next-bar entry and no overlapping test trades.';
  summary.appendChild(note);
  const header = document.createElement('tr');
  ['Timeframe', 'Latest close', 'Mechanical condition', 'Tested', 'Accuracy', 'W / L', 'Avg net', 'Expectancy', 'Max DD', 'Walk-forward later expectancy', 'Tournament #1 here (historical fit)', 'Equity curve (test trades)'].forEach(function(txt) {
    const th = document.createElement('th'); th.textContent = txt; header.appendChild(th);
  });
  table.appendChild(header);
  (data.timeframes || []).forEach(function(frame) {
    const tr = document.createElement('tr');
    let cells;
    if (frame.status !== 'ok') {
      cells = [frame.timeframe, 'n/a', frame.reason || 'Insufficient data', '0', 'n/a', '0 / 0', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a', 'n/a'];
      cells.forEach(function(txt) { const td = document.createElement('td'); td.textContent = txt; tr.appendChild(td); });
    } else {
      const v = frame.historical_validation;
      const wf = frame.walk_forward || {};
      const later = wf.later_slice || {};
      const tour = (frame.strategy_tournament && frame.strategy_tournament.engines && frame.strategy_tournament.engines[0]) || {};
      cells = [frame.timeframe + ' (' + frame.bars + ' bars)', fmtLab(frame.snapshot.close),
        conditionLabel(frame.latest_signal), fmtLab(v.signals_tested), fmtLab(v.accuracy_pct, '%'),
        v.wins + ' / ' + v.losses, fmtLab(v.average_net_return_pct, '%'),
        fmtLab(v.expectancy_pct_per_trade, '%'), fmtLab(v.max_drawdown_pct, '%'),
        fmtLab(later.expectancy_pct_per_trade, '%') + ' (' + fmtLab(later.trades) + ' trades · ' + (wf.robustness_verdict || 'n/a') + ')',
        (tour.strategy_name || 'n/a') + ' · exp ' + fmtLab(tour.expectancy_pct_per_trade, '%') + ' · acc ' + fmtLab(tour.accuracy_pct, '%')];
      cells.forEach(function(txt) { const td = document.createElement('td'); td.textContent = txt; tr.appendChild(td); });
      const sparkTd = document.createElement('td'); sparkTd.innerHTML = equitySpark(v.equity_curve); tr.appendChild(sparkTd);
    }
    table.appendChild(tr);
  });
  const details = document.createElement('details');
  const sm = document.createElement('summary'); sm.textContent = 'Full JSON result'; details.appendChild(sm);
  const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
  summary.appendChild(details);
}
async function postLab(payload) {
  currentLabPayload = payload;
  const status = document.getElementById('lab_status');
  status.textContent = 'Analyzing all available timeframes and testing the requested historical signals…';
  const response = await fetch('/api/lab/analyze', {
    method: 'POST', headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(Object.assign({}, labParams(), payload))
  });
  const data = await response.json();
  showLab(data);
  status.textContent = response.ok ? 'Analysis complete.' : ('Analysis failed: ' + (data.error || response.status));
  return data;
}
async function runLabDemo() {
  const status = document.getElementById('lab_status');
  status.textContent = 'Running deterministic synthetic validation. This verifies the software, not market profitability…';
  try {
    const q = new URLSearchParams(labParams());
    const response = await fetch('/api/lab/demo?' + q.toString());
    const data = await response.json();
    showLab(data);
    status.textContent = response.ok ? 'Synthetic validation complete.' : ('Validation failed: ' + (data.error || response.status));
  } catch (e) { status.textContent = 'Validation failed: ' + e; }
}
function payloadFromText(text, sourceLabel) {
  const clean = (text || '').trim();
  if (!clean) throw new Error('No data supplied');
  try {
    const parsed = JSON.parse(clean);
    const bars = Array.isArray(parsed) ? parsed : (parsed.bars || parsed.data || parsed.candles);
    if (!Array.isArray(bars)) throw new Error('JSON must be an array or contain bars[]');
    return {bars: bars, source_label: sourceLabel};
  } catch (e) {
    if (String(e).includes('JSON must')) throw e;
    return {csv_text: clean, source_label: sourceLabel};
  }
}
async function analyzeLabText() {
  try { await postLab(payloadFromText(document.getElementById('lab_data').value, 'pasted user-supplied OHLCV data')); }
  catch (e) { document.getElementById('lab_status').textContent = 'Data error: ' + e.message; }
}
async function analyzeCurrentLab() {
  try {
    if (currentLabPayload) { await postLab(currentLabPayload); return; }
    await analyzeLabText();
  } catch (e) { document.getElementById('lab_status').textContent = 'Current-data analysis error: ' + e.message; }
}
async function analyzeLabFile(input) {
  if (!input.files || !input.files[0]) return;
  try {
    const text = await input.files[0].text();
    await postLab(payloadFromText(text, 'uploaded file: ' + input.files[0].name));
  } catch (e) { document.getElementById('lab_status').textContent = 'File error: ' + e.message; }
}

function feedSymbolValue() {
  const el = document.getElementById('lab_feed_symbol');
  return (el ? el.value : '').trim();
}
function barsFromBinance(rows) {
  if (!Array.isArray(rows)) throw new Error('Binance response was not a kline array');
  const now = Date.now();
  return rows.filter(function(r) { return Array.isArray(r) && Number(r[6] || 0) <= now; }).map(function(r) {
    return {t: Math.floor(Number(r[0]) / 1000), o: Number(r[1]), h: Number(r[2]), l: Number(r[3]), c: Number(r[4]), v: Number(r[5] || 0)};
  });
}
function barsFromKraken(parsed) {
  if (!parsed || parsed.error && parsed.error.length) throw new Error('Kraken error: ' + ((parsed && parsed.error || []).join('; ') || 'bad response'));
  const result = parsed.result || {};
  const pair = Object.keys(result).find(function(k) { return k !== 'last' && Array.isArray(result[k]); });
  if (!pair) throw new Error('Kraken response had no OHLC pair array');
  const rows = result[pair].slice(0, -1); // last candle is still forming
  return {pair: pair, bars: rows.map(function(r) {
    return {t: Number(r[0]), o: Number(r[1]), h: Number(r[2]), l: Number(r[3]), c: Number(r[4]), v: Number(r[6] || 0)};
  })};
}
async function connectPublicFeed() {
  const provider = document.getElementById('lab_feed_provider').value;
  const symbol = feedSymbolValue();
  const interval = document.getElementById('lab_feed_interval').value;
  const limit = Math.max(100, Math.min(1000, parseInt(document.getElementById('lab_feed_limit').value || '1000', 10)));
  const status = document.getElementById('lab_status');
  if (provider === 'custom') { await pollLabFeed(); return; }
  if (!symbol) { status.textContent = 'Enter a market symbol for the selected public adapter first.'; return; }
  try {
    status.textContent = 'Connecting your browser directly to the selected public market-data endpoint…';
    if (provider === 'binance') {
      const url = 'https://api.binance.com/api/v3/klines?symbol=' + encodeURIComponent(symbol.toUpperCase()) + '&interval=' + encodeURIComponent(interval) + '&limit=' + limit;
      const response = await fetch(url, {cache: 'no-store'});
      if (!response.ok) throw new Error('Binance returned HTTP ' + response.status);
      const bars = barsFromBinance(await response.json());
      if (bars.length < 60) throw new Error('Only ' + bars.length + ' completed bars returned');
      document.getElementById('paper_symbol').value = symbol.toUpperCase();
      await postLab({bars: bars, source_label: 'Binance public spot klines via browser (' + symbol.toUpperCase() + ' ' + interval + ', completed bars only)'});
    } else if (provider === 'kraken') {
      const minutes = {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440, '1w': 10080}[interval] || 60;
      const url = 'https://api.kraken.com/0/public/OHLC?pair=' + encodeURIComponent(symbol.toUpperCase()) + '&interval=' + minutes;
      const response = await fetch(url, {cache: 'no-store'});
      if (!response.ok) throw new Error('Kraken returned HTTP ' + response.status);
      const converted = barsFromKraken(await response.json());
      if (converted.bars.length < 60) throw new Error('Only ' + converted.bars.length + ' completed bars returned');
      document.getElementById('paper_symbol').value = converted.pair;
      await postLab({bars: converted.bars, source_label: 'Kraken public OHLC via browser (' + converted.pair + ' ' + interval + ', completed bars only)'});
    } else if (provider === 'stooq') {
      const url = 'https://stooq.com/q/d/l/?s=' + encodeURIComponent(symbol.toLowerCase()) + '&i=d';
      document.getElementById('lab_feed_url').value = url;
      document.getElementById('paper_symbol').value = symbol.toUpperCase();
      await pollLabFeed();
    }
    status.textContent = 'Real public market data updated in your browser at ' + new Date().toLocaleTimeString() + '. Verify symbol, adjustments, licensing and whether the venue is available in your region.';
  } catch (e) {
    status.textContent = 'Public feed error (CORS, symbol, regional availability or venue limit): ' + e.message;
  }
}
async function pollSelectedFeed() {
  const providerEl = document.getElementById('lab_feed_provider');
  if (providerEl && providerEl.value !== 'custom') { await connectPublicFeed(); return; }
  await pollLabFeed();
}
function feedProviderChanged() {
  const provider = document.getElementById('lab_feed_provider').value;
  const symbol = document.getElementById('lab_feed_symbol');
  if (provider === 'binance') symbol.value = 'BTCUSDT';
  else if (provider === 'kraken') symbol.value = 'XBTUSD';
  else if (provider === 'stooq') symbol.value = 'aapl.us';
  else symbol.value = '';
}
function applyMarketPreset() {
  const key = document.getElementById('lab_market_preset').value;
  const presets = {
    crypto_binance: {provider: 'binance', symbol: 'BTCUSDT', interval: '1m', paper: 'BTCUSDT', db: 'BTCUSDT', asset: 'crypto', name: 'Bitcoin / USDT'},
    crypto_kraken: {provider: 'kraken', symbol: 'XBTUSD', interval: '1m', paper: 'XBTUSD', db: 'XBTUSD', asset: 'crypto', name: 'Bitcoin / USD'},
    stock_us: {provider: 'stooq', symbol: 'aapl.us', interval: '1d', paper: 'AAPL.US', db: 'AAPL.US', asset: 'stock', name: 'Apple Inc.'},
    etf_us: {provider: 'stooq', symbol: 'spy.us', interval: '1d', paper: 'SPY.US', db: 'SPY.US', asset: 'etf', name: 'SPDR S&P 500 ETF'},
    index_spx: {provider: 'stooq', symbol: '^spx', interval: '1d', paper: 'SPX', db: '^SPX', asset: 'index', name: 'S&P 500 index'},
    fx_eurusd: {provider: 'stooq', symbol: 'eurusd', interval: '1d', paper: 'EURUSD', db: 'EURUSD', asset: 'currency', name: 'Euro / US dollar'},
    stock_uk: {provider: 'stooq', symbol: 'vod.uk', interval: '1d', paper: 'VOD.UK', db: 'VOD.UK', asset: 'stock', name: 'UK-listed example (verify symbol)'},
    stock_de: {provider: 'stooq', symbol: 'bmw.de', interval: '1d', paper: 'BMW.DE', db: 'BMW.DE', asset: 'stock', name: 'German-listed example (verify symbol)'}
  };
  const preset = presets[key];
  if (!preset) return;
  document.getElementById('lab_feed_provider').value = preset.provider;
  document.getElementById('lab_feed_symbol').value = preset.symbol;
  document.getElementById('lab_feed_interval').value = preset.interval;
  document.getElementById('paper_symbol').value = preset.paper;
  document.getElementById('bot_symbol').value = preset.paper;
  document.getElementById('db_symbol').value = preset.db;
  document.getElementById('db_asset_type').value = preset.asset;
  document.getElementById('db_name').value = preset.name;
  document.getElementById('db_timeframe').value = preset.interval;
  if (preset.asset === 'crypto') document.getElementById('bot_timeframe').value = '1m';
  document.getElementById('lab_status').textContent = 'Market preset loaded: ' + preset.name + ' via ' + preset.provider + '. This selects browser market DATA only; verify the symbol, adjustments, terms and regional availability. It does not open a broker/exchange account.';
}
function privateHeaders(extra) {
  const headers = Object.assign({}, extra || {});
  const token = localStorage.getItem('tradeatlas_access_token') || '';
  if (token) headers['X-TradeAtlas-Token'] = token;
  return headers;
}
function savePrivateToken(input) {
  localStorage.setItem('tradeatlas_access_token', input.value.trim());
  const status = document.getElementById('db_status');
  if (status) status.textContent = input.value.trim() ? 'Private token saved in this browser only.' : 'Private token cleared in this browser.';
}
async function paperApi(path, payload) {
  const init = payload === undefined ? {headers: privateHeaders()} : {method: 'POST', headers: privateHeaders({'Content-Type': 'application/json'}), body: JSON.stringify(payload)};
  const response = await fetch(path, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
  return data;
}
function showPaperWallet(data) {
  const out = document.getElementById('paper_out');
  const wallet = data.wallet || data;
  out.textContent = '';
  const summary = document.createElement('p');
  summary.textContent = 'PAPER ONLY · cash ' + wallet.cash + ' · equity ' + wallet.equity +
    ' · realized P/L ' + wallet.realized_pnl + ' · following ' + wallet.following + ' · halted ' + wallet.halted +
    ' · demo crypto balances ' + ((wallet.paper_asset_balances || []).map(function(b) { return b.asset + ' × ' + b.quantity + ' (≈' + b.paper_usd_value + ' PAPER_USD)'; }).join(', ') || 'none') +
    ' · YOUR external account mirror (not in paper equity) ' + ((((wallet.external_account_mirror || {}).balances || []).map(function(b) { return b.asset + ' × ' + b.quantity; }).join(', ')) || 'none') +
    ' · positions ' + ((wallet.positions || []).map(function(p) { return p.symbol + ' × ' + p.quantity + ' @ avg ' + p.average_cost; }).join(', ') || 'none');
  out.appendChild(summary);
  const details = document.createElement('details');
  const sm = document.createElement('summary'); sm.textContent = 'Paper wallet JSON'; details.appendChild(sm);
  const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
  out.appendChild(details);
}
async function loadPaperWallet() {
  const status = document.getElementById('paper_status');
  try { const data = await paperApi('/api/paper/wallet'); showPaperWallet(data); status.textContent = 'Paper wallet loaded. No real funds exist in TradeAtlas.'; }
  catch (e) { status.textContent = 'Paper wallet error: ' + e.message; }
}
async function paperReset() {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/reset', {starting_balance: parseFloat(document.getElementById('paper_start').value || '10000')});
    showPaperWallet(data); status.textContent = 'Paper wallet reset.';
  } catch (e) { status.textContent = 'Paper reset error: ' + e.message; }
}
async function paperConvert() {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/deposit-simulated', {
      asset: document.getElementById('paper_asset').value,
      crypto_amount: parseFloat(document.getElementById('paper_crypto_amount').value || '0'),
      usd_rate: parseFloat(document.getElementById('paper_usd_rate').value || '1')
    });
    showPaperWallet(data); status.textContent = 'Hypothetical conversion recorded. Nothing was sent, received or converted for real.';
  } catch (e) { status.textContent = 'Simulated conversion error: ' + e.message; }
}
async function paperRecordExternalBalance() {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/external-balance', {
      venue_label: document.getElementById('external_venue').value,
      asset: document.getElementById('external_asset').value,
      quantity: parseFloat(document.getElementById('external_quantity').value || '0'),
      usd_rate: parseFloat(document.getElementById('external_rate').value || '0')
    });
    showPaperWallet(data);
    status.textContent = 'External-account mirror updated. Nothing was transferred to TradeAtlas, and the balance is not verified or included in paper equity.';
  } catch (e) { status.textContent = 'External-account mirror error: ' + e.message; }
}
async function paperDepositBalance() {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/deposit-balance-simulated', {
      asset: document.getElementById('paper_asset').value,
      crypto_amount: parseFloat(document.getElementById('paper_crypto_amount').value || '0'),
      usd_rate: parseFloat(document.getElementById('paper_usd_rate').value || '1')
    });
    showPaperWallet(data); status.textContent = 'Imaginary demo balance credited. DO NOT send crypto anywhere — no deposit address exists and no blockchain transfer occurred.';
  } catch (e) { status.textContent = 'Simulated balance deposit error: ' + e.message; }
}
async function paperConvertBalance() {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/convert-balance-simulated', {
      asset: document.getElementById('paper_asset').value,
      crypto_amount: parseFloat(document.getElementById('paper_crypto_amount').value || '0'),
      usd_rate: parseFloat(document.getElementById('paper_usd_rate').value || '1'),
      fee_bps: parseFloat(document.getElementById('paper_fee').value || '10')
    });
    showPaperWallet(data); status.textContent = 'Imaginary balance converted to PAPER_USD inside the demo only. No real asset changed hands.';
  } catch (e) { status.textContent = 'Simulated balance conversion error: ' + e.message; }
}
async function paperWithdrawSimulated() {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/withdraw-simulated', {
      asset: document.getElementById('paper_asset').value,
      amount: parseFloat(document.getElementById('paper_crypto_amount').value || '0'),
      usd_rate: parseFloat(document.getElementById('paper_usd_rate').value || '1')
    });
    showPaperWallet(data); status.textContent = 'Simulated withdrawal recorded by removing imaginary units. Nothing was sent to a wallet, bank or exchange.';
  } catch (e) { status.textContent = 'Simulated withdrawal error: ' + e.message; }
}
async function paperTransferBot(direction) {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/transfer-bot-simulated', {
      direction: direction,
      amount: parseFloat(document.getElementById('paper_transfer_amount').value || '0')
    });
    showPaperWallet(data); showBot(data);
    status.textContent = 'Internal PAPER_USD transfer complete (' + direction + '). This moved imaginary numbers between two local simulations only.';
  } catch (e) { status.textContent = 'Simulated internal transfer error: ' + e.message; }
}
async function paperSetFollow(on) {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/follow', {following: !!on});
    showPaperWallet(data); status.textContent = on ? 'Paper following is ON. Only simulated spot actions can occur on a follow-step.' : 'Paper following paused.';
  } catch (e) { status.textContent = 'Paper follow error: ' + e.message; }
}
async function paperStop() {
  const status = document.getElementById('paper_status');
  try {
    const data = await paperApi('/api/paper/stop', {close_all: false});
    showPaperWallet(data); status.textContent = 'STOP: paper following is hard-halted. Existing paper positions remain until you simulate an exit.';
  } catch (e) { status.textContent = 'Paper stop error: ' + e.message; }
}
async function paperFollowStep() {
  const status = document.getElementById('paper_status');
  try {
    let payload = currentLabPayload;
    if (!payload) payload = payloadFromText(document.getElementById('lab_data').value, 'pasted data for paper follow');
    const body = Object.assign({}, payload, {
      symbol: document.getElementById('paper_symbol').value.trim(),
      timeframe: document.getElementById('paper_timeframe').value,
      strategy: document.getElementById('lab_strategy').value,
      allocation_pct: parseFloat(document.getElementById('paper_allocation').value || '10'),
      fee_bps: parseFloat(document.getElementById('paper_fee').value || '10'),
      drop_last_bar: document.getElementById('paper_drop_last').checked
    });
    if (!body.symbol) throw new Error('Enter the paper symbol first');
    const data = await paperApi('/api/paper/follow-step', body);
    showPaperWallet(data);
    status.textContent = 'Paper follow step: ' + data.action + ' on ' + data.latest_bar_time + '. No real order was sent.';
  } catch (e) { status.textContent = 'Paper follow-step error: ' + e.message; }
}

async function botApi(path, payload) {
  const init = payload === undefined ? {headers: privateHeaders()} : {method: 'POST', headers: privateHeaders({'Content-Type': 'application/json'}), body: JSON.stringify(payload)};
  const response = await fetch(path, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
  return data;
}
function showBot(data) {
  const out = document.getElementById('bot_out');
  if (!out) return;
  const bot = data.bot || data;
  const wallet = bot.wallet || {};
  out.textContent = '';
  const summary = document.createElement('p');
  summary.textContent = 'HALAL PAPER BOT · status ' + bot.status + ' · PAPER_USD equity ' + wallet.equity +
    ' · registered ' + Object.keys(bot.registry || {}).length + ' asset(s) · open paper positions ' +
    ((wallet.positions || []).length) + ' · drawdown ' + ((bot.risk || {}).drawdown_from_peak_pct ?? 'n/a') + '%' +
    ' · profile ' + ((bot.settings || {}).mode_profile || 'n/a') + ' · ' + ((bot.settings || {}).strategy || '') + ' / ' +
    ((bot.settings || {}).timeframe || '') + ' · entries today ' + (bot.entries_today ?? 0) +
    ' · manual tickets ' + ((bot.manual_tickets || []).length) + ' · live execution ' + bot.live_execution_enabled;
  out.appendChild(summary);
  const details = document.createElement('details');
  const sm = document.createElement('summary'); sm.textContent = 'Bot JSON (screen, positions, risk and decision log)'; details.appendChild(sm);
  const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
  out.appendChild(details);
}
async function loadBot() {
  const status = document.getElementById('bot_status');
  try { const data = await botApi('/api/bot'); showBot(data); status.textContent = 'Paper bot loaded. It can only open registered assets whose current halal evidence screen status is exactly pass.'; }
  catch (e) { status.textContent = 'Bot load error: ' + e.message; }
}
function halalProfileFromForm() {
  const numberOrNull = function(id) {
    const raw = document.getElementById(id).value.trim();
    return raw === '' ? null : Number(raw);
  };
  return {
    symbol: document.getElementById('halal_symbol').value.trim(),
    company_name: document.getElementById('halal_company').value.trim(),
    sector: document.getElementById('halal_sector').value.trim(),
    asset_type: document.getElementById('halal_asset_type').value,
    user_standard_allows_asset: document.getElementById('halal_user_allows').checked,
    spot_only: document.getElementById('halal_spot_only').checked,
    leverage_used: document.getElementById('halal_leverage').checked,
    interest_or_swap_involved: document.getElementById('halal_interest').checked,
    short_selling_used: document.getElementById('halal_shorting').checked,
    project_activity_reviewed: document.getElementById('halal_asset_specific_reviewed').checked,
    settlement_reviewed: document.getElementById('halal_settlement_reviewed').checked,
    spot_settlement_reviewed: document.getElementById('halal_settlement_reviewed').checked,
    delivery_or_possession_reviewed: document.getElementById('halal_asset_specific_reviewed').checked,
    swap_free: document.getElementById('halal_swap_free').checked,
    staking_or_lending_involved: document.getElementById('halal_staking').checked,
    gambling_activity_involved: document.getElementById('halal_gambling').checked,
    fund_uses_leverage_or_interest: document.getElementById('halal_fund_bad').checked,
    underlying_holdings_screen_status: document.getElementById('halal_underlying_status').value,
    review_expires_at: document.getElementById('halal_expires').value.trim(),
    core_business_prohibited: document.getElementById('halal_core_prohibited').checked,
    activities_reviewed: document.getElementById('halal_activities_reviewed').checked,
    prohibited_activities: document.getElementById('halal_activities').value.split(',').map(function(x) { return x.trim(); }).filter(Boolean),
    interest_bearing_debt_pct_of_market_cap: numberOrNull('halal_debt'),
    interest_bearing_cash_securities_pct_of_market_cap: numberOrNull('halal_cash_securities'),
    receivables_pct_of_market_cap: numberOrNull('halal_receivables'),
    non_compliant_income_pct_of_revenue: numberOrNull('halal_income'),
    dividend_per_share: numberOrNull('halal_dividend'),
    source_note: document.getElementById('halal_source').value.trim(),
    financials_as_of: document.getElementById('halal_asof').value.trim()
  };
}
async function screenHalalStock(register) {
  const status = document.getElementById('bot_status');
  try {
    const profile = halalProfileFromForm();
    const preset = document.getElementById('halal_preset').value;
    const data = register
      ? await botApi('/api/bot/register-stock', {profile: profile, preset: preset})
      : await botApi('/api/halal/screen', {profile: profile, preset: preset});
    if (register) showBot(data);
    const result = data.registration || data;
    status.textContent = 'Halal screen for ' + result.symbol + ': ' + result.status + '. This is not a fatwa/certification; missing data can never pass.';
    if (!register) {
      const out = document.getElementById('bot_out'); out.textContent = JSON.stringify(result, null, 2);
    }
  } catch (e) { status.textContent = 'Halal screen error: ' + e.message; }
}
async function botReset() {
  const status = document.getElementById('bot_status');
  try {
    const data = await botApi('/api/bot/reset', {
      starting_balance: Number(document.getElementById('bot_start_balance').value || 10000),
      preset: document.getElementById('halal_preset').value,
      settings: botSettingsFromForm()
    });
    showBot(data); status.textContent = 'Halal paper bot reset and stopped.';
  } catch (e) { status.textContent = 'Bot reset error: ' + e.message; }
}
function botSettingsFromForm() {
  return {
    mode_profile: document.getElementById('bot_mode_profile').value,
    strategy: document.getElementById('lab_strategy').value,
    timeframe: document.getElementById('bot_timeframe').value,
    allocation_pct: Number(document.getElementById('bot_allocation').value || 5),
    max_positions: Number(document.getElementById('bot_max_positions').value || 3),
    risk_per_trade_pct: Number(document.getElementById('bot_risk').value || 0.5),
    atr_stop_multiple: Number(document.getElementById('bot_atr_stop').value || 1.5),
    take_profit_r_multiple: Number(document.getElementById('bot_take_r').value || 1.5),
    trailing_stop_atr_multiple: Number(document.getElementById('bot_trail').value || 1.5),
    fee_bps: Number(document.getElementById('bot_fee').value || 10),
    slippage_bps: Number(document.getElementById('bot_slippage').value || 5),
    max_daily_loss_pct: Number(document.getElementById('bot_daily_loss').value || 2),
    max_equity_drawdown_pct: Number(document.getElementById('bot_drawdown').value || 6),
    max_trades_per_day: Number(document.getElementById('bot_max_trades_day').value || 20),
    max_holding_bars: Number(document.getElementById('bot_max_holding').value || 30),
    cooldown_bars: Number(document.getElementById('bot_cooldown').value || 3),
    min_atr_pct: Number(document.getElementById('bot_min_atr').value || 0.02),
    manual_confirmation_required: true,
    live_execution_enabled: false,
    allow_short: false
  };
}
async function botSetStatus(action) {
  const status = document.getElementById('bot_status');
  try {
    if (action === 'stop' && botTimer) toggleBotAuto();
    const data = action === 'stop'
      ? await botApi('/api/bot/stop', {close_all: false})
      : await botApi('/api/bot/status', {action: action, settings: botSettingsFromForm()});
    showBot(data);
    status.textContent = action === 'stop' ? 'STOP: paper bot is hard-stopped. Open paper positions are not magically sold unless a later priced close-all is requested.' : ('Bot status: ' + (data.bot || data).status + '.');
  } catch (e) { status.textContent = 'Bot status error: ' + e.message; }
}
async function botStep() {
  const status = document.getElementById('bot_status');
  try {
    let payload = currentLabPayload;
    if (!payload) payload = payloadFromText(document.getElementById('lab_data').value, 'pasted stock data for halal paper bot');
    const symbol = (document.getElementById('bot_symbol').value || document.getElementById('halal_symbol').value).trim().toUpperCase();
    if (!symbol) throw new Error('Enter the registered stock symbol first');
    const symbols = {}; symbols[symbol] = payload;
    const data = await botApi('/api/bot/step', {
      symbols: symbols, settings: botSettingsFromForm(),
      drop_last_bar: document.getElementById('bot_drop_last').checked
    });
    showBot(data);
    const decision = (data.decisions || [])[0] || {};
    status.textContent = 'Paper bot cycle ' + data.cycle + ': ' + (decision.action || 'no decision') + '. No real order was sent.';
    return data;
  } catch (e) { status.textContent = 'Bot cycle error: ' + e.message; }
}
function toggleBotAuto() {
  const button = document.getElementById('bot_auto_btn');
  const status = document.getElementById('bot_status');
  if (botTimer) {
    clearInterval(botTimer); botTimer = null; button.textContent = '▶ Auto paper cycles';
    status.textContent = 'Automatic paper cycles stopped in this browser tab.';
    return;
  }
  const seconds = Math.max(60, Number(document.getElementById('bot_poll_seconds').value || 60));
  const run = async function() { await pollSelectedFeed(); await botStep(); };
  run();
  botTimer = setInterval(run, seconds * 1000);
  button.textContent = '⏹ Stop auto paper cycles';
  status.textContent = 'Automatic PAPER cycles every ' + seconds + 's while this page stays open, aligned to completed minute bars. Start the bot first; a stopped/risk-halted bot will not enter, and no real order can be sent.';
}

async function dbApi(path, payload) {
  const init = payload === undefined ? {headers: privateHeaders()} : {method: 'POST', headers: privateHeaders({'Content-Type': 'application/json'}), body: JSON.stringify(payload)};
  const response = await fetch(path, init);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
  return data;
}
function showDb(data) {
  const out = document.getElementById('db_out'); if (!out) return;
  out.textContent = '';
  const summary = document.createElement('p');
  if (data.counts) summary.textContent = 'SQLite database · ' + data.counts.bars + ' bars · ' + data.counts.instruments + ' instruments · ' + data.counts.halal_profiles + ' halal profiles · ' + data.counts.research_runs + ' research runs';
  else if (data.leaderboard) summary.textContent = 'Pooled research run ' + data.run_id + ' complete. Read attempts beside every accuracy; no leaderboard is a future guarantee.';
  else summary.textContent = 'Database operation complete.';
  out.appendChild(summary);
  const details = document.createElement('details');
  const sm = document.createElement('summary'); sm.textContent = 'Database JSON'; details.appendChild(sm);
  const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
  out.appendChild(details);
}
async function loadDb() {
  const status = document.getElementById('db_status');
  try { const data = await dbApi('/api/db/stats'); showDb(data); status.textContent = 'Local market database loaded.'; }
  catch (e) { status.textContent = 'Database error: ' + e.message; }
}
async function seedDb() {
  const status = document.getElementById('db_status');
  try { const data = await dbApi('/api/db/seed', {}); showDb(data.stats || data); status.textContent = 'Bundled real historical samples imported into SQLite.'; }
  catch (e) { status.textContent = 'Seed error: ' + e.message; }
}
async function importCurrentToDb() {
  const status = document.getElementById('db_status');
  try {
    let payload = currentLabPayload;
    if (!payload) payload = payloadFromText(document.getElementById('lab_data').value, 'pasted bars for database');
    const symbol = document.getElementById('db_symbol').value.trim().toUpperCase();
    if (!symbol) throw new Error('Enter the database symbol first');
    const body = Object.assign({}, payload, {
      symbol: symbol,
      timeframe: document.getElementById('db_timeframe').value,
      source: document.getElementById('db_source').value.trim(),
      instrument: {
        symbol: symbol, name: document.getElementById('db_name').value.trim(),
        asset_type: document.getElementById('db_asset_type').value,
        exchange: document.getElementById('db_exchange').value.trim(),
        currency: document.getElementById('db_currency').value.trim(),
        country: document.getElementById('db_country').value.trim(),
        sector: document.getElementById('halal_sector').value.trim()
      }
    });
    const data = await dbApi('/api/db/import-current', body);
    showDb(data); status.textContent = 'Stored ' + data.bars_imported_or_updated + ' bars for ' + data.symbol + ' ' + data.timeframe + '.';
  } catch (e) { status.textContent = 'Database import error: ' + e.message; }
}
async function runDbResearch() {
  const status = document.getElementById('db_status');
  try {
    status.textContent = 'Running hidden-future research on every stored series…';
    const data = await dbApi('/api/db/research', {attempts: Number(document.getElementById('db_attempts').value || 100)});
    showDb(data); status.textContent = 'Research stored. A pooled score is still historical and can be survivor/correlated-sample biased.';
  } catch (e) { status.textContent = 'Database research error: ' + e.message; }
}
async function saveHalalToDb() {
  const status = document.getElementById('db_status');
  try {
    const data = await dbApi('/api/db/halal-profile', {profile: halalProfileFromForm(), preset: document.getElementById('halal_preset').value, register_bot: true});
    showDb(data); showBot(data.bot_registration || data);
    status.textContent = 'Halal evidence saved. Status: ' + (data.registration || data).status + '. Not a fatwa/certification.';
  } catch (e) { status.textContent = 'Halal database error: ' + e.message; }
}
async function syncDbHalalToBot() {
  const status = document.getElementById('db_status');
  try { const data = await botApi('/api/bot/sync-halal-db', {}); showBot(data); status.textContent = 'Database halal profiles re-screened and synced to the paper bot registry.'; }
  catch (e) { status.textContent = 'Sync error: ' + e.message; }
}
function extractFeedBars(parsed) {
  if (Array.isArray(parsed)) return parsed;
  if (parsed && Array.isArray(parsed.bars)) return parsed.bars;
  if (parsed && Array.isArray(parsed.data)) return parsed.data;
  if (parsed && Array.isArray(parsed.candles)) return parsed.candles;
  return null;
}
async function pollLabFeed() {
  const url = document.getElementById('lab_feed_url').value.trim();
  const status = document.getElementById('lab_status');
  if (!url) { status.textContent = 'Enter your CORS-enabled JSON/CSV feed URL first.'; return; }
  try {
    const response = await fetch(url, {cache: 'no-store'});
    if (!response.ok) throw new Error('Feed returned HTTP ' + response.status);
    const text = await response.text();
    let payload;
    try {
      const parsed = JSON.parse(text);
      const incoming = extractFeedBars(parsed);
      if (!incoming) throw new Error('Feed JSON has no bars[] array');
      incoming.forEach(function(bar) {
        const key = bar.t || bar.time || bar.timestamp || bar.date || JSON.stringify(bar);
        liveBars.set(String(key), bar);
      });
      const merged = Array.from(liveBars.values()).slice(-20000);
      payload = {bars: merged, source_label: 'browser-polled user feed (' + merged.length + ' bars retained)'};
    } catch (jsonError) {
      payload = {csv_text: text, source_label: 'browser-polled user CSV feed'};
    }
    await postLab(payload);
    status.textContent = 'Live feed updated from your browser at ' + new Date().toLocaleTimeString() + '. Data rights/quality are yours to verify.';
  } catch (e) {
    status.textContent = 'Live feed error (often CORS or a paid/key-gated endpoint): ' + e.message;
  }
}
function toggleLabLive() {
  const btn = document.getElementById('lab_live_btn');
  if (liveTimer) {
    clearInterval(liveTimer); liveTimer = null; btn.textContent = '▶ Start browser live polling';
    document.getElementById('lab_status').textContent = 'Live polling stopped.'; return;
  }
  const seconds = Math.max(5, parseInt(document.getElementById('lab_poll_seconds').value || '30', 10));
  pollSelectedFeed();
  liveTimer = setInterval(pollSelectedFeed, seconds * 1000);
  btn.textContent = '⏹ Stop live polling';
}
async function analyzeWatchlist(input) {
  const status = document.getElementById('watch_status');
  const out = document.getElementById('watch_out');
  if (!input.files || !input.files.length) return;
  try {
    const symbols = {};
    for (const file of Array.from(input.files).slice(0, 12)) {
      const text = await file.text();
      const name = file.name.replace(/\.[^.]+$/, '').toUpperCase();
      try {
        const parsed = JSON.parse(text);
        symbols[name] = Array.isArray(parsed) ? parsed : (parsed.bars || parsed.data || parsed.candles || parsed);
      } catch (e) { symbols[name] = {csv: text}; }
    }
    status.textContent = 'Scanning ' + Object.keys(symbols).length + ' symbol file(s) across every honest timeframe…';
    const response = await fetch('/api/lab/watchlist', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({symbols: symbols, strategy: document.getElementById('lab_strategy').value})
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    out.textContent = '';
    const table = document.createElement('table');
    const header = document.createElement('tr');
    ['Symbol', '1m', '5m', '15m', '1h', '4h', '1d', '1w'].forEach(function(txt) {
      const th = document.createElement('th'); th.textContent = txt; header.appendChild(th);
    });
    table.appendChild(header);
    (data.symbols || []).forEach(function(row) {
      const tr = document.createElement('tr');
      const nameTd = document.createElement('td'); nameTd.textContent = row.symbol; tr.appendChild(nameTd);
      (row.timeframes || []).forEach(function(cell) {
        const td = document.createElement('td');
        if (cell.status !== 'ok') { td.textContent = '—'; td.title = cell.status; }
        else {
          td.textContent = (cell.condition === 'long_condition' ? 'LONG' : cell.condition === 'short_condition' ? 'SHORT' : 'bias ' + cell.bias_score) + ' · ' + cell.close;
          td.style.background = cell.condition === 'long_condition' ? '#14532d' : cell.condition === 'short_condition' ? '#7f1d1d' : cell.bias_score >= 2 ? '#164e2a' : cell.bias_score <= -2 ? '#5f1d1d' : '#0b1220';
          td.title = cell.bars + ' bars · window change ' + cell.change_over_window_pct + '%';
        }
        tr.appendChild(td);
      });
      table.appendChild(tr);
    });
    out.appendChild(table);
    (data.errors || []).forEach(function(err) {
      const p = document.createElement('p'); p.className = 'warn';
      p.textContent = err.symbol + ': ' + err.error; out.appendChild(p);
    });
    status.textContent = 'Watchlist scan complete. Heatmap only — run Market Lab per symbol for the 100-signal validation. Not financial advice.';
  } catch (e) { status.textContent = 'Watchlist error: ' + e.message; }
}
async function loadGoals() {
  const out = document.getElementById('goals_out');
  if (!out) return;
  out.textContent = 'Loading project goals…';
  try {
    const response = await fetch('/api/goals');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    out.textContent = '';
    const list = document.createElement('ul');
    (data.goals || []).forEach(function(goal) {
      const li = document.createElement('li');
      li.textContent = goal.title + ' — ' + goal.status;
      list.appendChild(li);
    });
    out.appendChild(list);
    const details = document.createElement('details');
    const sm = document.createElement('summary'); sm.textContent = 'Project goals JSON'; details.appendChild(sm);
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
    out.appendChild(details);
  } catch (e) { out.textContent = 'Goals error: ' + e.message; }
}
async function runMinuteForecast() {
  const status = document.getElementById('minute_status');
  const out = document.getElementById('minute_out');
  const verdict = document.getElementById('minute_verdict');
  try {
    const base = currentLabPayload || payloadFromText(
      document.getElementById('lab_data').value, 'pasted minute bars');
    const horizons = document.getElementById('minute_horizons').value
      .split(',').map(function(x) { return parseInt(x.trim(), 10); })
      .filter(function(x) { return Number.isFinite(x) && x > 0; }).slice(0, 10);
    if (!horizons.length) throw new Error('Enter at least one horizon');
    const payload = Object.assign({}, base, {
      attempts: parseInt(document.getElementById('minute_attempts').value || '1000', 10),
      horizons: horizons
    });
    status.textContent = 'Running the causal hidden-future minute race. This can take a while on large files…';
    const response = await fetch('/api/lab/minute-forecast', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    out.textContent = '';
    const table = document.createElement('table');
    const header = document.createElement('tr');
    ['Horizon', 'Atlas Minute Pulse', 'Pulse selective ≥0.45', 'EMA ribbon', '1-bar momentum'].forEach(function(txt) {
      const th = document.createElement('th'); th.textContent = txt; header.appendChild(th);
    });
    table.appendChild(header);
    (data.horizons || []).forEach(function(row) {
      const tr = document.createElement('tr');
      const methods = row.methods || {};
      const cell = function(m) {
        if (!m || !m.attempts_made) return 'n/a';
        return m.direction_accuracy_pct + '% · n=' + m.attempts_made + ' · coverage ' + m.coverage_pct +
          '% · 10bps ' + m.mean_net_pct_per_trade_10bps + '%/trade · CI [' + m.wilson_95_ci_pct.join(', ') + ']';
      };
      [('+' + row.horizon_bars + ' bars'), cell(methods.atlas_minute_pulse),
       cell(methods.atlas_minute_pulse_selective), cell(methods.minute_ema_ribbon),
       cell(methods.momentum_1bar)].forEach(function(txt) {
        const td = document.createElement('td'); td.textContent = txt; tr.appendChild(td);
      });
      table.appendChild(tr);
    });
    out.appendChild(table);
    const goal = data.goal_80_assessment || {};
    verdict.textContent = '80% goal assessment: ' + goal.status + ' · goal_established=' + goal.goal_established +
      '. A candidate on one series is not proof; external multi-symbol/day validation is still required.';
    const details = document.createElement('details');
    const sm = document.createElement('summary'); sm.textContent = 'Full minute-race JSON'; details.appendChild(sm);
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
    out.appendChild(details);
    status.textContent = 'Minute race done on ' + data.bars + ' supplied bars. Historical measurement only — not a live accuracy promise.';
  } catch (e) { status.textContent = 'Minute race error: ' + e.message; }
}
const SC_CAUSE_SEVERITY = {blocker: 'BLOCKER', warning: 'warning', goal_gap: 'goal gap'};
function scCell(text) { const td = document.createElement('td'); td.textContent = text; return td; }
function scTable(rows) {
  const table = document.createElement('table');
  rows.forEach(function(cells, index) {
    const tr = document.createElement('tr');
    cells.forEach(function(text) {
      if (index === 0) { const th = document.createElement('th'); th.textContent = text; tr.appendChild(th); }
      else { tr.appendChild(scCell(text)); }
    });
    table.appendChild(tr);
  });
  return table;
}
function scShowResult(data) {
  const out = document.getElementById('sc_out');
  out.textContent = '';
  (data.rounds || []).forEach(function(round) {
    const h = document.createElement('h4');
    h.textContent = 'Round ' + round.round + ' — ' + round.name +
      ' · candidates ' + (round.candidates || []).length +
      ' · retired ' + (round.retired || []).length;
    out.appendChild(h);
    const rows = [['Candidate', 'Accuracy', 'n / coverage', 'Mean net', 'Status', 'Causes']];
    (round.candidates || []).forEach(function(row) {
      const acc = row.direction_accuracy_pct == null ? '—' : row.direction_accuracy_pct + '%';
      const net = row.mean_net_pct == null ? '—' : row.mean_net_pct + '%';
      rows.push([row.method + ' @' + row.horizon_bars,
                 acc,
                 (row.attempts_made ?? '—') + ' / ' + (row.coverage_pct ?? '—') + '%',
                 net, row.status,
                 (row.blockers || []).join(', ') || (row.causes || []).map(function(c) { return c.id; }).join(', ') || '—']);
    });
    out.appendChild(scTable(rows));
    if ((round.lessons || []).length) {
      const ul = document.createElement('ul');
      (round.lessons || []).forEach(function(lesson) {
        const li = document.createElement('li');
        li.textContent = '[' + (SC_CAUSE_SEVERITY[lesson.severity] || lesson.severity) + '] ' +
          lesson.method + ' @' + lesson.horizon_bars + ' — ' + lesson.title +
          ' · ' + lesson.evidence + ' · avoid: ' + lesson.avoid +
          (lesson.status ? ' · lesson ' + lesson.status : '');
        ul.appendChild(li);
      });
      out.appendChild(ul);
    }
  });
  if ((data.retired_candidates || []).length) {
    const details = document.createElement('details');
    const sm = document.createElement('summary');
    sm.textContent = 'Retired candidates and why (' + data.retired_candidates.length + ')';
    details.appendChild(sm);
    const ul = document.createElement('ul');
    data.retired_candidates.forEach(function(item) {
      const li = document.createElement('li');
      li.textContent = item.method + ' @' + item.horizon_bars + ' — ' + item.cause + ': ' + item.reason;
      ul.appendChild(li);
    });
    details.appendChild(ul);
    out.appendChild(details);
  }
  if ((data.resolved_lessons || []).length) {
    const details = document.createElement('details');
    const sm = document.createElement('summary');
    sm.textContent = 'Lessons whose remedy worked (' + data.resolved_lessons.length + ')';
    details.appendChild(sm);
    const ul = document.createElement('ul');
    data.resolved_lessons.forEach(function(item) {
      const li = document.createElement('li');
      li.textContent = item.method + ' @' + item.horizon_bars + ' — ' + item.cause +
        ' fixed in round ' + item.resolved_in_round + ' (' + item.remedy + ')';
      ul.appendChild(li);
    });
    details.appendChild(ul);
    out.appendChild(details);
  }
  if ((data.next_actions || []).length) {
    const p = document.createElement('p');
    p.className = 'warn';
    p.textContent = 'Next actions: ' + data.next_actions.join(' ');
    out.appendChild(p);
  }
  const details = document.createElement('details');
  const sm = document.createElement('summary'); sm.textContent = 'Full self-correction JSON'; details.appendChild(sm);
  const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
  out.appendChild(details);
}
async function runSelfCorrection() {
  const status = document.getElementById('sc_status');
  const verdict = document.getElementById('sc_verdict');
  try {
    const base = currentLabPayload || payloadFromText(
      document.getElementById('lab_data').value, 'pasted bars (self-correction)');
    const horizons = document.getElementById('sc_horizons').value.split(',')
      .map(function(x) { return parseInt(x.trim(), 10); })
      .filter(function(x) { return Number.isFinite(x) && x > 0; });
    if (!horizons.length) throw new Error('Enter at least one horizon');
    const payload = Object.assign({}, base, {
      attempts: parseInt(document.getElementById('sc_attempts').value || '120', 10),
      horizons: horizons,
      cost_bps: parseFloat(document.getElementById('sc_cost').value || '10'),
      remember: document.getElementById('sc_remember').checked,
      use_saved_lessons: document.getElementById('sc_use_saved').checked
    });
    const second = document.getElementById('sc_second_file');
    if (second && second.files && second.files.length) {
      const file = second.files[0];
      const text = await file.text();
      try {
        const parsed = JSON.parse(text);
        payload.second_bars = Array.isArray(parsed) ? parsed : (parsed.bars || parsed.data || parsed.candles || parsed);
      } catch (e) { payload.second_csv_text = text; }
      payload.second_symbol = 'browser file: ' + file.name;
    }
    status.textContent = 'Screening, diagnosing and re-testing with the remedies applied…';
    const response = await fetch('/api/lab/self-correct', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    scShowResult(data);
    verdict.textContent = 'Verdict: ' + data.verdict + ' · 80% goal established: ' +
      (data.goal_80 || {}).goal_established + ' · lessons: ' + (data.lessons || []).length +
      ' · retired: ' + (data.retired_candidates || []).length;
    status.textContent = 'Loop complete on ' + (data.sources || []).length + ' series. ' +
      ((data.memory || {}).lessons_saved ? 'Saved ' + data.memory.lessons_saved + ' lessons to SQLite.' : 'Lesson ledger not saved.');
  } catch (e) { status.textContent = 'Self-correction error: ' + e.message; }
}
async function runSelfCorrectionDemo() {
  const status = document.getElementById('sc_status');
  const verdict = document.getElementById('sc_verdict');
  try {
    status.textContent = 'Running the deterministic synthetic software check…';
    const response = await fetch('/api/lab/self-correct', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({demo: true, remember: false})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    scShowResult(data);
    verdict.textContent = 'Synthetic demo (software check only, never market evidence) · verdict: ' + data.verdict;
    status.textContent = 'Synthetic demo complete. These prices are invented with a fixed seed.';
  } catch (e) { status.textContent = 'Demo error: ' + e.message; }
}
async function loadLessons() {
  const status = document.getElementById('sc_status');
  const out = document.getElementById('sc_out');
  try {
    status.textContent = 'Loading the persisted failure memory…';
    const response = await fetch('/api/lessons?limit=200');
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    out.textContent = '';
    const head = document.createElement('p');
    head.className = 'sub';
    head.textContent = data.count + ' stored lesson(s). Every lesson keeps the failure reason, ' +
      'the avoid-rule for the next test and its status (observed / resolved / recurred / retired).';
    out.appendChild(head);
    const rows = [['Cause', 'Lessons', 'Resolved', 'Recurred', 'Retired']];
    (data.tally || []).forEach(function(item) {
      rows.push([item.cause + ' (' + item.severity + ')', item.lessons, item.resolved, item.recurred, item.retired]);
    });
    if (rows.length > 1) out.appendChild(scTable(rows));
    const detailRows = [['Candidate', 'Cause', 'Status', 'Avoid rule for the next test']];
    (data.lessons || []).slice(0, 60).forEach(function(lesson) {
      detailRows.push([lesson.method + ' @' + lesson.horizon_bars, lesson.cause,
                       lesson.status, lesson.avoid]);
    });
    if (detailRows.length > 1) out.appendChild(scTable(detailRows));
    const details = document.createElement('details');
    const sm = document.createElement('summary'); sm.textContent = 'Cause library + full ledger JSON'; details.appendChild(sm);
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
    out.appendChild(details);
    status.textContent = 'Failure memory loaded.';
  } catch (e) { status.textContent = 'Lesson ledger error: ' + e.message; }
}
function todayUtc(seconds) {
  if (!seconds) return '—';
  return new Date(seconds * 1000).toISOString().replace('.000Z', 'Z');
}
function todayIntervalMinutes(interval) {
  return {'1m': 1, '5m': 5, '15m': 15, '1h': 60, '4h': 240, '1d': 1440, '1w': 10080}[interval] || 60;
}
async function fetchBinanceToday(symbol, interval, limit) {
  const hosts = ['https://data-api.binance.vision', 'https://api.binance.com'];
  let lastError = null;
  for (const host of hosts) {
    try {
      const url = host + '/api/v3/klines?symbol=' + encodeURIComponent(symbol.toUpperCase()) +
        '&interval=' + encodeURIComponent(interval) + '&limit=' + Math.max(200, Math.min(1000, limit));
      const response = await fetch(url, {cache: 'no-store'});
      if (!response.ok) throw new Error('HTTP ' + response.status);
      const rows = await response.json();
      // barsFromBinance keeps only rows whose closeTime is already past (completed bars)
      const bars = barsFromBinance(rows);
      if (bars.length < 200) throw new Error('only ' + bars.length + ' completed bars');
      return {bars: bars, host: host, url: url, venue: 'Binance spot public klines'};
    } catch (e) { lastError = e; }
  }
  throw lastError || new Error('Binance fetch failed');
}
async function fetchKrakenToday(symbol, interval, limit) {
  const minutes = todayIntervalMinutes(interval);
  const url = 'https://api.kraken.com/0/public/OHLC?pair=' + encodeURIComponent(symbol.toUpperCase()) +
    '&interval=' + minutes;
  const response = await fetch(url, {cache: 'no-store'});
  if (!response.ok) throw new Error('Kraken returned HTTP ' + response.status);
  const converted = barsFromKraken(await response.json());
  const bars = converted.bars.slice(-Math.max(200, Math.min(720, limit)));
  if (bars.length < 200) throw new Error('only ' + bars.length + ' completed bars');
  return {bars: bars, host: 'api.kraken.com', url: url, venue: 'Kraken public OHLC',
          symbol: converted.pair};
}
function showTodayProvenance(provenance) {
  const box = document.getElementById('today_provenance');
  box.style.display = 'block';
  box.textContent = '';
  const rows = [['Field', 'Value'],
    ['Venue', provenance.venue],
    ['Primary symbol', provenance.primary_symbol],
    ['Validation symbol', provenance.validation_symbol || 'not supplied'],
    ['Interval', provenance.interval],
    ['Completed bars (primary / validation)', provenance.primary_bars + ' / ' + (provenance.validation_bars ?? '—')],
    ['First bar (UTC)', provenance.first_bar_utc],
    ['Last completed bar (UTC)', provenance.last_bar_utc],
    ['Fetched at (UTC)', provenance.fetched_at_utc],
    ['Forming candle dropped', String(provenance.forming_candle_dropped)],
    ['Primary endpoint', provenance.primary_url]];
  rows.forEach(function(cells, index) {
    const tr = document.createElement('tr');
    cells.forEach(function(text) {
      if (index === 0) { const th = document.createElement('th'); th.textContent = text; tr.appendChild(th); }
      else { const td = document.createElement('td'); td.textContent = String(text); tr.appendChild(td); }
    });
    box.appendChild(tr);
  });
}
async function runTodayMarketTest() {
  const status = document.getElementById('today_status');
  const verdict = document.getElementById('sc_verdict');
  const out = document.getElementById('sc_out');
  const venue = document.getElementById('today_venue').value;
  const symbol = (document.getElementById('today_symbol').value || '').trim();
  const symbol2 = (document.getElementById('today_symbol2').value || '').trim();
  const interval = document.getElementById('today_interval').value;
  const limit = Math.max(405, Math.min(1000, parseInt(document.getElementById('today_limit').value || '1000', 10)));
  const costBps = parseFloat(document.getElementById('today_cost').value || '12');
  if (!symbol) { status.textContent = 'Enter a primary symbol first.'; return; }
  const fetchedAt = new Date().toISOString();
  try {
    status.textContent = 'Fetching completed ' + interval + ' bars directly from ' + venue + ' in your browser…';
    const fetcher = venue === 'kraken' ? fetchKrakenToday : fetchBinanceToday;
    const primary = await fetcher(symbol, interval, limit);
    let secondary = null;
    let secondaryError = '';
    if (symbol2) {
      try {
        secondary = await fetcher(symbol2, interval, limit);
      } catch (e) { secondaryError = e.message; }
    }
    if (primary.bars.length < 405) throw new Error('primary returned only ' + primary.bars.length + ' completed bars; ask for more or use a coarser interval');
    const lastBar = primary.bars[primary.bars.length - 1].t;
    const firstBar = primary.bars[0].t;
    const provenance = {
      venue: primary.venue,
      primary_symbol: primary.symbol || symbol.toUpperCase(),
      validation_symbol: secondary ? (secondary.symbol || symbol2.toUpperCase()) : null,
      interval: interval,
      primary_bars: primary.bars.length,
      validation_bars: secondary ? secondary.bars.length : null,
      first_bar_utc: todayUtc(firstBar),
      last_bar_utc: todayUtc(lastBar),
      fetched_at_utc: fetchedAt,
      forming_candle_dropped: true,
      primary_url: primary.url,
      validation_url: secondary ? secondary.url : null,
      validation_error: secondaryError || null,
      requested_bars: limit
    };
    showTodayProvenance(provenance);
    const series = [{
      symbol: (venue === 'kraken' ? 'KRAKEN-' : 'BINANCE-') + (primary.symbol || symbol.toUpperCase()) + '@' + interval,
      bars: primary.bars
    }];
    if (secondary) {
      series.push({
        symbol: (venue === 'kraken' ? 'KRAKEN-' : 'BINANCE-') + (secondary.symbol || symbol2.toUpperCase()) + '@' + interval,
        bars: secondary.bars
      });
    }
    status.textContent = 'Fetched ' + primary.bars.length + (secondary ? ' + ' + secondary.bars.length : '') +
      ' completed bars. Running the diagnosis / remedy / validation loop with ' + costBps + ' bps costs…';
    const payload = {
      bars: primary.bars,
      symbol: series[0].symbol,
      second_bars: secondary ? secondary.bars : null,
      second_symbol: secondary ? series[1].symbol : null,
      horizons: [3, 5, 15],
      attempts: 150,
      cost_bps: costBps,
      remember: true,
      use_saved_lessons: true,
      provenance: provenance,
      source_label: provenance.venue + ' via browser — ' + provenance.primary_symbol +
        (provenance.validation_symbol ? ' + ' + provenance.validation_symbol : '') +
        ' ' + interval + ' completed bars, fetched ' + fetchedAt
    };
    const response = await fetch('/api/lab/self-correct', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    scShowResult(data);
    const sources = (data.sources || []).length;
    verdict.textContent = 'TODAY · ' + provenance.venue + ' · ' + provenance.primary_symbol +
      (provenance.validation_symbol ? ' + ' + provenance.validation_symbol : '') + ' · ' + interval +
      ' · last completed bar ' + provenance.last_bar_utc + ' · verdict: ' + data.verdict +
      ' · 80% goal established: ' + ((data.goal_80 || {}).goal_established) +
      ' · lessons ' + (data.lessons || []).length + ' · retired ' + (data.retired_candidates || []).length +
      ' · series ' + sources;
    status.textContent = 'Done. ' + ((data.memory || {}).lessons_saved ? 'Saved ' + data.memory.lessons_saved +
      ' lessons to the local failure memory.' : 'Lesson ledger not saved.') +
      ' Historical measurement on completed bars only — not a prediction and not advice.';
  } catch (e) {
    status.textContent = 'Today-market test error (' + (venue === 'kraken' ? 'Kraken' : 'Binance') +
      ' may be blocked by your region, browser extension or CORS): ' + e.message +
      ' — you can still paste/upload a CSV of today\'s bars in the Market Lab and run card 5C on it.';
  }
}
function pipelinePlanValues() {
  const symbols = (document.getElementById('pl_symbols').value || '')
    .split(',').map(function(x) { return x.trim(); }).filter(Boolean);
  return {
    venue: document.getElementById('pl_venue').value,
    symbols: symbols,
    interval: document.getElementById('pl_interval').value,
    target_bars: parseInt(document.getElementById('pl_target').value || '3000', 10),
    cost_bps: parseFloat(document.getElementById('pl_cost').value || '12')
  };
}
function plStatus(text) { const el = document.getElementById('pl_status'); if (el) el.textContent = text; }
function plRenderProgress(data) {
  const box = document.getElementById('pl_progress');
  if (!box) return;
  box.textContent = '';
  const best = data.best_pooled_candidate || {};
  const accuracy = typeof best.accuracy_pct === 'number' ? best.accuracy_pct : 0;
  const wrap = document.createElement('div');
  wrap.style.background = '#0b1220';
  wrap.style.border = '1px solid #334155';
  wrap.style.borderRadius = '10px';
  wrap.style.padding = '10px';
  const label = document.createElement('p');
  label.className = 'sub';
  label.textContent = 'Best pooled candidate: ' +
    (best.method ? best.method + ' @' + best.horizon_bars + ' bars' : 'none yet') +
    ' · accuracy ' + (best.accuracy_pct ?? '—') + '% · Wilson ' +
    (best.wilson_95_ci_pct ? '[' + best.wilson_95_ci_pct.join(', ') + ']' : '—') +
    ' · attempts ' + (best.attempts ?? 0) +
    ' · distance to 80%: ' + (data.distance_to_target_points ?? '—') + ' points';
  wrap.appendChild(label);
  const track = document.createElement('div');
  track.style.height = '14px'; track.style.background = '#1e293b';
  track.style.borderRadius = '999px'; track.style.overflow = 'hidden';
  const fill = document.createElement('div');
  fill.style.height = '100%';
  fill.style.width = Math.max(2, Math.min(100, accuracy)) + '%';
  fill.style.background = accuracy >= 80 ? '#22c55e' : accuracy >= 60 ? '#f59e0b' : '#ef4444';
  track.appendChild(fill); wrap.appendChild(track);
  const gates = document.createElement('p');
  gates.className = 'warn';
  gates.textContent = 'Gates passed: ' + data.gates_passed + '/' + data.gates_total +
    ' · status ' + data.status + ' · goal established: ' + data.goal_established;
  wrap.appendChild(gates);
  const rows = [['Gate', 'Requirement', 'Measured', 'Passed']];
  (data.checks || []).forEach(function(check) {
    rows.push([check.gate, check.requirement, String(check.value), check.passed ? 'yes' : 'no']);
  });
  const table = document.createElement('table');
  rows.forEach(function(cells, index) {
    const tr = document.createElement('tr');
    cells.forEach(function(text) {
      if (index === 0) { const th = document.createElement('th'); th.textContent = text; tr.appendChild(th); }
      else { const td = document.createElement('td'); td.textContent = text; tr.appendChild(td); }
    });
    table.appendChild(tr);
  });
  wrap.appendChild(table);
  box.appendChild(wrap);
}
async function loadGoalProgress() {
  try {
    plStatus('Measuring pooled evidence across every stored series (tuning slices only)…');
    const response = await fetch('/api/goal-progress?cost_bps=' +
      encodeURIComponent(document.getElementById('pl_cost').value || '12'));
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    plRenderProgress(data);
    const out = document.getElementById('pl_out');
    out.textContent = '';
    const details = document.createElement('details');
    const sm = document.createElement('summary'); sm.textContent = 'Full goal-progress JSON'; details.appendChild(sm);
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
    out.appendChild(details);
    plStatus('Evidence: ' + data.evidence.series_used + ' series · ' +
      data.evidence.symbols.length + ' symbols · ' + data.evidence.distinct_days +
      ' distinct days · holdout evaluations ' + data.evidence.holdout_evaluations + '.');
  } catch (e) { plStatus('Goal progress error: ' + e.message); }
}
async function pipelineCollectServer() {
  try {
    const plan = pipelinePlanValues();
    plStatus('Server is fetching ' + plan.symbols.join(', ') + ' from ' + plan.venue +
      ' — it only contacts the allowlisted public hosts…');
    const response = await fetch('/api/pipeline/collect', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(plan)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    const out = document.getElementById('pl_out');
    out.textContent = '';
    const rows = [['Stored symbol', 'New bars', 'Total bars', 'First bar', 'Last bar', 'Errors']];
    (data.series || []).forEach(function(item) {
      rows.push([item.symbol, item.inserted, item.stored_total, item.first_bar || '—',
                 item.last_bar || '—', (item.errors || []).join('; ') || 'none']);
    });
    const table = document.createElement('table');
    rows.forEach(function(cells, index) {
      const tr = document.createElement('tr');
      cells.forEach(function(text) {
        if (index === 0) { const th = document.createElement('th'); th.textContent = text; tr.appendChild(th); }
        else { const td = document.createElement('td'); td.textContent = String(text); tr.appendChild(td); }
      });
      table.appendChild(tr);
    });
    out.appendChild(table);
    plStatus('Collected ' + data.inserted_total + ' new bars. ' +
      (data.inserted_total ? 'Now grade them, then refresh goal progress.' :
       'No new bars: your server may have no outbound network — use the browser collector.'));
  } catch (e) { plStatus('Server collection error: ' + e.message); }
}
async function pipelineCollectBrowser() {
  try {
    const plan = pipelinePlanValues();
    if (!plan.symbols.length) throw new Error('Add at least one symbol');
    const fetcher = plan.venue === 'kraken' ? fetchKrakenToday : fetchBinanceToday;
    const series = [];
    for (const symbol of plan.symbols) {
      plStatus('Fetching ' + symbol + ' ' + plan.interval + ' in your browser…');
      try {
        const page = await fetcher(symbol, plan.interval, 1000);
        series.push({symbol: symbol.toUpperCase(), interval: plan.interval,
                     bars: page.bars, endpoint: page.url,
                     source_label: page.venue + ' via browser (allowlisted venue)'});
      } catch (e) { plStatus('Skipped ' + symbol + ': ' + e.message); }
    }
    if (!series.length) throw new Error('No series could be fetched — venue blocked, or symbol unknown');
    plStatus('Posting ' + series.length + ' fetched series to be stored in SQLite…');
    const response = await fetch('/api/pipeline/import', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({venue: plan.venue, series: series,
                            provenance: {venue: plan.venue, interval: plan.interval,
                                         fetched_at_utc: new Date().toISOString(),
                                         forming_candle_dropped: true,
                                         symbols: series.map(function(x) { return x.symbol; })}})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    const out = document.getElementById('pl_out');
    out.textContent = '';
    const rows = [['Stored symbol', 'Bars', 'First bar', 'Last bar']];
    (data.series || []).forEach(function(item) {
      rows.push([item.symbol, item.stored_total, item.first_bar || '—', item.last_bar || '—']);
    });
    const table = document.createElement('table');
    rows.forEach(function(cells, index) {
      const tr = document.createElement('tr');
      cells.forEach(function(text) {
        if (index === 0) { const th = document.createElement('th'); th.textContent = text; tr.appendChild(th); }
        else { const td = document.createElement('td'); td.textContent = String(text); tr.appendChild(td); }
      });
      table.appendChild(tr);
    });
    out.appendChild(table);
    plStatus('Stored ' + data.series.length + ' series. Now grade everything stored.');
  } catch (e) { plStatus('Browser collection error: ' + e.message); }
}
async function runAutoResearch() {
  try {
    plStatus('Grading every stored series on its tuning slice (holdout untouched)…');
    const plan = pipelinePlanValues();
    const response = await fetch('/api/lab/auto-research', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({horizons: [3, 5, 15], attempts: 150, cost_bps: plan.cost_bps})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    plRenderProgress(data);
    const out = document.getElementById('pl_out');
    out.textContent = '';
    const rows = [['Method', 'Horizon', 'Attempts', 'Accuracy', 'Wilson low', 'Net @cost', 'Symbols']];
    (data.pooled || []).forEach(function(row) {
      rows.push([row.method, row.horizon_bars, row.attempts, row.accuracy_pct,
                 (row.wilson_95_ci_pct || [])[0], row.mean_net_pct, row.series_count]);
    });
    if (rows.length > 1) {
      const table = document.createElement('table');
      rows.forEach(function(cells, index) {
        const tr = document.createElement('tr');
        cells.forEach(function(text) {
          if (index === 0) { const th = document.createElement('th'); th.textContent = text; tr.appendChild(th); }
          else { const td = document.createElement('td'); td.textContent = String(text); tr.appendChild(td); }
        });
        table.appendChild(tr);
      });
      out.appendChild(table);
    }
    plStatus('Graded ' + data.evidence.series_used + ' series. Top row is the selection maximum — read the Wilson interval, not the point estimate.');
  } catch (e) { plStatus('Auto-research error: ' + e.message); }
}
async function runHoldout() {
  try {
    const symbol = (document.getElementById('pl_holdout_symbol').value || '').trim();
    if (!symbol) throw new Error('Enter a stored symbol');
    plStatus('Reading the reserved holdout for ' + symbol + ' (this read is recorded)…');
    const response = await fetch('/api/lab/holdout', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({symbol: symbol, horizons: [3, 5, 15],
                            cost_bps: parseFloat(document.getElementById('pl_cost').value || '12')})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    const out = document.getElementById('pl_out');
    out.textContent = '';
    const rows = [['Method', 'Horizon', 'Attempts', 'Accuracy', 'Wilson low', 'Net']];
    (data.rows || []).forEach(function(row) {
      rows.push([row.method, row.horizon_bars, row.attempts_made, row.direction_accuracy_pct,
                 (row.wilson_95_ci_pct || [])[0], row.mean_net_pct]);
    });
    const table = document.createElement('table');
    rows.forEach(function(cells, index) {
      const tr = document.createElement('tr');
      cells.forEach(function(text) {
        if (index === 0) { const th = document.createElement('th'); th.textContent = text; tr.appendChild(th); }
        else { const td = document.createElement('td'); td.textContent = String(text); tr.appendChild(td); }
      });
      table.appendChild(tr);
    });
    out.appendChild(table);
    plStatus('Holdout: ' + data.holdout_bars + ' reserved bars (' + data.holdout_first_bar +
      ' → ' + data.holdout_last_bar + '). Reads so far: ' + data.holdout_uses_total +
      '. Repeating this turns the holdout into tuning data.');
  } catch (e) { plStatus('Holdout error: ' + e.message); }
}
async function clearLessons() {
  const status = document.getElementById('sc_status');
  if (!confirm('Delete every stored lesson? They record measured failures, not signals. Clear only with genuinely new data or methods.')) return;
  try {
    const response = await fetch('/api/lessons/clear', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({})});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    status.textContent = 'Cleared ' + data.cleared + ' stored lesson(s).';
  } catch (e) { status.textContent = 'Clear error: ' + e.message; }
}
async function analyzeForecast(input) {
  const status = document.getElementById('fc_status');
  const out = document.getElementById('fc_out');
  const verdictEl = document.getElementById('fc_verdict');
  try {
    let payload;
    if (input && input.files && input.files.length) {
      const file = input.files[0];
      const text = await file.text();
      payload = {source_label: 'browser file upload (Forecast Lab): ' + file.name,
        attempts: parseInt(document.getElementById('fc_attempts').value || '100', 10),
        horizon: parseInt(document.getElementById('fc_horizon').value || '5', 10)};
      try {
        const parsed = JSON.parse(text);
        payload.bars = Array.isArray(parsed) ? parsed : (parsed.bars || parsed.data || parsed.candles || parsed);
      } catch (e) { payload.csv_text = text; }
    } else {
      const basePayload = currentLabPayload || payloadFromText(
        document.getElementById('lab_data').value, 'pasted data (Forecast Lab)');
      payload = Object.assign({}, basePayload, {
        attempts: parseInt(document.getElementById('fc_attempts').value || '100', 10),
        horizon: parseInt(document.getElementById('fc_horizon').value || '5', 10)});
      if (!payload.source_label) payload.source_label = 'currently analyzed data (Forecast Lab)';
    }
    status.textContent = 'Hiding the future and testing the requested analog forecasts out-of-sample…';
    const response = await fetch('/api/lab/forecast', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || ('HTTP ' + response.status));
    out.textContent = '';
    const rows = ((data.analog_now || {}).horizons || []).map(function(h) {
      return ['+' + h.horizon_bars + ' bars', String(h.n), (h.median_pct ?? '—') + '%',
              (h.p25_pct ?? '—') + '%', (h.p75_pct ?? '—') + '%', (h.share_up_pct ?? '—') + '%'];
    });
    const table = document.createElement('table');
    const header = document.createElement('tr');
    ['Horizon', 'Analogs', 'Median then', '25th pct then', '75th pct then', 'Were up then'].forEach(function(txt) {
      const th = document.createElement('th'); th.textContent = txt; header.appendChild(th);
    });
    table.appendChild(header);
    rows.forEach(function(cols) {
      const tr = document.createElement('tr');
      cols.forEach(function(v) { const td = document.createElement('td'); td.textContent = v; tr.appendChild(td); });
      table.appendChild(tr);
    });
    out.appendChild(table);
    const ev = data.rolling_eval || {};
    if (ev.error) { verdictEl.textContent = 'Rolling evaluation: ' + ev.error; }
    else {
      let txt = 'Out-of-sample test (' + ev.attempts_made + ' hidden-future attempts, horizon ' +
        ev.horizon_bars + ' bars): analog direction ' + ev.analog_direction_accuracy_pct + '% vs always-up ' +
        ev.baseline_always_up_pct + '%, naive momentum ' + ev.baseline_momentum_5bar_pct + '%, mean-reversion ' +
        ev.baseline_mean_reversion_5bar_pct + '% · Brier skill ' + ev.brier_skill_vs_climatology +
        ' → verdict: ' + ev.verdict + '. A forecaster that cannot beat these baselines on your own data is a coin with paperwork — believe the verdict, not the medians above.';
      const mh = (data.multi_horizon_eval || []).filter(function(r) { return !r.error; });
      if (mh.length) {
        txt += ' Multi-horizon analog accuracy: ' + mh.map(function(r) {
          return '+' + r.horizon_bars + ' bars ' + r.analog_direction_accuracy_pct + '% (always-up ' + r.baseline_always_up_pct + '%)';
        }).join(' · ') + '.';
      }
      const rg = ev.regimes || {};
      const rgParts = Object.keys(rg).map(function(k) {
        return k + ' ' + rg[k].analog_accuracy_pct + '% vs always-up ' + rg[k].always_up_pct + '% (n=' + rg[k].attempts + ')';
      });
      if (rgParts.length) txt += ' By regime: ' + rgParts.join(' · ') + '.';
      const ens = data.ensemble_eval || {};
      if (!ens.error && ens.direction_accuracy_pct) {
        const acc = ens.direction_accuracy_pct;
        txt += ' Ensemble race (same blind test): ' + Object.keys(acc).filter(function(k) { return acc[k] !== null; }).map(function(k) {
          return k + ' ' + acc[k] + '%';
        }).join(' · ') + ' — agreement filter covers only ' + ens.agreement_coverage_pct + '% of attempts, and the best of several variants on one sample is a hypothesis, not an edge.';
        const c10 = (ens.cost_analysis || [])[0];
        if (c10 && c10.majority_vote && c10.always_up_long) {
          txt += ' After ' + c10.round_trip_cost_bps + ' bps costs: majority vote nets ' + c10.majority_vote.mean_net_pct_per_trade + '%/trade (win ' + c10.majority_vote.win_rate_after_cost_pct + '%) vs always-long ' + c10.always_up_long.mean_net_pct_per_trade + '%/trade.';
        }
        if (c10 && c10.majority_vote_v3) {
          txt += ' v8 majority_vote_v3 nets ' + c10.majority_vote_v3.mean_net_pct_per_trade + '%/trade after the same costs';
          if (c10.consensus_3plus) txt += '; consensus_3plus nets ' + c10.consensus_3plus.mean_net_pct_per_trade + '%/trade but covers only ' + ens.consensus_3plus_coverage_pct + '% of attempts';
          txt += '.';
        }
        if (c10 && c10.multiscale_trend) {
          txt += ' v10 multiscale_trend nets ' + c10.multiscale_trend.mean_net_pct_per_trade + '%/trade after the same costs';
          if (c10.cycle_flow_analog_median) txt += ' (cycle/flow median ' + c10.cycle_flow_analog_median.mean_net_pct_per_trade + '%/trade; majority_vote_v5 ' + c10.majority_vote_v5.mean_net_pct_per_trade + '%/trade)';
          const mt = ((data.multiscale_trend_eval || {}).horizons || []).filter(function(r) { return !r.error; });
          if (mt.length) txt += '; multiscale by horizon: ' + mt.map(function(r) { return '+' + r.horizon_bars + ' bars ' + r.multiscale_direction_accuracy_pct + '% vs momentum ' + r.baseline_momentum_5bar_pct + '%'; }).join(' · ');
          const conf = (((ens.multiscale_confidence_coverage || {}).thresholds || []).find(function(r) { return r.absolute_score_at_least === 0.5; }) || {});
          if (conf.attempts) txt += '; |score|≥0.5 selective row: ' + conf.direction_accuracy_pct + '% on ' + conf.attempts + ' attempts (' + conf.coverage_pct + '% coverage — diagnostic only, never the headline)';
          txt += '.';
        }
        if (c10 && c10.kalman_trend) {
          txt += ' v11 Kalman nets ' + c10.kalman_trend.mean_net_pct_per_trade + '%/trade and Omni direct consensus nets ' + c10.omni_direct_consensus.mean_net_pct_per_trade + '%/trade after the same costs';
          if (c10.rank_fusion_analog_median) txt += ' (rank-fusion median ' + c10.rank_fusion_analog_median.mean_net_pct_per_trade + '%/trade; majority_vote_v6 ' + c10.majority_vote_v6.mean_net_pct_per_trade + '%/trade)';
          const direct = ((data.direct_method_eval || {}).horizons || []).filter(function(r) { return !r.error; });
          if (direct.length) txt += '; v11 direct by horizon: ' + direct.map(function(r) {
            return '+' + r.horizon_bars + ' Kalman ' + r.methods.kalman_trend.direction_accuracy_pct + '% / Omni ' + r.methods.omni_direct_consensus.direction_accuracy_pct + '%';
          }).join(' · ');
          txt += '. More correlated methods do not create a guaranteed lift.';
        }
        if (c10 && c10.hull_trend) {
          txt += ' v12 Hull nets ' + c10.hull_trend.mean_net_pct_per_trade + '%/trade, Markov regime ' + c10.markov_regime.mean_net_pct_per_trade + '%/trade and Atlas Fusion ' + c10.atlas_fusion_v12.mean_net_pct_per_trade + '%/trade after the same costs. A larger method zoo also creates more chances to overfit; no 80% universal rate is claimed.';
        }
        if (c10 && c10.ultimate_trend && c10.atlas_pressure_wave && c10.atlas_phoenix_fusion) {
          txt += ' v13 after the same costs: Ultimate ' + c10.ultimate_trend.mean_net_pct_per_trade + '%/trade, Atlas Pressure Wave ' + c10.atlas_pressure_wave.mean_net_pct_per_trade + '%/trade, Regime Compass ' + c10.atlas_regime_compass.mean_net_pct_per_trade + '%/trade, Phoenix ' + c10.atlas_phoenix_fusion.mean_net_pct_per_trade + '%/trade, Meta Hedge ' + c10.atlas_meta_hedge.mean_net_pct_per_trade + '%/trade, Online Logistic ' + c10.atlas_online_logistic.mean_net_pct_per_trade + '%/trade. Delayed-label learning is causal, but correlated features and one-sample fitting still do not create an 80% guarantee.';
        }
        if (c10 && c10.adaptive_selector) {
          txt += ' v9 adaptive_selector nets ' + c10.adaptive_selector.mean_net_pct_per_trade + '%/trade after the same costs';
          if (c10.path_analog_median) txt += ' (path-geometry median ' + c10.path_analog_median.mean_net_pct_per_trade + '%/trade; majority_vote_v4 ' + c10.majority_vote_v4.mean_net_pct_per_trade + '%/trade)';
          if (ens.adaptive_selector) txt += '; selector used its fallback on ' + ens.adaptive_selector.fallback_attempts + ' early attempts and learned only from fully revealed windows';
          txt += '.';
        }
      }
      const sim = data.path_simulation || {};
      if (!sim.error && sim.terminal_return_pct) {
        const t = sim.terminal_return_pct, dd = sim.max_drawdown_pct || {};
        txt += ' Analog path simulation (' + sim.simulated_paths + ' bootstrapped real look-alike paths over ' +
          sim.horizon_bars + ' bars): terminal p5 ' + t.p5 + '%, median ' + t.p50_median + '%, p95 ' + t.p95 +
          '%; median worst dip ' + dd.p50_median + '%, p95 dip ' + dd.p95 + '%. That is historical dispersion, not a price promise.';
      }
      verdictEl.textContent = txt;
    }
    const details = document.createElement('details');
    const sm = document.createElement('summary'); sm.textContent = 'Full Forecast Lab JSON'; details.appendChild(sm);
    const pre = document.createElement('pre'); pre.textContent = JSON.stringify(data, null, 2); details.appendChild(pre);
    out.appendChild(details);
    status.textContent = 'Done — ' + data.bars + ' bars. History, not prophecy: past analog outcomes never guarantee future prices.';
  } catch (e) { status.textContent = 'Forecast Lab error: ' + e.message; }
}
loadGoals();
loadPaperWallet();
loadBot();
loadDb();
if (new URLSearchParams(location.search).get('today') === '1') {
  // explicit opt-in: https://<preview>/?today=1 fetches today's public bars in
  // the browser and runs the failure loop immediately.
  setTimeout(function() { if (document.getElementById('today_status')) runTodayMarketTest(); }, 900);
}
"""


def render_home() -> str:
    strategies = "".join(_strategy_card(s) for s in STRATEGIES)
    methods = "".join(
        f'<article class="card"><h3>{html.escape(m["name"])}</h3>'
        f'<p>{html.escape(m["summary"])}</p><p><b>Tools:</b> {html.escape(m["tools"])}</p>'
        f'<p class="warn"><b>Watch out:</b> {html.escape(m["watch_out"])}</p></article>'
        for m in METHODS)
    patterns = "".join(
        f'<article class="card"><h3>{html.escape(p["name"])}</h3>{svg_candles(p["bars"])}'
        f'<p class="tags"><span>{html.escape(p["signal"])}</span></p><p>{html.escape(p["read"])}</p></article>'
        for p in PATTERNS)
    risk = "".join(
        f'<article class="card"><h3>{html.escape(t)}</h3><p>{html.escape(d)}</p></article>'
        for t, d in RISK_RULES)
    glossary = "".join(
        f'<tr><td><b>{html.escape(t)}</b></td><td>{html.escape(d)}</td></tr>'
        for t, d in GLOSSARY)
    lab_options = "".join(
        f'<option value="{html.escape(key)}"{" selected" if key == "atlas_minute_pulse" else ""}>'
        f'{html.escape(spec["name"])} — {html.escape(spec["atlas_strategy"])}</option>'
        for key, spec in ml.STRATEGY_ENGINES.items())
    lab_strategy_rows = "".join(
        f'<tr><td><b>{html.escape(spec["name"])}</b></td><td>{html.escape(spec["long_rule"])}</td>'
        f'<td>{html.escape(spec["short_rule"])}</td></tr>'
        for spec in ml.STRATEGY_ENGINES.values())
    preset_rows = "".join(
        f'<tr><td><b>{html.escape(p["label"])}</b></td><td>{html.escape(p["examples"])}</td>'
        f'<td>{html.escape(", ".join(p["typical_base_intervals"]))}</td>'
        f'<td>{html.escape(p["starting_cost_bps_to_research"])}</td>'
        f'<td>{html.escape(p["data_notes"])}</td></tr>'
        for p in ml.MARKET_PRESETS.values())
    sc_cause_list_html = " ".join(
        f'<code>{html.escape(cid)}</code>' for cid in sc.cause_ids())
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TradeAtlas — educational atlas of trading strategies & analysis methods</title>
<style>
:root{{--bg:#0f172a;--card:#1e293b;--ink:#e2e8f0;--mut:#94a3b8;--acc:#38bdf8}}
*{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,Segoe UI,Arial,sans-serif;background:var(--bg);color:var(--ink)}}
.wrap{{max-width:1080px;margin:0 auto;padding:22px 16px 46px}}
h1{{font-size:30px;margin:6px 0}}h2{{margin:0 0 12px}}h3{{margin:4px 0 8px}}
.sub{{color:var(--mut)}}
.banner{{background:#451a03;border:1px solid #b45309;border-radius:12px;padding:12px 14px;margin:14px 0;color:#fde68a}}
.tabs{{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}}
.tabs button{{background:var(--card);color:var(--ink);border:1px solid #334155;border-radius:999px;padding:8px 14px;cursor:pointer;font-size:15px}}
.tabs button.on{{background:var(--acc);color:#082f49;font-weight:700}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}}
.card{{background:var(--card);border:1px solid #334155;border-radius:14px;padding:16px}}
.tags span{{display:inline-block;background:#0b1220;border:1px solid #334155;border-radius:999px;padding:2px 9px;margin:0 4px 4px 0;font-size:12px;color:var(--mut)}}
.warn{{color:#fca5a5}}.pane{{display:none}}.pane.on{{display:block}}
label{{display:block;font-size:13px;color:var(--mut);margin-top:8px}}
input,select,textarea{{width:100%;padding:9px;border-radius:9px;border:1px solid #334155;background:#0b1220;color:var(--ink)}}
textarea{{min-height:130px;font-family:ui-monospace,Consolas,monospace;font-size:12px}}
th{{text-align:left;color:var(--mut);border-bottom:1px solid #334155;padding:8px}}
details pre{{white-space:pre-wrap;max-height:420px;overflow:auto;background:#020617;padding:10px;border-radius:10px}}
.labwide{{grid-column:1/-1}}.status{{color:var(--acc);margin-top:10px}}
button.go{{margin-top:12px;background:var(--acc);color:#082f49;font-weight:700;border:0;border-radius:10px;padding:10px 16px;cursor:pointer}}
.out{{background:#0b1220;border:1px solid #334155;border-radius:10px;padding:12px;margin-top:12px;white-space:pre-wrap;min-height:40px}}
table{{width:100%;border-collapse:collapse}}td{{border-bottom:1px solid #334155;padding:8px;vertical-align:top}}
.foot{{color:var(--mut);font-size:13px;margin-top:26px}}
</style></head><body><div class="wrap">
<h1>🗺️ TradeAtlas <small style="font-size:14px;color:var(--mut)">v{VERSION} · Genius Idea #14</small></h1>
<p class="sub">An educational atlas of the world's best-known trading <b>strategies</b> and <b>analysis methods</b> —
what each idea is, its classic textbook rules, how it fails, and the risk notes nobody should skip.</p>
<div class="banner">⚠️ <b>Education only — not financial advice.</b> {html.escape(DISCLAIMER)}</div>
<div class="tabs">
<button class="on" onclick="tab('strategies',this)">📈 Strategies ({len(STRATEGIES)})</button>
<button onclick="tab('methods',this)">🔬 Analysis methods ({len(METHODS)})</button>
<button onclick="tab('patterns',this)">🕯️ Candle patterns ({len(PATTERNS)})</button>
<button onclick="tab('lab',this)">📊 Market Lab · all timeframes</button>
<button onclick="tab('calcs',this)">🧮 Risk calculators</button>
<button onclick="tab('risk',this)">🛡️ Risk rules & glossary</button>
</div>

<section id="strategies" class="pane on"><h2>Strategies</h2><div class="grid">{strategies}</div></section>

<section id="methods" class="pane"><h2>Analysis methods</h2><div class="grid">{methods}</div></section>

<section id="patterns" class="pane"><h2>Candlestick patterns <small class="sub">(illustrations use invented example prices — shape only)</small></h2><div class="grid">{patterns}</div></section>

<section id="lab" class="pane"><h2>Market Lab — real data in, mechanical conditions + 100-signal validation out</h2>
<div class="banner">⚠️ <b>Research tool, not a signal seller.</b> “LONG / buy-condition” and “SHORT / sell-condition” below mean only that a published indicator rule fired on completed bars. They are <b>not recommendations</b>. TradeAtlas bundles <b>no licensed live prices</b>: upload/paste lawful OHLCV data or let your own browser poll a public/custom CORS feed. The wallet and bot below are <b>paper-only — never send money or crypto to TradeAtlas</b>; they have no deposit address or broker. The bot's paper-trading universe is only registered assets that pass your chosen halal screen; the screen is <b>not a fatwa</b>. A local SQLite database stores imported history and research, but no database can guarantee an 80% future hit rate.</div>
<div class="grid">
<div class="card labwide"><h3>🚀 Start here — simple 4-step paper workflow</h3>
<p class="sub"><b>v14 is minute-first.</b> <b>1)</b> Fetch real completed <b>1m</b> bars in your browser (BTC/USDT preset) or paste/upload lawful 1m/5m/15m OHLCV. <b>2)</b> Run the v14 minute race at 1/3/5/15/30 bars with up to 5000 hidden-future attempts before believing any number. <b>3)</b> Save real minute bars + halal evidence to SQLite across many symbols/days. <b>4)</b> Use the 1m paper bot and, if you independently decide to act in your own licensed account, its manual checklist tickets. <b>80% is a project GOAL, not a reached result.</b> TradeAtlas still has no deposit address, custody, API-key field, real conversion/withdrawal or automatic broker order.</p>
<button class="go" onclick="pollSelectedFeed()">1 · Fetch selected real market data</button>
<button class="go" onclick="analyzeCurrentLab()">2 · Analyze current data</button>
<button class="go" onclick="analyzeForecast(null)">3 · Run hidden-future Forecast Lab</button>
<button class="go" onclick="runMinuteForecast()">⏱ Run 1m hidden-future race</button>
<button class="go" onclick="loadGoals()">🎯 Show project goals</button>
<button class="go" onclick="seedDb()">Seed database</button>
<button class="go" onclick="importCurrentToDb()">Save current bars to database</button>
<button class="go" onclick="runDbResearch()">Run pooled database research</button>
<button class="go" onclick="botSetStatus('start')">▶ Start paper bot</button>
<button class="go" onclick="botSetStatus('resume')">↩ Resume paper bot</button>
<button class="go" onclick="botSetStatus('pause')">⏸ Pause paper bot</button>
<button class="go" onclick="botSetStatus('stop')">⏹ STOP paper bot</button>
</div>
<div class="card labwide"><h3>🎯 Project goals — minute trading, real-bot integration and the 80% accuracy gate</h3>
<p class="warn">Targets are tracked separately from evidence. <b>Current honest status: 80% is NOT reached or established.</b> It can only be marked reached after causal hidden-future tests on real minute data across symbols/days, with at least 1000 attempts per candidate, coverage, costs/slippage, confidence interval and fresh validation shown. USDT/BTC funding belongs in <b>your own licensed exchange account</b>; TradeAtlas can mirror a balance you report and create manual checklist tickets, but it must never receive or custody crypto.</p>
<button class="go" onclick="loadGoals()">Refresh goals JSON</button>
<div id="goals_out" style="overflow:auto"></div>
</div>
<div class="card"><h3>1 · Choose the mechanical engine</h3>
<label>Strategy engine</label><select id="lab_strategy">{lab_options}</select>
<label>Historical signals to test (most recent completed, non-overlapping)</label><input id="lab_max_signals" type="number" min="1" max="1000" step="1" value="100">
<label>Hold / forward-test horizon (bars on each timeframe; minute default)</label><input id="lab_horizon" type="number" min="1" max="500" step="1" value="5">
<label>Round-trip cost + slippage allowance (basis points)</label><input id="lab_cost" type="number" min="0" max="1000" step="any" value="10">
<p class="sub">The test enters at the <b>next bar open</b>, exits after the selected horizon, deducts costs, blocks overlaps, and reports accuracy together with expectancy, drawdown and an equity curve. <b>New in v3:</b> every timeframe also runs an <b>all-engine tournament</b> (all engines tested on the same bars) and a <b>70/30 walk-forward split</b>, and snapshots add Stochastic + ADX. <b>v10 raised the tournament to 14 engines</b> and snapshots added cycle/flow state. <b>v11 raised it to 20 engines</b>; <b>v12 raised it to 24</b>; <b>v13 raised it to 37</b>; <b>v14 raises it to 44</b> with rolling-VWAP reversion, EMA ribbon, RSI-2 snapback, UTC opening-range breakout, squeeze release, volume surge and the invented <b>Atlas Minute Pulse</b>. The default v14 workflow is Atlas Minute Pulse on 1m bars. The tournament's #1 row is the best fit to history — the most over-fit row — so trust it only where the later walk-forward slice agrees. <b>New in v4:</b> the <b>Forecast Lab</b> (card 5) answers "what happened next the last times it looked like this?" with historical analogs — then grades that very method with a <b>100-attempt hidden-future test</b> against naive baselines, on your data or on the bundled <b>real</b> AAPL 2015–2017 sample. If a method cannot beat a coin-flip dressed as a baseline, the lab prints exactly that.</p>
<button class="go" onclick="runLabDemo()">Run synthetic software validation</button>
</div>
<div class="card"><h3>2 · Analyze real OHLCV you supply</h3>
<label>Upload CSV or JSON</label><input id="lab_file" type="file" accept=".csv,.json,.txt" onchange="analyzeLabFile(this)">
<label>…or paste CSV/JSON bars</label><textarea id="lab_data" placeholder="timestamp,open,high,low,close,volume&#10;1767225600,100,101,99,100.7,12345"></textarea>
<button class="go" onclick="analyzeLabText()">Analyze pasted data on every timeframe</button>
<p class="sub">CSV header: <code>timestamp,open,high,low,close,volume</code>. JSON: an array or <code>bars[]</code> with <code>t/o/h/l/c/v</code>. Finer timeframes than your source interval are reported as unavailable — never fabricated.</p>
</div>
<div class="card"><h3>3 · Connect real market data in your browser</h3>
<label>One-click market preset (fills the fields; still data only)</label>
<select id="lab_market_preset" onchange="applyMarketPreset()">
<option value="crypto_binance" selected>Crypto 1m — BTC/USDT on Binance public data</option>
<option value="crypto_kraken">Crypto 1m — XBT/USD on Kraken public data</option>
<option value="stock_us">US stock — AAPL.US daily on Stooq</option>
<option value="etf_us">US ETF — SPY.US daily on Stooq</option>
<option value="index_spx">Index — ^SPX daily on Stooq</option>
<option value="fx_eurusd">Currency — EURUSD daily on Stooq</option>
<option value="stock_uk">UK stock example — VOD.UK daily on Stooq</option>
<option value="stock_de">German stock example — BMW.DE daily on Stooq</option>
</select>
<label>Market-data adapter (data only — never order routing)</label>
<select id="lab_feed_provider" onchange="feedProviderChanged()">
<option value="binance" selected>Binance public spot klines (crypto)</option>
<option value="kraken">Kraken public OHLC (crypto)</option>
<option value="stooq">Stooq daily CSV</option>
<option value="custom">My own CORS JSON/CSV endpoint</option>
</select>
<label>Symbol</label><input id="lab_feed_symbol" type="text" value="BTCUSDT" placeholder="BTCUSDT · XBTUSD · aapl.us">
<label>Base interval (v14 default: minutes)</label><select id="lab_feed_interval"><option selected>1m</option><option>5m</option><option>15m</option><option>1h</option><option>4h</option><option>1d</option><option>1w</option></select>
<label>History bars requested (Binance; other venues may cap it)</label><input id="lab_feed_limit" type="number" min="100" max="1000" step="50" value="1000">
<label>Custom CORS endpoint (used only by the custom adapter)</label><input id="lab_feed_url" type="url" placeholder="https://your-feed.example/bars?symbol=…">
<label>Poll every (seconds; use 60+ for completed 1m bars)</label><input id="lab_poll_seconds" type="number" min="5" max="3600" step="1" value="60">
<button id="lab_live_btn" class="go" onclick="toggleLabLive()">▶ Start browser live polling</button>
<button class="go" onclick="pollSelectedFeed()">Fetch real market data once</button>
<p class="sub">Your browser fetches the selected venue directly; the TradeAtlas server never sees feed credentials or fetches arbitrary URLs. Binance/Kraken adapters discard the still-forming candle. Public endpoints can fail through CORS, region, symbol naming, rate limits or terms; TradeAtlas does not bypass those controls. This is a market-data connection, <b>not a broker account and not live order execution</b>. For the halal paper bot, register and screen the exact asset first. Unregistered/review/fail assets of every class are blocked from bot entries.</p>
</div>
<div class="card"><h3>4 · Watch many symbols at once (all markets, your files)</h3>
<label>Upload one CSV/JSON file per symbol (up to 12; filename = symbol)</label>
<input id="watch_files" type="file" accept=".csv,.json,.txt" multiple onchange="analyzeWatchlist(this)">
<p class="sub">Crypto, stocks, FX, futures, indices — the lab is data-agnostic: if you can export honest OHLCV bars for it, every timeframe your base interval supports gets the same rulebook. The heatmap shows the latest mechanical condition; it deliberately does not rank symbols for you.</p>
<p id="watch_status" class="status"></p>
<div id="watch_out" style="overflow:auto"></div>
</div>
<div class="card"><h3>5 · Forecast Lab — “what happened next, last time it looked like this?”</h3>
<label>Upload one OHLCV file (same format as card 1; 250+ bars recommended)</label>
<input id="fc_file" type="file" accept=".csv,.json,.txt" onchange="analyzeForecast(this)">
<label>Out-of-sample attempts</label><input id="fc_attempts" type="number" min="10" max="300" value="100">
<label>Forecast horizon (bars)</label><input id="fc_horizon" type="number" min="1" max="60" value="5">
<button class="go" onclick="analyzeForecast(null)">Run Forecast Lab on current analyzed/pasted data</button>
<p class="sub">Two honest tools, neither is a crystal ball. <b>(a) Analog lookup:</b> finds the 30 past setups most similar to your latest bar (returns, RSI, SMA distance, volatility) and shows what those setups <i>actually did next</i> in your file. <b>(b) The 100-attempt hidden-future test:</b> replays history blind — forecast, uncover, score — and forces the analog method to compete against always-up, naive momentum and mean-reversion. <b>v5 adds:</b> the same test at 1/3/5/10/20-bar horizons (one-horizon "edges" usually evaporate), accuracy split by trend/volatility regime, and a path simulation that bootstraps the <i>real</i> look-alike paths to show how wide the historical spread — including worst dips — actually was. <b>v6 adds:</b> an ensemble race (analog median, distance-weighted analogs, momentum, majority vote, and an agreement-only filter whose accuracy is always printed next to its coverage) and a cost-aware re-scoring of every call after 10/25 bps round-trip costs — because a direction rate that dies after fees was never an edge. <b>v7 adds:</b> a candle-structure analog contestant — gap, range, body/wick balance, close location, range expansion and relative volume — raced under the identical hidden-future and cost rules, and explicitly unavailable on close-only files rather than fabricating candle anatomy. <b>v8 adds:</b> an indicator-regime analog contestant — RSI level/slope, ATR-normalized MACD, Bollinger %B/bandwidth, SMA distance/slope, Donchian/Stochastic position, ADX balance/strength, volatility regime and real volume surprise — plus majority_vote_v3 and a coverage-labelled consensus_3plus subset. <b>v9 adds:</b> a path-geometry analog contestant — 20/60-bar travel efficiency, volatility-normalized trend slopes, variance ratio, autocorrelation, skew/downside share, 60-bar excursion and drawdown position, volatility/range compression, sign streaks and real up/down volume balance — plus majority_vote_v4 and a <b>causal adaptive selector</b> that follows only contestants proven on attempts whose outcome windows had already ended (<code>old_origin + horizon ≤ current origin</code>), never on unfinished overlapping windows. <b>v13 adds:</b> direct Aroon/TSI/TRIX/CMO/Ultimate/RVI/regression/Donchian/OBV/Coppock signs, invented Atlas Pressure Wave + Regime Compass + family-balanced Phoenix Fusion, majority_vote_v8, and delayed-label Atlas Meta Hedge + online logistic learning. <b>v12 adds:</b> Hull trend, Supertrend, Kaufman AMA, Haar wavelet scales, a causal Markov trend/volatility/RSI regime vote, Atlas Fusion v12, majority_vote_v7, and a SQLite database that pools hidden-future research across every stored symbol/timeframe. <b>v11 adds:</b> causal Kalman local-trend, a fixed Omni direct consensus (multiscale + Kalman + horizon-matched trend + Parabolic SAR + a CCI/Williams/TSI/TRIX/Ultimate/CMO/Fisher/Schaff basket), rank-fusion neighbours across all five analog families, majority_vote_v6 and direct-method rows at neighbouring horizons. <b>v10 adds:</b> a cycle/flow analog family (Aroon, Vortex, CMO, Fisher, RVI, Schaff, KST, Coppock, CMF/MFI, Force Index, rolling VWAP, Ulcer, SuperSmoother, permutation entropy, overnight/intraday balance, plus invented Signed Path Pressure and Entropy-Weighted Trend), a direct volatility-normalized multiscale trend score across 3/5/10/20/60/120 bars, majority_vote_v5, multiscale rows at neighbouring horizons, and coverage-labelled confidence thresholds that are forbidden from becoming the headline. It gets no free pass: the same 100 hidden-future attempts and 10/25-bps cost rows decide whether it helps or merely decorates the loss. On the bundled real AAPL sample the original analog method <b>loses</b> (44% vs 56–58%) and the lab says so. That verdict is the product.</p>
<p id="fc_status" class="status"></p>
<p id="fc_verdict" class="warn"></p>
<div id="fc_out" style="overflow:auto"></div>
</div>
<div class="card"><h3>5B · Minute Accuracy Race — the road to the 80% GOAL</h3>
<p class="warn">Use real completed 1m/5m/15m bars only for evidence. This race tests seven causal minute engines plus baselines at several bar horizons, with coverage, Wilson 95% intervals and 5/10/25-bps costs. <b>It never declares the project goal proven from one series.</b> Synthetic minute bars test the software only.</p>
<label>Hidden-future attempts requested per horizon (goal gate starts at 1000)</label><input id="minute_attempts" type="number" min="10" max="5000" step="10" value="1000">
<label>Horizons in bars (comma-separated)</label><input id="minute_horizons" type="text" value="1,3,5,15,30">
<button class="go" onclick="runMinuteForecast()">Run minute hidden-future race on current/pasted bars</button>
<p class="sub">Methods with a hard state such as RSI-2, opening range or squeeze can abstain; accuracy is always printed with attempts and coverage. Minute OHLCV still omits the live order book, queue position, latency and partial fills.</p>
<p id="minute_status" class="status"></p>
<p id="minute_verdict" class="warn"></p>
<div id="minute_out" style="overflow:auto"></div>
</div>
<div class="card" id="failure-memory"><h3>5C · Failure Memory — the loop that learns from every failed test</h3>
<p class="warn">Research only. This loop does not predict markets and it never declares the 80% goal reached. What it does is refuse to repeat a failure silently.</p>
<p class="sub">Every candidate (method × horizon) is graded on completed bars only. A failed candidate is <b>diagnosed</b> against an explicit cause library — too few attempts, coverage too low, a naive baseline winning, costs eating the gross edge, one-horizon overfitting, walk-forward decay, regime dependence, deep drawdown, selection bias, zero volume, or a remedy that starved its own sample. Each cause carries an <b>avoid-rule</b> and an <b>implemented remedy</b>: the next round re-tests only what can still be saved, with that remedy applied. If the cause disappears the lesson is <b>resolved</b>; if it returns on a fair sample the candidate is <b>retired</b> and remembered, and later runs skip it automatically. Survivors must also hold on the recent 30% slice and, when you supply a second file, on that second symbol. Costs are always subtracted.</p>
<p class="sub"><b>Cause ids</b> (the full library is also returned by <code>GET /api/lessons</code>): {sc_cause_list_html}</p>
<label>Attempts per candidate in the screen round</label><input id="sc_attempts" type="number" min="30" max="5000" step="10" value="120">
<label>Horizons in bars (comma-separated)</label><input id="sc_horizons" type="text" value="3,5,15">
<label>Round-trip cost (bps)</label><input id="sc_cost" type="number" min="1" max="500" step="1" value="10">
<label>Second symbol file (optional, for the independent validation round)</label><input id="sc_second_file" type="file" accept=".csv,.json,.txt">
<label><input id="sc_remember" type="checkbox" checked> Save the lesson ledger to SQLite</label>
<label><input id="sc_use_saved" type="checkbox" checked> Avoid candidates my stored lessons already retired</label>
<button class="go" onclick="runSelfCorrection()">Run the self-correcting loop on current/pasted bars</button>
<button class="go" onclick="runSelfCorrectionDemo()">Run it on synthetic 1m demo bars (software check only)</button>
<h4>Real market test for today (your browser fetches, never this server)</h4>
<p class="sub">This sandbox cannot reach exchanges, and TradeAtlas deliberately never proxies arbitrary URLs. Your browser can reach these public endpoints directly, so it fetches the completed bars and posts them here. The still-forming candle is dropped. Two symbols are fetched so the validation round has an independent sample. Every run stores its provenance (venue, endpoint, bar times, fetch time) and its lessons in SQLite.</p>
<label>Public venue (no key, no login)</label><select id="today_venue">
<option value="binance" selected>Binance spot public klines</option>
<option value="kraken">Kraken public OHLC</option>
</select>
<label>Primary symbol (e.g. BTCUSDT on Binance, XBTUSD on Kraken)</label><input id="today_symbol" type="text" value="BTCUSDT">
<label>Validation symbol, same venue (e.g. ETHUSDT / ETHUSD)</label><input id="today_symbol2" type="text" value="ETHUSDT">
<label>Interval</label><select id="today_interval">
<option value="1m" selected>1m</option><option value="5m">5m</option><option value="15m">15m</option>
<option value="1h">1h</option><option value="4h">4h</option><option value="1d">1d</option>
</select>
<label>Completed bars requested (405–1000)</label><input id="today_limit" type="number" min="405" max="1000" step="5" value="1000">
<label>Round-trip cost assumed (bps) — Binance spot taker ≈ 7.5–10 bps per side depending on tier</label><input id="today_cost" type="number" min="1" max="500" step="0.5" value="12">
<button class="go" onclick="runTodayMarketTest()">Fetch today's completed bars in my browser → run the failure loop</button>
<p id="today_status" class="status"></p>
<div id="today_provenance" class="out" style="display:none"></div>
<button class="go" onclick="loadLessons()">Load the saved lesson ledger</button>
<button class="go" onclick="clearLessons()">Forget all stored lessons (asks first)</button>
<p id="sc_status" class="status"></p>
<p id="sc_verdict" class="warn"></p>
<div id="sc_out" style="overflow:auto"></div>
</div>
<div class="card labwide" id="auto-pipeline"><h3>6 · Auto-Collect &amp; Goal Progress — the site fetches and stores by itself</h3>
<p class="warn">Automation changes how much lawful data exists and how honestly it is measured. It cannot change the market: no button here makes a losing candidate win, and <b>goal_established stays false</b>.</p>
<p class="sub">Two collectors feed one SQLite database. <b>(a) Server collector:</b> the TradeAtlas process fetches from a <i>fixed allowlist</i> of public venues — no arbitrary URLs, no keys, no logins — walking backwards page by page until the target bar count is stored. <b>(b) Browser collector:</b> your browser fetches the same public endpoints and posts the bars back, which is what you need when the server has no network. Both store incrementally: later runs add only new bars. The newest <b>20%</b> of every series is reserved as a <b>holdout</b> that the tuning loop never sees; only the holdout button reads it, and every read is counted. The goal tracker then reports the honest distance to 80% gate by gate.</p>
<label>Venue</label><select id="pl_venue"><option value="binance" selected>Binance spot public klines</option><option value="kraken">Kraken public OHLC</option></select>
<label>Symbols (comma-separated)</label><input id="pl_symbols" type="text" value="BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT">
<label>Interval</label><select id="pl_interval"><option value="1m" selected>1m</option><option>5m</option><option>15m</option><option>1h</option><option>4h</option><option>1d</option></select>
<label>Target bars per symbol</label><input id="pl_target" type="number" min="300" max="20000" step="100" value="3000">
<label>Round-trip cost assumed (bps)</label><input id="pl_cost" type="number" min="1" max="500" step="0.5" value="12">
<button class="go" onclick="pipelineCollectServer()">Collect on the server (needs outbound network)</button>
<button class="go" onclick="pipelineCollectBrowser()">Collect in my browser, then store in SQLite</button>
<button class="go" onclick="runAutoResearch()">Grade everything stored (pooled evidence)</button>
<label>Stored symbol for the one-shot holdout test (e.g. BINANCE.BTCUSDT.1m)</label><input id="pl_holdout_symbol" type="text" value="BINANCE.BTCUSDT.1m">
<button class="go" onclick="runHoldout()">Evaluate the reserved holdout (recorded)</button>
<button class="go" onclick="loadGoalProgress()">Refresh 80% goal progress</button>
<p id="pl_status" class="status"></p>
<div id="pl_progress" style="margin-top:10px"></div>
<div id="pl_out" style="overflow:auto"></div>
</div>
<div class="card"><h3>6 · Demo e-wallet — simulated crypto balances, conversion, bot transfer + Follow / STOP</h3>
<p class="warn"><b>DO NOT SEND MONEY OR CRYPTOCURRENCY.</b> TradeAtlas has no deposit address, custody, real conversion, real withdrawal, leverage or broker/exchange execution. The demo e-wallet records imaginary balances and local PAPER_USD movements. <b>v14 adds an external-account mirror:</b> if your real USDT/BTC is in your own licensed exchange account, you may record that balance for accounting/checklists; TradeAtlas cannot access or verify it and does not add it to paper equity. Fund only through the exchange's own official deposit screen — never an address from TradeAtlas.</p>
<label>Reset starting PAPER_USD</label><input id="paper_start" type="number" min="1" step="any" value="10000">
<button class="go" onclick="paperReset()">Reset paper wallet</button>
<label>Hypothetical crypto asset</label><select id="paper_asset"><option>USDT</option><option>USDC</option><option>BTC</option><option>ETH</option><option>SOL</option><option>OTHER_PAPER_ASSET</option></select>
<label>Hypothetical crypto amount (simulation only)</label><input id="paper_crypto_amount" type="number" min="0" step="any" value="250">
<label>Hypothetical USD rate you type</label><input id="paper_usd_rate" type="number" min="0" step="any" value="1">
<button class="go" onclick="paperDepositBalance()">Add simulated crypto balance (no transfer)</button>
<button class="go" onclick="paperConvertBalance()">Convert simulated balance to PAPER_USD</button>
<button class="go" onclick="paperWithdrawSimulated()">Simulate withdrawal (remove imaginary units)</button>
<button class="go" onclick="paperConvert()">Legacy: credit a hypothetical conversion directly</button>
<label>Your own exchange/broker account label (never type a password, seed or API secret)</label><input id="external_venue" type="text" value="My own licensed account">
<label>External asset held by YOU outside TradeAtlas</label><select id="external_asset"><option>USDT</option><option>BTC</option><option>USDC</option><option>USD</option><option>ETH</option><option>SOL</option><option>OTHER_PAPER_ASSET</option></select>
<label>External balance quantity you report (0 clears the mirror row)</label><input id="external_quantity" type="number" min="0" step="any" value="0">
<label>USD rate you report for that asset</label><input id="external_rate" type="number" min="0" step="any" value="1">
<button class="go" onclick="paperRecordExternalBalance()">Record my external USDT/BTC balance (mirror only — no transfer)</button>
<label>Internal PAPER_USD transfer amount (demo wallet ↔ halal paper bot)</label><input id="paper_transfer_amount" type="number" min="0" step="any" value="1000">
<button class="go" onclick="paperTransferBot('wallet_to_bot')">Transfer PAPER_USD to paper bot</button>
<button class="go" onclick="paperTransferBot('bot_to_wallet')">Transfer bot PAPER_USD back to demo wallet</button>
<label>Paper symbol (must match the bars currently analyzed)</label><input id="paper_symbol" type="text" value="BTCUSDT">
<label>Paper timeframe</label><select id="paper_timeframe"><option value="source">Source bars</option><option selected>1m</option><option>5m</option><option>15m</option><option>1h</option><option>4h</option><option>1d</option><option>1w</option></select>
<label>Paper allocation per new long position (% of equity; hard cap 25%)</label><input id="paper_allocation" type="number" min="0.1" max="25" step="any" value="5">
<label>Simulated one-way fee (bps)</label><input id="paper_fee" type="number" min="0" max="500" step="any" value="10">
<label><input id="paper_drop_last" type="checkbox"> Drop the last bar first (use when my feed includes a still-forming candle)</label><br>
<button class="go" onclick="paperSetFollow(true)">▶ Follow paper signals</button>
<button class="go" onclick="paperFollowStep()">Run one paper follow-step</button>
<button class="go" onclick="paperSetFollow(false)">Pause following</button>
<button class="go" onclick="paperSetFollow(true)">Resume following</button>
<button class="go" onclick="paperStop()">⏹ STOP paper trading</button>
<button class="go" onclick="loadPaperWallet()">Refresh paper wallet</button>
<p class="sub">Follow mode is deliberately one click/one latest closed bar at a time: a fresh long condition may open one capped simulated spot position; a short condition exits a simulated holding. It cannot short, leverage, place a real order, or trade merely because a historical accuracy number looked attractive.</p>
<p id="paper_status" class="status"></p>
<div id="paper_out" style="overflow:auto"></div>
</div>
<div class="card"><h3>7 · Integrated minute bot — paper engine + manual tickets for your own external account</h3>
<p class="warn"><b>Integrated workflow, not custody or automatic live execution.</b> The v14 bot defaults to Atlas Minute Pulse on 1m bars, applies fees + simulated slippage, daily entry/holding/cooldown limits and halal-pass gating, then can produce a manual checklist ticket for your own licensed USDT/BTC account. It never accepts deposits or API keys and never sends a real order. The halal screen is a transparent calculator over evidence <b>you</b> type; it is <b>not a fatwa or certification</b>. Missing evidence = needs_review, and needs_review cannot enter even on paper.</p>
<label>Bot starting PAPER_USD (used by Reset bot)</label><input id="bot_start_balance" type="number" min="1" step="any" value="10000">
<label>Screen preset (examples — choose the standard you follow)</label><select id="halal_preset"><option value="strict" selected>Strict: debt/cash/receivables ≤30%, non-compliant income ≤5%</option><option value="balanced">Balanced: debt/cash ≤33%, receivables ≤49%, income ≤5%</option></select>
<label>Asset type</label><select id="halal_asset_type"><option value="stock" selected>Stock — financial-ratio screen</option><option value="crypto">Crypto — spot-only evidence screen</option><option value="currency">Currency/FX — spot/swap-free evidence screen</option><option value="commodity">Commodity — delivery/possession evidence screen</option><option value="etf">ETF — underlying-holdings screen</option><option value="fund">Fund — underlying-holdings screen</option></select>
<label>Asset symbol</label><input id="halal_symbol" type="text" value="TEST">
<label>Bot symbol for the currently analyzed bars</label><input id="bot_symbol" type="text" value="TEST">
<label>Company name</label><input id="halal_company" type="text" value="Synthetic test company">
<label>Sector</label><input id="halal_sector" type="text" value="technology">
<label>Prohibited activities found (comma list; leave empty only after checking)</label><input id="halal_activities" type="text" value="">
<label><input id="halal_activities_reviewed" type="checkbox"> I reviewed the company's core business activities myself</label><br>
<label><input id="halal_core_prohibited" type="checkbox"> Its core business/activity is prohibited under my chosen standard</label><br>
<label><input id="halal_user_allows" type="checkbox"> My chosen standard explicitly allows this asset in the exact form below</label><br>
<label><input id="halal_spot_only" type="checkbox" checked> Spot only (no futures/options/CFD form)</label><br>
<label><input id="halal_asset_specific_reviewed" type="checkbox"> Asset-specific activity/delivery reviewed</label><br>
<label><input id="halal_settlement_reviewed" type="checkbox"> Settlement/possession form reviewed</label><br>
<label><input id="halal_swap_free" type="checkbox"> Swap-free currency form (currency only)</label><br>
<label><input id="halal_leverage" type="checkbox"> Leverage/margin is involved</label><br>
<label><input id="halal_interest" type="checkbox"> Interest/swap/lending is involved</label><br>
<label><input id="halal_shorting" type="checkbox"> Short selling is involved</label><br>
<label><input id="halal_staking" type="checkbox"> Staking/lending/yield is involved (crypto)</label><br>
<label><input id="halal_gambling" type="checkbox"> Gambling activity is involved</label><br>
<label><input id="halal_fund_bad" type="checkbox"> Fund/ETF itself uses prohibited leverage/interest</label>
<label>Underlying ETF/fund holdings screen</label><select id="halal_underlying_status"><option value="">Not reviewed / not applicable</option><option value="pass">Pass</option><option value="needs_review">Needs review</option><option value="fail">Fail</option></select>
<label>Review expires (YYYY-MM-DD, optional but recommended)</label><input id="halal_expires" type="date" value="">
<label>Interest-bearing debt (% of market cap)</label><input id="halal_debt" type="number" min="0" step="any" value="10">
<label>Interest-bearing cash/securities (% of market cap)</label><input id="halal_cash_securities" type="number" min="0" step="any" value="5">
<label>Receivables (% of market cap)</label><input id="halal_receivables" type="number" min="0" step="any" value="20">
<label>Non-compliant income (% of revenue)</label><input id="halal_income" type="number" min="0" step="any" value="1">
<label>Dividend per share (optional, for a simple purification estimate)</label><input id="halal_dividend" type="number" min="0" step="any" value="">
<label>Where did these company figures come from?</label><input id="halal_source" type="text" value="DEMO FORM VALUES — replace with the company's latest filing">
<label>Financials as of</label><input id="halal_asof" type="text" value="replace-me">
<button class="go" onclick="screenHalalStock(false)">Screen only</button>
<button class="go" onclick="screenHalalStock(true)">Register screened asset</button>
<button class="go" onclick="saveHalalToDb()">Save evidence to database + bot</button>
<label>Bot mode profile</label><select id="bot_mode_profile"><option value="minute_scalping_paper" selected>Minute scalping — paper + manual tickets</option><option value="manual_live_companion">Manual live companion — paper decisions + tickets only</option><option value="standard_paper">Standard paper (non-minute research)</option></select>
<label>Bot timeframe</label><select id="bot_timeframe"><option value="source">Source bars</option><option selected>1m</option><option>5m</option><option>15m</option><option>1h</option><option>4h</option><option>1d</option><option>1w</option></select>
<label>Max allocation per position (% equity, hard cap 25)</label><input id="bot_allocation" type="number" min="0.1" max="25" step="any" value="5">
<label>Risk per trade (% equity, hard cap 2)</label><input id="bot_risk" type="number" min="0.05" max="2" step="any" value="0.5">
<label>Maximum open paper positions</label><input id="bot_max_positions" type="number" min="1" max="20" step="1" value="3">
<label>ATR stop multiple</label><input id="bot_atr_stop" type="number" min="0.25" max="10" step="any" value="1.5">
<label>Take-profit (R multiple)</label><input id="bot_take_r" type="number" min="0.1" max="20" step="any" value="1.5">
<label>Trailing stop (ATR multiple)</label><input id="bot_trail" type="number" min="0.25" max="10" step="any" value="1.5">
<label>Simulated one-way fee (bps)</label><input id="bot_fee" type="number" min="0" max="500" step="any" value="10">
<label>Simulated slippage (bps, worsens every paper fill)</label><input id="bot_slippage" type="number" min="0" max="500" step="any" value="5">
<label>Maximum new entries per UTC day</label><input id="bot_max_trades_day" type="number" min="1" max="5000" step="1" value="20">
<label>Maximum holding bars (0 = disabled; minute default 30)</label><input id="bot_max_holding" type="number" min="0" max="100000" step="1" value="30">
<label>Cooldown bars after an exit</label><input id="bot_cooldown" type="number" min="0" max="100000" step="1" value="3">
<label>Minimum ATR (% of price) before a minute entry</label><input id="bot_min_atr" type="number" min="0" max="20" step="any" value="0.02">
<label>Daily-loss halt (% — blocks new entries)</label><input id="bot_daily_loss" type="number" min="0.1" max="20" step="any" value="2">
<label>Peak drawdown halt (% — blocks new entries)</label><input id="bot_drawdown" type="number" min="1" max="50" step="any" value="6">
<label>Auto-cycle every (seconds, minimum 60 for 1m; this browser tab must stay open)</label><input id="bot_poll_seconds" type="number" min="60" max="3600" step="1" value="60">
<label><input id="bot_drop_last" type="checkbox"> Drop last bar (my feed includes a still-forming candle)</label><br>
<button class="go" onclick="botReset()">Reset halal paper bot</button>
<button class="go" onclick="botSetStatus('start')">▶ Start bot</button>
<button class="go" onclick="botStep()">Run one bot cycle</button>
<button id="bot_auto_btn" class="go" onclick="toggleBotAuto()">▶ Auto paper cycles</button>
<button class="go" onclick="botSetStatus('pause')">Pause bot</button>
<button class="go" onclick="botSetStatus('resume')">Resume bot</button>
<button class="go" onclick="botSetStatus('stop')">⏹ STOP bot</button>
<button class="go" onclick="botSetStatus('reset_risk')">Reset risk halt</button>
<button class="go" onclick="loadBot()">Refresh bot</button>
<p class="sub">The bot uses the Strategy engine selected in card 1 (all 44 engines are available; the v14 minute default is Atlas Minute Pulse). Start begins paper entries, Pause temporarily blocks them, Resume continues a paused bot, and STOP hard-halts following; protective logic and saved state remain inspectable. It buys only a fresh long condition on a registered <b>pass</b> asset, sizes by ATR risk, and exits on stop/target/trailing/short-condition. Short conditions never open shorts. State is saved locally in <code>tradeatlas-bot-state.json</code>; market/research history is in <code>tradeatlas.db</code>. Delete both files to erase the private paper platform data.</p>
<p id="bot_status" class="status"></p>
<div id="bot_out" style="overflow:auto"></div>
</div>
<div class="card"><h3>8 · Private market database — history, halal evidence, pooled research</h3>
<p class="sub">SQLite grows with every lawful file/feed you import. The package seeds the bundled real samples; it does <b>not</b> contain every global market's licensed history. Import Stooq/custom files or browser-fetched bars to expand it. Pooled research runs the hidden-future race on every stored series and saves attempts, accuracy and after-cost means — useful evidence, never an 80% guarantee.</p>
<label>Private access token (only needed if the server was started with TRADEATLAS_ACCESS_TOKEN)</label><input id="private_token" type="password" onchange="savePrivateToken(this)" placeholder="stored only in this browser">
<label>Database symbol</label><input id="db_symbol" type="text" value="AAPL">
<label>Asset type</label><select id="db_asset_type"><option>stock</option><option>crypto</option><option>currency</option><option>commodity</option><option>etf</option><option>fund</option><option>index</option><option>future</option></select>
<label>Instrument name</label><input id="db_name" type="text" value="">
<label>Exchange</label><input id="db_exchange" type="text" value="">
<label>Currency</label><input id="db_currency" type="text" value="USD">
<label>Country</label><input id="db_country" type="text" value="">
<label>Timeframe label for the currently analyzed/source bars</label><select id="db_timeframe"><option>1m</option><option>5m</option><option>15m</option><option>1h</option><option>4h</option><option selected>1d</option><option>1w</option><option>1mo</option><option>source</option></select>
<label>Source / licence note for these bars</label><input id="db_source" type="text" value="user-supplied bars — replace with exact source">
<button class="go" onclick="seedDb()">Seed bundled real samples</button>
<button class="go" onclick="importCurrentToDb()">Import current analyzed bars</button>
<label>Hidden-future attempts per long series</label><input id="db_attempts" type="number" min="10" max="1000" value="100">
<button class="go" onclick="runDbResearch()">Run pooled database research</button>
<button class="go" onclick="syncDbHalalToBot()">Re-screen + sync database halal profiles to bot</button>
<button class="go" onclick="loadDb()">Refresh database stats</button>
<p id="db_status" class="status"></p>
<div id="db_out" style="overflow:auto"></div>
</div>
<div class="card labwide"><h3>Market presets — cost & data homework per asset class</h3>
<p class="sub">Starting points for the cost field above, not facts about your broker: measure your real spread/fees/slippage and type that number in. A backtest with fantasy costs grades your imagination, not an engine.</p>
<table><tr><th>Market</th><th>Examples (your exports)</th><th>Typical base intervals</th><th>Round-trip cost to research</th><th>Data traps</th></tr>{preset_rows}</table></div>
<div class="card labwide"><h3>Mechanical rule sheet — all {len(ml.STRATEGY_ENGINES)} engines (every engine is also tournament-tested per timeframe)</h3><table><tr><th>Engine</th><th>Long / buy-condition</th><th>Short / sell-condition</th></tr>{lab_strategy_rows}</table></div>
<div class="card labwide"><h3>Results by timeframe</h3><div id="lab_summary"><p class="sub">Run the synthetic validation or supply market data. Accuracy alone is not an edge — read expectancy, average return, drawdown, sample count and costs beside it.</p></div><div style="overflow:auto"><table id="lab_table"></table></div><p id="lab_status" class="status"></p></div>
</div></section>

<section id="calcs" class="pane"><h2>Risk calculators <small class="sub">(arithmetic only — they size risk, they do not pick trades)</small></h2>
<div class="grid">
<div class="card"><h3>Position size</h3>
<label>Account size</label><input id="ps_account" type="number" step="any" value="10000">
<label>Risk per trade (%)</label><input id="ps_risk" type="number" step="any" value="1">
<label>Entry price</label><input id="ps_entry" type="number" step="any" value="50">
<label>Stop price</label><input id="ps_stop" type="number" step="any" value="47.5">
<button class="go" onclick="calc('position',{{account:'ps_account',risk_pct:'ps_risk',entry:'ps_entry',stop:'ps_stop'}},'ps_out')">Calculate</button>
<div class="out" id="ps_out">Result appears here.</div></div>
<div class="card"><h3>Risk : Reward</h3>
<label>Entry price</label><input id="rr_entry" type="number" step="any" value="50">
<label>Stop price</label><input id="rr_stop" type="number" step="any" value="47.5">
<label>Target price</label><input id="rr_target" type="number" step="any" value="57.5">
<button class="go" onclick="calc('riskreward',{{entry:'rr_entry',stop:'rr_stop',target:'rr_target'}},'rr_out')">Calculate</button>
<div class="out" id="rr_out">Result appears here.</div></div>
<div class="card"><h3>Expectancy</h3>
<label>Win rate (%)</label><input id="ex_win" type="number" step="any" value="45">
<label>Average win (R)</label><input id="ex_aw" type="number" step="any" value="2">
<label>Average loss (R)</label><input id="ex_al" type="number" step="any" value="1">
<button class="go" onclick="calc('expectancy',{{winrate_pct:'ex_win',avg_win_r:'ex_aw',avg_loss_r:'ex_al'}},'ex_out')">Calculate</button>
<div class="out" id="ex_out">Result appears here.</div></div>
</div></section>

<section id="risk" class="pane"><h2>Risk rules every textbook repeats</h2><div class="grid">{risk}</div>
<h2 style="margin-top:22px">Glossary</h2><div class="card"><table>{glossary}</table></div></section>

<p class="foot">TradeAtlas v{VERSION} · educational/research reference · no bundled licensed live feed · mechanical conditions only · no broker links ·
data API: <code>/api/strategies</code> · Market Lab: <code>GET /api/lab/spec</code>, <code>GET /api/lab/demo</code>, <code>POST /api/lab/analyze</code>, <code>POST /api/lab/watchlist</code>, <code>POST /api/lab/forecast</code> · goals: <code>GET /api/goals</code> · minute race: <code>POST /api/lab/minute-forecast</code> · per timeframe: snapshot (+minute/VWAP/ORB state), latest condition, 100-signal validation, walk-forward split, 44-engine tournament, equity curve · demo e-wallet: <code>GET /api/paper/wallet</code>, <code>POST /api/paper/deposit-simulated</code>, <code>POST /api/paper/deposit-balance-simulated</code>, <code>POST /api/paper/convert-balance-simulated</code>, <code>POST /api/paper/withdraw-simulated</code>, <code>POST /api/paper/external-balance</code> (user-reported own-account mirror only), <code>POST /api/paper/transfer-bot-simulated</code>, <code>POST /api/paper/follow</code>, <code>POST /api/paper/stop</code>, <code>POST /api/paper/follow-step</code> (simulation only; no real deposit/withdrawal) · halal paper bot: <code>GET /api/bot</code>, <code>POST /api/halal/screen</code>, <code>POST /api/bot/register-stock</code>, <code>POST /api/bot/status</code>, <code>POST /api/bot/step</code>, <code>POST /api/bot/stop</code> · database: <code>GET /api/db/stats</code>, <code>POST /api/db/import-current</code>, <code>POST /api/db/research</code>, <code>GET /api/db/leaderboard</code>, <code>POST /api/db/halal-profile</code> · Forecast Lab: analog history + 100-attempt hidden-future evaluation vs naive baselines (history, never prophecy) · calculator API: <code>/api/calc?kind=position&amp;account=10000&amp;risk_pct=1&amp;entry=50&amp;stop=47.5</code><br>
{html.escape(DISCLAIMER)}</p>
</div>
<script>
function tab(id,btn){{document.querySelectorAll('.pane').forEach(p=>p.classList.remove('on'));
document.querySelectorAll('.tabs button').forEach(b=>b.classList.remove('on'));
document.getElementById(id).classList.add('on');btn.classList.add('on');}}
async function calc(kind,map,outId){{const q=new URLSearchParams({{kind}});
for(const k in map)q.set(k,document.getElementById(map[k]).value);
const out=document.getElementById(outId);out.textContent='Calculating…';
try{{const r=await fetch('/api/calc?'+q.toString());const j=await r.json();
if(j.error){{out.textContent='Error: '+j.error;return;}}
out.textContent=Object.entries(j.result).map(([k,v])=>k+': '+v).join('\\n');}}
catch(e){{out.textContent='Request failed: '+e;}}}}
</script><script>{LAB_JS}</script></body></html>"""


def atlas_json() -> dict:
    return {"name": "TradeAtlas", "version": VERSION, "disclaimer": DISCLAIMER,
            "strategies": STRATEGIES, "methods": METHODS,
            "patterns": [{k: v for k, v in p.items()} for p in PATTERNS],
            "risk_rules": [{"title": t, "detail": d} for t, d in RISK_RULES],
            "glossary": [{"term": t, "definition": d} for t, d in GLOSSARY],
            "project_goals": ml.project_goals(),
            "market_lab": ml.lab_spec(),
            "failure_memory": sc.self_correction_spec(),
            "data_pipeline": pl.pipeline_spec(),
            "market_database": {
                "engine": "SQLite local file (tradeatlas.db)",
                "tables": ["instruments", "bars", "data_imports", "halal_profiles",
                           "halal_screen_history", "research_runs", "method_scores", "bot_events",
                           "self_correction_runs", "research_trials", "research_lessons"],
                "seed": "bundled real AAPL daily + five monthly samples; expand only with data you have the right to use",
                "private_access": "Set TRADEATLAS_ACCESS_TOKEN to require X-TradeAtlas-Token on paper/bot/halal/database APIs; bind to localhost for a private local platform",
                "contains_broker_credentials": False,
                "contains_payment_instruments": False,
            }}


class Handler(BaseHTTPRequestHandler):
    server_version = f"TradeAtlas/{VERSION}"

    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body: bytes, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    @staticmethod
    def _lab_options(source: dict) -> dict:
        strategy = str(source.get("strategy") or "atlas_minute_pulse")
        if strategy not in ml.STRATEGY_ENGINES:
            raise ValueError(f"unknown strategy '{strategy}' — use one of {sorted(ml.STRATEGY_ENGINES)}")
        try:
            return {
                "strategy": strategy,
                "max_signals": int(source.get("max_signals") or 100),
                "horizon_bars": int(source.get("horizon_bars") or source.get("horizon") or 5),
                "round_trip_cost_bps": float(
                    source.get("round_trip_cost_bps", source.get("cost_bps", 10))),
            }
        except (TypeError, ValueError) as exc:
            raise ValueError("max_signals, horizon_bars and round_trip_cost_bps must be numeric") from exc

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if not _private_request_ok(self.headers, path):
            self._json(401, {"error": "private access token required", "disclaimer": DISCLAIMER})
            return
        if path in ("/", "/index.html"):
            self._send(200, render_home().encode("utf-8"))
        elif path == "/api/strategies":
            self._json(200, atlas_json())
        elif path == "/api/calc":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            kind = qs.get("kind", "")
            spec = CALCS.get(kind)
            if not spec:
                self._json(400, {"error": f"unknown kind '{kind}' — use one of {sorted(CALCS)}"})
                return
            fn, fields = spec
            missing = [f for f in fields if f not in qs]
            if missing:
                self._json(400, {"error": f"missing parameter(s): {', '.join(missing)}"})
                return
            try:
                result = fn(*[qs[f] for f in fields])
            except ValueError as exc:
                self._json(400, {"error": str(exc)})
                return
            self._json(200, {"kind": kind, "inputs": {f: qs[f] for f in fields},
                             "result": result, "disclaimer": DISCLAIMER})
        elif path == "/api/goals":
            result = ml.project_goals()
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
        elif path == "/api/db/stats":
            with MARKET_DB_LOCK:
                result = _market_db().stats()
            result["private_access_token_required"] = bool(ACCESS_TOKEN)
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
        elif path == "/api/db/series":
            with MARKET_DB_LOCK:
                result = {"series": _market_db().list_series()}
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
        elif path == "/api/db/bars":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            try:
                with MARKET_DB_LOCK:
                    bars = _market_db().get_bars(
                        qs.get("symbol") or "", qs.get("timeframe") or "source",
                        limit=int(qs["limit"]) if qs.get("limit") else None)
            except (TypeError, ValueError) as exc:
                self._json(400, {"error": str(exc), "disclaimer": DISCLAIMER})
                return
            self._json(200, {"symbol": qs.get("symbol"), "timeframe": qs.get("timeframe"),
                             "bars": bars, "count": len(bars), "disclaimer": DISCLAIMER})
        elif path == "/api/db/leaderboard":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            try:
                run_id = int(qs["run_id"]) if qs.get("run_id") else None
                with MARKET_DB_LOCK:
                    result = {"leaderboard": _market_db().leaderboard(run_id=run_id)}
            except (TypeError, ValueError) as exc:
                self._json(400, {"error": str(exc), "disclaimer": DISCLAIMER})
                return
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
        elif path == "/api/db/halal":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            with MARKET_DB_LOCK:
                result = {"profiles": _market_db().list_halal_profiles(status=qs.get("status"))}
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
        elif path == "/api/bot":
            with HALAL_BOT_LOCK:
                result = ml.halal_bot_view(HALAL_BOT)
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
        elif path == "/api/paper/wallet":
            global PAPER_WALLET
            with PAPER_WALLET_LOCK:
                result = ml.paper_wallet_view(PAPER_WALLET)
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
        elif path == "/api/goal-progress":
            query = urllib.parse.parse_qs(parsed.query)
            def _num(name, default):
                try:
                    return float((query.get(name) or [default])[0])
                except (TypeError, ValueError):
                    return default
            with MARKET_DB_LOCK:
                db = _market_db()
                result = pl.goal_progress(
                    db, cost_bps=_num("cost_bps", 10.0), attempts=int(_num("attempts", 150)))
                result["history"] = db.goal_history(limit=10)
                result["stored_report_id"] = db.record_goal_report(result)["id"]
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
            return
        elif path == "/api/pipeline/status":
            with MARKET_DB_LOCK:
                db = _market_db()
                result = {
                    "mode": "pipeline_status",
                    "spec": pl.pipeline_spec(),
                    "collections": db.list_collections(limit=20),
                    "holdout_evaluations": db.holdout_use_count(),
                    "recent_holdouts": db.list_holdouts(limit=5),
                    "goal_history": db.goal_history(limit=10),
                    "stats": db.stats(),
                    "next_steps": [
                        "POST /api/pipeline/collect to fetch new bars from the allowlist (server needs network), or use the browser collector in card 6.",
                        "POST /api/lab/auto-research to grade everything stored.",
                        "POST /api/lab/holdout once to test the reserved slice.",
                        "GET /api/goal-progress for the honest distance to 80%.",
                    ],
                }
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
            return
        elif path == "/api/lessons":
            query = urllib.parse.parse_qs(parsed.query)
            symbol = (query.get("symbol") or [None])[0]
            status = (query.get("status") or [None])[0]
            with MARKET_DB_LOCK:
                db = _market_db()
                lessons = db.self_correction_lessons(symbol=symbol, status=status,
                                                     limit=int((query.get("limit") or ["200"])[0]))
                tally = db.lesson_tally(symbol=symbol)
                latest = db.latest_self_correction()
            self._json(200, {
                "mode": "failure_memory_lessons",
                "symbol": symbol, "status": status,
                "count": len(lessons), "lessons": lessons, "tally": tally,
                "latest_run": latest,
                "cause_library": sc.cause_library(),
                "note": ("Lessons are remembered failures: each one carries the reason it "
                         "failed, the avoid-rule for the next test and whether its remedy worked."),
                "disclaimer": DISCLAIMER,
            })
            return
        elif path == "/api/failure-memory":
            with MARKET_DB_LOCK:
                db = _market_db()
                tally = db.lesson_tally()
                latest = db.latest_self_correction()
                lessons = db.self_correction_lessons(limit=50)
            self._json(200, {
                "mode": "failure_memory_summary",
                "tally": tally, "latest_run": latest, "recent_lessons": lessons,
                "spec": sc.self_correction_spec(),
                "disclaimer": DISCLAIMER,
            })
            return
        elif path == "/api/evolution":
            # v17 evolution tracker
            with MARKET_DB_LOCK:
                db = _market_db()
                evo_list = db.list_evolution(limit=20)
                latest_lessons = db.self_correction_lessons(limit=200)
                clustered = evo.failure_cluster(latest_lessons)
                db_stats = db.stats()
                # compute evolution metrics from stored runs
                history = []
                latest_run = db.latest_self_correction()
                if latest_run:
                    history = [latest_run.get("summary") or {}]
                metrics = evo.compute_evolution_metrics(history)
            self._json(200, {
                "mode": "evolution_tracker",
                "version": evo.VERSION,
                "spec": evo.evolution_spec(),
                "generations": evo_list,
                "cluster": clustered,
                "metrics": metrics,
                "remedy_effectiveness": evo.remedy_effectiveness(latest_lessons, history) if latest_lessons else {},
                "db_stats": db_stats.get("evolution"),
                "disclaimer": DISCLAIMER,
                "goal_established": False,
            })
            return
        elif path == "/api/diagnostics":
            # v17 deep diagnostics
            query = urllib.parse.parse_qs(parsed.query)
            cause = (query.get("cause") or ["baseline_not_beaten"])[0]
            with MARKET_DB_LOCK:
                db = _market_db()
                lessons = db.self_correction_lessons(limit=100)
            # find example lesson for that cause
            example = next((l for l in lessons if l.get("cause") == cause), None)
            explanation = diag.explain_failure(cause, example.get("evidence") if example else "example evidence")
            self._json(200, {
                "mode": "deep_diagnostics",
                "cause": cause,
                "explanation": explanation,
                "batch_diagnosis": diag.diagnose_batch([{"direction_accuracy_pct": 52, "mean_net_pct": -0.1, "attempts_made": 100, "origins_considered": 100, "coverage_pct": 50, "abstention": {}, "zero_volume": False}], {"cost_bps": 10, "attempts": 100, "min_history": 130, "threshold_scale": 1.0, "cost_multiple": 0, "min_coverage_pct": 20, "min_attempts": 30, "max_drawdown_pct": 25, "min_baseline_margin_pct": 1, "target_accuracy_pct": 80, "require_neighbor_support": False, "require_walk_forward_ok": False, "require_regime_stability": False, "require_second_symbol": False, "late_slice_only": False}) if False else {},
                "spec": diag.diagnostics_spec(),
                "disclaimer": DISCLAIMER,
            })
            return
        elif path == "/api/pipeline/health":
            with MARKET_DB_LOCK:
                db = _market_db()
                health = pl.health_check(db)
                metrics = pl.pipeline_health_metrics(db)
            self._json(200, {
                "mode": "pipeline_health",
                "health": health,
                "metrics": metrics,
                "disclaimer": DISCLAIMER,
            })
            return
        elif path == "/api/lab/advanced-stats":
            # v17 advanced stats demo on synthetic data
            try:
                import random
                random.seed(42)
                sample_returns = [random.gauss(0.02, 0.5) for _ in range(100)]
                bootstrap = ml.bootstrap_mean_ci(sample_returns)
                tail = ml.tail_risk_metrics(sample_returns)
                auto = ml.autocorrelation_check(sample_returns)
                vol_regime = ml.volatility_regime_detection(sample_returns)
                perm = ml.permutation_pvalue(55, 100)
                sharpe = ml.deflated_sharpe_ratio(sample_returns, n_trials=12)
            except Exception as exc:
                self._json(500, {"error": str(exc)})
                return
            self._json(200, {
                "mode": "advanced_stats",
                "bootstrap_ci": bootstrap,
                "tail_risk": tail,
                "autocorrelation": auto,
                "volatility_regime": vol_regime,
                "permutation_pvalue": perm,
                "deflated_sharpe": sharpe,
                "bonferroni_threshold_12_tests": ml.bonferroni_threshold(12),
                "benjamini_hochberg_example": ml.benjamini_hochberg([0.01, 0.04, 0.06, 0.2, 0.5]),
                "disclaimer": DISCLAIMER,
                "warning": "Statistical tools describe past data; they do not predict future profits.",
            })
            return
        elif path == "/api/lab/spec":
            payload = ml.lab_spec()
            payload["disclaimer"] = DISCLAIMER
            self._json(200, payload)
        elif path == "/api/lab/demo":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            try:
                options = self._lab_options(qs)
                bars_per_timeframe = int(qs.get("bars_per_timeframe") or 6000)
                seed = int(qs.get("seed") or 42)
                result = ml.demo_analysis(
                    bars_per_timeframe=bars_per_timeframe, seed=seed, **options)
            except (TypeError, ValueError) as exc:
                self._json(400, {"error": str(exc), "disclaimer": DISCLAIMER})
                return
            result["disclaimer"] = DISCLAIMER
            self._json(200, result)
        elif path == "/healthz":
            self._send(200, b"ok", "text/plain")
        else:
            self._send(404, b"not found", "text/plain")


    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if not _private_request_ok(self.headers, parsed.path):
            self._json(401, {"error": "private access token required", "disclaimer": DISCLAIMER})
            return
        if parsed.path not in ("/api/lab/analyze", "/api/lab/watchlist", "/api/lab/forecast", "/api/lab/minute-forecast",
                               "/api/lab/self-correct", "/api/lessons/clear",
                               "/api/pipeline/collect", "/api/pipeline/import",
                               "/api/lab/auto-research", "/api/lab/holdout",
                               "/api/lab/predict-failure", "/api/lab/remedy-verify", "/api/lab/bootstrap",
                               "/api/lab/permutation", "/api/lab/advanced-stats",
                               "/api/evolution/record", "/api/diagnostics/explain",
                               "/api/paper/reset", "/api/paper/external-balance", "/api/paper/deposit-simulated",
                               "/api/paper/deposit-balance-simulated", "/api/paper/convert-balance-simulated",
                               "/api/paper/withdraw-simulated", "/api/paper/transfer-bot-simulated",
                               "/api/paper/order", "/api/paper/follow", "/api/paper/stop",
                               "/api/paper/follow-step", "/api/halal/screen",
                               "/api/bot/reset", "/api/bot/register-stock", "/api/bot/status",
                               "/api/bot/settings", "/api/bot/step", "/api/bot/stop", "/api/bot/sync-halal-db",
                               "/api/db/seed", "/api/db/import-current", "/api/db/research", "/api/db/halal-profile"):
            self._send(404, b"not found", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0 or length > 8_000_000:
            self._json(413, {"error": "request body must be between 1 byte and 8 MB",
                             "disclaimer": DISCLAIMER})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("JSON body must be an object")
            if parsed.path.startswith("/api/db/"):
                with MARKET_DB_LOCK:
                    db = _market_db()
                    if parsed.path == "/api/db/seed":
                        result = db.seed_bundled_data(os.path.dirname(os.path.abspath(__file__)))
                    elif parsed.path == "/api/db/import-current":
                        if payload.get("bars") is not None:
                            db_bars = payload["bars"]
                        elif payload.get("csv_text"):
                            db_bars = {"csv_text": payload["csv_text"]}
                        elif payload.get("csv"):
                            db_bars = {"csv": payload["csv"]}
                        else:
                            raise ValueError("supply bars[], csv_text or csv to import")
                        result = db.import_bars(
                            symbol=payload.get("symbol"), timeframe=str(payload.get("timeframe") or "source"),
                            bars=db_bars, source=str(payload.get("source") or ""),
                            instrument=payload.get("instrument") if isinstance(payload.get("instrument"), dict) else None)
                    elif parsed.path == "/api/db/research":
                        result = db.research_all(
                            attempts=int(payload.get("attempts") or 100),
                            top_n=int(payload.get("top_n") or 30))
                    else:  # halal-profile
                        profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else payload
                        preset = str(payload.get("preset") or "strict")
                        registration = db.save_halal_profile(profile, preset=preset)
                        result = {"registration": registration}
                        if payload.get("register_bot"):
                            global HALAL_BOT
                            with HALAL_BOT_LOCK:
                                bot_result = ml.halal_bot_register_asset(HALAL_BOT, profile, preset=preset)
                                _save_halal_bot()
                            result["bot_registration"] = bot_result
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if parsed.path == "/api/halal/screen":
                profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else payload
                result = ml.screen_halal_asset(
                    profile, preset=str(payload.get("preset") or "strict"))
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if parsed.path.startswith("/api/bot/"):
                with HALAL_BOT_LOCK:
                    if parsed.path == "/api/bot/reset":
                        HALAL_BOT = ml.new_halal_paper_bot(
                            starting_balance=float(payload.get("starting_balance") or 10_000),
                            preset=str(payload.get("preset") or "strict"),
                            settings=payload.get("settings") if isinstance(payload.get("settings"), dict) else None)
                        result = ml.halal_bot_view(HALAL_BOT)
                    elif parsed.path == "/api/bot/register-stock":
                        profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else payload
                        result = ml.halal_bot_register_asset(
                            HALAL_BOT, profile,
                            preset=str(payload.get("preset") or HALAL_BOT.get("screen_preset") or "strict"))
                    elif parsed.path == "/api/bot/status":
                        if isinstance(payload.get("settings"), dict):
                            HALAL_BOT["settings"] = ml._bot_settings(
                                payload["settings"], base=HALAL_BOT.get("settings"))
                        result = ml.halal_bot_set_status(
                            HALAL_BOT, action=str(payload.get("action") or ""))
                    elif parsed.path == "/api/bot/settings":
                        settings_payload = payload.get("settings") if isinstance(payload.get("settings"), dict) else payload
                        HALAL_BOT["settings"] = ml._bot_settings(
                            settings_payload, base=HALAL_BOT.get("settings"))
                        result = ml.halal_bot_view(HALAL_BOT)
                    elif parsed.path == "/api/bot/step":
                        market_data = payload.get("symbols") or payload.get("market_data")
                        if not isinstance(market_data, dict):
                            symbol = payload.get("symbol")
                            if not symbol:
                                raise ValueError("supply symbols{} or one symbol with bars[]/csv_text")
                            if payload.get("bars") is not None:
                                one_payload = payload["bars"]
                            elif payload.get("csv_text"):
                                one_payload = {"csv_text": payload["csv_text"]}
                            else:
                                raise ValueError("supply bars[] or csv_text for the bot cycle")
                            market_data = {str(symbol): one_payload}
                        settings_payload = payload.get("settings") if isinstance(payload.get("settings"), dict) else None
                        result = ml.halal_bot_step(
                            HALAL_BOT, market_data=market_data, settings=settings_payload,
                            drop_last_bar=bool(payload.get("drop_last_bar")))
                        try:
                            with MARKET_DB_LOCK:
                                result["database_events_recorded"] = _market_db().record_bot_decisions(
                                    result.get("decisions") or [])
                        except Exception:
                            result["database_events_recorded"] = 0
                    elif parsed.path == "/api/bot/sync-halal-db":
                        with MARKET_DB_LOCK:
                            db_rows = _market_db().list_halal_profiles()
                        synced = []
                        for row in db_rows:
                            prof = dict(row.get("profile") or {})
                            evidence = prof.pop("evidence", {}) if isinstance(prof.get("evidence"), dict) else {}
                            prof.update(evidence)
                            reg = ml.halal_bot_register_asset(
                                HALAL_BOT, prof, preset=str(row.get("preset") or "strict"))
                            synced.append({"symbol": reg["registration"]["symbol"],
                                           "status": reg["registration"]["status"]})
                        result = ml.halal_bot_view(HALAL_BOT)
                        result["synced_profiles"] = synced
                    else:  # /api/bot/stop
                        prices = payload.get("prices") or {}
                        if not isinstance(prices, dict):
                            raise ValueError("prices must be an object when supplied")
                        result = ml.halal_bot_stop(
                            HALAL_BOT, close_all=bool(payload.get("close_all")),
                            prices=prices, fee_bps=float(payload.get("fee_bps", 10)))
                    saved = _save_halal_bot()
                result["state_saved_locally"] = saved
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if parsed.path.startswith("/api/paper/"):
                global PAPER_WALLET
                with PAPER_WALLET_LOCK:
                    if parsed.path == "/api/paper/reset":
                        PAPER_WALLET = ml.new_paper_wallet(
                            starting_balance=float(payload.get("starting_balance") or 10_000))
                        result = ml.paper_wallet_view(PAPER_WALLET)
                    elif parsed.path == "/api/paper/external-balance":
                        result = ml.paper_wallet_record_external_balance(
                            PAPER_WALLET, venue_label=str(payload.get("venue_label") or ""),
                            asset=str(payload.get("asset") or "USDT"),
                            quantity=float(payload.get("quantity") or 0),
                            usd_rate=(float(payload["usd_rate"]) if payload.get("usd_rate") is not None else None),
                            reported_at=(str(payload["reported_at"]) if payload.get("reported_at") else None))
                    elif parsed.path == "/api/paper/deposit-simulated":
                        result = ml.paper_wallet_simulate_conversion(
                            PAPER_WALLET, asset=str(payload.get("asset") or "USDT"),
                            crypto_amount=payload.get("crypto_amount"),
                            usd_rate=payload.get("usd_rate", 1.0))
                    elif parsed.path == "/api/paper/deposit-balance-simulated":
                        result = ml.paper_wallet_simulate_crypto_deposit(
                            PAPER_WALLET, asset=str(payload.get("asset") or "USDT"),
                            crypto_amount=payload.get("crypto_amount"),
                            usd_rate=payload.get("usd_rate", 1.0))
                    elif parsed.path == "/api/paper/convert-balance-simulated":
                        result = ml.paper_wallet_convert_crypto_balance(
                            PAPER_WALLET, asset=str(payload.get("asset") or "USDT"),
                            crypto_amount=payload.get("crypto_amount"),
                            usd_rate=payload.get("usd_rate", 1.0),
                            fee_bps=float(payload.get("fee_bps", 10)))
                    elif parsed.path == "/api/paper/withdraw-simulated":
                        result = ml.paper_wallet_simulate_withdrawal(
                            PAPER_WALLET, asset=str(payload.get("asset") or "PAPER_USD"),
                            amount=payload.get("amount"), usd_rate=payload.get("usd_rate"))
                    elif parsed.path == "/api/paper/transfer-bot-simulated":
                        direction = str(payload.get("direction") or "wallet_to_bot")
                        with HALAL_BOT_LOCK:
                            if direction == "wallet_to_bot":
                                result = ml.paper_transfer_wallet_to_bot(
                                    PAPER_WALLET, HALAL_BOT, amount=payload.get("amount"))
                            elif direction == "bot_to_wallet":
                                result = ml.paper_transfer_bot_to_wallet(
                                    PAPER_WALLET, HALAL_BOT, amount=payload.get("amount"))
                            else:
                                raise ValueError("direction must be wallet_to_bot or bot_to_wallet")
                            result["bot_state_saved_locally"] = _save_halal_bot()
                    elif parsed.path == "/api/paper/order":
                        result = ml.paper_wallet_order(
                            PAPER_WALLET, symbol=payload.get("symbol"), side=payload.get("side"),
                            price=payload.get("price"), quantity=payload.get("quantity"),
                            quote_amount=payload.get("quote_amount"),
                            fee_bps=float(payload.get("fee_bps", 10)),
                            timestamp=payload.get("timestamp"))
                    elif parsed.path == "/api/paper/follow":
                        if not isinstance(payload.get("following"), bool):
                            raise ValueError("following must be true or false")
                        result = ml.paper_wallet_set_following(
                            PAPER_WALLET, following=payload["following"])
                    elif parsed.path == "/api/paper/stop":
                        prices = payload.get("prices") or {}
                        if not isinstance(prices, dict):
                            raise ValueError("prices must be an object when supplied")
                        result = ml.paper_wallet_stop(
                            PAPER_WALLET, close_all=bool(payload.get("close_all")),
                            prices=prices, fee_bps=float(payload.get("fee_bps", 10)))
                    else:  # follow-step
                        if payload.get("bars") is not None:
                            paper_bars = payload["bars"]
                        elif payload.get("csv_text"):
                            paper_bars = ml.parse_csv(str(payload["csv_text"]))
                        else:
                            raise ValueError("supply bars[] or csv_text for the paper follow-step")
                        result = ml.paper_follow_step(
                            PAPER_WALLET, symbol=payload.get("symbol"), bars=paper_bars,
                            timeframe=str(payload.get("timeframe") or "source"),
                            strategy=str(payload.get("strategy") or "consensus"),
                            allocation_pct=float(payload.get("allocation_pct", 10)),
                            fee_bps=float(payload.get("fee_bps", 10)),
                            drop_last_bar=bool(payload.get("drop_last_bar")))
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if parsed.path == "/api/pipeline/import":
                series = payload.get("series")
                if not isinstance(series, list) or not series:
                    raise ValueError("supply series[] with {symbol, interval, bars}")
                if len(series) > 12:
                    raise ValueError("at most 12 series per import")
                venue = str(payload.get("venue") or "browser")
                stored, inserted = [], 0
                with MARKET_DB_LOCK:
                    db = _market_db()
                    for item in series:
                        if not isinstance(item, dict) or not item.get("bars"):
                            raise ValueError("each series needs a bars[] list")
                        symbol = str(item.get("symbol") or "browser.series")
                        interval = str(item.get("interval") or "source")
                        if interval not in pl.INTERVAL_MINUTES:
                            interval = "source"
                        key = pl.storage_symbol(venue, symbol, interval)
                        duplicate = pl.find_duplicate_series(db, item["bars"])
                        if duplicate:
                            stored.append({"symbol": key, "interval": interval,
                                           "stored_total": 0, "duplicate_of": duplicate,
                                           "skipped": True})
                            continue
                        result = db.import_bars(
                            symbol=key, timeframe=interval, bars=item["bars"],
                            source=str(item.get("source_label")
                                       or f"{venue} public API via browser (allowlisted venue)")[:300],
                            instrument={"symbol": key, "asset_type": "crypto",
                                        "exchange": venue if venue in pl.VENUES else "browser",
                                        "source": str(item.get("endpoint") or "")[:300]})
                        run = db.record_collection({
                            "venue": venue, "symbol": key, "timeframe": interval,
                            "requested": len(item["bars"]),
                            "inserted": int(result.get("bars_imported_or_updated") or 0),
                            "previously_stored": 0,
                            "stored_total": len(db.get_bars(key, interval)),
                            "first_bar_time": result.get("first_bar_time"),
                            "last_bar_time": result.get("last_bar_time"),
                            "endpoints": [item.get("endpoint")] if item.get("endpoint") else [],
                            "errors": [], "requests": 1})
                        inserted += int(result.get("bars_imported_or_updated") or 0)
                        stored.append({"symbol": key, "interval": interval,
                                       "stored_total": len(db.get_bars(key, interval)),
                                       "collection_run_id": run["id"],
                                       "first_bar": result.get("first_bar_time"),
                                       "last_bar": result.get("last_bar_time")})
                result = {"mode": "browser_import", "venue": venue, "series": stored,
                          "inserted_total": inserted,
                          "provenance": payload.get("provenance"),
                          "server_received_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(
                              timespec="seconds").replace("+00:00", "Z"),
                          "next_step": "POST /api/lab/auto-research then GET /api/goal-progress"}
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if parsed.path == "/api/pipeline/collect":
                plan = pl.plan_collection(
                    payload.get("symbols"), payload.get("interval", "1m"),
                    payload.get("target_bars", 3000), payload.get("venue", "binance"))
                with MARKET_DB_LOCK:
                    result = pl.collect_plan(_market_db(), plan)
                result["mode"] = "server_collection"
                result["network_note"] = ("The server fetches only these allowlisted hosts. "
                                          "If your environment blocks them, use browser collection.")
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if parsed.path == "/api/lab/auto-research":
                methods = payload.get("methods")
                if isinstance(methods, str):
                    methods = [m.strip() for m in methods.split(",") if m.strip()]
                raw_horizons = payload.get("horizons", [3, 5, 15])
                if isinstance(raw_horizons, str):
                    raw_horizons = [int(x) for x in raw_horizons.split(",") if x.strip()]
                with MARKET_DB_LOCK:
                    db = _market_db()
                    progress = pl.goal_progress(
                        db, methods=methods, horizons=tuple(int(h) for h in raw_horizons),
                        cost_bps=float(payload.get("cost_bps") or 10.0),
                        attempts=int(payload.get("attempts") or 150))
                    progress["stored_report_id"] = db.record_goal_report(progress)["id"]
                    progress["pipeline_stats"] = db.stats()["pipeline"]
                progress["mode"] = "auto_research"
                progress["disclaimer"] = DISCLAIMER
                self._json(200, progress)
                return
            if parsed.path == "/api/lab/holdout":
                symbol = str(payload.get("symbol") or "").strip()
                if not symbol:
                    raise ValueError("supply the stored symbol, e.g. BINANCE.BTCUSDT.1m")
                interval = str(payload.get("interval") or "").strip()
                if not interval:
                    parts = symbol.split(".")
                    interval = parts[-1] if len(parts) >= 3 else "1m"
                methods = payload.get("methods")
                if isinstance(methods, str):
                    methods = [m.strip() for m in methods.split(",") if m.strip()]
                raw_horizons = payload.get("horizons", [3, 5, 15])
                if isinstance(raw_horizons, str):
                    raw_horizons = [int(x) for x in raw_horizons.split(",") if x.strip()]
                with MARKET_DB_LOCK:
                    db = _market_db()
                    if not db.get_bars(symbol, interval):
                        raise ValueError(f"no stored bars for '{symbol}' at '{interval}'")
                    result = pl.holdout_evaluation(
                        db, venue=str(payload.get("venue") or symbol.split(".")[0].lower()),
                        symbol=symbol.split(".")[1] if symbol.count(".") >= 2 else symbol,
                        interval=interval, methods=methods,
                        horizons=tuple(int(h) for h in raw_horizons),
                        cost_bps=float(payload.get("cost_bps") or 10.0),
                        attempts=int(payload.get("attempts") or 150))
                    result["holdout_uses_total"] = db.holdout_use_count()
                result["mode"] = "holdout_evaluation"
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if parsed.path == "/api/lessons/clear":
                symbol = payload.get("symbol")
                with MARKET_DB_LOCK:
                    result = _market_db().clear_lessons(symbol=str(symbol) if symbol else None)
                result["note"] = ("Lessons forgotten. They are only a memory of measured failures, "
                                  "not a market signal; clear them only with new data or new methods.")
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            # ---- v17 new POST endpoints ----
            if parsed.path == "/api/lab/predict-failure":
                methods = payload.get("methods") or ["atlas_minute_pulse"]
                horizons = payload.get("horizons") or [3,5,15]
                symbol = payload.get("symbol") or "supplied-series"
                with MARKET_DB_LOCK:
                    prior = _market_db().lessons_for_carry_over(symbol)
                predictions = {}
                for m in methods:
                    for h in horizons:
                        pred = evo.predict_failure_probability((m, int(h)), prior)
                        predictions[f"{m}@{h}"] = pred
                self._json(200, {"mode": "failure_prediction", "symbol": symbol, "predictions": predictions, "prior_lessons": len(prior), "disclaimer": DISCLAIMER})
                return
            if parsed.path == "/api/lab/remedy-verify":
                before = payload.get("before_causes") or []
                after = payload.get("after_causes") or []
                patch = payload.get("patch") or {}
                verification = diag.remedy_verification(before, after, patch)
                # optionally record
                if payload.get("record"):
                    with MARKET_DB_LOCK:
                        db = _market_db()
                        db.record_remedy_verification({"lesson_uid": payload.get("lesson_uid") or "manual", "symbol": payload.get("symbol") or "manual", "before": {"causes": before}, "after": {"causes": after}, "verdict": verification["verdict"], "confidence": verification["confidence"]})
                self._json(200, {"mode": "remedy_verification", "verification": verification, "disclaimer": DISCLAIMER})
                return
            if parsed.path == "/api/lab/bootstrap":
                values = payload.get("values") or []
                if not values:
                    raise ValueError("supply values[] for bootstrap")
                ci = ml.bootstrap_mean_ci(values, n_bootstrap=int(payload.get("n_bootstrap") or 1000))
                self._json(200, {"mode": "bootstrap_ci", "result": ci, "disclaimer": DISCLAIMER})
                return
            if parsed.path == "/api/lab/permutation":
                hits = int(payload.get("hits") or 0)
                total = int(payload.get("total") or 0)
                if total <= 0:
                    raise ValueError("supply hits and total")
                perm = ml.permutation_pvalue(hits, total, n_perm=int(payload.get("n_perm") or 2000))
                self._json(200, {"mode": "permutation_test", "result": perm, "disclaimer": DISCLAIMER})
                return
            if parsed.path == "/api/diagnostics/explain":
                cause = payload.get("cause") or "baseline_not_beaten"
                evidence = payload.get("evidence") or ""
                evaluation = payload.get("evaluation")
                explanation = diag.explain_failure(cause, evidence, evaluation)
                if payload.get("record"):
                    with MARKET_DB_LOCK:
                        db = _market_db()
                        db.record_diagnostic_report({"symbol": payload.get("symbol") or "manual", "cause": cause, "report": explanation})
                self._json(200, {"mode": "diagnostic_explanation", "explanation": explanation, "spec": diag.diagnostics_spec(), "disclaimer": DISCLAIMER})
                return
            if parsed.path == "/api/evolution/record":
                symbol = payload.get("symbol") or "manual"
                generation = int(payload.get("generation") or 1)
                lessons = payload.get("lessons") or []
                with MARKET_DB_LOCK:
                    db = _market_db()
                    clustered = evo.failure_cluster(lessons)
                    db.record_failure_cluster({"symbol": symbol, "dominant_cause": clustered.get("dominant_cause") or "unknown", "cluster": clustered, "lessons_count": len(lessons)})
                    db.record_evolution({"generation": generation, "symbol": symbol, "lessons_total": len(lessons), "resolved": sum(1 for l in lessons if l.get("status")=="resolved"), "retired": sum(1 for l in lessons if l.get("status")=="retired"), "accuracy_trend": payload.get("accuracy_trend") or [], "metrics": payload.get("metrics") or {}})
                self._json(200, {"mode": "evolution_recorded", "cluster": clustered, "disclaimer": DISCLAIMER})
                return
            if parsed.path == "/api/lab/self-correct":
                if payload.get("demo"):
                    result = sc.demo_self_correction()
                    result["disclaimer"] = DISCLAIMER
                    if payload.get("remember", False):
                        with MARKET_DB_LOCK:
                            result["memory"] = _market_db().save_self_correction(result)
                    self._json(200, result)
                    return
                primary = payload.get("bars")
                if primary is None and payload.get("csv_text"):
                    primary = ml.parse_csv(str(payload["csv_text"]))
                if primary is None:
                    raise ValueError("supply bars[] or csv_text for the self-correction run")
                second = payload.get("second_bars") or payload.get("validation_bars")
                if second is None and payload.get("second_csv_text"):
                    second = ml.parse_csv(str(payload["second_csv_text"]))
                series = [{"symbol": str(payload.get("symbol") or "supplied-series"), "bars": primary}]
                if second is not None:
                    series.append({"symbol": str(payload.get("second_symbol")
                                             or "validation-series"), "bars": second})
                symbol_key = series[0]["symbol"]
                prior_lessons = None
                if payload.get("use_saved_lessons", True):
                    with MARKET_DB_LOCK:
                        prior_lessons = _market_db().lessons_for_carry_over(symbol_key)
                raw_methods = payload.get("methods")
                if isinstance(raw_methods, str):
                    raw_methods = [m.strip() for m in raw_methods.split(",") if m.strip()]
                raw_horizons = payload.get("horizons", (3, 5, 15))
                if isinstance(raw_horizons, str):
                    raw_horizons = [int(x.strip()) for x in raw_horizons.split(",") if x.strip()]
                config = payload.get("config") if isinstance(payload.get("config"), dict) else {}
                if payload.get("attempts"):
                    config = {**config, "attempts": int(payload["attempts"])}
                if payload.get("cost_bps"):
                    config = {**config, "cost_bps": float(payload["cost_bps"])}
                result = sc.run_self_correction(
                    series, config=config, methods=raw_methods,
                    horizons=tuple(int(h) for h in raw_horizons),
                    prior_lessons=prior_lessons,
                    rounds=int(payload.get("rounds") or sc.MAX_ROUNDS))
                result["source_label"] = str(payload.get("source_label") or "user-supplied OHLCV data")[:160]
                provenance = payload.get("provenance")
                if isinstance(provenance, dict):
                    allowed = ("venue", "primary_symbol", "validation_symbol", "interval",
                               "primary_bars", "validation_bars", "first_bar_utc",
                               "last_bar_utc", "fetched_at_utc", "forming_candle_dropped",
                               "primary_url", "validation_url", "validation_error",
                               "requested_bars")
                    result["provenance"] = {k: provenance.get(k) for k in allowed if k in provenance}
                    result["provenance"]["server_received_at_utc"] = dt.datetime.now(
                        dt.timezone.utc).isoformat().replace("+00:00", "Z")
                if payload.get("remember", True):
                    with MARKET_DB_LOCK:
                        result["memory"] = _market_db().save_self_correction(result)
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            options = self._lab_options(payload)
            if parsed.path == "/api/lab/watchlist":
                result = ml.analyze_watchlist(
                    payload.get("symbols"), strategy=options["strategy"])
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if payload.get("bars") is not None:
                bars = payload["bars"]
            elif payload.get("csv_text"):
                bars = ml.parse_csv(str(payload["csv_text"]))
            else:
                raise ValueError("supply bars[] or csv_text")
            source_label = str(payload.get("source_label") or "user-supplied OHLCV data")[:160]
            if parsed.path == "/api/lab/minute-forecast":
                raw_horizons = payload.get("horizons") or (1, 3, 5, 15, 30)
                if isinstance(raw_horizons, str):
                    horizons = tuple(int(x.strip()) for x in raw_horizons.split(",") if x.strip())
                elif isinstance(raw_horizons, list):
                    horizons = tuple(int(x) for x in raw_horizons)
                else:
                    horizons = tuple(raw_horizons)
                if not horizons or len(horizons) > 10 or any(h <= 0 or h > 500 for h in horizons):
                    raise ValueError("horizons must contain 1-10 positive bar counts up to 500")
                result = ml.minute_forecast_eval(
                    bars, attempts=int(payload.get("attempts") or 1000), horizons=horizons,
                    min_history=int(payload.get("min_history") or 240),
                    target_accuracy_pct=float(payload.get("target_accuracy_pct") or ml.ACCURACY_TARGET_PCT))
                result["source"] = source_label
                result["source_label"] = source_label
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            if parsed.path == "/api/lab/forecast":
                result = ml.forecast_lab(
                    bars,
                    attempts=max(10, min(300, int(payload.get("attempts") or 100))),
                    horizon=max(1, min(60, int(payload.get("horizon") or 5))),
                    top_n=max(10, min(100, int(payload.get("top_n") or 30))),
                    min_history=max(60, min(1000, int(payload.get("min_history") or 200))),
                    sim_horizon=max(5, min(120, int(payload.get("sim_horizon") or 20))),
                    sim_paths=max(100, min(5000, int(payload.get("sim_paths") or 500))))
                result["source_label"] = source_label
                result["disclaimer"] = DISCLAIMER
                self._json(200, result)
                return
            result = ml.analyze_market(bars, source_label=source_label, **options)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            self._json(400, {"error": str(exc), "disclaimer": DISCLAIMER})
            return
        result["disclaimer"] = DISCLAIMER
        self._json(200, result)


def main() -> int:
    ap = argparse.ArgumentParser(description="TradeAtlas — educational trading-strategy atlas (not financial advice)")
    ap.add_argument("--serve", action="store_true", help="run the web UI")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8820)
    ap.add_argument("--demo", action="store_true", help="write sample-home.html, sample-atlas.json and synthetic Market Lab validation")
    ap.add_argument("--collect", action="store_true",
                    help="fetch bars by itself from an allowlisted public venue into SQLite")
    ap.add_argument("--auto", action="store_true",
                    help="collect + measure repeatedly (needs network); honest 80%% progress report each cycle")
    ap.add_argument("--venue", default="binance", choices=sorted(pl.VENUES))
    ap.add_argument("--symbols", default="", help="comma-separated symbols (venue defaults if empty)")
    ap.add_argument("--interval", default="1m", choices=sorted(pl.INTERVAL_MINUTES))
    ap.add_argument("--target-bars", type=int, default=3000)
    ap.add_argument("--cycles", type=int, default=1)
    ap.add_argument("--sleep", type=float, default=60.0)
    ap.add_argument("--db", default=os.environ.get("TRADEATLAS_DB", "tradeatlas.db"))
    args = ap.parse_args()
    if args.collect or args.auto:
        db = MarketDatabase(args.db)
        try:
            plan = pl.plan_collection(args.symbols, args.interval, args.target_bars, args.venue)
            cycles = max(1, args.cycles) if args.auto else 1
            for cycle in range(1, cycles + 1):
                print(f"[cycle {cycle}/{cycles}] collecting {plan['symbols']} "
                      f"{plan['interval']} from {plan['venue']} …", flush=True)
                collected = pl.collect_plan(db, plan)
                print(json.dumps(collected, ensure_ascii=False,
                                 default=str)[:4000], flush=True)
                progress = pl.goal_progress(db)
                db.record_goal_report(progress)
                print(json.dumps({key: progress[key] for key in (
                    "status", "goal_established", "gates_passed", "gates_total",
                    "distance_to_target_points", "evidence")}, ensure_ascii=False), flush=True)
                print("NOTE: goal_established is always false — a local database "
                      "cannot prove a universal 80%.", flush=True)
                if cycle < cycles:
                    time.sleep(max(0.0, args.sleep))
        finally:
            db.close()
        return 0
    if args.demo:
        open("sample-home.html", "w", encoding="utf-8").write(render_home())
        open("sample-atlas.json", "w", encoding="utf-8").write(
            json.dumps(atlas_json(), ensure_ascii=False, indent=1))
        validation = ml.demo_analysis(strategy="atlas_minute_pulse", max_signals=100)
        validation["disclaimer"] = DISCLAIMER
        open("sample-lab-validation.json", "w", encoding="utf-8").write(
            json.dumps(validation, ensure_ascii=False, indent=1))
        synth = ml.forecast_lab(ml.generate_demo_bars("1d", count=4000, seed=42),
                                attempts=100, horizon=5)
        synth["source"] = "deterministic SYNTHETIC daily bars (seed 42) — software validation only"
        synth["source_is_synthetic"] = True
        open("sample-forecast-synthetic.json", "w", encoding="utf-8").write(
            json.dumps(synth, ensure_ascii=False, indent=1))
        minute_synth = ml.minute_forecast_eval(
            ml.generate_demo_bars("1m", count=4000, seed=14), attempts=1000,
            horizons=(1, 3, 5, 15, 30))
        minute_synth["source"] = "deterministic SYNTHETIC 1m bars (seed 14) — software validation only, never evidence toward the 80% goal"
        minute_synth["source_is_synthetic"] = True
        minute_synth["disclaimer"] = DISCLAIMER
        open("sample-minute-forecast-synthetic.json", "w", encoding="utf-8").write(
            json.dumps(minute_synth, ensure_ascii=False, indent=1))
        selfcorr = sc.demo_self_correction()
        selfcorr["disclaimer"] = DISCLAIMER
        open("sample-self-correction.json", "w", encoding="utf-8").write(
            json.dumps(selfcorr, ensure_ascii=False, indent=1))
        goals = ml.project_goals(); goals["disclaimer"] = DISCLAIMER
        open("sample-project-goals.json", "w", encoding="utf-8").write(
            json.dumps(goals, ensure_ascii=False, indent=1))
        paper_wallet = ml.new_paper_wallet(starting_balance=10_000)
        balance_deposit = ml.paper_wallet_simulate_crypto_deposit(
            paper_wallet, asset="BTC", crypto_amount=0.01, usd_rate=50_000)
        balance_conversion = ml.paper_wallet_convert_crypto_balance(
            paper_wallet, asset="BTC", crypto_amount=0.005, usd_rate=60_000, fee_bps=10)
        balance_withdrawal = ml.paper_wallet_simulate_withdrawal(
            paper_wallet, asset="BTC", amount=0.001, usd_rate=60_000)
        conversion = ml.paper_wallet_simulate_conversion(
            paper_wallet, asset="USDT", crypto_amount=250, usd_rate=1.0)
        external_usdt = ml.paper_wallet_record_external_balance(
            paper_wallet, venue_label="DEMO label for a user's own licensed account",
            asset="USDT", quantity=500, usd_rate=1.0, reported_at="synthetic-demo")
        external_btc = ml.paper_wallet_record_external_balance(
            paper_wallet, venue_label="DEMO label for a user's own licensed account",
            asset="BTC", quantity=0.01, usd_rate=50_000, reported_at="synthetic-demo")
        ml.paper_wallet_set_following(paper_wallet, following=True)
        paper_step = ml.paper_follow_step(
            paper_wallet, symbol="SYNTHETIC-DEMO",
            bars=ml.generate_demo_bars("1m", count=2500, seed=13),
            strategy="atlas_minute_pulse", timeframe="1m", allocation_pct=5, fee_bps=10)
        stopped = ml.paper_wallet_stop(paper_wallet)
        paper_sample = {
            "mode": "paper_simulation_only",
            "source": "deterministic SYNTHETIC bars — software/wallet arithmetic validation only",
            "simulated_balance_deposit": balance_deposit,
            "simulated_balance_conversion": balance_conversion,
            "simulated_balance_withdrawal": balance_withdrawal,
            "conversion": conversion,
            "external_account_mirror_usdt": external_usdt,
            "external_account_mirror_btc": external_btc,
            "follow_step": paper_step,
            "wallet_after_stop": stopped,
            "warning": "No real deposit, conversion, custody or order occurred.",
            "disclaimer": DISCLAIMER,
        }
        open("sample-paper-wallet.json", "w", encoding="utf-8").write(
            json.dumps(paper_sample, ensure_ascii=False, indent=1))
        bot = ml.new_halal_paper_bot(starting_balance=10_000, preset="strict")
        synthetic_profile = {
            "symbol": "TEST", "company_name": "SYNTHETIC test company (not real)",
            "asset_type": "stock", "sector": "synthetic", "core_business_prohibited": False,
            "activities_reviewed": True, "prohibited_activities": [],
            "interest_bearing_debt_pct_of_market_cap": 10,
            "interest_bearing_cash_securities_pct_of_market_cap": 5,
            "receivables_pct_of_market_cap": 20,
            "non_compliant_income_pct_of_revenue": 1,
            "source_note": "INVENTED unit-test figures — not a real company and not a screen of any listed stock",
            "financials_as_of": "synthetic",
        }
        bot_registration = ml.halal_bot_register_stock(bot, synthetic_profile)
        ml.halal_bot_set_status(bot, action="start")
        bot_bars = ml.generate_demo_bars("1m", count=2500, seed=13)
        bot_step = ml.halal_bot_step(bot, market_data={"TEST": bot_bars})
        bot_after_stop = ml.halal_bot_stop(
            bot, close_all=True, prices={"TEST": float(bot_bars[-1]["c"])}, fee_bps=10)
        bot_sample = {
            "mode": "halal_paper_bot_only",
            "source": "deterministic SYNTHETIC bars and an INVENTED company profile — software arithmetic only",
            "registration": bot_registration,
            "step": bot_step,
            "bot_after_stop_close_all": bot_after_stop,
            "warning": "No real company was screened and no real order occurred. A screen pass is not a fatwa/certification.",
            "disclaimer": DISCLAIMER,
        }
        open("sample-halal-paper-bot.json", "w", encoding="utf-8").write(
            json.dumps(bot_sample, ensure_ascii=False, indent=1))
        demo_db = MarketDatabase(":memory:")
        demo_seed = demo_db.seed_bundled_data(os.path.dirname(os.path.abspath(__file__)))
        demo_research = demo_db.research_all(attempts=100)
        database_sample = {
            "mode": "sqlite_market_database_demo",
            "source": "bundled REAL historical samples only; in-memory demo database, not the user's private tradeatlas.db",
            "seed": demo_seed,
            "research": demo_research,
            "warning": "Pooled old samples are correlated/survivor-biased. This is not an 80% forecast claim.",
            "disclaimer": DISCLAIMER,
        }
        demo_db.close()
        open("sample-database-research.json", "w", encoding="utf-8").write(
            json.dumps(database_sample, ensure_ascii=False, indent=1))
        import os as _os
        real_path = _os.path.join("real-data", "aapl-daily-2015-2017.plotly.csv")
        if _os.path.exists(real_path):
            real_bars = ml.parse_csv(open(real_path, encoding="utf-8").read())
            real = ml.forecast_lab(real_bars, attempts=100, horizon=5)
            real["source"] = ("REAL historical AAPL daily bars 2015-02-17..2017-02-16 from the "
                              "public plotly/datasets sample (adjusted OHLC; see "
                              "real-data/REAL-DATA-NOTICE.md). Historical snapshot, not live data.")
            real["source_is_synthetic"] = False
            real["market_analysis_1d_1w"] = ml.analyze_market(
                real_bars, strategy="consensus", max_signals=100,
                source_label="bundled real AAPL daily sample (see REAL-DATA-NOTICE.md)")
            open("sample-forecast-real-aapl.json", "w", encoding="utf-8").write(
                json.dumps(real, ensure_ascii=False, indent=1))
        msft_path = _os.path.join("real-data", "vega-msft-monthly-2000-2010.csv")
        if _os.path.exists(msft_path):
            msft_bars = ml.parse_csv(open(msft_path, encoding="utf-8").read())
            msft = ml.forecast_lab(msft_bars, attempts=40, horizon=3, min_history=60,
                                   eval_horizons=(1, 3, 6), sim_horizon=12, sim_paths=500)
            msft["source"] = ("REAL historical MSFT MONTHLY closes 2000-2010 from the public "
                              "vega/vega-datasets sample (close-only, survivor-biased teaching "
                              "data; see real-data/REAL-DATA-NOTICE.md). Monthly bars: horizons "
                              "are months. Historical snapshot, not live data.")
            msft["source_is_synthetic"] = False
            open("sample-forecast-real-msft-monthly.json", "w", encoding="utf-8").write(
                json.dumps(msft, ensure_ascii=False, indent=1))
        print("Wrote sample-home.html + sample-atlas.json + sample-lab-validation.json (synthetic)"
              " + sample-forecast-synthetic.json + sample-minute-forecast-synthetic.json + sample-project-goals.json + sample-paper-wallet.json + sample-halal-paper-bot.json + sample-database-research.json"
              " + sample-forecast-real-aapl.json + sample-forecast-real-msft-monthly.json (real samples)")
        return 0
    if args.serve:
        srv = ThreadingHTTPServer((args.host, args.port), Handler)
        print(f"TradeAtlas v{VERSION} serving on http://{args.host}:{args.port} "
              f"(educational only — not financial advice)")
        srv.serve_forever()
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
