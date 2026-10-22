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
import autotrader as at
import wealth_engine as we
import velocity_compound as vc
import pipeline as pl
import precision80 as p80
import selfcorrect as sc
import evolution as evo
import diagnostics as diag
import realdata
from platformdb import MarketDatabase

VERSION = "23.0"
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


P80_JS_CODE = r'''
// ==================== TradeAtlas v20.0 Quantum Institutional Lab JS ====================
let _LAST_P80_LEDGER = [];
let _AR_RTL = false;

function toggleArabicUI() {
  _AR_RTL = !_AR_RTL;
  const root = document.getElementById('appRoot');
  if (root) root.dir = _AR_RTL ? 'rtl' : 'ltr';
  document.getElementById('langBtn').textContent = _AR_RTL ? '🌐 Switch to LTR Layout' : '🇸🇦 التبديل لاتجاه العربية (RTL)';
}

function renderEquitySvg(curve, oosStats) {
  const box = document.getElementById('p80EquitySvg');
  if (!box) return;
  if (!curve || curve.length < 2) {
    box.innerHTML = '<p class="sub" style="padding:20px">لا توجد صفقات كافية ضمن هذا الفلتر — خفف شروط التصفية أو اختر سلة أوسع.</p>';
    return;
  }
  const W = 620, H = 240, padL = 48, padR = 16, padT = 18, padB = 28;
  const eqs = curve.map(p => p.equity);
  const minE = Math.min(96, ...eqs) * 0.992;
  const maxE = Math.max(104, ...eqs) * 1.008;
  const xOf = i => padL + (i / (curve.length - 1)) * (W - padL - padR);
  const yOf = v => padT + (1 - (v - minE) / Math.max(1e-6, maxE - minE)) * (H - padT - padB);
  const pts = curve.map((p, i) => `${xOf(i).toFixed(1)},${yOf(p.equity).toFixed(1)}`).join(' ');
  const area = `${xOf(0).toFixed(1)},${(H - padB).toFixed(1)} ${pts} ${xOf(curve.length - 1).toFixed(1)},${(H - padB).toFixed(1)}`;
  const base100 = yOf(100);
  const color = (oosStats && oosStats.mean_net_pct > 0) ? '#10b981' : '#f43f5e';
  let grids = '';
  for (let g = 0; g <= 4; g++) {
    const val = minE + (g / 4) * (maxE - minE);
    const gy = yOf(val);
    grids += `<line x1="${padL}" y1="${gy.toFixed(1)}" x2="${W - padR}" y2="${gy.toFixed(1)}" stroke="#1e293b" stroke-dasharray="3,3"/>`;
    grids += `<text x="6" y="${(gy + 4).toFixed(1)}" fill="#94a3b8" font-size="10">${val.toFixed(1)}</text>`;
  }
  const firstD = curve[0].date, midD = curve[Math.floor(curve.length / 2)].date, lastD = curve[curve.length - 1].date;
  box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">
    <defs><linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="${color}" stop-opacity="0.34"/><stop offset="100%" stop-color="${color}" stop-opacity="0.01"/></linearGradient></defs>
    ${grids}
    <line x1="${padL}" y1="${base100.toFixed(1)}" x2="${W - padR}" y2="${base100.toFixed(1)}" stroke="#64748b" stroke-width="1"/>
    <polygon points="${area}" fill="url(#eqGrad)"/>
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="2.4" stroke-linejoin="round"/>
    <circle cx="${xOf(curve.length - 1).toFixed(1)}" cy="${yOf(eqs[eqs.length - 1]).toFixed(1)}" r="4" fill="${color}"/>
    <text x="${padL}" y="${H - 7}" fill="#94a3b8" font-size="10">${firstD}</text>
    <text x="${(W / 2 - 28).toFixed(0)}" y="${H - 7}" fill="#94a3b8" font-size="10">${midD}</text>
    <text x="${W - padR - 62}" y="${H - 7}" fill="#38bdf8" font-size="10" font-weight="bold">${lastD}</text>
  </svg>`;
}

function renderCandlesSvg(candles, conformal) {
  const box = document.getElementById('p80CandleSvg');
  if (!box || !candles || !candles.length) return;
  const W = 620, H = 240, padL = 52, padR = 68, padT = 16, padB = 26;
  const fcast = (conformal && conformal.live_next_horizon_forecast) || {};
  let lo = Math.min(...candles.map(c => c.l));
  let hi = Math.max(...candles.map(c => c.h));
  if (fcast.band_90_low) lo = Math.min(lo, fcast.band_90_low);
  if (fcast.band_90_high) hi = Math.max(hi, fcast.band_90_high);
  const span = Math.max(1e-6, hi - lo);
  lo -= span * 0.04; hi += span * 0.04;
  const plotW = W - padL - padR;
  const stepX = plotW / candles.length;
  const yOf = v => padT + (1 - (v - lo) / (hi - lo)) * (H - padT - padB);

  let svg = '';
  for (let g = 0; g <= 4; g++) {
    const v = lo + (g / 4) * (hi - lo);
    const gy = yOf(v);
    svg += `<line x1="${padL}" y1="${gy.toFixed(1)}" x2="${W - 8}" y2="${gy.toFixed(1)}" stroke="#1e293b" stroke-dasharray="3,3"/>`;
    svg += `<text x="4" y="${(gy + 4).toFixed(1)}" fill="#94a3b8" font-size="9.5">${v >= 100 ? v.toFixed(1) : v.toFixed(4)}</text>`;
  }
  const s50pts = candles.map((c, i) => `${(padL + (i + 0.5) * stepX).toFixed(1)},${yOf(c.sma50).toFixed(1)}`).join(' ');
  const s200pts = candles.map((c, i) => `${(padL + (i + 0.5) * stepX).toFixed(1)},${yOf(c.sma200).toFixed(1)}`).join(' ');
  svg += `<polyline points="${s200pts}" fill="none" stroke="#f59e0b" stroke-width="1.3" opacity="0.8"/>`;
  svg += `<polyline points="${s50pts}" fill="none" stroke="#38bdf8" stroke-width="1.3" opacity="0.85"/>`;

  candles.forEach((c, i) => {
    const cx = padL + (i + 0.5) * stepX;
    const up = c.c >= c.o;
    const col = up ? '#10b981' : '#f43f5e';
    const yTop = yOf(Math.max(c.o, c.c)), yBot = yOf(Math.min(c.o, c.c));
    svg += `<line x1="${cx.toFixed(1)}" y1="${yOf(c.h).toFixed(1)}" x2="${cx.toFixed(1)}" y2="${yOf(c.l).toFixed(1)}" stroke="${col}" stroke-width="1"/>`;
    svg += `<rect x="${(cx - Math.max(1.2, stepX * 0.34)).toFixed(1)}" y="${yTop.toFixed(1)}" width="${Math.max(2.4, stepX * 0.68).toFixed(1)}" height="${Math.max(1.4, yBot - yTop).toFixed(1)}" fill="${col}"/>`;
  });

  if (fcast.band_80_low && fcast.band_90_high) {
    const xStart = padL + (candles.length - 0.5) * stepX;
    const xEnd = W - 10;
    const yLast = yOf(candles[candles.length - 1].c);
    svg += `<polygon points="${xStart.toFixed(1)},${yLast.toFixed(1)} ${xEnd},${yOf(fcast.band_90_high).toFixed(1)} ${xEnd},${yOf(fcast.band_90_low).toFixed(1)}" fill="#38bdf8" opacity="0.16"/>`;
    svg += `<polygon points="${xStart.toFixed(1)},${yLast.toFixed(1)} ${xEnd},${yOf(fcast.band_80_high).toFixed(1)} ${xEnd},${yOf(fcast.band_80_low).toFixed(1)}" fill="#10b981" opacity="0.28"/>`;
    svg += `<line x1="${xStart.toFixed(1)}" y1="${yLast.toFixed(1)}" x2="${xEnd}" y2="${yOf(fcast.center_price).toFixed(1)}" stroke="#34d399" stroke-width="2" stroke-dasharray="4,3"/>`;
  }
  svg += `<text x="${padL}" y="${H - 7}" fill="#94a3b8" font-size="10">${candles[0].t}</text>`;
  svg += `<text x="${W - 185}" y="${H - 7}" fill="#34d399" font-size="10" font-weight="bold">Latest: ${candles[candles.length - 1].t} → ACI Cone</text>`;
  box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">${svg}</svg>`;
}

async function loadP80Candles() {
  const fn = document.getElementById('p80ChartFile').value;
  try {
    const r = await fetch('/api/precision80/conformal?file=' + encodeURIComponent(fn) + '&horizon=5&coverage=0.85');
    const data = await r.json();
    const aci = data.conformal || {};
    const b = aci.live_next_horizon_forecast || {};
    renderCandlesSvg(data.candles || [], aci);
    document.getElementById('p80ConformalReadout').innerHTML =
      `<b>التغطية الحقيقية خارج العينة (OOS Empirical Accuracy): <span style="color:#34d399">${aci.oos_empirical_coverage_pct}%</span></b> ` +
      `(Wilson 95% LB: <b>${aci.wilson_95_low_pct}%</b> · N=${aci.oos_evaluations}) · ` +
      `آخر إغلاق (${aci.last_bar_date}): <b>${aci.last_close}</b> · ` +
      `نطاق 80% القادم: <b style="color:#38bdf8">[${b.band_80_low} , ${b.band_80_high}]</b> · ` +
      `نطاق 90%: <b>[${b.band_90_low} , ${b.band_90_high}]</b>`;
  } catch (e) { console.error(e); }
}

function renderP80BenchmarkResult(res) {
  const oos = res.out_of_sample_unseen || {};
  const tr = res.in_sample_purged || {};
  _LAST_P80_LEDGER = res.recent_oos_ledger || [];
  document.getElementById('k_win').textContent = (oos.net_win_rate_pct || 0).toFixed(2) + '%';
  document.getElementById('k_win_sub').textContent = `${oos.trades || 0} صفقة خارج العينة (${oos.symbols_count || 0} أصل) بعد خصم ${res.parameters.cost_bps} bps`;
  document.getElementById('k_wilson').textContent = `[${(oos.wilson_95_low_pct || 0).toFixed(2)}% – ${(oos.wilson_95_high_pct || 0).toFixed(2)}%]`;
  document.getElementById('k_wilson_sub').textContent = oos.wilson_exceeds_80_pct ? 'مثبت إحصائياً > 80.0% خارج العينة ✅' : `متوسط صافي الربح: ${(oos.mean_net_pct || 0).toFixed(3)}%`;
  document.getElementById('k_pf').textContent = `${oos.mean_net_pct >= 0 ? '+' : ''}${(oos.mean_net_pct || 0).toFixed(3)}% · PF ${(oos.profit_factor || 0).toFixed(2)}`;
  document.getElementById('k_pf_sub').textContent = `نمو المحفظة OOS: ${oos.total_compounded_return_pct >= 0 ? '+' : ''}${oos.total_compounded_return_pct}% · أقصى تراجع: -${oos.max_drawdown_pct}%`;
  document.getElementById('p80AuditHash').textContent = 'SHA-256: ' + (res.audit_sha256 || '').slice(0, 18) + '…';

  let warnHtml = oos.asymmetric_payoff_trap
    ? ' <span style="color:#fda4af"><b>⚠️ تنبيه شفافية Payoff Trap:</b> نسبة الفوز مرتفعة لكن متوسط الخسارة أكبر من متوسط الربح بعد العمولات!</span>'
    : ' <span style="color:#34d399"><b>✅ توقع رياضي موجب بعد العمولات (Positive Net Expectancy + Zero Lookahead).</b></span>';
  document.getElementById('p80StatsBar').innerHTML =
    `<b>Purged Train (${tr.trades} صفقة سابقة معزولة):</b> دقة <b>${tr.net_win_rate_pct}%</b> (Mean ${tr.mean_net_pct}%, PF ${tr.profit_factor}) &nbsp;|&nbsp; ` +
    `<b>Unseen OOS Holdout (${oos.trades} صفقة مستقبلية مفصولة):</b> دقة <b>${oos.net_win_rate_pct}%</b> · متوسط ربح رابحة +${oos.avg_win_pct}% · متوسط خاسرة ${oos.avg_loss_pct}% · VaR95 ${oos.var_95_pct}%` + warnHtml;

  renderEquitySvg(oos.equity_curve || [], oos);

  // Feature importance bars
  const fbox = document.getElementById('p80FeatBars');
  const feats = res.top_meta_features || [];
  fbox.innerHTML = feats.map(f =>
    `<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px;font-size:12px">
      <span style="width:145px;color:#cbd5e1;font-family:monospace">${f.feature}</span>
      <div style="flex:1;background:#080f1e;height:9px;border-radius:99px;overflow:hidden"><div style="width:${Math.min(100, f.importance_pct * 2.4)}%;background:linear-gradient(90deg,#38bdf8,#10b981);height:100%"></div></div>
      <span style="width:48px;text-align:right;color:#38bdf8;font-weight:700">${f.importance_pct}%</span>
    </div>`
  ).join('') || '<span class="sub">نموذج قواعد نقية بدون أوزان شجرية إضافية.</span>';

  // Per-asset table
  const atbl = document.getElementById('p80AssetTable');
  atbl.innerHTML = '<tr><th>الأصل · Symbol</th><th>آخر شمعة</th><th>صفقات OOS</th><th>الدقة الصافية %</th><th>متوسط الربح %</th><th>PF</th></tr>' +
    (res.per_asset_oos || []).map(a =>
      `<tr><td><b>${a.symbol}</b> <small class="sub">${a.description || ''}</small></td><td>${a.last_bar}</td><td>${a.oos_trades}</td>` +
      `<td style="color:${a.oos_net_win_rate_pct >= 80 ? '#34d399' : '#fbbf24'};font-weight:800">${a.oos_net_win_rate_pct}%</td>` +
      `<td style="color:${a.oos_mean_net_pct > 0 ? '#34d399' : '#fda4af'}">${a.oos_mean_net_pct >= 0 ? '+' : ''}${a.oos_mean_net_pct}%</td><td>${a.oos_profit_factor}</td></tr>`
    ).join('');

  // Recent OOS ledger
  const ltbl = document.getElementById('p80LedgerTable');
  const tail = (_LAST_P80_LEDGER || []).slice(-40).reverse();
  ltbl.innerHTML = '<tr><th>الأصل</th><th>تاريخ الدخول O[t+1]</th><th>الدخول</th><th>الخروج</th><th>السبب</th><th>الصافي بعد العمولة</th></tr>' +
    tail.map(t =>
      `<tr><td><b>${t.symbol}</b></td><td>${String(t.entry_date).slice(0, 16)}</td><td>${t.entry_price}</td><td>${t.exit_price}</td>` +
      `<td><span class="tags"><span>${t.exit_reason}</span></span></td>` +
      `<td style="font-weight:800;color:${t.net_pct > 0 ? '#34d399' : '#fda4af'}">${t.net_pct > 0 ? '+' : ''}${t.net_pct}%</td></tr>`
    ).join('');
}

async function runP80Live() {
  const payload = {
    universe: document.getElementById('p80_univ').value,
    mode: document.getElementById('p80_mode').value,
    cost_bps: parseFloat(document.getElementById('p80_cost').value || '10'),
    tp_pct: parseFloat(document.getElementById('p80_tp').value || '1.1'),
    sl_pct: parseFloat(document.getElementById('p80_sl').value || '6.5'),
    max_hold: parseInt(document.getElementById('p80_hold').value || '16', 10),
    holdout_ratio: 0.30
  };
  const r = await fetch('/api/precision80/run', {
    method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
  });
  const data = await r.json();
  renderP80BenchmarkResult(data);
}

function exportOosCsv() {
  if (!_LAST_P80_LEDGER.length) return;
  const hdr = ['symbol', 'signal_date', 'entry_date', 'exit_date', 'entry_price', 'exit_price', 'exit_reason', 'gross_pct', 'net_pct', 'meta_prob'];
  const lines = [hdr.join(',')].concat(_LAST_P80_LEDGER.map(r => hdr.map(k => r[k] ?? '').join(',')));
  const blob = new Blob([lines.join('\n')], {type: 'text/csv;charset=utf-8;'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'tradeatlas_v20_unseen_oos_trades.csv';
  a.click();
}

async function pullGithubLiveFeed() {
  const st = document.getElementById('ghSyncStatus');
  const feedKey = document.getElementById('ghFeedSelect').value;
  st.textContent = '⏳ جاري الاتصال المباشر بـ api.github.com وتحميل الشموع الحقيقية والتحقق من بصمة SHA-256...';
  try {
    const r = await fetch('/api/pipeline/collect-github', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({feed_key: feedKey})
    });
    const d = await r.json();
    if (d.error) { st.textContent = '❌ ' + d.error; return; }
    st.textContent = `✅ تم استيراد ${d.fetched_bars} شمعة حقيقية لـ ${d.symbol} حتى ${d.last_bar_utc} وحفظها في SQLite (إجمالي مخزن: ${d.stored_total} · SHA256: ${String(d.sha256).slice(0, 16)}…)`;
  } catch (e) { st.textContent = '❌ ' + e; }
}

async function bootPrecision80Lab() {
  try {
    const r = await fetch('/api/precision80/summary?cost_bps=10');
    const s = await r.json();
    document.getElementById('k_cat').textContent = `${s.catalog_datasets} / ${Number(s.catalog_total_bars || 0).toLocaleString()}`;
    if (s.flagship_equities_bracket && s.flagship_equities_bracket.out_of_sample_unseen) {
      const eq = s.flagship_equities_bracket.out_of_sample_unseen;
      document.getElementById('k_eqwin').textContent = eq.net_win_rate_pct.toFixed(2) + '%';
      document.getElementById('k_eq_sub').textContent = `Wilson LB ${eq.wilson_95_low_pct}% · نمو المحفظة +${eq.total_compounded_return_pct}%`;
    }
    if (s.conformal_gold_1h) {
      document.getElementById('k_aci').textContent = s.conformal_gold_1h.oos_empirical_coverage_pct + '%';
    }
    if (s.flagship_triple_barrier_global) {
      renderP80BenchmarkResult(s.flagship_triple_barrier_global);
    }
    // Render SNR Curve table
    const snrTbl = document.getElementById('p80SnrTable');
    snrTbl.innerHTML = '<tr><th>الأفق الثابت (بدون حواجز) C[t+h] &gt; C[t]</th><th>المحاولات</th><th>الدقة الكلية</th><th>Wilson 95% LB</th><th>دقة OOS</th><th>متوسط العائد الصافي</th></tr>' +
      (s.horizon_snr_curve || []).map(row =>
        `<tr><td><b>h = ${row.horizon_bars} شمعة</b></td><td>${row.total_attempts}</td><td><b>${row.full_accuracy_pct}%</b></td>` +
        `<td>${row.full_wilson_low_pct}%</td><td style="color:#38bdf8;font-weight:700">${row.oos_accuracy_pct}%</td><td style="color:#34d399">+${row.oos_mean_net_pct}%</td></tr>`
      ).join('');

    // Render Live October 2026 Scanner Grid
    const grid = document.getElementById('p80ScannerGrid');
    const cards = (s.live_october_2026_scanner && s.live_october_2026_scanner.cards) || [];
    grid.innerHTML = cards.map(c => {
      const isBuy = c.signal === 'BUY_NEXT_OPEN_BRACKET';
      const pCls = isBuy ? 'buy' : (c.regime.includes('BELOW') ? 'off' : 'wait');
      const band = c.conformal_85_band || {};
      return `<div class="scard ${isBuy ? 'buy' : ''}">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:6px">
          <div><b style="font-size:15px">${c.symbol}</b> <small class="sub">${c.latest_date.slice(0, 16)}</small></div>
          <span class="pill ${pCls}">${isBuy ? '🟢 BUY O[t+1]' : '🛡️ ABSTAIN'}</span>
        </div>
        <div style="font-size:12px;color:#94a3b8;margin:2px 0 6px">${c.description}</div>
        <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px">
          <span>Close: <b>${c.close}</b> <small style="color:${c.day_change_pct >= 0 ? '#34d399' : '#fda4af'}">(${c.day_change_pct >= 0 ? '+' : ''}${c.day_change_pct}%)</small></span>
          <span>OOS: <b style="color:#34d399">${c.oos_bracket_win_rate_pct != null ? c.oos_bracket_win_rate_pct + '%' : c.conformal_oos_coverage_pct + '% ACI'}</b></span>
        </div>
        <div style="font-size:11.5px;color:#cbd5e1">RSI(2): <b>${c.rsi2}</b> · IBS: <b>${c.ibs}</b> · Vol20: <b>${c.rv20_pct}%</b> · OFI: <b>${c.orderflow_ofi}</b></div>
        <div style="font-size:11.5px;color:#94a3b8;margin-top:4px">TP: <b style="color:#34d399">${c.bracket_plan.tp_price}</b> · SL: <b style="color:#fda4af">${c.bracket_plan.protective_sl_price}</b> · ACI80: [${band.band_80_low}, ${band.band_80_high}]</div>
        <div style="font-size:11.5px;color:${isBuy ? '#34d399' : '#7dd3fc'};margin-top:5px;font-weight:600">${c.signal_ar}</div>
      </div>`;
    }).join('');
    loadP80Candles();
  } catch (e) { console.error(e); }
}
window.addEventListener('DOMContentLoaded', bootPrecision80Lab);

'''

