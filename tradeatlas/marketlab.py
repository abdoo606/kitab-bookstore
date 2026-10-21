#!/usr/bin/env python3
"""
TradeAtlas Market Lab — data, indicators, mechanical signal states and
walk-forward style historical validation.

Important boundaries
--------------------
* This module contains arithmetic and textbook indicator rules. It does not
  know the future and it is not financial advice.
* TradeAtlas bundles no licensed live market feed. Real-market work requires
  OHLCV bars that the user lawfully supplies (CSV/JSON), or a browser-polled
  feed endpoint that the user controls/has rights to use.
* "Long condition" / "short condition" means a mechanical rule fired. It is
  not a recommendation to buy or sell anything.
* Backtests enter on the NEXT bar's open after a signal closes, charge the
  configured round-trip cost, and prohibit overlapping trades. That reduces
  (but does not eliminate) look-ahead and double-counting.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import math
import random
import statistics
from typing import Iterable

TIMEFRAMES = {
    "1m": 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
    "4h": 4 * 60 * 60,
    "1d": 24 * 60 * 60,
    "1w": 7 * 24 * 60 * 60,
}

# v14 product focus. These are research targets and safety gates, not claims.
MINUTE_TIMEFRAMES = ("1m", "5m", "15m")
ACCURACY_TARGET_PCT = 80.0
MINUTE_GOAL_GATES = {
    "target_direction_accuracy_pct": ACCURACY_TARGET_PCT,
    "minimum_hidden_future_attempts_per_candidate": 1000,
    "minimum_selective_coverage_pct": 20.0,
    "wilson_95_lower_bound_for_strong_claim_pct": 80.0,
    "mean_net_after_10bps_must_be_positive": True,
    "requires_multiple_symbols_and_days": True,
    "requires_fresh_unseen_validation": True,
    "current_status": "not_reached_or_established",
}

STRATEGY_ENGINES = {
    "ma_cross": {
        "name": "EMA 20/50 cross",
        "atlas_strategy": "Moving-average cross / trend following",
        "long_rule": "EMA20 crosses above EMA50 at bar close.",
        "short_rule": "EMA20 crosses below EMA50 at bar close.",
    },
    "macd_cross": {
        "name": "MACD signal cross",
        "atlas_strategy": "MACD crossover & histogram",
        "long_rule": "MACD (12,26) crosses above its 9-period signal line.",
        "short_rule": "MACD crosses below its signal line.",
    },
    "breakout_20": {
        "name": "20-bar breakout",
        "atlas_strategy": "Breakout trading",
        "long_rule": "Close breaks above the highest high of the prior 20 bars.",
        "short_rule": "Close breaks below the lowest low of the prior 20 bars.",
    },
    "rsi_reversal": {
        "name": "RSI extreme reversal",
        "atlas_strategy": "RSI momentum & extremes",
        "long_rule": "RSI(14) crosses back above 30 after being oversold.",
        "short_rule": "RSI(14) crosses back below 70 after being overbought.",
    },
    "bollinger_mean_reversion": {
        "name": "Bollinger mean reversion",
        "atlas_strategy": "Range trading & mean reversion / Bollinger Bands",
        "long_rule": "Close returns inside the lower Bollinger Band after closing below it.",
        "short_rule": "Close returns inside the upper Bollinger Band after closing above it.",
    },
    "trend_pullback_rsi": {
        "name": "Trend pullback + RSI reset",
        "atlas_strategy": "Pullback / retest entries + RSI",
        "long_rule": "Close is above SMA50 and RSI crosses upward through 45.",
        "short_rule": "Close is below SMA50 and RSI crosses downward through 55.",
    },
    "consensus": {
        "name": "Multi-indicator consensus",
        "atlas_strategy": "Trend + MACD + RSI + moving-average confluence",
        "long_rule": "Consensus score rises to +3 or higher (EMA trend, MACD, RSI, price vs SMA50).",
        "short_rule": "Consensus score falls to -3 or lower.",
    },
    "stochastic_reversal": {
        "name": "Stochastic zone reversal",
        "atlas_strategy": "Stochastic oscillator & momentum extremes",
        "long_rule": "Stochastic %K crosses above %D while %D is in the oversold zone (<= 30).",
        "short_rule": "Stochastic %K crosses below %D while %D is in the overbought zone (>= 70).",
    },
    "adx_trend_strength": {
        "name": "ADX trend-strength onset",
        "atlas_strategy": "ADX / directional movement trend confirmation",
        "long_rule": "ADX(14) crosses above 25 while +DI is above -DI (a measurable uptrend is starting).",
        "short_rule": "ADX(14) crosses above 25 while -DI is above +DI (a measurable downtrend is starting).",
    },
    "schaff_cycle": {
        "name": "Schaff Trend Cycle turn",
        "atlas_strategy": "Schaff Trend Cycle (MACD stochastic, double-smoothed)",
        "long_rule": "STC crosses upward through 25 after a cycle washout.",
        "short_rule": "STC crosses downward through 75 after a cycle peak.",
    },
    "vortex_trend": {
        "name": "Vortex trend cross",
        "atlas_strategy": "Vortex Indicator (+VI / -VI)",
        "long_rule": "+VI(14) crosses above -VI(14).",
        "short_rule": "-VI(14) crosses above +VI(14).",
    },
    "fisher_reversal": {
        "name": "Fisher Transform reversal",
        "atlas_strategy": "Ehlers Fisher Transform",
        "long_rule": "Fisher crosses above its one-bar trigger while still below zero (turning up from the low side).",
        "short_rule": "Fisher crosses below its one-bar trigger while still above zero (turning down from the high side).",
    },
    "kst_momentum": {
        "name": "KST momentum cross",
        "atlas_strategy": "Know Sure Thing (weighted multi-horizon ROC)",
        "long_rule": "KST crosses above its 9-bar signal average.",
        "short_rule": "KST crosses below its 9-bar signal average.",
    },
    "entropy_trend": {
        "name": "Entropy-gated multiscale trend (TradeAtlas research rule)",
        "atlas_strategy": "Invented v10 Entropy-Weighted Trend: vol-normalized 3/5/10/20/60/120-bar momentum, gated by permutation entropy of smoothed log price",
        "long_rule": "Entropy-Weighted Trend crosses above +0.10 while 60-bar permutation entropy is <= 0.80 (ordered, not noise-dominated).",
        "short_rule": "Entropy-Weighted Trend crosses below -0.10 while 60-bar permutation entropy is <= 0.80.",
    },
    "cci_reversal": {
        "name": "CCI extreme reversal",
        "atlas_strategy": "Commodity Channel Index mean-reversion",
        "long_rule": "CCI(20) crosses back above -100 after an downside extreme.",
        "short_rule": "CCI(20) crosses back below +100 after an upside extreme.",
    },
    "williams_reversal": {
        "name": "Williams %R reversal",
        "atlas_strategy": "Williams %R close-location oscillator",
        "long_rule": "Williams %R(14) crosses back above -80.",
        "short_rule": "Williams %R(14) crosses back below -20.",
    },
    "parabolic_sar_trend": {
        "name": "Parabolic SAR flip",
        "atlas_strategy": "Wilder Parabolic SAR trend/stop flip",
        "long_rule": "Parabolic SAR flips from above price to below price.",
        "short_rule": "Parabolic SAR flips from below price to above price.",
    },
    "ichimoku_cloud": {
        "name": "Ichimoku cloud state",
        "atlas_strategy": "Ichimoku Tenkan/Kijun plus the cloud projected from past bars",
        "long_rule": "Ichimoku score crosses above +1/3 (price/cloud/Tenkan-Kijun confluence turns positive).",
        "short_rule": "Ichimoku score crosses below -1/3.",
    },
    "kalman_trend": {
        "name": "Kalman local-trend slope",
        "atlas_strategy": "Causal alpha-beta/Kalman-style local linear trend filter on log price",
        "long_rule": "Bounded Kalman log-price slope crosses above +0.15.",
        "short_rule": "Bounded Kalman log-price slope crosses below -0.15.",
    },
    "omni_consensus": {
        "name": "Omni direct consensus (TradeAtlas v11)",
        "atlas_strategy": "Fixed weighted fusion of multiscale trend, Kalman slope, horizon-matched trend, Parabolic SAR and an oscillator basket",
        "long_rule": "Omni direct score crosses above +0.20.",
        "short_rule": "Omni direct score crosses below -0.20.",
    },
    "hull_trend": {
        "name": "Hull moving-average trend",
        "atlas_strategy": "Alan Hull moving average (low-lag weighted MA combination)",
        "long_rule": "ATR-normalized Hull trend score crosses above +0.20.",
        "short_rule": "ATR-normalized Hull trend score crosses below -0.20.",
    },
    "supertrend_flip": {
        "name": "Supertrend flip",
        "atlas_strategy": "ATR-band Supertrend (10,3) direction flip",
        "long_rule": "Supertrend flips from above price to below price.",
        "short_rule": "Supertrend flips from below price to above price.",
    },
    "kaufman_trend": {
        "name": "Kaufman adaptive trend",
        "atlas_strategy": "Kaufman Adaptive Moving Average efficiency-ratio trend",
        "long_rule": "ATR-normalized price-plus-KAMA-slope score crosses above +0.20.",
        "short_rule": "ATR-normalized price-plus-KAMA-slope score crosses below -0.20.",
    },
    "haar_wavelet": {
        "name": "Haar wavelet multiscale trend",
        "atlas_strategy": "Haar block-average wavelet decomposition over 4/8/16/32/64 bars",
        "long_rule": "Volatility-normalized Haar trend score crosses above +0.20.",
        "short_rule": "Volatility-normalized Haar trend score crosses below -0.20.",
    },
    "aroon_trend": {
        "name": "Aroon oscillator trend",
        "atlas_strategy": "Aroon(25) recency of highs versus lows",
        "long_rule": "Aroon oscillator score crosses above +0.25.",
        "short_rule": "Aroon oscillator score crosses below -0.25.",
    },
    "tsi_momentum": {
        "name": "TSI signal momentum",
        "atlas_strategy": "True Strength Index double-smoothed momentum versus its signal",
        "long_rule": "Bounded TSI-minus-signal score crosses above +0.20.",
        "short_rule": "Bounded TSI-minus-signal score crosses below -0.20.",
    },
    "trix_momentum": {
        "name": "TRIX zero-cross momentum",
        "atlas_strategy": "Triple-smoothed EMA rate of change",
        "long_rule": "Bounded TRIX score crosses above zero.",
        "short_rule": "Bounded TRIX score crosses below zero.",
    },
    "cmo_momentum": {
        "name": "Chande Momentum trend",
        "atlas_strategy": "Chande Momentum Oscillator(14) gains-versus-losses balance",
        "long_rule": "CMO score crosses above +0.25.",
        "short_rule": "CMO score crosses below -0.25.",
    },
    "ultimate_reversal": {
        "name": "Ultimate Oscillator reversal",
        "atlas_strategy": "Larry Williams Ultimate Oscillator 7/14/28 buying pressure",
        "long_rule": "Ultimate Oscillator crosses back above 30 after an oversold reading.",
        "short_rule": "Ultimate Oscillator crosses back below 70 after an overbought reading.",
    },
    "rvi_trend": {
        "name": "Relative Vigor trend",
        "atlas_strategy": "Relative Vigor Index body/range pressure versus its signal",
        "long_rule": "Bounded RVI-minus-signal score crosses above +0.20.",
        "short_rule": "Bounded RVI-minus-signal score crosses below -0.20.",
    },
    "regression_trend": {
        "name": "Log-regression trend fusion",
        "atlas_strategy": "20/60-bar least-squares log-price slopes scaled by residual noise",
        "long_rule": "Fused regression trend score crosses above +0.20.",
        "short_rule": "Fused regression trend score crosses below -0.20.",
    },
    "donchian_trend": {
        "name": "Donchian channel state",
        "atlas_strategy": "Prior-20-bar Donchian breakout/midpoint state",
        "long_rule": "Donchian state flips from negative to positive.",
        "short_rule": "Donchian state flips from positive to negative.",
    },
    "obv_flow_trend": {
        "name": "OBV flow trend",
        "atlas_strategy": "20-bar On-Balance-Volume change normalized by real traded volume",
        "long_rule": "Bounded OBV-flow score crosses above +0.20.",
        "short_rule": "Bounded OBV-flow score crosses below -0.20.",
    },
    "coppock_trend": {
        "name": "Coppock cycle trend",
        "atlas_strategy": "Coppock Curve weighted 11/14-bar rate-of-change cycle",
        "long_rule": "Bounded Coppock score crosses above +0.20.",
        "short_rule": "Bounded Coppock score crosses below -0.20.",
    },
    "atlas_pressure_wave": {
        "name": "Atlas Pressure Wave (TradeAtlas v13)",
        "atlas_strategy": "Invented exponentially weighted candle close/body pressure scaled by ATR range and relative real volume, fused with 3/10-bar volatility-normalized momentum",
        "long_rule": "Atlas Pressure Wave crosses above +0.20.",
        "short_rule": "Atlas Pressure Wave crosses below -0.20.",
    },
    "atlas_regime_compass": {
        "name": "Atlas Regime Compass (TradeAtlas v13)",
        "atlas_strategy": "Invented smooth regime switch: ADX/permutation-entropy decide how much Hull/multiscale trend to trust versus Bollinger/RSI range reversion",
        "long_rule": "Atlas Regime Compass crosses above +0.20.",
        "short_rule": "Atlas Regime Compass crosses below -0.20.",
    },
    "atlas_phoenix_fusion": {
        "name": "Atlas Phoenix Fusion (TradeAtlas v13)",
        "atlas_strategy": "Invented family-balanced fusion of trend filters, momentum oscillators, price structure, OHLCV flow proxies and the Regime Compass; families are averaged before fusion so correlated cousins cannot outvote whole evidence types",
        "long_rule": "Atlas Phoenix Fusion crosses above +0.20.",
        "short_rule": "Atlas Phoenix Fusion crosses below -0.20.",
    },
    "minute_vwap_reversion": {
        "name": "Minute VWAP reversion (60-bar)",
        "atlas_strategy": "Intraday VWAP deviation / mean reversion on completed minute bars",
        "long_rule": "Bounded negative VWAP-deviation score crosses above +0.25 (price stretched below rolling VWAP).",
        "short_rule": "Bounded negative VWAP-deviation score crosses below -0.25 (price stretched above rolling VWAP).",
        "focus_timeframes": ["1m", "5m", "15m"],
    },
    "minute_ema_ribbon": {
        "name": "Minute EMA ribbon trend",
        "atlas_strategy": "EMA 5/13/34 ribbon alignment and volatility-normalized ribbon spread",
        "long_rule": "EMA-ribbon score crosses above +0.25.",
        "short_rule": "EMA-ribbon score crosses below -0.25.",
        "focus_timeframes": ["1m", "5m", "15m"],
    },
    "minute_rsi2_snapback": {
        "name": "Minute RSI-2 snapback",
        "atlas_strategy": "Larry Connors-style RSI(2) extreme with an SMA50 trend filter",
        "long_rule": "RSI(2) falls to 10 or below while close remains above SMA50.",
        "short_rule": "RSI(2) rises to 90 or above while close remains below SMA50.",
        "focus_timeframes": ["1m", "5m", "15m"],
    },
    "minute_orb_breakout": {
        "name": "Minute opening-range breakout",
        "atlas_strategy": "First-15-minute UTC opening range breakout (session proxy; verify the real venue session)",
        "long_rule": "Close breaks above the completed first-15-minute UTC range high.",
        "short_rule": "Close breaks below the completed first-15-minute UTC range low.",
        "focus_timeframes": ["1m", "5m", "15m"],
    },
    "minute_squeeze_breakout": {
        "name": "Minute Bollinger squeeze release",
        "atlas_strategy": "Low trailing Bollinger-bandwidth percentile followed by 5-bar volatility-normalized momentum",
        "long_rule": "Squeeze-release score crosses above +0.20.",
        "short_rule": "Squeeze-release score crosses below -0.20.",
        "focus_timeframes": ["1m", "5m", "15m"],
    },
    "minute_volume_surge": {
        "name": "Minute volume-surge pressure",
        "atlas_strategy": "Real relative-volume surge multiplied by completed-candle close-location pressure",
        "long_rule": "Volume-surge pressure score crosses above +0.35.",
        "short_rule": "Volume-surge pressure score crosses below -0.35.",
        "focus_timeframes": ["1m", "5m", "15m"],
    },
    "atlas_minute_pulse": {
        "name": "Atlas Minute Pulse (TradeAtlas v14)",
        "atlas_strategy": "Invented minute-first fusion of EMA ribbon, Atlas Pressure Wave, VWAP trend side, UTC opening-range state, volume surge and squeeze release, damped when permutation entropy says the path is noise-dominated",
        "long_rule": "Atlas Minute Pulse crosses above +0.25.",
        "short_rule": "Atlas Minute Pulse crosses below -0.25.",
        "focus_timeframes": ["1m", "5m", "15m"],
    },
}

REAL_MARKET_FEEDS = {
    "binance_public": {
        "label": "Binance public spot klines (browser-direct, no key entered here)",
        "markets": "Crypto spot pairs offered by that public endpoint (for example BTCUSDT, ETHUSDT)",
        "endpoint_shape": "GET https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1h&limit=1000",
        "intervals": ["1m", "5m", "15m", "1h", "4h", "1d", "1w"],
        "browser_direct": True,
        "credentials_in_tradeatlas": False,
        "notes": "The browser drops the still-forming last kline before analysis. Availability, regional access, CORS and terms are the venue's; this is market data only, never order routing.",
    },
    "kraken_public": {
        "label": "Kraken public OHLC (browser-direct, no key entered here)",
        "markets": "Crypto pairs offered by that public endpoint (for example XBTUSD, ETHUSD)",
        "endpoint_shape": "GET https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60",
        "intervals": ["1m", "5m", "15m", "1h", "4h", "1d", "1w"],
        "browser_direct": True,
        "credentials_in_tradeatlas": False,
        "notes": "The browser drops the still-forming last candle before analysis. Pair naming and history depth are venue-specific; market data only.",
    },
    "stooq_daily": {
        "label": "Stooq daily CSV (browser-direct)",
        "markets": "Daily symbols offered by Stooq's public CSV (for example aapl.us); availability/adjustments must be verified",
        "endpoint_shape": "GET https://stooq.com/q/d/l/?s=aapl.us&i=d",
        "intervals": ["1d", "1w via resampling"],
        "browser_direct": True,
        "credentials_in_tradeatlas": False,
        "notes": "Daily history cannot create intraday bars. Check symbol suffix, split/dividend adjustment and data rights before believing a test.",
    },
    "custom_cors": {
        "label": "Your own CORS-enabled JSON/CSV endpoint",
        "markets": "Any market for which you lawfully supply OHLCV bars",
        "endpoint_shape": "A URL returning bars[] JSON or timestamp,open,high,low,close,volume CSV",
        "intervals": ["source interval and every honest coarser resample"],
        "browser_direct": True,
        "credentials_in_tradeatlas": False,
        "notes": "TradeAtlas server never fetches the URL and never receives feed credentials; paid/key/CORS gates are not bypassed.",
    },
}

FEED_SPEC = {
    "purpose": "Bring-your-own real market data. TradeAtlas does not bundle or resell a licensed live feed.",
    "accepted_json": {
        "bars": [
            {"t": 1767225600, "o": 100.0, "h": 101.2, "l": 99.8, "c": 100.7, "v": 12345}
        ]
    },
    "accepted_csv_header": "timestamp,open,high,low,close,volume",
    "timestamp": "Unix seconds, Unix milliseconds, or ISO-8601 datetime.",
    "browser_live_feed": (
        "The web UI can poll a CORS-enabled JSON/CSV endpoint directly from the user's "
        "browser and re-analyze the newest bars. The TradeAtlas server never fetches "
        "the feed URL, avoiding server-side request forgery and credential leakage."
    ),
    "real_market_adapters": "See REAL_MARKET_FEEDS / lab_spec.real_market_feeds. Public adapters are browser-direct market-data connections, not broker/exchange order routing.",
}

DISCLAIMER = (
    "Educational/research output only — not financial advice and not a recommendation. "
    "Mechanical indicator conditions can be wrong, historical accuracy does not predict "
    "future results, and most short-term traders lose money. Verify data rights, costs, "
    "liquidity, taxes and broker rules independently; consider paper trading first."
)


def _parse_timestamp(value) -> int:
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 10_000_000_000:  # milliseconds
            number /= 1000.0
        return int(number)
    text = str(value).strip()
    if not text:
        raise ValueError("bar timestamp is empty")
    try:
        number = float(text)
        if number > 10_000_000_000:
            number /= 1000.0
        return int(number)
    except ValueError:
        pass
    normalized = text.replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(normalized)
    except ValueError:
        try:
            parsed_date = dt.date.fromisoformat(text[:10])
            parsed = dt.datetime(parsed_date.year, parsed_date.month, parsed_date.day,
                                 tzinfo=dt.timezone.utc)
        except ValueError as exc:
            raise ValueError(f"unrecognized timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp())


def _first(row: dict, names: Iterable[str], default=None):
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for name in names:
        if name in lower and lower[name] not in (None, ""):
            return lower[name]
    return default


def normalize_bars(data, *, max_bars: int = 100_000) -> list[dict]:
    """Normalize user supplied bars to sorted {t,o,h,l,c,v} dictionaries."""
    if isinstance(data, dict):
        data = data.get("bars") or data.get("data") or data.get("candles")
    if not isinstance(data, list) or not data:
        raise ValueError("bars must be a non-empty list")
    if len(data) > max_bars:
        raise ValueError(f"too many bars: maximum {max_bars} per analysis")
    by_time: dict[int, dict] = {}
    for idx, item in enumerate(data):
        if isinstance(item, dict):
            raw_t = _first(item, ("t", "time", "timestamp", "date", "datetime", "open_time"))
            raw_o = _first(item, ("o", "open"))
            raw_h = _first(item, ("h", "high"))
            raw_l = _first(item, ("l", "low"))
            raw_c = _first(item, ("c", "close"))
            raw_v = _first(item, ("v", "volume", "vol"), 0)
        elif isinstance(item, (list, tuple)) and len(item) >= 5:
            raw_t, raw_o, raw_h, raw_l, raw_c = item[:5]
            raw_v = item[5] if len(item) > 5 else 0
        else:
            raise ValueError(f"bar {idx} is not an OHLCV object/array")
        try:
            t = _parse_timestamp(raw_t)
            o, h, l, c = (float(raw_o), float(raw_h), float(raw_l), float(raw_c))
            v = float(raw_v or 0)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"bar {idx} has a non-numeric timestamp/OHLCV value") from exc
        if min(o, h, l, c) <= 0 or v < 0:
            raise ValueError(f"bar {idx} has non-positive prices or negative volume")
        if h < max(o, c) or l > min(o, c) or h < l:
            raise ValueError(f"bar {idx} is not valid OHLC data (high/low do not contain open/close)")
        by_time[t] = {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v}
    bars = [by_time[t] for t in sorted(by_time)]
    if len(bars) < 2:
        raise ValueError("at least two distinct bars are required")
    return bars


def parse_csv(text: str) -> list[dict]:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("CSV text is empty")
    sample = text.lstrip()[:4096]
    first_line = sample.splitlines()[0].lower() if sample.splitlines() else ""
    rows: list[dict] = []
    if any(word in first_line for word in ("open", "close", "timestamp", "date", "time")):
        reader = csv.DictReader(io.StringIO(text))
        rows = [dict(r) for r in reader if any(str(v).strip() for v in r.values() if v is not None)]
    else:
        reader = csv.reader(io.StringIO(text))
        for parts in reader:
            if not parts or all(not p.strip() for p in parts):
                continue
            if len(parts) < 5:
                raise ValueError("headerless CSV rows need timestamp,open,high,low,close[,volume]")
            rows.append({"t": parts[0], "o": parts[1], "h": parts[2],
                         "l": parts[3], "c": parts[4], "v": parts[5] if len(parts) > 5 else 0})
    return normalize_bars(rows)


def infer_interval_seconds(bars: list[dict]) -> int:
    if len(bars) < 2:
        raise ValueError("at least two bars are required")
    diffs = [b2["t"] - b1["t"] for b1, b2 in zip(bars, bars[1:]) if b2["t"] > b1["t"]]
    if not diffs:
        raise ValueError("bar timestamps must increase")
    return int(statistics.median(diffs))


def _bucket_start(timestamp: int, seconds: int) -> int:
    if seconds == TIMEFRAMES["1w"]:
        # 345600 = Monday 1970-01-05 00:00 UTC; align weekly buckets to Monday.
        return ((timestamp - 345600) // seconds) * seconds + 345600
    return (timestamp // seconds) * seconds


def resample_bars(bars: list[dict], timeframe_seconds: int) -> list[dict]:
    if timeframe_seconds <= 0:
        raise ValueError("timeframe_seconds must be positive")
    grouped: dict[int, dict] = {}
    for bar in bars:
        bucket = _bucket_start(int(bar["t"]), timeframe_seconds)
        if bucket not in grouped:
            grouped[bucket] = {"t": bucket, "o": float(bar["o"]), "h": float(bar["h"]),
                               "l": float(bar["l"]), "c": float(bar["c"]), "v": float(bar.get("v") or 0)}
        else:
            agg = grouped[bucket]
            agg["h"] = max(agg["h"], float(bar["h"]))
            agg["l"] = min(agg["l"], float(bar["l"]))
            agg["c"] = float(bar["c"])
            agg["v"] += float(bar.get("v") or 0)
    return [grouped[t] for t in sorted(grouped)]


def sma(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = []
    total = 0.0
    for i, value in enumerate(values):
        total += value
        if i >= period:
            total -= values[i - period]
        out.append(total / period if i >= period - 1 else None)
    return out


def ema(values: list[float], period: int) -> list[float]:
    if period <= 0 or not values:
        raise ValueError("EMA needs values and a positive period")
    alpha = 2.0 / (period + 1.0)
    out = [float(values[0])]
    for value in values[1:]:
        out.append(alpha * float(value) + (1 - alpha) * out[-1])
    return out


def rsi(closes: list[float], period: int = 14) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = [None] * len(closes)
    if len(closes) <= period:
        return out
    gains = []
    losses = []
    for prev, cur in zip(closes, closes[1:]):
        change = cur - prev
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def value(gain: float, loss: float) -> float:
        if loss == 0:
            return 100.0 if gain > 0 else 50.0
        rs = gain / loss
        return 100.0 - (100.0 / (1.0 + rs))

    out[period] = value(avg_gain, avg_loss)
    for idx in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[idx]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[idx]) / period
        out[idx + 1] = value(avg_gain, avg_loss)
    return out


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    fast_line = ema(closes, fast)
    slow_line = ema(closes, slow)
    macd_line = [f - s for f, s in zip(fast_line, slow_line)]
    signal_line = ema(macd_line, signal)
    histogram = [m - s for m, s in zip(macd_line, signal_line)]
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def bollinger(closes: list[float], period: int = 20, mult: float = 2.0) -> dict:
    middle = sma(closes, period)
    upper: list[float | None] = []
    lower: list[float | None] = []
    for i, mid in enumerate(middle):
        if mid is None:
            upper.append(None)
            lower.append(None)
            continue
        window = closes[i - period + 1:i + 1]
        # Direct float variance avoids statistics.pstdev's exact Fraction
        # path, which made the 44-engine tournament unexpectedly slow.
        deviation = math.sqrt(sum((float(x) - float(mid)) ** 2 for x in window) / period)
        upper.append(mid + mult * deviation)
        lower.append(mid - mult * deviation)
    return {"middle": middle, "upper": upper, "lower": lower}


def atr(bars: list[dict], period: int = 14) -> list[float | None]:
    if len(bars) < 2:
        return [None] * len(bars)
    true_ranges = [0.0]
    for prev, cur in zip(bars, bars[1:]):
        true_ranges.append(max(
            float(cur["h"]) - float(cur["l"]),
            abs(float(cur["h"]) - float(prev["c"])),
            abs(float(cur["l"]) - float(prev["c"])),
        ))
    # A simple rolling mean is transparent and sufficient for volatility scale.
    return sma(true_ranges, period)


def stochastic(bars: list[dict], k_period: int = 14, d_period: int = 3) -> dict:
    """Classic stochastic oscillator: %K position in the recent range, %D its SMA."""
    n = len(bars)
    k_values: list[float | None] = [None] * n
    for i in range(n):
        if i < k_period - 1:
            continue
        window = bars[i - k_period + 1:i + 1]
        highest = max(float(b["h"]) for b in window)
        lowest = min(float(b["l"]) for b in window)
        close = float(bars[i]["c"])
        k_values[i] = 50.0 if highest == lowest else 100.0 * (close - lowest) / (highest - lowest)
    d_values: list[float | None] = [None] * n
    for i in range(n):
        window = k_values[i - d_period + 1:i + 1] if i >= d_period - 1 else []
        if len(window) == d_period and all(v is not None for v in window):
            d_values[i] = sum(window) / d_period
    return {"k": k_values, "d": d_values}


def adx(bars: list[dict], period: int = 14) -> dict:
    """Wilder's ADX with +DI/-DI. Values are 0-100; None until enough history exists."""
    n = len(bars)
    plus_di: list[float | None] = [None] * n
    minus_di: list[float | None] = [None] * n
    dx: list[float | None] = [None] * n
    adx_values: list[float | None] = [None] * n
    if n < period + 2:
        return {"adx": adx_values, "plus_di": plus_di, "minus_di": minus_di}
    tr = [0.0] * n
    plus_dm = [0.0] * n
    minus_dm = [0.0] * n
    for i in range(1, n):
        high, low = float(bars[i]["h"]), float(bars[i]["l"])
        prev_high, prev_low = float(bars[i - 1]["h"]), float(bars[i - 1]["l"])
        prev_close = float(bars[i - 1]["c"])
        up = high - prev_high
        down = prev_low - low
        plus_dm[i] = up if (up > down and up > 0) else 0.0
        minus_dm[i] = down if (down > up and down > 0) else 0.0
        tr[i] = max(high - low, abs(high - prev_close), abs(low - prev_close))
    # Wilder smoothing: seed with the sum of the first `period` values (indices 1..period).
    smooth_tr = sum(tr[1:period + 1])
    smooth_plus = sum(plus_dm[1:period + 1])
    smooth_minus = sum(minus_dm[1:period + 1])
    for i in range(period, n):
        if i > period:
            smooth_tr = smooth_tr - (smooth_tr / period) + tr[i]
            smooth_plus = smooth_plus - (smooth_plus / period) + plus_dm[i]
            smooth_minus = smooth_minus - (smooth_minus / period) + minus_dm[i]
        if smooth_tr <= 0:
            continue
        p = 100.0 * smooth_plus / smooth_tr
        m = 100.0 * smooth_minus / smooth_tr
        plus_di[i], minus_di[i] = p, m
        total = p + m
        dx[i] = 100.0 * abs(p - m) / total if total > 0 else 0.0
    # ADX: first value is the mean of the first `period` DX readings, then Wilder-smoothed.
    dx_points = [(i, v) for i, v in enumerate(dx) if v is not None]
    if len(dx_points) >= period:
        first_idx = dx_points[period - 1][0]
        current = sum(v for _, v in dx_points[:period]) / period
        adx_values[first_idx] = current
        by_index = dict(dx_points)
        for i in range(first_idx + 1, n):
            if by_index.get(i) is None:
                continue
            current = (current * (period - 1) + by_index[i]) / period
            adx_values[i] = current
    return {"adx": adx_values, "plus_di": plus_di, "minus_di": minus_di}



def _rolling_sum(values: list[float], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = []
    total = 0.0
    for i, value in enumerate(values):
        total += float(value)
        if i >= period:
            total -= float(values[i - period])
        out.append(total if i >= period - 1 else None)
    return out


def _rolling_mean_nullable(values: list[float | None], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    out: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(None)
            continue
        window = values[i - period + 1:i + 1]
        out.append(sum(float(v) for v in window) / period if all(v is not None for v in window) else None)
    return out


def _ema_nullable(values: list[float | None], period: int) -> list[float | None]:
    if period <= 0:
        raise ValueError("period must be positive")
    alpha = 2.0 / (period + 1.0)
    out: list[float | None] = []
    current: float | None = None
    for value in values:
        if value is None:
            out.append(current)
            continue
        current = float(value) if current is None else alpha * float(value) + (1 - alpha) * current
        out.append(current)
    return out


def _ema_alpha_nullable(values: list[float | None], alpha: float) -> list[float | None]:
    out: list[float | None] = []
    current: float | None = None
    for value in values:
        if value is None:
            out.append(current)
            continue
        current = float(value) if current is None else alpha * float(value) + (1 - alpha) * current
        out.append(current)
    return out


def _roc_pct(closes: list[float], period: int) -> list[float | None]:
    out: list[float | None] = []
    for i, close in enumerate(closes):
        out.append((float(close) / float(closes[i - period]) - 1.0) * 100.0
                   if i >= period and closes[i - period] else None)
    return out


def aroon(bars: list[dict], period: int = 25) -> dict:
    """Aroon up/down and oscillator over the current plus prior `period` bars."""
    highs = [float(b["h"]) for b in bars]
    lows = [float(b["l"]) for b in bars]
    up: list[float | None] = [None] * len(bars)
    down: list[float | None] = [None] * len(bars)
    oscillator: list[float | None] = [None] * len(bars)
    for i in range(period, len(bars)):
        hi_window = highs[i - period:i + 1]
        lo_window = lows[i - period:i + 1]
        days_hi = period - max(j for j, v in enumerate(hi_window) if v == max(hi_window))
        days_lo = period - max(j for j, v in enumerate(lo_window) if v == min(lo_window))
        up[i] = 100.0 * (period - days_hi) / period
        down[i] = 100.0 * (period - days_lo) / period
        oscillator[i] = up[i] - down[i]
    return {"up": up, "down": down, "oscillator": oscillator}


def vortex(bars: list[dict], period: int = 14) -> dict:
    """Vortex +VI/-VI: directional movement divided by true range."""
    plus_vm = [0.0] * len(bars)
    minus_vm = [0.0] * len(bars)
    true_range = [0.0] * len(bars)
    for i in range(1, len(bars)):
        h, l = float(bars[i]["h"]), float(bars[i]["l"])
        prev = bars[i - 1]
        plus_vm[i] = abs(h - float(prev["l"]))
        minus_vm[i] = abs(l - float(prev["h"]))
        true_range[i] = max(h - l, abs(h - float(prev["c"])), abs(l - float(prev["c"])))
    plus_sum = _rolling_sum(plus_vm, period)
    minus_sum = _rolling_sum(minus_vm, period)
    tr_sum = _rolling_sum(true_range, period)
    plus = [None if i < period or not tr_sum[i] else float(plus_sum[i]) / float(tr_sum[i])
            for i in range(len(bars))]
    minus = [None if i < period or not tr_sum[i] else float(minus_sum[i]) / float(tr_sum[i])
             for i in range(len(bars))]
    return {"plus": plus, "minus": minus}


def chande_momentum(closes: list[float], period: int = 14) -> list[float | None]:
    diffs = [0.0] + [float(closes[i]) - float(closes[i - 1]) for i in range(1, len(closes))]
    gains = _rolling_sum([max(d, 0.0) for d in diffs], period)
    losses = _rolling_sum([max(-d, 0.0) for d in diffs], period)
    return [None if i < period or gains[i] is None or losses[i] is None or (gains[i] + losses[i]) <= 0
            else 100.0 * (float(gains[i]) - float(losses[i])) / (float(gains[i]) + float(losses[i]))
            for i in range(len(closes))]


def fisher_transform(bars: list[dict], period: int = 10) -> dict:
    """Ehlers Fisher Transform of median price, with a one-bar trigger."""
    medians = [(float(b["h"]) + float(b["l"])) / 2.0 for b in bars]
    fisher: list[float | None] = [None] * len(bars)
    trigger: list[float | None] = [None] * len(bars)
    x_smooth = 0.0
    prev_fisher = 0.0
    for i in range(len(bars)):
        if i < period - 1:
            continue
        window = medians[i - period + 1:i + 1]
        lo, hi = min(window), max(window)
        raw = 0.0 if hi <= lo else 2.0 * ((medians[i] - lo) / (hi - lo) - 0.5)
        x_smooth = 0.33 * raw + 0.67 * x_smooth
        x_smooth = max(-0.999, min(0.999, x_smooth))
        value = 0.5 * math.log((1.0 + x_smooth) / (1.0 - x_smooth)) + 0.5 * prev_fisher
        trigger[i] = prev_fisher if i > period - 1 else None
        fisher[i] = value
        prev_fisher = value
    return {"fisher": fisher, "trigger": trigger}


def relative_vigor_index(bars: list[dict], period: int = 10) -> dict:
    numerators = _rolling_mean_nullable([float(b["c"]) - float(b["o"]) for b in bars], period)
    denominators = _rolling_mean_nullable([float(b["h"]) - float(b["l"]) for b in bars], period)
    rvi: list[float | None] = [None if n is None or d is None else (n / d if d > 0 else 0.0)
                              for n, d in zip(numerators, denominators)]
    signal: list[float | None] = [None] * len(bars)
    for i in range(3, len(bars)):
        window = rvi[i - 3:i + 1]
        if all(v is not None for v in window):
            signal[i] = (float(window[3]) + 2.0 * float(window[2]) + 2.0 * float(window[1]) + float(window[0])) / 6.0
    return {"rvi": rvi, "signal": signal}


def chaikin_money_flow(bars: list[dict], period: int = 20) -> list[float | None]:
    money_flow_volume = []
    volumes = []
    for b in bars:
        h, l, c, v = float(b["h"]), float(b["l"]), float(b["c"]), float(b.get("v") or 0.0)
        multiplier = 0.0 if h <= l else ((c - l) - (h - c)) / (h - l)
        money_flow_volume.append(multiplier * v)
        volumes.append(v)
    flow = _rolling_sum(money_flow_volume, period)
    total = _rolling_sum(volumes, period)
    return [None if i < period - 1 else (0.0 if not total[i] else float(flow[i]) / float(total[i]))
            for i in range(len(bars))]


def money_flow_index(bars: list[dict], period: int = 14) -> list[float | None]:
    typical = [(float(b["h"]) + float(b["l"]) + float(b["c"])) / 3.0 for b in bars]
    positive = [0.0] * len(bars)
    negative = [0.0] * len(bars)
    for i in range(1, len(bars)):
        flow = typical[i] * float(bars[i].get("v") or 0.0)
        if typical[i] > typical[i - 1]:
            positive[i] = flow
        elif typical[i] < typical[i - 1]:
            negative[i] = flow
    pos = _rolling_sum(positive, period)
    neg = _rolling_sum(negative, period)
    out: list[float | None] = []
    for i in range(len(bars)):
        if i < period or pos[i] is None or neg[i] is None:
            out.append(None)
        elif float(pos[i]) <= 0 and float(neg[i]) <= 0:
            out.append(50.0)
        elif float(neg[i]) <= 0:
            out.append(100.0)
        else:
            out.append(100.0 - 100.0 / (1.0 + float(pos[i]) / float(neg[i])))
    return out


def _stochastic_of_values(values: list[float | None], period: int = 10) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(None)
            continue
        window = values[i - period + 1:i + 1]
        if any(v is None for v in window):
            out.append(None)
            continue
        nums = [float(v) for v in window]
        lo, hi = min(nums), max(nums)
        out.append(50.0 if hi <= lo else 100.0 * (nums[-1] - lo) / (hi - lo))
    return out


def schaff_trend_cycle(closes: list[float], fast: int = 23, slow: int = 50,
                       cycle: int = 10) -> list[float | None]:
    """Schaff Trend Cycle: stochastic of MACD, smoothed twice."""
    fast_line = ema(closes, fast)
    slow_line = ema(closes, slow)
    macd_line: list[float | None] = [f - s for f, s in zip(fast_line, slow_line)]
    first = _ema_alpha_nullable(_stochastic_of_values(macd_line, cycle), 0.5)
    return _ema_alpha_nullable(_stochastic_of_values(first, cycle), 0.5)


def kst(closes: list[float]) -> dict:
    """Know Sure Thing: four ROC horizons, smoothed and weighted 1/2/3/4."""
    components = []
    for roc_period, smooth_period, weight in ((10, 10, 1.0), (15, 10, 2.0), (20, 10, 3.0), (30, 15, 4.0)):
        components.append((_rolling_mean_nullable(_roc_pct(closes, roc_period), smooth_period), weight))
    values: list[float | None] = []
    for i in range(len(closes)):
        parts = [arr[i] for arr, _ in components]
        values.append(None if any(v is None for v in parts)
                      else sum(float(v) * w for v, (_, w) in zip(parts, components)))
    return {"kst": values, "signal": _rolling_mean_nullable(values, 9)}


def coppock(closes: list[float]) -> list[float | None]:
    roc14 = _roc_pct(closes, 14)
    roc11 = _roc_pct(closes, 11)
    base: list[float | None] = [None if a is None or b is None else a + b for a, b in zip(roc14, roc11)]
    out: list[float | None] = []
    weights = list(range(1, 11))
    for i in range(len(closes)):
        window = base[i - 9:i + 1] if i >= 9 else []
        out.append(None if len(window) != 10 or any(v is None for v in window)
                   else sum(float(v) * w for v, w in zip(window, weights)) / sum(weights))
    return out


def elder_force_index(bars: list[dict], period: int = 13) -> list[float | None]:
    raw: list[float | None] = [None]
    for i in range(1, len(bars)):
        raw.append((float(bars[i]["c"]) - float(bars[i - 1]["c"])) * float(bars[i].get("v") or 0.0))
    return _ema_nullable(raw, period)


def ulcer_index(closes: list[float], period: int = 14) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(closes)):
        if i < period - 1:
            out.append(None)
            continue
        window = [float(x) for x in closes[i - period + 1:i + 1]]
        peak = max(window)
        out.append((sum(((peak - x) / peak * 100.0) ** 2 for x in window) / period) ** 0.5 if peak > 0 else 0.0)
    return out


def ehlers_super_smoother(values: list[float], period: int = 10) -> list[float]:
    """Two-pole Ehlers SuperSmoother low-pass filter."""
    if not values:
        return []
    a1 = math.exp(-1.414 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(1.414 * math.pi / period)
    c2 = b1
    c3 = -(a1 ** 2)
    c1 = 1.0 - c2 - c3
    out = [float(values[0])]
    if len(values) > 1:
        out.append(float(values[1]))
    for i in range(2, len(values)):
        out.append(c1 * (float(values[i]) + float(values[i - 1])) / 2.0 + c2 * out[-1] + c3 * out[-2])
    return out


def permutation_entropy_series(values: list[float], *, window: int = 60, order: int = 4,
                               smooth_period: int = 5) -> list[float | None]:
    """Normalized permutation entropy of EMA-smoothed log values.

    The ordinal-pattern distribution is deliberately computed on a smoothed
    level series: raw one-bar returns are so pattern-uniform that the entropy
    sits near one and says almost nothing. Low entropy means a few ordered
    shapes dominate; high entropy means shape noise dominates.
    """
    if not values:
        return []
    safe = [math.log(max(float(v), 1e-12)) if float(v) > 0 else math.log(1e-12) for v in values]
    smoothed = ema(safe, smooth_period)
    out: list[float | None] = [None] * len(values)
    denominator = math.log(math.factorial(order))
    # Compute each ordinal pattern once, then slide the pattern-count window.
    # This preserves the original distribution while avoiding O(n*window)
    # re-sorting in every snapshot/tournament.
    patterns: list[tuple[int, ...]] = []
    for start in range(0, len(smoothed) - order + 1):
        chunk = smoothed[start:start + order]
        patterns.append(tuple(sorted(range(order), key=lambda k: (chunk[k], k))))
    counts: dict[tuple[int, ...], int] = {}
    total = window - order + 1
    if total <= 0:
        return out
    for end in range(window - 1, len(values)):
        newest_start = end - order + 1
        if end == window - 1:
            for pattern in patterns[:newest_start + 1]:
                counts[pattern] = counts.get(pattern, 0) + 1
        else:
            if 0 <= newest_start < len(patterns):
                pattern = patterns[newest_start]
                counts[pattern] = counts.get(pattern, 0) + 1
            oldest_start = end - window
            if 0 <= oldest_start < len(patterns):
                pattern = patterns[oldest_start]
                remaining = counts.get(pattern, 0) - 1
                if remaining > 0:
                    counts[pattern] = remaining
                else:
                    counts.pop(pattern, None)
        entropy = -sum((count / total) * math.log(count / total) for count in counts.values())
        out[end] = entropy / denominator if denominator > 0 else 0.0
    return out


def permutation_entropy_at(values: list[float], idx: int | None = None, *, window: int = 60,
                           order: int = 4, smooth_period: int = 5) -> float | None:
    """One origin-time permutation-entropy value (see permutation_entropy_series)."""
    if not values:
        return None
    end = len(values) - 1 if idx is None else int(idx)
    if end < window - 1 or end >= len(values):
        return None
    safe = [math.log(max(float(v), 1e-12)) if float(v) > 0 else math.log(1e-12)
            for v in values[:end + 1]]
    smoothed = ema(safe, smooth_period)
    segment = smoothed[end - window + 1:end + 1]
    counts: dict[tuple[int, ...], int] = {}
    total = 0
    for start in range(0, len(segment) - order + 1):
        chunk = segment[start:start + order]
        pattern = tuple(sorted(range(order), key=lambda k: (chunk[k], k)))
        counts[pattern] = counts.get(pattern, 0) + 1
        total += 1
    if not total:
        return None
    entropy = -sum((count / total) * math.log(count / total) for count in counts.values())
    return entropy / math.log(math.factorial(order))


def multiscale_trend_scores(closes: list[float], *, returns_pct: list[float] | None = None,
                            vol10: list[float | None] | None = None) -> list[float | None]:
    """Volatility-normalized time-series momentum across six horizons.

    Each horizon contributes tanh(return / (10-bar vol * sqrt(horizon))).
    This is deliberately not another nearest-neighbour costume: it is the
    classic multi-horizon trend question, with fast and slow evidence forced
    onto one bounded scale before they are averaged.
    """
    if returns_pct is None:
        returns_pct = [0.0] + [(float(closes[i]) / float(closes[i - 1]) - 1.0) * 100.0
                               if closes[i - 1] else 0.0 for i in range(1, len(closes))]
    if vol10 is None:
        vol10 = _rolling_vol10([float(x) for x in returns_pct])
    windows = (3, 5, 10, 20, 60, 120)
    out: list[float | None] = []
    for i, close in enumerate(closes):
        sd = vol10[i] if i < len(vol10) else None
        if i < 20 or sd is None or float(sd) <= 0 or not close:
            out.append(None)
            continue
        parts = []
        for w in windows:
            if i - w >= 0 and closes[i - w]:
                ret = (float(close) / float(closes[i - w]) - 1.0) * 100.0
                parts.append(math.tanh(ret / (float(sd) * math.sqrt(w))))
        out.append(sum(parts) / len(parts) if len(parts) >= 4 else None)
    return out


def entropy_weighted_trend_scores(bars: list[dict]) -> dict:
    closes = [float(b["c"]) for b in bars]
    trends = multiscale_trend_scores(closes)
    entropy = permutation_entropy_series(closes)
    scores: list[float | None] = [None if t is None or e is None else float(t) * (1.0 - float(e))
                                 for t, e in zip(trends, entropy)]
    return {"score": scores, "trend": trends, "entropy": entropy}

def commodity_channel_index(bars: list[dict], period: int = 20) -> list[float | None]:
    """Commodity Channel Index from typical price."""
    typical = [(float(b["h"]) + float(b["l"]) + float(b["c"])) / 3.0 for b in bars]
    means = sma(typical, period)
    out: list[float | None] = []
    for i, value in enumerate(typical):
        if i < period - 1 or means[i] is None:
            out.append(None); continue
        mean = float(means[i])
        mad = sum(abs(x - mean) for x in typical[i - period + 1:i + 1]) / period
        out.append(0.0 if mad <= 0 else (value - mean) / (0.015 * mad))
    return out


def williams_r(bars: list[dict], period: int = 14) -> list[float | None]:
    """Williams %R: close position inside the trailing high-low range."""
    out: list[float | None] = []
    for i, bar in enumerate(bars):
        if i < period - 1:
            out.append(None); continue
        window = bars[i - period + 1:i + 1]
        high = max(float(b["h"]) for b in window); low = min(float(b["l"]) for b in window)
        out.append(-50.0 if high <= low else -100.0 * (high - float(bar["c"])) / (high - low))
    return out


def true_strength_index(closes: list[float], long_period: int = 25,
                        short_period: int = 13, signal_period: int = 7) -> dict:
    """True Strength Index: double-smoothed momentum over double-smoothed abs momentum."""
    momentum = [0.0] + [float(closes[i]) - float(closes[i - 1]) for i in range(1, len(closes))]
    smoothed = ema(ema(momentum, long_period), short_period)
    absolute = ema(ema([abs(x) for x in momentum], long_period), short_period)
    values: list[float | None] = [None if b in (None, 0) else 100.0 * float(a) / float(b)
                                  for a, b in zip(smoothed, absolute)]
    signal = ema([0.0 if v is None else float(v) for v in values], signal_period)
    return {"tsi": values, "signal": signal}


def trix(closes: list[float], period: int = 15) -> list[float | None]:
    """TRIX: rate of change of a triple-smoothed EMA, in basis-point-like units."""
    triple = ema(ema(ema([float(c) for c in closes], period), period), period)
    out: list[float | None] = [None]
    for i in range(1, len(triple)):
        out.append(None if not triple[i - 1] else (float(triple[i]) / float(triple[i - 1]) - 1.0) * 10_000.0)
    return out


def ultimate_oscillator(bars: list[dict]) -> list[float | None]:
    """Larry Williams Ultimate Oscillator over 7/14/28-bar buying pressure."""
    buying_pressure: list[float] = []
    true_ranges: list[float] = []
    out: list[float | None] = []
    for i, bar in enumerate(bars):
        high, low, close = float(bar["h"]), float(bar["l"]), float(bar["c"])
        if i == 0:
            buying_pressure.append(0.0); true_ranges.append(high - low); out.append(None); continue
        prev_close = float(bars[i - 1]["c"])
        buying_pressure.append(close - min(low, prev_close))
        true_ranges.append(max(high, prev_close) - min(low, prev_close))
        if i < 28:
            out.append(None); continue
        weighted = 0.0
        for period, weight in ((7, 4.0), (14, 2.0), (28, 1.0)):
            tr_sum = sum(true_ranges[i - period + 1:i + 1])
            weighted += weight * (sum(buying_pressure[i - period + 1:i + 1]) / tr_sum if tr_sum else 0.5)
        out.append(100.0 * weighted / 7.0)
    return out


def parabolic_sar(bars: list[dict], step: float = 0.02, maximum: float = 0.20) -> dict:
    """Wilder Parabolic SAR and its causal trend state (+1 below price / -1 above)."""
    n = len(bars)
    sar: list[float | None] = [None] * n
    trend: list[int] = [1] * n
    if n < 2:
        return {"sar": sar, "trend": trend}
    up = True
    value = float(bars[0]["l"]); extreme = float(bars[0]["h"]); acceleration = float(step)
    sar[0] = value
    for i in range(1, n):
        high, low = float(bars[i]["h"]), float(bars[i]["l"])
        value = value + acceleration * (extreme - value)
        if up:
            prior_low = float(bars[i - 1]["l"])
            prior2_low = float(bars[i - 2]["l"]) if i >= 2 else prior_low
            value = min(value, prior_low, prior2_low)
            if low < value:
                up = False; value = extreme; extreme = low; acceleration = float(step)
            elif high > extreme:
                extreme = high; acceleration = min(float(maximum), acceleration + float(step))
        else:
            prior_high = float(bars[i - 1]["h"])
            prior2_high = float(bars[i - 2]["h"]) if i >= 2 else prior_high
            value = max(value, prior_high, prior2_high)
            if high > value:
                up = True; value = extreme; extreme = high; acceleration = float(step)
            elif low < extreme:
                extreme = low; acceleration = min(float(maximum), acceleration + float(step))
        sar[i] = value; trend[i] = 1 if up else -1
    return {"sar": sar, "trend": trend}


def ichimoku_scores(bars: list[dict]) -> list[float | None]:
    """Bounded Ichimoku state using the cloud that past bars projected to today."""
    closes = [float(b["c"]) for b in bars]

    def midpoint(idx: int, period: int) -> float | None:
        if idx < period - 1:
            return None
        window = bars[idx - period + 1:idx + 1]
        return (max(float(b["h"]) for b in window) + min(float(b["l"]) for b in window)) / 2.0

    out: list[float | None] = []
    for i in range(len(bars)):
        tenkan = midpoint(i, 9); kijun = midpoint(i, 26)
        source = i - 26
        span_a = span_b = None
        if source >= 51:
            a_tenkan, a_kijun = midpoint(source, 9), midpoint(source, 26)
            if a_tenkan is not None and a_kijun is not None:
                span_a = (a_tenkan + a_kijun) / 2.0
            span_b = midpoint(source, 52)
        if tenkan is None or kijun is None or span_a is None or span_b is None:
            out.append(None); continue
        cloud = 1 if closes[i] > max(span_a, span_b) else -1 if closes[i] < min(span_a, span_b) else 0
        cross = 1 if tenkan > kijun else -1 if tenkan < kijun else 0
        base = 1 if closes[i] > kijun else -1 if closes[i] < kijun else 0
        out.append((cloud + cross + base) / 3.0)
    return out


def on_balance_volume_slope(bars: list[dict], period: int = 20) -> list[float | None]:
    """OBV change normalized by trailing real volume; None when volume is absent."""
    obv = [0.0]
    for i in range(1, len(bars)):
        direction = 1 if bars[i]["c"] > bars[i - 1]["c"] else -1 if bars[i]["c"] < bars[i - 1]["c"] else 0
        obv.append(obv[-1] + direction * float(bars[i].get("v") or 0.0))
    out: list[float | None] = []
    for i in range(len(bars)):
        if i < period:
            out.append(None); continue
        scale = sum(float(bars[j].get("v") or 0.0) for j in range(i - period + 1, i + 1))
        out.append(None if scale <= 0 else (obv[i] - obv[i - period]) / scale)
    return out


def log_regression_trend_scores(closes: list[float], period: int = 60) -> list[float | None]:
    """Least-squares log-price slope scaled by residual noise (a bounded t-like score)."""
    logs = [math.log(max(float(c), 1e-12)) for c in closes]
    xs = list(range(period)); mean_x = sum(xs) / period
    denominator = sum((x - mean_x) ** 2 for x in xs) or 1.0
    out: list[float | None] = []
    for i in range(len(closes)):
        if i < period - 1:
            out.append(None); continue
        ys = logs[i - period + 1:i + 1]; mean_y = sum(ys) / period
        slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
        residual_sd = (sum((y - (mean_y + slope * (x - mean_x))) ** 2 for x, y in zip(xs, ys)) / period) ** 0.5
        out.append(math.tanh((slope * period) / ((residual_sd or 1e-9) * math.sqrt(period))))
    return out


def kalman_trend_scores(closes: list[float], *, level_gain: float = 0.35,
                        slope_gain: float = 0.08, scale: float = 100.0) -> list[float | None]:
    """Causal alpha-beta (Kalman-style) local linear trend of log price.

    The state is updated only with the current and past closes. The score is
    ``tanh(100 * estimated log-price slope per bar)`` and therefore bounded.
    """
    if not closes:
        return []
    level = math.log(max(float(closes[0]), 1e-12)); slope = 0.0
    out: list[float | None] = []
    for close in closes:
        observed = math.log(max(float(close), 1e-12))
        predicted = level + slope
        error = observed - predicted
        level = predicted + float(level_gain) * error
        slope = slope + float(slope_gain) * error
        out.append(math.tanh(float(scale) * slope))
    return out


def horizon_matched_trend_scores(closes: list[float], horizon: int, *,
                                 returns_pct: list[float] | None = None,
                                 vol10: list[float | None] | None = None) -> list[float | None]:
    """Vol-normalized trend whose lookbacks scale with the forecast horizon."""
    h = max(1, int(horizon))
    windows = tuple(sorted({max(2, h), max(2, 2 * h), max(2, 4 * h), max(2, 12 * h), max(2, 24 * h)}))
    if returns_pct is None:
        returns_pct = [0.0] + [(float(closes[i]) / float(closes[i - 1]) - 1.0) * 100.0
                               if closes[i - 1] else 0.0 for i in range(1, len(closes))]
    if vol10 is None:
        vol10 = _rolling_vol10([float(x) for x in returns_pct])
    out: list[float | None] = []
    for i, close in enumerate(closes):
        sd = vol10[i] if i < len(vol10) else None
        parts = []
        if sd is not None and float(sd) > 0 and close:
            for w in windows:
                if i - w >= 0 and closes[i - w]:
                    ret = (float(close) / float(closes[i - w]) - 1.0) * 100.0
                    parts.append(math.tanh(ret / (float(sd) * math.sqrt(w))))
        out.append(sum(parts) / len(parts) if len(parts) >= max(3, len(windows) - 1) else None)
    return out


def omni_oscillator_scores(bars: list[dict]) -> list[float | None]:
    """Bounded average of a classic/modern oscillator basket (origin-time only)."""
    closes = [float(b["c"]) for b in bars]
    cci_values = commodity_channel_index(bars)
    williams_values = williams_r(bars)
    tsi_data = true_strength_index(closes)
    trix_values = trix(closes)
    ultimate_values = ultimate_oscillator(bars)
    cmo_values = chande_momentum(closes)
    fisher_values = fisher_transform(bars)["fisher"]
    stc_values = schaff_trend_cycle(closes)
    out: list[float | None] = []
    for i in range(len(bars)):
        parts: list[float] = []
        if cci_values[i] is not None: parts.append(math.tanh(float(cci_values[i]) / 100.0))
        if williams_values[i] is not None: parts.append((float(williams_values[i]) + 50.0) / 50.0)
        if tsi_data["tsi"][i] is not None and tsi_data["signal"][i] is not None:
            parts.append(math.tanh((float(tsi_data["tsi"][i]) - float(tsi_data["signal"][i])) / 10.0))
        if trix_values[i] is not None: parts.append(1.0 if float(trix_values[i]) > 0 else -1.0 if float(trix_values[i]) < 0 else 0.0)
        if ultimate_values[i] is not None: parts.append((float(ultimate_values[i]) - 50.0) / 50.0)
        if cmo_values[i] is not None: parts.append(float(cmo_values[i]) / 100.0)
        if fisher_values[i] is not None: parts.append(math.tanh(float(fisher_values[i]) / 2.0))
        if stc_values[i] is not None: parts.append((float(stc_values[i]) - 50.0) / 50.0)
        out.append(sum(parts) / len(parts) if len(parts) >= 4 else None)
    return out


def omni_direct_scores(bars: list[dict], *, horizon: int = 5) -> list[float | None]:
    """TradeAtlas v11 fixed direct fusion (not fitted per symbol).

    Weighted available components: multiscale trend 1.2, Kalman slope 0.9,
    horizon-matched trend 0.7, Parabolic SAR state 0.5, oscillator basket 0.5.
    The weights are part of the published rule; the hidden-future race decides
    whether they helped on a supplied sample.
    """
    closes = [float(b["c"]) for b in bars]
    multiscale = multiscale_trend_scores(closes)
    kalman = kalman_trend_scores(closes)
    matched = horizon_matched_trend_scores(closes, horizon)
    sar_trend = parabolic_sar(bars)["trend"]
    oscillator = omni_oscillator_scores(bars)
    out: list[float | None] = []
    for i in range(len(bars)):
        weighted: list[tuple[float, float]] = []
        if multiscale[i] is not None: weighted.append((1.2, float(multiscale[i])))
        if kalman[i] is not None: weighted.append((0.9, float(kalman[i])))
        if matched[i] is not None: weighted.append((0.7, float(matched[i])))
        weighted.append((0.5, float(sar_trend[i])))
        if oscillator[i] is not None: weighted.append((0.5, float(oscillator[i])))
        out.append(sum(w * x for w, x in weighted) / sum(w for w, _ in weighted)
                   if len(weighted) >= 4 else None)
    return out



def _wma_nullable(values: list[float | None], period: int) -> list[float | None]:
    weights = list(range(1, int(period) + 1)); denominator = float(sum(weights)) or 1.0
    out: list[float | None] = []
    for i in range(len(values)):
        if i < period - 1:
            out.append(None); continue
        window = values[i - period + 1:i + 1]
        out.append(None if any(v is None for v in window)
                   else sum(float(v) * w for v, w in zip(window, weights)) / denominator)
    return out


def hull_moving_average(closes: list[float], period: int = 20) -> list[float | None]:
    """Alan Hull MA: WMA(sqrt(period)) of 2*WMA(period/2)-WMA(period)."""
    values: list[float | None] = [float(c) for c in closes]
    half = _wma_nullable(values, max(2, int(period) // 2))
    full = _wma_nullable(values, int(period))
    raw: list[float | None] = [None if a is None or b is None else 2.0 * float(a) - float(b)
                               for a, b in zip(half, full)]
    return _wma_nullable(raw, max(2, int(math.sqrt(int(period)))))


def hull_trend_scores(bars: list[dict], period: int = 20) -> list[float | None]:
    """Bounded Hull state: price distance plus 3-bar Hull slope, ATR-scaled."""
    closes = [float(b["c"]) for b in bars]
    hma = hull_moving_average(closes, period)
    atr_values = atr(bars, 14)
    out: list[float | None] = []
    for i, close in enumerate(closes):
        if hma[i] is None or i < 3 or hma[i - 3] is None:
            out.append(None); continue
        scale = float(atr_values[i]) if atr_values[i] not in (None, 0) else max(close * 0.01, 1e-9)
        out.append(math.tanh(((close - float(hma[i])) + (float(hma[i]) - float(hma[i - 3]))) / scale))
    return out


def supertrend(bars: list[dict], period: int = 10, multiplier: float = 3.0) -> dict:
    """Classic ATR Supertrend with causal final-band ratcheting."""
    atr_values = atr(bars, period)
    final_upper: list[float | None] = [None] * len(bars)
    final_lower: list[float | None] = [None] * len(bars)
    values: list[float | None] = [None] * len(bars)
    trend: list[int] = [1] * len(bars)
    for i, bar in enumerate(bars):
        if atr_values[i] is None:
            continue
        midpoint = (float(bar["h"]) + float(bar["l"])) / 2.0
        upper = midpoint + float(multiplier) * float(atr_values[i])
        lower = midpoint - float(multiplier) * float(atr_values[i])
        if i == 0 or final_upper[i - 1] is None or final_lower[i - 1] is None:
            final_upper[i] = upper; final_lower[i] = lower; trend[i] = 1; values[i] = lower; continue
        prev_close = float(bars[i - 1]["c"])
        final_upper[i] = upper if (upper < float(final_upper[i - 1]) or prev_close > float(final_upper[i - 1])) else float(final_upper[i - 1])
        final_lower[i] = lower if (lower > float(final_lower[i - 1]) or prev_close < float(final_lower[i - 1])) else float(final_lower[i - 1])
        previous = trend[i - 1]
        close = float(bar["c"])
        if previous < 0 and close > float(final_upper[i]):
            trend[i] = 1
        elif previous > 0 and close < float(final_lower[i]):
            trend[i] = -1
        else:
            trend[i] = previous
        values[i] = float(final_lower[i]) if trend[i] > 0 else float(final_upper[i])
    return {"supertrend": values, "trend": trend, "upper": final_upper, "lower": final_lower}


def kaufman_adaptive_moving_average(closes: list[float], er_period: int = 10,
                                    fast: int = 2, slow: int = 30) -> list[float | None]:
    """Kaufman AMA driven by the efficiency ratio."""
    out: list[float | None] = [None] * len(closes)
    fast_sc = 2.0 / (float(fast) + 1.0); slow_sc = 2.0 / (float(slow) + 1.0)
    ama: float | None = None
    for i, close in enumerate(closes):
        if i < er_period:
            continue
        change = abs(float(close) - float(closes[i - er_period]))
        volatility = sum(abs(float(closes[j]) - float(closes[j - 1]))
                         for j in range(i - er_period + 1, i + 1))
        efficiency = change / volatility if volatility > 0 else 0.0
        smoothing = (efficiency * (fast_sc - slow_sc) + slow_sc) ** 2
        ama = float(close) if ama is None else ama + smoothing * (float(close) - ama)
        out[i] = ama
    return out


def kaufman_trend_scores(bars: list[dict]) -> list[float | None]:
    closes = [float(b["c"]) for b in bars]
    ama = kaufman_adaptive_moving_average(closes)
    atr_values = atr(bars, 14)
    out: list[float | None] = []
    for i, close in enumerate(closes):
        if ama[i] is None or i < 3 or ama[i - 3] is None:
            out.append(None); continue
        scale = float(atr_values[i]) if atr_values[i] not in (None, 0) else max(close * 0.01, 1e-9)
        out.append(math.tanh(((close - float(ama[i])) + (float(ama[i]) - float(ama[i - 3]))) / scale))
    return out


def haar_wavelet_trend_scores(closes: list[float], *, returns_pct=None, vol10=None) -> list[float | None]:
    """Haar block-average trend at 4/8/16/32/64-bar scales."""
    logs = [math.log(max(float(c), 1e-12)) for c in closes]
    if returns_pct is None:
        returns_pct = [0.0] + [(float(closes[i]) / float(closes[i - 1]) - 1.0) * 100.0
                               if closes[i - 1] else 0.0 for i in range(1, len(closes))]
    if vol10 is None:
        vol10 = _rolling_vol10([float(x) for x in returns_pct])
    out: list[float | None] = []
    for i in range(len(closes)):
        sd = vol10[i] if i < len(vol10) else None
        parts: list[float] = []
        if sd is not None and float(sd) > 0:
            for scale in (4, 8, 16, 32, 64):
                if i >= 2 * scale - 1:
                    recent = sum(logs[i - scale + 1:i + 1]) / scale
                    prior = sum(logs[i - 2 * scale + 1:i - scale + 1]) / scale
                    parts.append(math.tanh(((recent - prior) * 100.0) / (float(sd) * math.sqrt(scale))))
        out.append(sum(parts) / len(parts) if len(parts) >= 3 else None)
    return out


def donchian_state(bars: list[dict], period: int = 20) -> list[int | None]:
    """Breakout/midpoint Donchian state from the prior channel only."""
    out: list[int | None] = []
    for i, bar in enumerate(bars):
        if i < period:
            out.append(None); continue
        window = bars[i - period:i]
        high = max(float(b["h"]) for b in window); low = min(float(b["l"]) for b in window)
        close = float(bar["c"])
        out.append(1 if close > high or close >= (high + low) / 2.0 else -1)
    return out


def _weighted_bounded_mean(parts) -> float | None:
    """Weighted mean of available bounded scores; None when nothing is known."""
    valid = [(float(w), float(v)) for w, v in parts if v is not None and float(w) > 0]
    if not valid:
        return None
    return max(-1.0, min(1.0, sum(w * v for w, v in valid) / sum(w for w, _ in valid)))


def aroon_trend_scores(bars: list[dict]) -> list[float | None]:
    return [None if v is None else float(v) / 100.0 for v in aroon(bars)["oscillator"]]


def tsi_momentum_scores(closes: list[float]) -> list[float | None]:
    data = true_strength_index(closes)
    return [None if a is None or b is None else math.tanh((float(a) - float(b)) / 8.0)
            for a, b in zip(data["tsi"], data["signal"])]


def trix_momentum_scores(closes: list[float]) -> list[float | None]:
    return [None if v is None else math.tanh(float(v) / 8.0) for v in trix(closes)]


def chande_momentum_scores(closes: list[float]) -> list[float | None]:
    return [None if v is None else float(v) / 100.0 for v in chande_momentum(closes)]


def ultimate_oscillator_scores(bars: list[dict]) -> list[float | None]:
    return [None if v is None else (float(v) - 50.0) / 50.0
            for v in ultimate_oscillator(bars)]


def rvi_trend_scores(bars: list[dict]) -> list[float | None]:
    data = relative_vigor_index(bars)
    return [None if a is None or b is None else math.tanh((float(a) - float(b)) * 4.0)
            for a, b in zip(data["rvi"], data["signal"])]


def regression_fusion_scores(closes: list[float]) -> list[float | None]:
    short = log_regression_trend_scores(closes, 20)
    long = log_regression_trend_scores(closes, 60)
    return [_weighted_bounded_mean(((1.0, a), (1.0, b))) for a, b in zip(short, long)]


def donchian_trend_scores(bars: list[dict]) -> list[float | None]:
    return [None if v is None else float(v) for v in donchian_state(bars)]


def obv_flow_scores(bars: list[dict]) -> list[float | None]:
    return [None if v is None else math.tanh(float(v) * 3.0)
            for v in on_balance_volume_slope(bars)]


def coppock_trend_scores(closes: list[float]) -> list[float | None]:
    return [None if v is None else math.tanh(float(v) / 5.0) for v in coppock(closes)]


def _atlas_pressure_wave_from_parts(opens, highs, lows, closes, volumes,
                                    atr_values, returns_pct, vol10) -> list[float | None]:
    """Invented v13 candle/range/volume pressure wave (origin-time only).

    Each completed bar contributes close-location/body pressure, scaled by
    its ATR range and by real relative volume when volume exists. A 15-bar
    exponentially weighted wave is then fused with 3/10-bar volatility-
    normalized momentum. On close-only bars the candle term collapses to the
    close-return sign and volume stays neutral; anatomy is never invented.
    """
    raw: list[float] = []
    for i in range(len(closes)):
        span = float(highs[i]) - float(lows[i])
        if span > 0:
            pressure = (0.65 * ((2.0 * float(closes[i]) - float(highs[i]) - float(lows[i])) / span)
                        + 0.35 * ((float(closes[i]) - float(opens[i])) / span))
        else:
            pressure = 1.0 if float(returns_pct[i]) > 0 else -1.0 if float(returns_pct[i]) < 0 else 0.0
        atr_value = atr_values[i] if i < len(atr_values) else None
        range_weight = min(2.0, span / float(atr_value)) if atr_value not in (None, 0) else 1.0
        trailing = [float(v) for v in volumes[max(0, i - 20):i] if float(v) > 0]
        median_volume = statistics.median(trailing) if trailing else 0.0
        volume_weight = 1.0
        if median_volume > 0 and float(volumes[i]) > 0:
            volume_weight = max(0.5, min(1.75, 1.0 + 0.35 * math.log(
                (float(volumes[i]) + 1.0) / (median_volume + 1.0))))
        raw.append(pressure * range_weight * volume_weight)
    out: list[float | None] = []
    for i in range(len(closes)):
        if i < 20:
            out.append(None)
            continue
        window = range(i - 14, i + 1)
        weights = [0.82 ** (i - j) for j in window]
        wave = sum(w * raw[j] for j, w in zip(window, weights)) / sum(weights)
        momentum = 0.0
        sd = vol10[i] if i < len(vol10) else None
        if sd is not None and float(sd) > 0 and closes[i - 3] and closes[i - 10]:
            momentum = (
                0.5 * math.tanh(((float(closes[i]) / float(closes[i - 3]) - 1.0) * 100.0)
                                / (float(sd) * math.sqrt(3)))
                + 0.5 * math.tanh(((float(closes[i]) / float(closes[i - 10]) - 1.0) * 100.0)
                                  / (float(sd) * math.sqrt(10))))
        out.append(max(-1.0, min(1.0, 0.65 * math.tanh(1.4 * wave) + 0.35 * momentum)))
    return out


def atlas_pressure_wave_scores(bars: list[dict]) -> list[float | None]:
    closes = [float(b["c"]) for b in bars]
    returns_pct = [0.0] + [(closes[i] / closes[i - 1] - 1.0) * 100.0 if closes[i - 1] else 0.0
                           for i in range(1, len(closes))]
    return _atlas_pressure_wave_from_parts(
        [float(b["o"]) for b in bars], [float(b["h"]) for b in bars],
        [float(b["l"]) for b in bars], closes,
        [float(b.get("v") or 0.0) for b in bars], atr(bars, 14),
        returns_pct, _rolling_vol10(returns_pct))


def _atlas_regime_compass_from_parts(closes, multiscale, hull, adx_values,
                                     entropy_values, bands, rsi_values) -> list[float | None]:
    """Smooth trend/range switch; all inputs are causal completed-bar state."""
    out: list[float | None] = []
    for i, close in enumerate(closes):
        ms = multiscale[i] if i < len(multiscale) else None
        if ms is None:
            out.append(None)
            continue
        hull_v = hull[i] if i < len(hull) and hull[i] is not None else ms
        adx_v = adx_values[i] if i < len(adx_values) and adx_values[i] is not None else 0.0
        trend_weight = max(0.0, min(1.0, (float(adx_v) - 15.0) / 20.0))
        entropy_v = entropy_values[i] if i < len(entropy_values) else None
        if entropy_v is not None:
            trend_weight = max(trend_weight, max(0.0, min(1.0, (0.90 - float(entropy_v)) / 0.25)))
        trend = 0.65 * float(ms) + 0.35 * float(hull_v)
        upper = bands["upper"][i] if i < len(bands["upper"]) else None
        lower = bands["lower"][i] if i < len(bands["lower"]) else None
        band_pos = 0.5
        if upper is not None and lower is not None and float(upper) > float(lower):
            band_pos = (float(close) - float(lower)) / (float(upper) - float(lower))
        rsi_v = rsi_values[i] if i < len(rsi_values) and rsi_values[i] is not None else 50.0
        range_score = 0.6 * (-(band_pos - 0.5) * 2.0) + 0.4 * (-(float(rsi_v) - 50.0) / 25.0)
        out.append(max(-1.0, min(1.0, trend_weight * trend
                                 + (1.0 - trend_weight) * (0.7 * range_score + 0.3 * trend))))
    return out


def atlas_regime_compass_scores(bars: list[dict]) -> list[float | None]:
    closes = [float(b["c"]) for b in bars]
    return _atlas_regime_compass_from_parts(
        closes, multiscale_trend_scores(closes), hull_trend_scores(bars),
        adx(bars)["adx"], permutation_entropy_series(closes), bollinger(closes), rsi(closes, 14))


def _atlas_phoenix_from_parts(arrays: dict) -> list[float | None]:
    """Family-balanced v13 fusion from already-computed causal score arrays."""
    n = max((len(v) for v in arrays.values()), default=0)

    def at(name: str, i: int):
        values = arrays.get(name) or []
        return values[i] if i < len(values) else None

    out: list[float | None] = []
    for i in range(n):
        trend_family = _weighted_bounded_mean(tuple((1.0, at(name, i)) for name in (
            "hull", "kalman", "kaufman", "haar")))
        momentum_family = _weighted_bounded_mean(tuple((1.0, at(name, i)) for name in (
            "multiscale", "tsi", "cmo", "trix", "coppock")))
        structure_family = _weighted_bounded_mean(tuple((1.0, at(name, i)) for name in (
            "regression60", "aroon", "ichimoku", "donchian")))
        flow_family = _weighted_bounded_mean(tuple((1.0, at(name, i)) for name in (
            "pressure", "rvi", "cmf", "obv")))
        out.append(_weighted_bounded_mean((
            (0.25, trend_family), (0.25, momentum_family), (0.20, structure_family),
            (0.20, flow_family), (0.10, at("compass", i)))))
    return out


def atlas_phoenix_scores(bars: list[dict]) -> list[float | None]:
    closes = [float(b["c"]) for b in bars]
    return _atlas_phoenix_from_parts({
        "hull": hull_trend_scores(bars), "kalman": kalman_trend_scores(closes),
        "kaufman": kaufman_trend_scores(bars), "haar": haar_wavelet_trend_scores(closes),
        "multiscale": multiscale_trend_scores(closes), "tsi": tsi_momentum_scores(closes),
        "cmo": chande_momentum_scores(closes), "trix": trix_momentum_scores(closes),
        "coppock": coppock_trend_scores(closes),
        "regression60": log_regression_trend_scores(closes, 60),
        "aroon": aroon_trend_scores(bars), "ichimoku": ichimoku_scores(bars),
        "donchian": donchian_trend_scores(bars), "pressure": atlas_pressure_wave_scores(bars),
        "rvi": rvi_trend_scores(bars), "cmf": chaikin_money_flow(bars),
        "obv": obv_flow_scores(bars), "compass": atlas_regime_compass_scores(bars),
    })


def rolling_vwap_series(bars: list[dict], period: int = 60) -> list[float | None]:
    """Rolling typical-price VWAP; equal weights only if a window has no volume."""
    if period <= 0:
        raise ValueError("VWAP period must be positive")
    out: list[float | None] = []
    typical = [(float(b["h"]) + float(b["l"]) + float(b["c"])) / 3.0 for b in bars]
    volumes = [max(0.0, float(b.get("v") or 0.0)) for b in bars]
    prefix_volume = [0.0]
    prefix_weighted = [0.0]
    prefix_typical = [0.0]
    for price, volume in zip(typical, volumes):
        prefix_volume.append(prefix_volume[-1] + volume)
        prefix_weighted.append(prefix_weighted[-1] + price * volume)
        prefix_typical.append(prefix_typical[-1] + price)
    for i in range(len(bars)):
        if i < period - 1:
            out.append(None)
            continue
        start = i - period + 1
        total_volume = prefix_volume[i + 1] - prefix_volume[start]
        if total_volume > 0:
            out.append((prefix_weighted[i + 1] - prefix_weighted[start]) / total_volume)
        else:
            out.append((prefix_typical[i + 1] - prefix_typical[start]) / period)
    return out


def minute_vwap_scores(bars: list[dict], *, mode: str = "reversion") -> list[float | None]:
    """Bounded close-to-rolling-VWAP deviation in ATR units."""
    if mode not in {"reversion", "trend"}:
        raise ValueError("VWAP mode must be reversion or trend")
    closes = [float(b["c"]) for b in bars]
    vwap_values = rolling_vwap_series(bars, 60)
    atr_values = atr(bars, 14)
    out: list[float | None] = []
    sign = -1.0 if mode == "reversion" else 1.0
    for close, vwap_value, atr_value in zip(closes, vwap_values, atr_values):
        if vwap_value is None or atr_value in (None, 0):
            out.append(None)
        else:
            out.append(sign * math.tanh((close - float(vwap_value)) / float(atr_value)))
    return out


def ema_ribbon_scores(closes: list[float]) -> list[float | None]:
    """EMA 5/13/34 ordering plus spread, scaled by 10-bar return volatility."""
    if len(closes) < 55:
        return [None] * len(closes)
    fast, middle, slow = ema(closes, 5), ema(closes, 13), ema(closes, 34)
    rets = [0.0] + [(closes[i] / closes[i - 1] - 1.0) * 100.0 if closes[i - 1] else 0.0
                    for i in range(1, len(closes))]
    vol = _rolling_vol10(rets)
    out: list[float | None] = []
    for i, close in enumerate(closes):
        if i < 54 or vol[i] in (None, 0) or not close:
            out.append(None)
            continue
        alignment = ((1 if fast[i] > middle[i] else -1 if fast[i] < middle[i] else 0)
                     + (1 if middle[i] > slow[i] else -1 if middle[i] < slow[i] else 0)
                     + (1 if close > slow[i] else -1 if close < slow[i] else 0)) / 3.0
        spread_pct = (fast[i] - slow[i]) / close * 100.0
        spread = math.tanh(spread_pct / (float(vol[i]) * math.sqrt(13.0)))
        out.append(max(-1.0, min(1.0, 0.55 * alignment + 0.45 * spread)))
    return out


def rsi2_snapback_scores(closes: list[float]) -> list[float | None]:
    """State score: +1 only for RSI2<=10 above SMA50; -1 mirror; otherwise 0."""
    rsi2 = rsi(closes, 2)
    trend = sma(closes, 50)
    out: list[float | None] = []
    for close, value, average in zip(closes, rsi2, trend):
        if value is None or average is None:
            out.append(None)
        elif float(value) <= 10.0 and close > float(average):
            out.append(1.0)
        elif float(value) >= 90.0 and close < float(average):
            out.append(-1.0)
        else:
            out.append(0.0)
    return out


def opening_range_scores(bars: list[dict], *, opening_minutes: int = 15) -> list[float | None]:
    """UTC opening-range state. This is a session proxy, not exchange-local time."""
    if len(bars) < 2:
        return [None] * len(bars)
    try:
        interval = infer_interval_seconds(bars)
    except ValueError:
        return [None] * len(bars)
    if interval > opening_minutes * 60:
        return [None] * len(bars)
    opening_bars = max(1, int(math.ceil((opening_minutes * 60) / interval)))
    out: list[float | None] = []
    current_day = None
    day_index = -1
    range_high = None
    range_low = None
    for bar in bars:
        day = dt.datetime.fromtimestamp(int(bar["t"]), tz=dt.timezone.utc).date().isoformat()
        if day != current_day:
            current_day = day
            day_index = 0
            range_high = float(bar["h"])
            range_low = float(bar["l"])
        else:
            day_index += 1
            if day_index < opening_bars:
                range_high = max(float(range_high), float(bar["h"]))
                range_low = min(float(range_low), float(bar["l"]))
        if day_index < opening_bars or range_high is None or range_low is None:
            out.append(None)
        elif float(bar["c"]) > range_high:
            out.append(1.0)
        elif float(bar["c"]) < range_low:
            out.append(-1.0)
        else:
            out.append(0.0)
    return out


def bollinger_squeeze_scores(closes: list[float]) -> list[float | None]:
    """Recent low bandwidth percentile, released in the 5-bar momentum direction."""
    bands = bollinger(closes, 20, 2.0)
    widths: list[float | None] = []
    for upper, lower, middle in zip(bands["upper"], bands["lower"], bands["middle"]):
        widths.append(None if None in (upper, lower, middle) or not middle
                      else (float(upper) - float(lower)) / float(middle))
    rets = [0.0] + [(closes[i] / closes[i - 1] - 1.0) * 100.0 if closes[i - 1] else 0.0
                    for i in range(1, len(closes))]
    vol = _rolling_vol10(rets)
    out: list[float | None] = []
    last_squeeze = -10_000
    for i, width in enumerate(widths):
        if i < 120 or width is None or vol[i] in (None, 0) or not closes[i - 5]:
            out.append(None)
            continue
        trailing = [float(x) for x in widths[max(0, i - 99):i + 1] if x is not None]
        percentile = sum(1 for x in trailing if x <= float(width)) / len(trailing) if trailing else 1.0
        if percentile <= 0.20:
            last_squeeze = i
        if i - last_squeeze > 5:
            out.append(0.0)
            continue
        ret5 = (closes[i] / closes[i - 5] - 1.0) * 100.0
        out.append(math.tanh(ret5 / (float(vol[i]) * math.sqrt(5.0))))
    return out


def volume_surge_scores(bars: list[dict]) -> list[float | None]:
    """Completed-bar candle pressure, active only on real relative-volume surges."""
    volumes = [max(0.0, float(b.get("v") or 0.0)) for b in bars]
    if not any(v > 0 for v in volumes):
        return [None] * len(bars)
    out: list[float | None] = []
    for i, bar in enumerate(bars):
        trailing = [v for v in volumes[max(0, i - 50):i] if v > 0]
        if i < 20 or len(trailing) < 20 or volumes[i] <= 0:
            out.append(None)
            continue
        baseline = statistics.median(trailing)
        if baseline <= 0:
            out.append(None)
            continue
        ratio = volumes[i] / baseline
        high, low, close, open_ = (float(bar["h"]), float(bar["l"]),
                                    float(bar["c"]), float(bar["o"]))
        span = high - low
        pressure = ((2.0 * close - high - low) / span if span > 0
                    else 1.0 if close > open_ else -1.0 if close < open_ else 0.0)
        out.append(pressure * math.tanh(math.log(ratio)) if ratio >= 1.25 else 0.0)
    return out


def _atlas_minute_pulse_from_parts(length: int, ribbon, pressure, vwap_trend,
                                   opening, surge, squeeze, entropy) -> list[float | None]:
    out: list[float | None] = []
    for i in range(length):
        fused = _weighted_bounded_mean((
            (0.25, ribbon[i]), (0.25, pressure[i]), (0.15, vwap_trend[i]),
            (0.15, opening[i]), (0.10, surge[i]), (0.10, squeeze[i])))
        if fused is None:
            out.append(None)
            continue
        gate = 1.0
        if entropy[i] is not None:
            # Ordered paths keep full weight; near-random ordinal paths are damped.
            gate = max(0.45, min(1.0, 1.0 - max(0.0, float(entropy[i]) - 0.75) * 1.8))
        out.append(max(-1.0, min(1.0, fused * gate)))
    return out


def atlas_minute_pulse_scores(bars: list[dict]) -> list[float | None]:
    """Invented v14 minute fusion; every constituent is origin-time causal."""
    closes = [float(b["c"]) for b in bars]
    return _atlas_minute_pulse_from_parts(
        len(bars), ema_ribbon_scores(closes), atlas_pressure_wave_scores(bars),
        minute_vwap_scores(bars, mode="trend"), opening_range_scores(bars),
        volume_surge_scores(bars), bollinger_squeeze_scores(closes),
        permutation_entropy_series(closes))


def minute_method_scores(bars: list[dict]) -> dict[str, list[float | None]]:
    """All v14 minute score arrays in one inspectable mapping."""
    closes = [float(b["c"]) for b in bars]
    ribbon = ema_ribbon_scores(closes)
    opening = opening_range_scores(bars)
    squeeze = bollinger_squeeze_scores(closes)
    surge = volume_surge_scores(bars)
    pulse = _atlas_minute_pulse_from_parts(
        len(bars), ribbon, atlas_pressure_wave_scores(bars),
        minute_vwap_scores(bars, mode="trend"), opening, surge, squeeze,
        permutation_entropy_series(closes))
    return {
        "minute_vwap_reversion": minute_vwap_scores(bars, mode="reversion"),
        "minute_ema_ribbon": ribbon,
        "minute_rsi2_snapback": rsi2_snapback_scores(closes),
        "minute_orb_breakout": opening,
        "minute_squeeze_breakout": squeeze,
        "minute_volume_surge": surge,
        "atlas_minute_pulse": pulse,
    }


def _wilson_interval_pct(hits: int, made: int) -> tuple[float | None, float | None]:
    if made <= 0:
        return None, None
    z = 1.959963984540054
    p = hits / made
    denominator = 1.0 + z * z / made
    centre = (p + z * z / (2.0 * made)) / denominator
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * made)) / made) / denominator
    return (_round(max(0.0, centre - margin) * 100.0, 3),
            _round(min(1.0, centre + margin) * 100.0, 3))


def minute_forecast_eval(bars: list[dict], *, attempts: int = 500,
                         horizons=(1, 3, 5, 15, 30), min_history: int = 240,
                         target_accuracy_pct: float = ACCURACY_TARGET_PCT) -> dict:
    """Hidden-future race designed for 1m/5m/15m bars and the 80% goal gate.

    Scores are causal arrays. Zero state scores abstain. A high point estimate
    on this one series still cannot establish the project goal: the response
    separates a sample-local candidate from multi-symbol/day proof.
    """
    bars = normalize_bars(bars)
    attempts = int(attempts)
    if not 10 <= attempts <= 5000:
        raise ValueError("attempts must be between 10 and 5000")
    min_history = max(130, int(min_history))
    interval = infer_interval_seconds(bars)
    closes = [float(b["c"]) for b in bars]
    arrays: dict[str, list[float | None]] = dict(minute_method_scores(bars))
    arrays.update({
        "atlas_pressure_wave": atlas_pressure_wave_scores(bars),
        "kalman_trend": kalman_trend_scores(closes),
        "multiscale_trend": multiscale_trend_scores(closes),
    })
    arrays["atlas_minute_pulse_selective"] = arrays["atlas_minute_pulse"]
    thresholds = {
        "minute_vwap_reversion": 0.0, "minute_ema_ribbon": 0.0,
        "minute_rsi2_snapback": 0.5, "minute_orb_breakout": 0.5,
        "minute_squeeze_breakout": 0.05, "minute_volume_surge": 0.05,
        "atlas_minute_pulse": 0.0, "atlas_minute_pulse_selective": 0.45,
        "atlas_pressure_wave": 0.0, "kalman_trend": 0.0, "multiscale_trend": 0.0,
    }
    rows = []
    candidates = []
    is_minute = interval <= TIMEFRAMES["15m"]
    for raw_horizon in horizons:
        horizon = int(raw_horizon)
        if horizon <= 0:
            continue
        last_origin = len(bars) - 1 - horizon
        if last_origin - min_history < 10:
            rows.append({"horizon_bars": horizon, "error": "insufficient origins",
                         "bars": len(bars), "min_history": min_history})
            continue
        span = last_origin - min_history
        step = max(1, span // attempts)
        origins = list(range(min_history, last_origin + 1, step))[-attempts:]
        method_names = list(arrays) + ["momentum_1bar", "momentum_5bar", "always_up"]
        stats = {name: {"made": 0, "hits": 0, "returns": []} for name in method_names}
        evaluable_origins = 0
        for origin in origins:
            if origin < 5 or not closes[origin]:
                continue
            evaluable_origins += 1
            actual = (closes[origin + horizon] / closes[origin] - 1.0) * 100.0
            signs: dict[str, int] = {}
            for name, values in arrays.items():
                score = values[origin] if origin < len(values) else None
                if score is None or abs(float(score)) <= thresholds[name]:
                    continue
                signs[name] = 1 if float(score) > 0 else -1
            signs["momentum_1bar"] = 1 if closes[origin] > closes[origin - 1] else -1
            signs["momentum_5bar"] = 1 if closes[origin] > closes[origin - 5] else -1
            signs["always_up"] = 1
            for name, sign_value in signs.items():
                slot = stats[name]
                slot["made"] += 1
                slot["hits"] += int(actual != 0 and (sign_value > 0) == (actual > 0))
                slot["returns"].append(sign_value * actual)
        methods = {}
        for name, slot in stats.items():
            made, hits = int(slot["made"]), int(slot["hits"])
            accuracy = _round(100.0 * hits / made, 3) if made else None
            low, high = _wilson_interval_pct(hits, made)
            returns = [float(x) for x in slot["returns"]]
            methods[name] = {
                "attempts_made": made, "hits": hits,
                "coverage_pct": _round(100.0 * made / evaluable_origins, 3) if evaluable_origins else None,
                "direction_accuracy_pct": accuracy,
                "wilson_95_ci_pct": [low, high],
                "mean_net_pct_per_trade_5bps": _round(sum(x - 0.05 for x in returns) / made, 4) if made else None,
                "mean_net_pct_per_trade_10bps": _round(sum(x - 0.10 for x in returns) / made, 4) if made else None,
                "mean_net_pct_per_trade_25bps": _round(sum(x - 0.25 for x in returns) / made, 4) if made else None,
            }
            if (is_minute and accuracy is not None and accuracy >= float(target_accuracy_pct)
                    and made >= MINUTE_GOAL_GATES["minimum_hidden_future_attempts_per_candidate"]
                    and (methods[name]["coverage_pct"] or 0) >= MINUTE_GOAL_GATES["minimum_selective_coverage_pct"]
                    and (methods[name]["mean_net_pct_per_trade_10bps"] or -1) > 0):
                candidates.append({
                    "method": name, "horizon_bars": horizon, **methods[name],
                    "status": ("sample_candidate_only_not_goal_proof"
                               if (low or 0) < float(target_accuracy_pct)
                               else "strong_single_sample_candidate_still_needs_external_validation"),
                })
        rows.append({"horizon_bars": horizon, "origins_evaluated": evaluable_origins,
                     "origin_step_bars": step, "methods": methods})
    return {
        "mode": "minute_hidden_future_evaluation",
        "bars": len(bars), "interval_seconds": interval,
        "is_minute_timeframe": is_minute,
        "attempts_requested_per_horizon": attempts,
        "min_history_bars": min_history,
        "horizons": rows,
        "goal_80_assessment": {
            "target_accuracy_pct": float(target_accuracy_pct),
            "goal_established": False,
            "sample_candidates": candidates,
            "status": ("not_reached_on_this_series" if not candidates else
                       "candidate_found_but_external_validation_still_required"),
            "gates": dict(MINUTE_GOAL_GATES),
            "why_not_established": [
                "One series/era cannot prove a universal minute-trading rate.",
                "The goal requires at least 1000 hidden-future attempts per candidate, positive mean after 10 bps, coverage disclosure, a Wilson lower bound at the target for a strong statistical claim, and fresh validation across symbols and days.",
                "Minute results are especially sensitive to spread, latency, partial fills and exchange fees; OHLCV alone does not observe the order book.",
            ] if is_minute else [
                "The supplied bars are not 1m/5m/15m bars, so this run cannot satisfy the minute goal."],
        },
        "warning": "Historical hidden-future measurement only. It is not a live accuracy promise.",
    }


def atlas_minute_pulse_now(bars: list[dict]) -> dict:
    bars = normalize_bars(bars)
    return _bounded_score_now(
        "Atlas Minute Pulse", bars, atlas_minute_pulse_scores(bars),
        "EMA ribbon 25% + Pressure Wave 25% + rolling-VWAP trend side 15% + UTC opening-range "
        "state 15% + volume surge 10% + squeeze release 10%, entropy-damped.")


def project_goals() -> dict:
    """Machine-readable v14 goals; status fields deliberately separate target from proof."""
    return {
        "version": "15.0", "updated": "2026-10-21",
        "goals": [
            {"id": "minute_timeframe_focus", "title": "Focus research and the bot on 1m/5m/15m bars",
             "status": "implemented_in_v14", "primary_timeframe": "1m",
             "evidence": "Seven minute engines, a 1/3/5/15/30-bar hidden-future race, minute bot defaults and 1m public-data presets."},
            {"id": "accuracy_80", "title": "Reach at least 80% out-of-sample direction accuracy",
             "status": "active_target_not_reached", "target_pct": ACCURACY_TARGET_PCT,
             "gates": dict(MINUTE_GOAL_GATES),
             "current_real_evidence": "v13 real daily/monthly samples reached 68% on one AAPL test and 63.077% pooled; no bundled real minute sample establishes a minute rate."},
            {"id": "integrated_real_bot", "title": "Become a complete real trading bot",
             "status": "manual_external_account_companion_only",
             "implemented": "Minute paper bot, risk halts, Start/Resume/Pause/STOP/flatten workflow and manual external execution tickets.",
             "not_implemented": "No exchange/broker credentials, API-key storage, automatic order routing, leverage or shorting in TradeAtlas.",
             "next_gate": "A separately reviewed testnet integration in the user's own licensed account would require security, legal, venue and halal-form review before any live automation."},
            {"id": "usdt_btc_funding", "title": "Let the user fund trading with USDT or BTC",
             "status": "user_own_exchange_account_only",
             "rule": "USDT/BTC remain in the user's own licensed exchange account. TradeAtlas has no deposit address and must never receive or custody crypto.",
             "implemented": "External-account balance mirror and paper conversion/transfer simulations; the mirror is user-reported and is not added to paper equity."},
            {"id": "failure_memory", "title": "Learn from every failed test instead of repeating it",
             "status": "implemented_in_v15",
             "evidence": ("A cause library of 20 named failure modes, an avoid-rule and an implemented "
                          "remedy per cause, a three-stage loop (screen -> apply lessons -> validate), "
                          "resolved/recurred/retired lesson states, and a SQLite failure memory that "
                          "makes later runs skip already-proven dead candidates."),
             "not_claimed": ("The failure memory improves the *research process*, not the market. "
                             "It cannot create an edge that the sample does not contain, and it never "
                             "lowers the 80% gates.")},
            {"id": "halal_gate", "title": "Keep bot entries behind current halal evidence",
             "status": "implemented_rule_gate_not_fatwa",
             "rule": "Only registered assets whose current screen is exactly pass may enter even a paper/manual-ticket workflow."},
        ],
        "real_money_execution_enabled": False,
        "tradeatlas_deposit_address": None,
        "accepts_real_crypto": False,
        "warning": "Goals are not performance claims. Do not send money or crypto to TradeAtlas.",
    }


def _round(value, digits: int = 6):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return round(float(value), digits)


def _iso(timestamp: int) -> str:
    return dt.datetime.fromtimestamp(int(timestamp), tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


def indicator_snapshot(bars: list[dict]) -> dict:
    closes = [float(b["c"]) for b in bars]
    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    rsi14 = rsi(closes, 14)
    macd_data = macd(closes)
    bands = bollinger(closes)
    atr14 = atr(bars, 14)
    stoch = stochastic(bars)
    adx_data = adx(bars)
    stc_values = schaff_trend_cycle(closes)
    vortex_data = vortex(bars)
    fisher_data = fisher_transform(bars)
    kst_data = kst(closes)
    cmf_values = chaikin_money_flow(bars)
    mfi_values = money_flow_index(bars)
    multiscale_values = multiscale_trend_scores(closes)
    cci_values = commodity_channel_index(bars)
    williams_values = williams_r(bars)
    tsi_data = true_strength_index(closes)
    trix_values = trix(closes)
    ultimate_values = ultimate_oscillator(bars)
    sar_data = parabolic_sar(bars)
    ichimoku_values = ichimoku_scores(bars)
    obv_values = on_balance_volume_slope(bars)
    kalman_values = kalman_trend_scores(closes)
    regression20_values = log_regression_trend_scores(closes, 20)
    regression60_values = log_regression_trend_scores(closes, 60)
    omni_values = omni_direct_scores(bars, horizon=5)
    hull_values = hull_moving_average(closes)
    hull_scores = hull_trend_scores(bars)
    supertrend_data = supertrend(bars)
    kama_values = kaufman_adaptive_moving_average(closes)
    kama_scores = kaufman_trend_scores(bars)
    haar_scores = haar_wavelet_trend_scores(closes)
    donchian_values = donchian_state(bars)
    entropy_latest = permutation_entropy_at(closes)
    aroon_data = aroon(bars)
    cmo_values = chande_momentum(closes)
    rvi_data = relative_vigor_index(bars)
    coppock_values = coppock(closes)
    minute_scores = minute_method_scores(bars)
    rolling_vwap_values = rolling_vwap_series(bars, 60)
    rsi2_values = rsi(closes, 2)
    snapshot_rets = [0.0] + [(closes[i] / closes[i - 1] - 1.0) * 100.0 if closes[i - 1] else 0.0
                             for i in range(1, len(closes))]
    pressure_scores = _atlas_pressure_wave_from_parts(
        [float(b["o"]) for b in bars], [float(b["h"]) for b in bars],
        [float(b["l"]) for b in bars], closes, [float(b.get("v") or 0.0) for b in bars],
        atr14, snapshot_rets, _rolling_vol10(snapshot_rets))
    entropy_for_latest: list[float | None] = [None] * len(closes)
    if entropy_for_latest:
        entropy_for_latest[-1] = entropy_latest
    compass_scores = _atlas_regime_compass_from_parts(
        closes, multiscale_values, hull_scores, adx_data["adx"], entropy_for_latest, bands, rsi14)
    tsi_scores = [None if a is None or b is None else math.tanh((float(a) - float(b)) / 8.0)
                  for a, b in zip(tsi_data["tsi"], tsi_data["signal"])]
    trix_scores = [None if v is None else math.tanh(float(v) / 8.0) for v in trix_values]
    cmo_scores = [None if v is None else float(v) / 100.0 for v in cmo_values]
    ultimate_scores = [None if v is None else (float(v) - 50.0) / 50.0 for v in ultimate_values]
    rvi_scores = [None if a is None or b is None else math.tanh((float(a) - float(b)) * 4.0)
                  for a, b in zip(rvi_data["rvi"], rvi_data["signal"])]
    regression_fusion = [_weighted_bounded_mean(((1.0, a), (1.0, b)))
                         for a, b in zip(regression20_values, regression60_values)]
    obv_scores = [None if v is None else math.tanh(float(v) * 3.0) for v in obv_values]
    coppock_scores = [None if v is None else math.tanh(float(v) / 5.0) for v in coppock_values]
    phoenix_scores = _atlas_phoenix_from_parts({
        "hull": hull_scores, "kalman": kalman_values, "kaufman": kama_scores,
        "haar": haar_scores, "multiscale": multiscale_values, "tsi": tsi_scores,
        "cmo": cmo_scores, "trix": trix_scores, "coppock": coppock_scores,
        "regression60": regression60_values,
        "aroon": [None if v is None else float(v) / 100.0 for v in aroon_data["oscillator"]],
        "ichimoku": ichimoku_values,
        "donchian": [None if v is None else float(v) for v in donchian_values],
        "pressure": pressure_scores, "rvi": rvi_scores, "cmf": cmf_values,
        "obv": obv_scores, "compass": compass_scores,
    })
    multiscale_latest = multiscale_values[-1] if multiscale_values else None
    latest = bars[-1]
    score = 0
    reasons = []
    if ema20[-1] > ema50[-1]:
        score += 1
        reasons.append("EMA20 is above EMA50")
    elif ema20[-1] < ema50[-1]:
        score -= 1
        reasons.append("EMA20 is below EMA50")
    if macd_data["histogram"][-1] > 0:
        score += 1
        reasons.append("MACD histogram is positive")
    elif macd_data["histogram"][-1] < 0:
        score -= 1
        reasons.append("MACD histogram is negative")
    if rsi14[-1] is not None:
        if rsi14[-1] >= 55:
            score += 1
            reasons.append("RSI is at/above 55")
        elif rsi14[-1] <= 45:
            score -= 1
            reasons.append("RSI is at/below 45")
    reference = sma200[-1] if sma200[-1] is not None else sma50[-1]
    if reference is not None:
        if closes[-1] > reference:
            score += 1
            reasons.append("Price is above its long moving average")
        elif closes[-1] < reference:
            score -= 1
            reasons.append("Price is below its long moving average")
    bias = "bullish_bias" if score >= 2 else "bearish_bias" if score <= -2 else "neutral_bias"
    return {
        "timestamp": int(latest["t"]), "time_utc": _iso(int(latest["t"])),
        "open": _round(latest["o"]), "high": _round(latest["h"]),
        "low": _round(latest["l"]), "close": _round(latest["c"]),
        "volume": _round(latest.get("v") or 0),
        "sma20": _round(sma20[-1]), "sma50": _round(sma50[-1]), "sma200": _round(sma200[-1]),
        "ema20": _round(ema20[-1]), "ema50": _round(ema50[-1]),
        "rsi14": _round(rsi14[-1], 2),
        "macd": _round(macd_data["macd"][-1]), "macd_signal": _round(macd_data["signal"][-1]),
        "macd_histogram": _round(macd_data["histogram"][-1]),
        "bollinger_middle": _round(bands["middle"][-1]),
        "bollinger_upper": _round(bands["upper"][-1]),
        "bollinger_lower": _round(bands["lower"][-1]),
        "atr14": _round(atr14[-1]),
        "stochastic_k": _round(stoch["k"][-1], 2), "stochastic_d": _round(stoch["d"][-1], 2),
        "adx14": _round(adx_data["adx"][-1], 2),
        "di_plus": _round(adx_data["plus_di"][-1], 2), "di_minus": _round(adx_data["minus_di"][-1], 2),
        "bias_score": score, "bias": bias, "bias_reasons": reasons,
        "cycle_flow": {
            "schaff_trend_cycle": _round(stc_values[-1], 2),
            "vortex_plus": _round(vortex_data["plus"][-1], 4),
            "vortex_minus": _round(vortex_data["minus"][-1], 4),
            "fisher": _round(fisher_data["fisher"][-1], 4),
            "fisher_trigger": _round(fisher_data["trigger"][-1], 4),
            "kst": _round(kst_data["kst"][-1], 4),
            "kst_signal": _round(kst_data["signal"][-1], 4),
            "chaikin_money_flow": _round(cmf_values[-1], 4),
            "money_flow_index": _round(mfi_values[-1], 2),
            "multiscale_trend_score": _round(multiscale_latest, 4),
            "permutation_entropy": _round(entropy_latest, 4),
            "entropy_weighted_trend": _round(
                None if multiscale_latest is None or entropy_latest is None
                else float(multiscale_latest) * (1.0 - float(entropy_latest)), 4),
            "note": "Additional origin-time state for the v10 cycle/flow engines; it does not change the legacy bias score above.",
        },
        "advanced_v11": {
            "cci20": _round(cci_values[-1], 2),
            "williams_r14": _round(williams_values[-1], 2),
            "tsi": _round(tsi_data["tsi"][-1], 3),
            "tsi_signal": _round(tsi_data["signal"][-1], 3),
            "trix15": _round(trix_values[-1], 4),
            "ultimate_oscillator": _round(ultimate_values[-1], 2),
            "parabolic_sar": _round(sar_data["sar"][-1]),
            "parabolic_sar_trend": sar_data["trend"][-1],
            "ichimoku_score": _round(ichimoku_values[-1], 4),
            "obv_slope_20": _round(obv_values[-1], 4),
            "kalman_trend_score": _round(kalman_values[-1], 4),
            "log_regression_trend_20": _round(regression20_values[-1], 4),
            "log_regression_trend_60": _round(regression60_values[-1], 4),
            "omni_direct_score_h5": _round(omni_values[-1], 4),
            "note": "Additional v11 direct-method state; it is research output, not a trade instruction.",
        },
        "advanced_v12": {
            "hull_ma20": _round(hull_values[-1]),
            "hull_trend_score": _round(hull_scores[-1], 4),
            "supertrend_10_3": _round(supertrend_data["supertrend"][-1]),
            "supertrend_trend": supertrend_data["trend"][-1],
            "kaufman_ama": _round(kama_values[-1]),
            "kaufman_trend_score": _round(kama_scores[-1], 4),
            "haar_wavelet_trend_score": _round(haar_scores[-1], 4),
            "donchian_state_20": donchian_values[-1],
            "note": "Additional v12 direct-method state; research only, not a trade instruction.",
        },
        "advanced_v13": {
            "aroon_oscillator": _round(aroon_data["oscillator"][-1], 2),
            "tsi_signal_score": _round(tsi_scores[-1], 4),
            "trix_score": _round(trix_scores[-1], 4),
            "cmo_score": _round(cmo_scores[-1], 4),
            "ultimate_score": _round(ultimate_scores[-1], 4),
            "rvi_score": _round(rvi_scores[-1], 4),
            "regression_fusion_score": _round(regression_fusion[-1], 4),
            "donchian_score": _round(donchian_values[-1], 4),
            "obv_flow_score": _round(obv_scores[-1], 4),
            "coppock_score": _round(coppock_scores[-1], 4),
            "atlas_pressure_wave_score": _round(pressure_scores[-1], 4),
            "atlas_regime_compass_score": _round(compass_scores[-1], 4),
            "atlas_phoenix_score": _round(phoenix_scores[-1], 4),
            "note": "Additional v13 classic/modern/invented state. Pressure Wave, Regime Compass and Phoenix are TradeAtlas research rules, not probabilities or trade instructions.",
        },
        "advanced_v14_minute": {
            "focus_timeframes": list(MINUTE_TIMEFRAMES),
            "rolling_vwap_60": _round(rolling_vwap_values[-1]),
            "minute_vwap_reversion_score": _round(minute_scores["minute_vwap_reversion"][-1], 4),
            "minute_ema_ribbon_score": _round(minute_scores["minute_ema_ribbon"][-1], 4),
            "rsi2": _round(rsi2_values[-1], 2),
            "minute_rsi2_snapback_score": _round(minute_scores["minute_rsi2_snapback"][-1], 4),
            "minute_orb_score": _round(minute_scores["minute_orb_breakout"][-1], 4),
            "minute_squeeze_score": _round(minute_scores["minute_squeeze_breakout"][-1], 4),
            "minute_volume_surge_score": _round(minute_scores["minute_volume_surge"][-1], 4),
            "atlas_minute_pulse_score": _round(minute_scores["atlas_minute_pulse"][-1], 4),
            "accuracy_target_pct": ACCURACY_TARGET_PCT,
            "accuracy_target_status": "goal_only_not_established_by_this_snapshot",
            "note": "Minute-first v14 research state. ORB uses a UTC session proxy; verify the venue's real session. Scores are not probabilities or trade instructions.",
        },
    }


def _crossed_up(prev_a, cur_a, prev_b, cur_b) -> bool:
    return None not in (prev_a, cur_a, prev_b, cur_b) and prev_a <= prev_b and cur_a > cur_b


def _crossed_down(prev_a, cur_a, prev_b, cur_b) -> bool:
    return None not in (prev_a, cur_a, prev_b, cur_b) and prev_a >= prev_b and cur_a < cur_b


def _consensus_scores(closes: list[float]) -> list[int]:
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    sma50 = sma(closes, 50)
    rsi14 = rsi(closes, 14)
    macd_data = macd(closes)
    scores = []
    for i, close in enumerate(closes):
        score = 0
        score += 1 if ema20[i] > ema50[i] else -1 if ema20[i] < ema50[i] else 0
        score += 1 if macd_data["histogram"][i] > 0 else -1 if macd_data["histogram"][i] < 0 else 0
        if rsi14[i] is not None:
            score += 1 if rsi14[i] >= 55 else -1 if rsi14[i] <= 45 else 0
        if sma50[i] is not None:
            score += 1 if close > sma50[i] else -1 if close < sma50[i] else 0
        scores.append(score)
    return scores


def generate_signal_events(bars: list[dict], strategy: str) -> list[dict]:
    if strategy not in STRATEGY_ENGINES:
        raise ValueError(f"unknown strategy '{strategy}'")
    if len(bars) < 55:
        return []
    closes = [float(b["c"]) for b in bars]
    highs = [float(b["h"]) for b in bars]
    lows = [float(b["l"]) for b in bars]
    # Compute only the indicator sets this engine reads (tournaments run every engine).
    ema20 = ema50 = sma50 = rsi14 = macd_data = bands = consensus = stoch = adx_data = None
    stc_values = vortex_data = fisher_data = kst_data = entropy_data = None
    cci_values = williams_values = sar_data = ichimoku_values = kalman_values = omni_values = None
    hull_scores = supertrend_data = kama_scores = haar_scores = None
    v13_scores = ultimate_values = minute_scores = None
    if strategy == "ma_cross":
        ema20, ema50 = ema(closes, 20), ema(closes, 50)
    elif strategy == "macd_cross":
        macd_data = macd(closes)
    elif strategy == "rsi_reversal":
        rsi14 = rsi(closes, 14)
    elif strategy == "bollinger_mean_reversion":
        bands = bollinger(closes)
    elif strategy == "trend_pullback_rsi":
        sma50, rsi14 = sma(closes, 50), rsi(closes, 14)
    elif strategy == "consensus":
        consensus = _consensus_scores(closes)
    elif strategy == "stochastic_reversal":
        stoch = stochastic(bars)
    elif strategy == "adx_trend_strength":
        adx_data = adx(bars)
    elif strategy == "schaff_cycle":
        stc_values = schaff_trend_cycle(closes)
    elif strategy == "vortex_trend":
        vortex_data = vortex(bars)
    elif strategy == "fisher_reversal":
        fisher_data = fisher_transform(bars)
    elif strategy == "kst_momentum":
        kst_data = kst(closes)
    elif strategy == "entropy_trend":
        entropy_data = entropy_weighted_trend_scores(bars)
    elif strategy == "cci_reversal":
        cci_values = commodity_channel_index(bars)
    elif strategy == "williams_reversal":
        williams_values = williams_r(bars)
    elif strategy == "parabolic_sar_trend":
        sar_data = parabolic_sar(bars)
    elif strategy == "ichimoku_cloud":
        ichimoku_values = ichimoku_scores(bars)
    elif strategy == "kalman_trend":
        kalman_values = kalman_trend_scores(closes)
    elif strategy == "omni_consensus":
        omni_values = omni_direct_scores(bars, horizon=5)
    elif strategy == "hull_trend":
        hull_scores = hull_trend_scores(bars)
    elif strategy == "supertrend_flip":
        supertrend_data = supertrend(bars)
    elif strategy == "kaufman_trend":
        kama_scores = kaufman_trend_scores(bars)
    elif strategy == "haar_wavelet":
        haar_scores = haar_wavelet_trend_scores(closes)
    elif strategy == "aroon_trend":
        v13_scores = aroon_trend_scores(bars)
    elif strategy == "tsi_momentum":
        v13_scores = tsi_momentum_scores(closes)
    elif strategy == "trix_momentum":
        v13_scores = trix_momentum_scores(closes)
    elif strategy == "cmo_momentum":
        v13_scores = chande_momentum_scores(closes)
    elif strategy == "ultimate_reversal":
        ultimate_values = ultimate_oscillator(bars)
    elif strategy == "rvi_trend":
        v13_scores = rvi_trend_scores(bars)
    elif strategy == "regression_trend":
        v13_scores = regression_fusion_scores(closes)
    elif strategy == "donchian_trend":
        v13_scores = donchian_trend_scores(bars)
    elif strategy == "obv_flow_trend":
        v13_scores = obv_flow_scores(bars)
    elif strategy == "coppock_trend":
        v13_scores = coppock_trend_scores(closes)
    elif strategy == "atlas_pressure_wave":
        v13_scores = atlas_pressure_wave_scores(bars)
    elif strategy == "atlas_regime_compass":
        v13_scores = atlas_regime_compass_scores(bars)
    elif strategy == "atlas_phoenix_fusion":
        v13_scores = atlas_phoenix_scores(bars)
    elif strategy in ("minute_vwap_reversion", "minute_ema_ribbon", "minute_rsi2_snapback",
                      "minute_orb_breakout", "minute_squeeze_breakout", "minute_volume_surge",
                      "atlas_minute_pulse"):
        # Compute only the requested array; the all-engine tournament calls
        # this branch once per minute engine and must not rebuild all seven.
        if strategy == "minute_vwap_reversion":
            minute_scores = minute_vwap_scores(bars, mode="reversion")
        elif strategy == "minute_ema_ribbon":
            minute_scores = ema_ribbon_scores(closes)
        elif strategy == "minute_rsi2_snapback":
            minute_scores = rsi2_snapback_scores(closes)
        elif strategy == "minute_orb_breakout":
            minute_scores = opening_range_scores(bars)
        elif strategy == "minute_squeeze_breakout":
            minute_scores = bollinger_squeeze_scores(closes)
        elif strategy == "minute_volume_surge":
            minute_scores = volume_surge_scores(bars)
        else:
            minute_scores = atlas_minute_pulse_scores(bars)
    events = []

    def add(i: int, direction: int, reason: str):
        events.append({
            "index": i, "timestamp": int(bars[i]["t"]), "time_utc": _iso(int(bars[i]["t"])),
            "direction": direction,
            "condition": "long_condition" if direction > 0 else "short_condition",
            "close": _round(closes[i]), "reason": reason,
        })

    start = 55
    for i in range(start, len(bars)):
        if strategy == "ma_cross":
            if _crossed_up(ema20[i - 1], ema20[i], ema50[i - 1], ema50[i]):
                add(i, 1, "EMA20 crossed above EMA50")
            elif _crossed_down(ema20[i - 1], ema20[i], ema50[i - 1], ema50[i]):
                add(i, -1, "EMA20 crossed below EMA50")
        elif strategy == "macd_cross":
            if _crossed_up(macd_data["macd"][i - 1], macd_data["macd"][i],
                           macd_data["signal"][i - 1], macd_data["signal"][i]):
                add(i, 1, "MACD crossed above its signal line")
            elif _crossed_down(macd_data["macd"][i - 1], macd_data["macd"][i],
                               macd_data["signal"][i - 1], macd_data["signal"][i]):
                add(i, -1, "MACD crossed below its signal line")
        elif strategy == "breakout_20":
            prior_high = max(highs[i - 20:i])
            prior_low = min(lows[i - 20:i])
            if closes[i] > prior_high and closes[i - 1] <= max(highs[i - 21:i - 1]):
                add(i, 1, "Close broke the prior 20-bar high")
            elif closes[i] < prior_low and closes[i - 1] >= min(lows[i - 21:i - 1]):
                add(i, -1, "Close broke the prior 20-bar low")
        elif strategy == "rsi_reversal":
            if rsi14[i - 1] is not None and rsi14[i] is not None:
                if rsi14[i - 1] <= 30 < rsi14[i]:
                    add(i, 1, "RSI crossed back above 30")
                elif rsi14[i - 1] >= 70 > rsi14[i]:
                    add(i, -1, "RSI crossed back below 70")
        elif strategy == "bollinger_mean_reversion":
            if None not in (bands["lower"][i - 1], bands["lower"][i], bands["upper"][i - 1], bands["upper"][i]):
                if closes[i - 1] < bands["lower"][i - 1] and closes[i] >= bands["lower"][i]:
                    add(i, 1, "Close returned inside the lower Bollinger Band")
                elif closes[i - 1] > bands["upper"][i - 1] and closes[i] <= bands["upper"][i]:
                    add(i, -1, "Close returned inside the upper Bollinger Band")
        elif strategy == "trend_pullback_rsi":
            if sma50[i] is not None and rsi14[i - 1] is not None and rsi14[i] is not None:
                if closes[i] > sma50[i] and rsi14[i - 1] <= 45 < rsi14[i]:
                    add(i, 1, "Uptrend pullback reset: price above SMA50 and RSI crossed up through 45")
                elif closes[i] < sma50[i] and rsi14[i - 1] >= 55 > rsi14[i]:
                    add(i, -1, "Downtrend pullback reset: price below SMA50 and RSI crossed down through 55")
        elif strategy == "consensus":
            if consensus[i - 1] < 3 <= consensus[i]:
                add(i, 1, "Multi-indicator consensus reached +3")
            elif consensus[i - 1] > -3 >= consensus[i]:
                add(i, -1, "Multi-indicator consensus reached -3")
        elif strategy == "stochastic_reversal":
            k_prev, k_cur = stoch["k"][i - 1], stoch["k"][i]
            d_prev, d_cur = stoch["d"][i - 1], stoch["d"][i]
            if None not in (k_prev, k_cur, d_prev, d_cur):
                if k_prev <= d_prev and k_cur > d_cur and d_cur <= 30:
                    add(i, 1, "Stochastic %K crossed above %D in the oversold zone")
                elif k_prev >= d_prev and k_cur < d_cur and d_cur >= 70:
                    add(i, -1, "Stochastic %K crossed below %D in the overbought zone")
        elif strategy == "adx_trend_strength":
            a_prev, a_cur = adx_data["adx"][i - 1], adx_data["adx"][i]
            p_cur, m_cur = adx_data["plus_di"][i], adx_data["minus_di"][i]
            if None not in (a_prev, a_cur, p_cur, m_cur) and a_prev < 25 <= a_cur:
                if p_cur > m_cur:
                    add(i, 1, "ADX crossed above 25 with +DI above -DI (uptrend strengthening)")
                elif m_cur > p_cur:
                    add(i, -1, "ADX crossed above 25 with -DI above +DI (downtrend strengthening)")
        elif strategy == "schaff_cycle":
            prev, cur = stc_values[i - 1], stc_values[i]
            if prev is not None and cur is not None:
                if prev <= 25 < cur:
                    add(i, 1, "Schaff Trend Cycle crossed upward through 25")
                elif prev >= 75 > cur:
                    add(i, -1, "Schaff Trend Cycle crossed downward through 75")
        elif strategy == "vortex_trend":
            if _crossed_up(vortex_data["plus"][i - 1], vortex_data["plus"][i],
                           vortex_data["minus"][i - 1], vortex_data["minus"][i]):
                add(i, 1, "Vortex +VI crossed above -VI")
            elif _crossed_down(vortex_data["plus"][i - 1], vortex_data["plus"][i],
                               vortex_data["minus"][i - 1], vortex_data["minus"][i]):
                add(i, -1, "Vortex +VI crossed below -VI")
        elif strategy == "fisher_reversal":
            f_prev, f_cur = fisher_data["fisher"][i - 1], fisher_data["fisher"][i]
            t_prev, t_cur = fisher_data["trigger"][i - 1], fisher_data["trigger"][i]
            if _crossed_up(f_prev, f_cur, t_prev, t_cur) and float(f_cur) < 0:
                add(i, 1, "Fisher Transform crossed above its trigger below zero")
            elif _crossed_down(f_prev, f_cur, t_prev, t_cur) and float(f_cur) > 0:
                add(i, -1, "Fisher Transform crossed below its trigger above zero")
        elif strategy == "kst_momentum":
            if _crossed_up(kst_data["kst"][i - 1], kst_data["kst"][i],
                           kst_data["signal"][i - 1], kst_data["signal"][i]):
                add(i, 1, "KST crossed above its 9-bar signal average")
            elif _crossed_down(kst_data["kst"][i - 1], kst_data["kst"][i],
                               kst_data["signal"][i - 1], kst_data["signal"][i]):
                add(i, -1, "KST crossed below its 9-bar signal average")
        elif strategy == "entropy_trend":
            prev, cur = entropy_data["score"][i - 1], entropy_data["score"][i]
            entropy = entropy_data["entropy"][i]
            if prev is not None and cur is not None and entropy is not None and float(entropy) <= 0.80:
                if prev <= 0.10 < cur:
                    add(i, 1, "Entropy-Weighted Trend crossed above +0.10 in an ordered path regime")
                elif prev >= -0.10 > cur:
                    add(i, -1, "Entropy-Weighted Trend crossed below -0.10 in an ordered path regime")
        elif strategy == "cci_reversal":
            prev, cur = cci_values[i - 1], cci_values[i]
            if prev is not None and cur is not None:
                if prev <= -100 < cur:
                    add(i, 1, "CCI crossed back above -100")
                elif prev >= 100 > cur:
                    add(i, -1, "CCI crossed back below +100")
        elif strategy == "williams_reversal":
            prev, cur = williams_values[i - 1], williams_values[i]
            if prev is not None and cur is not None:
                if prev <= -80 < cur:
                    add(i, 1, "Williams %R crossed back above -80")
                elif prev >= -20 > cur:
                    add(i, -1, "Williams %R crossed back below -20")
        elif strategy == "parabolic_sar_trend":
            if sar_data["trend"][i - 1] < 0 < sar_data["trend"][i]:
                add(i, 1, "Parabolic SAR flipped below price")
            elif sar_data["trend"][i - 1] > 0 > sar_data["trend"][i]:
                add(i, -1, "Parabolic SAR flipped above price")
        elif strategy == "ichimoku_cloud":
            prev, cur = ichimoku_values[i - 1], ichimoku_values[i]
            if prev is not None and cur is not None:
                if prev <= (1.0 / 3.0) < cur:
                    add(i, 1, "Ichimoku score crossed above +1/3")
                elif prev >= (-1.0 / 3.0) > cur:
                    add(i, -1, "Ichimoku score crossed below -1/3")
        elif strategy == "kalman_trend":
            prev, cur = kalman_values[i - 1], kalman_values[i]
            if prev is not None and cur is not None:
                if prev <= 0.15 < cur:
                    add(i, 1, "Kalman local-trend slope crossed above +0.15")
                elif prev >= -0.15 > cur:
                    add(i, -1, "Kalman local-trend slope crossed below -0.15")
        elif strategy == "omni_consensus":
            prev, cur = omni_values[i - 1], omni_values[i]
            if prev is not None and cur is not None:
                if prev <= 0.20 < cur:
                    add(i, 1, "Omni direct consensus crossed above +0.20")
                elif prev >= -0.20 > cur:
                    add(i, -1, "Omni direct consensus crossed below -0.20")
        elif strategy == "hull_trend":
            prev, cur = hull_scores[i - 1], hull_scores[i]
            if prev is not None and cur is not None:
                if prev <= 0.20 < cur:
                    add(i, 1, "Hull trend score crossed above +0.20")
                elif prev >= -0.20 > cur:
                    add(i, -1, "Hull trend score crossed below -0.20")
        elif strategy == "supertrend_flip":
            if supertrend_data["trend"][i - 1] < 0 < supertrend_data["trend"][i]:
                add(i, 1, "Supertrend flipped below price")
            elif supertrend_data["trend"][i - 1] > 0 > supertrend_data["trend"][i]:
                add(i, -1, "Supertrend flipped above price")
        elif strategy == "kaufman_trend":
            prev, cur = kama_scores[i - 1], kama_scores[i]
            if prev is not None and cur is not None:
                if prev <= 0.20 < cur:
                    add(i, 1, "Kaufman adaptive trend crossed above +0.20")
                elif prev >= -0.20 > cur:
                    add(i, -1, "Kaufman adaptive trend crossed below -0.20")
        elif strategy == "haar_wavelet":
            prev, cur = haar_scores[i - 1], haar_scores[i]
            if prev is not None and cur is not None:
                if prev <= 0.20 < cur:
                    add(i, 1, "Haar wavelet trend crossed above +0.20")
                elif prev >= -0.20 > cur:
                    add(i, -1, "Haar wavelet trend crossed below -0.20")
        elif strategy == "ultimate_reversal":
            prev, cur = ultimate_values[i - 1], ultimate_values[i]
            if prev is not None and cur is not None:
                if prev <= 30 < cur:
                    add(i, 1, "Ultimate Oscillator crossed back above 30")
                elif prev >= 70 > cur:
                    add(i, -1, "Ultimate Oscillator crossed back below 70")
        elif strategy == "donchian_trend":
            prev, cur = v13_scores[i - 1], v13_scores[i]
            if prev is not None and cur is not None:
                if prev < 0 < cur:
                    add(i, 1, "Donchian state flipped positive")
                elif prev > 0 > cur:
                    add(i, -1, "Donchian state flipped negative")
        elif strategy in ("aroon_trend", "tsi_momentum", "trix_momentum", "cmo_momentum",
                          "rvi_trend", "regression_trend", "obv_flow_trend", "coppock_trend",
                          "atlas_pressure_wave", "atlas_regime_compass", "atlas_phoenix_fusion"):
            prev, cur = v13_scores[i - 1], v13_scores[i]
            threshold = (0.25 if strategy in ("aroon_trend", "cmo_momentum")
                         else 0.0 if strategy == "trix_momentum" else 0.20)
            if prev is not None and cur is not None:
                label = STRATEGY_ENGINES[strategy]["name"]
                if prev <= threshold < cur:
                    add(i, 1, f"{label} crossed above +{threshold:.2f}")
                elif prev >= -threshold > cur:
                    add(i, -1, f"{label} crossed below -{threshold:.2f}")
        elif strategy in ("minute_rsi2_snapback", "minute_orb_breakout"):
            prev, cur = minute_scores[i - 1], minute_scores[i]
            if prev is not None and cur is not None:
                label = STRATEGY_ENGINES[strategy]["name"]
                if prev <= 0 < cur:
                    add(i, 1, f"{label} state flipped positive")
                elif prev >= 0 > cur:
                    add(i, -1, f"{label} state flipped negative")
        elif strategy in ("minute_vwap_reversion", "minute_ema_ribbon",
                          "minute_squeeze_breakout", "minute_volume_surge",
                          "atlas_minute_pulse"):
            prev, cur = minute_scores[i - 1], minute_scores[i]
            threshold = {"minute_vwap_reversion": 0.25, "minute_ema_ribbon": 0.25,
                         "minute_squeeze_breakout": 0.20, "minute_volume_surge": 0.35,
                         "atlas_minute_pulse": 0.25}[strategy]
            if prev is not None and cur is not None:
                label = STRATEGY_ENGINES[strategy]["name"]
                if prev <= threshold < cur:
                    add(i, 1, f"{label} crossed above +{threshold:.2f}")
                elif prev >= -threshold > cur:
                    add(i, -1, f"{label} crossed below -{threshold:.2f}")
    return events


def latest_signal(bars: list[dict], strategy: str, *, fresh_bars: int = 3,
                  snapshot: dict | None = None,
                  events: list[dict] | None = None) -> dict:
    if snapshot is None:
        snapshot = indicator_snapshot(bars)
    if events is None:
        events = generate_signal_events(bars, strategy)
    if not events:
        return {"condition": "no_fresh_trigger", "fresh": False,
                "bias": snapshot["bias"], "bias_score": snapshot["bias_score"],
                "last_event": None, "bars_since_last_event": None,
                "message": "No completed signal event exists in the supplied history."}
    last = events[-1]
    age = len(bars) - 1 - int(last["index"])
    fresh = age <= max(0, int(fresh_bars))
    return {
        "condition": last["condition"] if fresh else "no_fresh_trigger",
        "fresh": fresh, "bias": snapshot["bias"], "bias_score": snapshot["bias_score"],
        "last_event": last, "bars_since_last_event": age,
        "message": (f"A mechanical {last['condition']} fired {age} bar(s) ago: {last['reason']}."
                    if fresh else
                    f"No fresh trigger in the last {fresh_bars + 1} bars. Last mechanical event was {age} bars ago."),
    }


def backtest_signals(
    bars: list[dict], strategy: str, *, max_trades: int = 100,
    horizon_bars: int = 10, round_trip_cost_bps: float = 10.0,
    include_trades: bool = False, events: list[dict] | None = None,
) -> dict:
    if max_trades <= 0 or max_trades > 1000:
        raise ValueError("max_trades must be between 1 and 1000")
    if horizon_bars <= 0 or horizon_bars > 500:
        raise ValueError("horizon_bars must be between 1 and 500")
    if round_trip_cost_bps < 0 or round_trip_cost_bps > 1000:
        raise ValueError("round_trip_cost_bps must be between 0 and 1000")
    if events is None:
        events = generate_signal_events(bars, strategy)
    all_trades = []
    busy_until = -1
    for event in events:
        signal_idx = int(event["index"])
        entry_idx = signal_idx + 1  # next bar open: no same-bar look-ahead
        exit_idx = entry_idx + int(horizon_bars)
        if signal_idx <= busy_until or entry_idx >= len(bars) or exit_idx >= len(bars):
            continue
        entry = float(bars[entry_idx]["o"])
        exit_price = float(bars[exit_idx]["c"])
        direction = int(event["direction"])
        gross = direction * ((exit_price - entry) / entry)
        net = gross - (float(round_trip_cost_bps) / 10_000.0)
        all_trades.append({
            "signal_index": signal_idx, "entry_index": entry_idx, "exit_index": exit_idx,
            "signal_time_utc": event["time_utc"],
            "entry_time_utc": _iso(int(bars[entry_idx]["t"])),
            "exit_time_utc": _iso(int(bars[exit_idx]["t"])),
            "direction": direction,
            "condition": event["condition"],
            "entry": _round(entry), "exit": _round(exit_price),
            "gross_return_pct": _round(gross * 100, 4),
            "net_return_pct": _round(net * 100, 4),
            "reason": event["reason"],
        })
        busy_until = exit_idx
    selected = all_trades[-int(max_trades):]
    nets = [float(t["net_return_pct"]) / 100.0 for t in selected]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x < 0]
    flats = len(nets) - len(wins) - len(losses)
    decided = len(wins) + len(losses)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    curve = [{"trade": 0, "equity": 1.0, "drawdown_pct": 0.0}]
    for idx, net in enumerate(nets, 1):
        equity *= max(0.000001, 1.0 + net)
        peak = max(peak, equity)
        drawdown = (peak - equity) / peak if peak else 0.0
        max_dd = max(max_dd, drawdown)
        curve.append({"trade": idx, "equity": _round(equity, 4),
                      "drawdown_pct": _round(drawdown * 100, 4)})
    if len(curve) > 51:  # downsample to <= 51 points, always keeping the last
        step = math.ceil(len(curve) / 51)
        sampled = curve[::step]
        if sampled[-1] is not curve[-1]:
            sampled.append(curve[-1])
        curve = sampled
    long_nets = [float(t["net_return_pct"]) / 100.0 for t in selected if t["direction"] > 0]
    short_nets = [float(t["net_return_pct"]) / 100.0 for t in selected if t["direction"] < 0]

    def side_stats(values: list[float]) -> dict:
        side_wins = sum(1 for x in values if x > 0)
        side_losses = sum(1 for x in values if x < 0)
        side_decided = side_wins + side_losses
        return {"trades": len(values), "wins": side_wins, "losses": side_losses,
                "accuracy_pct": _round(100 * side_wins / side_decided, 2) if side_decided else None,
                "average_net_return_pct": _round(100 * statistics.fmean(values), 4) if values else None}

    result = {
        "strategy": strategy,
        "strategy_name": STRATEGY_ENGINES[strategy]["name"],
        "methodology": {
            "signal_timing": "Signal is known only after its bar closes.",
            "entry": "Next bar open.",
            "exit": f"Close {int(horizon_bars)} bars after entry bar.",
            "overlap": "Blocked until the prior test trade exits.",
            "costs": f"{float(round_trip_cost_bps)} bps round-trip deducted from every trade.",
            "selection": f"Most recent {int(max_trades)} completed non-overlapping signals.",
            "accuracy_definition": "Winning decided trades / (winning + losing decided trades), after costs. Flat trades excluded from accuracy.",
        },
        "candidate_signal_events": len(events),
        "completed_non_overlapping_trades_before_cap": len(all_trades),
        "signals_tested": len(selected),
        "requested_max_signals": int(max_trades),
        "exactly_requested_count": len(selected) == int(max_trades),
        "wins": len(wins), "losses": len(losses), "flats": flats,
        "accuracy_pct": _round(100 * len(wins) / decided, 2) if decided else None,
        "win_rate_including_flats_pct": _round(100 * len(wins) / len(selected), 2) if selected else None,
        "average_net_return_pct": _round(100 * statistics.fmean(nets), 4) if nets else None,
        "median_net_return_pct": _round(100 * statistics.median(nets), 4) if nets else None,
        "average_win_pct": _round(100 * statistics.fmean(wins), 4) if wins else None,
        "average_loss_pct": _round(100 * statistics.fmean(losses), 4) if losses else None,
        "expectancy_pct_per_trade": _round(100 * statistics.fmean(nets), 4) if nets else None,
        "profit_factor": _round(gross_profit / gross_loss, 4) if gross_loss > 0 else None,
        "compounded_test_equity_return_pct": _round((equity - 1) * 100, 4) if selected else None,
        "max_drawdown_pct": _round(max_dd * 100, 4),
        "best_trade_pct": _round(max(nets) * 100, 4) if nets else None,
        "worst_trade_pct": _round(min(nets) * 100, 4) if nets else None,
        "long_only": side_stats(long_nets),
        "short_only": side_stats(short_nets),
        "equity_curve": curve,
        "equity_curve_note": "Compounded test-trade equity (1.0 = start), downsampled to at most 51 points; it restates the same historical trades, not a forecast.",
        "warning": ("Historical test only. Accuracy can look attractive while expectancy is negative; "
                    "judge expectancy, drawdown, sample size, costs and out-of-sample behavior together."),
    }
    if include_trades:
        result["trades"] = selected
    else:
        result["last_10_trades"] = selected[-10:]
    return result


def _trade_stats(trades: list[dict]) -> dict:
    nets = [float(t["net_return_pct"]) / 100.0 for t in trades]
    wins = [x for x in nets if x > 0]
    losses = [x for x in nets if x < 0]
    decided = len(wins) + len(losses)
    gross_loss = abs(sum(losses))
    return {
        "trades": len(trades), "wins": len(wins), "losses": len(losses),
        "flats": len(nets) - decided,
        "accuracy_pct": _round(100 * len(wins) / decided, 2) if decided else None,
        "average_net_return_pct": _round(100 * statistics.fmean(nets), 4) if nets else None,
        "expectancy_pct_per_trade": _round(100 * statistics.fmean(nets), 4) if nets else None,
        "profit_factor": _round(sum(wins) / gross_loss, 4) if gross_loss > 0 else None,
    }


def walk_forward_split(bars: list[dict], strategy: str, *, max_signals: int = 100,
                       horizon_bars: int = 10, round_trip_cost_bps: float = 10.0,
                       in_sample_fraction: float = 0.7,
                       events: list[dict] | None = None) -> dict:
    """Chronological 70/30 split of the same tested trades: earlier vs later.

    This is a robustness sniff-test, not full walk-forward optimisation (no
    parameters are fitted anywhere in TradeAtlas). If the later slice falls
    apart while the earlier slice looked good, the historical edge is likely
    regime-specific or noise.
    """
    bt = backtest_signals(bars, strategy, max_trades=max_signals,
                          horizon_bars=horizon_bars,
                          round_trip_cost_bps=round_trip_cost_bps,
                          include_trades=True, events=events)
    trades = bt.get("trades", [])
    cut = int(len(trades) * in_sample_fraction)
    early = _trade_stats(trades[:cut])
    late = _trade_stats(trades[cut:])
    delta = None
    if early["expectancy_pct_per_trade"] is not None and late["expectancy_pct_per_trade"] is not None:
        delta = _round(late["expectancy_pct_per_trade"] - early["expectancy_pct_per_trade"], 4)
    if late["trades"] < 10:
        verdict = "insufficient_later_trades"
        note = "Fewer than 10 later-slice trades: no robustness conclusion is possible."
    elif (early["expectancy_pct_per_trade"] or 0) > 0 and (late["expectancy_pct_per_trade"] or 0) <= 0:
        verdict = "degraded_later"
        note = "Earlier slice expectancy was positive but the later slice is not — treat the headline numbers as regime-specific until proven otherwise."
    elif (late["expectancy_pct_per_trade"] or 0) > 0:
        verdict = "later_slice_positive"
        note = "The later slice is also positive after costs. That is consistency inside one history, still not a promise about the future."
    else:
        verdict = "both_slices_non_positive"
        note = "Neither slice shows positive expectancy after costs on this history."
    return {
        "method": (f"Same {len(trades)} tested trades split chronologically "
                   f"{int(in_sample_fraction * 100)}/{100 - int(in_sample_fraction * 100)}; no parameters fitted."),
        "earlier_slice": early, "later_slice": late,
        "expectancy_change_pct_points": delta,
        "robustness_verdict": verdict, "robustness_note": note,
        "warning": "A split of one history cannot prove an edge; it can only expose obvious fragility.",
    }


def strategy_tournament(bars: list[dict], *, max_signals: int = 100,
                        horizon_bars: int = 10, round_trip_cost_bps: float = 10.0) -> dict:
    """Run EVERY engine over the same bars and rank them by historical expectancy.

    Ranking history is curve-fitting bait: the top row is the engine that
    happened to fit this sample best, not a recommendation. Use it together
    with the walk-forward split and out-of-sample paper tracking.
    """
    rows = []
    for key, spec in STRATEGY_ENGINES.items():
        events = generate_signal_events(bars, key)
        bt = backtest_signals(bars, key, max_trades=max_signals,
                              horizon_bars=horizon_bars,
                              round_trip_cost_bps=round_trip_cost_bps, events=events)
        age = (len(bars) - 1 - int(events[-1]["index"])) if events else None
        latest_condition = (events[-1]["condition"] if (events and age is not None and age <= 3)
                            else "no_fresh_trigger")
        rows.append({
            "strategy": key, "strategy_name": spec["name"],
            "signals_tested": bt["signals_tested"],
            "accuracy_pct": bt["accuracy_pct"],
            "expectancy_pct_per_trade": bt["expectancy_pct_per_trade"],
            "average_net_return_pct": bt["average_net_return_pct"],
            "profit_factor": bt["profit_factor"],
            "max_drawdown_pct": bt["max_drawdown_pct"],
            "latest_condition": latest_condition,
            "last_event_bars_ago": age,
        })
    rows.sort(key=lambda r: (r["expectancy_pct_per_trade"] is not None,
                             r["expectancy_pct_per_trade"] or 0.0), reverse=True)
    for idx, row in enumerate(rows, 1):
        row["historical_rank"] = idx
    return {
        "ranked_by": "historical expectancy_pct_per_trade (descending), after the selected cost",
        "engines_tested": len(rows), "max_signals_each": int(max_signals),
        "engines": rows,
        "warning": ("The #1 row is the best fit to THIS sample and the most likely to be over-fit. "
                    "Prefer engines that also survive the walk-forward split and fresh paper tracking."),
    }


def _rolling_vol10(rets: list[float]) -> list[float | None]:
    out: list[float | None] = []
    for i in range(len(rets)):
        if i < 9:
            out.append(None)
            continue
        window = rets[i - 9:i + 1]
        mean_w = sum(window) / len(window)
        out.append((sum((x - mean_w) ** 2 for x in window) / len(window)) ** 0.5)
    return out


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(value)))


def _forecast_context(bars: list[dict]) -> dict:
    closes = [float(b["c"]) for b in bars]
    opens = [float(b["o"]) for b in bars]
    highs = [float(b["h"]) for b in bars]
    lows = [float(b["l"]) for b in bars]
    volumes = [float(b.get("v") or 0.0) for b in bars]
    rets = [0.0] + [(closes[i] / closes[i - 1] - 1.0) * 100.0 if closes[i - 1] else 0.0
                    for i in range(1, len(closes))]
    range_pct = [((highs[i] - lows[i]) / closes[i] * 100.0) if closes[i] else 0.0
                 for i in range(len(closes))]
    ctx = {"closes": closes, "opens": opens, "highs": highs, "lows": lows,
           "volumes": volumes, "range_pct": range_pct, "rets": rets,
           "rsi": rsi(closes, 14), "sma20": sma(closes, 20), "sma50": sma(closes, 50),
           "bollinger": bollinger(closes, 20, 2.0), "macd": macd(closes),
           "atr14": atr(bars, 14), "stochastic": stochastic(bars), "adx": adx(bars),
           "vol10": _rolling_vol10(rets)}
    ctx["aroon"] = aroon(bars)
    ctx["vortex"] = vortex(bars)
    ctx["fisher"] = fisher_transform(bars)
    ctx["rvi_data"] = relative_vigor_index(bars)
    ctx["kst_data"] = kst(closes)
    ctx["cmo"] = chande_momentum(closes)
    ctx["cmf"] = chaikin_money_flow(bars)
    ctx["mfi"] = money_flow_index(bars)
    ctx["stc"] = schaff_trend_cycle(closes)
    ctx["coppock"] = coppock(closes)
    ctx["force_index"] = elder_force_index(bars)
    ctx["ulcer"] = ulcer_index(closes)
    ctx["super_smoother"] = ehlers_super_smoother(closes)
    ctx["entropy"] = permutation_entropy_series(closes)
    ctx["multiscale_trend"] = multiscale_trend_scores(
        closes, returns_pct=rets, vol10=ctx["vol10"])
    ctx["cci"] = commodity_channel_index(bars)
    ctx["williams_r"] = williams_r(bars)
    ctx["tsi_data"] = true_strength_index(closes)
    ctx["trix"] = trix(closes)
    ctx["ultimate"] = ultimate_oscillator(bars)
    ctx["psar"] = parabolic_sar(bars)
    ctx["ichimoku"] = ichimoku_scores(bars)
    ctx["obv_slope"] = on_balance_volume_slope(bars)
    ctx["kalman_trend"] = kalman_trend_scores(closes)
    ctx["regression20"] = log_regression_trend_scores(closes, 20)
    ctx["regression60"] = log_regression_trend_scores(closes, 60)
    ctx["omni_oscillator"] = omni_oscillator_scores(bars)
    ctx["hull_trend"] = hull_trend_scores(bars)
    ctx["supertrend"] = supertrend(bars)
    ctx["kaufman_trend"] = kaufman_trend_scores(bars)
    ctx["haar_trend"] = haar_wavelet_trend_scores(closes, returns_pct=rets, vol10=ctx["vol10"])
    ctx["donchian_state"] = donchian_state(bars)
    ctx["aroon_score"] = [None if v is None else float(v) / 100.0
                          for v in ctx["aroon"]["oscillator"]]
    ctx["tsi_score"] = [None if a is None or b is None else math.tanh((float(a) - float(b)) / 8.0)
                        for a, b in zip(ctx["tsi_data"]["tsi"], ctx["tsi_data"]["signal"])]
    ctx["trix_score"] = [None if v is None else math.tanh(float(v) / 8.0) for v in ctx["trix"]]
    ctx["cmo_score"] = [None if v is None else float(v) / 100.0 for v in ctx["cmo"]]
    ctx["ultimate_score"] = [None if v is None else (float(v) - 50.0) / 50.0
                             for v in ctx["ultimate"]]
    ctx["rvi_score"] = [None if a is None or b is None else math.tanh((float(a) - float(b)) * 4.0)
                        for a, b in zip(ctx["rvi_data"]["rvi"], ctx["rvi_data"]["signal"])]
    ctx["regression_fusion"] = [_weighted_bounded_mean(((1.0, a), (1.0, b)))
                                for a, b in zip(ctx["regression20"], ctx["regression60"])]
    ctx["donchian_score"] = [None if v is None else float(v) for v in ctx["donchian_state"]]
    ctx["obv_score"] = [None if v is None else math.tanh(float(v) * 3.0)
                        for v in ctx["obv_slope"]]
    ctx["coppock_score"] = [None if v is None else math.tanh(float(v) / 5.0)
                            for v in ctx["coppock"]]
    ctx["pressure_wave"] = _atlas_pressure_wave_from_parts(
        opens, highs, lows, closes, volumes, ctx["atr14"], rets, ctx["vol10"])
    ctx["regime_compass"] = _atlas_regime_compass_from_parts(
        closes, ctx["multiscale_trend"], ctx["hull_trend"], ctx["adx"]["adx"],
        ctx["entropy"], ctx["bollinger"], ctx["rsi"])
    ctx["phoenix"] = _atlas_phoenix_from_parts({
        "hull": ctx["hull_trend"], "kalman": ctx["kalman_trend"],
        "kaufman": ctx["kaufman_trend"], "haar": ctx["haar_trend"],
        "multiscale": ctx["multiscale_trend"], "tsi": ctx["tsi_score"],
        "cmo": ctx["cmo_score"], "trix": ctx["trix_score"], "coppock": ctx["coppock_score"],
        "regression60": ctx["regression60"], "aroon": ctx["aroon_score"],
        "ichimoku": ctx["ichimoku"], "donchian": ctx["donchian_score"],
        "pressure": ctx["pressure_wave"], "rvi": ctx["rvi_score"], "cmf": ctx["cmf"],
        "obv": ctx["obv_score"], "compass": ctx["regime_compass"],
    })
    usable_ranges = sum(1 for i in range(len(closes)) if highs[i] > lows[i])
    nonzero_volumes = sum(1 for v in volumes if v > 0)
    ctx["candle_data"] = {
        "usable_range_share": _round(usable_ranges / len(closes), 4) if closes else 0.0,
        "nonzero_volume_share": _round(nonzero_volumes / len(closes), 4) if closes else 0.0,
        "available": bool(closes and usable_ranges / len(closes) >= 0.5),
    }
    # Precompute every feature vector once: the rolling evaluation asks for
    # ~attempts x history vectors, and recomputing them per origin was O(n^2)
    # with a heavy constant. Cache turns each lookup into a list index.
    ctx["vecs"] = [_feature_vector(ctx, i) for i in range(len(closes))]
    ctx["candle_vecs"] = [_candle_feature_vector(ctx, i) for i in range(len(closes))]
    ctx["indicator_vecs"] = [_indicator_feature_vector(ctx, i) for i in range(len(closes))]
    ctx["path_vecs"] = [_path_feature_vector(ctx, i) for i in range(len(closes))]
    ctx["cycle_vecs"] = [_cycle_flow_feature_vector(ctx, i) for i in range(len(closes))]
    ctx["indicator_data"] = {
        "available": any(v is not None for v in ctx["indicator_vecs"]),
        "min_feature_index": 60,
        "close_only_series": bool(closes and usable_ranges / len(closes) < 0.5),
        "nonzero_volume_share": _round(nonzero_volumes / len(closes), 4) if closes else 0.0,
        "note": "On close-only bars, range-based indicators collapse to functions of the "
                "close path; they do not invent highs, lows or candle anatomy.",
    }
    ctx["path_data"] = {
        "available": any(v is not None for v in ctx["path_vecs"]),
        "min_feature_index": 80,
        "close_only_series": bool(closes and usable_ranges / len(closes) < 0.5),
        "nonzero_volume_share": _round(nonzero_volumes / len(closes), 4) if closes else 0.0,
        "note": "Path geometry is computed from completed closes (and real highs/lows/volume "
                "when present). On close-only bars the range-position pieces collapse to the "
                "close path; no candle anatomy or volume is invented.",
    }
    ctx["cycle_data"] = {
        "available": any(v is not None for v in ctx["cycle_vecs"]),
        "min_feature_index": 80,
        "close_only_series": bool(closes and usable_ranges / len(closes) < 0.5),
        "nonzero_volume_share": _round(nonzero_volumes / len(closes), 4) if closes else 0.0,
        "note": "Cycle/flow coordinates use completed OHLCV only. On close-only bars, range and "
                "flow pieces collapse toward close-path/neutral values; highs, lows, volume and "
                "order flow are never invented.",
    }
    return ctx


def _feature_vector(ctx: dict, idx: int) -> list[float] | None:
    """Scaled snapshot of 'what the chart looked like' at bar `idx` (no future data)."""
    closes, rets = ctx["closes"], ctx["rets"]
    if idx < 30 or idx >= len(closes):
        return None
    c = closes[idx]
    if not c or not closes[idx - 20]:
        return None
    rsi_v = ctx["rsi"][idx]
    sma_v = ctx["sma20"][idx]
    if rsi_v is None or not sma_v:
        return None
    cached_vol = (ctx.get("vol10") or [None] * len(closes))[idx]
    if cached_vol is not None:
        vol10 = float(cached_vol)
    else:
        window = rets[idx - 9:idx + 1]
        mean_w = sum(window) / len(window)
        vol10 = (sum((x - mean_w) ** 2 for x in window) / len(window)) ** 0.5
    return [
        rets[idx] / 1.5,
        (c / closes[idx - 3] - 1.0) * 100.0 / 2.5,
        (c / closes[idx - 5] - 1.0) * 100.0 / 3.5,
        (c / closes[idx - 10] - 1.0) * 100.0 / 5.0,
        (c / closes[idx - 20] - 1.0) * 100.0 / 7.0,
        (float(rsi_v) - 50.0) / 25.0,
        (c / float(sma_v) - 1.0) * 100.0 / 4.0,
        vol10 / 1.5,
    ]


def _analog_scored(ctx: dict, origin: int, horizon: int, top_n: int) -> list[tuple[float, float]]:
    """(distance, forward %) pairs for the `top_n` nearest past setups.

    Candidates must satisfy j + horizon <= origin, so every analog outcome was
    fully known before the origin bar — the no-lookahead rule that makes the
    rolling evaluation honest.
    """
    vecs = ctx.get("vecs")
    target = vecs[origin] if vecs else _feature_vector(ctx, origin)
    if target is None:
        return []
    closes = ctx["closes"]
    scored = []
    for j in range(30, origin - horizon + 1):
        vec = vecs[j] if vecs else _feature_vector(ctx, j)
        if vec is None or not closes[j]:
            continue
        dist = sum((a - b) ** 2 for a, b in zip(vec, target)) ** 0.5
        scored.append((dist, (closes[j + horizon] / closes[j] - 1.0) * 100.0))
    scored.sort(key=lambda item: item[0])
    return scored[:top_n]


def _analog_forward_returns(ctx: dict, origin: int, horizon: int, top_n: int) -> list[float]:
    """Forward % returns of the nearest past setups (see _analog_scored)."""
    return [fwd for _, fwd in _analog_scored(ctx, origin, horizon, top_n)]



def _candle_feature_vector(ctx: dict, idx: int) -> list[float] | None:
    """Origin-time candle-structure snapshot: gap/range/body/wicks/close
    location/range expansion/relative volume. This deliberately does NOT use
    the multi-bar close-return ladder from _feature_vector, so v7 tests a
    different description of the same completed bars — still with no future.
    """
    opens, highs, lows, closes = ctx["opens"], ctx["highs"], ctx["lows"], ctx["closes"]
    volumes, range_pct = ctx["volumes"], ctx["range_pct"]
    if idx < 30 or idx >= len(closes) or not closes[idx] or not closes[idx - 1]:
        return None

    def shape(i: int) -> tuple[float, float, float, float]:
        o, h, l, c = opens[i], highs[i], lows[i], closes[i]
        span = h - l
        if span <= 0:
            return (0.0, 0.0, 0.0, 0.5)
        body = (c - o) / span
        upper = (h - max(o, c)) / span
        lower = (min(o, c) - l) / span
        close_loc = (c - l) / span
        return (body, upper, lower, close_loc)

    body, upper, lower, close_loc = shape(idx)
    last3 = [shape(i) for i in range(idx - 2, idx + 1)]
    mean_body3 = sum(x[0] for x in last3) / 3.0
    mean_close_loc3 = sum(x[3] for x in last3) / 3.0
    gap_pct = (opens[idx] / closes[idx - 1] - 1.0) * 100.0
    trailing_ranges = [x for x in range_pct[idx - 20:idx] if x > 0]
    mean_range20 = sum(trailing_ranges) / len(trailing_ranges) if trailing_ranges else 0.0
    range_expansion = (range_pct[idx] / mean_range20 - 1.0) if mean_range20 > 0 else 0.0
    trailing_volumes = [v for v in volumes[idx - 20:idx] if v > 0]
    median_volume20 = statistics.median(trailing_volumes) if trailing_volumes else 0.0
    volume_surprise = (math.log((volumes[idx] + 1.0) / (median_volume20 + 1.0))
                       if median_volume20 > 0 else 0.0)
    return [
        _clip(gap_pct, -3.0, 3.0) / 1.5,
        _clip(range_pct[idx], 0.0, 8.0) / 3.0,
        _clip(body, -1.0, 1.0) * 1.5,
        _clip(mean_body3, -1.0, 1.0) * 1.5,
        _clip(close_loc, 0.0, 1.0) * 2.0 - 1.0,
        _clip(mean_close_loc3, 0.0, 1.0) * 2.0 - 1.0,
        _clip(upper - lower, -1.0, 1.0) * 1.5,
        _clip(range_expansion, -1.0, 2.0),
        _clip(volume_surprise, -2.0, 2.0),
    ]


def _candle_analog_scored(ctx: dict, origin: int, horizon: int, top_n: int) -> list[tuple[float, float]]:
    """Nearest candle-structure neighbours under the same no-lookahead rule:
    candidate j is eligible only when j + horizon <= origin."""
    if not (ctx.get("candle_data") or {}).get("available"):
        return []
    vecs = ctx.get("candle_vecs")
    target = vecs[origin] if vecs else _candle_feature_vector(ctx, origin)
    if target is None:
        return []
    closes = ctx["closes"]
    scored = []
    for j in range(30, origin - horizon + 1):
        vec = vecs[j] if vecs else _candle_feature_vector(ctx, j)
        if vec is None or not closes[j]:
            continue
        dist = sum((a - b) ** 2 for a, b in zip(vec, target)) ** 0.5
        scored.append((dist, (closes[j + horizon] / closes[j] - 1.0) * 100.0))
    scored.sort(key=lambda item: item[0])
    return scored[:top_n]


def candle_analog_forecast(bars: list[dict], *, horizons=(1, 3, 5, 10, 20), top_n: int = 30) -> dict:
    """Latest-setup history lookup using ONLY candle structure (v7).

    Close-only series (O=H=L=C) have no candle anatomy to compare; the lab
    says so instead of pretending zero-range bars carry shape information.
    """
    if len(bars) < 120:
        return {"error": "candle analog forecast needs at least 120 bars", "bars": len(bars)}
    ctx = _forecast_context(bars)
    candle_data = ctx.get("candle_data") or {}
    if not candle_data.get("available"):
        return {"error": "candle-structure analogs unavailable: fewer than half the bars have high > low",
                "candle_data": candle_data}
    origin = len(bars) - 1
    rows = []
    for horizon in horizons:
        fwds = [fwd for _, fwd in _candle_analog_scored(ctx, origin, int(horizon), top_n)]
        rows.append({"horizon_bars": int(horizon), **_distribution(fwds)})
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "analogs_per_horizon": top_n,
        "horizons": rows,
        "candle_data": candle_data,
        "method": "candle vector per completed bar (gap, range, signed body and 3-bar body, "
                  "close location, wick balance, range expansion, relative volume); nearest "
                  "neighbours by scaled Euclidean distance; outcomes must end before origin",
        "warning": "A second conditional histogram of THIS sample, not another oracle. Judge it "
                   "only by the candle rows in the hidden-future ensemble evaluation.",
    }


INDICATOR_FEATURES = [
    "rsi14_centered", "rsi14_slope_3bar", "macd_line_atr_normalized",
    "macd_histogram_atr_normalized", "bollinger_percent_b", "bollinger_bandwidth_pct",
    "distance_to_sma20_in_atr", "distance_to_sma50_in_atr", "sma20_slope_5bar_pct",
    "donchian20_position", "stochastic_k14", "directional_balance_plus_minus_di",
    "adx14_trend_strength", "realized_volatility_vs_trailing_median_log",
    "volume_surprise_vs_20bar_median_log",
]


def _indicator_feature_vector(ctx: dict, idx: int) -> list[float] | None:
    """Origin-time indicator/regime snapshot (v8).

    This is a deliberately different coordinate system from the v4 return
    ladder and the v7 candle-shape vector: oscillator state/slope,
    MACD normalized by ATR, Bollinger position/bandwidth, moving-average
    distances in ATR units, Donchian/Stochastic position, ADX direction and
    strength, realized-volatility regime, and real volume surprise when a
    volume column exists. Every component at `idx` is computed from bars up
    to and including `idx`; there is no forward data in the vector.
    """
    closes, highs, lows, volumes = ctx["closes"], ctx["highs"], ctx["lows"], ctx["volumes"]
    if idx < 60 or idx >= len(closes) or not closes[idx]:
        return None
    c = float(closes[idx])
    rsi_v = ctx["rsi"][idx]
    rsi_3ago = ctx["rsi"][idx - 3]
    sma20_v = ctx["sma20"][idx]
    sma20_5ago = ctx["sma20"][idx - 5]
    sma50_v = ctx["sma50"][idx]
    bb = ctx.get("bollinger") or {}
    bb_mid = (bb.get("middle") or [None] * len(closes))[idx]
    bb_upper = (bb.get("upper") or [None] * len(closes))[idx]
    bb_lower = (bb.get("lower") or [None] * len(closes))[idx]
    macd_data = ctx.get("macd") or {}
    macd_line = (macd_data.get("macd") or [None] * len(closes))[idx]
    macd_hist = (macd_data.get("histogram") or [None] * len(closes))[idx]
    atr_v = (ctx.get("atr14") or [None] * len(closes))[idx]
    stoch_k = ((ctx.get("stochastic") or {}).get("k") or [None] * len(closes))[idx]
    adx_data = ctx.get("adx") or {}
    adx_v = (adx_data.get("adx") or [None] * len(closes))[idx]
    plus_di = (adx_data.get("plus_di") or [None] * len(closes))[idx]
    minus_di = (adx_data.get("minus_di") or [None] * len(closes))[idx]
    required = (rsi_v, rsi_3ago, sma20_v, sma20_5ago, sma50_v, bb_mid, bb_upper,
                bb_lower, macd_line, macd_hist, stoch_k, adx_v, plus_di, minus_di)
    if any(v is None for v in required) or not sma20_5ago or not bb_mid:
        return None
    atr_scale = float(atr_v) if atr_v and float(atr_v) > 0 else max(c * 0.01, 1e-9)
    bb_range = float(bb_upper) - float(bb_lower)
    pct_b = ((c - float(bb_lower)) / bb_range) if bb_range > 0 else 0.5
    bandwidth_pct = (bb_range / float(bb_mid) * 100.0) if bb_mid else 0.0
    high20 = max(highs[idx - 19:idx + 1])
    low20 = min(lows[idx - 19:idx + 1])
    donchian_pos = ((c - low20) / (high20 - low20)) if high20 > low20 else 0.5
    vol_values = [v for v in ctx["vol10"][max(0, idx - 99):idx + 1] if v is not None]
    vol_now = ctx["vol10"][idx]
    if vol_values and vol_now is not None:
        trailing_med_vol = statistics.median(vol_values)
        vol_regime = math.log((float(vol_now) + 1e-9) / (float(trailing_med_vol) + 1e-9))
    else:
        vol_regime = 0.0
    trailing_volumes = [v for v in volumes[idx - 20:idx] if v > 0]
    median_volume20 = statistics.median(trailing_volumes) if trailing_volumes else 0.0
    volume_surprise = (math.log((float(volumes[idx]) + 1.0) / (median_volume20 + 1.0))
                       if median_volume20 > 0 else 0.0)
    return [
        _clip((float(rsi_v) - 50.0) / 25.0, -2.0, 2.0),
        _clip((float(rsi_v) - float(rsi_3ago)) / 15.0, -2.0, 2.0),
        _clip(float(macd_line) / atr_scale, -3.0, 3.0),
        _clip(float(macd_hist) / atr_scale, -2.0, 2.0) * 1.25,
        _clip((pct_b - 0.5) * 2.0, -2.0, 2.0),
        _clip(bandwidth_pct / 8.0, 0.0, 2.0),
        _clip((c - float(sma20_v)) / atr_scale, -3.0, 3.0),
        _clip((c - float(sma50_v)) / atr_scale, -4.0, 4.0) / 1.5,
        _clip(((float(sma20_v) / float(sma20_5ago) - 1.0) * 100.0) / 2.0, -2.0, 2.0),
        _clip((donchian_pos - 0.5) * 2.0, -1.0, 1.0) * 1.5,
        _clip((float(stoch_k) - 50.0) / 50.0, -1.0, 1.0) * 1.25,
        _clip((float(plus_di) - float(minus_di)) / 25.0, -2.0, 2.0),
        _clip(float(adx_v) / 50.0, 0.0, 2.0),
        _clip(vol_regime, -1.5, 1.5),
        _clip(volume_surprise, -2.0, 2.0),
    ]


def _indicator_analog_scored(ctx: dict, origin: int, horizon: int, top_n: int) -> list[tuple[float, float]]:
    """Nearest indicator-regime neighbours under j + horizon <= origin."""
    vecs = ctx.get("indicator_vecs")
    target = vecs[origin] if vecs else _indicator_feature_vector(ctx, origin)
    if target is None:
        return []
    closes = ctx["closes"]
    scored = []
    for j in range(60, origin - horizon + 1):
        vec = vecs[j] if vecs else _indicator_feature_vector(ctx, j)
        if vec is None or not closes[j]:
            continue
        dist = sum((a - b) ** 2 for a, b in zip(vec, target)) ** 0.5
        scored.append((dist, (closes[j + horizon] / closes[j] - 1.0) * 100.0))
    scored.sort(key=lambda item: item[0])
    return scored[:top_n]


def indicator_analog_forecast(bars: list[dict], *, horizons=(1, 3, 5, 10, 20), top_n: int = 30) -> dict:
    """Latest-setup history lookup in indicator/regime coordinates (v8)."""
    if len(bars) < 120:
        return {"error": "indicator analog forecast needs at least 120 bars", "bars": len(bars)}
    ctx = _forecast_context(bars)
    origin = len(bars) - 1
    if _indicator_feature_vector(ctx, origin) is None:
        return {"error": "indicator analog forecast unavailable: latest bar lacks a complete "
                         "60-bar indicator warm-up", "indicator_data": ctx.get("indicator_data") or {}}
    rows = []
    for horizon in horizons:
        fwds = [fwd for _, fwd in _indicator_analog_scored(ctx, origin, int(horizon), top_n)]
        rows.append({"horizon_bars": int(horizon), **_distribution(fwds)})
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "analogs_per_horizon": top_n,
        "horizons": rows,
        "indicator_data": ctx.get("indicator_data") or {},
        "feature_set": INDICATOR_FEATURES,
        "method": "15 origin-time indicator/regime features per completed bar (RSI level/slope, "
                  "ATR-normalized MACD, Bollinger %B/bandwidth, SMA distances/slope, Donchian and "
                  "Stochastic position, ADX direction/strength, volatility regime and volume "
                  "surprise); nearest neighbours by scaled Euclidean distance; candidate outcomes "
                  "must end on or before the origin",
        "warning": "Another conditional histogram of THIS sample, not a third independent oracle: "
                   "indicators are transformations of the same price path and are often correlated. "
                   "Believe only the blind ensemble rows beside it.",
    }


PATH_FEATURES = [
    "efficiency_ratio_20_signed", "efficiency_ratio_60_signed",
    "log_trend_slope_20_vol_normalized", "log_trend_slope_60_vol_normalized",
    "variance_ratio_5_log", "lag1_autocorrelation_30", "realized_skew_20",
    "downside_variance_share_20", "drawdown_from_60bar_high_pct",
    "runup_from_60bar_low_pct", "range_position_60", "max_drawdown_20_pct",
    "volatility_ratio_10_to_60_log", "signed_return_streak",
    "up_down_volume_balance_20", "range_compression_10_to_60_log",
]


def _path_mean_sd(values: list[float]) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    mean_v = sum(values) / len(values)
    var_v = sum((x - mean_v) ** 2 for x in values) / len(values)
    return (mean_v, var_v ** 0.5)


def _path_log_slope(values: list[float]) -> float:
    """Least-squares slope of log(price) per bar over one completed window."""
    if len(values) < 3 or any(v <= 0 for v in values):
        return 0.0
    ys = [math.log(v) for v in values]
    n = len(ys)
    x_mean = (n - 1) / 2.0
    y_mean = sum(ys) / n
    denom = sum((i - x_mean) ** 2 for i in range(n))
    if denom <= 0:
        return 0.0
    return sum((i - x_mean) * (y - y_mean) for i, y in enumerate(ys)) / denom


def _path_feature_vector(ctx: dict, idx: int) -> list[float] | None:
    """Origin-time path-geometry snapshot (v9).

    A fourth coordinate system, distinct from the close-return ladder,
    candle anatomy and indicator state: how efficiently price travelled,
    whether its variance scales like trend or chop, autocorrelation/skew,
    where it sits inside its own 60-bar excursion, how deep the latest
    drawdown was, volatility compression, sign streaks and real up/down
    volume balance. Every window ends at `idx`; nothing after `idx` enters.
    """
    closes, highs, lows, volumes = ctx["closes"], ctx["highs"], ctx["lows"], ctx["volumes"]
    rets, range_pct = ctx["rets"], ctx["range_pct"]
    if idx < 80 or idx >= len(closes) or not closes[idx] or not closes[idx - 60]:
        return None
    c = float(closes[idx])

    def efficiency(window: int) -> float:
        net = (c / float(closes[idx - window]) - 1.0) * 100.0 if closes[idx - window] else 0.0
        travelled = sum(abs(float(x)) for x in rets[idx - window + 1:idx + 1])
        return _clip(net / travelled, -1.0, 1.0) if travelled > 0 else 0.0

    rets20 = [float(x) for x in rets[idx - 19:idx + 1]]
    rets60 = [float(x) for x in rets[idx - 59:idx + 1]]
    _m20, sd20 = _path_mean_sd(rets20)
    _m60, sd60 = _path_mean_sd(rets60)
    slope20 = _path_log_slope([float(x) for x in closes[idx - 19:idx + 1]]) * 100.0
    slope60 = _path_log_slope([float(x) for x in closes[idx - 59:idx + 1]]) * 100.0
    slope20_scaled = slope20 * (20.0 ** 0.5) / sd20 if sd20 > 0 else 0.0
    slope60_scaled = slope60 * (60.0 ** 0.5) / sd60 if sd60 > 0 else 0.0

    five_bar = []
    for end in range(idx - 55, idx + 1, 5):
        if closes[end - 5]:
            five_bar.append((float(closes[end]) / float(closes[end - 5]) - 1.0) * 100.0)
    _m1, sd1_60 = _path_mean_sd(rets60)
    _m5, sd5 = _path_mean_sd(five_bar)
    variance_ratio = (sd5 ** 2) / (5.0 * sd1_60 ** 2) if sd1_60 > 0 and sd5 > 0 else 1.0
    vr_log = math.log(max(variance_ratio, 1e-9))

    lag_x = [float(x) for x in rets[idx - 29:idx]]
    lag_y = [float(x) for x in rets[idx - 28:idx + 1]]
    mx, sdx = _path_mean_sd(lag_x)
    my, sdy = _path_mean_sd(lag_y)
    autocorr = (sum((x - mx) * (y - my) for x, y in zip(lag_x, lag_y)) / len(lag_x) / (sdx * sdy)
                if lag_x and sdx > 0 and sdy > 0 else 0.0)
    skew = (sum(((x - _m20) / sd20) ** 3 for x in rets20) / len(rets20) if sd20 > 0 else 0.0)
    downside_share = (sum(min(x, 0.0) ** 2 for x in rets20) / sum(x * x for x in rets20)
                      if sum(x * x for x in rets20) > 0 else 0.5)

    high60 = max(float(x) for x in highs[idx - 59:idx + 1])
    low60 = min(float(x) for x in lows[idx - 59:idx + 1])
    drawdown60 = (c / high60 - 1.0) * 100.0 if high60 > 0 else 0.0
    runup60 = (c / low60 - 1.0) * 100.0 if low60 > 0 else 0.0
    range_pos60 = (c - low60) / (high60 - low60) if high60 > low60 else 0.5

    peak = float(closes[idx - 19])
    max_dd20 = 0.0
    for value in closes[idx - 19:idx + 1]:
        peak = max(peak, float(value))
        if peak > 0:
            max_dd20 = max(max_dd20, (peak - float(value)) / peak * 100.0)

    _m10, sd10 = _path_mean_sd([float(x) for x in rets[idx - 9:idx + 1]])
    vol_ratio_log = math.log((sd10 + 1e-9) / (sd60 + 1e-9)) if sd60 > 0 else 0.0

    streak = 0
    if rets[idx] > 0:
        while streak < 10 and idx - streak >= 0 and rets[idx - streak] > 0:
            streak += 1
    elif rets[idx] < 0:
        while streak > -10 and idx + streak >= 0 and rets[idx + streak] < 0:
            streak -= 1

    vol_window = [float(v) for v in volumes[idx - 19:idx + 1]]
    ret_window = [float(x) for x in rets[idx - 19:idx + 1]]
    total_vol = sum(vol_window)
    volume_balance = (sum((1.0 if x > 0 else -1.0 if x < 0 else 0.0) * v
                          for x, v in zip(ret_window, vol_window)) / total_vol
                      if total_vol > 0 else 0.0)

    ranges10 = [float(x) for x in range_pct[idx - 9:idx + 1] if x > 0]
    ranges60 = [float(x) for x in range_pct[idx - 59:idx + 1] if x > 0]
    range_compression = (math.log((statistics.median(ranges10) + 1e-9) /
                                   (statistics.median(ranges60) + 1e-9))
                         if ranges10 and ranges60 else 0.0)

    return [
        efficiency(20) * 1.5,
        efficiency(60) * 1.5,
        _clip(slope20_scaled, -3.0, 3.0),
        _clip(slope60_scaled, -3.0, 3.0),
        _clip(vr_log, -1.5, 1.5),
        _clip(autocorr, -1.0, 1.0) * 1.5,
        _clip(skew, -2.0, 2.0),
        _clip((downside_share - 0.5) * 2.0, -1.0, 1.0) * 1.5,
        _clip(drawdown60 / 5.0, -3.0, 0.0),
        _clip(runup60 / 5.0, 0.0, 3.0),
        _clip((range_pos60 - 0.5) * 2.0, -1.0, 1.0) * 1.5,
        _clip(max_dd20 / 5.0, 0.0, 3.0),
        _clip(vol_ratio_log, -1.5, 1.5),
        _clip(streak / 5.0, -2.0, 2.0),
        _clip(volume_balance, -1.0, 1.0) * 1.5,
        _clip(range_compression, -1.5, 1.5),
    ]


def _path_analog_scored(ctx: dict, origin: int, horizon: int, top_n: int) -> list[tuple[float, float]]:
    """Nearest path-geometry neighbours under j + horizon <= origin."""
    vecs = ctx.get("path_vecs")
    target = vecs[origin] if vecs else _path_feature_vector(ctx, origin)
    if target is None:
        return []
    closes = ctx["closes"]
    scored = []
    for j in range(80, origin - horizon + 1):
        vec = vecs[j] if vecs else _path_feature_vector(ctx, j)
        if vec is None or not closes[j]:
            continue
        dist = sum((a - b) ** 2 for a, b in zip(vec, target)) ** 0.5
        scored.append((dist, (closes[j + horizon] / closes[j] - 1.0) * 100.0))
    scored.sort(key=lambda item: item[0])
    return scored[:top_n]


def path_analog_forecast(bars: list[dict], *, horizons=(1, 3, 5, 10, 20), top_n: int = 30) -> dict:
    """Latest-setup history lookup in path-geometry coordinates (v9)."""
    if len(bars) < 120:
        return {"error": "path analog forecast needs at least 120 bars", "bars": len(bars)}
    ctx = _forecast_context(bars)
    origin = len(bars) - 1
    if _path_feature_vector(ctx, origin) is None:
        return {"error": "path analog forecast unavailable: latest bar lacks the 80-bar path warm-up",
                "path_data": ctx.get("path_data") or {}}
    rows = []
    for horizon in horizons:
        fwds = [fwd for _, fwd in _path_analog_scored(ctx, origin, int(horizon), top_n)]
        rows.append({"horizon_bars": int(horizon), **_distribution(fwds)})
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "analogs_per_horizon": top_n,
        "horizons": rows,
        "path_data": ctx.get("path_data") or {},
        "feature_set": PATH_FEATURES,
        "method": "16 origin-time path-geometry features per completed bar (20/60-bar travel "
                  "efficiency, volatility-normalized log-trend slopes, 5-bar variance ratio, "
                  "lag-1 autocorrelation, skew/downside share, 60-bar drawdown/run-up/range "
                  "position, 20-bar max drawdown, volatility and range compression, sign streak "
                  "and real up/down volume balance); nearest neighbours by scaled Euclidean "
                  "distance; candidate outcomes must end on or before the origin",
        "warning": "A fourth conditional histogram of THIS sample, not a fourth oracle: path "
                   "geometry re-describes the same completed bars. Only the blind race and "
                   "after-cost rows beside it say whether the description helped here.",
    }


CYCLE_FLOW_FEATURES = [
    "aroon_oscillator_25", "vortex_balance_14", "chande_momentum_14",
    "fisher_transform_10", "relative_vigor_index_10", "schaff_trend_cycle",
    "kst_volatility_normalized", "coppock_volatility_normalized",
    "chaikin_money_flow_20", "money_flow_index_14",
    "elder_force_index_atr_volume_normalized", "rolling_vwap_distance_atr_20",
    "ulcer_index_14", "ehlers_super_smoother_slope_atr",
    "permutation_entropy_order_score", "signed_path_pressure_index_20",
    "entropy_weighted_multiscale_trend", "overnight_to_intraday_volatility_log_20",
]


def _cycle_flow_feature_vector(ctx: dict, idx: int) -> list[float] | None:
    """Origin-time cycle/flow snapshot (v10).

    A fifth coordinate system built from cycle, flow and pressure tools that
    the earlier families do not use in this form: Aroon, Vortex, CMO, Fisher,
    RVI, Schaff, KST, Coppock, CMF/MFI, Force Index, rolling VWAP distance,
    Ulcer, SuperSmoother slope, permutation entropy, overnight/intraday
    volatility balance, plus two explicitly TradeAtlas-invented composites —
    Signed Path Pressure and Entropy-Weighted Multiscale Trend. All windows
    end at idx.
    """
    closes, opens, highs, lows, volumes = (ctx["closes"], ctx["opens"], ctx["highs"],
                                           ctx["lows"], ctx["volumes"])
    if idx < 80 or idx >= len(closes) or not closes[idx]:
        return None
    def at(name, key=None):
        data = ctx.get(name)
        if key is not None:
            data = (data or {}).get(key)
        return data[idx] if isinstance(data, list) and idx < len(data) else None

    aroon_v = at("aroon", "oscillator")
    vortex_plus = at("vortex", "plus")
    vortex_minus = at("vortex", "minus")
    cmo_v = at("cmo")
    fisher_v = at("fisher", "fisher")
    rvi_v = at("rvi_data", "rvi")
    stc_v = at("stc")
    kst_v = at("kst_data", "kst")
    coppock_v = at("coppock")
    cmf_v = at("cmf")
    mfi_v = at("mfi")
    force_v = at("force_index")
    ulcer_v = at("ulcer")
    smoother = ctx.get("super_smoother") or []
    entropy_v = at("entropy")
    multiscale_v = at("multiscale_trend")
    atr_v = at("atr14")
    vol10_v = at("vol10")
    required = (aroon_v, vortex_plus, vortex_minus, cmo_v, fisher_v, rvi_v, stc_v,
                kst_v, coppock_v, cmf_v, mfi_v, ulcer_v, entropy_v, multiscale_v)
    if any(v is None for v in required) or idx < 3 or idx >= len(smoother):
        return None
    c = float(closes[idx])
    atr_scale = float(atr_v) if atr_v and float(atr_v) > 0 else max(c * 0.01, 1e-9)
    vol_scale = float(vol10_v) if vol10_v and float(vol10_v) > 0 else 1.0

    typical = [(float(highs[j]) + float(lows[j]) + float(closes[j])) / 3.0
               for j in range(idx - 19, idx + 1)]
    vol_window = [float(v) for v in volumes[idx - 19:idx + 1]]
    total_volume = sum(vol_window)
    rolling_vwap = (sum(price * volume for price, volume in zip(typical, vol_window)) / total_volume
                    if total_volume > 0 else sum(typical) / len(typical))
    median_volume = statistics.median([v for v in volumes[idx - 20:idx] if v > 0]) \
        if any(v > 0 for v in volumes[idx - 20:idx]) else 0.0
    force_norm = (float(force_v) / (atr_scale * median_volume)
                  if force_v is not None and median_volume > 0 else 0.0)

    pressure_total = 0.0
    for j in range(idx - 19, idx + 1):
        span = float(highs[j]) - float(lows[j])
        if span > 0:
            signed_location = (2.0 * float(closes[j]) - float(highs[j]) - float(lows[j])) / span
            magnitude = span / atr_scale
        else:
            move = float(closes[j]) - float(closes[j - 1]) if j > 0 else 0.0
            signed_location = 1.0 if move > 0 else -1.0 if move < 0 else 0.0
            magnitude = abs(move) / atr_scale
        volume_factor = 1.0
        if median_volume > 0 and volumes[j] > 0:
            volume_factor = _clip(math.sqrt(float(volumes[j]) / median_volume), 0.25, 2.0)
        pressure_total += signed_location * magnitude * volume_factor
    signed_path_pressure = pressure_total / math.sqrt(20.0)

    close_only = bool((ctx.get("candle_data") or {}).get("available") is False)
    if close_only:
        overnight_intraday = 0.0
    else:
        overnight = []
        intraday = []
        for j in range(idx - 19, idx + 1):
            if closes[j - 1] and opens[j]:
                overnight.append(math.log(float(opens[j]) / float(closes[j - 1])))
                intraday.append(math.log(float(closes[j]) / float(opens[j])))
        def _sd(vals):
            if len(vals) < 2:
                return 0.0
            mean = sum(vals) / len(vals)
            return (sum((x - mean) ** 2 for x in vals) / len(vals)) ** 0.5
        overnight_intraday = math.log((_sd(overnight) + 1e-6) / (_sd(intraday) + 1e-6))

    entropy = float(entropy_v)
    multiscale = float(multiscale_v)
    return [
        _clip(float(aroon_v) / 50.0, -2.0, 2.0),
        _clip((float(vortex_plus) - float(vortex_minus)) * 5.0, -2.0, 2.0),
        _clip(float(cmo_v) / 50.0, -2.0, 2.0),
        _clip(float(fisher_v), -3.0, 3.0),
        _clip(float(rvi_v) * 2.0, -2.0, 2.0),
        _clip((float(stc_v) - 50.0) / 25.0, -2.0, 2.0),
        _clip(float(kst_v) / max(10.0 * vol_scale, 1.0), -3.0, 3.0),
        _clip(float(coppock_v) / max(5.0 * vol_scale, 1.0), -3.0, 3.0),
        _clip(float(cmf_v) * 2.0, -2.0, 2.0),
        _clip((float(mfi_v) - 50.0) / 25.0, -2.0, 2.0),
        _clip(force_norm, -3.0, 3.0),
        _clip((c - rolling_vwap) / atr_scale, -3.0, 3.0),
        _clip(float(ulcer_v) / 5.0, 0.0, 3.0),
        _clip((float(smoother[idx]) - float(smoother[idx - 3])) / atr_scale, -3.0, 3.0),
        _clip((0.75 - entropy) * 4.0, -2.0, 2.0),
        _clip(signed_path_pressure, -3.0, 3.0),
        _clip(multiscale * (1.0 - entropy) * 3.0, -2.0, 2.0),
        _clip(overnight_intraday, -2.0, 2.0),
    ]


def _cycle_flow_analog_scored(ctx: dict, origin: int, horizon: int, top_n: int) -> list[tuple[float, float]]:
    """Nearest cycle/flow neighbours under j + horizon <= origin."""
    vecs = ctx.get("cycle_vecs")
    target = vecs[origin] if vecs else _cycle_flow_feature_vector(ctx, origin)
    if target is None:
        return []
    closes = ctx["closes"]
    scored = []
    for j in range(80, origin - horizon + 1):
        vec = vecs[j] if vecs else _cycle_flow_feature_vector(ctx, j)
        if vec is None or not closes[j]:
            continue
        dist = sum((a - b) ** 2 for a, b in zip(vec, target)) ** 0.5
        scored.append((dist, (closes[j + horizon] / closes[j] - 1.0) * 100.0))
    scored.sort(key=lambda item: item[0])
    return scored[:top_n]


def cycle_flow_analog_forecast(bars: list[dict], *, horizons=(1, 3, 5, 10, 20), top_n: int = 30) -> dict:
    """Latest-setup history lookup in cycle/flow coordinates (v10)."""
    if len(bars) < 120:
        return {"error": "cycle/flow analog forecast needs at least 120 bars", "bars": len(bars)}
    ctx = _forecast_context(bars)
    origin = len(bars) - 1
    if _cycle_flow_feature_vector(ctx, origin) is None:
        return {"error": "cycle/flow analog forecast unavailable: latest bar lacks the 80-bar warm-up",
                "cycle_data": ctx.get("cycle_data") or {}}
    rows = []
    for horizon in horizons:
        fwds = [fwd for _, fwd in _cycle_flow_analog_scored(ctx, origin, int(horizon), top_n)]
        rows.append({"horizon_bars": int(horizon), **_distribution(fwds)})
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "analogs_per_horizon": top_n,
        "horizons": rows,
        "cycle_data": ctx.get("cycle_data") or {},
        "feature_set": CYCLE_FLOW_FEATURES,
        "method": "18 origin-time cycle/flow features (Aroon, Vortex, CMO, Fisher, RVI, Schaff, "
                  "KST, Coppock, CMF/MFI, Force Index, rolling VWAP distance, Ulcer, SuperSmoother "
                  "slope, permutation entropy, Signed Path Pressure, Entropy-Weighted Multiscale "
                  "Trend and overnight/intraday volatility balance); nearest neighbours by scaled "
                  "Euclidean distance; candidate outcomes must end on or before the origin",
        "warning": "A fifth conditional histogram of the same completed bars, not five independent "
                   "sources of information. Flow formulas here are OHLCV proxies, not exchange order flow.",
    }


RANK_FUSION_FAMILIES = [
    ("vecs", "return_shape"), ("candle_vecs", "candle_structure"),
    ("indicator_vecs", "indicator_regime"), ("path_vecs", "path_geometry"),
    ("cycle_vecs", "cycle_flow"),
]


def _rank_fusion_analog_scored(ctx: dict, origin: int, horizon: int,
                               top_n: int) -> list[tuple[float, float]]:
    """Multi-view neighbours: average each candidate's distance rank across families.

    A candidate must have a feature vector in every family available at the
    origin, and its outcome must end by the origin (`j + horizon <= origin`).
    The returned "distance" is mean normalized rank (0 is closest), which
    puts incompatible feature scales on one common footing.
    """
    closes = ctx["closes"]
    families: list[tuple[list, str]] = []
    for key, label in RANK_FUSION_FAMILIES:
        vecs = ctx.get(key) or []
        if origin < len(vecs) and vecs[origin] is not None:
            families.append((vecs, label))
    if not families or origin - int(horizon) < 80:
        return []
    candidates = [
        j for j in range(80, origin - int(horizon) + 1)
        if closes[j] and all(j < len(vecs) and vecs[j] is not None for vecs, _ in families)
    ]
    if len(candidates) < 10:
        return []
    rank_parts: dict[int, list[float]] = {j: [] for j in candidates}
    denominator = max(1, len(candidates) - 1)
    for vecs, _label in families:
        target = vecs[origin]
        ordered = sorted(
            (sum((float(a) - float(b)) ** 2 for a, b in zip(vecs[j], target)) ** 0.5, j)
            for j in candidates)
        for rank, (_distance, j) in enumerate(ordered):
            rank_parts[j].append(rank / denominator)
    ranked = sorted(
        candidates,
        key=lambda j: sum(rank_parts[j]) / len(rank_parts[j]))[:int(top_n)]
    return [
        (sum(rank_parts[j]) / len(rank_parts[j]),
         (closes[j + int(horizon)] / closes[j] - 1.0) * 100.0)
        for j in ranked
    ]


def rank_fusion_analog_forecast(bars: list[dict], *, horizons=(1, 3, 5, 10, 20),
                                top_n: int = 30) -> dict:
    """Latest setup lookup using rank fusion across all five analog families."""
    if len(bars) < 120:
        return {"error": "rank-fusion analog forecast needs at least 120 bars", "bars": len(bars)}
    ctx = _forecast_context(bars)
    origin = len(bars) - 1
    available = [label for key, label in RANK_FUSION_FAMILIES
                 if (ctx.get(key) or [None] * (origin + 1))[origin] is not None]
    rows = []
    for horizon in horizons:
        fwds = [fwd for _, fwd in _rank_fusion_analog_scored(ctx, origin, int(horizon), top_n)]
        rows.append({"horizon_bars": int(horizon), **_distribution(fwds)})
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "analogs_per_horizon": top_n,
        "horizons": rows,
        "families_used": available,
        "method": "For every admissible past candidate, average its distance rank across the "
                  "return/candle/indicator/path/cycle-flow views; take the lowest mean-rank "
                  "neighbours. Candidate outcomes must end on or before the origin.",
        "warning": "Rank fusion cannot create new information: all views are transformations of "
                   "the same completed bars. The blind race and costs decide whether it helped.",
    }


def kalman_trend_now(bars: list[dict]) -> dict:
    bars = normalize_bars(bars)
    closes = [float(b["c"]) for b in bars]
    scores = kalman_trend_scores(closes)
    if not scores or scores[-1] is None:
        return {"error": "Kalman trend needs at least one valid close", "bars": len(bars)}
    score = float(scores[-1])
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "score": _round(score, 4),
        "mechanical_direction": "positive" if score > 0 else "negative" if score < 0 else "flat",
        "method": "Causal alpha-beta local-linear trend on log price (level gain 0.35, "
                  "slope gain 0.08); score=tanh(100*slope per bar).",
        "warning": "A local trend descriptor, not a probability or trade instruction.",
    }


def hull_trend_now(bars: list[dict]) -> dict:
    bars = normalize_bars(bars)
    scores = hull_trend_scores(bars)
    if not scores or scores[-1] is None:
        return {"error": "Hull trend needs more warm-up bars", "bars": len(bars)}
    score = float(scores[-1])
    return {"as_of_bar": _iso(int(bars[-1]["t"])), "score": _round(score, 4),
            "mechanical_direction": "positive" if score > 0 else "negative" if score < 0 else "flat",
            "method": "Hull MA(20) price distance plus 3-bar Hull slope, ATR-normalized and tanh-bounded.",
            "warning": "A trend descriptor, not a probability or trade instruction."}


def _bounded_score_now(name: str, bars: list[dict], scores, method: str) -> dict:
    if not scores or scores[-1] is None:
        return {"error": f"{name} needs more warm-up bars", "bars": len(bars)}
    score = float(scores[-1])
    return {"as_of_bar": _iso(int(bars[-1]["t"])), "score": _round(score, 4),
            "mechanical_direction": "positive" if score > 0 else "negative" if score < 0 else "flat",
            "method": method,
            "warning": "A bounded origin-time research score, not a probability or trade instruction."}


def atlas_pressure_wave_now(bars: list[dict]) -> dict:
    bars = normalize_bars(bars)
    return _bounded_score_now(
        "Atlas Pressure Wave", bars, atlas_pressure_wave_scores(bars),
        "15-bar exponentially weighted candle close/body pressure scaled by ATR range and real "
        "relative volume, fused with 3/10-bar volatility-normalized momentum.")


def atlas_regime_compass_now(bars: list[dict]) -> dict:
    bars = normalize_bars(bars)
    return _bounded_score_now(
        "Atlas Regime Compass", bars, atlas_regime_compass_scores(bars),
        "ADX and permutation entropy smoothly choose between Hull/multiscale trend evidence "
        "and Bollinger/RSI range-reversion evidence.")


def atlas_phoenix_now(bars: list[dict]) -> dict:
    bars = normalize_bars(bars)
    return _bounded_score_now(
        "Atlas Phoenix Fusion", bars, atlas_phoenix_scores(bars),
        "Family-balanced fusion (trend filters 25%, momentum 25%, structure 20%, flow 20%, "
        "Regime Compass 10%); each family is averaged before fusion.")


def omni_direct_now(bars: list[dict], *, horizon: int = 5) -> dict:
    bars = normalize_bars(bars)
    closes = [float(b["c"]) for b in bars]
    scores = omni_direct_scores(bars, horizon=horizon)
    if not scores or scores[-1] is None:
        return {"error": "omni direct score needs more warm-up bars", "bars": len(bars)}
    multiscale = multiscale_trend_scores(closes)
    kalman = kalman_trend_scores(closes)
    matched = horizon_matched_trend_scores(closes, horizon)
    sar = parabolic_sar(bars)
    oscillator = omni_oscillator_scores(bars)
    score = float(scores[-1])
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "horizon_bars": int(horizon),
        "score": _round(score, 4),
        "mechanical_direction": "positive" if score > 0 else "negative" if score < 0 else "flat",
        "components": {
            "multiscale_trend": _round(multiscale[-1], 4),
            "kalman_trend": _round(kalman[-1], 4),
            "horizon_matched_trend": _round(matched[-1], 4),
            "parabolic_sar_trend": sar["trend"][-1],
            "oscillator_basket": _round(oscillator[-1], 4),
        },
        "weights": {"multiscale_trend": 1.2, "kalman_trend": 0.9,
                    "horizon_matched_trend": 0.7, "parabolic_sar_trend": 0.5,
                    "oscillator_basket": 0.5},
        "method": "Fixed weighted average of available bounded direct components; not fitted to this symbol.",
        "warning": "A consensus score, not a probability and not a trade instruction.",
    }



def multiscale_trend_now(bars: list[dict]) -> dict:
    """Latest multiscale trend score with every horizon contribution exposed."""
    bars = normalize_bars(bars)
    closes = [float(b["c"]) for b in bars]
    rets = [0.0] + [(closes[i] / closes[i - 1] - 1.0) * 100.0 if closes[i - 1] else 0.0
                    for i in range(1, len(closes))]
    vol10 = _rolling_vol10(rets)
    scores = multiscale_trend_scores(closes, returns_pct=rets, vol10=vol10)
    idx = len(closes) - 1
    score = scores[idx] if scores else None
    if score is None:
        return {"error": "multiscale trend needs at least 21 bars and measurable 10-bar volatility",
                "bars": len(bars)}
    sd = float(vol10[idx] or 0.0)
    contributions = []
    for w in (3, 5, 10, 20, 60, 120):
        if idx - w < 0 or not closes[idx - w] or sd <= 0:
            contributions.append({"window_bars": w, "available": False})
            continue
        ret = (closes[idx] / closes[idx - w] - 1.0) * 100.0
        contributions.append({
            "window_bars": w, "available": True, "return_pct": _round(ret, 3),
            "volatility_normalized": _round(ret / (sd * math.sqrt(w)), 4),
            "tanh_contribution": _round(math.tanh(ret / (sd * math.sqrt(w))), 4),
        })
    entropy = permutation_entropy_at(closes)
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "score": _round(score, 4),
        "mechanical_direction": "positive" if score > 0 else "negative" if score < 0 else "flat",
        "contributions": contributions,
        "permutation_entropy": _round(entropy, 4),
        "entropy_weighted_score": _round(
            None if entropy is None else float(score) * (1.0 - float(entropy)), 4),
        "method": "Average of tanh(return/(10-bar volatility*sqrt(window))) over available "
                  "3/5/10/20/60/120-bar windows (at least four required). Origin-time only.",
        "warning": "A bounded trend descriptor, not a probability and not a trade instruction. "
                   "Its worth is decided only by the hidden-future rows.",
    }



def _distribution(values: list[float]) -> dict:
    if not values:
        return {"n": 0}
    ordered = sorted(values)
    n = len(ordered)
    def pct(p: float) -> float:
        return ordered[min(n - 1, max(0, int(p * n)))]
    return {
        "n": n,
        "median_pct": _round(ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2, 3),
        "p25_pct": _round(pct(0.25), 3), "p75_pct": _round(pct(0.75), 3),
        "share_up_pct": _round(100.0 * sum(1 for v in values if v > 0) / n, 1),
        "worst_pct": _round(ordered[0], 3), "best_pct": _round(ordered[-1], 3),
    }


def analog_forecast(bars: list[dict], *, horizons=(1, 3, 5, 10, 20), top_n: int = 30) -> dict:
    """What actually happened after the most similar past setups to the LATEST bar.

    This is a conditional history lookup, not a prediction: it reports the
    distribution of real forward returns that followed look-alike setups in
    the supplied bars, with the sample size attached so thin evidence looks thin.
    """
    if len(bars) < 120:
        return {"error": "analog forecast needs at least 120 bars", "bars": len(bars)}
    ctx = _forecast_context(bars)
    origin = len(bars) - 1
    rows = []
    for horizon in horizons:
        dist = _distribution(_analog_forward_returns(ctx, origin, int(horizon), top_n))
        rows.append({"horizon_bars": int(horizon), **dist})
    return {
        "as_of_bar": _iso(int(bars[-1]["t"])),
        "analogs_per_horizon": top_n,
        "horizons": rows,
        "method": "feature vector per bar (1/3/5/10/20-bar returns, RSI-14, distance to SMA-20, "
                  "10-bar volatility), nearest neighbours by scaled Euclidean distance; analog "
                  "outcomes must end before the origin bar (no lookahead)",
        "warning": "A histogram of what followed similar setups in THIS sample — not a price "
                   "forecast, not a probability about the future, and worthless without the "
                   "out-of-sample evaluation next to it.",
    }


def rolling_forecast_eval(bars: list[dict], *, attempts: int = 100, horizon: int = 5,
                          top_n: int = 30, min_history: int = 200) -> dict:
    """Out-of-sample test: hide the future, forecast, then check — `attempts` times.

    Each origin uses only bars before it (analogs must also resolve before the
    origin). Direction accuracy is reported against three naive baselines so a
    coin-flip-grade forecaster is labelled as one.
    """
    n_bars = len(bars)
    last_origin = n_bars - 1 - horizon
    if last_origin - min_history < 10:
        return {"error": f"needs at least {min_history + horizon + 10} bars for a rolling "
                         f"evaluation with min_history={min_history}, horizon={horizon}",
                "bars": n_bars}
    ctx = _forecast_context(bars)
    closes = ctx["closes"]
    span = last_origin - min_history
    step = max(1, span // max(1, attempts))
    origins = list(range(min_history, last_origin + 1, step))[-attempts:]
    analog_hits = up_hits = mom_hits = rev_hits = 0
    brier_terms, outcomes = [], []
    regimes: dict[str, list[int]] = {}
    made = 0
    for origin in origins:
        fwds = _analog_forward_returns(ctx, origin, horizon, top_n)
        if len(fwds) < 10 or not closes[origin]:
            continue
        actual = (closes[origin + horizon] / closes[origin] - 1.0) * 100.0
        dist = _distribution(fwds)
        median = float(dist["median_pct"])
        share_up = float(dist["share_up_pct"]) / 100.0
        made += 1
        outcomes.append(1 if actual > 0 else 0)
        analog_hits += 1 if (median > 0) == (actual > 0) and median != 0 else 0
        up_hits += 1 if actual > 0 else 0
        mom = closes[origin] / closes[origin - 5] - 1.0 if closes[origin - 5] else 0.0
        mom_hits += 1 if (mom > 0) == (actual > 0) and mom != 0 else 0
        rev_hits += 1 if (mom < 0) == (actual > 0) and mom != 0 else 0
        brier_terms.append((share_up - (1 if actual > 0 else 0)) ** 2)
        # Regime buckets use ONLY data available at the origin: trend vs the
        # causal SMA-20, volatility vs its own trailing-100-bar median.
        hit_a = 1 if (median > 0) == (actual > 0) and median != 0 else 0
        hit_u = 1 if actual > 0 else 0
        sma_v = ctx["sma20"][origin]
        trend = ("above_sma20" if sma_v and closes[origin] > float(sma_v)
                 else "below_sma20")
        trail = [v for v in ctx["vol10"][max(0, origin - 100):origin + 1] if v is not None]
        vol_now = ctx["vol10"][origin]
        vol_regime = ("high_vol" if (vol_now is not None and trail
                      and vol_now > statistics.median(trail)) else "low_vol")
        for bucket in (trend, vol_regime):
            slot = regimes.setdefault(bucket, [0, 0, 0])
            slot[0] += 1
            slot[1] += hit_a
            slot[2] += hit_u
    if made < 10:
        return {"error": "too few evaluable origins with enough analogs", "attempts_made": made}
    def rate(hits: int) -> float:
        return _round(100.0 * hits / made, 1)
    brier = sum(brier_terms) / made
    clim_p = sum(outcomes) / made
    brier_clim = sum((clim_p - o) ** 2 for o in outcomes) / made
    skill = (1.0 - brier / brier_clim) if brier_clim > 0 else 0.0
    analog_rate = rate(analog_hits)
    best_baseline = max(rate(up_hits), rate(mom_hits), rate(rev_hits))
    return {
        "attempts_requested": attempts, "attempts_made": made,
        "horizon_bars": horizon, "analogs_per_forecast": top_n,
        "origin_step_bars": step,
        "analog_direction_accuracy_pct": analog_rate,
        "baseline_always_up_pct": rate(up_hits),
        "baseline_momentum_5bar_pct": rate(mom_hits),
        "baseline_mean_reversion_5bar_pct": rate(rev_hits),
        "brier_score_analog": _round(brier, 4),
        "brier_skill_vs_climatology": _round(skill, 4),
        "verdict": ("analog_beat_baselines_on_this_sample"
                    if analog_rate > best_baseline and skill > 0
                    else "no_edge_over_baselines_on_this_sample"),
        "regimes": {
            bucket: {"attempts": n,
                     "analog_accuracy_pct": _round(100.0 * a / n, 1) if n else None,
                     "always_up_pct": _round(100.0 * u / n, 1) if n else None}
            for bucket, (n, a, u) in sorted(regimes.items())
        },
        "regime_note": "Buckets use only origin-time information (price vs causal SMA-20; "
                       "10-bar volatility vs its trailing-100-bar median). Small buckets are "
                       "noise with labels — compare against always-up inside the same bucket.",
        "honesty_notes": [
            "Out-of-sample by construction: analogs and their outcomes all predate each origin.",
            "Origins may overlap in time, so attempts are not fully independent — treat the "
            "accuracy gap, not the third decimal, as the signal.",
            "One symbol and one era prove nothing about other symbols, eras or the future; "
            "re-run per series and distrust any single-sample 'edge'.",
            "Direction accuracy ignores magnitude, costs and risk: a 55% direction rate can "
            "still lose money after spreads, fees and tails.",
        ],
    }


def ensemble_forecast_eval(bars: list[dict], *, attempts: int = 100, horizon: int = 5,
                           top_n: int = 30, min_history: int = 200,
                           cost_levels_bps=(10, 25)) -> dict:
    """Classic + modern forecast variants, same hidden-future discipline.

    Variants per origin (all origin-time information only):
      * analog_median      — v4 method (median of nearest analogs)
      * analog_weighted    — distance-weighted analog vote (nearer = louder)
      * momentum_5bar      — the classic naive baseline, kept as a contestant
      * majority_vote      — weighted-analog + momentum + RSI-trend votes
      * candle_analog_median / candle_analog_weighted — v7 candle-structure
        neighbours (gap/range/body/wicks/close location/volume surprise)
      * majority_vote_v2   — prior majority inputs plus the candle vote
      * indicator_analog_median / indicator_analog_weighted — v8 classic/modern
        indicator-regime neighbours (RSI/MACD/Bollinger/SMA/Donchian/Stochastic/
        ADX/volatility/volume, all known at the origin)
      * majority_vote_v3   — v2 inputs plus the indicator-regime vote
      * path_analog_median / path_analog_weighted — v9 path-geometry neighbours
        (travel efficiency, trend slopes, variance ratio, autocorrelation,
        skew, excursion/drawdown position, volatility compression, streaks and
        real up/down volume balance)
      * majority_vote_v4   — available v3 inputs plus the path-geometry vote
      * cycle_flow_analog_median / cycle_flow_analog_weighted — v10 cycle/flow
        neighbours (Aroon/Vortex/Fisher/Schaff/KST/Coppock/CMF/MFI/Force/VWAP/
        Ulcer/SuperSmoother/entropy/path-pressure/volatility balance)
      * multiscale_trend   — v10 direct classic contestant: volatility-normalized
        3/5/10/20/60/120-bar time-series momentum on one tanh scale
      * majority_vote_v5   — available prior family votes plus cycle/flow and
        multiscale trend
      * adaptive_selector  — v9 causal meta-method: after each candidate has
        20 fully REVEALED prior attempts (an old attempt counts only when
        old_origin + horizon <= current origin), follow the candidate with the
        best shrunken revealed hit rate; before that, fall back to majority_v5
      * consensus_3plus    — speaks only when at least three of the available
        return/momentum/candle/indicator family votes point the same way
        (accuracy always printed with coverage)
      * agreement_only     — trade only when weighted-analog and momentum agree
                             (accuracy reported WITH its coverage, always)
    Then the part direction accuracy hides: the same calls are re-scored as
    trades after round-trip costs, next to a plain always-long position.
    """
    n_bars = len(bars)
    last_origin = n_bars - 1 - horizon
    if last_origin - min_history < 10:
        return {"error": f"needs at least {min_history + horizon + 10} bars for an ensemble "
                         f"evaluation with min_history={min_history}, horizon={horizon}",
                "bars": n_bars}
    ctx = _forecast_context(bars)
    closes = ctx["closes"]
    kalman_scores = ctx.get("kalman_trend") or kalman_trend_scores(closes)
    omni_scores = omni_direct_scores(bars, horizon=horizon)
    hull_scores = ctx.get("hull_trend") or hull_trend_scores(bars)
    supertrend_states = (ctx.get("supertrend") or supertrend(bars)).get("trend") or []
    kaufman_scores = ctx.get("kaufman_trend") or kaufman_trend_scores(bars)
    haar_scores = ctx.get("haar_trend") or haar_wavelet_trend_scores(closes)
    v13_arrays = {
        "aroon_trend": ctx.get("aroon_score") or aroon_trend_scores(bars),
        "tsi_momentum": ctx.get("tsi_score") or tsi_momentum_scores(closes),
        "trix_momentum": ctx.get("trix_score") or trix_momentum_scores(closes),
        "cmo_momentum": ctx.get("cmo_score") or chande_momentum_scores(closes),
        "ultimate_trend": ctx.get("ultimate_score") or ultimate_oscillator_scores(bars),
        "rvi_trend": ctx.get("rvi_score") or rvi_trend_scores(bars),
        "regression_trend": ctx.get("regression_fusion") or regression_fusion_scores(closes),
        "donchian_trend": ctx.get("donchian_score") or donchian_trend_scores(bars),
        "obv_flow_trend": ctx.get("obv_score") or obv_flow_scores(bars),
        "coppock_trend": ctx.get("coppock_score") or coppock_trend_scores(closes),
        "atlas_pressure_wave": ctx.get("pressure_wave") or atlas_pressure_wave_scores(bars),
        "atlas_regime_compass": ctx.get("regime_compass") or atlas_regime_compass_scores(bars),
        "atlas_phoenix_fusion": ctx.get("phoenix") or atlas_phoenix_scores(bars),
    }
    meta_candidates = (
        "analog_weighted", "path_analog_weighted", "cycle_flow_analog_weighted",
        "rank_fusion_analog_weighted", "multiscale_trend", "kalman_trend",
        "omni_direct_consensus", "hull_trend", "kaufman_trend", "atlas_fusion_v12",
        "majority_vote_v7", "tsi_momentum", "ultimate_trend", "atlas_pressure_wave",
        "atlas_regime_compass", "atlas_phoenix_fusion")
    meta_weights = {m: 1.0 for m in meta_candidates}
    meta_pending: list[tuple[int, dict, float]] = []
    meta_revealed_attempts = 0
    logistic_feature_names = (
        "multiscale_trend", "hull_trend", "kalman_trend", "kaufman_trend",
        "haar_wavelet_trend", "regression_trend", "atlas_pressure_wave",
        "atlas_regime_compass", "atlas_phoenix_fusion", "ultimate_trend",
        "analog_weighted_share", "path_weighted_share", "cycle_weighted_share",
        "rank_weighted_share", "rsi_centered")
    logistic_weights = [0.0] * len(logistic_feature_names)
    logistic_bias = 0.0
    logistic_pending: list[tuple[int, list[float], float]] = []
    logistic_revealed_attempts = 0
    markov_pending: list[tuple[int, tuple[int, int, int], float]] = []
    markov_states: dict[tuple[int, int, int], list[float]] = {}
    span = last_origin - min_history
    step = max(1, span // max(1, attempts))
    origins = list(range(min_history, last_origin + 1, step))[-attempts:]
    methods = ("analog_median", "analog_weighted", "momentum_5bar", "majority_vote",
               "candle_analog_median", "candle_analog_weighted", "majority_vote_v2",
               "indicator_analog_median", "indicator_analog_weighted", "majority_vote_v3",
               "path_analog_median", "path_analog_weighted", "majority_vote_v4",
               "cycle_flow_analog_median", "cycle_flow_analog_weighted",
               "multiscale_trend", "majority_vote_v5",
               "kalman_trend", "omni_direct_consensus",
               "rank_fusion_analog_median", "rank_fusion_analog_weighted",
               "majority_vote_v6", "hull_trend", "supertrend_trend",
               "kaufman_trend", "haar_wavelet_trend", "markov_regime",
               "atlas_fusion_v12", "majority_vote_v7",
               "aroon_trend", "tsi_momentum", "trix_momentum", "cmo_momentum",
               "ultimate_trend", "rvi_trend", "regression_trend", "donchian_trend",
               "obv_flow_trend", "coppock_trend", "atlas_pressure_wave",
               "atlas_regime_compass", "atlas_phoenix_fusion", "majority_vote_v8",
               "atlas_meta_hedge", "atlas_online_logistic", "adaptive_selector")
    selector_candidates = tuple(m for m in methods if m != "adaptive_selector")
    selector_stats = {m: [0, 0] for m in selector_candidates}  # revealed attempts, hits
    selector_pending: list[tuple[int, dict, float]] = []
    selector_choices = {m: 0 for m in selector_candidates}
    selector_log: list[dict] = []
    selector_fallback_attempts = 0
    hits = {m: 0 for m in methods}
    method_made = {m: 0 for m in methods}
    made = 0
    agree_made = agree_hits = 0
    consensus_made = consensus_hits = 0
    trade_log: dict[str, list[float]] = {m: [] for m in methods + ("agreement_only", "consensus_3plus", "always_up_long")}
    multiscale_confidence_samples: list[tuple[float, float, bool]] = []  # abs(score), signed actual %, hit
    for origin in origins:
        scored = _analog_scored(ctx, origin, horizon, top_n)
        if len(scored) < 10 or not closes[origin]:
            continue
        fwds = [f for _, f in scored]
        dist = _distribution(fwds)
        median = float(dist["median_pct"])
        weights = [1.0 / (d + 0.05) for d, _ in scored]
        w_share = (sum(w for w, (_, f) in zip(weights, scored) if f > 0) / sum(weights)
                   if weights else 0.5)
        actual = (closes[origin + horizon] / closes[origin] - 1.0) * 100.0
        mom = closes[origin] / closes[origin - 5] - 1.0 if closes[origin - 5] else 0.0
        rsi_v = ctx["rsi"][origin]
        rsi_sign = 1 if (rsi_v or 50) >= 50 else -1
        votes = {
            "analog_median": 1 if median > 0 else -1,
            "analog_weighted": 1 if w_share >= 0.5 else -1,
            "momentum_5bar": 1 if mom > 0 else -1,
        }
        votes["majority_vote"] = (1 if (votes["analog_weighted"] + votes["momentum_5bar"]
                                        + rsi_sign) >= 0 else -1)
        candle_scored = _candle_analog_scored(ctx, origin, horizon, top_n)
        if len(candle_scored) >= 10:
            candle_fwds = [f for _, f in candle_scored]
            candle_median = float(_distribution(candle_fwds)["median_pct"])
            candle_weights = [1.0 / (d + 0.05) for d, _ in candle_scored]
            candle_w_share = (sum(w for w, (_, f) in zip(candle_weights, candle_scored) if f > 0)
                              / sum(candle_weights) if candle_weights else 0.5)
            votes["candle_analog_median"] = 1 if candle_median > 0 else -1
            votes["candle_analog_weighted"] = 1 if candle_w_share >= 0.5 else -1
            combo = (votes["analog_weighted"] + votes["momentum_5bar"] + rsi_sign
                     + votes["candle_analog_weighted"])
            votes["majority_vote_v2"] = (1 if combo > 0 else -1 if combo < 0
                                         else votes["momentum_5bar"])
        candle_vote = votes.get("candle_analog_weighted")
        indicator_scored = _indicator_analog_scored(ctx, origin, horizon, top_n)
        indicator_vote = None
        if len(indicator_scored) >= 10:
            indicator_fwds = [f for _, f in indicator_scored]
            indicator_median = float(_distribution(indicator_fwds)["median_pct"])
            indicator_weights = [1.0 / (d + 0.05) for d, _ in indicator_scored]
            indicator_w_share = (sum(w for w, (_, f) in zip(indicator_weights, indicator_scored) if f > 0)
                                 / sum(indicator_weights) if indicator_weights else 0.5)
            votes["indicator_analog_median"] = 1 if indicator_median > 0 else -1
            votes["indicator_analog_weighted"] = 1 if indicator_w_share >= 0.5 else -1
            indicator_vote = votes["indicator_analog_weighted"]
            combo_v3_inputs = [votes["analog_weighted"], votes["momentum_5bar"], rsi_sign, indicator_vote]
            if candle_vote is not None:
                combo_v3_inputs.append(candle_vote)
            combo_v3 = sum(combo_v3_inputs)
            votes["majority_vote_v3"] = (1 if combo_v3 > 0 else -1 if combo_v3 < 0
                                         else indicator_vote)
        path_scored = _path_analog_scored(ctx, origin, horizon, top_n)
        path_vote = None
        path_w_share = None
        if len(path_scored) >= 10:
            path_fwds = [f for _, f in path_scored]
            path_median = float(_distribution(path_fwds)["median_pct"])
            path_weights = [1.0 / (d + 0.05) for d, _ in path_scored]
            path_w_share = (sum(w for w, (_, f) in zip(path_weights, path_scored) if f > 0)
                            / sum(path_weights) if path_weights else 0.5)
            votes["path_analog_median"] = 1 if path_median > 0 else -1
            votes["path_analog_weighted"] = 1 if path_w_share >= 0.5 else -1
            path_vote = votes["path_analog_weighted"]
            combo_v4_inputs = [votes["analog_weighted"], votes["momentum_5bar"], rsi_sign, path_vote]
            if candle_vote is not None:
                combo_v4_inputs.append(candle_vote)
            if indicator_vote is not None:
                combo_v4_inputs.append(indicator_vote)
            combo_v4 = sum(combo_v4_inputs)
            votes["majority_vote_v4"] = (1 if combo_v4 > 0 else -1 if combo_v4 < 0
                                         else path_vote)
        cycle_scored = _cycle_flow_analog_scored(ctx, origin, horizon, top_n)
        cycle_vote = None
        cycle_w_share = None
        if len(cycle_scored) >= 10:
            cycle_fwds = [f for _, f in cycle_scored]
            cycle_median = float(_distribution(cycle_fwds)["median_pct"])
            cycle_weights = [1.0 / (d + 0.05) for d, _ in cycle_scored]
            cycle_w_share = (sum(w for w, (_, f) in zip(cycle_weights, cycle_scored) if f > 0)
                             / sum(cycle_weights) if cycle_weights else 0.5)
            votes["cycle_flow_analog_median"] = 1 if cycle_median > 0 else -1
            votes["cycle_flow_analog_weighted"] = 1 if cycle_w_share >= 0.5 else -1
            cycle_vote = votes["cycle_flow_analog_weighted"]
        multiscale_score = (ctx.get("multiscale_trend") or [None] * len(closes))[origin]
        multiscale_vote = None
        if multiscale_score is not None:
            multiscale_vote = 1 if float(multiscale_score) > 0 else -1
            votes["multiscale_trend"] = multiscale_vote
            multiscale_confidence_samples.append((
                abs(float(multiscale_score)), float(multiscale_vote * actual),
                bool((multiscale_vote > 0) == (actual > 0) and actual != 0)))
        if cycle_vote is not None or multiscale_vote is not None:
            combo_v5_inputs = [votes["analog_weighted"], votes["momentum_5bar"], rsi_sign]
            for extra_vote in (candle_vote, indicator_vote, path_vote, cycle_vote, multiscale_vote):
                if extra_vote is not None:
                    combo_v5_inputs.append(extra_vote)
            combo_v5 = sum(combo_v5_inputs)
            tie_vote = multiscale_vote if multiscale_vote is not None else (
                cycle_vote if cycle_vote is not None else votes["momentum_5bar"])
            votes["majority_vote_v5"] = (1 if combo_v5 > 0 else -1 if combo_v5 < 0 else tie_vote)
        kalman_score = kalman_scores[origin] if origin < len(kalman_scores) else None
        kalman_vote = None
        if kalman_score is not None:
            kalman_vote = 1 if float(kalman_score) > 0 else -1
            votes["kalman_trend"] = kalman_vote
        omni_score = omni_scores[origin] if origin < len(omni_scores) else None
        omni_vote = None
        if omni_score is not None:
            omni_vote = 1 if float(omni_score) > 0 else -1
            votes["omni_direct_consensus"] = omni_vote
        rank_scored = _rank_fusion_analog_scored(ctx, origin, horizon, top_n)
        rank_vote = None
        rank_w_share = None
        if len(rank_scored) >= 10:
            rank_fwds = [f for _, f in rank_scored]
            rank_median = float(_distribution(rank_fwds)["median_pct"])
            rank_weights = [1.0 / (d + 0.02) for d, _ in rank_scored]
            rank_w_share = (sum(w for w, (_, f) in zip(rank_weights, rank_scored) if f > 0)
                            / sum(rank_weights) if rank_weights else 0.5)
            votes["rank_fusion_analog_median"] = 1 if rank_median > 0 else -1
            votes["rank_fusion_analog_weighted"] = 1 if rank_w_share >= 0.5 else -1
            rank_vote = votes["rank_fusion_analog_weighted"]
        if kalman_vote is not None or omni_vote is not None or rank_vote is not None:
            combo_v6_inputs = [votes["analog_weighted"], votes["momentum_5bar"], rsi_sign]
            for extra_vote in (candle_vote, indicator_vote, path_vote, cycle_vote,
                               multiscale_vote, kalman_vote, omni_vote, rank_vote):
                if extra_vote is not None:
                    combo_v6_inputs.append(extra_vote)
            combo_v6 = sum(combo_v6_inputs)
            tie_v6 = next((v for v in (omni_vote, kalman_vote, multiscale_vote)
                           if v is not None), votes["momentum_5bar"])
            votes["majority_vote_v6"] = (1 if combo_v6 > 0 else -1 if combo_v6 < 0 else tie_v6)
        hull_vote = None
        if origin < len(hull_scores) and hull_scores[origin] is not None:
            hull_vote = 1 if float(hull_scores[origin]) > 0 else -1
            votes["hull_trend"] = hull_vote
        supertrend_vote = None
        if origin < len(supertrend_states):
            supertrend_vote = 1 if int(supertrend_states[origin]) > 0 else -1
            votes["supertrend_trend"] = supertrend_vote
        kaufman_vote = None
        if origin < len(kaufman_scores) and kaufman_scores[origin] is not None:
            kaufman_vote = 1 if float(kaufman_scores[origin]) > 0 else -1
            votes["kaufman_trend"] = kaufman_vote
        haar_vote = None
        if origin < len(haar_scores) and haar_scores[origin] is not None:
            haar_vote = 1 if float(haar_scores[origin]) > 0 else -1
            votes["haar_wavelet_trend"] = haar_vote
        while markov_pending and markov_pending[0][0] <= origin:
            _reveal, old_state, old_actual = markov_pending.pop(0)
            markov_states.setdefault(old_state, []).append(old_actual)
        vol_trail = [v for v in ctx["vol10"][max(0, origin - 99):origin + 1] if v is not None]
        high_vol_state = 1 if (ctx["vol10"][origin] is not None and vol_trail
                               and float(ctx["vol10"][origin]) > statistics.median(vol_trail)) else 0
        markov_state = (
            1 if multiscale_vote is not None and multiscale_vote > 0 else -1,
            high_vol_state,
            1 if (ctx["rsi"][origin] or 50) >= 50 else -1,
        )
        state_outcomes = markov_states.get(markov_state, [])
        markov_vote = (1 if sum(state_outcomes) / len(state_outcomes) > 0 else -1) if len(state_outcomes) >= 10 else multiscale_vote
        if markov_vote is not None:
            votes["markov_regime"] = markov_vote
        markov_pending.append((origin + horizon, markov_state, float(actual)))
        atlas_inputs = [v for v in (hull_vote, kalman_vote, markov_vote, omni_vote, multiscale_vote) if v is not None]
        atlas_vote = None
        if atlas_inputs:
            atlas_sum = sum(atlas_inputs)
            atlas_vote = 1 if atlas_sum > 0 else -1 if atlas_sum < 0 else (kalman_vote or multiscale_vote or votes["momentum_5bar"])
            votes["atlas_fusion_v12"] = atlas_vote
        combo_v7_inputs = [votes["analog_weighted"], votes["momentum_5bar"], rsi_sign]
        for extra_vote in (candle_vote, indicator_vote, path_vote, cycle_vote, multiscale_vote,
                           kalman_vote, omni_vote, rank_vote, hull_vote, supertrend_vote,
                           kaufman_vote, haar_vote, markov_vote):
            if extra_vote is not None:
                combo_v7_inputs.append(extra_vote)
        combo_v7 = sum(combo_v7_inputs)
        votes["majority_vote_v7"] = (1 if combo_v7 > 0 else -1 if combo_v7 < 0
                                     else (atlas_vote or kalman_vote or votes["momentum_5bar"]))
        v13_votes: dict[str, int] = {}
        for v13_method, v13_scores_array in v13_arrays.items():
            if origin < len(v13_scores_array) and v13_scores_array[origin] is not None:
                v13_votes[v13_method] = 1 if float(v13_scores_array[origin]) > 0 else -1
                votes[v13_method] = v13_votes[v13_method]
        combo_v8_inputs = [votes["analog_weighted"], votes["momentum_5bar"], rsi_sign]
        for extra_vote in (candle_vote, indicator_vote, path_vote, cycle_vote, multiscale_vote,
                           kalman_vote, omni_vote, rank_vote, hull_vote, supertrend_vote,
                           kaufman_vote, haar_vote, markov_vote):
            if extra_vote is not None:
                combo_v8_inputs.append(extra_vote)
        combo_v8_inputs.extend(v13_votes.values())
        combo_v8 = sum(combo_v8_inputs)
        votes["majority_vote_v8"] = (
            1 if combo_v8 > 0 else -1 if combo_v8 < 0
            else v13_votes.get("atlas_phoenix_fusion",
                               v13_votes.get("atlas_pressure_wave",
                                             atlas_vote or votes["momentum_5bar"])))
        # Atlas Meta Hedge: exponential weights learn ONLY from attempts whose
        # outcome window has ended by this origin (reveal index <= origin).
        while meta_pending and meta_pending[0][0] <= origin:
            _reveal_at, old_meta_votes, old_meta_actual = meta_pending.pop(0)
            meta_revealed_attempts += 1
            for candidate, old_sign in old_meta_votes.items():
                meta_hit = (old_sign > 0) == (old_meta_actual > 0) and old_meta_actual != 0
                meta_weights[candidate] *= math.exp(0.15 if meta_hit else -0.15)
            weight_scale = sum(meta_weights.values()) / len(meta_weights)
            if weight_scale > 0:
                meta_weights = {m: w / weight_scale for m, w in meta_weights.items()}
        meta_current = {m: votes[m] for m in meta_candidates if m in votes}
        meta_denominator = sum(meta_weights[m] for m in meta_current)
        meta_score = (sum(meta_weights[m] * sign for m, sign in meta_current.items())
                      / meta_denominator if meta_denominator > 0 else 0.0)
        votes["atlas_meta_hedge"] = (
            1 if meta_score > 0 else -1 if meta_score < 0
            else v13_votes.get("atlas_phoenix_fusion",
                               votes.get("atlas_fusion_v12", votes["momentum_5bar"])))
        meta_pending.append((origin + horizon, dict(meta_current), float(actual)))
        # Atlas Online Logistic: one regularized SGD update per revealed label.
        logistic_raw = {
            "multiscale_trend": multiscale_score,
            "hull_trend": hull_scores[origin] if origin < len(hull_scores) else None,
            "kalman_trend": kalman_score,
            "kaufman_trend": kaufman_scores[origin] if origin < len(kaufman_scores) else None,
            "haar_wavelet_trend": haar_scores[origin] if origin < len(haar_scores) else None,
            "regression_trend": (v13_arrays["regression_trend"][origin]
                                 if origin < len(v13_arrays["regression_trend"]) else None),
            "atlas_pressure_wave": (v13_arrays["atlas_pressure_wave"][origin]
                                    if origin < len(v13_arrays["atlas_pressure_wave"]) else None),
            "atlas_regime_compass": (v13_arrays["atlas_regime_compass"][origin]
                                     if origin < len(v13_arrays["atlas_regime_compass"]) else None),
            "atlas_phoenix_fusion": (v13_arrays["atlas_phoenix_fusion"][origin]
                                     if origin < len(v13_arrays["atlas_phoenix_fusion"]) else None),
            "ultimate_trend": (v13_arrays["ultimate_trend"][origin]
                               if origin < len(v13_arrays["ultimate_trend"]) else None),
            "analog_weighted_share": 2.0 * float(w_share) - 1.0,
            "path_weighted_share": None if path_w_share is None else 2.0 * float(path_w_share) - 1.0,
            "cycle_weighted_share": None if cycle_w_share is None else 2.0 * float(cycle_w_share) - 1.0,
            "rank_weighted_share": None if rank_w_share is None else 2.0 * float(rank_w_share) - 1.0,
            "rsi_centered": ((float(rsi_v) if rsi_v is not None else 50.0) - 50.0) / 25.0,
        }
        logistic_features = [
            0.0 if logistic_raw[name] is None else max(-1.0, min(1.0, float(logistic_raw[name])))
            for name in logistic_feature_names]
        while logistic_pending and logistic_pending[0][0] <= origin:
            _reveal_at, old_features, old_logistic_actual = logistic_pending.pop(0)
            logistic_revealed_attempts += 1
            target = 1.0 if old_logistic_actual > 0 else 0.0
            old_z = logistic_bias + sum(w * x for w, x in zip(logistic_weights, old_features))
            old_p = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, old_z))))
            logistic_error = target - old_p
            for j in range(len(logistic_weights)):
                logistic_weights[j] += 0.08 * (logistic_error * old_features[j]
                                               - 0.002 * logistic_weights[j])
            logistic_bias += 0.08 * logistic_error
        logistic_z = logistic_bias + sum(w * x for w, x in zip(logistic_weights, logistic_features))
        votes["atlas_online_logistic"] = 1 if logistic_z >= 0 else -1
        logistic_pending.append((origin + horizon, list(logistic_features), float(actual)))
        # Reveal only attempts whose outcome window has fully ended by NOW.
        while selector_pending and selector_pending[0][0] <= origin:
            _reveal_at, old_votes, old_actual = selector_pending.pop(0)
            for candidate, old_sign in old_votes.items():
                selector_stats[candidate][0] += 1
                if (old_sign > 0) == (old_actual > 0) and old_actual != 0:
                    selector_stats[candidate][1] += 1
        eligible = [m for m in selector_candidates
                    if m in votes and selector_stats[m][0] >= 20]
        if eligible:
            chosen = eligible[0]
            best_score = -1.0
            for candidate in eligible:
                revealed, revealed_hits = selector_stats[candidate]
                # Ten 50/50 pseudo-attempts shrink small samples toward a coin.
                score = (revealed_hits + 5.0) / (revealed + 10.0)
                if score > best_score + 1e-12:
                    best_score = score
                    chosen = candidate
            used_fallback = False
        else:
            chosen = next((m for m in ("majority_vote_v8", "majority_vote_v7", "majority_vote_v6", "majority_vote_v5", "majority_vote_v4", "majority_vote_v3",
                                       "majority_vote_v2", "majority_vote",
                                       "momentum_5bar") if m in votes),
                          "analog_weighted")
            used_fallback = True
            selector_fallback_attempts += 1
        votes["adaptive_selector"] = votes[chosen]
        selector_choices[chosen] = selector_choices.get(chosen, 0) + 1
        try:
            origin_time = _iso(int(bars[origin]["t"]))
        except Exception:
            origin_time = None
        selector_log.append({
            "origin_index": int(origin), "origin_time": origin_time,
            "chosen_method": chosen, "used_fallback": used_fallback,
            "revealed_attempts_for_chosen": int(selector_stats[chosen][0]),
            "eligible_methods": list(eligible),
        })
        selector_pending.append((origin + horizon,
                                 {m: votes[m] for m in selector_candidates if m in votes},
                                 float(actual)))
        family_votes = [votes["analog_weighted"], votes["momentum_5bar"]]
        if candle_vote is not None:
            family_votes.append(candle_vote)
        if indicator_vote is not None:
            family_votes.append(indicator_vote)
        consensus_sign = None
        if len(family_votes) >= 3:
            family_sum = sum(family_votes)
            if family_sum >= 3:
                consensus_sign = 1
            elif family_sum <= -3:
                consensus_sign = -1
        made += 1
        for name, sign in votes.items():
            method_made[name] += 1
            if (sign > 0) == (actual > 0) and actual != 0:
                hits[name] += 1
            trade_log[name].append(sign * actual)
        trade_log["always_up_long"].append(actual)
        if consensus_sign is not None:
            consensus_made += 1
            if (consensus_sign > 0) == (actual > 0) and actual != 0:
                consensus_hits += 1
            trade_log["consensus_3plus"].append(consensus_sign * actual)
        if votes["analog_weighted"] == votes["momentum_5bar"]:
            agree_made += 1
            sign = votes["analog_weighted"]
            if (sign > 0) == (actual > 0) and actual != 0:
                agree_hits += 1
            trade_log["agreement_only"].append(sign * actual)
    if made < 10:
        return {"error": "too few evaluable origins with enough analogs", "attempts_made": made}
    accuracy = {m: (_round(100.0 * hits[m] / method_made[m], 1)
                    if method_made[m] >= 10 else None) for m in methods}
    accuracy["agreement_only"] = (_round(100.0 * agree_hits / agree_made, 1)
                                  if agree_made >= 10 else None)
    accuracy["consensus_3plus"] = (_round(100.0 * consensus_hits / consensus_made, 1)
                                   if consensus_made >= 10 else None)
    cost_rows = []
    for bps in cost_levels_bps:
        cost_pct = float(bps) / 100.0
        row = {"round_trip_cost_bps": int(bps)}
        for name, trades in trade_log.items():
            if not trades:
                row[name] = None
                continue
            net = [t - cost_pct for t in trades]
            row[name] = {
                "trades": len(net),
                "win_rate_after_cost_pct": _round(100.0 * sum(1 for x in net if x > 0) / len(net), 1),
                "mean_net_pct_per_trade": _round(sum(net) / len(net), 3),
                "total_net_pct_overlapping_sum": _round(sum(net), 1),
            }
        cost_rows.append(row)
    confidence_rows = []
    for threshold in (0.3, 0.5, 0.7):
        selected = [row for row in multiscale_confidence_samples if row[0] >= threshold]
        selected_hits = sum(1 for _score, _ret, hit in selected if hit)
        confidence_rows.append({
            "absolute_score_at_least": threshold,
            "attempts": len(selected),
            "coverage_pct": _round(100.0 * len(selected) / made, 1) if made else 0.0,
            "direction_accuracy_pct": (_round(100.0 * selected_hits / len(selected), 1)
                                       if len(selected) >= 10 else None),
            "mean_net_pct_per_trade_10bps": (_round(
                sum(ret - 0.10 for _score, ret, _hit in selected) / len(selected), 3)
                if selected else None),
            "mean_net_pct_per_trade_25bps": (_round(
                sum(ret - 0.25 for _score, ret, _hit in selected) / len(selected), 3)
                if selected else None),
        })
    # The "best" label is reserved for methods that actually faced the full
    # test. Coverage-limited subsets (agreement_only, consensus_3plus) are
    # reported beside it, but a high rate on a small self-selected slice must
    # never be crowned as the race winner.
    scored_methods = {k: accuracy[k] for k in methods
                      if accuracy[k] is not None and method_made[k] >= 10}
    best_method = max(scored_methods, key=scored_methods.get) if scored_methods else None
    return {
        "attempts_made": made,
        "horizon_bars": horizon,
        "direction_accuracy_pct": accuracy,
        "method_attempts": method_made,
        "candle_data": ctx.get("candle_data") or {},
        "candle_feature_set": ["gap_pct", "range_pct", "signed_body", "mean_body_3bar",
                               "close_location", "mean_close_location_3bar", "wick_balance",
                               "range_expansion_vs_20bar", "volume_surprise_vs_20bar_median"],
        "agreement_coverage_pct": _round(100.0 * agree_made / made, 1),
        "agreement_attempts": agree_made,
        "consensus_3plus_coverage_pct": _round(100.0 * consensus_made / made, 1),
        "consensus_3plus_attempts": consensus_made,
        "indicator_data": ctx.get("indicator_data") or {},
        "indicator_feature_set": INDICATOR_FEATURES,
        "path_data": ctx.get("path_data") or {},
        "path_feature_set": PATH_FEATURES,
        "cycle_data": ctx.get("cycle_data") or {},
        "cycle_feature_set": CYCLE_FLOW_FEATURES,
        "multiscale_trend": {
            "windows_bars": [3, 5, 10, 20, 60, 120],
            "rule": "sign of the average tanh(return/(10-bar volatility*sqrt(window))) across available windows",
            "attempts": method_made.get("multiscale_trend", 0),
        },
        "multiscale_confidence_coverage": {
            "thresholds": confidence_rows,
            "warning": "Coverage-limited diagnostic only. A high selective rate is not the full-test score, is never eligible for best_method_on_this_sample, and score magnitude may not calibrate across symbols/eras.",
        },
        "adaptive_selector": {
            "rule": "Follow the candidate with the best shrunken hit rate over fully revealed "
                    "prior attempts only: (revealed_hits + 5) / (revealed_attempts + 10). A "
                    "prior attempt is revealed only when old_origin + horizon <= current origin, "
                    "so overlapping unfinished windows cannot teach the selector early.",
            "min_revealed_attempts_per_method": 20,
            "prior_pseudo_attempts_at_50pct": 10,
            "fallback": "majority_vote_v8 when available, otherwise the newest available majority vote, then momentum_5bar",
            "fallback_attempts": selector_fallback_attempts,
            "choices": {m: n for m, n in selector_choices.items() if n},
            "revealed_attempts_by_method_at_end": {m: int(v[0]) for m, v in selector_stats.items()},
            "revealed_hits_by_method_at_end": {m: int(v[1]) for m, v in selector_stats.items()},
            "selection_log": selector_log,
        },
        "v11_direct_methods": {
            "kalman_trend": "sign of causal alpha-beta log-price slope (level gain 0.35, slope gain 0.08)",
            "omni_direct_consensus": "fixed weighted fusion of multiscale trend (1.2), Kalman slope (0.9), horizon-matched trend (0.7), Parabolic SAR (0.5) and a CCI/Williams/TSI/TRIX/Ultimate/CMO/Fisher/Schaff oscillator basket (0.5)",
            "rank_fusion_analog": "neighbours selected by mean normalized distance rank across the five existing feature families",
            "attempts": {m: method_made.get(m, 0) for m in (
                "kalman_trend", "omni_direct_consensus", "rank_fusion_analog_median",
                "rank_fusion_analog_weighted", "majority_vote_v6")},
        },
        "v12_direct_methods": {
            "hull_trend": "Hull MA price distance plus 3-bar slope, ATR-normalized",
            "supertrend_trend": "Supertrend(10,3) state",
            "kaufman_trend": "Kaufman AMA price/slope state, ATR-normalized",
            "haar_wavelet_trend": "Haar block-average scales 4/8/16/32/64, volatility-normalized",
            "markov_regime": "trend/volatility/RSI state; sign is mean fully revealed prior-attempt outcome in that state after 10 samples, otherwise multiscale",
            "atlas_fusion_v12": "majority of Hull, Kalman, Markov regime, Omni and multiscale votes",
            "attempts": {m: method_made.get(m, 0) for m in (
                "hull_trend", "supertrend_trend", "kaufman_trend", "haar_wavelet_trend",
                "markov_regime", "atlas_fusion_v12", "majority_vote_v7")},
        },
        "v13_direct_methods": {
            "classic_and_modern": "Aroon, TSI, TRIX, CMO, Ultimate, RVI, 20/60 log-regression, Donchian, OBV flow and Coppock are raced as bounded direct signs beside every older method.",
            "atlas_pressure_wave": "15-bar exponentially weighted candle close/body pressure scaled by ATR range and real relative volume, fused with 3/10-bar volatility-normalized momentum; close-only inputs collapse honestly to close-path pressure.",
            "atlas_regime_compass": "ADX/permutation-entropy trend weight blends Hull/multiscale trend with Bollinger/RSI range reversion.",
            "atlas_phoenix_fusion": "family-balanced fusion: trend filters 25%, momentum 25%, structure 20%, OHLCV flow proxies 20%, Regime Compass 10%; correlated inputs are averaged inside families first.",
            "majority_vote_v8": "all available analog-family, v4-v12 direct and v13 direct votes; Phoenix/Pressure/Atlas Fusion breaks ties in that order.",
            "attempts": {m: method_made.get(m, 0) for m in (
                "aroon_trend", "tsi_momentum", "trix_momentum", "cmo_momentum",
                "ultimate_trend", "rvi_trend", "regression_trend", "donchian_trend",
                "obv_flow_trend", "coppock_trend", "atlas_pressure_wave",
                "atlas_regime_compass", "atlas_phoenix_fusion", "majority_vote_v8")},
        },
        "v13_meta_learners": {
            "atlas_meta_hedge": {
                "rule": "Exponentially weighted majority over 16 diversified contestants. A revealed hit multiplies a candidate weight by exp(+0.15), a miss by exp(-0.15), then weights are renormalized to mean 1. Labels reveal only when old_origin + horizon <= current origin.",
                "candidates": list(meta_candidates),
                "eta": 0.15,
                "revealed_attempts_by_end": int(meta_revealed_attempts),
                "final_weights_mean_one": {m: _round(w, 4) for m, w in meta_weights.items()},
                "attempts": method_made.get("atlas_meta_hedge", 0),
            },
            "atlas_online_logistic": {
                "rule": "Online logistic regression on bounded origin-time scores/analog shares. One L2-regularized SGD update (learning rate 0.08, lambda 0.002) is applied only after an attempt's full horizon has revealed; missing features are neutral zero, never future-filled.",
                "features": list(logistic_feature_names),
                "learning_rate": 0.08,
                "l2_lambda": 0.002,
                "revealed_attempts_by_end": int(logistic_revealed_attempts),
                "final_intercept": _round(logistic_bias, 4),
                "final_weights": {name: _round(weight, 4) for name, weight in zip(logistic_feature_names, logistic_weights)},
                "attempts": method_made.get("atlas_online_logistic", 0),
            },
            "warning": "Causal online learning prevents label leakage, not overfitting, regime change or correlated-input double counting. A meta-learner trained inside one race still needs untouched symbols/eras before anyone should trust it.",
        },
        "best_method_on_this_sample": best_method,
        "cost_analysis": cost_rows,
        "honesty_notes": [
            "Several variants raced on ONE sample: the best-looking one is inflated by "
            "multiple comparisons. Treat the winner as a hypothesis to re-test on fresh "
            "data, never as a discovered edge.",
            "agreement_only accuracy is meaningless without its coverage: a filter that "
            "speaks rarely can look clever while avoiding most of the test.",
            "Cost rows use overlapping origins, so totals are NOT a compounded equity "
            "curve — read mean-net-per-trade and win-rate-after-cost instead.",
            "Costs shown are flat round-trip bps; real spreads/slippage vary by market, "
            "size and hour and are usually worse than the tidy number.",
            "Candle-shape neighbours can be numerous and near-duplicates within one trend; "
            "their outcome spread is sample folklore until this same blind test survives a "
            "second symbol/era. Close-only bars are reported unavailable, not scored as zero.",
            "Indicator-regime neighbours are transformations of the same historical price path, "
            "not independent information: RSI, MACD, Bollinger, Stochastic and Donchian can all "
            "agree because they are looking at one move through related windows. On close-only "
            "data the range-based pieces collapse to close-path functions and are labelled as such.",
            "consensus_3plus is a coverage-limited subset, never a full-test score: judge it only "
            "beside its attempts/coverage and after-cost rows, and expect small subsets to wobble.",
            "Path-geometry neighbours re-describe the same completed price path (efficiency, "
            "variance scaling, drawdowns and streaks are not new information arriving from "
            "outside the chart). On close-only data its high/low pieces collapse to closes and "
            "its volume balance is zero rather than invented.",
            "adaptive_selector is causal by construction — it learns only from attempts whose "
            "outcome window had already ended — but it is still selecting among many correlated "
            "contestants on one sample. A good selector score here is a reason to re-test on a "
            "second symbol/era, not evidence of a durable forecasting edge.",
            "Cycle/flow neighbours add classic Aroon/Vortex/Fisher/Schaff/KST/Coppock and OHLCV "
            "flow proxies, but they remain transformations of the same bars. CMF/MFI/Force/VWAP "
            "are not exchange order-flow data, and close-only inputs collapse toward neutral.",
            "multiscale_trend is a direct trend contestant, not a nearest-neighbour oracle. A "
            "60/100-style result beside momentum's high-50s on one sample is inside ordinary "
            "sampling noise unless it survives other horizons, symbols, eras and costs.",
            "multiscale confidence rows are selective subsets. Their accuracy must always be read "
            "with attempts and coverage; TradeAtlas does not let a threshold manufacture a headline.",
            "v11 adds Kalman, PSAR/Ichimoku/oscillator-informed direct fusion and rank-fused "
            "neighbours. They are more transformations of the same OHLCV bars, so a higher "
            "sample score can still be multiple-comparison luck; no universal percentage lift is claimed.",
            "v12 adds Hull/Supertrend/Kaufman/Haar and a causal Markov-regime vote. More methods "
            "also means more chances to overfit one sample; an 80% universal direction rate is not claimed.",
            "v13 adds Aroon/TSI/TRIX/CMO/Ultimate/RVI/regression/Donchian/OBV/Coppock direct signs, "
            "invented Pressure Wave/Regime Compass/Phoenix scores, and causal Meta Hedge + online "
            "logistic learners. They are still deterministic transformations or delayed-label fits to "
            "the same OHLCV history; more machinery can lose faster and an 80% universal rate remains unproven.",
        ],
    }


def multi_horizon_eval(bars: list[dict], *, horizons=(1, 3, 5, 10, 20),
                       attempts: int = 100, top_n: int = 30,
                       min_history: int = 200) -> list[dict]:
    """The same hidden-future test at several horizons: an 'edge' that exists
    at exactly one horizon and nowhere else is usually a cherry, not a signal."""
    rows = []
    for h in horizons:
        ev = rolling_forecast_eval(bars, attempts=attempts, horizon=int(h),
                                   top_n=top_n, min_history=min_history)
        if "error" in ev:
            rows.append({"horizon_bars": int(h), "error": ev["error"]})
        else:
            rows.append({
                "horizon_bars": int(h),
                "attempts_made": ev["attempts_made"],
                "analog_direction_accuracy_pct": ev["analog_direction_accuracy_pct"],
                "baseline_always_up_pct": ev["baseline_always_up_pct"],
                "baseline_momentum_5bar_pct": ev["baseline_momentum_5bar_pct"],
                "baseline_mean_reversion_5bar_pct": ev["baseline_mean_reversion_5bar_pct"],
                "brier_skill_vs_climatology": ev["brier_skill_vs_climatology"],
                "verdict": ev["verdict"],
            })
    return rows


def _analog_paths(ctx: dict, origin: int, horizon: int, top_n: int) -> list[list[float]]:
    """Actual forward PATHS (cumulative % per bar) of the nearest past setups.
    Same no-lookahead rule as _analog_forward_returns: j + horizon <= origin."""
    vecs = ctx.get("vecs")
    target = vecs[origin] if vecs else _feature_vector(ctx, origin)
    if target is None:
        return []
    closes = ctx["closes"]
    scored = []
    for j in range(30, origin - horizon + 1):
        vec = vecs[j] if vecs else _feature_vector(ctx, j)
        if vec is None or not closes[j]:
            continue
        dist = sum((a - b) ** 2 for a, b in zip(vec, target)) ** 0.5
        base = closes[j]
        path = [(closes[j + k] / base - 1.0) * 100.0 for k in range(1, horizon + 1)]
        scored.append((dist, path))
    scored.sort(key=lambda item: item[0])
    return [path for _, path in scored[:top_n]]


def _max_drawdown_pct(path_pct: list[float]) -> float:
    peak = 100.0
    worst = 0.0
    for cum in path_pct:
        equity = 100.0 * (1.0 + cum / 100.0)
        peak = max(peak, equity)
        if peak > 0:
            worst = max(worst, (peak - equity) / peak * 100.0)
    return worst


def analog_path_simulation(bars: list[dict], *, horizon: int = 20, top_n: int = 30,
                           paths: int = 500, seed: int = 42) -> dict:
    """Bootstrap over REAL analog paths: resample what look-alike setups
    actually did, bar by bar, and summarize terminal outcome + worst dip.
    A picture of historical dispersion — not a forecast distribution."""
    if len(bars) < 120:
        return {"error": "path simulation needs at least 120 bars", "bars": len(bars)}
    ctx = _forecast_context(bars)
    real_paths = _analog_paths(ctx, len(bars) - 1, int(horizon), top_n)
    if len(real_paths) < 10:
        return {"error": "too few analog paths with full horizon",
                "analog_paths_real": len(real_paths)}
    rng = random.Random(seed)
    sampled = [rng.choice(real_paths) for _ in range(max(50, int(paths)))]
    terminals = sorted(p[-1] for p in sampled)
    drawdowns = sorted(_max_drawdown_pct(p) for p in sampled)
    n = len(sampled)
    def pct(vals, p):
        return _round(vals[min(n - 1, max(0, int(p * n)))], 2)
    return {
        "horizon_bars": int(horizon),
        "analog_paths_real": len(real_paths),
        "simulated_paths": n,
        "seed": seed,
        "terminal_return_pct": {"p5": pct(terminals, 0.05), "p25": pct(terminals, 0.25),
                                "p50_median": pct(terminals, 0.50), "p75": pct(terminals, 0.75),
                                "p95": pct(terminals, 0.95)},
        "max_drawdown_pct": {"p50_median": pct(drawdowns, 0.50), "p75": pct(drawdowns, 0.75),
                             "p95": pct(drawdowns, 0.95)},
        "share_paths_up_pct": _round(100.0 * sum(1 for t in terminals if t > 0) / n, 1),
        "warning": "Bootstrapped from the realized paths of similar past setups in THIS file. "
                   "It quantifies how wide the historical spread was; it is not a probability "
                   "distribution for the future and inherits every bias of the sample.",
    }


def multiscale_trend_eval(bars: list[dict], *, horizons=(1, 3, 5, 10, 20),
                          attempts: int = 100, min_history: int = 200) -> dict:
    """Hidden-future test of the direct multiscale trend score at many horizons.

    This exists specifically to stop a 5-bar result from being marketed as a
    universal law: the same fixed score is forced through neighbouring
    horizons, with 5-bar momentum and always-up beside it and after-cost means.
    """
    bars = normalize_bars(bars)
    ctx = _forecast_context(bars)
    closes = ctx["closes"]
    scores = ctx.get("multiscale_trend") or []
    rows = []
    for horizon in horizons:
        h = int(horizon)
        last_origin = len(bars) - 1 - h
        if last_origin - min_history < 10:
            rows.append({"horizon_bars": h, "error": "insufficient origins"})
            continue
        span = last_origin - min_history
        step = max(1, span // max(1, int(attempts)))
        origins = list(range(min_history, last_origin + 1, step))[-max(1, int(attempts)):]
        made = hits = momentum_hits = always_hits = 0
        signed_returns = []
        momentum_returns = []
        for origin in origins:
            score = scores[origin] if origin < len(scores) else None
            if score is None or not closes[origin] or origin < 5:
                continue
            actual = (closes[origin + h] / closes[origin] - 1.0) * 100.0
            sign = 1 if float(score) > 0 else -1
            momentum_sign = 1 if closes[origin] > closes[origin - 5] else -1
            made += 1
            hits += int((sign > 0) == (actual > 0) and actual != 0)
            momentum_hits += int((momentum_sign > 0) == (actual > 0) and actual != 0)
            always_hits += int(actual > 0)
            signed_returns.append(sign * actual)
            momentum_returns.append(momentum_sign * actual)
        rows.append({
            "horizon_bars": h,
            "attempts_made": made,
            "multiscale_direction_accuracy_pct": _round(100.0 * hits / made, 1) if made else None,
            "baseline_momentum_5bar_pct": _round(100.0 * momentum_hits / made, 1) if made else None,
            "baseline_always_up_pct": _round(100.0 * always_hits / made, 1) if made else None,
            "multiscale_mean_net_pct_per_trade_10bps": _round(
                sum(x - 0.10 for x in signed_returns) / made, 3) if made else None,
            "multiscale_mean_net_pct_per_trade_25bps": _round(
                sum(x - 0.25 for x in signed_returns) / made, 3) if made else None,
            "momentum_mean_net_pct_per_trade_10bps": _round(
                sum(x - 0.10 for x in momentum_returns) / made, 3) if made else None,
        })
    return {
        "method": "fixed multiscale trend score; origins selected exactly like the ensemble race",
        "windows_bars": [3, 5, 10, 20, 60, 120],
        "horizons": rows,
        "warning": "Neighbouring horizons are a fragility check, not independent confirmations: overlapping windows on one symbol/era remain one sample.",
    }


def direct_method_eval(bars: list[dict], *, horizons=(1, 3, 5, 10, 20),
                       attempts: int = 100, min_history: int = 200) -> dict:
    """Hidden-future rows for v11 direct methods beside multiscale/momentum.

    Omni is rebuilt for each horizon because its horizon-matched component is
    explicitly horizon-aware. Origins and cost treatment match the ensemble.
    """
    bars = normalize_bars(bars)
    ctx = _forecast_context(bars)
    closes = ctx["closes"]
    kalman_scores = ctx.get("kalman_trend") or []
    multiscale_scores = ctx.get("multiscale_trend") or []
    hull_scores = ctx.get("hull_trend") or []
    supertrend_states = (ctx.get("supertrend") or {}).get("trend") or []
    kaufman_scores = ctx.get("kaufman_trend") or []
    haar_scores = ctx.get("haar_trend") or []
    v13_direct_arrays = {
        "ultimate_trend": ctx.get("ultimate_score") or [],
        "tsi_momentum": ctx.get("tsi_score") or [],
        "regression_trend": ctx.get("regression_fusion") or [],
        "atlas_pressure_wave": ctx.get("pressure_wave") or [],
        "atlas_regime_compass": ctx.get("regime_compass") or [],
        "atlas_phoenix_fusion": ctx.get("phoenix") or [],
    }
    rows = []
    for horizon in horizons:
        h = int(horizon)
        last_origin = len(bars) - 1 - h
        if last_origin - min_history < 10:
            rows.append({"horizon_bars": h, "error": "insufficient origins"})
            continue
        omni_scores = omni_direct_scores(bars, horizon=h)
        span = last_origin - min_history
        step = max(1, span // max(1, int(attempts)))
        origins = list(range(min_history, last_origin + 1, step))[-max(1, int(attempts)):]
        stats = {name: {"made": 0, "hits": 0, "returns": []}
                 for name in ("kalman_trend", "omni_direct_consensus", "multiscale_trend",
                              "hull_trend", "supertrend_trend", "kaufman_trend",
                              "haar_wavelet_trend", "ultimate_trend", "tsi_momentum",
                              "regression_trend", "atlas_pressure_wave",
                              "atlas_regime_compass", "atlas_phoenix_fusion",
                              "momentum_5bar", "always_up")}
        arrays = {"kalman_trend": kalman_scores, "omni_direct_consensus": omni_scores,
                  "multiscale_trend": multiscale_scores, "hull_trend": hull_scores,
                  "supertrend_trend": supertrend_states, "kaufman_trend": kaufman_scores,
                  "haar_wavelet_trend": haar_scores, **v13_direct_arrays}
        for origin in origins:
            if not closes[origin] or origin < 5:
                continue
            actual = (closes[origin + h] / closes[origin] - 1.0) * 100.0
            signs = {}
            for name, arr in arrays.items():
                score = arr[origin] if origin < len(arr) else None
                if score is not None:
                    signs[name] = 1 if float(score) > 0 else -1
            signs["momentum_5bar"] = 1 if closes[origin] > closes[origin - 5] else -1
            signs["always_up"] = 1
            for name, sign_value in signs.items():
                slot = stats[name]
                slot["made"] += 1
                slot["hits"] += int((sign_value > 0) == (actual > 0) and actual != 0)
                slot["returns"].append(sign_value * actual)
        row = {"horizon_bars": h, "methods": {}}
        for name, slot in stats.items():
            made = int(slot["made"])
            row["methods"][name] = {
                "attempts_made": made,
                "direction_accuracy_pct": _round(100.0 * int(slot["hits"]) / made, 1) if made else None,
                "mean_net_pct_per_trade_10bps": _round(
                    sum(x - 0.10 for x in slot["returns"]) / made, 3) if made else None,
                "mean_net_pct_per_trade_25bps": _round(
                    sum(x - 0.25 for x in slot["returns"]) / made, 3) if made else None,
            }
        rows.append(row)
    return {
        "method": "fixed v11/v12/v13 direct scores; origins selected exactly like the ensemble race",
        "horizons": rows,
        "warning": "Neighbouring horizons and methods are correlated checks on one sample, not independent confirmations.",
    }



def forecast_lab(bars: list[dict], *, attempts: int = 100, horizon: int = 5,
                 top_n: int = 30, min_history: int = 200,
                 eval_horizons=(1, 3, 5, 10, 20),
                 sim_horizon: int = 20, sim_paths: int = 500) -> dict:
    bars = normalize_bars(bars)
    return {
        "bars": len(bars),
        "analog_now": analog_forecast(bars, top_n=top_n),
        "candle_analog_now": candle_analog_forecast(bars, top_n=top_n),
        "indicator_analog_now": indicator_analog_forecast(bars, top_n=top_n),
        "path_analog_now": path_analog_forecast(bars, top_n=top_n),
        "cycle_analog_now": cycle_flow_analog_forecast(bars, top_n=top_n),
        "rank_fusion_analog_now": rank_fusion_analog_forecast(bars, top_n=top_n),
        "multiscale_trend_now": multiscale_trend_now(bars),
        "kalman_trend_now": kalman_trend_now(bars),
        "hull_trend_now": hull_trend_now(bars),
        "omni_direct_now": omni_direct_now(bars, horizon=horizon),
        "atlas_pressure_wave_now": atlas_pressure_wave_now(bars),
        "atlas_regime_compass_now": atlas_regime_compass_now(bars),
        "atlas_phoenix_now": atlas_phoenix_now(bars),
        "atlas_minute_pulse_now": atlas_minute_pulse_now(bars),
        "rolling_eval": rolling_forecast_eval(
            bars, attempts=attempts, horizon=horizon, top_n=top_n,
            min_history=min_history),
        "ensemble_eval": ensemble_forecast_eval(
            bars, attempts=attempts, horizon=horizon, top_n=top_n,
            min_history=min_history),
        "multi_horizon_eval": multi_horizon_eval(
            bars, horizons=eval_horizons, attempts=attempts, top_n=top_n,
            min_history=min_history),
        "multiscale_trend_eval": multiscale_trend_eval(
            bars, horizons=eval_horizons, attempts=attempts, min_history=min_history),
        "direct_method_eval": direct_method_eval(
            bars, horizons=eval_horizons, attempts=attempts, min_history=min_history),
        "path_simulation": analog_path_simulation(
            bars, horizon=sim_horizon, top_n=top_n, paths=sim_paths),
        "disclaimer": DISCLAIMER,
    }


def analyze_timeframe(bars: list[dict], timeframe: str, strategy: str, **backtest_kwargs) -> dict:
    if len(bars) < 60:
        return {"timeframe": timeframe, "bars": len(bars), "status": "insufficient_data",
                "reason": "At least 60 bars are required for the standard indicators and event test."}
    max_signals = int(backtest_kwargs.get("max_trades", 100))
    horizon = int(backtest_kwargs.get("horizon_bars", 10))
    costs = float(backtest_kwargs.get("round_trip_cost_bps", 10.0))
    events = generate_signal_events(bars, strategy)
    snapshot = indicator_snapshot(bars)
    return {
        "timeframe": timeframe, "bars": len(bars), "status": "ok",
        "snapshot": snapshot,
        "latest_signal": latest_signal(bars, strategy, snapshot=snapshot, events=events),
        "historical_validation": backtest_signals(
            bars, strategy, include_trades=False, events=events,
            **{k: v for k, v in backtest_kwargs.items() if k not in ("include_trades", "events")}),
        "walk_forward": walk_forward_split(
            bars, strategy, max_signals=max_signals, horizon_bars=horizon,
            round_trip_cost_bps=costs, events=events),
        "strategy_tournament": strategy_tournament(
            bars, max_signals=max_signals, horizon_bars=horizon,
            round_trip_cost_bps=costs),
    }


def analyze_market(data, *, strategy: str = "consensus", max_signals: int = 100,
                   horizon_bars: int = 10, round_trip_cost_bps: float = 10.0,
                   source_label: str = "user-supplied OHLCV data") -> dict:
    bars = normalize_bars(data)
    base_interval = infer_interval_seconds(bars)
    frames = []
    skipped = []
    for label, seconds in TIMEFRAMES.items():
        if seconds < base_interval:
            skipped.append({"timeframe": label, "reason": "Finer than the supplied base interval; cannot be reconstructed honestly."})
            continue
        resampled = bars if seconds == base_interval else resample_bars(bars, seconds)
        frames.append(analyze_timeframe(
            resampled, label, strategy, max_trades=max_signals,
            horizon_bars=horizon_bars, round_trip_cost_bps=round_trip_cost_bps))
    return {
        "source": source_label,
        "source_is_synthetic": False,
        "base_interval_seconds": base_interval,
        "input_bars": len(bars),
        "strategy": strategy,
        "strategy_detail": STRATEGY_ENGINES[strategy],
        "timeframes": frames,
        "skipped_timeframes": skipped,
        "disclaimer": DISCLAIMER,
    }


def generate_demo_bars(timeframe: str = "1h", count: int = 6000, seed: int = 42) -> list[dict]:
    """Deterministic invented OHLCV for software validation — not market data."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"unknown timeframe '{timeframe}'")
    if count < 100 or count > 100_000:
        raise ValueError("count must be between 100 and 100000")
    seconds = TIMEFRAMES[timeframe]
    vol_map = {"1m": 0.0012, "5m": 0.0025, "15m": 0.004, "1h": 0.008,
               "4h": 0.015, "1d": 0.022, "1w": 0.045}
    volatility = vol_map[timeframe]
    offset = sum((idx + 1) * ord(ch) for idx, ch in enumerate(timeframe))
    rng = random.Random(int(seed) + offset)
    end = 1767225600  # 2026-01-01 UTC, fixed for reproducibility
    start = end - (count - 1) * seconds
    price = 100.0
    anchor = 100.0
    regime_drift = 0.0
    bars = []
    for i in range(count):
        if i % 180 == 0:
            regime_drift = rng.uniform(-0.22, 0.22) * volatility
            anchor *= math.exp(rng.uniform(-0.05, 0.05))
        cycle = math.sin(i / 37.0) * 0.16 * volatility + math.sin(i / 131.0) * 0.10 * volatility
        mean_reversion = (math.log(anchor / price) * 0.018) if price > 0 else 0.0
        shock = rng.gauss(0.0, volatility)
        open_price = price
        close = max(0.01, open_price * math.exp(regime_drift + cycle + mean_reversion + shock))
        high = max(open_price, close) * math.exp(abs(rng.gauss(0.0, volatility * 0.42)))
        low = min(open_price, close) * math.exp(-abs(rng.gauss(0.0, volatility * 0.42)))
        volume = max(1.0, 10_000 * (0.55 + abs(shock) / max(volatility, 0.000001)) * rng.uniform(0.65, 1.45))
        bars.append({"t": start + i * seconds, "o": round(open_price, 6),
                     "h": round(high, 6), "l": round(low, 6),
                     "c": round(close, 6), "v": round(volume, 2)})
        price = close
    return bars


def demo_analysis(*, strategy: str = "consensus", max_signals: int = 100,
                  horizon_bars: int = 10, round_trip_cost_bps: float = 10.0,
                  bars_per_timeframe: int = 6000, seed: int = 42) -> dict:
    frames = []
    for label in TIMEFRAMES:
        demo = generate_demo_bars(label, count=bars_per_timeframe, seed=seed)
        frames.append(analyze_timeframe(
            demo, label, strategy, max_trades=max_signals,
            horizon_bars=horizon_bars, round_trip_cost_bps=round_trip_cost_bps))
    return {
        "source": "deterministic synthetic OHLCV generated only to validate the software",
        "source_is_synthetic": True,
        "warning": "These are invented prices. Their accuracy numbers say nothing about any real market or future result.",
        "base_interval_seconds": None,
        "input_bars": bars_per_timeframe * len(TIMEFRAMES),
        "bars_per_timeframe": bars_per_timeframe,
        "strategy": strategy,
        "strategy_detail": STRATEGY_ENGINES[strategy],
        "timeframes": frames,
        "skipped_timeframes": [],
        "disclaimer": DISCLAIMER,
    }


MARKET_PRESETS = {
    "crypto_spot": {
        "label": "Crypto spot (24/7)",
        "examples": "BTC, ETH and other exchange pairs — exported from your own exchange account/tools",
        "typical_base_intervals": ["1m", "5m", "15m", "1h"],
        "starting_cost_bps_to_research": "10-30 round-trip (fees + spread + slippage vary wildly by venue/pair)",
        "data_notes": "Trades around the clock; exchange outages and wick anomalies are common — sanity-check bars.",
    },
    "us_stocks_etfs": {
        "label": "US stocks & ETFs",
        "examples": "Single names and index ETFs via your broker/data vendor export",
        "typical_base_intervals": ["1m", "5m", "1d"],
        "starting_cost_bps_to_research": "1-10 for liquid names (plus borrow costs for shorts, which this lab does not model)",
        "data_notes": "Mind splits/dividends (adjusted vs raw), halts, and pre/post-market thin bars.",
    },
    "fx_majors": {
        "label": "FX majors",
        "examples": "EUR/USD, USD/JPY class pairs from your broker export",
        "typical_base_intervals": ["5m", "15m", "1h"],
        "starting_cost_bps_to_research": "1-5 spread on majors at liquid hours (swap/rollover not modelled here)",
        "data_notes": "Broker feeds differ; weekend gaps and news spikes dominate short-horizon results.",
    },
    "futures_commodities": {
        "label": "Futures & commodities",
        "examples": "Index, energy and metals futures continuous or single-contract exports",
        "typical_base_intervals": ["5m", "15m", "1h", "1d"],
        "starting_cost_bps_to_research": "Convert per-contract commissions/ticks to bps yourself; roll gaps distort backtests",
        "data_notes": "Continuous-contract joins create fake jumps; prefer testing single contracts or adjusted series you trust.",
    },
    "indices_global": {
        "label": "Global indices (cash/CFD exports)",
        "examples": "Regional index series exported from a vendor you subscribe to",
        "typical_base_intervals": ["15m", "1h", "1d"],
        "starting_cost_bps_to_research": "Vendor/CFD spreads vary; dividend and financing adjustments are not modelled here",
        "data_notes": "Confirm timezone/session alignment before comparing timeframes across regions.",
    },
}


def trades_to_csv(trades: list[dict]) -> str:
    """Spreadsheet-ready signal log for the trades of one backtest."""
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["signal_time_utc", "entry_time_utc", "exit_time_utc", "condition",
                     "entry", "exit", "gross_return_pct", "net_return_pct", "reason"])
    for t in trades:
        writer.writerow([t.get("signal_time_utc"), t.get("entry_time_utc"), t.get("exit_time_utc"),
                         t.get("condition"), t.get("entry"), t.get("exit"),
                         t.get("gross_return_pct"), t.get("net_return_pct"), t.get("reason")])
    return out.getvalue()


def analyze_watchlist(symbols: dict, *, strategy: str = "consensus",
                      max_symbols: int = 12) -> dict:
    """Latest mechanical condition per timeframe for many user-supplied symbols.

    `symbols` maps a display name to bars (list/dict payload) or {"csv": text}.
    This is a tracking heatmap, not a ranking of what to buy: every cell is the
    same textbook rulebook applied to data the user supplied.
    """
    if strategy not in STRATEGY_ENGINES:
        raise ValueError(f"unknown strategy '{strategy}'")
    if not isinstance(symbols, dict) or not symbols:
        raise ValueError("symbols must be a non-empty object mapping names to OHLCV bars")
    rows = []
    errors = []
    for raw_name in list(symbols)[:max(1, int(max_symbols))]:
        name = str(raw_name)[:40] or "(unnamed)"
        payload = symbols[raw_name]
        try:
            if isinstance(payload, dict) and "csv" in payload:
                bars = parse_csv(str(payload["csv"]))
            else:
                bars = normalize_bars(payload)
            base_interval = infer_interval_seconds(bars)
            cells = []
            for label, seconds in TIMEFRAMES.items():
                if seconds < base_interval:
                    cells.append({"timeframe": label, "status": "finer_than_source"})
                    continue
                resampled = bars if seconds == base_interval else resample_bars(bars, seconds)
                if len(resampled) < 60:
                    cells.append({"timeframe": label, "status": "insufficient_data",
                                  "bars": len(resampled)})
                    continue
                snap = indicator_snapshot(resampled)
                sig = latest_signal(resampled, strategy)
                first_close = float(resampled[0]["c"])
                cells.append({
                    "timeframe": label, "status": "ok", "bars": len(resampled),
                    "close": snap["close"], "bias": snap["bias"],
                    "bias_score": snap["bias_score"],
                    "condition": sig["condition"],
                    "change_over_window_pct": _round(
                        100.0 * (float(resampled[-1]["c"]) - first_close) / first_close, 4)
                    if first_close else None,
                })
            rows.append({"symbol": name, "base_interval_seconds": base_interval,
                         "input_bars": len(bars), "timeframes": cells})
        except (TypeError, ValueError, KeyError) as exc:
            errors.append({"symbol": name, "error": str(exc)[:220]})
    return {
        "strategy": strategy, "strategy_detail": STRATEGY_ENGINES[strategy],
        "symbols": rows, "errors": errors,
        "note": ("Heatmap of mechanical conditions on user-supplied data only. "
                 "Run the full Market Lab analysis per symbol for the 100-signal validation."),
        "disclaimer": DISCLAIMER,
    }


# ---------------------------------------------------------------------------
# Paper wallet (simulation only — no custody, conversion, broker or orders)
# ---------------------------------------------------------------------------

PAPER_WALLET_SPEC = {
    "mode": "paper_simulation_only",
    "currency": "PAPER_USD",
    "demo_crypto_balances": "The v13 demo e-wallet can hold imaginary USDT/USDC/BTC/ETH/SOL quantities, convert those imaginary balances to PAPER_USD at a user-typed rate, simulate a withdrawal by deleting imaginary units, and move PAPER_USD internally to/from the paper bot. None of those actions touches a blockchain, bank, exchange or real asset.",
    "external_account_mirror": "v14 can record balances that the user says are held in the user's OWN licensed exchange/broker account. This is an unverified accounting mirror only: TradeAtlas cannot access, verify, receive, convert, withdraw or trade those assets, and mirrored balances are excluded from paper equity.",
    "accepts_real_money_or_crypto": False,
    "deposit_address": None,
    "blockchain_transfer": False,
    "broker_or_exchange_execution": False,
    "what_simulated_conversion_means": (
        "A user types a hypothetical crypto amount and a hypothetical USD rate; "
        "TradeAtlas adds the product to an imaginary PAPER_USD balance. Nothing "
        "is received, converted, custodied, withdrawn or traded for real."
    ),
    "follow_mode": (
        "When following is ON, one follow-step may create a simulated spot "
        "position from the latest completed supplied bar. STOP sets a hard halt "
        "that blocks new paper-follow actions. Spot paper wallet is long-only: "
        "a short condition exits a simulated holding; it never opens a real or "
        "leveraged short."
    ),
    "risk_caps": {"max_follow_allocation_pct_per_step": 25.0, "leverage": "none", "margin": "none"},
    "warning": "Never send cryptocurrency or money to TradeAtlas. It has no deposit address and cannot convert or trade real assets.",
}


def _paper_number(value, field: str, *, positive: bool = True, maximum: float | None = None) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(number) or (positive and number <= 0) or (not positive and number < 0):
        raise ValueError(f"{field} must be {'positive' if positive else 'non-negative'} and finite")
    if maximum is not None and number > maximum:
        raise ValueError(f"{field} exceeds the paper-wallet safety cap ({maximum})")
    return number


def _paper_symbol(value) -> str:
    symbol = str(value or "").strip().upper()[:24]
    if not symbol or any(not (ch.isalnum() or ch in ".-/_") for ch in symbol):
        raise ValueError("symbol must use letters, digits, dot, dash, slash or underscore")
    return symbol


def _paper_ledger(state: dict, kind: str, **fields) -> dict:
    state["_seq"] = int(state.get("_seq") or 0) + 1
    entry = {"seq": state["_seq"], "kind": kind, **fields}
    state.setdefault("ledger", []).append(entry)
    return entry


def _paper_asset_code(value) -> str:
    asset_code = str(value or "").strip().upper()
    if asset_code not in {"USDT", "USDC", "BTC", "ETH", "SOL", "OTHER_PAPER_ASSET"}:
        raise ValueError("asset must be USDT, USDC, BTC, ETH, SOL or OTHER_PAPER_ASSET")
    return asset_code


def _external_asset_code(value) -> str:
    asset_code = str(value or "").strip().upper()
    if asset_code == "USD":
        return asset_code
    return _paper_asset_code(asset_code)


def new_paper_wallet(*, starting_balance: float = 10_000.0) -> dict:
    """Create an in-memory PAPER_USD wallet. This is not a financial account."""
    balance = _paper_number(starting_balance, "starting_balance", maximum=100_000_000.0)
    state = {
        "mode": "paper_simulation_only",
        "currency": "PAPER_USD",
        "starting_balance": balance,
        "cash": balance,
        "positions": {},
        "paper_asset_balances": {},
        "external_account_mirror": {
            "venue_label": "", "balances": {},
            "custody": "user_own_external_account",
            "tradeatlas_can_access": False, "verified_by_tradeatlas": False,
        },
        "simulated_withdrawal_total_paper_usd_equivalent": 0.0,
        "ledger": [],
        "follow_log": [],
        "realized_pnl": 0.0,
        "total_fees": 0.0,
        "simulated_conversion_total_paper_usd": 0.0,
        "following": False,
        "halted": True,
        "last_follow_bars": {},
        "settings": {"allocation_pct": 10.0, "max_allocation_pct": 25.0,
                     "fee_bps": 10.0, "spot_long_only": True, "leverage": "none"},
        "real_money": False,
        "accepts_real_crypto": False,
        "deposit_address": None,
        "_seq": 0,
    }
    _paper_ledger(state, "initial_paper_capital", amount=balance,
                  note="Imaginary teaching balance; no deposit occurred.")
    return state


def paper_wallet_view(state: dict, *, prices: dict | None = None) -> dict:
    if not isinstance(state, dict) or state.get("mode") != "paper_simulation_only":
        raise ValueError("invalid paper wallet state")
    prices = prices or {}
    positions = []
    market_value_total = 0.0
    unrealized_total = 0.0
    for symbol, raw in sorted((state.get("positions") or {}).items()):
        quantity = float(raw.get("quantity") or 0.0)
        if quantity <= 0:
            continue
        cost_basis = float(raw.get("cost_basis") or 0.0)
        avg_cost = cost_basis / quantity if quantity else 0.0
        supplied_price = prices.get(symbol)
        mark = _paper_number(supplied_price, f"prices.{symbol}") if supplied_price is not None else avg_cost
        market_value = quantity * mark
        unrealized = market_value - cost_basis
        market_value_total += market_value
        unrealized_total += unrealized
        positions.append({
            "symbol": symbol, "quantity": _round(quantity, 10),
            "average_cost": _round(avg_cost, 8), "cost_basis": _round(cost_basis, 4),
            "mark_price": _round(mark, 8), "market_value": _round(market_value, 4),
            "unrealized_pnl": _round(unrealized, 4),
            "price_is_supplied_mark": supplied_price is not None,
        })
    paper_balances = []
    paper_balance_value_total = 0.0
    for asset, raw_balance in sorted((state.get("paper_asset_balances") or {}).items()):
        if isinstance(raw_balance, dict):
            quantity = float(raw_balance.get("quantity") or 0.0)
            last_rate = float(raw_balance.get("last_simulated_usd_rate") or 0.0)
        else:
            quantity = float(raw_balance or 0.0)
            last_rate = 0.0
        if quantity <= 0:
            continue
        supplied_balance_price = prices.get(asset)
        mark = (_paper_number(supplied_balance_price, f"prices.{asset}")
                if supplied_balance_price is not None else last_rate)
        value = quantity * mark if mark > 0 else 0.0
        paper_balance_value_total += value
        paper_balances.append({
            "asset": asset, "quantity": _round(quantity, 10),
            "last_simulated_usd_rate": _round(last_rate, 8),
            "mark_price": _round(mark, 8), "paper_usd_value": _round(value, 4),
            "price_is_supplied_mark": supplied_balance_price is not None,
            "real_crypto": False, "deposit_address": None,
        })
    cash = float(state.get("cash") or 0.0)
    mirror_state = state.get("external_account_mirror") or {}
    external_balances = []
    external_total = 0.0
    for asset, raw_balance in sorted((mirror_state.get("balances") or {}).items()):
        if isinstance(raw_balance, dict):
            quantity = float(raw_balance.get("quantity") or 0.0)
            last_rate = float(raw_balance.get("last_user_reported_usd_rate") or 0.0)
            reported_at = raw_balance.get("reported_at")
        else:
            quantity, last_rate, reported_at = float(raw_balance or 0.0), 0.0, None
        if quantity <= 0:
            continue
        supplied_price = prices.get(asset)
        mark = (_paper_number(supplied_price, f"prices.{asset}")
                if supplied_price is not None else last_rate)
        value = quantity * mark if mark > 0 else 0.0
        external_total += value
        external_balances.append({
            "asset": asset, "quantity": _round(quantity, 10),
            "user_reported_usd_rate": _round(last_rate, 8),
            "mark_price": _round(mark, 8), "reported_usd_value": _round(value, 4),
            "reported_at": reported_at, "custody": "user_own_external_account",
            "tradeatlas_can_access": False, "verified_by_tradeatlas": False,
            "deposit_address": None,
        })
    external_mirror = {
        "venue_label": str(mirror_state.get("venue_label") or ""),
        "balances": external_balances,
        "reported_total_usd_value": _round(external_total, 4),
        "custody": "user_own_external_account",
        "tradeatlas_can_access": False, "verified_by_tradeatlas": False,
        "included_in_paper_equity": False, "deposit_address": None,
        "funding_instruction": "If you choose to fund an account, use only the official deposit screen inside your own licensed exchange/broker account. TradeAtlas does not provide or verify a deposit address.",
    }
    return {
        "mode": "paper_simulation_only",
        "currency": "PAPER_USD",
        "cash": _round(cash, 4),
        "positions": positions,
        "paper_asset_balances": paper_balances,
        "paper_asset_balances_value": _round(paper_balance_value_total, 4),
        "external_account_mirror": external_mirror,
        "positions_market_value": _round(market_value_total, 4),
        "equity": _round(cash + market_value_total + paper_balance_value_total, 4),
        "realized_pnl": _round(float(state.get("realized_pnl") or 0.0), 4),
        "unrealized_pnl": _round(unrealized_total, 4),
        "total_fees": _round(float(state.get("total_fees") or 0.0), 4),
        "simulated_conversion_total_paper_usd": _round(
            float(state.get("simulated_conversion_total_paper_usd") or 0.0), 4),
        "simulated_withdrawal_total_paper_usd_equivalent": _round(
            float(state.get("simulated_withdrawal_total_paper_usd_equivalent") or 0.0), 4),
        "following": bool(state.get("following")),
        "halted": bool(state.get("halted", True)),
        "settings": dict(state.get("settings") or {}),
        "ledger": [dict(entry) for entry in (state.get("ledger") or [])],
        "follow_log": [dict(entry) for entry in (state.get("follow_log") or [])],
        "real_money": False,
        "accepts_real_crypto": False,
        "deposit_address": None,
        "broker_or_exchange_execution": False,
        "warning": PAPER_WALLET_SPEC["warning"],
    }


def paper_wallet_record_external_balance(state: dict, *, venue_label: str = "",
                                         asset: str = "USDT", quantity: float,
                                         usd_rate: float | None = None,
                                         reported_at: str | None = None) -> dict:
    """Record a user-reported balance held in the user's own external account.

    This is not a deposit into TradeAtlas and does not verify the balance.
    The quantity replaces the prior mirror value for that asset; zero clears
    it. Mirrored funds never affect paper cash/equity or bot sizing.
    """
    paper_wallet_view(state)
    asset_code = _external_asset_code(asset)
    qty = _paper_number(quantity, "quantity", positive=False, maximum=1_000_000_000.0)
    rate = (1.0 if asset_code in {"USD", "USDT", "USDC"} and usd_rate is None
            else _paper_number(usd_rate, "usd_rate", positive=False, maximum=10_000_000.0)
            if usd_rate is not None else 0.0)
    label = str(venue_label or "").strip()[:80]
    lowered = label.lower()
    if any(word in lowered for word in ("api key", "secret", "password", "seed phrase", "private key")):
        raise ValueError("venue_label must be a harmless account label; never enter credentials or secrets")
    when = str(reported_at or dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"))[:40]
    mirror = state.setdefault("external_account_mirror", {})
    mirror["venue_label"] = label
    mirror["custody"] = "user_own_external_account"
    mirror["tradeatlas_can_access"] = False
    mirror["verified_by_tradeatlas"] = False
    balances = mirror.setdefault("balances", {})
    if qty <= 0:
        balances.pop(asset_code, None)
    else:
        balances[asset_code] = {"quantity": qty, "last_user_reported_usd_rate": rate,
                                "reported_at": when}
    entry = _paper_ledger(
        state, "external_account_balance_reported_by_user", venue_label=label,
        asset=asset_code, quantity=qty, user_reported_usd_rate=rate, reported_at=when,
        custody="user_own_external_account", tradeatlas_received_asset=False,
        verified_by_tradeatlas=False, deposit_address=None,
        note="Mirror only. Any funding must occur inside the user's own licensed account; nothing was sent to TradeAtlas.")
    prices = {asset_code: rate} if rate > 0 else {}
    return {"external_balance_record": entry, "wallet": paper_wallet_view(state, prices=prices)}


def paper_wallet_simulate_conversion(state: dict, *, asset: str = "USDT",
                                     crypto_amount: float, usd_rate: float = 1.0) -> dict:
    """Add imaginary PAPER_USD for a hypothetical crypto amount/rate.

    No wallet address exists, no blockchain transfer is detected or accepted,
    and no real asset is converted. The function name and ledger keep that
    boundary impossible to miss.
    """
    asset_code = _paper_asset_code(asset)
    amount = _paper_number(crypto_amount, "crypto_amount", maximum=1_000_000_000.0)
    rate = _paper_number(usd_rate, "usd_rate", maximum=10_000_000.0)
    converted = amount * rate
    if converted > 100_000_000.0:
        raise ValueError("simulated conversion exceeds the paper-wallet safety cap")
    state["cash"] = float(state.get("cash") or 0.0) + converted
    state["simulated_conversion_total_paper_usd"] = (
        float(state.get("simulated_conversion_total_paper_usd") or 0.0) + converted)
    entry = _paper_ledger(
        state, "simulated_crypto_conversion", asset=asset_code,
        hypothetical_crypto_amount=amount, hypothetical_usd_rate=rate,
        paper_usd_credited=_round(converted, 4), real_blockchain_transfer=False,
        deposit_address=None, note="Simulation only: nothing was received or converted.")
    return {"conversion": entry, "wallet": paper_wallet_view(state)}


def paper_wallet_simulate_crypto_deposit(state: dict, *, asset: str = "USDT",
                                         crypto_amount: float, usd_rate: float = 1.0) -> dict:
    """Credit an IMAGINARY crypto balance for the demo e-wallet.

    This deliberately has no deposit address and detects no blockchain
    transfer. It exists so a learner can model 'what if this quantity were in
    the demo wallet?' without sending anything anywhere.
    """
    paper_wallet_view(state)
    asset_code = _paper_asset_code(asset)
    amount = _paper_number(crypto_amount, "crypto_amount", maximum=1_000_000_000.0)
    rate = _paper_number(usd_rate, "usd_rate", maximum=10_000_000.0)
    balances = state.setdefault("paper_asset_balances", {})
    current = balances.get(asset_code) or {}
    old_quantity = float(current.get("quantity") or 0.0) if isinstance(current, dict) else float(current or 0.0)
    old_rate = float(current.get("last_simulated_usd_rate") or rate) if isinstance(current, dict) else rate
    new_quantity = old_quantity + amount
    weighted_rate = ((old_quantity * old_rate + amount * rate) / new_quantity
                     if new_quantity > 0 else rate)
    balances[asset_code] = {"quantity": new_quantity,
                            "last_simulated_usd_rate": weighted_rate}
    entry = _paper_ledger(
        state, "simulated_crypto_deposit_balance", asset=asset_code,
        hypothetical_crypto_amount=amount, hypothetical_usd_rate=rate,
        new_paper_quantity=_round(new_quantity, 10), real_blockchain_transfer=False,
        deposit_address=None, note="Simulation only: no crypto was sent, received or custodied.")
    return {"deposit": entry, "wallet": paper_wallet_view(state, prices={asset_code: rate})}


def paper_wallet_convert_crypto_balance(state: dict, *, asset: str,
                                        crypto_amount: float | None = None,
                                        usd_rate: float, fee_bps: float = 10.0) -> dict:
    """Convert part/all of an imaginary crypto balance into PAPER_USD cash."""
    paper_wallet_view(state)
    asset_code = _paper_asset_code(asset)
    balances = state.setdefault("paper_asset_balances", {})
    current = balances.get(asset_code) or {}
    held = float(current.get("quantity") or 0.0) if isinstance(current, dict) else float(current or 0.0)
    if held <= 0:
        raise ValueError(f"no simulated {asset_code} balance to convert")
    amount = held if crypto_amount is None else _paper_number(
        crypto_amount, "crypto_amount", maximum=1_000_000_000.0)
    if amount > held + 1e-12:
        raise ValueError(f"cannot convert more than the simulated {asset_code} balance")
    rate = _paper_number(usd_rate, "usd_rate", maximum=10_000_000.0)
    fee_bps = _paper_number(fee_bps, "fee_bps", positive=False, maximum=500.0)
    gross = amount * rate
    if gross > 100_000_000.0:
        raise ValueError("simulated conversion exceeds the paper-wallet safety cap")
    fee = gross * fee_bps / 10_000.0
    net = gross - fee
    remaining = held - amount
    if remaining <= 1e-12:
        balances.pop(asset_code, None)
    else:
        balances[asset_code] = {"quantity": remaining, "last_simulated_usd_rate": rate}
    state["cash"] = float(state.get("cash") or 0.0) + net
    state["simulated_conversion_total_paper_usd"] = (
        float(state.get("simulated_conversion_total_paper_usd") or 0.0) + net)
    state["total_fees"] = float(state.get("total_fees") or 0.0) + fee
    entry = _paper_ledger(
        state, "simulated_crypto_balance_conversion", asset=asset_code,
        hypothetical_crypto_amount=amount, hypothetical_usd_rate=rate,
        gross_paper_usd=_round(gross, 4), fee=_round(fee, 4), fee_bps=fee_bps,
        paper_usd_credited=_round(net, 4), remaining_paper_quantity=_round(max(remaining, 0.0), 10),
        real_blockchain_transfer=False, real_conversion=False, deposit_address=None,
        note="Simulation only: imaginary units became imaginary PAPER_USD.")
    return {"conversion": entry, "wallet": paper_wallet_view(state, prices={asset_code: rate})}


def paper_wallet_simulate_withdrawal(state: dict, *, asset: str = "PAPER_USD",
                                     amount: float, usd_rate: float | None = None) -> dict:
    """Remove imaginary cash/crypto from the demo wallet.

    No destination address is accepted and nothing leaves TradeAtlas; the
    ledger merely models the accounting effect of a hypothetical withdrawal.
    """
    paper_wallet_view(state)
    asset_code = str(asset or "").strip().upper()
    quantity = _paper_number(amount, "amount", maximum=1_000_000_000.0)
    if asset_code == "PAPER_USD":
        cash = float(state.get("cash") or 0.0)
        if quantity > cash + 1e-9:
            raise ValueError("insufficient PAPER_USD cash for this simulated withdrawal")
        state["cash"] = cash - quantity
        paper_value = quantity
        rate_used = 1.0
    else:
        asset_code = _paper_asset_code(asset_code)
        balances = state.setdefault("paper_asset_balances", {})
        current = balances.get(asset_code) or {}
        held = float(current.get("quantity") or 0.0) if isinstance(current, dict) else float(current or 0.0)
        if quantity > held + 1e-12:
            raise ValueError(f"insufficient simulated {asset_code} balance for this withdrawal")
        rate_used = (_paper_number(usd_rate, "usd_rate", maximum=10_000_000.0)
                     if usd_rate is not None else
                     float(current.get("last_simulated_usd_rate") or 0.0) if isinstance(current, dict) else 0.0)
        remaining = held - quantity
        if remaining <= 1e-12:
            balances.pop(asset_code, None)
        else:
            balances[asset_code] = {"quantity": remaining,
                                    "last_simulated_usd_rate": rate_used}
        paper_value = quantity * rate_used
    state["simulated_withdrawal_total_paper_usd_equivalent"] = (
        float(state.get("simulated_withdrawal_total_paper_usd_equivalent") or 0.0) + paper_value)
    entry = _paper_ledger(
        state, "simulated_withdrawal", asset=asset_code, hypothetical_amount=quantity,
        hypothetical_usd_rate=rate_used, paper_usd_equivalent=_round(paper_value, 4),
        real_withdrawal=False, real_blockchain_transfer=False, destination_address=None,
        note="Simulation only: imaginary units were removed; nothing was sent anywhere.")
    return {"withdrawal": entry, "wallet": paper_wallet_view(state)}


def paper_wallet_order(state: dict, *, symbol: str, side: str, price: float,
                       quantity: float | None = None, quote_amount: float | None = None,
                       fee_bps: float = 10.0, timestamp=None) -> dict:
    """Apply one simulated spot order at a supplied price (long-only)."""
    symbol = _paper_symbol(symbol)
    side = str(side or "").strip().lower()
    if side not in {"buy", "sell"}:
        raise ValueError("side must be buy or sell")
    if (quantity is None) == (quote_amount is None):
        raise ValueError("supply exactly one of quantity or quote_amount")
    unit_price = _paper_number(price, "price", maximum=100_000_000.0)
    fee_bps = _paper_number(fee_bps, "fee_bps", positive=False, maximum=500.0)
    fee_rate = fee_bps / 10_000.0
    positions = state.setdefault("positions", {})
    position = positions.get(symbol) or {"quantity": 0.0, "cost_basis": 0.0}
    held = float(position.get("quantity") or 0.0)
    if quantity is not None:
        qty = _paper_number(quantity, "quantity", maximum=1_000_000_000.0)
        gross = qty * unit_price
        fee = gross * fee_rate
    else:
        quote = _paper_number(quote_amount, "quote_amount", maximum=100_000_000.0)
        gross = quote / (1.0 + fee_rate) if side == "buy" else quote
        fee = gross * fee_rate
        qty = gross / unit_price
    cash = float(state.get("cash") or 0.0)
    realized = 0.0
    if side == "buy":
        total = gross + fee
        if total > cash + 1e-9:
            raise ValueError("insufficient PAPER_USD cash for this simulated buy")
        state["cash"] = cash - total
        position["quantity"] = held + qty
        position["cost_basis"] = float(position.get("cost_basis") or 0.0) + total
        positions[symbol] = position
    else:
        if qty > held + 1e-12:
            raise ValueError("cannot sell more than the simulated spot holding (no shorting/leverage)")
        proceeds = gross - fee
        cost_portion = float(position.get("cost_basis") or 0.0) * (qty / held) if held else 0.0
        realized = proceeds - cost_portion
        state["cash"] = cash + proceeds
        state["realized_pnl"] = float(state.get("realized_pnl") or 0.0) + realized
        remaining = held - qty
        if remaining <= 1e-12:
            positions.pop(symbol, None)
        else:
            position["quantity"] = remaining
            position["cost_basis"] = float(position.get("cost_basis") or 0.0) - cost_portion
            positions[symbol] = position
    state["total_fees"] = float(state.get("total_fees") or 0.0) + fee
    entry = _paper_ledger(
        state, "simulated_spot_order", symbol=symbol, side=side,
        quantity=_round(qty, 10), price=unit_price, gross=_round(gross, 4),
        fee=_round(fee, 4), fee_bps=fee_bps, realized_pnl=_round(realized, 4),
        timestamp=timestamp, execution="paper_only_no_broker")
    return {"order": entry, "wallet": paper_wallet_view(state, prices={symbol: unit_price})}


def paper_wallet_set_following(state: dict, *, following: bool) -> dict:
    state["following"] = bool(following)
    if following:
        state["halted"] = False
    _paper_ledger(state, "paper_follow_on" if following else "paper_follow_off",
                  note="Simulation control only; no broker connection exists.")
    return paper_wallet_view(state)


def paper_wallet_stop(state: dict, *, close_all: bool = False,
                      prices: dict | None = None, fee_bps: float = 10.0) -> dict:
    """Hard-stop paper following; optionally liquidate simulated spot holdings."""
    state["following"] = False
    state["halted"] = True
    _paper_ledger(state, "paper_trading_stopped", close_all=bool(close_all),
                  note="Hard halt for the simulation. No real orders exist to cancel.")
    if close_all:
        prices = prices or {}
        for symbol, raw in list((state.get("positions") or {}).items()):
            if symbol not in prices:
                raise ValueError(f"close_all needs a supplied mark price for {symbol}")
            qty = float(raw.get("quantity") or 0.0)
            if qty > 0:
                paper_wallet_order(state, symbol=symbol, side="sell", quantity=qty,
                                   price=prices[symbol], fee_bps=fee_bps)
    return paper_wallet_view(state, prices=prices)


def paper_follow_step(state: dict, *, symbol: str, bars,
                      timeframe: str = "source", strategy: str = "consensus",
                      allocation_pct: float = 10.0, fee_bps: float = 10.0,
                      drop_last_bar: bool = False) -> dict:
    """One deterministic paper-follow decision on the latest supplied closed bar.

    Long condition opens at most one capped spot paper position. Short
    condition exits a holding. The same symbol/timeframe/strategy bar cannot
    be processed twice. Set drop_last_bar=True when a feed includes a still-
    forming candle that the caller has not already removed.
    """
    symbol = _paper_symbol(symbol)
    if strategy not in STRATEGY_ENGINES:
        raise ValueError(f"unknown strategy '{strategy}'")
    allocation = _paper_number(allocation_pct, "allocation_pct", maximum=25.0)
    clean = normalize_bars(bars)
    requested = str(timeframe or "source")
    if requested != "source":
        if requested not in TIMEFRAMES:
            raise ValueError("timeframe must be source or one of the supported labels")
        base = infer_interval_seconds(clean)
        target = TIMEFRAMES[requested]
        if target < base:
            raise ValueError("requested timeframe is finer than the supplied source bars")
        if target > base:
            clean = resample_bars(clean, target)
    if drop_last_bar and len(clean) > 61:
        clean = clean[:-1]
    if len(clean) < 60:
        raise ValueError("paper follow needs at least 60 bars on the selected timeframe")
    signal = latest_signal(clean, strategy)
    latest = clean[-1]
    price = float(latest["c"])
    key = f"{symbol}|{requested}|{strategy}"
    decision = {
        "mode": "paper_simulation_only", "symbol": symbol, "timeframe": requested,
        "strategy": strategy, "latest_bar_time": _iso(int(latest["t"])),
        "latest_close": _round(price), "latest_signal": signal,
        "action": "no_action", "real_order_sent": False,
    }
    if state.get("halted", True) or not state.get("following"):
        decision["action"] = "blocked_stopped" if state.get("halted", True) else "blocked_not_following"
        decision["wallet"] = paper_wallet_view(state, prices={symbol: price})
        return decision
    last_seen = (state.get("last_follow_bars") or {}).get(key)
    if last_seen == int(latest["t"]):
        decision["action"] = "duplicate_bar_ignored"
        decision["wallet"] = paper_wallet_view(state, prices={symbol: price})
        return decision
    state.setdefault("last_follow_bars", {})[key] = int(latest["t"])
    position = (state.get("positions") or {}).get(symbol) or {}
    held = float(position.get("quantity") or 0.0)
    condition = signal.get("condition")
    if condition == "long_condition" and held <= 0:
        marked = paper_wallet_view(state, prices={symbol: price})
        quote = min(float(marked["equity"]) * allocation / 100.0, float(state.get("cash") or 0.0))
        if quote > 0:
            result = paper_wallet_order(
                state, symbol=symbol, side="buy", quote_amount=quote,
                price=price, fee_bps=fee_bps, timestamp=int(latest["t"]))
            decision["action"] = "simulated_buy"
            decision["order"] = result["order"]
        else:
            decision["action"] = "no_paper_cash"
    elif condition == "long_condition":
        decision["action"] = "hold_existing_simulated_position"
    elif condition == "short_condition" and held > 0:
        result = paper_wallet_order(
            state, symbol=symbol, side="sell", quantity=held,
            price=price, fee_bps=fee_bps, timestamp=int(latest["t"]))
        decision["action"] = "simulated_sell_exit"
        decision["order"] = result["order"]
    elif condition == "short_condition":
        decision["action"] = "short_condition_ignored_spot_long_only"
    else:
        decision["action"] = "hold_no_fresh_trigger"
    state.setdefault("follow_log", []).append({
        "symbol": symbol, "timeframe": requested, "strategy": strategy,
        "latest_bar_time": decision["latest_bar_time"], "action": decision["action"],
        "condition": condition, "latest_close": _round(price),
    })
    decision["wallet"] = paper_wallet_view(state, prices={symbol: price})
    return decision



# ---------------------------------------------------------------------------
# Halal-stock screen + full paper-trading bot (private/local simulation only)
# ---------------------------------------------------------------------------

SHARIAH_SCREEN_PRESETS = {
    "strict": {
        "interest_bearing_debt_max_pct": 30.0,
        "interest_bearing_cash_securities_max_pct": 30.0,
        "receivables_max_pct": 30.0,
        "non_compliant_income_max_pct": 5.0,
    },
    "balanced": {
        "interest_bearing_debt_max_pct": 33.0,
        "interest_bearing_cash_securities_max_pct": 33.0,
        "receivables_max_pct": 49.0,
        "non_compliant_income_max_pct": 5.0,
    },
}

PROHIBITED_CORE_ACTIVITIES = {
    "alcohol", "pork", "gambling", "casino", "conventional_banking",
    "conventional_insurance", "interest_lending", "riba_lending",
    "adult_entertainment", "pornography", "tobacco", "non_halal_meat",
}

HALAL_SCREEN_SPEC = {
    "purpose": "A transparent, user-configurable stock screen for the paper bot. It is software arithmetic on data the user supplies, NOT a fatwa and NOT a certification that any security is halal.",
    "bot_rule": "The bot may open a paper position only when asset_type is stock and the registered screen status is exactly pass. Missing data is needs_review, never pass.",
    "presets": SHARIAH_SCREEN_PRESETS,
    "required_profile_fields": [
        "symbol", "asset_type=stock", "core_business_prohibited (true/false)",
        "activities_reviewed=true", "interest_bearing_debt_pct_of_market_cap",
        "interest_bearing_cash_securities_pct_of_market_cap",
        "receivables_pct_of_market_cap", "non_compliant_income_pct_of_revenue",
    ],
    "prohibited_core_activities_examples": sorted(PROHIBITED_CORE_ACTIVITIES),
    "important_limits": [
        "Standards differ between scholars, indices and jurisdictions; choose the preset/thresholds you personally follow.",
        "TradeAtlas does not fetch or verify company accounts. Wrong or stale user inputs produce a wrong screen.",
        "A pass can expire when newer financial statements arrive; re-screen periodically.",
        "Dividend purification methods differ; any estimate shown must be checked with your chosen standard.",
    ],
}

HALAL_BOT_SPEC = {
    "mode": "halal_paper_bot_only",
    "universe": "registered assets whose current user-supplied halal screen status is pass (stocks use financial ratios; other classes require explicit spot/no-interest/no-leverage evidence)",
    "execution": "paper fills only; optional manual external-account checklist tickets are generated but never sent. No broker/exchange credentials, automatic real order, leverage, margin or short selling exists in TradeAtlas.",
    "controls": ["start", "resume", "pause", "stop", "reset_risk", "close_all_paper_positions"],
    "risk_controls": [
        "risk-per-trade position sizing from ATR stop distance",
        "allocation cap and maximum open positions",
        "stop-loss, take-profit and ATR trailing stop",
        "daily-loss and peak-equity drawdown halts for new entries",
        "minute-profile maximum entries per UTC day, maximum holding bars and post-exit cooldown",
        "simulated slippage and a minimum-ATR filter so tiny minute moves are not mistaken for cost-free trades",
        "duplicate-bar protection per symbol/strategy/timeframe",
    ],
    "automation_boundary": "The browser fetches market data and calls one bot cycle per interval while the page is open. The TradeAtlas server does not fetch arbitrary market URLs or hold trading credentials.",
    "real_money": False,
    "accepts_real_money_or_crypto": False,
    "deposit_address": None,
}


def _screen_ratio(profile: dict, field: str) -> float | None:
    value = profile.get(field)
    if value is None or value == "":
        return None
    return _paper_number(value, field, positive=False, maximum=1000.0)


def _normalized_activity(value) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def screen_halal_stock(profile: dict, *, preset: str = "strict") -> dict:
    """Screen one user-supplied stock profile under transparent thresholds.

    This is deliberately not called a certification. It can only classify the
    numbers/flags supplied by the user: `pass`, `needs_review`, or `fail`.
    """
    if not isinstance(profile, dict):
        raise ValueError("stock profile must be an object")
    preset_name = str(preset or "strict").strip().lower()
    if preset_name not in SHARIAH_SCREEN_PRESETS:
        raise ValueError(f"unknown halal screen preset '{preset_name}'")
    thresholds = dict(SHARIAH_SCREEN_PRESETS[preset_name])
    custom = profile.get("thresholds") or {}
    if custom:
        if not isinstance(custom, dict):
            raise ValueError("thresholds must be an object")
        for key, value in custom.items():
            if key in thresholds:
                thresholds[key] = _paper_number(value, f"thresholds.{key}", positive=False, maximum=1000.0)
    symbol = _paper_symbol(profile.get("symbol"))
    asset_type = str(profile.get("asset_type") or "stock").strip().lower()
    ratios = {
        "interest_bearing_debt_pct_of_market_cap": _screen_ratio(
            profile, "interest_bearing_debt_pct_of_market_cap"),
        "interest_bearing_cash_securities_pct_of_market_cap": _screen_ratio(
            profile, "interest_bearing_cash_securities_pct_of_market_cap"),
        "receivables_pct_of_market_cap": _screen_ratio(
            profile, "receivables_pct_of_market_cap"),
        "non_compliant_income_pct_of_revenue": _screen_ratio(
            profile, "non_compliant_income_pct_of_revenue"),
    }
    threshold_by_ratio = {
        "interest_bearing_debt_pct_of_market_cap": thresholds["interest_bearing_debt_max_pct"],
        "interest_bearing_cash_securities_pct_of_market_cap": thresholds["interest_bearing_cash_securities_max_pct"],
        "receivables_pct_of_market_cap": thresholds["receivables_max_pct"],
        "non_compliant_income_pct_of_revenue": thresholds["non_compliant_income_max_pct"],
    }
    activities = profile.get("prohibited_activities") or []
    if isinstance(activities, str):
        activities = [x for x in activities.replace(";", ",").split(",") if x.strip()]
    if not isinstance(activities, list):
        raise ValueError("prohibited_activities must be a list")
    activity_codes = sorted({_normalized_activity(x) for x in activities if _normalized_activity(x)})
    prohibited_present = [x for x in activity_codes if x in PROHIBITED_CORE_ACTIVITIES]
    failures: list[str] = []
    reviews: list[str] = []
    if asset_type != "stock":
        failures.append("asset_type is not stock; the halal bot universe is stocks only")
    if profile.get("core_business_prohibited") is True:
        failures.append("core_business_prohibited is true")
    elif profile.get("core_business_prohibited") is not False:
        reviews.append("core_business_prohibited must be explicitly true or false")
    if prohibited_present:
        failures.append("prohibited core activities present: " + ", ".join(prohibited_present))
    if profile.get("activities_reviewed") is not True:
        reviews.append("business activities have not been marked reviewed")
    for field, value in ratios.items():
        if value is None:
            reviews.append(f"missing {field}")
        elif value > float(threshold_by_ratio[field]):
            failures.append(f"{field}={value:g}% exceeds max {float(threshold_by_ratio[field]):g}%")
    if not str(profile.get("source_note") or "").strip():
        reviews.append("source_note is missing (write where the company figures came from)")
    expiry_raw = str(profile.get("review_expires_at") or "").strip()
    if expiry_raw:
        try:
            expiry_date = dt.date.fromisoformat(expiry_raw[:10])
            if expiry_date < dt.datetime.now(dt.timezone.utc).date():
                reviews.append("halal review has expired; re-screen with newer financials")
        except ValueError:
            reviews.append("review_expires_at must be an ISO date (YYYY-MM-DD)")
    status = "fail" if failures else "needs_review" if reviews else "pass"
    dividend = profile.get("dividend_per_share")
    purification = None
    if dividend is not None and ratios["non_compliant_income_pct_of_revenue"] is not None:
        dividend_value = _paper_number(dividend, "dividend_per_share", positive=False, maximum=1_000_000.0)
        purification = _round(
            dividend_value * float(ratios["non_compliant_income_pct_of_revenue"]) / 100.0, 8)
    normalized_profile = {
        "symbol": symbol,
        "company_name": str(profile.get("company_name") or "")[:120],
        "asset_type": asset_type,
        "sector": str(profile.get("sector") or "")[:120],
        "core_business_prohibited": profile.get("core_business_prohibited"),
        "activities_reviewed": profile.get("activities_reviewed") is True,
        "prohibited_activities": activity_codes,
        **ratios,
        "dividend_per_share": dividend,
        "source_note": str(profile.get("source_note") or "")[:300],
        "financials_as_of": str(profile.get("financials_as_of") or "")[:40],
        "review_expires_at": str(profile.get("review_expires_at") or "")[:40],
    }
    return {
        "symbol": symbol,
        "status": status,
        "can_bot_open_paper_position": status == "pass",
        "preset": preset_name,
        "thresholds": thresholds,
        "ratios": ratios,
        "failures": failures,
        "needs_review_reasons": reviews,
        "estimated_dividend_purification_per_share": purification,
        "purification_note": "Simple dividend × non-compliant-income-ratio estimate only; purification rules differ by standard.",
        "profile": normalized_profile,
        "certification": False,
        "warning": "Software screen on user-supplied figures, not a fatwa or halal certification.",
    }


ASSET_SCREEN_TYPES = ("stock", "crypto", "currency", "commodity", "etf", "fund")


def screen_halal_asset(profile: dict, *, preset: str = "strict") -> dict:
    """Screen any asset class with explicit user-reviewed evidence.

    Stocks use the financial-ratio screen. Other classes can pass only when
    the user explicitly confirms spot-only/no-interest/no-leverage/no-short
    conditions and the asset-specific review fields for their chosen standard.
    This is a rule engine over supplied evidence, not a fatwa.
    """
    if not isinstance(profile, dict):
        raise ValueError("asset profile must be an object")
    asset_type = str(profile.get("asset_type") or "stock").strip().lower()
    if asset_type == "stock":
        return screen_halal_stock(profile, preset=preset)
    symbol = _paper_symbol(profile.get("symbol"))
    failures: list[str] = []
    reviews: list[str] = []
    if asset_type not in ASSET_SCREEN_TYPES:
        failures.append(f"unsupported asset_type '{asset_type}'")
    required_true = {
        "activities_reviewed": "asset/activity has not been marked reviewed",
        "user_standard_allows_asset": "user's chosen standard has not explicitly allowed this asset/spot form",
        "spot_only": "only spot form is allowed by this paper-bot gate",
    }
    required_false = {
        "leverage_used": "leverage/margin is involved",
        "interest_or_swap_involved": "interest/swap/lending is involved",
        "short_selling_used": "short selling is involved",
    }
    if asset_type == "crypto":
        required_true.update({
            "project_activity_reviewed": "crypto project activity/utility has not been reviewed",
            "settlement_reviewed": "crypto spot settlement/custody form has not been reviewed",
        })
        required_false.update({
            "staking_or_lending_involved": "staking/lending/yield is involved in the planned form",
            "gambling_activity_involved": "gambling activity is involved",
        })
    elif asset_type == "currency":
        required_true.update({
            "spot_settlement_reviewed": "currency spot settlement/possession form has not been reviewed",
            "swap_free": "currency account/form is not marked swap-free",
        })
    elif asset_type == "commodity":
        required_true.update({
            "delivery_or_possession_reviewed": "commodity delivery/possession/settlement form has not been reviewed",
        })
    elif asset_type in {"etf", "fund"}:
        if profile.get("underlying_holdings_screen_status") != "pass":
            reviews.append("underlying holdings have not been separately screened as pass")
        required_false.update({
            "fund_uses_leverage_or_interest": "fund/ETF uses leverage or interest in a prohibited form",
        })
    for field, message in required_true.items():
        if profile.get(field) is not True:
            reviews.append(message)
    for field, message in required_false.items():
        if profile.get(field) is True:
            failures.append(message)
        elif profile.get(field) is not False:
            reviews.append(f"{field} must be explicitly false")
    activities = profile.get("prohibited_activities") or []
    if isinstance(activities, str):
        activities = [x for x in activities.replace(";", ",").split(",") if x.strip()]
    activity_codes = sorted({_normalized_activity(x) for x in activities if _normalized_activity(x)}) if isinstance(activities, list) else []
    prohibited = [x for x in activity_codes if x in PROHIBITED_CORE_ACTIVITIES]
    if prohibited:
        failures.append("prohibited activities present: " + ", ".join(prohibited))
    if profile.get("core_business_prohibited") is True:
        failures.append("core_business_prohibited is true")
    elif profile.get("core_business_prohibited") not in (False, None):
        reviews.append("core_business_prohibited must be true or false")
    if not str(profile.get("source_note") or "").strip():
        reviews.append("source_note is missing")
    expiry_raw = str(profile.get("review_expires_at") or "").strip()
    if expiry_raw:
        try:
            if dt.date.fromisoformat(expiry_raw[:10]) < dt.datetime.now(dt.timezone.utc).date():
                reviews.append("halal review has expired")
        except ValueError:
            reviews.append("review_expires_at must be an ISO date (YYYY-MM-DD)")
    status = "fail" if failures else "needs_review" if reviews else "pass"
    normalized = {
        "symbol": symbol, "company_name": str(profile.get("company_name") or profile.get("name") or "")[:120],
        "asset_type": asset_type, "sector": str(profile.get("sector") or "")[:120],
        "activities_reviewed": profile.get("activities_reviewed") is True,
        "prohibited_activities": activity_codes,
        "source_note": str(profile.get("source_note") or "")[:300],
        "financials_as_of": str(profile.get("financials_as_of") or profile.get("reviewed_as_of") or "")[:40],
        "review_expires_at": expiry_raw[:40],
        "evidence": {k: profile.get(k) for k in sorted(set(required_true) | set(required_false) | {
            "core_business_prohibited", "underlying_holdings_screen_status"})},
    }
    return {
        "symbol": symbol, "status": status,
        "can_bot_open_paper_position": status == "pass",
        "preset": preset, "thresholds": {}, "ratios": {},
        "failures": failures, "needs_review_reasons": reviews,
        "estimated_dividend_purification_per_share": None,
        "profile": normalized, "certification": False,
        "warning": "Software screen on user-supplied evidence, not a fatwa or halal certification.",
    }



def screen_halal_universe(profiles, *, preset: str = "strict") -> dict:
    if isinstance(profiles, dict):
        items = [{"symbol": symbol, **(value if isinstance(value, dict) else {})}
                 for symbol, value in profiles.items()]
    elif isinstance(profiles, list):
        items = profiles
    else:
        raise ValueError("profiles must be a list or an object keyed by symbol")
    rows = [screen_halal_asset(profile, preset=preset) for profile in items]
    return {
        "preset": preset,
        "pass": [r["symbol"] for r in rows if r["status"] == "pass"],
        "needs_review": [r["symbol"] for r in rows if r["status"] == "needs_review"],
        "fail": [r["symbol"] for r in rows if r["status"] == "fail"],
        "results": rows,
        "certification": False,
    }


MINUTE_BOT_DEFAULT_SETTINGS = {
    "mode_profile": "minute_scalping_paper", "strategy": "atlas_minute_pulse",
    "timeframe": "1m", "allocation_pct": 5.0, "max_positions": 3,
    "risk_per_trade_pct": 0.5, "atr_stop_multiple": 1.5,
    "take_profit_r_multiple": 1.5, "trailing_stop_atr_multiple": 1.5,
    "fee_bps": 10.0, "slippage_bps": 5.0, "max_daily_loss_pct": 2.0,
    "max_equity_drawdown_pct": 6.0, "max_trades_per_day": 20,
    "max_holding_bars": 30, "cooldown_bars": 3, "min_atr_pct": 0.02,
}


def _bot_settings(raw: dict | None = None, base: dict | None = None) -> dict:
    settings = {
        "mode_profile": "standard_paper",
        "strategy": "omni_consensus", "timeframe": "source",
        "allocation_pct": 10.0, "max_positions": 5, "risk_per_trade_pct": 1.0,
        "atr_stop_multiple": 2.0, "take_profit_r_multiple": 2.0,
        "trailing_stop_atr_multiple": 2.5, "fee_bps": 10.0, "slippage_bps": 0.0,
        "max_daily_loss_pct": 3.0, "max_equity_drawdown_pct": 10.0,
        "max_trades_per_day": 1000, "max_holding_bars": 0, "cooldown_bars": 0,
        "min_atr_pct": 0.0, "manual_confirmation_required": True,
        "live_execution_enabled": False, "allow_short": False,
    }
    if base:
        settings.update({k: v for k, v in base.items() if k in settings})
    if raw:
        if not isinstance(raw, dict):
            raise ValueError("bot settings must be an object")
        settings.update({k: v for k, v in raw.items() if k in settings})
    if raw is None and base is None:
        # A newly created v14 bot is minute-first by default. Imported/older
        # explicit settings keep their own strategy/timeframe.
        settings.update(MINUTE_BOT_DEFAULT_SETTINGS)
    if settings["strategy"] not in STRATEGY_ENGINES:
        raise ValueError(f"unknown bot strategy '{settings['strategy']}'")
    if settings["timeframe"] != "source" and settings["timeframe"] not in TIMEFRAMES:
        raise ValueError("bot timeframe must be source or a supported timeframe")
    settings["allocation_pct"] = _paper_number(settings["allocation_pct"], "allocation_pct", maximum=25.0)
    settings["risk_per_trade_pct"] = _paper_number(settings["risk_per_trade_pct"], "risk_per_trade_pct", maximum=2.0)
    settings["atr_stop_multiple"] = _paper_number(settings["atr_stop_multiple"], "atr_stop_multiple", maximum=10.0)
    settings["take_profit_r_multiple"] = _paper_number(settings["take_profit_r_multiple"], "take_profit_r_multiple", maximum=20.0)
    settings["trailing_stop_atr_multiple"] = _paper_number(settings["trailing_stop_atr_multiple"], "trailing_stop_atr_multiple", maximum=10.0)
    settings["fee_bps"] = _paper_number(settings["fee_bps"], "fee_bps", positive=False, maximum=500.0)
    settings["slippage_bps"] = _paper_number(settings["slippage_bps"], "slippage_bps", positive=False, maximum=500.0)
    settings["max_daily_loss_pct"] = _paper_number(settings["max_daily_loss_pct"], "max_daily_loss_pct", maximum=20.0)
    settings["max_equity_drawdown_pct"] = _paper_number(settings["max_equity_drawdown_pct"], "max_equity_drawdown_pct", maximum=50.0)
    settings["min_atr_pct"] = _paper_number(settings["min_atr_pct"], "min_atr_pct", positive=False, maximum=20.0)
    settings["mode_profile"] = str(settings["mode_profile"] or "standard_paper").strip().lower()
    if settings["mode_profile"] not in {"standard_paper", "minute_scalping_paper", "manual_live_companion"}:
        raise ValueError("mode_profile must be standard_paper, minute_scalping_paper or manual_live_companion")
    for field, low, high in (("max_positions", 1, 20), ("max_trades_per_day", 1, 5000),
                             ("max_holding_bars", 0, 100000), ("cooldown_bars", 0, 100000)):
        try:
            settings[field] = int(settings[field])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{field} must be an integer") from exc
        if not low <= settings[field] <= high:
            raise ValueError(f"{field} must be between {low} and {high}")
    # Hard safety boundary: settings can never enable shorts or real routing.
    settings["manual_confirmation_required"] = True
    settings["live_execution_enabled"] = False
    settings["allow_short"] = False
    return settings


def new_halal_paper_bot(*, starting_balance: float = 10_000.0,
                        preset: str = "strict", settings: dict | None = None) -> dict:
    if preset not in SHARIAH_SCREEN_PRESETS:
        raise ValueError(f"unknown halal screen preset '{preset}'")
    wallet = new_paper_wallet(starting_balance=starting_balance)
    return {
        "mode": "halal_paper_bot_only",
        "status": "stopped",
        "halal_only": True,
        "allowed_asset_types": list(ASSET_SCREEN_TYPES),
        "screen_preset": preset,
        "wallet": wallet,
        "registry": {},
        "position_meta": {},
        "settings": _bot_settings(settings),
        "last_bars": {},
        "decision_log": [],
        "entries_today": 0,
        "cooldown_until": {},
        "manual_tickets": [],
        "equity_peak": float(wallet["cash"]),
        "day_start_equity": float(wallet["cash"]),
        "day_key": None,
        "cycle_count": 0,
        "real_money": False,
        "accepts_real_money_or_crypto": False,
        "deposit_address": None,
        "broker_or_exchange_execution": False,
        "_seq": 0,
    }


def _validate_halal_bot(state: dict) -> None:
    if not isinstance(state, dict) or state.get("mode") != "halal_paper_bot_only":
        raise ValueError("invalid halal paper bot state")
    if not isinstance(state.get("wallet"), dict):
        raise ValueError("halal bot wallet is missing")
    paper_wallet_view(state["wallet"])  # validates paper state shape


def halal_bot_import_state(payload: dict) -> dict:
    """Validate a previously exported local paper-bot state."""
    if not isinstance(payload, dict):
        raise ValueError("bot state must be an object")
    state = {
        "mode": "halal_paper_bot_only",
        "status": str(payload.get("status") or "stopped"),
        "halal_only": True,
        "allowed_asset_types": list(ASSET_SCREEN_TYPES),
        "screen_preset": str(payload.get("screen_preset") or "strict"),
        "wallet": payload.get("wallet"),
        "registry": payload.get("registry") if isinstance(payload.get("registry"), dict) else {},
        "position_meta": payload.get("position_meta") if isinstance(payload.get("position_meta"), dict) else {},
        "settings": _bot_settings(payload.get("settings") if isinstance(payload.get("settings"), dict) else None),
        "last_bars": payload.get("last_bars") if isinstance(payload.get("last_bars"), dict) else {},
        "decision_log": payload.get("decision_log") if isinstance(payload.get("decision_log"), list) else [],
        "entries_today": int(payload.get("entries_today") or 0),
        "cooldown_until": payload.get("cooldown_until") if isinstance(payload.get("cooldown_until"), dict) else {},
        "manual_tickets": payload.get("manual_tickets") if isinstance(payload.get("manual_tickets"), list) else [],
        "equity_peak": float(payload.get("equity_peak") or 0.0),
        "day_start_equity": float(payload.get("day_start_equity") or 0.0),
        "day_key": payload.get("day_key"),
        "cycle_count": int(payload.get("cycle_count") or 0),
        "real_money": False,
        "accepts_real_money_or_crypto": False,
        "deposit_address": None,
        "broker_or_exchange_execution": False,
        "_seq": int(payload.get("_seq") or 0),
    }
    if state["status"] not in {"stopped", "paused", "running", "risk_halted"}:
        state["status"] = "stopped"
    if state["screen_preset"] not in SHARIAH_SCREEN_PRESETS:
        raise ValueError("invalid screen preset in bot state")
    _validate_halal_bot(state)
    if state["equity_peak"] <= 0:
        state["equity_peak"] = float(paper_wallet_view(state["wallet"])["equity"] or 0.0)
    if state["day_start_equity"] <= 0:
        state["day_start_equity"] = state["equity_peak"]
    return state


def halal_bot_view(state: dict, *, prices: dict | None = None) -> dict:
    _validate_halal_bot(state)
    wallet = paper_wallet_view(state["wallet"], prices=prices)
    equity = float(wallet["equity"] or 0.0)
    peak = max(float(state.get("equity_peak") or 0.0), equity)
    drawdown = 0.0 if peak <= 0 else max(0.0, (peak - equity) / peak * 100.0)
    day_start = float(state.get("day_start_equity") or equity)
    daily = 0.0 if day_start <= 0 else (equity / day_start - 1.0) * 100.0
    registry = {}
    for symbol, row in sorted((state.get("registry") or {}).items()):
        registry[symbol] = {
            "profile": dict((row or {}).get("profile") or {}),
            "screen": dict((row or {}).get("screen") or {}),
        }
    positions = []
    wallet_positions = {p["symbol"]: p for p in wallet.get("positions") or []}
    for symbol, raw in sorted((state.get("position_meta") or {}).items()):
        positions.append({"symbol": symbol, **dict(raw or {}),
                          "wallet_position": wallet_positions.get(symbol)})
    return {
        "mode": "halal_paper_bot_only",
        "status": state.get("status") or "stopped",
        "halal_only": True,
        "allowed_asset_types": list(ASSET_SCREEN_TYPES),
        "screen_preset": state.get("screen_preset") or "strict",
        "settings": _bot_settings(state.get("settings")),
        "wallet": wallet,
        "registry": registry,
        "position_meta": positions,
        "decision_log": [dict(x) for x in (state.get("decision_log") or [])][-200:],
        "manual_tickets": [dict(x) for x in (state.get("manual_tickets") or [])][-50:],
        "execution_mode": "paper_plus_manual_external_tickets",
        "live_execution_enabled": False,
        "entries_today": int(state.get("entries_today") or 0),
        "cooldown_until": dict(state.get("cooldown_until") or {}),
        "cycle_count": int(state.get("cycle_count") or 0),
        "goal_status": {"minute_focus": "v14_default_profile", "accuracy_target_pct": ACCURACY_TARGET_PCT,
                        "accuracy_goal_established": False},
        "risk": {
            "equity": _round(equity, 4), "equity_peak": _round(peak, 4),
            "drawdown_from_peak_pct": _round(drawdown, 4),
            "day_start_equity": _round(day_start, 4),
            "day_change_pct": _round(daily, 4), "day_key": state.get("day_key"),
        },
        "real_money": False,
        "accepts_real_money_or_crypto": False,
        "deposit_address": None,
        "broker_or_exchange_execution": False,
        "warning": "Paper bot only. A screen pass is not a fatwa/certification, and no real order can be sent.",
    }


def halal_bot_register_stock(state: dict, profile: dict, *, preset: str | None = None) -> dict:
    _validate_halal_bot(state)
    chosen = str(preset or state.get("screen_preset") or "strict")
    result = screen_halal_asset(profile, preset=chosen)
    state.setdefault("registry", {})[result["symbol"]] = {
        "profile": result["profile"], "screen": result,
    }
    return {"registration": result, "bot": halal_bot_view(state)}


def halal_bot_register_asset(state: dict, profile: dict, *, preset: str | None = None) -> dict:
    """Register any asset class; entries remain blocked unless screen status is pass."""
    return halal_bot_register_stock(state, profile, preset=preset)


def _bot_log(state: dict, **fields) -> dict:
    state["_seq"] = int(state.get("_seq") or 0) + 1
    entry = {"seq": state["_seq"], **fields}
    state.setdefault("decision_log", []).append(entry)
    if len(state["decision_log"]) > 1000:
        state["decision_log"] = state["decision_log"][-1000:]
    return entry


def halal_bot_set_status(state: dict, *, action: str) -> dict:
    _validate_halal_bot(state)
    action = str(action or "").strip().lower()
    wallet = state["wallet"]
    if action in {"start", "resume", "run"}:
        if state.get("status") == "risk_halted":
            raise ValueError("bot is risk-halted; use reset_risk after reviewing the paper account")
        state["status"] = "running"
        wallet["following"] = True; wallet["halted"] = False
    elif action == "pause":
        state["status"] = "paused"; wallet["following"] = False
    elif action == "stop":
        state["status"] = "stopped"; wallet["following"] = False; wallet["halted"] = True
    elif action == "reset_risk":
        view = paper_wallet_view(wallet)
        state["status"] = "stopped"; wallet["following"] = False; wallet["halted"] = True
        state["equity_peak"] = float(view["equity"] or 0.0)
        state["day_start_equity"] = float(view["equity"] or 0.0)
        state["day_key"] = None
        state["entries_today"] = 0
        state["cooldown_until"] = {}
    else:
        raise ValueError("bot action must be start, pause, stop or reset_risk")
    _bot_log(state, kind="status", action=action, status=state["status"], real_order_sent=False)
    return halal_bot_view(state)


def halal_bot_stop(state: dict, *, close_all: bool = False,
                   prices: dict | None = None, fee_bps: float = 10.0) -> dict:
    _validate_halal_bot(state)
    state["status"] = "stopped"
    paper_wallet_stop(state["wallet"], close_all=close_all, prices=prices, fee_bps=fee_bps)
    if close_all:
        state["position_meta"] = {}
    _bot_log(state, kind="stop", close_all=bool(close_all), real_order_sent=False)
    return halal_bot_view(state, prices=prices)


def _paper_internal_transfer(wallet_state: dict, bot_state: dict, *, amount: float,
                             direction: str) -> dict:
    _validate_halal_bot(bot_state)
    paper_wallet_view(wallet_state)
    bot_wallet = bot_state["wallet"]
    if wallet_state is bot_wallet:
        raise ValueError("standalone paper wallet and bot wallet must be different states")
    transfer = _paper_number(amount, "amount", maximum=100_000_000.0)
    if direction == "wallet_to_bot":
        source, destination = wallet_state, bot_wallet
        signed_to_bot = transfer
    elif direction == "bot_to_wallet":
        source, destination = bot_wallet, wallet_state
        signed_to_bot = -transfer
    else:
        raise ValueError("direction must be wallet_to_bot or bot_to_wallet")
    if transfer > float(source.get("cash") or 0.0) + 1e-9:
        raise ValueError("insufficient PAPER_USD cash in the source simulated wallet")
    source["cash"] = float(source.get("cash") or 0.0) - transfer
    destination["cash"] = float(destination.get("cash") or 0.0) + transfer
    current_bot_equity = float(paper_wallet_view(bot_wallet)["equity"] or 0.0)
    if signed_to_bot > 0:
        bot_state["equity_peak"] = float(bot_state.get("equity_peak") or 0.0) + signed_to_bot
        bot_state["day_start_equity"] = float(bot_state.get("day_start_equity") or 0.0) + signed_to_bot
    else:
        bot_state["equity_peak"] = max(current_bot_equity,
                                       float(bot_state.get("equity_peak") or 0.0) + signed_to_bot)
        bot_state["day_start_equity"] = max(0.0,
                                            float(bot_state.get("day_start_equity") or 0.0) + signed_to_bot)
    source_name = "standalone_paper_wallet" if direction == "wallet_to_bot" else "halal_paper_bot"
    destination_name = "halal_paper_bot" if direction == "wallet_to_bot" else "standalone_paper_wallet"
    _paper_ledger(source, "simulated_internal_transfer_out", amount=transfer,
                  destination=destination_name, real_transfer=False)
    _paper_ledger(destination, "simulated_internal_transfer_in", amount=transfer,
                  source=source_name, real_transfer=False)
    _bot_log(bot_state, kind="simulated_internal_transfer", direction=direction,
             amount=transfer, real_order_sent=False, real_transfer=False)
    return {
        "transfer": {"direction": direction, "amount_paper_usd": _round(transfer, 4),
                     "real_transfer": False, "blockchain_transfer": False,
                     "deposit_address": None},
        "wallet": paper_wallet_view(wallet_state),
        "bot": halal_bot_view(bot_state),
    }


def paper_transfer_wallet_to_bot(wallet_state: dict, bot_state: dict, *, amount: float) -> dict:
    """Move imaginary PAPER_USD from the demo e-wallet into the paper bot."""
    return _paper_internal_transfer(wallet_state, bot_state, amount=amount,
                                    direction="wallet_to_bot")


def paper_transfer_bot_to_wallet(wallet_state: dict, bot_state: dict, *, amount: float) -> dict:
    """Move imaginary PAPER_USD from the paper bot back to the demo e-wallet."""
    return _paper_internal_transfer(wallet_state, bot_state, amount=amount,
                                    direction="bot_to_wallet")


def _manual_execution_ticket(*, symbol: str, side: str, quantity: float,
                             reference_price: float, timeframe: str, strategy: str,
                             stop_loss=None, take_profit=None, reason: str = "") -> dict:
    """Checklist for the user's own external account; never an order transmission."""
    qty = float(quantity or 0.0)
    price = float(reference_price or 0.0)
    return {
        "ticket_type": "manual_external_execution_checklist",
        "status": "not_sent_requires_user_manual_confirmation_in_own_account",
        "venue": "YOUR_OWN_LICENSED_EXCHANGE_OR_BROKER_ONLY",
        "funding_assets_supported_by_workflow": ["USDT", "BTC", "USD"],
        "funding_location": "user's own external account; never TradeAtlas",
        "symbol": symbol, "side": side, "quantity": _round(qty, 10),
        "reference_price": _round(price, 8),
        "reference_notional_usd": _round(qty * price, 4),
        "timeframe": timeframe, "strategy": strategy,
        "stop_loss_reference": _round(stop_loss, 8) if stop_loss is not None else None,
        "take_profit_reference": _round(take_profit, 8) if take_profit is not None else None,
        "reason_from_paper_bot": str(reason or "")[:240],
        "checks_before_any_manual_action": [
            "Confirm the exact symbol, spot form, network/venue and current halal evidence yourself.",
            "Check live spread, fees, minimum order, liquidity and whether the reference price is still available.",
            "Confirm USDT/BTC is already in your own licensed account; do not send anything to TradeAtlas.",
            "Decide independently; this checklist is not financial advice.",
            "Place any order manually only in your own account, then record the actual fill and fees outside the paper result.",
        ],
        "real_order_sent": False, "api_key_accepted": False,
        "deposit_address": None, "broker_or_exchange_execution": False,
    }


def _bot_prepare_bars(payload, timeframe: str, drop_last_bar: bool) -> list[dict]:
    if isinstance(payload, dict) and "csv" in payload:
        bars = parse_csv(str(payload["csv"]))
    elif isinstance(payload, dict) and "csv_text" in payload:
        bars = parse_csv(str(payload["csv_text"]))
    elif isinstance(payload, dict) and "bars" in payload:
        bars = normalize_bars(payload["bars"])
    else:
        bars = normalize_bars(payload)
    if timeframe != "source":
        base = infer_interval_seconds(bars); target = TIMEFRAMES[timeframe]
        if target < base:
            raise ValueError("requested timeframe is finer than supplied source bars")
        if target > base:
            bars = resample_bars(bars, target)
    if drop_last_bar and len(bars) > 61:
        bars = bars[:-1]
    if len(bars) < 60:
        raise ValueError("bot needs at least 60 bars on the selected timeframe")
    return bars


def halal_bot_step(state: dict, *, market_data: dict,
                   settings: dict | None = None, drop_last_bar: bool = False) -> dict:
    """Run one automated paper-bot cycle over registered halal-screened stocks.

    Entries are long-only spot paper fills. Before any entry, every open bot
    position is checked against its ATR stop, target and trailing stop. A
    risk halt blocks new entries but still processes protective exits.
    """
    _validate_halal_bot(state)
    if not isinstance(market_data, dict) or not market_data:
        raise ValueError("market_data must map stock symbols to bars")
    if settings is not None:
        state["settings"] = _bot_settings(settings, base=state.get("settings"))
    cfg = _bot_settings(state.get("settings"))
    state["settings"] = cfg
    prepared: dict[str, list[dict]] = {}
    prices: dict[str, float] = {}
    errors: dict[str, str] = {}
    for raw_symbol, payload in list(market_data.items())[:12]:
        try:
            symbol = _paper_symbol(raw_symbol)
            bars = _bot_prepare_bars(payload, cfg["timeframe"], bool(drop_last_bar))
            prepared[symbol] = bars; prices[symbol] = float(bars[-1]["c"])
        except (TypeError, ValueError, KeyError) as exc:
            errors[str(raw_symbol)] = str(exc)[:220]
    state["cycle_count"] = int(state.get("cycle_count") or 0) + 1
    wallet = state["wallet"]
    marked = paper_wallet_view(wallet, prices=prices)
    equity = float(marked["equity"] or 0.0)
    if prepared:
        latest_time = max(int(bars[-1]["t"]) for bars in prepared.values())
        day_key = _iso(latest_time)[:10]
        if state.get("day_key") != day_key:
            state["day_key"] = day_key; state["day_start_equity"] = equity
            state["entries_today"] = 0
    state["equity_peak"] = max(float(state.get("equity_peak") or 0.0), equity)
    peak = float(state["equity_peak"] or equity)
    drawdown_pct = 0.0 if peak <= 0 else max(0.0, (peak - equity) / peak * 100.0)
    day_start = float(state.get("day_start_equity") or equity)
    day_loss_pct = 0.0 if day_start <= 0 else max(0.0, (day_start - equity) / day_start * 100.0)
    risk_block_entries = False
    risk_reason = None
    if state.get("status") == "running" and (
            drawdown_pct >= float(cfg["max_equity_drawdown_pct"])
            or day_loss_pct >= float(cfg["max_daily_loss_pct"])):
        state["status"] = "risk_halted"; wallet["following"] = False; wallet["halted"] = True
        risk_block_entries = True
        risk_reason = (f"risk halt: drawdown {drawdown_pct:.3f}% / daily loss {day_loss_pct:.3f}%")
    elif state.get("status") == "risk_halted":
        risk_block_entries = True; risk_reason = "risk halted; review and reset_risk before new entries"

    decisions: list[dict] = []
    status = str(state.get("status") or "stopped")
    for symbol in sorted(prepared):
        bars = prepared[symbol]; latest = bars[-1]; price = float(latest["c"])
        try:
            bar_interval_seconds = TIMEFRAMES.get(cfg["timeframe"]) or infer_interval_seconds(bars)
        except ValueError:
            bar_interval_seconds = 60
        key = f"{symbol}|{cfg['timeframe']}|{cfg['strategy']}"
        registry_row = (state.get("registry") or {}).get(symbol) or {}
        screen = registry_row.get("screen") or {}
        profile = registry_row.get("profile") or {}
        snapshot = indicator_snapshot(bars)
        signal = latest_signal(bars, cfg["strategy"])
        decision = {
            "symbol": symbol, "timeframe": cfg["timeframe"], "strategy": cfg["strategy"],
            "latest_bar_time": _iso(int(latest["t"])), "latest_close": _round(price),
            "halal_screen_status": screen.get("status") or "not_registered",
            "asset_type": profile.get("asset_type"),
            "latest_signal": signal, "snapshot_atr14": snapshot.get("atr14"),
            "mode_profile": cfg["mode_profile"], "slippage_bps": cfg["slippage_bps"],
            "entries_today_before_decision": int(state.get("entries_today") or 0),
            "action": "no_action", "real_order_sent": False,
        }
        if status in {"stopped", "paused"}:
            decision["action"] = "blocked_stopped" if status == "stopped" else "blocked_paused"
            decisions.append(decision); _bot_log(state, kind="decision", **decision); continue
        if (state.get("last_bars") or {}).get(key) == int(latest["t"]):
            decision["action"] = "duplicate_bar_ignored"
            decisions.append(decision); _bot_log(state, kind="decision", **decision); continue
        state.setdefault("last_bars", {})[key] = int(latest["t"])
        held = float(((wallet.get("positions") or {}).get(symbol) or {}).get("quantity") or 0.0)
        meta = dict((state.get("position_meta") or {}).get(symbol) or {})
        atr_value = snapshot.get("atr14")
        atr_number = float(atr_value) if atr_value not in (None, 0) else max(price * 0.01, 1e-9)
        exited = False
        if held > 0:
            if not meta:
                raw_position = (wallet.get("positions") or {}).get(symbol) or {}
                avg = (float(raw_position.get("cost_basis") or 0.0) / held) if held else price
                stop_distance = atr_number * float(cfg["atr_stop_multiple"])
                meta = {"entry_price": avg, "entry_timestamp": int(latest["t"]),
                        "entry_timestamp_estimated_for_legacy_position": True,
                        "stop_loss": avg - stop_distance,
                        "take_profit": avg + float(cfg["take_profit_r_multiple"]) * stop_distance,
                        "trailing_high": float(latest["h"]), "quantity_at_entry": held}
            meta["trailing_high"] = max(float(meta.get("trailing_high") or latest["h"]), float(latest["h"]))
            trailing_stop = float(meta["trailing_high"]) - atr_number * float(cfg["trailing_stop_atr_multiple"])
            effective_stop = max(float(meta.get("stop_loss") or 0.0), trailing_stop)
            meta["effective_stop"] = _round(effective_stop, 8)
            meta["trailing_stop"] = _round(trailing_stop, 8)
            entry_timestamp = meta.get("entry_timestamp")
            if entry_timestamp is None and meta.get("entry_time"):
                try:
                    entry_timestamp = _parse_timestamp(meta["entry_time"])
                except ValueError:
                    entry_timestamp = int(latest["t"])
            holding_bars = (sum(1 for b in bars if int(b["t"]) > int(entry_timestamp))
                            if entry_timestamp is not None else 0)
            meta["holding_bars_seen"] = int(holding_bars)
            state.setdefault("position_meta", {})[symbol] = meta
            exit_reason = None
            if float(latest["l"]) <= effective_stop:
                exit_reason = "stop_or_trailing_stop_touched"
            elif float(meta.get("take_profit") or float("inf")) <= float(latest["h"]):
                exit_reason = "take_profit_touched"
            elif int(cfg["max_holding_bars"]) > 0 and holding_bars >= int(cfg["max_holding_bars"]):
                exit_reason = "max_holding_bars_reached"
            elif signal.get("condition") == "short_condition":
                exit_reason = "mechanical_short_condition_exit"
            if exit_reason:
                exit_execution_price = price * (1.0 - float(cfg["slippage_bps"]) / 10_000.0)
                result = paper_wallet_order(
                    wallet, symbol=symbol, side="sell", quantity=held, price=exit_execution_price,
                    fee_bps=float(cfg["fee_bps"]), timestamp=int(latest["t"]))
                state.get("position_meta", {}).pop(symbol, None)
                if int(cfg["cooldown_bars"]) > 0:
                    state.setdefault("cooldown_until", {})[symbol] = (
                        int(latest["t"]) + int(cfg["cooldown_bars"]) * int(bar_interval_seconds))
                ticket = _manual_execution_ticket(
                    symbol=symbol, side="sell_exit_spot_holding", quantity=held,
                    reference_price=exit_execution_price, timeframe=cfg["timeframe"],
                    strategy=cfg["strategy"], stop_loss=meta.get("stop_loss"),
                    take_profit=meta.get("take_profit"), reason=exit_reason)
                state.setdefault("manual_tickets", []).append(ticket)
                state["manual_tickets"] = state["manual_tickets"][-200:]
                decision["action"] = "simulated_exit"; decision["exit_reason"] = exit_reason
                decision["simulated_execution_price"] = _round(exit_execution_price, 8)
                decision["manual_execution_ticket"] = ticket
                decision["order"] = result["order"]; exited = True; held = 0.0
        if not exited:
            if held > 0:
                decision["action"] = "hold_existing_paper_position"
                decision["position_meta"] = dict((state.get("position_meta") or {}).get(symbol) or {})
            elif risk_block_entries:
                decision["action"] = "blocked_risk_halt"; decision["risk_reason"] = risk_reason
            elif screen.get("status") != "pass" or profile.get("asset_type") not in ASSET_SCREEN_TYPES:
                decision["action"] = "blocked_not_halal_pass"
                decision["halal_failures"] = screen.get("failures") or []
                decision["halal_review_reasons"] = screen.get("needs_review_reasons") or ["stock is not registered/screened"]
            elif signal.get("condition") == "long_condition":
                current_view = paper_wallet_view(wallet, prices=prices)
                current_equity = float(current_view["equity"] or 0.0)
                open_positions = len(current_view.get("positions") or [])
                cooldown_until = int((state.get("cooldown_until") or {}).get(symbol) or 0)
                atr_pct = atr_number / price * 100.0 if price else 0.0
                decision["atr_pct_of_price"] = _round(atr_pct, 6)
                if int(state.get("entries_today") or 0) >= int(cfg["max_trades_per_day"]):
                    decision["action"] = "blocked_max_trades_per_day"
                elif int(latest["t"]) <= cooldown_until:
                    decision["action"] = "blocked_cooldown"
                    decision["cooldown_until_utc"] = _iso(cooldown_until)
                elif atr_pct < float(cfg["min_atr_pct"]):
                    decision["action"] = "blocked_volatility_too_low_for_costs"
                elif open_positions >= int(cfg["max_positions"]):
                    decision["action"] = "blocked_max_positions"
                else:
                    entry_execution_price = price * (1.0 + float(cfg["slippage_bps"]) / 10_000.0)
                    stop_distance = max(atr_number * float(cfg["atr_stop_multiple"]), entry_execution_price * 0.001)
                    risk_quantity = (current_equity * float(cfg["risk_per_trade_pct"]) / 100.0) / stop_distance
                    allocation_quantity = (current_equity * float(cfg["allocation_pct"]) / 100.0) / entry_execution_price
                    fee_rate = float(cfg["fee_bps"]) / 10_000.0
                    cash_quantity = float(wallet.get("cash") or 0.0) / (entry_execution_price * (1.0 + fee_rate))
                    quantity = min(risk_quantity, allocation_quantity, cash_quantity)
                    if quantity <= 0:
                        decision["action"] = "no_paper_cash_or_risk_budget"
                    else:
                        result = paper_wallet_order(
                            wallet, symbol=symbol, side="buy", quantity=quantity,
                            price=entry_execution_price,
                            fee_bps=float(cfg["fee_bps"]), timestamp=int(latest["t"]))
                        meta = {
                            "entry_price": _round(entry_execution_price, 8),
                            "reference_close": _round(price, 8),
                            "entry_time": _iso(int(latest["t"])),
                            "entry_timestamp": int(latest["t"]),
                            "quantity_at_entry": _round(quantity, 10),
                            "stop_loss": _round(entry_execution_price - stop_distance, 8),
                            "take_profit": _round(entry_execution_price + float(cfg["take_profit_r_multiple"]) * stop_distance, 8),
                            "trailing_high": float(latest["h"]),
                            "atr_at_entry": _round(atr_number, 8),
                            "halal_screen_status_at_entry": screen.get("status"),
                        }
                        state.setdefault("position_meta", {})[symbol] = meta
                        state["entries_today"] = int(state.get("entries_today") or 0) + 1
                        ticket = _manual_execution_ticket(
                            symbol=symbol, side="buy_spot_long_only", quantity=quantity,
                            reference_price=entry_execution_price, timeframe=cfg["timeframe"],
                            strategy=cfg["strategy"], stop_loss=meta["stop_loss"],
                            take_profit=meta["take_profit"],
                            reason=(signal.get("last_event") or {}).get("reason") or signal.get("message") or "")
                        state.setdefault("manual_tickets", []).append(ticket)
                        state["manual_tickets"] = state["manual_tickets"][-200:]
                        decision["action"] = "simulated_buy"; decision["order"] = result["order"]
                        decision["simulated_execution_price"] = _round(entry_execution_price, 8)
                        decision["manual_execution_ticket"] = ticket
                        decision["position_meta"] = meta
            elif signal.get("condition") == "short_condition":
                decision["action"] = "short_condition_ignored_long_only_spot"
            else:
                decision["action"] = "hold_no_fresh_trigger"
        decisions.append(decision)
        _bot_log(state, kind="decision", **decision)
    return {
        "mode": "halal_paper_bot_only", "cycle": int(state["cycle_count"]),
        "status": state.get("status"), "decisions": decisions, "errors": errors,
        "bot": halal_bot_view(state, prices=prices), "real_order_sent": False,
    }



DATA_GUIDE = [
    {"step": "1. Export real bars you already have a right to use",
     "detail": "Broker/exchange history export, TradingView chart data export (paid plans), "
               "or your data vendor's CSV download. TradeAtlas ships no licensed live feed."},
    {"step": "2. Match the canonical columns",
     "detail": "timestamp,open,high,low,close,volume (aliases like Date/AAPL.Close are "
               "converted by you before upload; UNIX seconds or ISO dates both parse)."},
    {"step": "3. Decide adjusted vs raw — and write it down",
     "detail": "Splits/dividends make raw series jump. State which you used; results from "
               "mixed series are not comparable."},
    {"step": "4. Intraday claims need intraday files",
     "detail": "Daily bars honestly support only 1d/1w here. Nobody can reconstruct 5-minute "
               "history from daily bars; anyone who claims otherwise is fabricating data."},
    {"step": "5. Judge forecasters out-of-sample or not at all",
     "detail": "Use the Forecast Lab's rolling evaluation: hide the future, forecast, check, "
               "repeat 100 times, and demand it beat always-up/momentum baselines before "
               "believing any 'edge' — then re-test on a second symbol and era."},
]


def lab_spec() -> dict:
    return {
        "name": "TradeAtlas Market Lab",
        "version": "15.0",
        "timeframes": TIMEFRAMES,
        "strategies": STRATEGY_ENGINES,
        "indicators": ["SMA20/50/200", "EMA20/50", "RSI(14)", "MACD(12,26,9)",
                       "Bollinger Bands(20,2)", "ATR(14)", "Stochastic %K/%D (14,3)",
                       "ADX(14) with +DI/-DI", "Aroon(25)", "Vortex(14)",
                       "Chande Momentum(14)", "Fisher Transform(10)", "RVI(10)",
                       "Schaff Trend Cycle", "KST", "Coppock", "Chaikin Money Flow(20)",
                       "Money Flow Index(14)", "Elder Force Index(13)", "Ulcer Index(14)",
                       "Ehlers SuperSmoother", "permutation entropy",
                       "multiscale trend score", "Signed Path Pressure (TradeAtlas)",
                       "Entropy-Weighted Trend (TradeAtlas)", "CCI(20)", "Williams %R(14)",
                       "True Strength Index", "TRIX(15)", "Ultimate Oscillator",
                       "Parabolic SAR", "Ichimoku score", "OBV slope",
                       "log-regression trend", "Kalman local trend", "Omni direct consensus (TradeAtlas)",
                       "Hull MA(20)", "Supertrend(10,3)", "Kaufman AMA", "Haar wavelet trend", "Donchian state",
                       "Atlas Pressure Wave (TradeAtlas)", "Atlas Regime Compass (TradeAtlas)",
                       "Atlas Phoenix Fusion (TradeAtlas)", "Atlas Meta Hedge (online, delayed labels)",
                       "Atlas Online Logistic (online SGD, delayed labels)",
                       "rolling VWAP(60)", "EMA ribbon 5/13/34", "RSI(2)", "UTC opening range",
                       "Bollinger bandwidth squeeze percentile", "relative-volume surge",
                       "Atlas Minute Pulse (TradeAtlas v14)"],
        "market_presets": MARKET_PRESETS,
        "features": ["per-timeframe latest mechanical long/short condition",
                     "100-signal historical validation (next-bar entry, cost-adjusted, no overlaps)",
                     "all-engine strategy tournament per timeframe",
                     "70/30 walk-forward robustness split",
                     "equity curve points per backtest",
                     "multi-symbol watchlist heatmap (POST /api/lab/watchlist)",
                     "Forecast Lab: historical-analog distributions for the latest setup "
                     "(POST /api/lab/forecast) — what followed look-alike setups, never a price call",
                     "rolling out-of-sample forecast evaluation (100 hidden-future attempts "
                     "vs always-up/momentum/mean-reversion baselines, Brier skill)",
                     "multi-horizon evaluation (1/3/5/10/20 bars) — single-horizon 'edges' exposed",
                     "regime-split accuracy (trend vs causal SMA-20; volatility vs trailing median)",
                     "analog path simulation: bootstrap over REAL look-alike paths with terminal "
                     "and max-drawdown percentiles (dispersion picture, not a forecast)",
                     "ensemble evaluation: analog median vs distance-weighted analogs vs "
                     "momentum vs majority vote vs agreement-only filter (accuracy WITH coverage)",
                     "cost-aware re-scoring: win rate and mean net per trade after 10/25 bps "
                     "round-trip costs vs always-long — direction accuracy alone is half the truth",
                     "candle-structure analog race: gap/range/body/wicks/close-location/volume "
                     "neighbours tested beside return analogs under the same no-lookahead rule; "
                     "close-only series are marked unavailable instead of inventing candle anatomy",
                     "indicator-regime analog race (v8): RSI slope, ATR-normalized MACD, Bollinger "
                     "%B/bandwidth, SMA distance/slope, Donchian/Stochastic position, ADX balance, "
                     "volatility regime and volume surprise matched under j + horizon <= origin; "
                     "majority_vote_v3 and a coverage-labelled consensus_3plus subset join the race",
                     "path-geometry analog race + causal adaptive selector (v9): travel efficiency, "
                     "volatility-normalized trend slopes, variance ratio, autocorrelation, skew, "
                     "60-bar excursion/drawdown position, volatility/range compression, streaks and "
                     "real up/down volume balance; majority_vote_v4 joins the race and "
                     "adaptive_selector follows only candidates proven on fully revealed prior "
                     "attempts (old_origin + horizon <= current origin), never unfinished windows",
                     "cycle/flow analog race + direct multiscale trend (v10): Aroon/Vortex/CMO/"
                     "Fisher/RVI/Schaff/KST/Coppock/CMF/MFI/Force/rolling-VWAP/Ulcer/SuperSmoother/"
                     "permutation-entropy neighbours, TradeAtlas Signed Path Pressure and "
                     "Entropy-Weighted Trend, majority_vote_v5, a fixed 3/5/10/20/60/120-bar "
                     "volatility-normalized trend contestant, its multi-horizon hidden-future rows, "
                     "and coverage-labelled confidence diagnostics that cannot win best-method",
                     "five new signal engines on every honest timeframe (Schaff cycle, Vortex, "
                     "Fisher reversal, KST and entropy-gated multiscale trend) — 14 engines total",
                     "v11 direct forecast race: causal Kalman local-trend slope, fixed Omni direct consensus (multiscale + Kalman + horizon-matched trend + Parabolic SAR + CCI/Williams/TSI/TRIX/Ultimate/CMO/Fisher/Schaff basket), rank-fusion neighbours across all five analog families, majority_vote_v6 and direct-method rows at neighbouring horizons",
                     "six additional signal engines in v11 (CCI, Williams %R, Parabolic SAR, Ichimoku, Kalman trend, Omni consensus) — 20 engines total",
                     "halal-stock paper bot: registered user-supplied Shariah-screen profiles (pass/needs_review/fail, never a certification), stocks-only long spot paper entries, ATR risk sizing, stop/target/trailing exits, daily/drawdown halts, Start/Pause/STOP and duplicate-bar protection",
                     "v12 direct/statistical race: Hull trend, Supertrend, Kaufman AMA, Haar wavelet trend, causal Markov trend/volatility/RSI regime outcomes, Atlas Fusion v12 and majority_vote_v7 — 24 signal engines at that version",
                     "v13 forecast race: Aroon/TSI/TRIX/CMO/Ultimate/RVI/log-regression/Donchian/OBV/Coppock direct signs, invented Atlas Pressure Wave + Regime Compass + family-balanced Phoenix Fusion, majority_vote_v8, and two delayed-label online learners (Meta Hedge exponential weights and L2 online logistic SGD) — all under old_origin + horizon <= current origin",
                     "thirteen additional v13 signal engines on every honest timeframe (Aroon, TSI, TRIX, CMO, Ultimate reversal, RVI, regression, Donchian, OBV flow, Coppock, Pressure Wave, Regime Compass, Phoenix) — 37 engines at v13",
                     "v14 minute-first layer: seven additional engines (rolling-VWAP reversion, EMA ribbon, RSI-2 snapback, UTC opening-range breakout, Bollinger squeeze release, volume-surge pressure and invented Atlas Minute Pulse) — 44 engines total",
                     "v14 minute hidden-future race at 1/3/5/15/30 bars with coverage, Wilson intervals and 5/10/25-bps costs, plus an explicit 80% goal gate requiring 1000+ attempts and external multi-symbol/day validation before any strong claim",
                     "v15 failure memory (Atlas self-correction): every failed method x horizon is "
                     "diagnosed against an explicit cause library (sample too small, coverage too low, "
                     "baseline not beaten, cost-eaten edge, single-horizon overfit, walk-forward decay, "
                     "regime dependence, drawdown, selection bias, missing volume, remedy-starved sample...), "
                     "each cause carries an avoid-rule plus an implemented remedy, the next round re-tests "
                     "only what can still be saved with that remedy applied, resolved causes are kept as "
                     "reusable lessons, recurring causes retire the candidate with its reason, and later "
                     "runs skip candidates their stored lessons already proved hopeless — the 80% goal is "
                     "still never claimed",
                     "POST /api/lab/self-correct runs the loop over one or two series and GET /api/lessons "
                     "returns the persisted lesson ledger with resolved/recurred/retired status",
                     "v14 minute bot profile: 1m/Atlas Minute Pulse defaults, simulated slippage, entries-per-day cap, maximum holding bars, cooldown, minimum-ATR filter, external-account balance mirror and manual execution checklist tickets; live routing remains disabled",
                     "v12 all-asset halal gate: stocks use financial ratios; crypto/currency/commodity/ETF/fund profiles require explicit user-reviewed spot/no-interest/no-leverage/no-short evidence and can expire to needs_review; missing evidence never passes",
                     "SQLite market database in the web app: instruments, OHLCV bars, halal profiles/screens, imports and pooled hidden-future research runs with method leaderboards",
                     "bundled real historical samples with provenance notice (real-data/)",
                     "browser-polled bring-your-own live feed and browser-direct public real-market adapters",
                     "demo e-wallet simulation: imaginary crypto balances, balance-to-PAPER_USD conversion at a user-typed rate, imaginary withdrawal accounting, PAPER_USD internal transfer to/from the halal paper bot, spot long-only paper positions, Follow/Pause/Resume/STOP controls and duplicate-bar protection — no real deposits, custody, withdrawals, leverage or broker execution"],
        "data_guide": DATA_GUIDE,
        "feed": FEED_SPEC,
        "real_market_feeds": REAL_MARKET_FEEDS,
        "paper_wallet": PAPER_WALLET_SPEC,
        "halal_screen": HALAL_SCREEN_SPEC,
        "halal_paper_bot": HALAL_BOT_SPEC,
        "project_goals": project_goals(),
        "validation_defaults": {"max_signals": 100, "horizon_bars": 5, "round_trip_cost_bps": 10,
                                "primary_timeframe": "1m", "minute_timeframes": list(MINUTE_TIMEFRAMES),
                                "minute_horizons_bars": [1, 3, 5, 15, 30],
                                "accuracy_target_pct": ACCURACY_TARGET_PCT,
                                "accuracy_goal_established": False},
        "disclaimer": DISCLAIMER,
    }
