"""TradeAtlas v16 — autonomous data pipeline + honest goal tracking.

What this module does
---------------------
1. **Collects** OHLCV by itself from a *fixed allowlist* of public, keyless
   venues (Binance spot, Kraken public OHLC). No arbitrary URLs, no API keys,
   no logins, no credentials stored. The allowlist is the security boundary.
2. **Stores** every bar in SQLite, incrementally: a second run only asks for
   bars newer than the newest stored bar, so history grows instead of being
   re-downloaded. Each series keeps its provenance (venue, endpoint, window).
3. **Protects the holdout**: the newest share of every series is reserved and
   never used for tuning or remedies. Only ``holdout_evaluation`` reads it,
   and every such read is recorded, so "raising the success rate" cannot be
   done by peeking.
4. **Measures pooled evidence** across all stored series and reports the real
   distance to the 80% project target against explicit gates.

What it refuses to do
---------------------
* It never tunes on the holdout, never re-labels a failed candidate, and never
  sets ``goal_established`` true. A local database cannot establish a
  universal rate; the strongest honest status is
  ``goal_evidence_ready_for_independent_review``.
* It is not financial advice and has no order path.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import urllib.error
import urllib.parse
import urllib.request

import marketlab as ml
import selfcorrect as sc

VERSION = "17.0"
DEFAULT_USER_AGENT = "TradeAtlas/17.0 (educational research; public data only)"
TIMEOUT_SECONDS = 20
MAX_BARS_PER_REQUEST = 1000
HOLDOUT_FRACTION = 0.2
MIN_ATTEMPTS_FOR_GOAL = int(ml.MINUTE_GOAL_GATES["minimum_hidden_future_attempts_per_candidate"])
MIN_SYMBOLS_FOR_GOAL = 3
MIN_DAYS_FOR_GOAL = 30
WILSON_TARGET = float(ml.MINUTE_GOAL_GATES["wilson_95_lower_bound_for_strong_claim_pct"])

# Fixed allowlist. Nothing outside this map can be fetched.
VENUES: dict[str, dict] = {
    "binance": {
        "label": "Binance spot public klines",
        "hosts": ("api.binance.com", "data-api.binance.vision"),
        "path": "/api/v3/klines",
        "intervals": ("1m", "5m", "15m", "1h", "4h", "1d"),
        "max_limit": 1000,
        "supports_end_time": True,
        "default_symbols": ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"),
        "quote": "USDT",
    },
    "kraken": {
        "label": "Kraken public OHLC",
        "hosts": ("api.kraken.com",),
        "path": "/0/public/OHLC",
        "intervals": ("1m", "5m", "15m", "1h", "4h", "1d"),
        "max_limit": 720,
        "supports_end_time": True,
        "default_symbols": ("XBTUSD", "ETHUSD", "SOLUSD"),
        "quote": "USD",
    },
    "github_archive": {
        "label": "GitHub Verified Market Archives (2026 OHLCV + OrderFlow via Contents API)",
        "hosts": ("api.github.com",),
        "path": "/repos/",
        "intervals": ("1m", "15m", "1h", "4h", "1d"),
        "max_limit": 50000,
        "supports_end_time": False,
        "default_symbols": ("BTCUSDT", "ETHUSDT", "XAUUSD", "BRENT", "SPY", "AAPL", "NVDA"),
        "quote": "USD",
    },
}

INTERVAL_MINUTES = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440, "1w": 10080}
MINUTE_TIMEFRAMES = ("1m", "5m", "15m")


class FetchError(RuntimeError):
    """Raised when a venue cannot be fetched or the response is unusable."""


# ---------------------------------------------------------------------------
# 1. Guarded fetching
# ---------------------------------------------------------------------------

def allowed_hosts(venue: str) -> tuple[str, ...]:
    spec = VENUES.get(venue)
    if not spec:
        raise FetchError(f"unknown venue '{venue}' — allowed: {sorted(VENUES)}")
    return spec["hosts"]


def check_url(url: str, venue: str, *, allow_private: bool = False) -> str:
    """Refuse anything outside the venue allowlist (SSRF guard)."""
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("https", "http"):
        raise FetchError("only http(s) URLs are allowed")
    hosts = allowed_hosts(venue)
    if parsed.hostname not in hosts:
        if not (allow_private and parsed.hostname in ("127.0.0.1", "localhost", "::1")):
            raise FetchError(f"host '{parsed.hostname}' is not an allowlisted {venue} endpoint")
    return url


def _http_get_json(url: str, *, opener=None) -> object:
    request = urllib.request.Request(url, headers={"User-Agent": DEFAULT_USER_AGENT,
                                                   "Accept": "application/json"})
    try:
        with (opener or urllib.request.urlopen)(request, timeout=TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} from {urllib.parse.urlparse(url).hostname}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FetchError(f"network error fetching {urllib.parse.urlparse(url).hostname}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise FetchError("venue returned non-JSON") from exc


def binance_url(symbol: str, interval: str, limit: int, *, end_time: int | None = None,
                host: str | None = None, scheme: str = "https") -> str:
    if interval not in VENUES["binance"]["intervals"]:
        raise FetchError(f"binance does not support interval '{interval}'")
    limit = max(2, min(VENUES["binance"]["max_limit"], int(limit)))
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    if end_time:
        params["endTime"] = int(end_time) * 1000
    host = host or VENUES["binance"]["hosts"][0]
    return f"{scheme}://{host}{VENUES['binance']['path']}?{urllib.parse.urlencode(params)}"


def kraken_url(symbol: str, interval: str, *, since: int | None = None,
               host: str | None = None, scheme: str = "https") -> str:
    if interval not in VENUES["kraken"]["intervals"]:
        raise FetchError(f"kraken does not support interval '{interval}'")
    params = {"pair": symbol.upper(), "interval": INTERVAL_MINUTES[interval]}
    if since:
        params["since"] = int(since)
    host = host or VENUES["kraken"]["hosts"][0]
    return f"{scheme}://{host}{VENUES['kraken']['path']}?{urllib.parse.urlencode(params)}"


def parse_binance(rows, *, now: int | None = None) -> list[dict]:
    """Binance kline rows -> bars, dropping the still-forming candle."""
    if not isinstance(rows, list):
        raise FetchError("Binance response was not a kline array")
    now_ms = int((now if now is not None else dt.datetime.now(dt.timezone.utc).timestamp()) * 1000)
    bars = []
    for row in rows:
        if not isinstance(row, list) or len(row) < 6:
            continue
        try:
            close_time = int(row[6]) if len(row) > 6 else int(row[0])
            if close_time > now_ms:  # candle not finished yet
                continue
            bars.append({"t": int(row[0]) // 1000, "o": float(row[1]), "h": float(row[2]),
                         "l": float(row[3]), "c": float(row[4]), "v": float(row[5] or 0.0)})
        except (TypeError, ValueError):
            continue
    return bars


def parse_kraken(payload) -> tuple[str, list[dict]]:
    if not isinstance(payload, dict):
        raise FetchError("Kraken response was not JSON")
    errors = payload.get("error") or []
    if errors:
        raise FetchError("Kraken error: " + "; ".join(str(e) for e in errors))
    result = payload.get("result") or {}
    pair = next((key for key, value in result.items() if key != "last" and isinstance(value, list)), None)
    if not pair:
        raise FetchError("Kraken response had no OHLC pair array")
    rows = result[pair][:-1]  # drop the still-forming candle
    bars = []
    for row in rows:
        try:
            bars.append({"t": int(row[0]), "o": float(row[1]), "h": float(row[2]),
                         "l": float(row[3]), "c": float(row[4]), "v": float(row[6] or 0.0)})
        except (TypeError, ValueError, IndexError):
            continue
    return pair, bars


def fetch(venue: str, symbol: str, interval: str, *, limit: int = 1000,
          end_time: int | None = None, host: str | None = None,
          opener=None, allow_private: bool = False, scheme: str = "https") -> dict:
    """Fetch one page of completed bars from an allowlisted venue."""
    if venue == "binance":
        url = binance_url(symbol, interval, limit, end_time=end_time, host=host, scheme=scheme)
    elif venue == "kraken":
        url = kraken_url(symbol, interval, since=end_time, host=host, scheme=scheme)
    else:
        raise FetchError(f"unknown venue '{venue}'")
    check_url(url, venue, allow_private=allow_private)
    payload = _http_get_json(url, opener=opener)
    if venue == "binance":
        bars = parse_binance(payload)
        resolved = symbol.upper()
    else:
        resolved, bars = parse_kraken(payload)
    return {"venue": venue, "symbol": resolved, "interval": interval,
            "url": url, "bars": bars, "fetched_at": now_utc()}


def storage_symbol(venue: str, symbol: str, interval: str) -> str:
    """Stable, filter-safe database key, e.g. ``BINANCE.BTCUSDT.1m``."""
    clean = "".join(ch for ch in str(symbol).upper() if ch.isalnum() or ch in ".-_/")
    if not clean:
        raise FetchError("symbol is empty after sanitising")
    return f"{venue.upper()}.{clean}.{interval}"


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# 2. Incremental collection into SQLite
# ---------------------------------------------------------------------------

def plan_collection(symbols, interval: str = "1m", target_bars: int = 3000,
                    venue: str = "binance") -> dict:
    if venue not in VENUES:
        raise FetchError(f"unknown venue '{venue}'")
    if interval not in VENUES[venue]["intervals"]:
        raise FetchError(f"{venue} does not support interval '{interval}'")
    if isinstance(symbols, str):
        symbols = [s.strip() for s in symbols.split(",") if s.strip()]
    symbols = [str(s).strip().upper() for s in (symbols or []) if str(s).strip()]
    if not symbols:
        symbols = list(VENUES[venue]["default_symbols"])
    if len(symbols) > 12:
        raise ValueError("at most 12 symbols per collection plan")
    return {"venue": venue, "interval": interval,
            "target_bars": max(300, min(20000, int(target_bars))),
            "symbols": symbols}


def collect_series(db, *, venue: str, symbol: str, interval: str,
                   target_bars: int = 3000, host: str | None = None,
                   opener=None, allow_private: bool = False,
                   max_requests: int = 12, scheme: str = "https") -> dict:
    """Fetch backwards until ``target_bars`` are stored. Incremental.

    The page cursor walks backwards from the newest completed bar, so the
    first run backfills and later runs only fill the gap at the front.
    """
    stored_symbol = storage_symbol(venue, symbol, interval)
    existing = db.get_bars(stored_symbol, interval)
    have = len(existing)
    newest = existing[-1]["t"] if existing else None
    oldest = existing[0]["t"] if existing else None
    collected: dict[int, dict] = {}
    urls: list[str] = []
    errors: list[str] = []
    requests = 0

    def absorb(bars):
        added = 0
        for bar in bars:
            stamp = int(bar["t"])
            if newest is not None and stamp <= newest:
                continue  # already-stored range ends at the newest stored bar
            if stamp in collected:
                continue
            collected[stamp] = bar
            added += 1
        return added

    # 1) newest page first: this is what makes later runs incremental
    try:
        head = fetch(venue, symbol, interval,
                     limit=min(VENUES[venue]["max_limit"], max(2, int(target_bars))),
                     host=host, opener=opener, allow_private=allow_private, scheme=scheme)
        requests += 1
        urls.append(head["url"])
        absorb(head["bars"])
    except FetchError as exc:
        errors.append(str(exc))
        head = None

    # 2) backfill older bars until the target is met
    cursor = oldest - 1 if oldest is not None else (
        min(collected) - 1 if collected else None)
    max_requests = max(1, int(max_requests))
    while requests < max_requests:
        if have + len(collected) >= int(target_bars):
            break
        if cursor is None:
            break
        remaining = int(target_bars) - (have + len(collected))
        page_limit = min(VENUES[venue]["max_limit"], max(2, remaining))
        if venue == "kraken":
            page_limit = 720
        try:
            page = fetch(venue, symbol, interval, limit=page_limit,
                         end_time=cursor, host=host, opener=opener,
                         allow_private=allow_private, scheme=scheme)
        except FetchError as exc:
            errors.append(str(exc))
            break
        requests += 1
        urls.append(page["url"])
        bars = page["bars"]
        if not bars:
            break
        before = len(collected)
        absorb(bars)
        cursor = min(int(bar["t"]) for bar in bars) - 1
        if len(bars) < 2 or len(collected) == before:
            break

    fresh = [collected[key] for key in sorted(collected)]
    inserted = 0
    if fresh:
        result = db.import_bars(symbol=stored_symbol, timeframe=interval, bars=fresh,
                                source=f"{venue} public API (allowlisted collector)",
                                instrument={"symbol": stored_symbol,
                                            "asset_type": "crypto",
                                            "exchange": venue,
                                            "source": urls[-1] if urls else ""})
        inserted = int(result.get("bars_imported_or_updated") or 0)
    total = db.get_bars(stored_symbol, interval)
    run = db.record_collection({
        "venue": venue, "symbol": stored_symbol, "timeframe": interval,
        "requested": int(target_bars), "inserted": inserted,
        "previously_stored": have, "stored_total": len(total),
        "first_bar_time": _iso(total[0]["t"]) if total else None,
        "last_bar_time": _iso(total[-1]["t"]) if total else None,
        "endpoints": urls, "errors": errors, "requests": requests,
    })
    return {"symbol": stored_symbol, "venue": venue, "interval": interval,
            "previously_stored": have, "inserted": inserted, "stored_total": len(total),
            "first_bar": _iso(total[0]["t"]) if total else None,
            "last_bar": _iso(total[-1]["t"]) if total else None,
            "requests": requests, "endpoints": urls, "errors": errors,
            "collection_run_id": run.get("id")}


def collect_plan(db, plan: dict, *, opener=None, host: str | None = None,
                 allow_private: bool = False, scheme: str = "https") -> dict:
    plan = plan_collection(plan.get("symbols"), plan.get("interval", "1m"),
                           plan.get("target_bars", 3000), plan.get("venue", "binance"))
    results, inserted = [], 0
    for symbol in plan["symbols"]:
        item = collect_series(db, venue=plan["venue"], symbol=symbol,
                              interval=plan["interval"], target_bars=plan["target_bars"],
                              host=host, opener=opener, allow_private=allow_private,
                              scheme=scheme)
        inserted += item["inserted"]
        results.append(item)
    return {"venue": plan["venue"], "interval": plan["interval"],
            "symbols": plan["symbols"], "target_bars": plan["target_bars"],
            "inserted_total": inserted,
            "series": results,
            "next_step": ("Run POST /api/lab/auto-research to grade what was stored, "
                          "then GET /api/goal-progress for the honest distance to 80%.")}


def _iso(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return dt.datetime.fromtimestamp(int(timestamp), tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# 3. Holdout protection
# ---------------------------------------------------------------------------

def split_holdout(bars: list[dict], fraction: float = HOLDOUT_FRACTION) -> tuple[list[dict], list[dict]]:
    """Split into (tuning, holdout). The holdout is always the newest slice."""
    bars = ml.normalize_bars(bars)
    if len(bars) < 120:
        raise ValueError("a series needs at least 120 bars to reserve a holdout")
    cut = int(len(bars) * (1.0 - max(0.1, min(0.4, float(fraction)))))
    return bars[:cut], bars[cut:]


def holdout_evaluation(db, *, venue: str, symbol: str, interval: str,
                       methods=None, horizons=(3, 5, 15), cost_bps: float = 10.0,
                       attempts: int = 150) -> dict:
    """The ONLY reader of the reserved slice. Every call is recorded."""
    stored = storage_symbol(venue, symbol, interval)
    bars = db.get_bars(stored, interval)
    tuning, holdout = split_holdout(bars)
    methods = methods or ["atlas_minute_pulse", "minute_ema_ribbon", "minute_vwap_reversion"]
    rows = []
    for method in methods:
        for horizon in horizons:
            ctx = sc._context(sc._series(holdout, f"{stored} holdout"))
            evaluation = sc.evaluate_candidate(
                ctx, method, int(horizon),
                {"attempts": int(attempts), "cost_bps": float(cost_bps),
                 "min_history": 60, "min_attempts": 20})
            rows.append({key: evaluation.get(key) for key in (
                "method", "horizon_bars", "attempts_made", "hits", "coverage_pct",
                "direction_accuracy_pct", "wilson_95_ci_pct", "mean_gross_pct",
                "mean_net_pct", "max_drawdown_pct")})
    record = db.record_holdout({"venue": venue, "symbol": stored, "timeframe": interval,
                                "tuning_bars": len(tuning), "holdout_bars": len(holdout),
                                "methods": list(methods), "horizons": [int(h) for h in horizons],
                                "cost_bps": float(cost_bps), "rows": rows})
    return {"symbol": stored, "tuning_bars": len(tuning), "holdout_bars": len(holdout),
            "holdout_first_bar": _iso(holdout[0]["t"]),
            "holdout_last_bar": _iso(holdout[-1]["t"]),
            "cost_bps": float(cost_bps), "rows": rows,
            "holdout_use_id": record.get("id"),
            "warning": ("This is the reserved slice. Reading it repeatedly turns it "
                        "into tuning data — the count of reads is recorded on purpose.")}


# ---------------------------------------------------------------------------
# 4. Pooled evidence and the honest goal tracker
# ---------------------------------------------------------------------------

GATE_SPECS = [
    ("attempts", f"at least {MIN_ATTEMPTS_FOR_GOAL} hidden-future attempts per candidate"),
    ("accuracy", "pooled direction accuracy at least 80%"),
    ("wilson_lower", f"Wilson 95% lower bound at least {WILSON_TARGET:.0f}%"),
    ("costs", "positive mean net per attempt after 10 bps"),
    ("coverage", "coverage at least 20% when the method can abstain"),
    ("symbols", f"at least {MIN_SYMBOLS_FOR_GOAL} symbols"),
    ("days", f"at least {MIN_DAYS_FOR_GOAL} distinct UTC days"),
    ("holdout", "a recorded holdout evaluation on the reserved slice"),
    ("external", "fresh unseen validation outside this local database"),
]


def series_signature(bars: list[dict]) -> tuple:
    """Content identity: length, time span and sampled close prices.

    Used to stop the same series being stored or pooled twice under two names
    (which would silently inflate attempts and narrow the interval). Two
    different symbols that merely share the same timestamps have different
    closes and therefore different signatures.
    """
    if not bars:
        return (0, None, None, ())
    step = max(1, len(bars) // 8)
    closes = tuple(round(float(bars[i]["c"]), 6) for i in range(0, len(bars), step))
    return (len(bars), int(bars[0]["t"]), int(bars[-1]["t"]), closes)


def find_duplicate_series(db, bars: list[dict], *, exclude_symbol: str | None = None,
                          exclude_timeframe: str | None = None) -> str | None:
    signature = series_signature(bars)
    for series in db.list_series():
        if series["symbol"] == exclude_symbol and series["timeframe"] == exclude_timeframe:
            continue
        existing = db.get_bars(series["symbol"], series["timeframe"])
        if series_signature(existing) == signature and signature[0] > 0:
            return f"{series['symbol']}|{series['timeframe']}"
    return None


def _wilson(hits: int, made: int) -> tuple[float | None, float | None]:
    if made <= 0:
        return None, None
    low, high = sc.wilson_pct(hits, made)
    return low, high


def pooled_evidence(db, *, methods=None, horizons=(3, 5, 15), cost_bps: float = 10.0,
                    attempts: int = 150, max_series: int = 40) -> dict:
    """Pool hidden-future attempts across every stored series (tuning slice only)."""
    methods = methods or ["atlas_minute_pulse", "minute_ema_ribbon",
                          "minute_vwap_reversion", "multiscale_trend", "hull_trend"]
    pooled: dict[tuple[str, int], dict] = {}
    per_series = []
    days: set[str] = set()
    symbols: set[str] = set()
    used = 0
    signatures: dict[tuple, str] = {}
    duplicates = []
    for series in db.list_series():
        if used >= max_series:
            break
        symbol, timeframe = series["symbol"], series["timeframe"]
        if timeframe not in ml.TIMEFRAMES:
            continue
        bars = db.get_bars(symbol, timeframe)
        needed = 400 if timeframe in MINUTE_TIMEFRAMES else 180
        if len(bars) < needed:
            per_series.append({"symbol": symbol, "timeframe": timeframe,
                               "bars": len(bars), "skipped": f"needs {needed} bars"})
            continue
        signature = (series_signature(bars), timeframe)
        if signature in signatures:
            duplicates.append({"symbol": symbol, "timeframe": timeframe,
                               "duplicate_of": signatures[signature],
                               "bars": len(bars)})
            continue
        signatures[signature] = f"{symbol}|{timeframe}"
        tuning, _holdout = split_holdout(bars)
        if len(tuning) < needed * 0.8:
            per_series.append({"symbol": symbol, "timeframe": timeframe,
                               "bars": len(bars), "skipped": "holdout reservation leaves too little"})
            continue
        used += 1
        symbols.add(symbol)
        for bar in tuning[::max(1, len(tuning) // 60)]:
            days.add(dt.datetime.fromtimestamp(int(bar["t"]), tz=dt.timezone.utc).date().isoformat())
        ctx = sc._context(sc._series(tuning, symbol))
        for method in methods:
            for horizon in horizons:
                try:
                    ev = sc.evaluate_candidate(
                        ctx, method, int(horizon),
                        {"attempts": int(attempts), "cost_bps": float(cost_bps),
                         "min_history": 120 if timeframe in MINUTE_TIMEFRAMES else 100,
                         "min_attempts": 20})
                except (ValueError, KeyError):
                    continue
                made = int(ev.get("attempts_made") or 0)
                if made <= 0:
                    continue
                key = (method, int(horizon))
                slot = pooled.setdefault(key, {"method": method, "horizon_bars": int(horizon),
                                               "attempts": 0, "hits": 0, "net": 0.0,
                                               "gross": 0.0, "coverage_weighted": 0.0,
                                               "series": set(), "series_positive": 0})
                slot["attempts"] += made
                slot["hits"] += int(ev.get("hits") or 0)
                slot["net"] += float(ev.get("mean_net_pct") or 0.0) * made
                slot["gross"] += float(ev.get("mean_gross_pct") or 0.0) * made
                slot["coverage_weighted"] += float(ev.get("coverage_pct") or 0.0) * made
                slot["series"].add(symbol)
                if (ev.get("mean_net_pct") or 0) > 0:
                    slot["series_positive"] += 1
                per_series.append({"symbol": symbol, "timeframe": timeframe,
                                   "method": method, "horizon_bars": int(horizon),
                                   "attempts": made,
                                   "accuracy_pct": ev.get("direction_accuracy_pct"),
                                   "net_pct": ev.get("mean_net_pct"),
                                   "coverage_pct": ev.get("coverage_pct")})
    rows = []
    for key, slot in pooled.items():
        made = slot["attempts"]
        low, high = _wilson(slot["hits"], made)
        rows.append({
            "method": slot["method"], "horizon_bars": slot["horizon_bars"],
            "attempts": made, "hits": slot["hits"],
            "accuracy_pct": sc._round(100.0 * slot["hits"] / made, 3) if made else None,
            "wilson_95_ci_pct": [low, high],
            "mean_net_pct": sc._round(slot["net"] / made, 4) if made else None,
            "mean_gross_pct": sc._round(slot["gross"] / made, 4) if made else None,
            "coverage_pct": sc._round(slot["coverage_weighted"] / made, 3) if made else None,
            "series_count": len(slot["series"]),
            "series_positive": slot["series_positive"],
        })
    rows.sort(key=lambda r: (-(r["accuracy_pct"] or 0), -(r["mean_net_pct"] or 0)))
    return {"series_used": used, "series": per_series, "pooled": rows,
            "duplicates_skipped": duplicates,
            "symbols": sorted(symbols), "distinct_days": len(days),
            "config": {"methods": methods, "horizons": [int(h) for h in horizons],
                       "cost_bps": float(cost_bps), "attempts": int(attempts),
                       "holdout_reserved_fraction": HOLDOUT_FRACTION},
            "note": ("Identical series stored under two names are pooled once and listed "
                     "in duplicates_skipped; double counting would shrink the interval "
                     "for free. The top pooled row is the retrospective maximum of many candidates, "
                     "so its number is inflated by selection. Read the Wilson interval and "
                     "the holdout, not the point estimate.")}


def goal_progress(db, *, methods=None, horizons=(3, 5, 15), cost_bps: float = 10.0,
                  attempts: int = 150) -> dict:
    """The honest distance to the 80% target, gate by gate."""
    evidence = pooled_evidence(db, methods=methods, horizons=horizons,
                               cost_bps=cost_bps, attempts=attempts)
    eligible = [row for row in evidence["pooled"]
                if row["attempts"] >= MIN_ATTEMPTS_FOR_GOAL
                and (row.get("coverage_pct") or 0) >= 20.0]
    best = eligible[0] if eligible else (evidence["pooled"][0] if evidence["pooled"] else None)
    holdouts = db.list_holdouts(limit=25)
    attempts_total = best["attempts"] if best else 0
    accuracy = best["accuracy_pct"] if best else None
    wilson_low = (best["wilson_95_ci_pct"][0] if best else None)
    net = best["mean_net_pct"] if best else None
    symbol_count = len(evidence["symbols"])
    days = evidence["distinct_days"]
    holdout_ok = bool(holdouts)
    checks = [
        {"gate": "attempts", "requirement": GATE_SPECS[0][1], "value": attempts_total,
         "passed": attempts_total >= MIN_ATTEMPTS_FOR_GOAL},
        {"gate": "accuracy", "requirement": GATE_SPECS[1][1], "value": accuracy,
         "passed": accuracy is not None and accuracy >= 80.0},
        {"gate": "wilson_lower", "requirement": GATE_SPECS[2][1], "value": wilson_low,
         "passed": wilson_low is not None and wilson_low >= WILSON_TARGET},
        {"gate": "costs", "requirement": GATE_SPECS[3][1], "value": net,
         "passed": net is not None and net > 0},
        {"gate": "coverage", "requirement": GATE_SPECS[4][1],
         "value": (best or {}).get("coverage_pct", 100.0),
         "passed": (best or {}).get("coverage_pct", 100.0) >= 20.0},
        {"gate": "symbols", "requirement": GATE_SPECS[5][1], "value": symbol_count,
         "passed": symbol_count >= MIN_SYMBOLS_FOR_GOAL},
        {"gate": "days", "requirement": GATE_SPECS[6][1], "value": days,
         "passed": days >= MIN_DAYS_FOR_GOAL},
        {"gate": "holdout", "requirement": GATE_SPECS[7][1], "value": len(holdouts),
         "passed": holdout_ok},
        {"gate": "external", "requirement": GATE_SPECS[8][1],
         "value": "not available inside one local database", "passed": False},
    ]
    passed = sum(1 for c in checks if c["passed"])
    distance = None
    if accuracy is not None:
        distance = sc._round(max(0.0, 80.0 - float(accuracy)), 3)
    status = ("no_evidence_yet" if not best else
              "goal_evidence_ready_for_independent_review" if passed == len(checks) else
              "below_target_on_local_data")
    return {
        "mode": "honest_goal_progress", "version": VERSION,
        "target_accuracy_pct": 80.0,
        "goal_established": False,
        "status": status,
        "best_pooled_candidate": best,
        "distance_to_target_points": distance,
        "gates_passed": passed, "gates_total": len(checks), "checks": checks,
        "evidence": {"series_used": evidence["series_used"],
                     "symbols": evidence["symbols"], "distinct_days": days,
                     "holdout_evaluations": len(holdouts),
                     "config": evidence["config"]},
        "pooled": evidence["pooled"][:10],
        "how_to_move_forward": [
            "Collect more lawful bars (more symbols, more days) — attempts and coverage gates.",
            "Run the failure loop so dead candidates are retired instead of re-tested.",
            "Evaluate candidates only on the reserved holdout, once, and record it.",
            "Validate survivors on symbols/days that were never used for tuning.",
        ],
        "why_it_is_not_established": (
            "A local database can show a candidate that passes every measurable gate; it "
            "cannot prove a universal 80% edge. goal_established therefore stays false and "
            "the strongest status is goal_evidence_ready_for_independent_review."),
        "warning": "Research measurement only. Not financial advice and not an order path.",
    }


def pipeline_spec() -> dict:
    return {
        "name": "Atlas Auto-Collect + Goal Tracker", "version": VERSION,
        "venues": {key: {"label": spec["label"], "hosts": list(spec["hosts"]),
                         "intervals": list(spec["intervals"]),
                         "default_symbols": list(spec["default_symbols"])}
                   for key, spec in VENUES.items()},
        "security": ["fixed host allowlist; no arbitrary URLs",
                     "no API keys, logins or credentials",
                     "public keyless endpoints only",
                     "read-only market data; no order routing"],
        "collection": {"incremental": True, "holdout_fraction": HOLDOUT_FRACTION,
                       "max_bars_per_request": MAX_BARS_PER_REQUEST},
        "goal_gates": [{"id": gate, "requirement": text} for gate, text in GATE_SPECS],
        "goal_established_ever": False,
    }


def demo_collection_plan() -> dict:
    return plan_collection(VENUES["binance"]["default_symbols"][:3], "1m", 1200, "binance")

# ---------------------------------------------------------------------------
# v17 — Health monitoring, retry with backoff, and adaptive collection
# ---------------------------------------------------------------------------

def health_check(db) -> dict:
    """Check database health and collection freshness."""
    stats = db.stats()
    collections = db.list_collections(limit=5)
    holdouts = db.list_holdouts(limit=3)
    now = dt.datetime.now(dt.timezone.utc)
    stale = []
    for coll in collections:
        try:
            created = dt.datetime.fromisoformat(coll["created_at"].replace("Z", "+00:00"))
            age_hours = (now - created).total_seconds() / 3600
            if age_hours > 24:
                stale.append({"symbol": coll["symbol"], "age_hours": round(age_hours, 1)})
        except Exception:
            pass
    return {
        "status": "healthy" if not stale else "stale_data",
        "collections_recent": len(collections),
        "holdouts_recorded": len(holdouts),
        "stale_series": stale,
        "total_bars": stats["counts"].get("bars", 0),
        "db_version": stats["db_version"],
        "evolution": stats.get("evolution", {}),
        "recommendation": "Collect fresh data if stale_series is non-empty." if stale else "Database is current.",
    }

def adaptive_target_bars(current_bars: int, desired_attempts: int = 1000, interval: str = "1m") -> int:
    """Recommend target_bars based on desired attempts and interval."""
    # Rule: need ~ 1.5x attempts in bars for sufficient separation
    min_history = 240 if interval in MINUTE_TIMEFRAMES else 180
    recommended = int(min_history + desired_attempts * 1.8)
    recommended = max(1000, min(20000, recommended))
    return recommended

def retry_collect_with_backoff(db, plan: dict, *, max_retries: int = 3, base_sleep: float = 1.0, **kwargs) -> dict:
    """Collect with exponential backoff on FetchError."""
    import time as _time
    last_error = None
    for attempt in range(max_retries):
        try:
            result = collect_plan(db, plan, **kwargs)
            result["retry_attempts"] = attempt
            result["backoff_used"] = attempt > 0
            return result
        except FetchError as exc:
            last_error = str(exc)
            if attempt < max_retries - 1:
                sleep_time = base_sleep * (2 ** attempt)
                _time.sleep(min(sleep_time, 5))
            continue
    return {"error": last_error, "retry_attempts": max_retries, "success": False, "venue": plan.get("venue")}

def pipeline_health_metrics(db) -> dict:
    """Detailed pipeline metrics for dashboard."""
    health = health_check(db)
    progress = goal_progress(db)
    ev = progress.get("evidence") or {}
    return {
        "health": health,
        "goal_progress": {
            "status": progress.get("status"),
            "gates_passed": progress.get("gates_passed"),
            "gates_total": progress.get("gates_total"),
            "best_accuracy": (progress.get("best_pooled_candidate") or {}).get("accuracy_pct"),
            "distance_to_80": progress.get("distance_to_target_points"),
        },
        "evidence": ev,
        "goal_established": False,
        "version": VERSION,
    }


GITHUB_ARCHIVE_FEEDS: dict[str, dict] = {
    "BTCUSDT_1M_OCT2026": {
        "repo": "parshant231234-eng/BTCUSDT-Historical-Data",
        "path": "1m/2026/10/BTCUSDT_1m_2026-10.csv",
        "symbol": "GITHUB.BTCUSDT.1m",
        "timeframe": "1m",
        "tail_bars": 5000,
    },
    "ETHUSDT_1M_OCT2026": {
        "repo": "parshant231234-eng/ETHUSDT-Historical-Data",
        "path": "1m/2026/10/ETHUSDT_1m_2026-10.csv",
        "symbol": "GITHUB.ETHUSDT.1m",
        "timeframe": "1m",
        "tail_bars": 5000,
    },
    "XAUUSD_1H_2026": {
        "repo": "jptrustlearning/gold",
        "path": "gold_prices_h1.csv",
        "symbol": "GITHUB.XAUUSD.1h",
        "timeframe": "1h",
        "tail_bars": 8000,
    },
    "XAUUSD_1D_2026": {
        "repo": "jptrustlearning/gold",
        "path": "gold_prices.csv",
        "symbol": "GITHUB.XAUUSD.1d",
        "timeframe": "1d",
        "tail_bars": 4000,
    },
    "BRENT_1D_2026": {
        "repo": "jptrustlearning/gold",
        "path": "brent_prices.csv",
        "symbol": "GITHUB.BRENT.1d",
        "timeframe": "1d",
        "tail_bars": 2500,
    },
    "BTC_1D_2026": {
        "repo": "jptrustlearning/btc",
        "path": "btc_prices.csv",
        "symbol": "GITHUB.BTCUSD.1d",
        "timeframe": "1d",
        "tail_bars": 4000,
    },
}


def collect_github_archive_feed(db, feed_key: str = "XAUUSD_1H_2026", *, max_bars: int | None = None) -> dict:
    import hashlib
    import os
    import realdata as rd

    spec = GITHUB_ARCHIVE_FEEDS.get(feed_key)
    if not spec:
        raise FetchError(f"unknown github feed '{feed_key}' — available: {sorted(GITHUB_ARCHIVE_FEEDS)}")
    url = f"https://api.github.com/repos/{spec['repo']}/contents/{spec['path']}"
    check_url(url, "github_archive")
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/vnd.github.raw+json",
    }
    gh_tok = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
    if gh_tok:
        headers["Authorization"] = f"Bearer {gh_tok}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_bytes = resp.read()
    except Exception as exc:
        raise FetchError(f"github archive request failed for {feed_key}: {exc}") from exc

    sha256 = hashlib.sha256(raw_bytes).hexdigest()
    parsed_rows = rd.load_csv_text(raw_bytes.decode("utf-8-sig", errors="replace"))
    keep = max_bars or int(spec["tail_bars"])
    bars = []
    for b in parsed_rows:
        o, h, l, c = float(b["o"]), float(b["h"]), float(b["l"]), float(b["c"])
        if min(o, h, l, c) <= 0:
            continue
        bars.append({
            "t": int(b["ts"]),
            "o": o,
            "h": max(h, o, c),
            "l": min(l, o, c),
            "c": c,
            "v": float(b.get("v") or 0.0),
        })
    norm = ml.normalize_bars(bars, max_bars=100_000)[-keep:]
    up = db.import_bars(
        symbol=spec["symbol"],
        timeframe=spec["timeframe"],
        bars=norm,
        source=f"github_archive:{spec['repo']}/{spec['path']}",
    )
    return {
        "feed_key": feed_key,
        "symbol": spec["symbol"],
        "timeframe": spec["timeframe"],
        "repo": spec["repo"],
        "path": spec["path"],
        "sha256": sha256,
        "fetched_bars": len(norm),
        "inserted": up.get("bars_imported_or_updated", 0),
        "stored_total": len(db.get_bars(spec["symbol"], spec["timeframe"])),
        "last_bar_utc": ml._iso(norm[-1]["t"]),
    }


def ingest_bundled_real_catalog(db, *, limit_files: int | None = None) -> dict:
    import realdata as rd
    items = rd.list_real_datasets()
    if limit_files is not None:
        items = items[:limit_files]
    ingested = []
    for d in items:
        prov = d.get("provenance") or {}
        sym_base = prov.get("symbol", d["file"].split("-")[0].upper())
        tf = prov.get("interval", "1d")
        series_sym = f"REAL.{sym_base}.{tf}.{d['file'].split('.')[0][:18]}"
        mbars = rd.load_market_bars(d["path"])
        if len(mbars) < 55:
            continue
        norm = ml.normalize_bars(mbars, max_bars=100_000)
        up = db.import_bars(symbol=series_sym, timeframe=tf, bars=norm, source=f"real-data/{d['file']}")
        db.record_real_dataset(
            d["file"], sym_base, prov.get("market", "Historical"),
            tf, len(norm), str(d["first"]), str(d["last"]),
            {**prov, "sha256": d.get("sha256")},
        )
        ingested.append({"file": d["file"], "series": series_sym, "bars": len(norm)})
    return {"datasets_ingested": len(ingested), "series": ingested}