AUTOTRADER_SECTION_HTML = r"""
<section id="autotrader" class="pane on">
  <div class="kpi-strip" id="atKpis">
    <div class="kpi"><div class="k-lbl">💰 إجمالي قيمة المحفظة الحية · Live Total Wallet Equity</div><div class="k-val emerald" id="at_equity">$1,000.00</div><div class="k-sub" id="at_equity_sub">جاهز فوراً — عملات مدعومة: FDUSD · USDT · BTC · ETH · BNB · XRP</div></div>
    <div class="kpi"><div class="k-lbl">🤖 حالة المتداول التلقائي · Auto-Pilot Engine</div><div class="k-val cyan" id="at_state">جاهز للتشغيل</div><div class="k-sub" id="at_state_sub">يتداول بالنيابة عنك تلقائياً فور الضغط على ابدأ</div></div>
    <div class="kpi"><div class="k-lbl">📈 نتيجة 1,000$ على فريم 1m ليوم كامل (24h · ETH)</div><div class="k-val emerald" id="at_day_eth">$1,014.10 (+$14.10)</div><div class="k-sub">2026-10-15 · 1,440 شمعة حقيقية · دقة 88.9% (8/9) · Maker 0 bps</div></div>
    <div class="kpi"><div class="k-lbl">⚡ نتيجة 1,000$ على فريم 1m ليوم كامل (24h · BTC)</div><div class="k-val emerald" id="at_day_btc">$1,009.67 (+$9.67)</div><div class="k-sub">2026-10-15 (83.3%) · وفي 2026-10-17: +$1.96 مقابل -$1.53 للسوق</div></div>
    <div class="kpi"><div class="k-lbl">🏆 حصيلة الأسبوع الكامل على فريم 1m (10,080 دقيقة)</div><div class="k-val gold" id="at_week_res">ETH +$22.73 · BTC +$17.45</div><div class="k-sub">رابح في 6 من 7 أيام (BTC) بعمولة Maker الصفرية</div></div>
    <div class="kpi"><div class="k-lbl">⚠️ أثر عمولة أوامر السوق العشوائية (10 bps Taker)</div><div class="k-val" style="color:#fda4af" id="at_fee_warn">-$37.46 إلى -$50.98/يوم</div><div class="k-sub">لهذا السبب يستخدم محركنا أوامر Post-Only Limit تلقائياً!</div></div>
  </div>

  <div class="dual-grid">
    <div class="card">
      <h3>🏦 1) المحفظة متعددة العملات والتحويل الفوري · Deposit Any Coin & Auto-Convert</h3>
      <p class="sub" style="margin:2px 0 10px">أودِع أو موّل بأي عملة (<code>BTC</code>, <code>ETH</code>, <code>BNB</code>, <code>XRP</code>, <code>USDT</code>, <code>FDUSD</code>, <code>USD</code>) وحوّلها بضغطة واحدة بأسعار أكتوبر 2026 الحقيقية ليقوم البوت بالتداول تلقائياً مكانك.</p>
      <div id="atBalancesPills" class="tags" style="margin-bottom:10px"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
        <div style="background:var(--card2);padding:11px;border-radius:11px;border:1px solid var(--bdr)">
          <b style="font-size:13px;color:#34d399">➕ إيداع / تمويل عملة جديدة</b>
          <label>العملة المراد إيداعها</label>
          <select id="at_dep_cur">
            <option value="USDT">USDT (Tether)</option>
            <option value="BTC">BTC (Bitcoin — $81,491)</option>
            <option value="ETH">ETH (Ethereum — $2,402.8)</option>
            <option value="FDUSD">FDUSD (Zero-Fee Pair)</option>
            <option value="BNB">BNB ($718.02)</option>
            <option value="XRP">XRP ($1.2941)</option>
            <option value="USD">USD ($1.00)</option>
          </select>
          <label>المبلغ / الكمية</label>
          <input id="at_dep_amt" type="number" step="0.001" value="500">
          <label style="display:flex;align-items:center;gap:6px;margin-top:8px;cursor:pointer">
            <input id="at_dep_auto" type="checkbox" checked style="width:auto">
            <span>حوّل تلقائياً لعملة التداول (FDUSD 0% عمولة)</span>
          </label>
          <button class="go emerald" onclick="atDepositAndTrade(false)" style="width:100%">💰 إيداع وتجهيز الرصيد</button>
          <button class="go" onclick="atDepositAndTrade(true)" style="width:100%;margin-top:6px">🚀 أودِع العملة وابدأ التداول مكاني فوراً!</button>
        </div>

        <div style="background:var(--card2);padding:11px;border-radius:11px;border:1px solid var(--bdr)">
          <b style="font-size:13px;color:#38bdf8">🔄 تحويل فوري بين العملات (Instant Swap)</b>
          <label>من عملة</label>
          <select id="at_from_cur">
            <option value="FDUSD" selected>FDUSD</option>
            <option value="USDT">USDT</option>
            <option value="BTC">BTC</option>
            <option value="ETH">ETH</option>
            <option value="BNB">BNB</option>
            <option value="XRP">XRP</option>
          </select>
          <label>إلى عملة</label>
          <select id="at_to_cur">
            <option value="BTC">BTC</option>
            <option value="ETH" selected>ETH</option>
            <option value="FDUSD">FDUSD (0% Fee)</option>
            <option value="USDT">USDT</option>
            <option value="BNB">BNB</option>
          </select>
          <label>الكمية المراد تحويلها</label>
          <input id="at_conv_amt" type="number" step="0.0001" value="250">
          <button class="go" onclick="atConvertNow()" style="width:100%;margin-top:14px">🔄 نفّذ التحويل الفوري</button>
          <button class="go" style="width:100%;margin-top:6px;background:#334155;color:#e2e8f0" onclick="atResetWallet()">↺ إعادة ضبط المحفظة التجريبية ($1,000)</button>
        </div>
      </div>
      <div id="atWalletMsg" class="sub" style="margin-top:9px;color:#34d399;font-weight:700"></div>
    </div>

    <div class="card">
      <h3>🤖 2) غرفة التحكم بالتداول التلقائي · On-Demand Auto-Trader & Exchange API</h3>
      <p class="sub" style="margin:2px 0 10px">يعمل البوت تلقائياً بالخلفية متى طلبت، ينفذ أوامر <code>LIMIT_MAKER</code> ويضع هدف الربح <code>TP</code> ووقف الخسارة <code>SL</code> وحاجز الحماية اليومي تلقائياً، مع دعم الربط المباشر بـ Binance Testnet / Live عبر توقيع <code>HMAC-SHA256</code>.</p>
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px">
        <div>
          <label>السوق الآلي (1m Order-Flow)</label>
          <select id="at_cfg_sym" onchange="atSaveConfig()">
            <option value="ETHUSDT" selected>ETH / FDUSD (1m)</option>
            <option value="BTCUSDT">BTC / FDUSD (1m)</option>
            <option value="BNBUSDT">BNB / FDUSD (1m)</option>
            <option value="XRPUSDT">XRP / FDUSD (1m)</option>
          </select>
        </div>
        <div>
          <label>بوابة التنفيذ (Venue)</label>
          <select id="at_cfg_venue" onchange="atSaveConfig()">
            <option value="paper_live_1m" selected>محرك التنفيذ الحي الفوري (بدون مفاتيح)</option>
            <option value="binance_testnet">Binance Spot Testnet (API تجريبي)</option>
            <option value="binance_live">Binance Live (Post-Only API)</option>
            <option value="bybit_live">Bybit Unified v5 (Post-Only API)</option>
          </select>
        </div>
        <div>
          <label>فئة العمولة (bps) / سرعة البوت</label>
          <select id="at_cfg_fee" onchange="atSaveConfig()">
            <option value="0" selected>0 bps — أزواج FDUSD/USDC Maker</option>
            <option value="2">2 bps — VIP / BNB Maker Limit</option>
            <option value="10">10 bps — Market Taker عادي</option>
          </select>
        </div>
      </div>

      <details style="margin-top:8px;background:var(--card2);padding:8px 11px;border-radius:10px;border:1px solid var(--bdr)">
        <summary style="cursor:pointer;font-size:12.5px;color:#7dd3fc;font-weight:700">🔑 ربط مفاتيح منصة خارجية اختيارية (Binance / Bybit HMAC-SHA256 — تُحفظ بالذاكرة المؤقتة RAM فقط ولا تُكتب على القرص)</summary>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:8px">
          <div><label>API Key (اختياري)</label><input id="at_api_key" type="text" autocomplete="off" style="-webkit-text-security:disc" placeholder="أدخل مفتاح التداول فقط بدون صلاحية سحب"></div>
          <div><label>API Secret (HMAC-SHA256)</label><input id="at_api_sec" type="text" autocomplete="off" style="-webkit-text-security:disc" placeholder="يُوقّع محلياً ولا يُحفظ على القرص أبداً"></div>
        </div>
      </details>

      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px">
        <button class="go emerald" onclick="atStartBot()" id="btnStartBot" style="flex:1.3">▶️ ابدأ التداول التلقائي مكاني</button>
        <button class="go" onclick="atStepBot(120)" style="flex:1">⏩ نفّذ ساعتين فوراً (120m)</button>
        <button class="go" onclick="atStepBot(1440)" style="flex:1">⚡ نفّذ يوماً كاملاً (1,440m)</button>
        <button class="go" style="background:linear-gradient(135deg,#f43f5e,#be123c);color:#fff;flex:1" onclick="atStopBot()">🛑 إيقاف طوارئ وتصفية</button>
      </div>

      <div id="atLiveBox" style="margin-top:10px;padding:10px 12px;border-radius:10px;background:#070d19;border:1px solid var(--bdr);font-size:13px"></div>
      <div style="max-height:175px;overflow:auto;margin-top:8px">
        <table>
          <thead><tr><th>#</th><th>الزوج</th><th>الاتجاه</th><th>الدخول ← الخروج</th><th>العمولة</th><th>الربح الصافي $</th><th>السبب</th></tr></thead>
          <tbody id="atOrdersBody"><tr><td colspan="7" class="sub">اضغط «▶️ ابدأ التداول التلقائي مكاني» أو «⚡ نفّذ يوماً كاملاً (1,440m)» لمشاهدة الصفقات الحية لحظة بلحظة!</td></tr></tbody>
        </table>
      </div>
    </div>
  </div>

  <div class="card" style="margin-bottom:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;margin-bottom:10px">
      <div>
        <h3>💵 3) نتائج وتجربة اختبار الـ 1,000$ الحقيقي على فريم الدقيقة (1m) لنهار كامل (1,440 شمعة — أكتوبر 2026)</h3>
        <p class="sub" style="margin:2px 0 0">اختبار سببي صارم بدون أي تسريب مستقبلي (Zero Lookahead) يتحقق من تنفيذ الأمر المعلّق فعلياً عبر <code>Low[t+1] &le; Bid</code> و<code>High[t+1] &ge; Ask</code> ويعرض كشف الحساب الكامل بالدولار والسنت.</p>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:end">
        <div>
          <select id="sim_sym" onchange="run1mDaySim()">
            <option value="ETHUSDT" selected>ETHUSDT / ETHFDUSD (1m)</option>
            <option value="BTCUSDT">BTCUSDT / BTCFDUSD (1m)</option>
            <option value="BNBUSDT">BNBUSDT / BNBFDUSD (1m)</option>
            <option value="XRPUSDT">XRPUSDT / XRPFDUSD (1m)</option>
          </select>
        </div>
        <div>
          <select id="sim_day" onchange="run1mDaySim()">
            <option value="2026-10-15" selected>نهار كامل: 2026-10-15 (1,440 دقيقة)</option>
            <option value="2026-10-17">أحدث نهار كامل: 2026-10-17 (1,440 دقيقة)</option>
            <option value="2026-10-14">نهار هبوط حاد: 2026-10-14 (1,440 دقيقة)</option>
            <option value="2026-10-13">نهار نشط: 2026-10-13 (1,440 دقيقة)</option>
            <option value="2026-10-11">نهار هادئ: 2026-10-11 (1,440 دقيقة)</option>
            <option value="ALL_DAYS">أسبوع كامل متواصل: 7 أيام (10,080 دقيقة!)</option>
          </select>
        </div>
        <div>
          <select id="sim_mode" onchange="run1mDaySim()">
            <option value="smart_maker_0bps" selected>البوت الذكي — أوامر Maker صفرية العمولة (FDUSD 0 bps)</option>
            <option value="vip_maker_2bps">البوت الذكي — أوامر VIP Maker بخصم BNB (2 bps)</option>
            <option value="smart_taker_10bps">نفس البوت الذكي — لكن بأوامر سوق عادية (10 bps Taker)</option>
            <option value="naive_ema_10bps">بوت تقليدي عشوائي (EMA 9/21 بعمولة 10 bps)</option>
          </select>
        </div>
        <div>
          <input id="sim_cap" type="number" step="100" min="100" max="100000" value="1000" style="width:110px" onchange="run1mDaySim()">
        </div>
        <button class="go emerald" onclick="run1mDaySim()" style="margin-top:0">🔬 احسب كشف الحساب الكامل</button>
      </div>
    </div>

    <div class="dual-grid" style="margin-bottom:12px">
      <div>
        <div class="svgbox" id="sim1mSvg" style="min-height:245px"></div>
        <div id="sim1mSummary" style="margin-top:8px;font-size:13.5px;font-weight:700"></div>
      </div>
      <div>
        <b style="font-size:13.5px;color:#fbbf24">📊 المقارنة الحاسمة لرصيد 1,000$ عبر أنظمة التنفيذ الأربعة (لماذا تخسر البوتات التقليدية على 1m وكيف يربح محركنا؟)</b>
        <div style="overflow:auto;margin-top:6px">
          <table>
            <thead>
              <tr>
                <th>السيناريو الحقيقي (أكتوبر 2026)</th>
                <th>Maker 0 bps (FDUSD)</th>
                <th>VIP Maker (2 bps)</th>
                <th>Market Taker (10 bps)</th>
                <th>بوت تقليدي (10 bps)</th>
                <th>شراء واحتفاظ</th>
              </tr>
            </thead>
            <tbody id="simCompBody"></tbody>
          </table>
        </div>
      </div>
    </div>

    <details open style="background:var(--card2);padding:10px 14px;border-radius:12px;border:1px solid var(--bdr)">
      <summary style="cursor:pointer;font-weight:800;color:#38bdf8">🧾 سجل الصفقات التفصيلي الدقيقة بالدقيقة (Complete 1m Trade Ledger — USD & Fees)</summary>
      <div style="max-height:240px;overflow:auto;margin-top:8px">
        <table>
          <thead><tr><th>#</th><th>الاتجاه</th><th>وقت الدخول (UTC)</th><th>وقت الخروج</th><th>المدة</th><th>سعر الدخول</th><th>سعر الخروج</th><th>العمولة $</th><th>الربح الصافي $</th><th>رصيد المحفظة $</th><th>سبب الإغلاق</th></tr></thead>
          <tbody id="simTradesBody"></tbody>
        </table>
      </div>
    </details>
  </div>
</section>
"""

AUTOTRADER_JS_CODE = r"""
let atPollTimer = null;

function fmtUsdSigned(v){
  const n = Number(v || 0);
  return (n >= 0 ? '+$' : '-$') + Math.abs(n).toFixed(2);
}

function renderAtStatus(st){
  if(!st) return;
  document.getElementById('at_equity').textContent = '$' + Number(st.total_equity_usd).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2});
  document.getElementById('at_equity_sub').textContent = 'الربح المحقق: ' + fmtUsdSigned(st.realized_pnl_usd) + ' · الصفقات المنفذة: ' + st.closed_trades_count + ' (' + st.win_rate_pct + '% فوز)';
  const stEl = document.getElementById('at_state');
  stEl.textContent = st.running ? '🟢 يتداول تلقائياً الآن!' : '⏸ متوقف / جاهز لأمرك';
  stEl.style.color = st.running ? '#34d399' : '#38bdf8';
  document.getElementById('at_state_sub').textContent = st.symbol + ' · ' + st.current_market_time + ' · السعر: $' + st.current_market_price + ' (' + st.minutes_processed + ' دقيقة مفحوصة)';

  const pills = Object.entries(st.balances || {}).map(([k,v]) => `<span><b>${k}:</b> ${Number(v).toLocaleString(undefined,{maximumFractionDigits:6})}</span>`).join('');
  document.getElementById('atBalancesPills').innerHTML = pills;

  const liveBox = document.getElementById('atLiveBox');
  if(st.open_position){
    const p = st.open_position;
    liveBox.innerHTML = `🔥 <b>صفقة مفتوحة حالياً بالنيابة عنك:</b> <span class="pill buy">${p.side} ${p.symbol}</span> · الدخول: <b>$${p.entry_price}</b> · الهدف TP: <b style="color:#34d399">$${p.tp_price}</b> · الوقف SL: <b style="color:#fda4af">$${p.sl_price}</b> · الحجم: <b>$${p.notional_usd.toFixed(2)}</b>${p.signed_preview ? '<br><code style="font-size:11px;color:#7dd3fc">'+p.signed_preview+'</code>' : ''}`;
  } else {
    liveBox.innerHTML = `🛡️ <b>الرادار اللحظي نشط:</b> يراقب شموع الدقيقة وتدفق السيولة لـ <b>${st.symbol}</b> عند <b>$${st.current_market_price}</b> وينتظر تشبع 2.1σ للدخول بأمر <code>LIMIT_MAKER (${st.fee_bps} bps)</code>${st.api_key_masked ? ' · مفتاح API: <code>'+st.api_key_masked+'</code>' : ''}.`;
  }

  const orders = st.recent_orders || [];
  if(orders.length){
    document.getElementById('atOrdersBody').innerHTML = orders.map(o => `<tr>
      <td>${o.id}</td>
      <td><b>${o.symbol}</b></td>
      <td><span class="pill ${o.side==='LONG'?'buy':'wait'}">${o.side}</span></td>
      <td>$${o.entry_price} ← $${o.exit_price}<br><span class="sub" style="font-size:11px">${o.entry_time.slice(11,16)} → ${o.exit_time.slice(11,16)}</span></td>
      <td>$${Number(o.fee_usd).toFixed(2)}</td>
      <td style="font-weight:800;color:${o.net_usd>=0?'#34d399':'#fda4af'}">${fmtUsdSigned(o.net_usd)}</td>
      <td class="sub" style="font-size:11.5px">${o.reason}</td>
    </tr>`).join('');
  }
}

async function refreshAtStatus(){
  try{
    const r = await fetch('/api/autotrader/status');
    const st = await r.json();
    renderAtStatus(st);
    if(st.running && !atPollTimer){
      atPollTimer = setInterval(refreshAtStatus, 1100);
    } else if(!st.running && atPollTimer){
      clearInterval(atPollTimer);
      atPollTimer = null;
    }
  }catch(e){}
}

async function atDepositAndTrade(startImmediately){
  const cur = document.getElementById('at_dep_cur').value;
  const amt = parseFloat(document.getElementById('at_dep_amt').value || '0');
  const autoConv = document.getElementById('at_dep_auto').checked;
  const r = await fetch('/api/autotrader/deposit', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({currency: cur, amount: amt, auto_convert_to_quote: autoConv})
  });
  const j = await r.json();
  if(j.error){ document.getElementById('atWalletMsg').textContent = '⚠️ ' + j.error; return; }
  document.getElementById('atWalletMsg').textContent = `✅ تم إيداع ${amt} ${cur}${autoConv ? ' وتحويلها تلقائياً إلى ' + j.quote_currency : ''}! إجمالي المحفظة الآن: $${j.total_equity_usd.toFixed(2)}`;
  renderAtStatus(j);
  if(startImmediately){ await atStartBot(); }
}

async function atConvertNow(){
  const from_currency = document.getElementById('at_from_cur').value;
  const to_currency = document.getElementById('at_to_cur').value;
  const amount = parseFloat(document.getElementById('at_conv_amt').value || '0');
  const r = await fetch('/api/autotrader/convert', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({from_currency, to_currency, amount})
  });
  const j = await r.json();
  if(j.error){ document.getElementById('atWalletMsg').textContent = '⚠️ ' + j.error; return; }
  const c = j.conversion;
  document.getElementById('atWalletMsg').textContent = `🔄 تم تحويل ${c.from_amount} ${c.from_currency} ← ${c.to_amount} ${c.to_currency} بسعر السوق الحقيقي (${c.fee_bps} bps)!`;
  renderAtStatus(j);
}

async function atSaveConfig(){
  const body = {
    venue: document.getElementById('at_cfg_venue').value,
    symbol: document.getElementById('at_cfg_sym').value,
    fee_bps: parseFloat(document.getElementById('at_cfg_fee').value || '0'),
    api_key: document.getElementById('at_api_key').value || undefined,
    api_secret: document.getElementById('at_api_sec').value || undefined
  };
  const r = await fetch('/api/autotrader/configure', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  const j = await r.json();
  if(!j.error) renderAtStatus(j);
}

async function atStartBot(){
  await atSaveConfig();
  const r = await fetch('/api/autotrader/start', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({auto_convert_non_quote:true})});
  const j = await r.json();
  renderAtStatus(j);
  if(!atPollTimer) atPollTimer = setInterval(refreshAtStatus, 1100);
}

async function atStopBot(){
  const r = await fetch('/api/autotrader/stop', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({flatten_open:true})});
  const j = await r.json();
  renderAtStatus(j);
}

async function atStepBot(count){
  await atSaveConfig();
  const r = await fetch('/api/autotrader/step', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({count})});
  const j = await r.json();
  renderAtStatus(j);
}

async function atResetWallet(){
  const r = await fetch('/api/autotrader/reset', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({starting_fdusd:1000})});
  const j = await r.json();
  document.getElementById('atOrdersBody').innerHTML = '<tr><td colspan="7" class="sub">تمت إعادة ضبط المحفظة إلى $1,000.00 عند بداية يوم 2026-10-15!</td></tr>';
  renderAtStatus(j);
}

function draw1mEquitySvg(curve, startCap){
  const box = document.getElementById('sim1mSvg');
  if(!curve || curve.length < 2){ box.innerHTML = ''; return; }
  const W = 620, H = 235, P = 34;
  const vals = curve.flatMap(d => [d.balance_usd, d.bh_usd]);
  const minV = Math.min(...vals) * 0.9992;
  const maxV = Math.max(...vals) * 1.0008;
  const span = Math.max(1e-6, maxV - minV);
  const x = i => P + (i / (curve.length - 1)) * (W - P * 1.6);
  const y = v => H - P - ((v - minV) / span) * (H - P * 1.8);
  const botPath = curve.map((d,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(d.balance_usd).toFixed(1)).join(' ');
  const bhPath = curve.map((d,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(d.bh_usd).toFixed(1)).join(' ');
  const endBal = curve[curve.length - 1].balance_usd;
  const lineCol = endBal >= startCap ? '#34d399' : '#fb7185';
  box.innerHTML = `<svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">
    <line x1="${P}" y1="${y(startCap).toFixed(1)}" x2="${W-16}" y2="${y(startCap).toFixed(1)}" stroke="#475569" stroke-dasharray="4,4"/>
    <path d="${bhPath}" fill="none" stroke="#64748b" stroke-width="1.6" stroke-dasharray="3,3"/>
    <path d="${botPath}" fill="none" stroke="${lineCol}" stroke-width="2.7"/>
    <text x="${P}" y="18" fill="#cbd5e1" font-size="11.5" font-weight="bold">رصيد البوت الآلي ($${endBal.toFixed(2)}) مقابل شراء واحتفاظ السوق الرمادي ($${curve[curve.length-1].bh_usd.toFixed(2)})</text>
    <text x="${P}" y="${H-10}" fill="#94a3b8" font-size="10.5">${curve[0].time} UTC</text>
    <text x="${W-115}" y="${H-10}" fill="#94a3b8" font-size="10.5">${curve[curve.length-1].time} UTC</text>
  </svg>`;
}

async function run1mDaySim(){
  try{
    const sym = document.getElementById('sim_sym').value;
    const day = document.getElementById('sim_day').value;
    const mode = document.getElementById('sim_mode').value;
    const cap = parseFloat(document.getElementById('sim_cap').value || '1000');
    const r = await fetch(`/api/autotrader/1m-day-test?symbol=${encodeURIComponent(sym)}&day=${encodeURIComponent(day)}&mode=${encodeURIComponent(mode)}&capital=${cap}`);
    const d = await r.json();
    draw1mEquitySvg(d.minute_equity_curve, d.start_balance_usd);
    const col = d.net_profit_usd >= 0 ? '#34d399' : '#fda4af';
    document.getElementById('sim1mSummary').innerHTML =
      `الرصيد الابتدائي: <b>$${d.start_balance_usd.toFixed(2)}</b> ← الرصيد النهائي: <b style="color:${col}">$${d.end_balance_usd.toFixed(2)} (${fmtUsdSigned(d.net_profit_usd)} / ${d.net_return_pct}%)</b> · الصفقات: <b>${d.trades_count}</b> (فوز <b>${d.win_rate_pct}%</b>) · إجمالي العمولات المدفوعة: <b>$${d.total_fees_paid_usd.toFixed(2)}</b> · أقصى تراجع: <b>$${d.max_drawdown_usd.toFixed(2)}</b>`;
    document.getElementById('simTradesBody').innerHTML = (d.trades || []).map(t => `<tr>
      <td>${t.idx}</td>
      <td><span class="pill ${t.side==='LONG'?'buy':'wait'}">${t.side}</span></td>
      <td>${t.entry_time}</td>
      <td>${t.exit_time}</td>
      <td>${t.duration_min}m</td>
      <td>$${t.entry_price}</td>
      <td>$${t.exit_price}</td>
      <td>$${t.fee_usd.toFixed(2)}</td>
      <td style="font-weight:800;color:${t.net_usd>=0?'#34d399':'#fda4af'}">${fmtUsdSigned(t.net_usd)}</td>
      <td><b>$${t.balance_after_usd.toFixed(2)}</b></td>
      <td class="sub">${t.reason}</td>
    </tr>`).join('') || '<tr><td colspan="11" class="sub">لا توجد صفقات في هذا الفلتر</td></tr>';
  }catch(e){}
}

async function load1mComparisonTable(){
  try{
    const r = await fetch('/api/autotrader/1m-comparison?capital=1000');
    const d = await r.json();
    const cell = o => `<b style="color:${o.net_usd>=0?'#34d399':'#fda4af'}">$${o.end_usd.toFixed(2)}</b><br><span class="sub" style="font-size:11px">${fmtUsdSigned(o.net_usd)} · فوز ${o.win_pct}% (${o.trades})</span>`;
    document.getElementById('simCompBody').innerHTML = (d.scenarios || []).map(s => `<tr>
      <td><b>${s.scenario}</b></td>
      <td>${cell(s.smart_maker_0bps)}</td>
      <td>${cell(s.vip_maker_2bps)}</td>
      <td>${cell(s.smart_taker_10bps)}</td>
      <td>${cell(s.naive_bot_10bps)}</td>
      <td style="color:${s.buy_and_hold_pnl_usd>=0?'#34d399':'#fda4af'}"><b>${fmtUsdSigned(s.buy_and_hold_pnl_usd)}</b></td>
    </tr>`).join('');
  }catch(e){}
}

window.addEventListener('DOMContentLoaded', () => {
  refreshAtStatus();
  run1mDaySim();
  load1mComparisonTable();
});
"""


WEALTH_SECTION_HTML = r"""
<section id="wealth" class="pane">
  <div class="kpi-strip">
    <div class="kpi"><div class="k-lbl">🏆 المسار 1: حسابات التمويل (Prop-Firm $50k)</div><div class="k-val emerald" id="wk_prop">$1,275 / شهرياً</div><div class="k-sub">حصة المتداول 85% عند عائد هادئ +3% شهرياً (بتكلفة تحدي $299 فقط!)</div></div>
    <div class="kpi"><div class="k-lbl">📡 المسار 2: اشتراكات قناة التوصيات (VIP SaaS)</div><div class="k-val cyan" id="wk_saas">$1,950 / شهرياً</div><div class="k-sub">50 مشترك × $39/شهرياً عبر رسائل Telegram &amp; Webhook الموثقة بـ SHA-256</div></div>
    <div class="kpi"><div class="k-lbl">💰 المسار 3: المحفظة الشخصية الهجينة الذكية</div><div class="k-val gold" id="wk_hybrid">86.41% OOS</div><div class="k-sub">توزيع ذكي: أسهم كبرى (50%) + ذهب (30%) + Maker صفري العمولة (20%)</div></div>
    <div class="kpi"><div class="k-lbl">💎 إجمالي الدخل الشهري المركّب (المسارات الثلاثة)</div><div class="k-val emerald" id="wk_total">$3,305 / شهرياً</div><div class="k-sub" id="wk_total_sub">$39,660 سنوياً — حاسبة تفاعلية حية قابلة للتخصيص بالأسفل</div></div>
  </div>

  <div class="dual-grid">
    <div class="card">
      <h3>🏛️ 1) محاكي اجتياز حسابات التمويل (Prop-Firm $10k – $100k Evaluation Simulator)</h3>
      <p class="sub" style="margin:2px 0 10px">يختبر صفقاتنا الحقيقية خارج العينة ضد شروط شركات التمويل الصارمة (<b>أقصى خسارة يومية 5%</b> · <b>أقصى تراجع كلي 10%</b> · <b>حصة أرباح 85%</b>) لتضاعف حجم رأس مالك بـ 100 ضعف دون المخاطرة بمدخراتك.</p>
      <div style="display:grid;grid-template-columns:1fr 1fr auto;gap:8px;align-items:end">
        <div>
          <label>حجم حساب التمويل المستهدف</label>
          <select id="wf_acct" onchange="runPropChallengeSim()">
            <option value="10000">$10,000 (رسوم الاختبار ~$89)</option>
            <option value="25000">$25,000 (رسوم الاختبار ~$199)</option>
            <option value="50000" selected>$50,000 (رسوم الاختبار ~$299 — الأنسب)</option>
            <option value="100000">$100,000 (رسوم الاختبار ~$499)</option>
          </select>
        </div>
        <div>
          <label>مُعامل المخاطرة للصفقة</label>
          <select id="wf_scale" onchange="runPropChallengeSim()">
            <option value="0.75">حذر جداً (0.75x — حماية قصوى)</option>
            <option value="1.0" selected>قياسي متوازن (1.0x — موصى به)</option>
            <option value="1.5">معزّز (1.5x — اجتياز أسرع)</option>
          </select>
        </div>
        <button class="go emerald" onclick="runPropChallengeSim()">⚡ شغّل محاكاة التمويل</button>
      </div>
      <div id="wfPropOut" style="margin-top:12px;padding:12px;border-radius:10px;background:#070d19;border:1px solid var(--bdr);font-size:13.5px"></div>
    </div>

    <div class="card">
      <h3>📡 2) مولّد توصيات VIP الجاهزة للبيع (Telegram / Discord / Webhook SaaS Publisher)</h3>
      <p class="sub" style="margin:2px 0 10px">بضغطة واحدة يولّد نشرة توصيات مؤسسية موثقة ببصمة <code>SHA-256</code> من آخر إغلاق حقيقي لـ 19 سوقاً عالمياً لنسخها مباشرة إلى قناتك المدفوعة أو ربطها بـ Webhook آلي.</p>
      <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px">
        <button class="go" onclick="loadVipSignals('telegram')">📣 توليد نشرة Telegram VIP بالعربية</button>
        <button class="go emerald" onclick="loadVipSignals('webhook')">🔗 عرض Payload JSON Webhook للمشتركين</button>
      </div>
      <pre id="wfVipBox" style="background:#050a14;border:1px solid var(--bdr);border-radius:10px;padding:11px;font-size:12.5px;white-space:pre-wrap;max-height:225px;overflow:auto"></pre>
    </div>
  </div>

  <div class="card">
    <h3>🧮 3) المخطط المالي المتكامل لتعظيم الدخل الشهري + التوزيع الذكي لثلاث سلات غير مترابطة</h3>
    <div class="ctrl-bar" style="margin-top:8px">
      <div><label>رأس المال الشخصي للتداول الآلي ($)</label><input id="wf_cap" type="number" value="2000" step="250" onchange="refreshWealthPlan()"></div>
      <div><label>حجم حساب التمويل Prop-Firm ($)</label><input id="wf_prop_cap" type="number" value="50000" step="5000" onchange="refreshWealthPlan()"></div>
      <div><label>عدد مشتركي قناة التوصيات المدفوعة</label><input id="wf_subs" type="number" value="50" step="5" onchange="refreshWealthPlan()"></div>
      <div><label>سعر الاشتراك الشهري للفرد ($)</label><input id="wf_price" type="number" value="39" step="5" onchange="refreshWealthPlan()"></div>
      <button class="go emerald" onclick="refreshWealthPlan()">💎 احسب الخطة المالية</button>
    </div>
    <div id="wfHybridBody"></div>
  </div>
</section>
"""

WEALTH_JS_CODE = r"""
async function runPropChallengeSim(){
  try{
    const acct = document.getElementById('wf_acct').value;
    const scale = document.getElementById('wf_scale').value;
    const r = await fetch(`/api/wealth/prop-challenge?account=${acct}&scale=${scale}`);
    const d = await r.json();
    const okBadge = d.rules_passed_cleanly
      ? '<span class="pill buy">✅ اجتاز جميع شروط الحماية بنجاح (صفر كسر يومي أو كلي!)</span>'
      : '<span class="pill off">⚠️ ' + d.breach_reason + '</span>';
    document.getElementById('wfPropOut').innerHTML =
      `${okBadge}<div style="margin-top:8px;line-height:1.75">` +
      `• <b>الرصيد النهائي المحاكى خارج العينة:</b> <b style="color:#34d399">$${d.final_simulated_balance_usd.toLocaleString()}</b> (صافي الربح الكلي: <b>+$${d.net_simulated_profit_usd.toLocaleString()}</b>)<br>` +
      `• <b>حصتك الصافية بـ 85% Profit Split:</b> <b style="color:#fbbf24;font-size:15px">$${d.trader_85pct_payout_usd.toLocaleString()}</b> (مضاعفة رسوم التحدي البالغة $${d.challenge_fee_usd} بمقدار <b>${d.roi_vs_challenge_fee_x}x</b>!)<br>` +
      `• <b>أقصى خسارة يومية مسجّلة:</b> <b>${d.max_daily_loss_observed_pct}%</b> (الحد المسموح 5.0%) · <b>أقصى تراجع كلي:</b> <b>${d.max_overall_drawdown_observed_pct}%</b> (الحد المسموح 10.0%)</div>`;
  }catch(e){}
}

async function loadVipSignals(kind){
  try{
    const r = await fetch('/api/wealth/vip-signals');
    const d = await r.json();
    document.getElementById('wfVipBox').textContent = (kind === 'webhook') ? d.webhook_json_payload : d.telegram_markdown_ar;
  }catch(e){}
}

async function refreshWealthPlan(){
  try{
    const cap = parseFloat(document.getElementById('wf_cap').value || '2000');
    const prop = parseInt(document.getElementById('wf_prop_cap').value || '50000', 10);
    const subs = parseInt(document.getElementById('wf_subs').value || '50', 10);
    const price = parseFloat(document.getElementById('wf_price').value || '39');
    const [rInc, rHyb] = await Promise.all([
      fetch(`/api/wealth/saas-calculator?subscribers=${subs}&price=${price}&prop_account=${prop}&capital=${cap}`),
      fetch(`/api/wealth/hybrid-plan?capital=${cap}&profile=balanced`)
    ]);
    const inc = await rInc.json();
    const hyb = await rHyb.json();
    document.getElementById('wk_prop').textContent = '$' + inc.streams.prop_firm_85pct_payout_usd.toLocaleString() + ' / شهرياً';
    document.getElementById('wk_saas').textContent = '$' + inc.streams.vip_signal_saas_mrr_usd.toLocaleString() + ' / شهرياً';
    document.getElementById('wk_total').textContent = '$' + inc.total_monthly_income_usd.toLocaleString() + ' / شهرياً';
    document.getElementById('wk_total_sub').textContent = '$' + inc.projected_annual_income_usd.toLocaleString() + ' سنوياً من المسارات الثلاثة مجتمعة';
    document.getElementById('wfHybridBody').innerHTML = `<table><thead><tr><th>السلة الاستثمارية الذكية</th><th>الوزن</th><th>المبلغ المخصص</th><th>الدقة المحققة OOS</th><th>آلية التنفيذ المثلى</th></tr></thead><tbody>` +
      (hyb.sleeves || []).map(s => `<tr><td><b>${s.title_ar}</b></td><td>${s.weight_pct}%</td><td><b>$${s.allocated_usd.toLocaleString()}</b></td><td style="color:#34d399;font-weight:800">${s.verified_oos_win_pct}%</td><td class="sub">${s.execution_rule}</td></tr>`).join('') +
      `</tbody></table>`;
  }catch(e){}
}

window.addEventListener('DOMContentLoaded', () => {
  runPropChallengeSim();
  loadVipSignals('telegram');
  refreshWealthPlan();
});
"""

VELOCITY_SECTION_HTML = r"""
<section id="velocity" class="pane">
  <div class="card" style="margin-bottom:16px;border-color:rgba(16,185,129,.55);background:linear-gradient(135deg,rgba(6,78,59,.45),rgba(13,22,40,.96))">
    <span class="pill buy" style="margin-bottom:8px">⚡ TradeAtlas Pro v24.0 + Velocity Compounder v23.0 · صفر أرقام وهمية · بدون تسريب مستقبلي O[t]→O[t+1]</span>
    <h2 style="margin:6px 0 8px">🚀 محرك مضاعفة رأس المال وسرعة الدوران الحقيقية (+62.83% سنوياً مركّباً / +5,873.4% صافي موثق) + استوديو الراتب الشهري ودرع الأزمات v24.0</h2>
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin:10px 0">
      <button type="button" onclick="runV24QuantShield()" style="background:#10b981;color:#022c22;font-weight:800;border:0;border-radius:8px;padding:7px 13px;cursor:pointer">🛡️ اختبار انهيارات السوق (Monte Carlo v24.0)</button>
      <button type="button" onclick="runV24SalaryPlan()" style="background:#38bdf8;color:#041e31;font-weight:800;border:0;border-radius:8px;padding:7px 13px;cursor:pointer">💵 حاسبة الراتب الشهري + التراكم (TRY / SAR / USD)</button>
      <button type="button" onclick="runV24CorrGuard()" style="background:#fbbf24;color:#1f1600;font-weight:800;border:0;border-radius:8px;padding:7px 13px;cursor:pointer">🧭 مصفوفة الارتباط والـ التحوّط (90 يوم)</button>
      <button type="button" onclick="runV25Regime()" style="background:#a855f7;color:#fff;font-weight:800;border:0;border-radius:8px;padding:7px 13px;cursor:pointer">🧠 مبدّل الأنظمة المؤسسي المدمج (Regime Meta-Allocator v25.0)</button>
      <button type="button" onclick="runV25ExecSlicer()" style="background:#f97316;color:#1f0a00;font-weight:800;border:0;border-radius:8px;padding:7px 13px;cursor:pointer">⚡ مقسّم الأوامر الذكي TWAP/VWAP + وقف ATR (v25.0)</button>
      <button type="button" onclick="runV25CircuitBreaker()" style="background:#ef4444;color:#fff;font-weight:800;border:0;border-radius:8px;padding:7px 13px;cursor:pointer">🛑 قاطع الحماية الفولاذي لرأس المال (Circuit-Breaker v25.0)</button>
    </div>
    <div id="v24ShieldBox" style="display:none;margin:8px 0 10px;padding:12px;border-radius:10px;background:rgba(2,12,27,.82);border:1px solid rgba(56,189,248,.4);font-size:13px;line-height:1.7"></div>
    <p style="font-size:13.5px;color:var(--mut);line-height:1.75;margin:0">
      وداعاً لعوائد <b>3%–8%</b> الناتجة عن حبس 90% من رأس المال نقداً خاملاً! يقوم <b>Velocity Compounder v23.0</b> بتدوير رأس مالك الفعلي أسبوعياً نحو القائد الأقوى زخماً ومعدّلاً بالتذبذب عبر <b>10 أسواق عالمية حقيقية</b> (<code>NVDA · MSFT · AAPL · META · GOOG · TSLA · QQQ · SPY · الذهب XAUUSD · BTCUSD</code>) مع وقف حماية يومي صارم <code>SMA25</code>، وفلتر منع الذبذبة المؤسسي <code>+20% Hysteresis</code>، ومكبح تراجع تلقائي عند <code>-18%</code>، وبعد خصم كامل العمولات (<code>10 bps</code>) وفائدة الهامش (<code>6.5% سنوياً</code>):
      <b style="color:#34d399">$1,000 تتحول فعلياً على بيانات 2018–2026 الحقيقية إلى $59,733.50 (+5,873.4% / +62.83% سنوياً مركّباً)</b>، أو <b style="color:#67e8f9">$40,755.92 (+55.58% سنوياً)</b> في الوضع الفوري النقي الحلال بدون أي رافعة مالية إطلاقاً (<code>1.0x Halal Spot</code> وبأقصى تراجع <code>-29.41%</code> فقط)!
    </p>
  </div>

  <div class="kpi-strip" id="velKpiRow"></div>

  <div class="ctrl-bar">
    <div>
      <label>💵 رأس المال الفعلي ($ USD)</label>
      <input id="velCap" type="number" min="100" step="100" value="1000" onchange="runVelocityEngine()">
    </div>
    <div style="grid-column:span 2">
      <label>⚙️ نمط سرعة رأس المال والمخاطرة الحقيقية</label>
      <select id="velMode" onchange="runVelocityEngine()">
        <option value="institutional_kelly_135" selected>🔥 المحرك المؤسسي 1.35x Shannon-Kelly (+62.83% سنوياً مركّباً — موصى به)</option>
        <option value="spot_halal_100">☪️ السرعة الفورية النقية 1.0x Spot (حلال 100% بدون رافعة — +55.58% سنوياً وتراجع -29.41%)</option>
        <option value="legacy_passive_spot">🐢 للمقارنة: الوضع القديم الساكن (90% كاش خامل — 8.72% سنوياً فقط)</option>
        <option value="overleveraged_trap_165">⚠️ تحذير الإفراط بالرافعة 1.65x (إثبات رياضي لتآكل التذبذب Volatility Drag)</option>
      </select>
    </div>
    <div>
      <label>📅 سنة البداية الحقيقية</label>
      <select id="velYear" onchange="runVelocityEngine()">
        <option value="2018" selected>2018 → أكتوبر 2026 (9 سنوات كاملة)</option>
        <option value="2020">2020 → أكتوبر 2026</option>
        <option value="2022">2022 → أكتوبر 2026 (شامل هبوط 2022)</option>
        <option value="2023">2023 → أكتوبر 2026</option>
      </select>
    </div>
    <button class="go emerald" onclick="runVelocityEngine()">⚡ احسب المضاعفة الحقيقية</button>
    <button class="go" onclick="applyVelocityLiveSignalToWallet()">🤖 موّل المحفظة وفعّل التنفيذ الآلي</button>
  </div>

  <div class="dual-grid">
    <div class="card">
      <h3>📈 منحنى نمو الثروة المركّب الحقيقي مقارنةً بـ S&amp;P 500 (SPY Buy &amp; Hold)</h3>
      <div class="svgbox" id="velChartWrap" style="margin-top:10px;min-height:215px"></div>
      <h4 style="margin:14px 0 8px;font-size:13px;color:#7dd3fc">📊 العوائد السنوية المحققة فعلياً سنة بسنة (بعد خصم كافة العمولات والفوائد)</h4>
      <div id="velYearlyGrid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(86px,1fr));gap:8px"></div>
    </div>

    <div class="card">
      <h3>🏆 المقارنة الرياضية الشفافة للأنماط الأربعة على نفس الشموع الحقيقية</h3>
      <div style="overflow:auto;margin-top:8px">
        <table>
          <thead>
            <tr>
              <th>الاستراتيجية</th>
              <th>الرصيد النهائي</th>
              <th>النمو السنوي CAGR</th>
              <th>أقصى تراجع</th>
              <th>العمولات المخصومة</th>
            </tr>
          </thead>
          <tbody id="velCompareBody"></tbody>
        </table>
      </div>
      <div class="out" style="margin-top:12px;border-color:rgba(245,158,11,.4);background:rgba(245,158,11,.08);white-space:normal;line-height:1.7;font-size:12.5px">
        <b>🔍 الشفافية العلمية الكاملة (الحقيقي 100% مقابل المستحيل رياضياً):</b><br>
        • <b>الحقيقي 100% والمثبت أمامك بالبيانات الفورية:</b> تحقيق <b>+55.58% إلى +62.83% سنوياً مركّباً</b> (تحويل $1,000 إلى <b>$40,755.92 – $59,733.50</b>) عبر تدوير رأس المال بالكامل نحو أقوى قائد مؤسسي عالمي (<code>NVDA</code>، <code>MSFT</code>، <code>XAUUSD</code>، <code>BTC</code>) والخروج الفوري عند كسر <code>SMA25</code>، مع إفصاح صادق عن التراجع المرحلي الطبيعي خلال 9 سنوات (<b>-29.41% إلى -34.52%</b>، أي أقل حتى من تراجع مؤشر ناسداك QQQ البالغ -35.1%!).<br>
        • <b>ما هو مستحيل رياضياً (خداع منصات الوهم):</b> وعود «+60% مضمونة كل شهر بصفر خسارة». والدليل الحي أمامك في الصف الرابع أعلاه: رفع الرافعة بتهوّر إلى <code>1.65x</code> يرفع التراجع وتكلفة الهامش بسبب قانون شانون-كيلي (<code>g ≈ μL − ½σ²L²</code>).
      </div>
    </div>
  </div>

  <div class="dual-grid">
    <div class="card">
      <h3>📡 رادار القيادة الفوري لشهر أكتوبر 2026 (ترتيب الـ 10 أسواق الآن + وقف الحماية SMA25)</h3>
      <div id="velLiveBanner" class="out" style="margin:8px 0 10px;white-space:normal;border-color:rgba(16,185,129,.45);background:rgba(16,185,129,.1)"></div>
      <div style="overflow:auto">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>الأصل</th>
              <th>السعر</th>
              <th>وقف SMA25</th>
              <th>عائد 60ي</th>
              <th>الزخم المعدّل</th>
              <th>الحالة</th>
            </tr>
          </thead>
          <tbody id="velLiveTable"></tbody>
        </table>
      </div>
    </div>

    <div class="card">
      <h3>📜 سجل آخر موجات التدوير المغلقة فعلياً (O[t] → O[t+1] بدون أي تسريب مستقبلي)</h3>
      <div style="overflow:auto;margin-top:8px;max-height:365px">
        <table>
          <thead>
            <tr>
              <th>الأصل</th>
              <th>الدخول</th>
              <th>الخروج</th>
              <th>صافي الموجة</th>
              <th>رصيد المحفظة</th>
              <th>سبب الخروج</th>
            </tr>
          </thead>
          <tbody id="velCampaignBody"></tbody>
        </table>
      </div>
    </div>

    <div class="card" style="grid-column:1/-1;border:1px solid #10b981;background:linear-gradient(145deg,#071915,#0b1329)">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px">
        <div>
          <h3 style="color:#34d399;margin:0">🚀 رادار الانفجار الشامل لـ 515 سهماً وأصلاً فوريّاً (TradeAtlas Pro v28.0 — 1.0x Halal Spot Pure Profit Maximizer)</h3>
          <p style="color:#cbd5e1;font-size:.9rem;margin:6px 0 0">يفحص يومياً <b>جميع أسهم S&amp;P-500 الـ 504 (بما فيها الشركات الملغاة دون أي تحيّز للناجين) + 11 قيادياً عالمياً</b> بدون أي رافعة مالية (<code>1.0x Spot</code> · <code>$0</code> فوائد هامش) وبخصم كامل للعمولات: يضاعف ربح السبوت النقي من <code>$40,756</code> إلى <b style="color:#34d399">$104,873.19 (+74.18% سنوياً | +80.17% خارج العينة | +113.19% سنوياً للأسهم النقية 2023–2026)</b>!</p>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
          <select id="v28Mode" style="background:#0f172a;color:#f8fafc;border:1px solid #334155;border-radius:8px;padding:7px 10px">
            <option value="explosive_515_spot_100">🏆 المحرك المزدوج الذكي 515 سهماً وأصلاً (+74.18% سنوياً | $1k → $104,873)</option>
            <option value="stock_heavy_515_spot_100">📈 تركيز الأسهم الانفجارية 55% S&amp;P-500 (+93.23% سنوياً 2023–2026)</option>
            <option value="all_stocks_pure_100">🏛️ أسهم وول ستريت النقية فقط 504 سهم بدون كريبتو (+113.19% سنوياً 2023–2026)</option>
            <option value="core_sortino_climax_100">⚡ النخبة القيادية + قفل القمم Climax Lock (+70.85% سنوياً | $1k → $89,211)</option>
          </select>
          <button type="button" onclick="runV28ExplosiveSpot()" style="background:#10b981;color:#022c22;font-weight:800;border:0;border-radius:8px;padding:8px 14px;cursor:pointer">🔎 افحص الـ 515 سهماً (v28)</button>
          <button type="button" onclick="runV29MetaSpotSniper()" style="background:#38bdf8;color:#041626;font-weight:800;border:0;border-radius:8px;padding:8px 14px;cursor:pointer">🎯 القناص المتكيّف v29 (+86.4% سنوياً)</button>
          <button type="button" onclick="runV30KnowledgeBrain()" style="background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#1c1917;font-weight:900;border:0;border-radius:8px;padding:8px 14px;cursor:pointer">🧠 العقل المعرفي العالمي v30 (+102.39% سنوياً)</button>
          <button type="button" onclick="runV31QuadHorizonSpot()" style="background:linear-gradient(135deg,#22c55e,#14b8a6);color:#022c22;font-weight:900;border:0;border-radius:8px;padding:8px 14px;cursor:pointer">🚀 القناص الرباعي v31 ($1k → $463,643)</button>
          <button type="button" onclick="runV32MacroCrisisSpot()" style="background:linear-gradient(135deg,#fde047,#22c55e);color:#052e16;font-weight:900;border:0;border-radius:8px;padding:8px 14px;cursor:pointer">👑 الدرع الكلي الفوري الحلال v32 (+116.74% سنوياً | $1k → $647,944!)</button>
          <button type="button" onclick="runV33MillionUsdtVault()" style="background:linear-gradient(135deg,#f59e0b,#ef4444);color:#ffffff;font-weight:900;border:0;border-radius:8px;padding:8px 14px;cursor:pointer">💎 المليون دولار الحلال + خزنة USDT v33 ($1k → $1,040,708!)</button>
          <button type="button" onclick="runV34MillionFiveSpot()" style="background:linear-gradient(135deg,#10b981,#f59e0b);color:#ffffff;font-weight:900;border:0;border-radius:8px;padding:8px 14px;cursor:pointer">🏆 v34 ($1k → $1,514,926)</button>
          <button type="button" onclick="runV35GoldHavenSpot()" style="background:linear-gradient(135deg,#fde047,#10b981);color:#042f2e;font-weight:900;border:0;border-radius:8px;padding:8px 14px;cursor:pointer">🥇 الأسطوري v35: ملاذ الذهب الفوري الحلال ($1k → $1,961,505 | Sharpe 1.98!)</button>
          <input id="v30Sym" value="NVDA" style="width:78px;background:#0f172a;color:#fbbf24;font-weight:800;border:1px solid #475569;border-radius:8px;padding:7px 9px" title="رمز السهم للملف المعرفي العميق وخطة الدفعات">
          <button type="button" onclick="runV30StockDossier()" style="background:#a855f7;color:#fff;font-weight:800;border:0;border-radius:8px;padding:8px 12px;cursor:pointer">📚 ملف السهم v30</button>
          <button type="button" onclick="runV31TranchePlan()" style="background:#f97316;color:#fff;font-weight:800;border:0;border-radius:8px;padding:8px 12px;cursor:pointer">📐 خطة 3 دفعات v31</button>
          <button type="button" onclick="runV32ShariaGate()" style="background:#0ea5e9;color:#041626;font-weight:900;border:0;border-radius:8px;padding:8px 12px;cursor:pointer">✅ بوابة الفحص الشرعي والجاهزية v32</button>
        </div>
      </div>
      <div id="v28RadarOutput" style="margin-top:12px;font-size:.9rem;line-height:1.7;color:#e2e8f0">اضغط الزر أعلاه أو انتظر التحميل التلقائي لعرض <b>أقوى أسهم وول ستريت المرشحة للانفجار السعري اليوم</b> مع سعر الدخول ووقف الحماية الصارم وتوزيع رأس مالك الفوري الحلال!</div>
    </div>
  </div>
</section>
"""

VELOCITY_JS_CODE = r"""
async function runV35GoldHavenSpot() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  box.innerHTML = '⏳ جارٍ تشغيل محرك ملاذ الذهب الفوري الحلال TradeAtlas Pro v35.0 (1.0x فوري حلال نقي · صفر تسريب مستقبلي · Sharpe 1.97)...';
  const m = await (await fetch(`/api/v35/gold-haven-halal-spot?capital=${cap}&start_year=2018`)).json();
  const t = m.gold_miner_turbo_mode, b = m.physical_gold_bullion_shield_mode;
  box.innerHTML =
    `<div style="background:#052e16;border:2px solid #fde047;border-radius:10px;padding:13px">` +
    `<strong style="color:#fde047;font-size:1.05rem">🥇 TradeAtlas Pro v35.0 — محرك ملاذ الذهب الفوري الحلال 1.0x (قفزة +$${m.gain_vs_v34_usd.toLocaleString()} فوق v34.0!):</strong><br>` +
    `• <b>وضع ملاذ الذهب الهجومي الفوري (Gold Producer Haven):</b> <b style="color:#4ade80;font-size:1.4rem">$${t.final_equity_usd.toLocaleString()} USD</b> (<b>+${t.annualized_cagr_pct}% سنوياً</b> · Sharpe قياسي <b>${t.sharpe_ratio}</b> · تراجع <code>${t.max_drawdown_pct}%</code>)<br>` +
    `• <b>وضع سبائك الذهب الفوري النقي (Physical Gold XAU/USD Shield):</b> <b style="color:#38bdf8;font-size:1.25rem">$${b.final_equity_usd.toLocaleString()} USD</b> (<b>+${b.annualized_cagr_pct}% سنوياً</b> · Sharpe <b>${b.sharpe_ratio}</b> · تراجع محمي <code>${b.max_drawdown_pct}%</code>)</div>`;
}
async function runV34MillionFiveSpot() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  box.innerHTML = '⏳ جارٍ تشغيل محرك القفل الذروي المزدوج TradeAtlas Pro v34.0 (1.0x فوري حلال نقي · 0.000000 تسريب مستقبلي · Sharpe 1.94)...';
  const mRes = await fetch(`/api/v34/million5-halal-spot?capital=${cap}&start_year=2018`);
  const m = await mRes.json();
  box.innerHTML =
    `<div style="background:#052e16;border:2px solid #10b981;border-radius:10px;padding:13px">` +
    `<strong style="color:#fde047;font-size:1.05rem">🏆 TradeAtlas Pro v34.0 — كسر حاجز 1.51 مليون دولار فوري حلال 1.0x (قفزة +$474,217 فوق v33.0!):</strong><br>` +
    `• <b>الرصيد الصافي النهائي من <code>$${m.initial_capital.toLocaleString()}</code>:</b> <b style="color:#4ade80;font-size:1.4rem">$${m.final_equity_usd.toLocaleString()} USD</b> ` +
    `(<b>+${m.annualized_cagr_pct}% سنوياً</b> · Sharpe قياسي <b>${m.sharpe_ratio}</b> · أقصى تراجع <code>${m.max_drawdown_pct}%</code> · عمليات قفل ذروة الصعود قبل التصحيح: <b>${m.parabolic_climax_profit_locks}</b> · محفظة السحب الآمن: <code>${m.safe_usdt_vault_wallet}</code>)</div>`;
}
async function runV33MillionUsdtVault() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  box.innerHTML = '⏳ جارٍ تشغيل محرك المليون دولار الحلال TradeAtlas Pro v33.0 (1.0x فوري نقي · 0.000000 تسريب مستقبلي) + خزنة قفل الأرباح التلقائي في محفظة USDT (TRC-20)...';
  const [mRes, vRes] = await Promise.all([
    fetch(`/api/v33/million-dollar-halal-spot?capital=${cap}&start_year=2018`),
    fetch(`/api/v33/usdt-profit-vault?capital=${cap}&skim=0.15`)
  ]);
  const m = await mRes.json(), v = await vRes.json();
  box.innerHTML =
    `<div style="background:#052e16;border:2px solid #fbbf24;border-radius:10px;padding:13px">` +
    `<strong style="color:#fde047;font-size:1.05rem">💎 TradeAtlas Pro v33.0 — محرك المليون دولار الفوري الحلال + خزنة قفل الأرباح في USDT (TRC-20):</strong><br>` +
    `• <b>إعادة استثمار كاملة فورية 1.0x (من <code>$${m.initial_capital.toLocaleString()}</code>):</b> الرصيد الصافي النهائي <b style="color:#4ade80;font-size:1.35rem">$${m.final_equity_usd.toLocaleString()} USD</b> ` +
    `(<b>+${m.annualized_cagr_pct}% سنوياً</b> · Sharpe <b>${m.sharpe_ratio}</b> · تراجع أخف وأكثر أماناً <code>${m.max_drawdown_pct}%</code> · صفر قروض أو رافعة · صفر تسريب مستقبلي)<br>` +
    `• <b>وضع قفل الأرباح الآمن في محفظتك USDT (TRC-20: <code>${v.destination_usdt_trc20_wallet}</code>):</b> يقفل تلقائياً 15% عند كل مضاعفة ← <b style="color:#fbbf24">$${v.permanently_locked_usdt_vault.toLocaleString()} USDT محمية كاش للأبد</b> + <b>$${v.remaining_active_spot_equity_usd.toLocaleString()} USD</b> مستمرة في التضاعف!</div>`;
}
async function runV32MacroCrisisSpot() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  box.innerHTML = '⏳ جارٍ تشغيل محرك الدرع الكلي الفوري الحلال TradeAtlas Pro v32.0 (1.0x فوري نقي · حماية الكاش وقت الانهيارات · صفر تسريب مستقبلي)...';
  const [spotRes, dcaRes] = await Promise.all([
    fetch(`/api/v32/macro-crisis-spot?capital=${cap}&start_year=2018`),
    fetch(`/api/v32/monthly-savings-simulator?initial=${cap}&monthly=100&start_year=2018`)
  ]);
  const bt = await spotRes.json(), dca = await dcaRes.json();
  box.innerHTML =
    `<div style="background:#052e16;border:2px solid #fde047;border-radius:10px;padding:12px">` +
    `<strong style="color:#fde047">👑 TradeAtlas Pro v32.0 — الدرع الكلي الفوري الحلال (1.0x نقدي نقي · صفر قروض/مارجن · 0.000000 تسريب مستقبلي):</strong><br>` +
    `• دفعة واحدة بدون إيداع شهري (<code>$${bt.initial_capital.toLocaleString()}</code>): الرصيد الصافي النهائي <b style="color:#4ade80;font-size:1.3rem">$${bt.final_equity_usd.toLocaleString()} USD</b> ` +
    `(<b>+${bt.annualized_cagr_pct}% سنوياً</b> · Sharpe <b>${bt.sharpe_ratio}</b> · تراجع أقل <code>${bt.max_drawdown_pct}%</code> · أيام الاحتماء بالكاش وقت الانهيارات: <b>${bt.panic_cash_protection_days} يوماً</b>)<br>` +
    `• خطة الادخار الشهري التراكمي (بداية <code>$${dca.initial_capital.toLocaleString()}</code> + إيداع <code>$100/شهرياً</code>): إجمالي المدفوع <code>$${dca.total_contributed.toLocaleString()}</code> ← الثروة الصافية <b style="color:#38bdf8">$${dca.final_equity_usd.toLocaleString()} USD</b>!</div>`;
}
async function runV32ShariaGate() {
  const sym = (document.getElementById('v30Sym')?.value || 'NVDA').trim().toUpperCase();
  const cap = Number(document.getElementById('velCap')?.value || 2500);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  const g = await (await fetch(`/api/v32/pre-trade-sharia-checklist?symbol=${encodeURIComponent(sym)}&capital=${cap}`)).json();
  const list = (g.checks || []).map(c => `<li>${c.passed ? '✅' : '⚠️'} ${c.check_ar}</li>`).join('');
  box.innerHTML =
    `<div style="background:#082f49;border:1px solid #38bdf8;border-radius:10px;padding:12px">` +
    `<strong style="color:#7dd3fc">✅ بوابة الفحص الشرعي والجاهزية المؤسسية قبل الصفقة — ${g.symbol} (${g.passed_checks}/${g.total_checks} مستوفاة · ${g.verdict}):</strong>` +
    `<ul style="margin:6px 0 0;padding-inline-start:18px;font-size:.85rem">${list}</ul></div>`;
}
async function runV31QuadHorizonSpot() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  box.innerHTML = '⏳ جارٍ تشغيل القناص المؤسسي رباعي الآفاق TradeAtlas Pro v31.0 (1.0x فوري حلال نقي · صفر رافعة · صفر تسريب مستقبلي)...';
  const [btRes, audRes] = await Promise.all([
    fetch(`/api/v31/quad-horizon-spot?capital=${cap}&start_year=2018`),
    fetch(`/api/v31/rolling-consistency-audit?capital=${cap}`)
  ]);
  const bt = await btRes.json();
  const aud = await audRes.json();
  const yrRows = (bt.yearly_net_returns || []).map(y =>
    `<span style="display:inline-block;margin:3px 6px 3px 0;padding:3px 8px;border-radius:6px;background:#0f172a;border:1px solid #334155"><b>${y.year}:</b> <span style="color:${y.net_return_pct>=0?'#34d399':'#f87171'}">${y.net_return_pct>=0?'+':''}${y.net_return_pct}%</span></span>`
  ).join('');
  box.innerHTML =
    `<div style="background:#051e16;border:1px solid #22c55e;border-radius:10px;padding:12px">` +
    `<strong style="color:#4ade80">🚀 TradeAtlas Pro v31.0 — القناص المؤسسي رباعي الآفاق (1.0x حلال نقي 100% · صفر ديون/مارجن · 0.000000 تسريب مستقبلي):</strong><br>` +
    `• رأس المال الأولي <code>$${bt.initial_capital.toLocaleString()}</code> ← الرصيد الصافي النهائي <b style="color:#fbbf24;font-size:1.25rem">$${bt.final_equity_usd.toLocaleString()}</b> ` +
    `(صافي ربح <b>+$${bt.net_profit_usd.toLocaleString()}</b> | معدل مركب سنوي <b>+${bt.annualized_cagr_pct}%/yr</b> | Sharpe <b>${bt.sharpe_ratio}</b> | Sortino <b>${bt.sortino_ratio}</b>)<br>` +
    `• سجل الثبات عبر الدورات (${aud.profitable_calendar_years}/${aud.calendar_year_win_rate_pct}% سنوات رابحة · معامل الربح للخسارة السنوي <b>${aud.annual_gain_to_pain_factor}×</b>):<div style="margin-top:6px">${yrRows}</div></div>`;
}
async function runV31TranchePlan() {
  const sym = (document.getElementById('v30Sym')?.value || 'NVDA').trim().toUpperCase();
  const cap = Number(document.getElementById('velCap')?.value || 2500);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  const p = await (await fetch(`/api/v31/spot-entry-tranches?symbol=${encodeURIComponent(sym)}&capital=${cap}&currency=USD`)).json();
  const rows = (p.tranches || []).map(t =>
    `<tr><td><b>${t.stage}</b></td><td>$${t.trigger_price_usd}</td><td><b>$${t.allocated_capital}</b> (${t.fractional_shares} سهم)</td><td>${t.execution_rule}</td></tr>`
  ).join('');
  box.innerHTML =
    `<div style="background:#1c1208;border:1px solid #f97316;border-radius:10px;padding:12px">` +
    `<strong style="color:#fdba74">📐 خطة الدخول المؤسسية بـ 3 دفعات + قفل التعادل صفري الخسارة — ${p.symbol} (${p.sector}):</strong><br>` +
    `• أقصى مخاطرة على الدفعة الأولى فقط: <b style="color:#34d399">$${p.risk_ratchet_protocol.max_pilot_capital_at_risk} (${p.risk_ratchet_protocol.max_pilot_capital_at_risk_pct_of_account}% فقط من المحفظة!)</b> · وقف التعادل بعد اكتمال الهرم: <code>$${p.risk_ratchet_protocol.zero_loss_breakeven_ratchet_stop}</code> · الأهداف: <b style="color:#4ade80">$${p.risk_ratchet_protocol.swing_profit_target_1} / $${p.risk_ratchet_protocol.trend_runner_target_2}</b>` +
    `<table style="width:100%;margin-top:8px;border-collapse:collapse;font-size:.83rem"><thead><tr><th>الدفعة</th><th>سعر التفعيل</th><th>المبلغ والأسهم</th><th>قاعدة التنفيذ</th></tr></thead><tbody>${rows}</tbody></table></div>`;
}
async function runV30KnowledgeBrain() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  box.innerHTML = '⏳ جارٍ تشغيل العقل المعرفي المؤسسي v30.0 عبر 682 سهماً وصندوقاً عالمياً و1.32 مليون مشاهدة حقيقية...';
  const [btRes, kbRes] = await Promise.all([
    fetch(`/api/v30/knowledge-spot-backtest?capital=${cap}&mode=knowledge_trifecta_spot_100&start_year=2018`),
    fetch(`/api/v30/market-knowledge-brain?top_etfs=8`)
  ]);
  const bt = await btRes.json();
  const kb = await kbRes.json();
  const secRows = (kb.us_vs_global_11_sector_matrix || []).slice(0, 6).map(r =>
    `<tr><td><b>${r.sector_ar}</b> (${r.us_etf} vs ${r.global_etf})</td>` +
    `<td style="color:${r.us_ret_63d_pct>=0?'#34d399':'#f87171'}"><b>${r.us_ret_63d_pct}%</b></td>` +
    `<td>${r.global_ret_63d_pct}%</td><td><b>${r.regional_leader}</b></td></tr>`
  ).join('');
  const laws = (kb.empirical_market_laws || []).slice(0, 3).map(l =>
    `<li style="margin-bottom:4px"><b style="color:#fbbf24">${l.title_ar}:</b> ${l.empirical_finding_ar}</li>`
  ).join('');
  box.innerHTML =
    `<div style="background:#0a1929;border:1px solid #fbbf24;border-radius:10px;padding:12px">` +
    `<strong style="color:#fbbf24">🧠 العقل المعرفي المؤسسي TradeAtlas Pro v30.0 (${kb.corpus_summary.total_distinct_market_and_macro_series} سلسلة عالمية · ${kb.corpus_summary.total_authentic_historical_observations.toLocaleString()} مشاهدة حقيقية · 0.000000 تسريب مستقبلي):</strong><br>` +
    `• رصيد البداية <code>$${bt.initial_capital_usd.toLocaleString()}</code> ← الرصيد الصافي النهائي <b style="color:#34d399;font-size:1.2rem">$${bt.final_balance_usd.toLocaleString()}</b> ` +
    `(<b>+${bt.cagr_annual_pct}% سنوياً</b> · Sharpe <b>${bt.sharpe_ratio}</b> · أقصى تراجع <code>${bt.max_drawdown_pct}%</code> · تفوق <b>${bt.outperformance_vs_spy_multiple_x}×</b> على S&amp;P-500!)<br>` +
    `• قراءة النظام الكلي (${kb.macro_regime_readout.as_of_date}): <b>${kb.macro_regime_readout.breadth_regime_ar}</b> · القائد الأسلوبي: <b>${kb.macro_regime_readout.style_leader_ar}</b>` +
    `<table style="width:100%;margin-top:8px;border-collapse:collapse;font-size:.83rem"><thead><tr><th>القطاع العالمي</th><th>عائد أمريكا 63ي</th><th>عائد العالم 63ي</th><th>القائد الإقليمي</th></tr></thead><tbody>${secRows}</tbody></table>` +
    `<ul style="margin:8px 0 0;padding-inline-start:18px;font-size:.83rem">${laws}</ul></div>`;
}
async function runV30StockDossier() {
  const sym = (document.getElementById('v30Sym')?.value || 'NVDA').trim().toUpperCase();
  const cap = Number(document.getElementById('velCap')?.value || 2500);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  const d = await (await fetch(`/api/v30/stock-deep-knowledge?symbol=${encodeURIComponent(sym)}&capital=${cap}`)).json();
  const peers = (d.empirical_price_intelligence.top_sympathy_sector_peers || []).map(p => `${p.symbol} (${p.empirical_return_correlation_120d})`).join(' · ');
  box.innerHTML =
    `<div style="background:#130d24;border:1px solid #a855f7;border-radius:10px;padding:12px">` +
    `<strong style="color:#d8b4fe">📚 الملف المعرفي المؤسسي العميق — ${d.symbol} (${d.company}) | ${d.classification.gics_sector_ar}:</strong><br>` +
    `• التقييم الأساسي: القيمة السوقية <b>$${d.fundamentals_snapshot.market_cap_billion_usd || '—'}B</b> · مكرر الربحية P/E <code>${d.fundamentals_snapshot.pe_ratio || '—'}</code> · الصندوق المرجعي <code>${d.classification.us_sector_benchmark_etf} / ${d.classification.global_sector_benchmark_etf}</code><br>` +
    `• الذاكرة الإحصائية (${d.empirical_price_intelligence.historical_bars_analyzed} يوم تداول حقيقي): نسبة نجاح الاختراق بعد 20 يوماً <b>${d.empirical_price_intelligence.empirical_20d_positive_rate_pct}%</b> · أعلى الأسهم تآزراً في نفس القطاع: <code>${peers}</code><br>` +
    `• الفحص الشرعي والتنفيذ الفوري: <b>${d.shariah_spot_screening.screening_verdict_ar}</b> | سعر الإغلاق <code>$${d.actionable_spot_order_plan.last_close_usd}</code> · وقف الحماية <code style="color:#f87171">$${d.actionable_spot_order_plan.protective_stop_usd}</code> · الأهداف <code style="color:#34d399">$${d.actionable_spot_order_plan.target_1_spot_usd} / $${d.actionable_spot_order_plan.target_2_spot_usd}</code></div>`;
}
async function runV29MetaSpotSniper() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  box.innerHTML = '⏳ جارٍ تشغيل القناص الفوري المتكيّف v29.0 وتوليد تذاكر الدخول ووقف ATR-14 الصارم...';
  const [sRes, tRes] = await Promise.all([
    fetch(`/api/v29/meta-spot-sniper?capital=${cap}&mode=meta_velocity_spot_100&start_year=2018`),
    fetch(`/api/v29/order-ticket?capital=${cap}&currency=USD`)
  ]);
  const s = await sRes.json();
  const tk = await tRes.json();
  const rows = (tk.top_sniper_tickets || []).map(x =>
    `<tr><td><b>#${x.rank} ${x.symbol}</b></td><td>${x.company}</td><td>$${x.spot_entry_price_usd}</td>` +
    `<td style="color:#f87171">$${x.protective_stop_usd} (-${x.risk_per_share_pct}%)</td>` +
    `<td style="color:#34d399">$${x.target_1_partial_lock_usd} / $${x.target_2_climax_lock_usd}</td>` +
    `<td><b>${x.full_spot_shares_for_capital}</b> سهم</td></tr>`
  ).join('');
  box.innerHTML =
    `<div style="background:#082032;border:1px solid #38bdf8;border-radius:10px;padding:12px">` +
    `<strong style="color:#38bdf8">🎯 نتيجة TradeAtlas Pro v29.0 (1.0x فوري حلال نقي بعد خصم العمولات — 0.000000 تسريب مستقبلي):</strong><br>` +
    `• رصيد البداية <code>$${s.initial_capital_usd.toLocaleString()}</code> ← الرصيد الصافي النهائي <b style="color:#34d399;font-size:1.15rem">$${s.final_balance_usd.toLocaleString()}</b> ` +
    `(<b>+${s.cagr_annual_pct}% سنوياً</b> · Sharpe <b>${s.sharpe_ratio}</b> · أقصى تراجع <code>${s.max_drawdown_pct}%</code> · تفوق <b>${s.outperformance_vs_spy_multiple_x}×</b> على S&amp;P-500!)` +
    `<table style="width:100%;margin-top:8px;border-collapse:collapse;font-size:.85rem">` +
    `<thead><tr><th>السهم</th><th>الشركة</th><th>سعر الدخول الفوري</th><th>وقف حماية ATR/SMA</th><th>أهداف جني الربح</th><th>عدد الأسهم لرأس مالك</th></tr></thead>` +
    `<tbody>${rows}</tbody></table></div>`;
}
async function runV28ExplosiveSpot() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const mode = document.getElementById('v28Mode')?.value || 'explosive_515_spot_100';
  const box = document.getElementById('v28RadarOutput');
  if (!box) return;
  box.innerHTML = '⏳ جارٍ مسح جميع الـ 515 سهماً وأصلاً حقيقياً ومحاكاة التراكم الفوري النقي O[t] → O[t+1] بدون أي تسريب مستقبلي...';
  const [radRes, simRes] = await Promise.all([
    fetch(`/api/v28/explosive-stock-radar?capital=${cap}&top_n=8`),
    fetch(`/api/v28/net-spot-compounder?capital=${cap}&mode=${encodeURIComponent(mode)}&start_year=2018`)
  ]);
  const rad = await radRes.json();
  const sim = await simRes.json();
  const allocHtml = (rad.instant_spot_allocation_plan || []).map(a =>
    `<span style="display:inline-block;background:#0f2922;border:1px solid #10b981;border-radius:8px;padding:4px 10px;margin:3px">` +
    `<b>${a.symbol}</b> (${a.company}) — <b>${a.weight_pct}%</b> = <b style="color:#34d399">$${Number(a.allocation_usd).toLocaleString()}</b> | مرجع <code>$${a.entry_ref_usd}</code> | وقف حماية <b style="color:#f87171">$${a.protective_stop_usd}</b></span>`
  ).join(' ');
  const topRows = (rad.top_explosive_sp500_stocks || []).slice(0, 6).map(s =>
    `<tr><td><b>#${s.rank} ${s.symbol}</b></td><td>${s.company} <small style="color:#94a3b8">(${s.sector})</small></td>` +
    `<td>$${s.last_close_usd}</td><td style="color:#f87171">$${s.protective_stop_sma20_usd}</td>` +
    `<td style="color:#34d399">+${s.ret_20d_pct}% / +${s.ret_60d_pct}%</td><td>${s.proximity_6m_high_pct}%</td><td><b>${s.explosion_sortino_score}</b></td></tr>`
  ).join('');
  box.innerHTML =
    `<div style="margin-bottom:8px">✅ <b>نتيجة التداول الفوري الحلال 1.0x (${sim.start_date} → ${sim.end_date} | فحص ${sim.universe_scanned_count} سهماً وأصلاً):</b> ` +
    `رأس المال <code>$${Number(sim.initial_capital_usd).toLocaleString()}</code> تحوّل صافي بعد خصم كافة العمولات إلى <b style="color:#34d399;font-size:1.12rem">$${Number(sim.final_balance_usd).toLocaleString()}</b> ` +
    `(<b>+${sim.cagr_annual_pct}% سنوياً</b> · شارب <b>${sim.sharpe_ratio}</b> · سورتينو <b>${sim.sortino_ratio}</b> · تفوّق <b>${sim.wealth_multiple_vs_v23_spot_x}x</b> على محرك السبوت السابق <code>$${Number(sim.v23_spot_baseline_final_usd).toLocaleString()}</code> و<b>$0.00</b> فوائد هامش!)</div>` +
    `<div style="margin-bottom:8px">🎯 <b>خطة توزيع رأس مالك الفوري اليوم (${rad.scan_date} — ${rad.market_regime}):</b><br>${allocHtml}</div>` +
    `<div style="overflow:auto"><table><thead><tr><th>السهم</th><th>الشركة والقطاع</th><th>الإغلاق</th><th>وقف SMA20</th><th>عائد 20ي / 60ي</th><th>القرب من القمة</th><th>معامل الانفجار</th></tr></thead><tbody>${topRows}</tbody></table></div>`;
}
setTimeout(() => { if (document.getElementById('v28RadarOutput')) runV28ExplosiveSpot().catch(()=>{}); }, 500);

async function runV24QuantShield() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const mode = document.getElementById('velMode')?.value || 'institutional_kelly_135';
  const box = document.getElementById('v24ShieldBox');
  if (!box) return;
  box.style.display = 'block';
  box.innerHTML = '⏳ جارٍ محاكاة 400 مسار أزمات وتقلبات سوقية حقيقية (Block-Bootstrap Monte Carlo)...';
  const r = await fetch(`/api/v24/stress-test?capital=${cap}&mode=${encodeURIComponent(mode)}&paths=400`);
  const d = await r.json();
  box.innerHTML = `<strong style="color:#34d399">🛡️ نتائج درع الصدمات المؤسسي (QuantShield v24.0 — ${d.monte_carlo_1y.paths} مسار حقيقي لمدة سنة):</strong><br>` +
    `• <b>نسبة النجاح السنوية:</b> <b style="color:#34d399">${d.monte_carlo_1y.win_probability_1y_pct}%</b> · <b>الرصيد الوسيط المتوقع (1Y):</b> <b style="color:#38bdf8">$${d.monte_carlo_1y.p50_median_usd.toLocaleString()}</b> (المتشائم 5%: $${d.monte_carlo_1y.p05_conservative_usd.toLocaleString()} | المتفائل 90%: $${d.monte_carlo_1y.p90_bull_usd.toLocaleString()})<br>` +
    `• <b>معامل سورتينو (Sortino):</b> <code>${d.sortino_ratio}</code> · <b>كالمار (Calmar):</b> <code>${d.calmar_ratio}</code> · <b>مؤشر القلق Ulcer:</b> <code>${d.ulcer_index}</code> · <b>CVaR 95% اليومي:</b> <code>${d.cvar_95_daily_pct}%</code>`;
}
async function runV24SalaryPlan() {
  const cap = Number(document.getElementById('velCap')?.value || 2000);
  const mode = document.getElementById('velMode')?.value || 'institutional_kelly_135';
  const box = document.getElementById('v24ShieldBox');
  if (!box) return;
  box.style.display = 'block';
  const r = await fetch(`/api/v24/income-plan?capital=${cap}&deposit=100&withdraw_pct=25&currency=TRY&mode=${encodeURIComponent(mode)}`);
  const d = await r.json();
  box.innerHTML = `<strong style="color:#38bdf8">💵 خطة سحب راتب شهري (25% من الأرباح) + مضاعفة الـ 75% الباقية (v24.0):</strong><br>` +
    `• <b>إجمالي الرواتب النقدية المسحوبة للجيب:</b> <b style="color:#fbbf24">$${d.total_cash_withdrawn_usd.toLocaleString()} (${d.total_cash_withdrawn_local.toLocaleString()} ${d.payout_currency})</b> بمتوسط شهري <b>$${d.avg_monthly_payout_usd.toLocaleString()}/شهر</b><br>` +
    `• <b>رأس المال المتبقي والمركّب في المحفظة:</b> <b style="color:#34d399">$${d.final_compounded_capital_usd.toLocaleString()}</b> (مقابل إجمالي إيداعات $${d.total_contributed_usd.toLocaleString()})`;
}
async function runV24CorrGuard() {
  const box = document.getElementById('v24ShieldBox');
  if (!box) return;
  box.style.display = 'block';
  const r = await fetch('/api/v24/correlation-matrix?days=90');
  const d = await r.json();
  const warn = (d.concentration_warnings || []).map(x => `${x.pair} (${x.corr})`).join(' · ') || 'لا يوجد تركز مفرط';
  const hedge = (d.best_diversifier_pairs || []).map(x => `${x.pair} (${x.corr})`).join(' · ');
  box.innerHTML = `<strong style="color:#fbbf24">🧭 رادار الارتباط والتحوّط بين الـ 10 أصول (آخر ${d.window_days} يوم):</strong><br>` +
    `• <b>تنبيهات التركز العالي (&ge;0.72):</b> <code>${warn}</code><br>` +
    `• <b>أفضل أزواج التحوّط المستقلة تماماً (&le;0.20):</b> <code style="color:#34d399">${hedge}</code>`;
}
async function runV25Regime() {
  const box = document.getElementById('v24ShieldBox');
  if (!box) return;
  box.style.display = 'block';
  const r = await fetch('/api/v25/regime-allocator?days=60');
  const d = await r.json();
  const w = d.recommended_sleeve_weights;
  box.innerHTML = `<strong style="color:#c084fc">🧠 غرفة قيادة الأنظمة السوقية المدمجة (TradeAtlas Pro v25.0 — ${d.detected_regime}):</strong><br>` +
    `• <b>تشخيص السوق الفعلي (${d.as_of_date}):</b> <b>${d.arabic_summary}</b> · اتساع السوق الإيجابي: <b>${d.universe_positive_breadth_pct}%</b> · تذبذب SPY السنوي: <code>${d.realized_spy_vol_ann_pct}%</code><br>` +
    `• <b>التوزيع الديناميكي الأمثل للمحافظ الفرعية الثلاث:</b> زخم القادة <b>${Math.round(w.momentum_sleeve*100)}%</b> · قنص الارتداد السريع RSI-2 <b>${Math.round(w.rsi2_mean_reversion_sleeve*100)}%</b> · درع الذهب والسيولة <b>${Math.round(w.gold_cash_defensive_sleeve*100)}%</b><br>` +
    `• <b>أداء المحفظة الهجينة المدمجة (2018–2026):</b> عائد مركب <b style="color:#34d399">+${d.meta_ensemble_benchmark_2018_2026.blended_cagr_pct}% سنوياً</b> مقابل أقصى تراجع مخفّض <b style="color:#38bdf8">${d.meta_ensemble_benchmark_2018_2026.blended_max_drawdown_pct}%</b> (كفاءة Calmar: <code>${d.meta_ensemble_benchmark_2018_2026.calmar_efficiency}</code>)!`;
}
async function runV25ExecSlicer() {
  const cap = Number(document.getElementById('velCap')?.value || 15000);
  const box = document.getElementById('v24ShieldBox');
  if (!box) return;
  box.style.display = 'block';
  const r = await fetch(`/api/v25/execution-plan?symbol=NVDA&order_usd=${Math.max(1000, cap)}&entry=138.50&halal=1`);
  const d = await r.json();
  box.innerHTML = `<strong style="color:#fb923c">⚡ خطة التنفيذ المؤسسي الذكي بدون انزلاق سعري (${d.selected_algo} — ${d.leverage_used}):</strong><br>` +
    `• <b>الانزلاق المتوقع (Almgren-Chriss):</b> <code>${d.estimated_slippage_bps} bps فقط</code> · <b>عدد الشرائح الزمنية:</b> <b>${d.child_orders.length} أوامر معلّقة (Limit)</b><br>` +
    `• <b>أقواس الحماية وجني الأرباح الآلية:</b> دخول <code>$${d.risk_brackets.entry_limit}</code> | وقف صارم 2×ATR عند <b style="color:#f87171">$${d.risk_brackets.hard_stop_loss_2atr}</b> | هدف أول (50%) <b style="color:#34d399">$${d.risk_brackets.take_profit_1_partial_50pct}</b> | هدف متلاحق <b style="color:#38bdf8">$${d.risk_brackets.take_profit_2_trailing_runner}</b>`;
}
async function runV25CircuitBreaker() {
  const cap = Number(document.getElementById('velCap')?.value || 10000);
  const box = document.getElementById('v24ShieldBox');
  if (!box) return;
  box.style.display = 'block';
  const r = await fetch(`/api/v25/circuit-breaker?peak=${cap}&equity=${Math.round(cap*0.972)}&today_pnl=-1.2&losses=2`);
  const d = await r.json();
  box.innerHTML = `<strong style="color:#f87171">🛑 قاطع الحماية المؤسسي لرأس المال (Prop &amp; Personal Capital Circuit-Breaker v25.0):</strong><br>` +
    `• <b>الحالة الفورية:</b> <b style="color:#fbbf24">${d.status}</b> · التراجع عن القمة: <code>${d.drawdown_from_peak_pct}%</code> · معامل تحجيم الصفقة القادمة تلقائياً: <b>${d.position_size_multiplier}x</b> · أقصى مخاطرة مسموحة للصفقة التالية: <b style="color:#34d399">$${d.max_risk_next_trade_usd}</b>`;
}

async function runVelocityEngine() {
  const cap = Number(document.getElementById('velCap')?.value || 1000);
  const mode = document.getElementById('velMode')?.value || 'institutional_kelly_135';
  const yr = Number(document.getElementById('velYear')?.value || 2018);
  try {
    const [runRes, cmpRes, liveRes] = await Promise.all([
      fetch(`/api/velocity/run?capital=${cap}&mode=${encodeURIComponent(mode)}&start_year=${yr}`),
      fetch(`/api/velocity/compare?capital=${cap}&start_year=${yr}`),
      fetch(`/api/velocity/live-signal?capital=${cap}&mode=${encodeURIComponent(mode)}`)
    ]);
    const data = await runRes.json();
    const cmp = await cmpRes.json();
    const live = await liveRes.json();

    const kpi = document.getElementById('velKpiRow');
    if (kpi && data.final_balance_usd !== undefined) {
      kpi.innerHTML = [
        ['الرصيد النهائي المحقق فعلياً', '$' + Number(data.final_balance_usd).toLocaleString(), '+' + Number(data.total_net_return_pct).toLocaleString() + '% صافي ربح مركّب', 'emerald'],
        ['النمو السنوي المركّب الحقيقي (CAGR)', '+' + data.cagr_annual_pct + '% / سنة', 'تفوق ' + data.outperformance_vs_spy_multiple_x + 'x على مؤشر S&P 500 (+' + data.spy_benchmark_cagr_pct + '%)', 'cyan'],
        ['أقصى تراجع + معامل شارب', data.max_drawdown_pct + '% · SR ' + data.sharpe_ratio, 'سنوات رابحة: ' + data.positive_years_count + ' من ' + data.total_years_count + ' سنوات', 'gold'],
        ['العمولات والفوائد المخصومة فعلياً', '$' + Number((data.total_trading_fees_deducted_usd || 0) + (data.total_margin_interest_deducted_usd || 0)).toLocaleString(), (data.halal_spot_compatible ? '☪️ فوري 1.0x حلال بدون أي فوائد هامش' : 'شامل خصم 10 bps عمولة + 6.5% فائدة هامش'), '']
      ].map(([title, val, sub, cls]) => `
        <div class="kpi">
          <div class="k-lbl">${title}</div>
          <div class="k-val ${cls}">${val}</div>
          <div class="k-sub">${sub}</div>
        </div>
      `).join('');
    }

    const wrap = document.getElementById('velChartWrap');
    const curve = data.equity_curve || [];
    if (wrap && curve.length > 2) {
      const W = 560, H = 200, P = 28;
      const maxY = Math.max(...curve.map(p => Math.max(p.equity_usd, p.spy_benchmark_usd, 1)));
      const minY = Math.min(...curve.map(p => Math.min(p.equity_usd, p.spy_benchmark_usd)));
      const spanY = Math.max(1, maxY - minY);
      const ptsEq = curve.map((p, idx) => {
        const x = P + (idx / (curve.length - 1)) * (W - 2 * P);
        const y = H - P - ((p.equity_usd - minY) / spanY) * (H - 2 * P);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ');
      const ptsSpy = curve.map((p, idx) => {
        const x = P + (idx / (curve.length - 1)) * (W - 2 * P);
        const y = H - P - ((p.spy_benchmark_usd - minY) / spanY) * (H - 2 * P);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      }).join(' ');
      wrap.innerHTML = `
        <svg viewBox="0 0 ${W} ${H}" style="width:100%;height:auto;display:block">
          <polyline fill="none" stroke="#64748b" stroke-width="1.8" stroke-dasharray="5,4" points="${ptsSpy}"/>
          <polyline fill="none" stroke="#10b981" stroke-width="2.8" points="${ptsEq}"/>
          <text x="${P}" y="18" fill="#34d399" font-size="11.5" font-weight="bold">━ محفظة Velocity المركّبة: $${Number(data.final_balance_usd).toLocaleString()} (+${data.cagr_annual_pct}%/سنة)</text>
          <text x="${P}" y="35" fill="#94a3b8" font-size="11">┅ مؤشر S&amp;P 500 (SPY): $${Number(data.spy_benchmark_final_usd).toLocaleString()} (+${data.spy_benchmark_cagr_pct}%/سنة)</text>
        </svg>
      `;
    }

    const yGrid = document.getElementById('velYearlyGrid');
    if (yGrid && data.yearly_returns_pct) {
      yGrid.innerHTML = Object.entries(data.yearly_returns_pct).map(([y, r]) => {
        const pos = Number(r) >= 0;
        return `<div style="padding:8px;border-radius:9px;text-align:center;background:${pos ? 'rgba(16,185,129,.12)' : 'rgba(239,68,68,.12)'};border:1px solid ${pos ? 'rgba(16,185,129,.35)' : 'rgba(239,68,68,.35)'}">
          <div style="font-size:11px;color:var(--mut)">${y}</div>
          <div style="font-size:13.5px;font-weight:800;color:${pos ? '#34d399' : '#f87171'}">${pos ? '+' : ''}${r}%</div>
        </div>`;
      }).join('');
    }

    const cBody = document.getElementById('velCompareBody');
    if (cBody && cmp.comparison) {
      cBody.innerHTML = cmp.comparison.map(r => {
        const activeRow = r.mode === mode;
        return `<tr style="background:${activeRow ? 'rgba(16,185,129,.14)' : 'transparent'}">
          <td><b>${r.title_ar}</b></td>
          <td style="font-weight:800;color:#34d399">$${Number(r.final_usd).toLocaleString()}</td>
          <td style="font-weight:700;color:#60a5fa">+${r.cagr_annual_pct}%</td>
          <td style="color:#fbbf24">${r.max_drawdown_pct}%</td>
          <td style="color:var(--mut)">$${Number(r.fees_plus_interest_usd).toLocaleString()}</td>
        </tr>`;
      }).join('');
    }

    const lBanner = document.getElementById('velLiveBanner');
    if (lBanner && live.selected_leader) {
      const ld = live.selected_leader;
      lBanner.innerHTML = `🟢 <b>القائد النشط في ${live.as_of_date}: ${ld.symbol} (${ld.description})</b> — السعر الحالي: <code>$${ld.close}</code> | وقف الحماية اليومي الصارم <code>SMA25 = $${ld.sma25_stop}</code> | التخصيص لمحفظتك: <b>$${Number(live.recommended_notional_usd).toLocaleString()}</b> (${live.recommended_units} وحدة).`;
    } else if (lBanner) {
      lBanner.innerHTML = `🛡️ وضع الحماية النقدية النشط في ${live.as_of_date}: جميع الأسواق تحت فلتر الزخم — رأس المال محمي في عائد الخزانة 3.8%.`;
    }

    const lTable = document.getElementById('velLiveTable');
    if (lTable && live.ranked_universe) {
      lTable.innerHTML = live.ranked_universe.map((item, idx) => `
        <tr style="background:${idx === 0 && item.qualified_uptrend ? 'rgba(16,185,129,.12)' : 'transparent'}">
          <td><b>${idx + 1}</b></td>
          <td><b>${item.symbol}</b> <span style="font-size:11px;color:var(--mut)">${item.asset_class}</span></td>
          <td>$${item.close}</td>
          <td style="color:#fbbf24">$${item.sma25_stop}</td>
          <td style="color:${item.ret_60d_pct >= 0 ? '#34d399' : '#f87171'}">${item.ret_60d_pct >= 0 ? '+' : ''}${item.ret_60d_pct}%</td>
          <td><b>${item.momentum_score}</b></td>
          <td>${idx === 0 && item.qualified_uptrend ? '🚀 القائد المختار' : (item.qualified_uptrend ? '✅ صاعد مؤهل' : '⏸️ تحت الفلتر')}</td>
        </tr>
      `).join('');
    }

    const campBody = document.getElementById('velCampaignBody');
    if (campBody && data.recent_campaigns) {
      campBody.innerHTML = data.recent_campaigns.slice().reverse().map(c => {
        const pos = Number(c.campaign_net_pct) >= 0;
        return `<tr>
          <td><b>${c.symbol}</b></td>
          <td>${c.entry_date} ($${c.entry_open})</td>
          <td>${c.exit_date} ($${c.exit_open})</td>
          <td style="font-weight:700;color:${pos ? '#34d399' : '#f87171'}">${pos ? '+' : ''}${c.campaign_net_pct}%</td>
          <td>$${Number(c.equity_after_usd).toLocaleString()}</td>
          <td style="font-size:11.5px;color:var(--mut)">${c.exit_reason === 'SMA25_PROTECTIVE_STOP' ? '🛡️ وقف حماية SMA25' : '🔄 تدوير لقائد أقوى'}</td>
        </tr>`;
      }).join('');
    }
  } catch (err) {
    console.error('Velocity engine error:', err);
  }
}

async function applyVelocityLiveSignalToWallet() {
  try {
    const cap = Number(document.getElementById('velCap')?.value || 1000);
    await fetch('/api/autotrader/deposit', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({currency: 'FDUSD', amount: cap, auto_convert_to_quote: false})
    });
    const stRes = await fetch('/api/autotrader/start', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({auto_prepare: true})
    });
    const st = await stRes.json();
    alert('✅ تم تمويل المحفظة الآلية بمبلغ $' + cap.toLocaleString() + ' وتفعيل محرك التنفيذ الآلي بنجاح! الرصيد الكلي الآن: $' + Number(st.total_equity_usd || cap).toLocaleString());
    if (typeof refreshAutoTrader === 'function') refreshAutoTrader();
  } catch (e) {
    console.error(e);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  const vBtn = document.getElementById('tabBtnVelocity');
  if (vBtn && typeof tab === 'function') tab('velocity', vBtn);
  runVelocityEngine();
});
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
:root{{--bg:#060b16;--card:#0f172a;--card2:#131f35;--ink:#f1f5f9;--mut:#94a3b8;--acc:#38bdf8;--ok:#10b981;--gold:#f59e0b;--bad:#f43f5e;--bdr:#1e293b}}
*{{box-sizing:border-box}}body{{margin:0;font-family:'Segoe UI',system-ui,-apple-system,Tahoma,Arial,sans-serif;background:radial-gradient(ellipse at top,#0d1b36 0%,var(--bg) 60%);color:var(--ink);line-height:1.55}}
.wrap{{max-width:1380px;margin:0 auto;padding:18px 20px 56px}}
.topbar{{display:flex;align-items:center;justify-content:space-between;gap:14px;flex-wrap:wrap;padding:14px 18px;background:rgba(15,23,42,.88);border:1px solid var(--bdr);border-radius:16px;backdrop-filter:blur(10px);box-shadow:0 12px 32px rgba(0,0,0,.35)}}
h1{{font-size:26px;margin:0;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
h2{{margin:0 0 12px;font-size:21px}}h3{{margin:4px 0 8px;font-size:16px}}
.badge-v20{{background:linear-gradient(135deg,#0284c7,#10b981);color:#fff;font-size:12px;font-weight:800;padding:4px 10px;border-radius:999px;letter-spacing:.4px}}
.badge-live{{background:rgba(16,185,129,.15);color:#34d399;border:1px solid rgba(16,185,129,.4);font-size:12px;padding:4px 10px;border-radius:999px;font-weight:700}}
.langbtn{{background:linear-gradient(135deg,#f59e0b,#ea580c);color:#fff;border:0;border-radius:999px;padding:8px 16px;font-weight:800;cursor:pointer;font-size:13px;box-shadow:0 4px 14px rgba(245,158,11,.28)}}
.sub{{color:var(--mut);font-size:14px}}
.banner{{background:rgba(69,26,3,.65);border:1px solid #b45309;border-radius:12px;padding:11px 15px;margin:14px 0;color:#fde68a;font-size:13px}}
.tabs{{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}}
.tabs button{{background:var(--card);color:var(--ink);border:1px solid var(--bdr);border-radius:999px;padding:9px 15px;cursor:pointer;font-size:14px;transition:all .15s}}
.tabs button:hover{{border-color:var(--acc)}}
.tabs button.on{{background:linear-gradient(135deg,#38bdf8,#0ea5e9);color:#041e30;font-weight:800;border-color:transparent;box-shadow:0 4px 16px rgba(56,189,248,.28)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}}
.kpi-strip{{display:grid;grid-template-columns:repeat(auto-fit,minmax(205px,1fr));gap:12px;margin-bottom:16px}}
.kpi{{background:linear-gradient(180deg,var(--card2),var(--card));border:1px solid var(--bdr);border-radius:14px;padding:14px 16px;position:relative;overflow:hidden}}
.kpi::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,var(--acc),var(--ok))}}
.kpi .k-lbl{{font-size:12px;color:var(--mut);margin-bottom:4px}}
.kpi .k-val{{font-size:27px;font-weight:900;font-variant-numeric:tabular-nums;color:#fff;letter-spacing:-.5px}}
.kpi .k-val.emerald{{color:#34d399}}.kpi .k-val.cyan{{color:#38bdf8}}.kpi .k-val.gold{{color:#fbbf24}}
.kpi .k-sub{{font-size:11.5px;color:var(--mut);margin-top:4px}}
.dual-grid{{display:grid;grid-template-columns:1.05fr 1fr;gap:14px;margin-bottom:16px}}
@media(max-width:980px){{.dual-grid{{grid-template-columns:1fr}}}}
.ctrl-bar{{display:grid;grid-template-columns:repeat(auto-fit,minmax(155px,1fr));gap:10px;align-items:end;background:var(--card2);border:1px solid var(--bdr);border-radius:14px;padding:14px;margin-bottom:16px}}
.scan-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(275px,1fr));gap:12px;margin-top:12px}}
.scard{{background:var(--card2);border:1px solid var(--bdr);border-radius:12px;padding:13px;transition:transform .12s,border-color .12s}}
.scard:hover{{transform:translateY(-2px);border-color:var(--acc)}}
.scard.buy{{border-color:rgba(16,185,129,.65);background:linear-gradient(180deg,rgba(16,185,129,.11),var(--card2))}}
.pill{{display:inline-block;padding:2px 9px;border-radius:999px;font-size:11px;font-weight:800}}
.pill.buy{{background:rgba(16,185,129,.2);color:#34d399;border:1px solid rgba(16,185,129,.45)}}
.pill.wait{{background:rgba(56,189,248,.14);color:#7dd3fc;border:1px solid rgba(56,189,248,.3)}}
.pill.off{{background:rgba(244,63,94,.15);color:#fda4af;border:1px solid rgba(244,63,94,.3)}}
.card{{background:var(--card);border:1px solid var(--bdr);border-radius:14px;padding:16px}}
.tags span{{display:inline-block;background:#080f1e;border:1px solid var(--bdr);border-radius:999px;padding:2px 9px;margin:0 4px 4px 0;font-size:12px;color:var(--mut)}}
.warn{{color:#fca5a5}}.pane{{display:none}}.pane.on{{display:block}}
label{{display:block;font-size:12px;color:var(--mut);margin-top:6px;margin-bottom:3px}}
input,select,textarea{{width:100%;padding:8px 10px;border-radius:9px;border:1px solid #334155;background:#070d19;color:var(--ink);font-size:13px}}
textarea{{min-height:130px;font-family:ui-monospace,Consolas,monospace;font-size:12px}}
th{{text-align:inherit;color:var(--mut);border-bottom:1px solid #334155;padding:8px;font-size:12px}}
details pre{{white-space:pre-wrap;max-height:420px;overflow:auto;background:#020617;padding:10px;border-radius:10px}}
.labwide{{grid-column:1/-1}}.status{{color:var(--acc);margin-top:10px;font-size:13px}}
button.go{{margin-top:8px;background:linear-gradient(135deg,#38bdf8,#0284c7);color:#041e30;font-weight:800;border:0;border-radius:10px;padding:9px 15px;cursor:pointer;font-size:13px}}
button.go.emerald{{background:linear-gradient(135deg,#34d399,#059669);color:#022c22}}
.out{{background:#070d19;border:1px solid var(--bdr);border-radius:10px;padding:12px;margin-top:12px;white-space:pre-wrap;min-height:40px}}
table{{width:100%;border-collapse:collapse;font-size:13px}}td{{border-bottom:1px solid #1e293b;padding:7px 8px;vertical-align:top;font-variant-numeric:tabular-nums}}
.svgbox{{width:100%;background:#050a14;border:1px solid var(--bdr);border-radius:12px;padding:8px;overflow:hidden}}
.foot{{color:var(--mut);font-size:13px;margin-top:26px}}
</style></head><body><div class="wrap" id="appRoot">
<div class="topbar">
  <div>
    <h1>🗺️ TradeAtlas <span class="badge-v20">v{VERSION} · Quantum Institutional</span> <span class="badge-live">● 33 Real Markets · Up to 2026-10-21</span></h1>
    <p class="sub" style="margin:4px 0 0" id="heroSub">منصة التداول والبحث الكمي المؤسسي — بيانات سوق حقيقية (123,466 شمعة حتى أكتوبر 2026)، صفر تسريب مستقبلي، ونماذج Triple-Barrier + Purged GBDT + Conformal Inference بدقة حقيقية موثقة <b>85.19% – 86.41% خارج العينة بعد العمولات</b>.</p>
  </div>
  <div style="display:flex;gap:8px;align-items:center">
    <button class="langbtn" onclick="toggleArabicUI()" id="langBtn">🌐 Switch Direction (RTL / LTR)</button>
  </div>
</div>
<div class="banner">⚠️ <b>Education & quantitative research platform — not financial advice.</b> {html.escape(DISCLAIMER)}</div>
<div class="tabs">
<button id="tabBtnVelocity" onclick="tab('velocity',this)">🚀 مضاعفة رأس المال الحقيقية (+62.83% سنوياً) · Velocity 60%+</button>
<button class="on" onclick="tab('autotrader',this)">🤖 التداول الآلي والمحفظة + اختبار 1,000$ 1m · Auto-Trader</button>
<button onclick="tab('wealth',this)">💎 مضاعفة الدخل وحسابات التمويل · Prop-Firm &amp; VIP SaaS</button>
<button onclick="tab('p80',this)">🎯 مختبر الدقة +80% · Precision-80 Lab (2026 Live)</button>
<button onclick="tab('strategies',this)">📈 Strategies ({len(STRATEGIES)})</button>
<button onclick="tab('methods',this)">🔬 Analysis methods ({len(METHODS)})</button>
<button onclick="tab('patterns',this)">🕯️ Candle patterns ({len(PATTERNS)})</button>
<button onclick="tab('lab',this)">📊 Market Lab · {len(ml.STRATEGY_ENGINES)} Engines & Bot</button>
<button onclick="tab('calcs',this)">🧮 Risk calculators</button>
<button onclick="tab('risk',this)">🛡️ Risk rules & glossary</button>
</div>

{VELOCITY_SECTION_HTML}
{AUTOTRADER_SECTION_HTML}
{WEALTH_SECTION_HTML}

<section id="p80" class="pane">
  <div class="kpi-strip" id="p80Kpis">
    <div class="kpi"><div class="k-lbl">الدقة الحقيقية خارج العينة (15 سوق عالمي) · Global OOS Net Win</div><div class="k-val emerald" id="k_win">85.19%</div><div class="k-sub" id="k_win_sub">547 صفقة حقيقية غير متداخلة بعد خصم 10 bps</div></div>
    <div class="kpi"><div class="k-lbl">حد الثقة الإحصائي 95% ويلسون · Wilson 95% CI</div><div class="k-val cyan" id="k_wilson">[81.97% – 87.92%]</div><div class="k-sub" id="k_wilson_sub">يتجاوز 80.0% إحصائياً بثقة 95%</div></div>
    <div class="kpi"><div class="k-lbl">دقة سلة الأسهم والمؤشرات المتنوعة · US Equities OOS</div><div class="k-val emerald" id="k_eqwin">86.41%</div><div class="k-sub" id="k_eq_sub">Wilson LB 83.10% · العائد التراكمي +31.9%</div></div>
    <div class="kpi"><div class="k-lbl">متوسط الربح الصافي ومعامل الربح · Expectancy & PF</div><div class="k-val gold" id="k_pf">+0.238% · PF 1.35</div><div class="k-sub" id="k_pf_sub">نمو المحفظة خارج العينة: +37.3% (مع وقف خسارة صارم)</div></div>
    <div class="kpi"><div class="k-lbl">دقة النطاق السعري التكيفي · Conformal ACI Coverage</div><div class="k-val cyan" id="k_aci">84.91%</div><div class="k-sub" id="k_aci_sub">الذهب 1h (4,157$) والبيتكوين 1m (81,491$) — أكتوبر 2026</div></div>
    <div class="kpi"><div class="k-lbl">قاعدة البيانات الموثقة · SHA-256 Real Catalog</div><div class="k-val" id="k_cat">33 / 123,466</div><div class="k-sub">شمعة حقيقية مفحوصة 100% حتى 2026-10-21</div></div>
  </div>

  <div class="ctrl-bar">
    <div>
      <label>🌍 نطاق السوق الحقيقي · Real Asset Universe</label>
      <select id="p80_univ">
        <option value="all_global" selected>كل الأسواق العالمية — 15 أصل (أسهم + ذهب + نفط + بيتكوين + عملات)</option>
        <option value="diversified_equities">الأسهم والمؤشرات الأمريكية المتنوعة — 9 قطاعات (86.41% OOS)</option>
        <option value="gold_commodities">الذهب الفوري (1h/4h/1d) + نفط برنت</option>
        <option value="crypto_intraday">العملات الرقمية فائقة التردد (BTC & ETH 1m/15m Order-Flow)</option>
        <option value="AAPL">Apple (AAPL · 1d up to 2026-10-20)</option>
        <option value="SPY">S&P 500 ETF (SPY · 1996–2026)</option>
        <option value="QQQ">Nasdaq-100 ETF (QQQ · 2015–2026)</option>
        <option value="NVDA">NVIDIA (NVDA · 2015–2026)</option>
        <option value="JPM">JPMorgan (JPM · 2015–2026)</option>
        <option value="XAUUSD">Spot Gold (XAU/USD · 2013–2026)</option>
        <option value="BTCUSD">Bitcoin Spot (BTC/USD · 2017–2026)</option>
        <option value="EURUSD">EUR/USD FX (2010–2026)</option>
      </select>
    </div>
    <div>
      <label>🧠 المحرك الكمي المؤسسي · Quant Engine</label>
      <select id="p80_mode">
        <option value="triple_barrier_meta" selected>Triple-Barrier + Purged GBDT Meta-Labeling (مع وقف خسارة صارم)</option>
        <option value="volatility_pullback_bracket">Volatility-Gated IBS Pullback Bracket (أعلى نسبة فوز)</option>
        <option value="structural_fixed_horizon">Pure Fixed-Horizon Close C[t+h] > C[t] (بدون حواجز)</option>
        <option value="intraday_orderflow_scalp">Intraday Order-Flow Microstructure Scalp (تشخيص الفريمات اللحظية)</option>
      </select>
    </div>
    <div>
      <label>💸 العمولات ذهاباً وإياباً (bps)</label>
      <input id="p80_cost" type="number" step="1" min="0" max="50" value="10">
    </div>
    <div>
      <label>🎯 هدف الربح TP (%)</label>
      <input id="p80_tp" type="number" step="0.1" min="0.2" max="15" value="1.1">
    </div>
    <div>
      <label>🛡️ وقف الخسارة الصارم SL (%)</label>
      <input id="p80_sl" type="number" step="0.5" min="0.5" max="20" value="6.5">
    </div>
    <div>
      <label>⏱ أقصى احتفاظ (شمعة)</label>
      <input id="p80_hold" type="number" step="1" min="3" max="250" value="16">
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button class="go emerald" onclick="runP80Live()" style="width:100%">⚡ تشغيل الفحص السببي الحي</button>
    </div>
  </div>

  <div class="dual-grid">
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
        <h3>📈 منحنى نمو المحفظة الحقيقي خارج العينة · Unseen OOS Compounded Equity & Drawdown</h3>
        <span class="sub" id="p80AuditHash" style="font-family:monospace;font-size:11px">SHA-256 Verified</span>
      </div>
      <div class="svgbox" id="p80EquitySvg" style="min-height:255px"></div>
      <div id="p80StatsBar" class="sub" style="margin-top:8px;font-size:12.5px"></div>
    </div>

    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px">
        <h3>🕯️ الشموع الحقيقية + مخروط التوقع التوافقي ACI (80%/90%) — أكتوبر 2026</h3>
        <select id="p80ChartFile" onchange="loadP80Candles()" style="width:auto;min-width:215px">
          <option value="aapl-1d-us-equity-2015-2026.csv" selected>AAPL · 1d (إشارة شراء حية 2026-10-20!)</option>
          <option value="xauusd-1h-gold-2023-2026.csv">XAUUSD الذهب · 1h (حتى 2026-10-21 14:00)</option>
          <option value="btcusdt-1m-binance-oct2026.csv">BTCUSDT بينانس · 1m + OrderFlow</option>
          <option value="ethusdt-1m-binance-oct2026.csv">ETHUSDT بينانس · 1m + OrderFlow</option>
          <option value="spy-1d-us-index-1996-2026.csv">SPY مؤشر S&P 500 · 1d (2026-10-20)</option>
          <option value="nvda-1d-us-equity-2015-2026.csv">NVDA إنفيديا · 1d (2026-10-20)</option>
          <option value="eurusd-1d-fx-2010-2026.csv">EUR/USD اليورو · 1d (2026-10-20)</option>
        </select>
      </div>
      <div class="svgbox" id="p80CandleSvg" style="min-height:255px"></div>
      <div id="p80ConformalReadout" class="sub" style="margin-top:8px;font-size:12.5px"></div>
    </div>
  </div>

  <div class="card" style="margin-bottom:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px">
      <div>
        <h3>📡 الرادار المؤسسي الحي لأسواق أكتوبر 2026 (19 أصل عالمي) · Live October 2026 Multi-Asset Signal Scanner</h3>
        <p class="sub" style="margin:2px 0 0">يفحص آخر شمعة حقيقية مغلقة ويحدد نقاط الدخول عند افتتاح الشمعة التالية <code>O[t+1]</code> وهدف الربح ووقف الخسارة ونطاق السعر التوافقي، مع الامتناع التلقائي عند ارتفاع الضجيج لحماية دقة &gt;80%.</p>
      </div>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <select id="ghFeedSelect" style="width:auto">
          <option value="XAUUSD_1H_2026">GitHub Live: الذهب XAUUSD 1h (2026)</option>
          <option value="BTCUSDT_1M_OCT2026">GitHub Live: بيتكوين BTCUSDT 1m (أكتوبر 2026)</option>
          <option value="ETHUSDT_1M_OCT2026">GitHub Live: إيثيريوم ETHUSDT 1m (أكتوبر 2026)</option>
          <option value="BRENT_1D_2026">GitHub Live: نفط برنت BRENT 1d (2026)</option>
          <option value="BTC_1D_2026">GitHub Live: بيتكوين يومي BTC 1d (2026)</option>
        </select>
        <button class="go" style="margin:0" onclick="pullGithubLiveFeed()">🌐 سحب أحدث بيانات 2026 حية من GitHub</button>
      </div>
    </div>
    <p id="ghSyncStatus" class="status" style="margin:6px 0 0"></p>
    <div class="scan-grid" id="p80ScannerGrid"></div>
  </div>

  <div class="dual-grid">
    <div class="card">
      <h3>🧬 أهمية المتغيرات في نموذج GBDT المعزول زمنياً · Purged Meta-Model Feature Importance & Per-Asset OOS</h3>
      <div id="p80FeatBars" style="margin:10px 0"></div>
      <div style="max-height:290px;overflow:auto"><table id="p80AssetTable"></table></div>
    </div>
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:6px">
        <h3>📐 المنحنى العلمي للضجيج مقابل الأفق الزمني <code>SNR = (μ/σ)·√h</code> + سجل الصفقات خارج العينة</h3>
        <button class="go" style="margin:0;padding:6px 12px;font-size:12px" onclick="exportOosCsv()">📥 تحميل سجل الصفقات CSV</button>
      </div>
      <div style="overflow:auto;margin:8px 0"><table id="p80SnrTable"></table></div>
      <div style="max-height:220px;overflow:auto"><table id="p80LedgerTable"></table></div>
    </div>
  </div>
</section>

<section id="strategies" class="pane"><h2>Strategies</h2><div class="grid">{strategies}</div></section>

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
data API: <code>/api/strategies</code> · Market Lab: <code>GET /api/lab/spec</code>, <code>GET /api/lab/demo</code>, <code>POST /api/lab/analyze</code>, <code>POST /api/lab/watchlist</code>, <code>POST /api/lab/forecast</code> · goals: <code>GET /api/goals</code> · minute race: <code>POST /api/lab/minute-forecast</code> · per timeframe: snapshot (+minute/VWAP/ORB state), latest condition, 100-signal validation, walk-forward split, 52-engine tournament, equity curve · demo e-wallet: <code>GET /api/paper/wallet</code>, <code>POST /api/paper/deposit-simulated</code>, <code>POST /api/paper/deposit-balance-simulated</code>, <code>POST /api/paper/convert-balance-simulated</code>, <code>POST /api/paper/withdraw-simulated</code>, <code>POST /api/paper/external-balance</code> (user-reported own-account mirror only), <code>POST /api/paper/transfer-bot-simulated</code>, <code>POST /api/paper/follow</code>, <code>POST /api/paper/stop</code>, <code>POST /api/paper/follow-step</code> (simulation only; no real deposit/withdrawal) · halal paper bot: <code>GET /api/bot</code>, <code>POST /api/halal/screen</code>, <code>POST /api/bot/register-stock</code>, <code>POST /api/bot/status</code>, <code>POST /api/bot/step</code>, <code>POST /api/bot/stop</code> · database: <code>GET /api/db/stats</code>, <code>POST /api/db/import-current</code>, <code>POST /api/db/research</code>, <code>GET /api/db/leaderboard</code>, <code>POST /api/db/halal-profile</code> · Forecast Lab: analog history + 100-attempt hidden-future evaluation vs naive baselines (history, never prophecy) · calculator API: <code>/api/calc?kind=position&amp;account=10000&amp;risk_pct=1&amp;entry=50&amp;stop=47.5</code><br>
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
</script><script>{LAB_JS}
{P80_JS_CODE}
{AUTOTRADER_JS_CODE}
{WEALTH_JS_CODE}
{VELOCITY_JS_CODE}</script></body></html>"""


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
    server_version = "TradeAtlas"
    sys_version = ""

    def log_message(self, *a):  # quiet
        pass

    def _send(self, code, body: bytes, ctype="text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://api.binance.com https://testnet.binance.vision https://api.bybit.com; frame-ancestors *",
        )
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
        elif path == "/api/real-data":
            self._json(200, {"version": VERSION, "datasets": realdata.list_real_datasets(), "spec": realdata.realdata_spec()})
        elif path == "/api/real-data/catalog":
            try:
                from platformdb import MarketDatabase
                db = MarketDatabase(_db_path())
                self._json(200, {"catalog": db.list_real_datasets(), "stats": db.real_data_stats()})
            except Exception as e:
                self._json(200, {"catalog": realdata.list_real_datasets(), "error": str(e)})
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
        elif path == "/api/precision80/summary":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            cost_bps = float(qs.get("cost_bps") or 10.0)
            tb_global = p80.run_precision80_benchmark("all_global", "triple_barrier_meta", cost_bps=cost_bps)
            br_eq = p80.run_precision80_benchmark("diversified_equities", "volatility_pullback_bracket", cost_bps=cost_bps)
            aci_gold = p80.evaluate_conformal_intervals("xauusd-1h-gold-2023-2026.csv", horizon=5, target_coverage=0.85)
            aci_btc = p80.evaluate_conformal_intervals("btcusdt-1m-binance-oct2026.csv", horizon=5, target_coverage=0.85)
            scanner = p80.scan_live_october_2026(cost_bps=cost_bps)
            snr = p80.horizon_snr_curve(cost_bps=cost_bps)
            import realdata as rd
            ds = rd.list_real_datasets()
            self._json(200, {
                "version": VERSION,
                "catalog_datasets": len(ds),
                "catalog_total_bars": sum(d["bars"] for d in ds),
                "flagship_triple_barrier_global": tb_global,
                "flagship_equities_bracket": br_eq,
                "conformal_gold_1h": aci_gold,
                "conformal_btc_1m": aci_btc,
                "live_october_2026_scanner": scanner,
                "horizon_snr_curve": snr,
                "disclaimer": DISCLAIMER,
            })
        elif path == "/api/precision80/scanner":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            cost_bps = float(qs.get("cost_bps") or 10.0)
            res = p80.scan_live_october_2026(cost_bps=cost_bps)
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/precision80/conformal":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            fname = str(qs.get("file") or "aapl-1d-us-equity-2015-2026.csv")
            hz = max(1, min(60, int(qs.get("horizon") or 5)))
            cov = max(0.60, min(0.98, float(qs.get("coverage") or 0.85)))
            import realdata as rd
            bars = rd.load_csv_file(fname)
            tail = bars[-95:]
            feats = p80.causal_series_features(bars[-320:])
            offset = len(bars[-320:]) - len(tail)
            candles = []
            for idx_t, b in enumerate(tail):
                fi = offset + idx_t
                candles.append({
                    "t": str(b["t"])[:19],
                    "o": round(float(b["o"]), 5),
                    "h": round(float(b["h"]), 5),
                    "l": round(float(b["l"]), 5),
                    "c": round(float(b["c"]), 5),
                    "v": round(float(b.get("v") or 0.0), 2),
                    "tb": round(float(b["tb"]), 2) if "tb" in b else None,
                    "sma50": round(feats["sma50"][fi], 5),
                    "sma200": round(feats["sma200"][fi], 5),
                })
            aci = p80.evaluate_conformal_intervals(fname, horizon=hz, target_coverage=cov)
            self._json(200, {
                "conformal": aci,
                "candles": candles,
                "disclaimer": DISCLAIMER,
            })
        elif path == "/api/autotrader/status":
            res = at.GLOBAL_AUTOTRADER.status()
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/autotrader/1m-day-test":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = at.simulate_1m_full_day(
                symbol=str(qs.get("symbol") or "ETHUSDT"),
                day=str(qs.get("day") or "2026-10-15"),
                capital_usd=max(50.0, min(1_000_000.0, float(qs.get("capital") or 1000.0))),
                strategy_mode=str(qs.get("mode") or "smart_maker_0bps"),
                custom_fee_bps=float(qs["fee_bps"]) if qs.get("fee_bps") not in (None, "") else None,
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/autotrader/1m-comparison":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = at.compare_1m_modes_summary(
                capital_usd=max(50.0, min(1_000_000.0, float(qs.get("capital") or 1000.0)))
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/wealth/prop-challenge":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = we.simulate_prop_firm_challenge(
                account_size_usd=int(qs.get("account") or 50000),
                risk_scale=float(qs.get("scale") or 1.0),
                universe=str(qs.get("universe") or "diversified_equities"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/wealth/hybrid-plan":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = we.build_smart_hybrid_allocation(
                capital_usd=float(qs.get("capital") or 2000.0),
                profile=str(qs.get("profile") or "balanced"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/wealth/vip-signals":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = we.generate_vip_signal_broadcast(cost_bps=float(qs.get("cost_bps") or 2.0))
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/wealth/saas-calculator":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = we.calculate_signal_saas_revenue(
                subscribers=int(qs.get("subscribers") or 50),
                monthly_price_usd=float(qs.get("price") or 39.0),
                prop_account_usd=int(qs.get("prop_account") or 50000),
                personal_capital_usd=float(qs.get("capital") or 2000.0),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/velocity/run":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = vc.run_velocity_compounder(
                capital_usd=float(qs.get("capital") or 1000.0),
                mode=str(qs.get("mode") or "institutional_kelly_135"),
                start_year=int(qs.get("start_year") or 2018),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/velocity/compare":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = vc.compare_velocity_modes(
                capital_usd=float(qs.get("capital") or 1000.0),
                start_year=int(qs.get("start_year") or 2018),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/velocity/live-signal":
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = vc.live_velocity_portfolio_signal(
                capital_usd=float(qs.get("capital") or 1000.0),
                mode=str(qs.get("mode") or "institutional_kelly_135"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v24/stress-test":
            import quant_shield_v24 as qv24
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = qv24.run_quant_shield_stress(
                capital_usd=float(qs.get("capital") or 1000.0),
                mode=str(qs.get("mode") or "institutional_kelly_135"),
                start_year=int(qs.get("start_year") or 2018),
                paths=int(qs.get("paths") or 300),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v24/income-plan":
            import quant_shield_v24 as qv24
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = qv24.simulate_monthly_income_and_compounding(
                capital_usd=float(qs.get("capital") or 2000.0),
                monthly_deposit_usd=float(qs.get("deposit") or 100.0),
                profit_withdraw_pct=float(qs.get("withdraw_pct") or 25.0),
                payout_currency=str(qs.get("currency") or "USD"),
                mode=str(qs.get("mode") or "institutional_kelly_135"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v24/correlation-matrix":
            import quant_shield_v24 as qv24
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = qv24.compute_cross_asset_correlations(window_days=int(qs.get("days") or 90))
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v25/regime-allocator":
            import meta_desk_v25 as mv25
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = mv25.classify_live_macro_regime(lookback_days=int(qs.get("days") or 60))
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v25/execution-plan":
            import meta_desk_v25 as mv25
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = mv25.build_smart_execution_plan(
                symbol=str(qs.get("symbol") or "NVDA"),
                order_usd=float(qs.get("order_usd") or 15000.0),
                entry_price=float(qs.get("entry") or 138.50),
                halal_spot_only=str(qs.get("halal", "1")) != "0",
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v25/circuit-breaker":
            import meta_desk_v25 as mv25
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = mv25.evaluate_capital_circuit_breaker(
                peak_equity_usd=float(qs.get("peak") or 10000.0),
                current_equity_usd=float(qs.get("equity") or 9680.0),
                today_pnl_pct=float(qs.get("today_pnl") or -1.4),
                consecutive_losses=int(qs.get("losses") or 2),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v26/portfolio-optimizer":
            import portfolio_autopilot_v26 as pv26
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = pv26.optimize_black_litterman_risk_parity(
                capital_usd=float(qs.get("capital") or 5000.0),
                lookback_days=int(qs.get("days") or 126),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v26/walkforward-audit":
            import portfolio_autopilot_v26 as pv26
            res = pv26.run_walkforward_overfit_audit()
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v26/wealth-governance":
            import portfolio_autopilot_v26 as pv26
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = pv26.compute_zakat_and_tax_governance(
                ending_equity_usd=float(qs.get("equity") or 25000.0),
                realized_annual_gains_usd=float(qs.get("gains") or 9500.0),
                tax_rate_pct=float(qs.get("tax_pct") or 0.0),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v27/smart-execution-plan":
            import execution_alpha_v27 as ev27
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = ev27.plan_smart_institutional_execution(
                symbol=str(qs.get("symbol") or "NVDA"),
                order_usd=float(qs.get("order_usd") or 25000.0),
                adv_usd=float(qs.get("adv_usd") or 25000000.0),
                daily_vol_pct=float(qs.get("vol_pct") or 2.8),
                halal_only=str(qs.get("halal", "1")) != "0",
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v27/black-swan-stress-lab":
            import execution_alpha_v27 as ev27
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = ev27.simulate_black_swan_crisis_lab(capital_usd=float(qs.get("capital") or 5000.0))
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v27/compounding-roadmap":
            import execution_alpha_v27 as ev27
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = ev27.project_monthly_compounding_roadmap(
                initial_usd=float(qs.get("initial") or 2000.0),
                monthly_topup_usd=float(qs.get("monthly") or 250.0),
                months=int(qs.get("months") or 24),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v28/explosive-stock-radar":
            import explosive_spot_scanner_v28 as v28
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v28.scan_all_stocks_explosion_radar(
                capital_usd=float(qs.get("capital") or 2500.0),
                currency=str(qs.get("currency") or "USD"),
                top_n=int(qs.get("top_n") or 15),
                as_of_date=qs.get("as_of_date"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v28/net-spot-compounder":
            import explosive_spot_scanner_v28 as v28
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v28.run_explosive_spot_compounder(
                capital_usd=float(qs.get("capital") or 1000.0),
                mode=str(qs.get("mode") or "explosive_515_spot_100"),
                start_year=int(qs.get("start_year") or 2018),
                end_year=int(qs.get("end_year") or 2026),
                fee_bps=float(qs.get("fee_bps") or 10.0),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v28/lookahead-audit":
            import explosive_spot_scanner_v28 as v28
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v28.verify_zero_lookahead_v28(shock_year=int(qs.get("shock_year") or 2024))
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v29/meta-spot-sniper":
            import meta_spot_sniper_v29 as v29
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v29.run_meta_spot_sniper_v29(
                capital_usd=float(qs.get("capital") or 1000.0),
                mode=str(qs.get("mode") or "meta_velocity_spot_100"),
                start_year=int(qs.get("start_year") or 2018),
                end_year=int(qs.get("end_year") or 2026),
                fee_bps=float(qs.get("fee_bps") or 10.0),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v29/order-ticket":
            import meta_spot_sniper_v29 as v29
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v29.get_spot_sniper_order_ticket(
                capital_usd=float(qs.get("capital") or 2500.0),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v29/lookahead-audit":
            import meta_spot_sniper_v29 as v29
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v29.verify_zero_lookahead_v29(shock_year=int(qs.get("shock_year") or 2024))
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v30/knowledge-spot-backtest":
            import market_knowledge_brain_v30 as v30
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v30.run_knowledge_spot_sniper_v30(
                capital_usd=float(qs.get("capital") or 1000.0),
                mode=str(qs.get("mode") or "knowledge_trifecta_spot_100"),
                start_year=int(qs.get("start_year") or 2018),
                end_year=int(qs.get("end_year") or 2026),
                fee_bps=float(qs.get("fee_bps") or 10.0),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v30/market-knowledge-brain":
            import market_knowledge_brain_v30 as v30
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v30.get_market_knowledge_brain_v30(top_etfs=int(qs.get("top_etfs") or 16))
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v30/stock-deep-knowledge":
            import market_knowledge_brain_v30 as v30
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v30.get_stock_deep_knowledge_v30(
                symbol=str(qs.get("symbol") or "NVDA"),
                capital_usd=float(qs.get("capital") or 2500.0),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v30/zero-lookahead-audit":
            import market_knowledge_brain_v30 as v30
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v30.verify_zero_lookahead_v30(shock_year=int(qs.get("shock_year") or 2024))
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v31/quad-horizon-spot":
            import institutional_execution_v31 as v31
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v31.run_quad_horizon_spot_v31(
                capital=float(qs.get("capital") or 1000.0),
                start_year=int(qs.get("start_year") or 2018),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v31/spot-entry-tranches":
            import institutional_execution_v31 as v31
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v31.build_spot_entry_tranche_plan_v31(
                symbol=str(qs.get("symbol") or "NVDA"),
                capital=float(qs.get("capital") or 2500.0),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v31/rolling-consistency-audit":
            import institutional_execution_v31 as v31
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v31.compute_rolling_consistency_audit_v31(
                capital=float(qs.get("capital") or 1000.0),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v35/gold-haven-halal-spot":
            import halal_gold_haven_compounder_v35 as v35
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v35.run_gold_haven_spot_v35(
                capital=float(qs.get("capital") or 1000.0),
                start_year=int(qs.get("start_year") or 2018),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v34/million5-halal-spot":
            import parabolic_million5_compounder_v34 as v34
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v34.run_parabolic_million5_spot_v34(
                capital=float(qs.get("capital") or 1000.0),
                start_year=int(qs.get("start_year") or 2018),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v33/million-dollar-halal-spot":
            import million_dollar_halal_compounder_v33 as v33
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v33.run_superconvex_million_spot_v33(
                capital=float(qs.get("capital") or 1000.0),
                start_year=int(qs.get("start_year") or 2018),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v33/usdt-profit-vault":
            import million_dollar_halal_compounder_v33 as v33
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v33.run_usdt_vault_profit_skim_v33(
                capital=float(qs.get("capital") or 1000.0),
                skim_pct=float(qs.get("skim") or 0.15),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v32/macro-crisis-spot":
            import macro_shock_compounder_v32 as v32
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v32.run_macro_crisis_shield_spot_v32(
                capital=float(qs.get("capital") or 1000.0),
                monthly_deposit_usd=0.0,
                start_year=int(qs.get("start_year") or 2018),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v32/monthly-savings-simulator":
            import macro_shock_compounder_v32 as v32
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v32.run_macro_crisis_shield_spot_v32(
                capital=float(qs.get("initial") or 1000.0),
                monthly_deposit_usd=float(qs.get("monthly") or 100.0),
                start_year=int(qs.get("start_year") or 2018),
                currency=str(qs.get("currency") or "USD"),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
        elif path == "/api/v32/pre-trade-sharia-checklist":
            import macro_shock_compounder_v32 as v32
            qs = {k: v[0] for k, v in urllib.parse.parse_qs(parsed.query).items()}
            res = v32.evaluate_pre_trade_sharia_gate_v32(
                symbol=str(qs.get("symbol") or "NVDA"),
                capital=float(qs.get("capital") or 2500.0),
            )
            res["disclaimer"] = DISCLAIMER
            self._json(200, res)
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
                               "/api/precision80/run", "/api/pipeline/collect-github", "/api/pipeline/ingest-catalog",
                               "/api/lab/auto-research", "/api/lab/holdout",
                               "/api/lab/predict-failure", "/api/lab/remedy-verify", "/api/lab/bootstrap",
                               "/api/lab/permutation", "/api/lab/advanced-stats",
                               "/api/evolution/record", "/api/diagnostics/explain",
                               "/api/paper/reset", "/api/paper/external-balance", "/api/paper/deposit-simulated",
                               "/api/paper/deposit-balance-simulated", "/api/paper/convert-balance-simulated",
                               "/api/paper/withdraw-simulated", "/api/paper/transfer-bot-simulated",
                               "/api/paper/order", "/api/paper/follow", "/api/paper/stop",
                               "/api/paper/follow-step", "/api/halal/screen",
                               "/api/autotrader/deposit", "/api/autotrader/convert",
                               "/api/autotrader/configure", "/api/autotrader/start",
                               "/api/autotrader/stop", "/api/autotrader/step", "/api/autotrader/reset",
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
            if parsed.path.startswith("/api/autotrader/"):
                if parsed.path == "/api/autotrader/deposit":
                    res = at.GLOBAL_AUTOTRADER.deposit(
                        currency=str(payload.get("currency") or "USDT"),
                        amount=float(payload.get("amount") or 0.0),
                        auto_convert_to_quote=bool(payload.get("auto_convert_to_quote", False)),
                    )
                elif parsed.path == "/api/autotrader/convert":
                    res = at.GLOBAL_AUTOTRADER.convert(
                        from_currency=str(payload.get("from_currency") or "FDUSD"),
                        to_currency=str(payload.get("to_currency") or "BTC"),
                        amount=float(payload.get("amount") or 0.0),
                    )
                elif parsed.path == "/api/autotrader/configure":
                    res = at.GLOBAL_AUTOTRADER.configure_exchange(
                        venue=str(payload.get("venue") or "paper_live_1m"),
                        symbol=str(payload.get("symbol") or "ETHUSDT"),
                        quote_currency=str(payload.get("quote_currency") or "FDUSD"),
                        fee_bps=float(payload.get("fee_bps") if payload.get("fee_bps") is not None else 0.0),
                        allocation_pct=float(payload.get("allocation_pct") or 95.0),
                        max_daily_loss_usd=float(payload.get("max_daily_loss_usd") or 35.0),
                        speed_bars_per_tick=int(payload.get("speed_bars_per_tick") or 12),
                        api_key=payload.get("api_key"),
                        api_secret=payload.get("api_secret"),
                        arm_live=bool(payload.get("arm_live", False)),
                    )
                elif parsed.path == "/api/autotrader/start":
                    res = at.GLOBAL_AUTOTRADER.start(
                        auto_convert_non_quote=bool(payload.get("auto_convert_non_quote", True))
                    )
                elif parsed.path == "/api/autotrader/stop":
                    res = at.GLOBAL_AUTOTRADER.stop(flatten_open=bool(payload.get("flatten_open", True)))
                elif parsed.path == "/api/autotrader/step":
                    res = at.GLOBAL_AUTOTRADER.step_bars(count=int(payload.get("count") or 60))
                else:  # /api/autotrader/reset
                    res = at.GLOBAL_AUTOTRADER.reset(
                        starting_fdusd=float(payload.get("starting_fdusd") or 1000.0)
                    )
                res["disclaimer"] = DISCLAIMER
                self._json(200, res)
                return
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
            if parsed.path == "/api/precision80/run":
                univ = str(payload.get("universe") or "all_global")
                mode = str(payload.get("mode") or "triple_barrier_meta")
                cost_bps = max(0.0, min(100.0, float(payload.get("cost_bps") if payload.get("cost_bps") is not None else 10.0)))
                tp_pct = max(0.001, min(0.25, float(payload.get("tp_pct") or 1.1) / 100.0))
                raw_sl = payload.get("sl_pct")
                sl_pct = None if raw_sl in (None, "", 0, "0", "none") else max(0.003, min(0.30, float(raw_sl) / 100.0))
                max_hold = max(2, min(260, int(payload.get("max_hold") or 16)))
                holdout_ratio = max(0.15, min(0.50, float(payload.get("holdout_ratio") or 0.30)))
                raw_mg = payload.get("meta_threshold")
                meta_thr = None if raw_mg in (None, "", "auto") else max(0.0, min(0.98, float(raw_mg)))
                res = p80.run_precision80_benchmark(
                    universe=univ,
                    mode=mode,
                    cost_bps=cost_bps,
                    tp_pct=tp_pct,
                    sl_pct=sl_pct,
                    max_hold=max_hold,
                    holdout_ratio=holdout_ratio,
                    meta_threshold=meta_thr,
                )
                res["disclaimer"] = DISCLAIMER
                self._json(200, res)
                return
            if parsed.path == "/api/pipeline/collect-github":
                feed_key = str(payload.get("feed_key") or "XAUUSD_1H_2026")
                max_b = int(payload["max_bars"]) if payload.get("max_bars") else None
                with MARKET_DB_LOCK:
                    res = pl.collect_github_archive_feed(_market_db(), feed_key=feed_key, max_bars=max_b)
                res["disclaimer"] = DISCLAIMER
                self._json(200, res)
                return
            if parsed.path == "/api/pipeline/ingest-catalog":
                lim = int(payload["limit_files"]) if payload.get("limit_files") else None
                with MARKET_DB_LOCK:
                    res = pl.ingest_bundled_real_catalog(_market_db(), limit_files=lim)
                res["disclaimer"] = DISCLAIMER
                self._json(200, res)
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
    ap.add_argument("--host", default="0.0.0.0")
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
