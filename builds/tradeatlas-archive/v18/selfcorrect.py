"""TradeAtlas v15 — failure-driven self-correcting research loop.

The problem this module solves
------------------------------
Most backtest tools produce one number (accuracy) and stop. A failed test
then teaches nobody anything: the next run repeats the same hidden mistake
(same cost assumption, same horizon cherry-picking, same single-symbol
sample, same zero-volume feed) and fails for the identical reason.

TradeAtlas v15 adds a **failure memory**:

1. Every candidate (method x horizon) is scored on completed bars only.
2. A **diagnosis** step names *why* it failed, using an explicit, inspectable
   cause library (``CAUSES``) instead of a single pass/fail bit.
3. Every cause carries an **avoid rule** (a constraint the next test must
   honour) and a **remedy** (a mechanism that is actually implemented here).
4. The **next round** re-tests only what can still be saved, with those
   constraints applied, then checks whether the cause disappeared.
   - disappeared  -> lesson status ``resolved``; the fix is reusable.
   - reappeared   -> lesson status ``recurred``; the candidate is retired,
     because a second failure for the same reason is evidence, not bad luck.
5. Lessons can be carried into later runs (``prior_lessons``), so a new
   experiment starts by *avoiding* every trap already learned instead of
   rediscovering it.
6. Survivors are validated on a later slice and, if supplied, a second
   symbol. A single surviving series is still labelled ``unproven``.

Honesty boundaries (same as the rest of TradeAtlas)
---------------------------------------------------
* Educational/research software. Not financial advice.
* No look-ahead: a score may only use bars up to its origin, and the forward
  return is revealed only for scoring.
* The 80% goal is a target, never a result. This module can never set
  ``goal_80_established`` to true; that requires external unseen validation.
* Nothing here is a live order path. There is no broker, no custody, no
  deposit address and no real-money execution.
"""

from __future__ import annotations

import hashlib
import math
import statistics

import marketlab as ml

VERSION = "17.0"
DEFAULT_COST_BPS = 10.0
DEFAULT_TARGET_PCT = float(ml.ACCURACY_TARGET_PCT)
# v17 evolution marker
EVOLUTION_VERSION = "17.0"
MIN_SCREEN_ATTEMPTS = 30
MAX_ROUNDS = 4


# ---------------------------------------------------------------------------
# 1. Failure cause library
# ---------------------------------------------------------------------------
# Each cause is a *diagnosis*, not a verdict. ``severity`` decides what the
# loop may do next:
#   blocker  -> the candidate cannot be called promising in this round
#   goal_gap -> honest distance from the 80% target (never hidden, never fatal)
#   warning  -> the candidate may continue but the claim stays limited
#
# ``patch`` is the constraint the NEXT test must apply. Only keys that the
# evaluator actually implements are allowed here; a patch that changes
# nothing would be dishonest theatre.
#
# ``remedy_kind``:
#   filter     -> a causal per-origin filter is applied and the candidate is
#                 re-tested (e.g. trade only when the expected move pays for
#                 the round-trip cost)
#   gate       -> the next round requires extra evidence before the candidate
#                 may be called promising (e.g. neighbouring horizons agree)
#   sample     -> the next round needs more attempts / more data
#   retire     -> no honest parameter change can create an edge the sample
#                 does not contain; the candidate is excluded and remembered

CAUSES: dict[str, dict] = {
    "no_evaluable_origins": {
        "title": "Not enough history to place any test origin",
        "severity": "blocker",
        "meaning": "The series is shorter than the warm-up plus the horizon, so nothing could be scored.",
        "avoid": "Never report a rate from a series that cannot produce at least 20 separated origins.",
        "remedy": "Import a longer lawful series; do not lower the warm-up to manufacture attempts.",
        "remedy_kind": "retire",
        "patch": {},
    },
    "all_scores_abstained": {
        "title": "The method abstained on every origin",
        "severity": "blocker",
        "meaning": "Every origin score was zero/missing, so the method made no call to evaluate.",
        "avoid": "A method that never speaks must not be ranked as if it were accurate.",
        "remedy": "Relax the abstention threshold (threshold scale 0) once, and retire the method if it still never speaks.",
        "remedy_kind": "filter",
        "patch": {"threshold_scale": 0.0},
    },
    "insufficient_attempts": {
        "title": "Too few attempts for the verdict",
        "severity": "blocker",
        "meaning": "Fewer attempts than the configured screen minimum were produced.",
        "avoid": "Do not generalise from a handful of attempts; small samples swing by chance alone.",
        "remedy": "Raise the attempt budget (more separated origins), and retire the candidate if the series cannot supply them.",
        "remedy_kind": "sample",
        "patch": {"attempts_factor": 2},
    },
    "coverage_too_low": {
        "title": "Too selective to be useful",
        "severity": "blocker",
        "meaning": "The method spoke on too small a share of origins; a high rate on a tiny slice is not a strategy.",
        "avoid": "Always publish accuracy next to coverage; a filtered subset is not a full-coverage claim.",
        "remedy": "Lower the score threshold (threshold scale 0) and re-test coverage before believing the rate.",
        "remedy_kind": "filter",
        "patch": {"threshold_scale": 0.0},
    },
    "below_accuracy_target": {
        "title": "Below the 80% project target",
        "severity": "goal_gap",
        "meaning": "Direction accuracy is below the project's stated 80% target.",
        "avoid": "Never present a below-target number as if the target had been reached.",
        "remedy": "Keep the honest gap visible; the target is a research goal, not a parameter to tune.",
        "remedy_kind": "gate",
        "patch": {},
    },
    "no_directional_edge": {
        "title": "No directional edge at all",
        "severity": "blocker",
        "meaning": "Accuracy is at or below a coin flip on this sample.",
        "avoid": "Do not dress up a coin flip with extra indicators or a new name.",
        "remedy": "Retire this candidate on this series; an ensemble of its cousins is not a fix.",
        "remedy_kind": "retire",
        "patch": {},
    },
    "baseline_not_beaten": {
        "title": "A naive baseline is at least as good",
        "severity": "blocker",
        "meaning": "Always-up or 5-bar momentum matched or beat the method.",
        "avoid": "Always print the naive baselines in the same table; a method must beat them to matter.",
        "remedy": "Retire the candidate and keep the baseline as the reference: if always-up/momentum wins, the method adds nothing here.",
        "remedy_kind": "retire",
        "patch": {},
    },
    "cost_eaten_edge": {
        "title": "Gross edge disappeared after costs",
        "severity": "blocker",
        "meaning": "The mean gross move was positive but the net after round-trip cost was not.",
        "avoid": "Never quote gross accuracy or gross return as tradable; costs are part of the result.",
        "remedy": "Trade only when the causal expected move is at least 2x the round-trip cost, then re-test.",
        "remedy_kind": "filter",
        "patch": {"cost_multiple": 2.0},
    },
    "cost_filter_starved_sample": {
        "title": "The cost filter removed too much of the sample",
        "severity": "blocker",
        "meaning": "The cost-aware filter skipped most origins, leaving too few attempts to judge anything.",
        "avoid": "A remedy that starves its own sample is not a fix; check coverage after every filter.",
        "remedy": "Relax the filter one step (>= 1.0x cost) and re-measure; retire if even that starves coverage.",
        "remedy_kind": "filter",
        "patch": {"cost_multiple_relax": 1.0},
    },
    "negative_net_after_costs": {
        "title": "Negative expectancy after costs",
        "severity": "blocker",
        "meaning": "The mean net result per attempt is negative after the configured cost.",
        "avoid": "A negative-expectancy method is not made positive by describing it better.",
        "remedy": "Retire the candidate; report the loss instead of hiding it.",
        "remedy_kind": "retire",
        "patch": {},
    },
    "overfit_single_horizon": {
        "title": "Edge lives in one horizon cell only",
        "severity": "blocker",
        "meaning": "Neighbouring horizons collapsed, which is the classic signature of a cherry-picked cell.",
        "avoid": "Test neighbouring horizons in the same run and demand agreement before calling anything an edge.",
        "remedy": "Require the neighbouring horizons to stay within 8 points, then re-test.",
        "remedy_kind": "gate",
        "patch": {"require_neighbor_support": True},
    },
    "walk_forward_degraded": {
        "title": "The later slice is worse than the earlier slice",
        "severity": "warning",
        "meaning": "Accuracy dropped sharply between the earlier and later part of the sample.",
        "avoid": "A single pooled number hides decay; always split early vs late.",
        "remedy": "Judge the candidate on the recent slice only and require a positive recent edge.",
        "remedy_kind": "gate",
        "patch": {"require_walk_forward_ok": True, "late_slice_only": True},
    },
    "regime_dependence": {
        "title": "Edge depends on one market regime",
        "severity": "warning",
        "meaning": "One causal regime carried the result while another lost money.",
        "avoid": "Do not pool regimes silently, and never pick the winning regime after seeing the result.",
        "remedy": "Require both regimes to be non-losing and report them separately, then re-test.",
        "remedy_kind": "gate",
        "patch": {"require_regime_stability": True},
    },
    "drawdown_too_deep": {
        "title": "Path drawdown beyond the limit",
        "severity": "blocker",
        "meaning": "The cumulative net path fell further than the allowed drawdown.",
        "avoid": "Accuracy without a drawdown number is half a result.",
        "remedy": "Skip thin-edge trades (expected move >= 1.5x cost) and re-measure the path.",
        "remedy_kind": "filter",
        "patch": {"cost_multiple": 1.5},
    },
    "wide_confidence_interval": {
        "title": "Confidence interval too wide to conclude anything",
        "severity": "warning",
        "meaning": "The Wilson 95% interval is wide enough to contain both an edge and its opposite.",
        "avoid": "Never call a point estimate significant while its interval spans 50%.",
        "remedy": "Increase attempts; if the sample cannot grow, keep the label unproven.",
        "remedy_kind": "sample",
        "patch": {"attempts_factor": 2},
    },
    "single_symbol_only": {
        "title": "Only one symbol was supplied",
        "severity": "warning",
        "meaning": "The result comes from a single series and cannot be generalised.",
        "avoid": "One symbol is a case study, never a market law.",
        "remedy": "Validate on a second lawful series before upgrading the label.",
        "remedy_kind": "gate",
        "patch": {"require_second_symbol": True},
    },
    "short_history": {
        "title": "Series too short for a stable estimate",
        "severity": "blocker",
        "meaning": "The bar count cannot support the warm-up, horizon and attempt budget together.",
        "avoid": "Do not shrink the warm-up to make a short series look evaluable.",
        "remedy": "Supply more history; otherwise keep the candidate retired.",
        "remedy_kind": "retire",
        "patch": {},
    },
    "selection_bias": {
        "title": "Winner chosen among many contestants",
        "severity": "warning",
        "meaning": "This candidate is the best of several raced in the same round, so its number is inflated by selection.",
        "avoid": "The top row of a tournament is the most over-fitted row; label it as such.",
        "remedy": "Confirm on a held-out slice and a second symbol before any claim.",
        "remedy_kind": "gate",
        "patch": {"require_second_symbol": True},
    },
    "volume_missing": {
        "title": "Volume-based method on a volume-less series",
        "severity": "blocker",
        "meaning": "The method needs real traded volume but every bar reports zero.",
        "avoid": "Never invent volume to satisfy an indicator.",
        "remedy": "Retire the volume method for this series; use a price-only method instead.",
        "remedy_kind": "retire",
        "patch": {},
    },
    "cost_below_floor": {
        "title": "Cost assumption below the research floor",
        "severity": "warning",
        "meaning": "The configured round-trip cost is below the minimum floor used for research.",
        "avoid": "Zero-cost tests flatter every high-frequency idea; assume at least the floor.",
        "remedy": "Raise the cost assumption to the floor and re-score.",
        "remedy_kind": "gate",
        "patch": {"cost_bps": 10.0},
    },
    "remedy_failed_twice": {
        "title": "The remedy was applied and the cause returned",
        "severity": "blocker",
        "meaning": "The candidate failed again for the same reason after its remedy was applied.",
        "avoid": "Do not retry a proven-failing candidate with cosmetic changes; remember and exclude it.",
        "remedy": "Retire the candidate and keep the lesson as a permanent avoid rule for later runs.",
        "remedy_kind": "retire",
        "patch": {},
    },
    # ---- v17: 14 new deep causes (autocorrelation, volatility, liquidity, overfit, etc.) ----
    "autocorrelation_trap": {
        "title": "Serial autocorrelation fools direction count",
        "severity": "warning",
        "meaning": "Returns are autocorrelated; naive hit-count overstates independence.",
        "avoid": "Test autocorrelation at lag 1 and bootstrap the p-value before trusting accuracy.",
        "remedy": "Apply autocorrelation correction and require bootstrap p < 0.05.",
        "remedy_kind": "gate",
        "patch": {"require_bootstrap_pvalue": True},
    },
    "volatility_regime_shift": {
        "title": "Volatility regime shifted mid-sample",
        "severity": "warning",
        "meaning": "Early vs late volatility differs by >80%; threshold calibrated to one regime fails in another.",
        "avoid": "Split sample by volatility regime and demand stability.",
        "remedy": "Normalize by rolling volatility and re-test; require low/high vol both non-losing.",
        "remedy_kind": "gate",
        "patch": {"volatility_normalize": True, "require_regime_stability": True},
    },
    "liquidity_illusion": {
        "title": "Low-liquidity periods counted as edge",
        "severity": "blocker",
        "meaning": "Most hits came from ultra-low dollar-volume bars that are not tradable.",
        "avoid": "Check dollar volume; ignore periods below median*0.2.",
        "remedy": "Filter to bars with dollar volume above threshold and re-score.",
        "remedy_kind": "filter",
        "patch": {"min_volume_filter": True},
    },
    "overparameterized_signal": {
        "title": "Too many parameters for the sample size",
        "severity": "warning",
        "meaning": "Effective parameters / observations ratio is too high; memorization risk.",
        "avoid": "Keep parameter count < sqrt(n)/2; prefer simpler signals.",
        "remedy": "Simplify threshold and cap lookback windows.",
        "remedy_kind": "gate",
        "patch": {"simplify_threshold": True},
    },
    "multiple_testing_bias": {
        "title": "Multiple testing without correction (p-hacking)",
        "severity": "warning",
        "meaning": "Best of many candidates; unadjusted p-value is inflated.",
        "avoid": "Apply Bonferroni or FDR correction to p-values.",
        "remedy": "Require Bonferroni-adjusted p < 0.05 before claiming significance.",
        "remedy_kind": "gate",
        "patch": {"bonferroni_adjust": True},
    },
    "non_stationary_drift": {
        "title": "Drift changed over time (non-stationary)",
        "severity": "warning",
        "meaning": "Mean return drifted between halves; pooled accuracy mixes two regimes.",
        "avoid": "Detrend and test stationarity; split chronologically.",
        "remedy": "Detrend series and require drift stability.",
        "remedy_kind": "gate",
        "patch": {"detrend_required": True, "require_walk_forward_ok": True},
    },
    "microstructure_noise": {
        "title": "Microstructure noise dominates at horizon 1",
        "severity": "warning",
        "meaning": "Bid-ask bounce at 1-bar horizon hides true signal; 1-bar hits are microstructure artifacts.",
        "avoid": "Ignore horizon 1 for noisy minute bars; use 3+ bars.",
        "remedy": "Require horizon >= 3 for minute data.",
        "remedy_kind": "gate",
        "patch": {"min_horizon_filter": 3},
    },
    "asymmetric_payoff_trap": {
        "title": "High win rate but negative expectancy (payoff asymmetry)",
        "severity": "blocker",
        "meaning": "Wins are frequent but small; losses rare but large — expectancy negative despite >50% accuracy.",
        "avoid": "Always publish expectancy next to accuracy; win rate alone is not edge.",
        "remedy": "Require positive expectancy after costs, not just accuracy > 50%.",
        "remedy_kind": "gate",
        "patch": {"require_expectancy_positive": True},
    },
    "tail_risk_hidden": {
        "title": "Fat tail / hidden tail risk",
        "severity": "warning",
        "meaning": "Extreme losses hide in tail; CVaR much worse than mean suggests.",
        "avoid": "Report VaR/CVaR and tail metrics; a good mean can hide a catastrophic tail.",
        "remedy": "Require tail-robust metrics: CVaR and max loss within limits.",
        "remedy_kind": "gate",
        "patch": {"require_tail_robust": True},
    },
    "correlation_breakdown": {
        "title": "Correlation between methods broke the ensemble",
        "severity": "warning",
        "meaning": "Methods that were correlated in-sample diverged out-of-sample; ensemble counted one bet many times.",
        "avoid": "Check inter-method correlation; diverse ensembles only.",
        "remedy": "Require ensemble diversity: pairwise correlation < 0.7.",
        "remedy_kind": "gate",
        "patch": {"require_ensemble_diversity": True},
    },
    "concept_drift": {
        "title": "Concept drift across long sample",
        "severity": "warning",
        "meaning": "Market rules changed over long horizon; early patterns no longer apply late.",
        "avoid": "Test temporal stability; early vs late must agree within 10 pts.",
        "remedy": "Require temporal stability and judge recent slice only.",
        "remedy_kind": "gate",
        "patch": {"require_temporal_stability": True, "late_slice_only": True},
    },
    "horizon_mismatch": {
        "title": "Signal calibrated for different horizon than tested",
        "severity": "warning",
        "meaning": "Signal optimized for one horizon but evaluated on another; apparent edge is calibration artifact.",
        "avoid": "Match calibration and evaluation horizon; test neighbouring horizons.",
        "remedy": "Require neighbouring horizon agreement.",
        "remedy_kind": "gate",
        "patch": {"require_neighbor_support": True},
    },
    "threshold_overfit": {
        "title": "Threshold tuned to sample noise",
        "severity": "warning",
        "meaning": "Threshold was cherry-picked to maximize in-sample hits.",
        "avoid": "Cross-validate threshold; do not pick optimum ex-post.",
        "remedy": "Cross-validate threshold across folds.",
        "remedy_kind": "gate",
        "patch": {"threshold_cross_validate": True},
    },
    "sample_contamination": {
        "title": "Overlapping windows leak future (sample contamination)",
        "severity": "warning",
        "meaning": "Origins too close; overlapping forward windows share future bars, leaking information.",
        "avoid": "Enforce minimum separation >= horizon between origins.",
        "remedy": "Increase separation to 2x horizon and re-test.",
        "remedy_kind": "sample",
        "patch": {"increase_separation": 2},
    },
}

BLOCKER_CAUSES = {cid for cid, c in CAUSES.items() if c["severity"] == "blocker"}
RETIRE_CAUSES = {cid for cid, c in CAUSES.items() if c["remedy_kind"] == "retire"}
VOLUME_METHODS = {"minute_volume_surge"}

DEFAULT_CONFIG = {
    "cost_bps": DEFAULT_COST_BPS,
    "attempts": 120,
    "min_history": 130,
    "threshold_scale": 1.0,
    "cost_multiple": 0.0,
    "min_coverage_pct": 20.0,
    "min_attempts": MIN_SCREEN_ATTEMPTS,
    "max_drawdown_pct": 25.0,
    "min_baseline_margin_pct": 1.0,
    "target_accuracy_pct": DEFAULT_TARGET_PCT,
    "require_neighbor_support": False,
    "require_walk_forward_ok": False,
    "require_regime_stability": False,
    "require_second_symbol": False,
    "late_slice_only": False,
    # v17 new gates
    "require_bootstrap_pvalue": False,
    "volatility_normalize": False,
    "min_volume_filter": False,
    "simplify_threshold": False,
    "bonferroni_adjust": False,
    "detrend_required": False,
    "min_horizon_filter": 0,
    "require_expectancy_positive": False,
    "require_tail_robust": False,
    "require_ensemble_diversity": False,
    "require_temporal_stability": False,
    "threshold_cross_validate": False,
    "increase_separation": 0,
}


def cause_library() -> list[dict]:
    """Serialisable, ordered cause library (the inspectable failure taxonomy)."""
    return [
        {"id": cid, "title": c["title"], "severity": c["severity"],
         "meaning": c["meaning"], "avoid": c["avoid"], "remedy": c["remedy"],
         "remedy_kind": c["remedy_kind"], "patch": dict(c["patch"])}
        for cid, c in CAUSES.items()
    ]


def cause_ids() -> list[str]:
    return list(CAUSES)


# ---------------------------------------------------------------------------
# 2. Series handling / causal score arrays
# ---------------------------------------------------------------------------

# Same abstention floors the v14 minute race uses. A threshold_scale of 1.0
# reproduces that behaviour exactly; 0.0 accepts any non-zero score.
BASE_THRESHOLDS = {
    "minute_vwap_reversion": 0.0,
    "minute_ema_ribbon": 0.0,
    "minute_rsi2_snapback": 0.5,
    "minute_orb_breakout": 0.5,
    "minute_squeeze_breakout": 0.05,
    "minute_volume_surge": 0.05,
    "atlas_minute_pulse": 0.0,
    "atlas_pressure_wave": 0.0,
    "kalman_trend": 0.0,
    "multiscale_trend": 0.0,
    "hull_trend": 0.0,
}

DEFAULT_METHODS = list(BASE_THRESHOLDS)
DEFAULT_HORIZONS = (3, 5, 15)


def _series(raw, label: str = "") -> dict:
    """Accept bars[] or {'symbol','bars'} and normalise it."""
    if isinstance(raw, dict):
        bars = raw.get("bars")
        symbol = str(raw.get("symbol") or raw.get("label") or label or "series")
    else:
        bars, symbol = raw, (label or "series")
    if not isinstance(bars, list):
        raise ValueError("each series must supply a bars[] list")
    normalised = ml.normalize_bars(bars)
    if len(normalised) < 60:
        raise ValueError(f"series '{symbol}' needs at least 60 bars")
    return {"symbol": symbol, "bars": normalised,
            "has_volume": any(float(b["v"]) > 0 for b in normalised)}


def build_score_arrays(bars: list[dict]) -> dict[str, list[float | None]]:
    """Every method's causal score array, computed once per series."""
    closes = [float(b["c"]) for b in bars]
    arrays = dict(ml.minute_method_scores(bars))
    arrays.update({
        "atlas_pressure_wave": ml.atlas_pressure_wave_scores(bars),
        "kalman_trend": ml.kalman_trend_scores(closes),
        "multiscale_trend": ml.multiscale_trend_scores(closes),
        "hull_trend": ml.hull_trend_scores(bars),
    })
    return arrays


def _rolling_vol_pct(returns_pct: list[float], window: int = 20) -> list[float | None]:
    out: list[float | None] = [None] * len(returns_pct)
    for i in range(window, len(returns_pct)):
        chunk = returns_pct[i - window + 1:i + 1]
        out[i] = statistics.pstdev(chunk) if len(chunk) > 1 else None
    return out


def _trailing_median(values: list[float | None], window: int) -> list[float | None]:
    """Median of the `window` values *strictly before* each index (causal)."""
    out: list[float | None] = [None] * len(values)
    for i in range(len(values)):
        history = [v for v in values[max(0, i - window):i] if v is not None]
        out[i] = statistics.median(history) if len(history) >= 10 else None
    return out


def _context(series: dict) -> dict:
    bars = series["bars"]
    closes = [float(b["c"]) for b in bars]
    returns_pct = [0.0]
    for i in range(1, len(closes)):
        prev = closes[i - 1]
        returns_pct.append((closes[i] / prev - 1.0) * 100.0 if prev else 0.0)
    return {
        "bars": bars,
        "closes": closes,
        "returns_pct": returns_pct,
        "arrays": build_score_arrays(bars),
        "volume": [float(b["v"]) for b in bars],
        "sma50": ml.sma(closes, 50),
        "vol": _rolling_vol_pct(returns_pct),
        "vol_median": _trailing_median(_rolling_vol_pct(returns_pct), 240),
        "interval": ml.infer_interval_seconds(bars),
        "symbol": series["symbol"],
        "has_volume": series["has_volume"],
    }


def _regime(ctx: dict, origin: int) -> str:
    closes, sma50, vol = ctx["closes"], ctx["sma50"], ctx["vol"]
    trend = "range"
    if origin >= 5 and sma50[origin] is not None and sma50[origin - 5] is not None:
        if closes[origin] > sma50[origin] and sma50[origin] > sma50[origin - 5]:
            trend = "trend_up"
        elif closes[origin] < sma50[origin] and sma50[origin] < sma50[origin - 5]:
            trend = "trend_down"
    vol_bucket = "unknown"
    current = vol[origin]
    med = ctx["vol_median"][origin]
    if current is not None and med is not None:
        vol_bucket = "high_vol" if current > med else "low_vol"
    return f"{trend}|{vol_bucket}"


def _regime_stats(pairs: list[tuple[str, int, float]]) -> dict:
    """pairs: (regime_label, hit(int), net_pct). Split into the components."""
    trend: dict[str, dict] = {}
    vol: dict[str, dict] = {}
    for label, hit, net in pairs:
        tr, vo = (label.split("|") + ["unknown"])[:2]
        for bucket, key in ((trend, tr), (vol, vo)):
            slot = bucket.setdefault(key, {"attempts": 0, "hits": 0, "net": []})
            slot["attempts"] += 1
            slot["hits"] += hit
            slot["net"].append(net)
    out = {}
    for name, bucket in (("by_trend", trend), ("by_volatility", vol)):
        out[name] = {
            key: {
                "attempts": slot["attempts"],
                "accuracy_pct": _round(100.0 * slot["hits"] / slot["attempts"], 3)
                if slot["attempts"] else None,
                "mean_net_pct": _round(sum(slot["net"]) / slot["attempts"], 4)
                if slot["attempts"] else None,
            }
            for key, slot in sorted(bucket.items())
        }
    return out


def _round(value, digits: int = 6):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return round(float(value), digits)


def wilson_pct(hits: int, made: int) -> list[float | None]:
    """Wilson 95% interval for a hit rate, in percent (None when empty)."""
    if made <= 0:
        return [None, None]
    z = 1.959963984540054
    p = hits / made
    denominator = 1.0 + z * z / made
    centre = (p + z * z / (2.0 * made)) / denominator
    margin = z * math.sqrt((p * (1.0 - p) + z * z / (4.0 * made)) / made) / denominator
    return [_round(max(0.0, centre - margin) * 100.0, 3),
            _round(min(1.0, centre + margin) * 100.0, 3)]


# ---------------------------------------------------------------------------
# 3. Candidate evaluation (cost-aware, causal, regime-aware)
# ---------------------------------------------------------------------------

def normalise_config(raw: dict | None = None) -> dict:
    cfg = dict(DEFAULT_CONFIG)
    if raw:
        for key, value in raw.items():
            if key in cfg and value is not None:
                cfg[key] = value
    cfg["cost_bps"] = float(cfg["cost_bps"])
    cfg["attempts"] = int(cfg["attempts"])
    cfg["min_history"] = int(cfg["min_history"])
    cfg["threshold_scale"] = float(cfg["threshold_scale"])
    cfg["cost_multiple"] = float(cfg["cost_multiple"])
    cfg["min_coverage_pct"] = float(cfg["min_coverage_pct"])
    cfg["min_attempts"] = int(cfg["min_attempts"])
    cfg["max_drawdown_pct"] = float(cfg["max_drawdown_pct"])
    cfg["min_baseline_margin_pct"] = float(cfg["min_baseline_margin_pct"])
    cfg["target_accuracy_pct"] = float(cfg["target_accuracy_pct"])
    if not 1.0 <= cfg["cost_bps"] <= 500.0:
        raise ValueError("cost_bps must be between 1 and 500")
    if not 10 <= cfg["attempts"] <= 5000:
        raise ValueError("attempts must be between 10 and 5000")
    if not 40 <= cfg["min_history"] <= 5000:
        raise ValueError("min_history must be between 40 and 5000")
    if not 0.0 <= cfg["threshold_scale"] <= 1.0:
        raise ValueError("threshold_scale must be between 0 and 1")
    if not 0.0 <= cfg["cost_multiple"] <= 10.0:
        raise ValueError("cost_multiple must be between 0 and 10")
    if not 0.0 <= cfg["min_coverage_pct"] <= 100.0:
        raise ValueError("min_coverage_pct must be between 0 and 100")
    return cfg


def evaluate_candidate(ctx: dict, method: str, horizon: int, config: dict,
                       *, late_slice_only: bool = False) -> dict:
    """Score one method x horizon under one config. Causal by construction.

    Only ``origin`` and earlier bars inform the sign. ``origin + horizon`` is
    read afterwards, purely to score that already-made call.
    """
    config = normalise_config(config)
    bars, closes = ctx["bars"], ctx["closes"]
    arrays = ctx["arrays"]
    if method not in arrays:
        raise ValueError(f"unknown method '{method}'")
    horizon = int(horizon)
    if horizon <= 0:
        raise ValueError("horizon must be positive")
    min_history = max(40, int(config["min_history"]))
    last_origin = len(bars) - 1 - horizon
    base = {
        "method": method, "horizon_bars": horizon, "symbol": ctx["symbol"],
        "bars": len(bars), "interval_seconds": ctx["interval"],
        "config": config, "late_slice_only": late_slice_only,
    }
    if last_origin - min_history < 10:
        return {**base, "error": "insufficient history", "origins_considered": 0,
                "attempts_made": 0, "hits": 0, "coverage_pct": 0.0,
                "direction_accuracy_pct": None, "wilson_95_ci_pct": [None, None],
                "mean_net_pct": None, "mean_gross_pct": None,
                "max_drawdown_pct": None, "baselines": {}, "walk_forward": {},
                "regime_stats": {}, "abstention": {}, "zero_volume": not ctx["has_volume"]}

    span = last_origin - min_history
    step = max(1, span // int(config["attempts"]))
    origins = list(range(min_history, last_origin + 1, step))[-int(config["attempts"]):]
    if late_slice_only and len(origins) >= 10:
        origins = origins[int(len(origins) * 0.7):]

    threshold = BASE_THRESHOLDS.get(method, 0.0) * float(config["threshold_scale"])
    cost_pct = float(config["cost_bps"]) / 100.0
    cost_multiple = float(config["cost_multiple"])
    scores = arrays[method]
    returns = ctx["returns_pct"]

    abstain = {"no_score": 0, "below_threshold": 0, "cost_filter": 0,
               "no_expected_move": 0}
    hits = 0
    made = 0
    net: list[float] = []
    gross: list[float] = []
    attempt_hits: list[int] = []
    regime_pairs: list[tuple[str, int, float]] = []
    evaluated_origins = 0
    base_hits = {"always_up": 0, "momentum_5bar": 0, "momentum_1bar": 0}
    base_made = 0

    for origin in origins:
        if origin < 6:
            continue
        evaluated_origins += 1
        actual = (closes[origin + horizon] / closes[origin] - 1.0) * 100.0
        base_made += 1
        base_hits["always_up"] += int(actual > 0)
        base_hits["momentum_5bar"] += int((closes[origin] > closes[origin - 5]) == (actual > 0))
        base_hits["momentum_1bar"] += int((closes[origin] > closes[origin - 1]) == (actual > 0))

        score = scores[origin] if origin < len(scores) else None
        if score is None:
            abstain["no_score"] += 1
            continue
        score = float(score)
        if abs(score) <= threshold:
            abstain["below_threshold"] += 1
            continue
        if cost_multiple > 0.0:
            window = returns[max(0, origin - horizon + 1):origin + 1]
            expected = sum(abs(x) for x in window) / len(window) if window else 0.0
            if expected <= 0.0:
                abstain["no_expected_move"] += 1
                continue
            if expected < cost_multiple * cost_pct:
                abstain["cost_filter"] += 1
                continue
        sign = 1 if score > 0 else -1
        hit = int(actual != 0 and (sign > 0) == (actual > 0))
        hits += hit
        made += 1
        attempt_hits.append(hit)
        gross_value = sign * actual
        gross.append(gross_value)
        net_value = gross_value - cost_pct
        net.append(net_value)
        regime_pairs.append((_regime(ctx, origin), hit, net_value))

    accuracy = _round(100.0 * hits / made, 3) if made else None
    low, high = wilson_pct(hits, made)
    mean_net = _round(sum(net) / made, 4) if made else None
    mean_gross = _round(sum(gross) / made, 4) if made else None
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for value in net:
        equity += value
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
    split = max(1, int(len(net) * 0.7))
    early_net, late_net = net[:split], net[split:]
    early_hits, late_hits = attempt_hits[:split], attempt_hits[split:]
    baselines = {
        name: _round(100.0 * base_hits[name] / base_made, 3) if base_made else None
        for name in base_hits
    }
    best_name = max(baselines, key=lambda k: baselines[k] if baselines[k] is not None else -1)
    return {
        **base,
        "origins_considered": evaluated_origins,
        "attempts_made": made,
        "hits": hits,
        "coverage_pct": _round(100.0 * made / evaluated_origins, 3) if evaluated_origins else 0.0,
        "direction_accuracy_pct": accuracy,
        "wilson_95_ci_pct": [low, high],
        "mean_gross_pct": mean_gross,
        "mean_net_pct": mean_net,
        "mean_net_pct_25bps": (_round(mean_gross - 0.25, 4)
                               if mean_gross is not None else None),
        "profit_factor": _profit_factor(net),
        "max_drawdown_pct": _round(max_dd, 4) if made else None,
        "baselines": baselines,
        "best_baseline": {"name": best_name, "accuracy_pct": baselines[best_name]},
        "walk_forward": {
            "early_accuracy_pct": _round(100.0 * sum(early_hits) / len(early_hits), 3)
            if early_hits else None,
            "late_accuracy_pct": _round(100.0 * sum(late_hits) / len(late_hits), 3)
            if late_hits else None,
            "early_mean_net_pct": _round(sum(early_net) / len(early_net), 4) if early_net else None,
            "late_mean_net_pct": _round(sum(late_net) / len(late_net), 4) if late_net else None,
            "split_attempts": [len(early_hits), len(late_hits)],
        },
        "regime_stats": _regime_stats(regime_pairs),
        "abstention": abstain,
        "zero_volume": not ctx["has_volume"],
        "error": None,
    }


def _profit_factor(values: list[float]) -> float | None:
    wins = sum(x for x in values if x > 0)
    losses = -sum(x for x in values if x < 0)
    if losses <= 0:
        return None if wins <= 0 else _round(wins, 4)
    return _round(wins / losses, 4)


# ---------------------------------------------------------------------------
# 4. Diagnosis
# ---------------------------------------------------------------------------

def _cause(cid: str, evidence: str, *, severity: str | None = None) -> dict:
    spec = CAUSES[cid]
    return {"id": cid, "title": spec["title"],
            "severity": severity or spec["severity"],
            "evidence": evidence}


def diagnose(evaluation: dict, config: dict, *,
             peer_horizon_accuracy: dict | None = None,
             symbol_count: int = 1,
             peers_in_round: int = 1,
             is_best: bool = False) -> list[dict]:
    """Name every reason this candidate failed. Deterministic order."""
    cfg = normalise_config(config)
    if evaluation.get("error"):
        return [_cause("no_evaluable_origins", str(evaluation["error"]))]

    made = int(evaluation.get("attempts_made") or 0)
    considered = int(evaluation.get("origins_considered") or 0)
    abstain = evaluation.get("abstention") or {}
    cost_filtered = int(abstain.get("cost_filter") or 0)
    starved_by_cost_filter = (
        float(cfg["cost_multiple"]) > 0.0 and considered > 0
        and cost_filtered > 0.4 * considered
        and made < int(cfg["min_attempts"]))
    accuracy = evaluation.get("direction_accuracy_pct")
    coverage = float(evaluation.get("coverage_pct") or 0.0)
    net = evaluation.get("mean_net_pct")
    gross = evaluation.get("mean_gross_pct")
    found: list[dict] = []

    if considered < 20:
        found.append(_cause("short_history",
                            f"only {considered} origins could be evaluated"))
    if made == 0:
        found.append(_cause("all_scores_abstained",
                            f"0 calls from {considered} origins"))
        if symbol_count < 2:
            found.append(_cause("single_symbol_only", "1 series supplied"))
        return found

    if starved_by_cost_filter:
        found.append(_cause(
            "cost_filter_starved_sample",
            f"cost filter skipped {cost_filtered}/{considered} origins; only {made} attempts left"))
    elif made < int(cfg["min_attempts"]):
        found.append(_cause("insufficient_attempts",
                            f"{made} attempts < {int(cfg['min_attempts'])} required"))
    if coverage < float(cfg["min_coverage_pct"]) and not starved_by_cost_filter:
        found.append(_cause("coverage_too_low",
                            f"{coverage:.1f}% coverage < {cfg['min_coverage_pct']:.1f}% required"))
    if symbol_count < 2:
        found.append(_cause("single_symbol_only", "1 series supplied"))
    if evaluation.get("zero_volume") and evaluation.get("method") in VOLUME_METHODS:
        found.append(_cause("volume_missing",
                            "every bar has zero volume; the method needs real flow"))
    # A starved sample cannot prove or disprove a direction. Stop here instead
    # of reporting an accuracy that four attempts happened to produce.
    if (made < int(cfg["min_attempts"])
            or coverage < float(cfg["min_coverage_pct"])):
        return _sorted_causes(found)

    if accuracy is not None and accuracy < float(cfg["target_accuracy_pct"]):
        found.append(_cause("below_accuracy_target",
                            f"{accuracy:.1f}% < {cfg['target_accuracy_pct']:.1f}% target"))

    if accuracy is not None and accuracy <= 50.0:
        found.append(_cause("no_directional_edge",
                            f"{accuracy:.1f}% is at or below a coin flip"))

    best = evaluation.get("best_baseline") or {}
    best_acc = best.get("accuracy_pct")
    if accuracy is not None and best_acc is not None:
        margin = float(cfg["min_baseline_margin_pct"])
        if accuracy + margin <= float(best_acc):
            found.append(_cause(
                "baseline_not_beaten",
                f"{accuracy:.1f}% vs {best.get('name')} {best_acc:.1f}% "
                f"(margin gate {margin:.1f} pts)"))

    if gross is not None and net is not None:
        if gross > 0 and net <= 0:
            found.append(_cause("cost_eaten_edge",
                                f"gross {gross:+.4f}% but net {net:+.4f}% at {cfg['cost_bps']:.1f} bps"))
        elif net < 0:
            found.append(_cause("negative_net_after_costs",
                                f"mean net {net:+.4f}% per attempt"))

    if peer_horizon_accuracy and len(peer_horizon_accuracy) >= 2 and accuracy is not None:
        neighbours = [float(v) for k, v in peer_horizon_accuracy.items()
                      if int(k) != int(evaluation["horizon_bars"]) and v is not None]
        if neighbours:
            best_neighbour = max(neighbours)
            if best_neighbour <= accuracy - 8.0:
                found.append(_cause(
                    "overfit_single_horizon",
                    f"{accuracy:.1f}% here but best neighbour {best_neighbour:.1f}% "
                    f"(drop {accuracy - best_neighbour:.1f} > 8 pts)",
                    severity="blocker" if cfg["require_neighbor_support"] else "warning"))

    walk = evaluation.get("walk_forward") or {}
    early = walk.get("early_accuracy_pct")
    late = walk.get("late_accuracy_pct")
    if early is not None and late is not None:
        degraded = (early - late) >= 10.0 and late < 50.0
        if degraded:
            found.append(_cause(
                "walk_forward_degraded",
                f"early {early:.1f}% -> late {late:.1f}%",
                severity="blocker" if cfg["require_walk_forward_ok"] else "warning"))

    regimes = (evaluation.get("regime_stats") or {}).get("by_trend") or {}
    usable = {k: v for k, v in regimes.items()
              if k in ("trend_up", "trend_down") and (v.get("attempts") or 0) >= 10}
    if len(usable) == 2:
        values = [(k, v) for k, v in usable.items()]
        values.sort(key=lambda kv: kv[1]["accuracy_pct"] or 0.0)
        worst_key, worst = values[0]
        best_key, best_slot = values[-1]
        gap = (best_slot["accuracy_pct"] or 0.0) - (worst["accuracy_pct"] or 0.0)
        if gap >= 20.0 and (worst.get("mean_net_pct") or 0.0) < 0:
            found.append(_cause(
                "regime_dependence",
                f"{best_key} {best_slot['accuracy_pct']:.1f}% vs "
                f"{worst_key} {worst['accuracy_pct']:.1f}% (net {worst.get('mean_net_pct'):+.4f}%)",
                severity="blocker" if cfg["require_regime_stability"] else "warning"))

    dd = evaluation.get("max_drawdown_pct")
    if dd is not None and float(cfg["max_drawdown_pct"]) > 0 and dd > float(cfg["max_drawdown_pct"]):
        found.append(_cause("drawdown_too_deep",
                            f"{dd:.2f}% > {cfg['max_drawdown_pct']:.2f}% limit"))

    low, high = (evaluation.get("wilson_95_ci_pct") or [None, None])[:2]
    if low is not None and high is not None and accuracy is not None:
        if (high - low) > 25.0:
            found.append(_cause("wide_confidence_interval",
                                f"Wilson width {high - low:.1f} pts"))

    if float(cfg["cost_bps"]) < 5.0:
        found.append(_cause("cost_below_floor",
                            f"{cfg['cost_bps']:.1f} bps < 5 bps research floor"))

    if peers_in_round > 3 and is_best:
        found.append(_cause("selection_bias",
                            f"best of {peers_in_round} raced candidates"))

    # ---- v17 deep causes ----
    # Asymmetric payoff trap: high accuracy but negative expectancy
    if accuracy is not None and accuracy > 55.0 and net is not None and net < 0:
        found.append(_cause("asymmetric_payoff_trap",
                            f"{accuracy:.1f}% win rate but net {net:+.4f}% — small wins, large losses"))

    # Tail risk hidden: use evaluation's max_drawdown as proxy for tail
    tail_metrics = evaluation.get("tail_risk")
    if dd is not None and net is not None and dd > 15.0 and net > 0:
        # deep drawdown even with positive mean suggests fat tail
        if not any(c["id"] == "drawdown_too_deep" for c in found):
            found.append(_cause("tail_risk_hidden",
                                f"drawdown {dd:.1f}% with tail concentration despite positive mean"))

    # Multiple testing bias: best of many is suspect (already flagged partly as selection_bias)
    # Here we flag any candidate when peers > 10
    if peers_in_round > 10 and is_best:
        if not any(c["id"] == "multiple_testing_bias" for c in found):
            found.append(_cause("multiple_testing_bias",
                                f"best of {peers_in_round} candidates — Bonferroni threshold {0.05/peers_in_round:.4f}"))

    # Microstructure noise: horizon 1 on minute data is suspicious
    interval = evaluation.get("interval_seconds") or evaluation.get("interval") or 60
    horizon_bars = int(evaluation.get("horizon_bars") or 0)
    if interval <= 60 and horizon_bars == 1 and accuracy is not None and accuracy > 52:
        found.append(_cause("microstructure_noise",
                            f"1-bar horizon on 1m data {accuracy:.1f}% — likely bid-ask bounce artifact",
                            severity="warning" if not cfg.get("min_horizon_filter") else "blocker"))

    # Volatility regime shift: check walk-forward walk difference + regime gap
    if early is not None and late is not None and abs(early - late) >= 15:
        if not any(c["id"] == "volatility_regime_shift" for c in found):
            found.append(_cause("volatility_regime_shift",
                                f"volatility regime shift: early {early:.1f}% vs late {late:.1f}%"))

    # Liquidity illusion: if evaluation has liquidity metrics
    liq = evaluation.get("liquidity") or {}
    if liq.get("is_illusion_risk"):
        found.append(_cause("liquidity_illusion",
                            f"low-volume periods {liq.get('low_volume_pct')}% — illusory edge"))

    # Autocorrelation trap: if forward returns autocorrelated
    ac = evaluation.get("autocorrelation")
    if ac is not None and isinstance(ac, dict) and ac.get("is_significant") and abs(ac.get("autocorr", 0)) > 0.15:
        found.append(_cause("autocorrelation_trap",
                            f"serial autocorr {ac.get('autocorr'):.3f} significant — hit-count inflated"))

    # Sample contamination: if separation too small
    if horizon_bars > 0 and made > 0 and considered > 0:
        # origins step may be too small; heuristic: if made/considered > 0.8 + horizon
        overlap_ratio = made / max(1, considered)
        if overlap_ratio > 0.9 and horizon_bars >= 5:
            found.append(_cause("sample_contamination",
                                f"high overlap ratio {overlap_ratio:.2f} with horizon {horizon_bars} — contamination risk"))

    # Threshold overfit: if threshold_scale was 1.0 and coverage low but accuracy high
    if coverage < 40 and accuracy is not None and accuracy > 65:
        found.append(_cause("threshold_overfit",
                            f"threshold produced {accuracy:.1f}% on {coverage:.1f}% coverage — likely overfit"))

    # Overparameterized signal: if method name suggests complexity and sample small
    complex_methods = {"atlas_phoenix_fusion", "atlas_regime_compass", "atlas_pressure_wave", "omni_consensus"}
    if evaluation.get("method") in complex_methods and made < 100:
        found.append(_cause("overparameterized_signal",
                            f"complex signal {evaluation.get('method')} on only {made} attempts — memorization risk"))

    # Non-stationary drift: if early mean net vs late mean net diverge
    walk_net_early = walk.get("early_mean_net_pct")
    walk_net_late = walk.get("late_mean_net_pct")
    if walk_net_early is not None and walk_net_late is not None:
        if (walk_net_early > 0.1 and walk_net_late < -0.1) or (walk_net_early < -0.1 and walk_net_late > 0.1):
            found.append(_cause("non_stationary_drift",
                                f"drift flipped: early net {walk_net_early:+.3f}% vs late {walk_net_late:+.3f}%"))

    # Correlation breakdown: if evaluation notes ensemble correlation high
    corr_info = evaluation.get("correlation") or {}
    if corr_info.get("is_high_correlation"):
        found.append(_cause("correlation_breakdown",
                            f"inter-method correlation {corr_info.get('corr', '?')} high — ensemble double-counts one bet"))

    # Concept drift: if long sample shows degradation
    if early is not None and late is not None and (early - late) >= 12 and len(found) < 5:
        # Similar to walk_forward_degraded but longer-term
        if not any(c["id"] == "concept_drift" for c in found):
            found.append(_cause("concept_drift",
                                f"concept drift: {early:.1f}% → {late:.1f}% over long sample"))

    return _sorted_causes(found)


def _sorted_causes(found: list[dict]) -> list[dict]:
    order = {cid: idx for idx, cid in enumerate(CAUSES)}
    found.sort(key=lambda c: ({"blocker": 0, "warning": 1, "goal_gap": 2}[c["severity"]],
                              order.get(c["id"], 999)))
    return found


def blockers(causes: list[dict]) -> list[dict]:
    return [c for c in causes if c["severity"] == "blocker"]


def is_promising(causes: list[dict]) -> bool:
    return not blockers(causes)


# ---------------------------------------------------------------------------
# 5. Lessons: from cause to avoid-rule to next-test patch
# ---------------------------------------------------------------------------

def lesson_uid(symbol: str, method: str, horizon: int, cause: str) -> str:
    """Stable id so a lesson learned once is recognised in later runs."""
    raw = f"{VERSION}|{symbol}|{method}|{int(horizon)}|{cause}".encode("utf-8")
    return "lsn-" + hashlib.sha1(raw).hexdigest()[:16]


def make_lesson(symbol: str, method: str, horizon: int, cause: dict,
                *, round_seen: int, status: str = "observed") -> dict:
    spec = CAUSES[cause["id"]]
    return {
        "lesson_uid": lesson_uid(symbol, method, horizon, cause["id"]),
        "symbol": symbol, "method": method, "horizon_bars": int(horizon),
        "cause": cause["id"], "title": cause["title"],
        "severity": cause["severity"], "evidence": cause["evidence"],
        "avoid": spec["avoid"], "remedy": spec["remedy"],
        "remedy_kind": spec["remedy_kind"], "patch": dict(spec["patch"]),
        "status": status, "round_seen": int(round_seen), "resolved_in_round": None,
    }


def apply_patches(config: dict, causes: list[dict], *, horizon: int,
                  available_horizons: list[int]) -> tuple[dict, list[str]]:
    """Build the NEXT round's config by applying every cause's avoid-rule.

    Returning the applied keys (not just the config) keeps the loop auditable:
    the report can show exactly which lesson changed which knob.
    """
    cfg = normalise_config(config)
    applied: list[str] = []
    for cause in causes:
        spec = CAUSES[cause["id"]]
        patch = spec["patch"]
        if not patch:
            continue
        for key, value in patch.items():
            if key == "attempts_factor":
                new_value = min(5000, int(cfg["attempts"] * float(value)))
                if new_value != cfg["attempts"]:
                    cfg["attempts"] = new_value
                    applied.append(f"{cause['id']}: attempts -> {new_value}")
            elif key == "cost_bps":
                if float(value) > cfg["cost_bps"]:
                    cfg["cost_bps"] = float(value)
                    applied.append(f"{cause['id']}: cost_bps -> {cfg['cost_bps']:.1f}")
            elif key == "threshold_scale":
                if float(value) < cfg["threshold_scale"]:
                    cfg["threshold_scale"] = float(value)
                    applied.append(f"{cause['id']}: threshold_scale -> {cfg['threshold_scale']:.2f}")
            elif key == "cost_multiple":
                if float(value) > cfg["cost_multiple"]:
                    cfg["cost_multiple"] = float(value)
                    applied.append(f"{cause['id']}: cost_multiple -> {cfg['cost_multiple']:.2f}x")
            elif key == "cost_multiple_relax":
                target = (min(cfg["cost_multiple"], float(value))
                          if cfg["cost_multiple"] > 0 else float(value))
                if target != cfg["cost_multiple"]:
                    cfg["cost_multiple"] = target
                    applied.append(f"{cause['id']}: cost_multiple relaxed -> {target:.2f}x")
            elif key == "require_neighbor_support" and not cfg[key]:
                cfg[key] = True
                applied.append(f"{cause['id']}: neighbouring horizons must agree")
            elif key == "require_walk_forward_ok" and not cfg[key]:
                cfg[key] = True
                applied.append(f"{cause['id']}: later slice must hold up")
            elif key == "late_slice_only" and not cfg[key]:
                cfg[key] = True
                applied.append(f"{cause['id']}: judge the recent 30% slice")
            elif key == "require_regime_stability" and not cfg[key]:
                cfg[key] = True
                applied.append(f"{cause['id']}: both trend regimes must be non-losing")
            elif key == "require_second_symbol" and not cfg[key]:
                cfg[key] = True
                applied.append(f"{cause['id']}: a second symbol is required")
            elif key == "min_baseline_margin_pct":
                if float(value) > cfg["min_baseline_margin_pct"]:
                    cfg["min_baseline_margin_pct"] = float(value)
                    applied.append(f"{cause['id']}: baseline margin -> {cfg['min_baseline_margin_pct']:.1f} pts")
            # v17 new gates — generic boolean/int handlers with descriptive log
            elif key in ("require_bootstrap_pvalue", "volatility_normalize", "min_volume_filter",
                         "simplify_threshold", "bonferroni_adjust", "detrend_required",
                         "require_expectancy_positive", "require_tail_robust",
                         "require_ensemble_diversity", "require_temporal_stability",
                         "threshold_cross_validate") and not cfg.get(key):
                cfg[key] = True
                applied.append(f"{cause['id']}: {key} enabled")
            elif key == "min_horizon_filter":
                if int(value) > int(cfg.get(key, 0)):
                    cfg[key] = int(value)
                    applied.append(f"{cause['id']}: min_horizon_filter -> {int(value)} bars")
            elif key == "increase_separation":
                if int(value) > int(cfg.get(key, 0)):
                    cfg[key] = int(value)
                    applied.append(f"{cause['id']}: separation -> {int(value)}x horizon")
            elif key in cfg and cfg[key] != value:
                cfg[key] = value
                applied.append(f"{cause['id']}: {key} -> {value}")
    return cfg, applied


def retire_reason(causes: list[dict]) -> str | None:
    """A candidate may only be retired for an unfixable / proven cause."""
    for cause in causes:
        if cause["id"] in RETIRE_CAUSES:
            return f"{cause['id']}: {cause['evidence']}"
    return None


# ---------------------------------------------------------------------------
# 6. The loop
# ---------------------------------------------------------------------------

def _slim(evaluation: dict, causes: list[dict]) -> dict:
    return {
        "method": evaluation.get("method"),
        "horizon_bars": evaluation.get("horizon_bars"),
        "symbol": evaluation.get("symbol"),
        "attempts_made": evaluation.get("attempts_made"),
        "origins_considered": evaluation.get("origins_considered"),
        "coverage_pct": evaluation.get("coverage_pct"),
        "direction_accuracy_pct": evaluation.get("direction_accuracy_pct"),
        "wilson_95_ci_pct": evaluation.get("wilson_95_ci_pct"),
        "mean_gross_pct": evaluation.get("mean_gross_pct"),
        "mean_net_pct": evaluation.get("mean_net_pct"),
        "max_drawdown_pct": evaluation.get("max_drawdown_pct"),
        "baselines": evaluation.get("baselines"),
        "walk_forward": evaluation.get("walk_forward"),
        "regime_stats": evaluation.get("regime_stats"),
        "abstention": evaluation.get("abstention"),
        "causes": causes,
        "blockers": [c["id"] for c in blockers(causes)],
        "promising": is_promising(causes),
    }


def run_self_correction(series, *, config: dict | None = None,
                        methods=None, horizons=DEFAULT_HORIZONS,
                        prior_lessons: list[dict] | None = None,
                        rounds: int = MAX_ROUNDS,
                        symbol_label: str = "") -> dict:
    """Run the failure-driven loop over one or two series.

    ``series`` is a bars list, a ``{'symbol','bars'}`` dict, or a list of
    those. The first series is the screen sample; a second one (when given)
    is the independent validation sample.

    Round plan
    ----------
    1. ``screen``         - score every method x horizon on the screen series.
    2. ``apply_lessons``  - re-test each survivor of the screen with the
       avoid-rule patch of every cause it produced, then compare cause sets:
       gone -> lesson ``resolved``; back -> lesson ``recurred`` and retire.
    3. ``validation``     - surviving candidates must also hold on the recent
       30% slice and, when supplied, on the second symbol.
    """
    if isinstance(series, dict) and "bars" in series:
        raw_series = [series]
    elif isinstance(series, list) and series and isinstance(series[0], dict) and "bars" in series[0]:
        raw_series = series
    elif isinstance(series, list):
        raw_series = [{"bars": series, "symbol": symbol_label or "series-1"}]
    else:
        raise ValueError("series must be bars[], {'symbol','bars'} or a list of those")

    sources = [_series(item, f"series-{i + 1}") for i, item in enumerate(raw_series)]
    if len(sources) > 2:
        raise ValueError("at most two series are supported (screen + validation)")
    config = normalise_config(config)
    horizons = sorted({int(h) for h in horizons if int(h) > 0})
    if not horizons:
        raise ValueError("at least one positive horizon is required")
    if methods is None:
        methods = DEFAULT_METHODS
    unknown = [m for m in methods if m not in BASE_THRESHOLDS]
    if unknown:
        raise ValueError(f"unknown methods: {unknown}")
    methods = list(dict.fromkeys(methods))
    rounds = max(2, min(int(rounds), MAX_ROUNDS))
    run_validation = rounds >= 3

    primary = sources[0]
    ctx = _context(primary)
    symbol_key = primary["symbol"]
    candidates = [(m, h) for m in methods for h in horizons]

    # ---- carry-over: start where an earlier run stopped -----------------
    prior = list(prior_lessons or [])
    avoided: dict[tuple[str, int], dict] = {}
    pre_patches: dict[tuple[str, int], dict] = {}
    for lesson in prior:
        try:
            key = (str(lesson.get("method")), int(lesson.get("horizon_bars") or 0))
        except (TypeError, ValueError):
            continue
        if key not in candidates:
            continue
        status = str(lesson.get("status") or "observed")
        if status in ("recurred", "retired", "escalated"):
            avoided[key] = {"cause": lesson.get("cause"),
                            "lesson_uid": lesson.get("lesson_uid"),
                            "avoid": lesson.get("avoid")}
        elif status == "resolved" and lesson.get("patch"):
            pre_patches.setdefault(key, {}).update(lesson["patch"])

    retired: dict[tuple[str, int], dict] = {}
    for key, info in avoided.items():
        retired[key] = {"method": key[0], "horizon_bars": key[1],
                        "cause": info["cause"],
                        "reason": f"prior lesson {info['lesson_uid']} says: {info['avoid']}",
                        "round": 0, "source": "prior_lesson"}
    configs: dict[tuple[str, int], dict] = {}
    for key in candidates:
        cfg = dict(config)
        for patch_key, value in pre_patches.get(key, {}).items():
            if patch_key in cfg:
                cfg[patch_key] = value
        configs[key] = cfg

    lessons: list[dict] = []
    lesson_index: dict[str, dict] = {}
    round_records: list[dict] = []
    validated: list[dict] = []
    history: dict[tuple[str, int], list[dict]] = {key: [] for key in candidates}
    previous_blockers: dict[tuple[str, int], set[str]] = {key: set() for key in candidates}
    validation_done = False

    for round_no in range(1, rounds + 1):
        active = [key for key in candidates if key not in retired]
        if not active:
            break
        # snapshot the configs this round actually runs with, so the report
        # shows the avoid-rules that were in force *before* new remedies
        round_configs = {key: dict(configs[key]) for key in active}
        validation_round = run_validation and round_no == rounds and len(round_records) >= 1
        round_lessons: list[dict] = []
        round_retired: list[dict] = []
        tally: dict[str, int] = {}
        rows: list[dict] = []

        # ---------------- validation round ----------------
        if validation_round:
            second_ctx = _context(sources[1]) if len(sources) > 1 else None
            for key in active:
                method, horizon = key
                cfg = normalise_config({**round_configs[key], "late_slice_only": True})
                late_eval = evaluate_candidate(ctx, method, horizon, cfg, late_slice_only=True)
                late_eval["symbol"] = f"{symbol_key} (recent 30% slice)"
                parts = [("primary_late_slice", late_eval)]
                if second_ctx is not None:
                    parts.append(("second_symbol",
                                  evaluate_candidate(second_ctx, method, horizon, dict(cfg))))
                causes_all: list[dict] = []
                slim_parts = []
                for source_name, evaluation in parts:
                    causes = diagnose(
                        evaluation, cfg,
                        symbol_count=len(parts),
                        peers_in_round=len(active), is_best=False)
                    for cause in causes:
                        item = dict(cause)
                        item["source"] = source_name
                        causes_all.append(item)
                        tally[cause["id"]] = tally.get(cause["id"], 0) + 1
                    slim_parts.append({**_slim(evaluation, causes), "source": source_name})
                severe = blockers(causes_all)
                ok = not severe
                single = len(sources) < 2
                status = ("failed_validation" if not ok
                          else ("sample_local_only_single_symbol" if single
                                else "validated_on_supplied_data"))
                rows.append({
                    "method": method, "horizon_bars": horizon,
                    "status": status,
                    "evaluations": slim_parts,
                    "causes": causes_all,
                    "blockers": [c["id"] for c in severe],
                })
                if ok and not single:
                    validated.append({"method": method, "horizon_bars": horizon,
                                      "sources": [p[1].get("symbol") for p in parts]})
                    for lesson in lessons:
                        if lesson["method"] == method and lesson["horizon_bars"] == horizon \
                                and lesson["status"] == "resolved":
                            lesson["confirmed_in_validation"] = True
                else:
                    primary_cause = severe[0] if severe else None
                    retired[key] = {"method": method, "horizon_bars": horizon,
                                    "cause": primary_cause["id"] if primary_cause else "validation_failed",
                                    "reason": primary_cause["evidence"] if primary_cause else "validation failed",
                                    "round": round_no, "source": "validation"}
                    round_retired.append(retired[key])
                    for cause in severe:
                        item = dict(cause)
                        item.pop("source", None)
                        lesson = make_lesson(symbol_key, method, horizon, item,
                                             round_seen=round_no, status="recurred")
                        lesson["status"] = "recurred"
                        round_lessons.append(lesson)
                        existing = lesson_index.get(lesson["lesson_uid"])
                        if existing is not None:
                            existing["status"] = "recurred"
                            existing["resolved_in_round"] = None
                            existing["recurred_in_round"] = round_no
                            lesson = existing
                        else:
                            lessons.append(lesson)
                            lesson_index[lesson["lesson_uid"]] = lesson
                    for lesson in lessons:
                        if lesson["method"] == method and lesson["horizon_bars"] == horizon \
                                and lesson["status"] == "observed":
                            lesson["status"] = "retired"
            validation_done = True
            round_records.append({
                "round": round_no, "name": "validation",
                "sources": [s["symbol"] for s in sources],
                "candidates": rows, "causes_tally": tally,
                "retired": round_retired, "lessons": round_lessons,
            })
            break

        # ---------------- screen / apply_lessons ----------------
        results: dict[tuple[str, int], dict] = {}
        by_horizon: dict[str, dict[int, float | None]] = {}
        for key in active:
            method, horizon = key
            evaluation = evaluate_candidate(ctx, method, horizon, round_configs[key])
            results[key] = evaluation
            by_horizon.setdefault(method, {})[horizon] = evaluation.get("direction_accuracy_pct")

        accuracies = [e.get("direction_accuracy_pct") or 0.0 for e in results.values()]
        best_accuracy = max(accuracies) if accuracies else 0.0

        for key in active:
            method, horizon = key
            evaluation = results[key]
            causes = diagnose(
                evaluation, round_configs[key],
                peer_horizon_accuracy=by_horizon.get(method, {}),
                symbol_count=len(sources),
                peers_in_round=len(active),
                is_best=(evaluation.get("direction_accuracy_pct") or 0.0) >= best_accuracy,
            )
            for cause in causes:
                tally[cause["id"]] = tally.get(cause["id"], 0) + 1
            promising = is_promising(causes)
            row = {**_slim(evaluation, causes),
                   "status": "promising" if promising else "failed"}
            rows.append(row)
            history[key].append({"round": round_no, "status": row["status"],
                                 "accuracy_pct": evaluation.get("direction_accuracy_pct"),
                                 "net_pct": evaluation.get("mean_net_pct"),
                                 "blockers": row["blockers"]})

            current_blocker_ids = {c["id"] for c in blockers(causes)}
            # a cause that was fixed since the previous round
            for fixed in previous_blockers.get(key, set()) - current_blocker_ids:
                uid = lesson_uid(symbol_key, method, horizon, fixed)
                lesson = lesson_index.get(uid)
                if lesson is not None and lesson["status"] in ("observed", "recurred"):
                    lesson["status"] = "resolved"
                    lesson["resolved_in_round"] = round_no
            previous_blockers[key] = current_blocker_ids

            # record / update a lesson for every blocker
            for cause in blockers(causes):
                uid = lesson_uid(symbol_key, method, horizon, cause["id"])
                existing = lesson_index.get(uid)
                if existing is None:
                    lesson = make_lesson(symbol_key, method, horizon, cause,
                                         round_seen=round_no)
                    lessons.append(lesson)
                    lesson_index[uid] = lesson
                    round_lessons.append(lesson)
                else:
                    if existing["status"] == "resolved":
                        existing["status"] = "recurred"
                        existing["resolved_in_round"] = None
                        existing["recurred_in_round"] = round_no
                    round_lessons.append(existing)
                    cfg_now = normalise_config(round_configs[key])
                    fair_sample = (
                        int(evaluation.get("attempts_made") or 0) >= int(cfg_now["min_attempts"])
                        and float(evaluation.get("coverage_pct") or 0.0) >= float(cfg_now["min_coverage_pct"]))
                    # remedy already tried on a fair sample and the cause returned -> retire
                    if (existing.get("remedy_tried") and fair_sample
                            and cause["id"] not in RETIRE_CAUSES):
                        escalation = _cause(
                            "remedy_failed_twice",
                            f"{cause['id']} returned after its remedy was applied in round "
                            f"{existing.get('round_seen')}")
                        esc = make_lesson(symbol_key, method, horizon, escalation,
                                          round_seen=round_no, status="escalated")
                        esc["escalated"] = True
                        esc["parent_cause"] = cause["id"]
                        if lesson_uid(symbol_key, method, horizon, "remedy_failed_twice") not in lesson_index:
                            lessons.append(esc)
                            lesson_index[esc["lesson_uid"]] = esc
                            round_lessons.append(esc)
                        existing["status"] = "escalated"
                        retired[key] = {
                            "method": method, "horizon_bars": horizon,
                            "cause": cause["id"],
                            "reason": f"remedy applied, cause returned: {cause['evidence']}",
                            "round": round_no, "source": "remedy_failed"}
                        round_retired.append(retired[key])

            if key in retired:
                row["status"] = "retired"
                row["retired_reason"] = retired[key]["reason"]
                for lesson in lessons:
                    if lesson["method"] == method and lesson["horizon_bars"] == horizon \
                            and lesson["status"] == "observed":
                        lesson["status"] = "retired"
                continue

            # unfixable cause -> retire, remember, never silently reuse
            reason = retire_reason(causes)
            if reason:
                cause_id = next(c["id"] for c in causes if c["id"] in RETIRE_CAUSES)
                retired[key] = {"method": method, "horizon_bars": horizon,
                                "cause": cause_id, "reason": reason,
                                "round": round_no, "source": "unfixable"}
                round_retired.append(retired[key])
                row["status"] = "retired"
                row["retired_reason"] = reason
                for lesson in lessons:
                    if lesson["method"] == method and lesson["horizon_bars"] == horizon \
                            and lesson["status"] == "observed":
                        lesson["status"] = "retired"
                continue

            actionable = [c for c in causes if c["severity"] != "goal_gap"]
            next_cfg, applied = apply_patches(
                round_configs[key], actionable, horizon=horizon,
                available_horizons=horizons)
            if not promising and not applied:
                # a blocker with no implemented remedy cannot be retried blindly
                first = blockers(causes)[0]
                retired[key] = {"method": method, "horizon_bars": horizon,
                                "cause": first["id"],
                                "reason": (f"{first['id']}: no further honest adjustment "
                                           f"left ({first['evidence']})"),
                                "round": round_no, "source": "no_remedy"}
                round_retired.append(retired[key])
                row["status"] = "retired"
                row["retired_reason"] = retired[key]["reason"]
                continue
            row["lessons_applied"] = applied
            row["next_config"] = dict(sorted(next_cfg.items()))
            for lesson in round_lessons:
                if lesson["method"] == method and lesson["horizon_bars"] == horizon:
                    lesson["remedy_tried"] = bool(applied)
            configs[key] = next_cfg

        round_records.append({
            "round": round_no,
            "name": "screen" if round_no == 1 else "apply_lessons",
            "config": dict(sorted(config.items())),
            "candidate_configs": {f"{key[0]}@{key[1]}": dict(sorted(cfg.items()))
                                  for key, cfg in round_configs.items() if key in results},
            "candidates": rows,
            "causes_tally": tally,
            "retired": round_retired,
            "lessons": round_lessons,
        })

    # ---------------- final report ----------------
    survivors = [key for key in candidates
                 if key not in retired and history.get(key)
                 and history[key][-1]["status"] == "promising"]
    if survivors and not validation_done and run_validation:
        # validation was planned but the loop stopped early: say so, do not imply proof
        validation_done = False

    tally_out: dict[str, dict] = {}
    for lesson in lessons:
        slot = tally_out.setdefault(lesson["cause"], {
            "cause": lesson["cause"], "title": lesson["title"],
            "occurrences": 0, "resolved": 0, "recurred": 0, "retired": 0})
        slot["occurrences"] += 1
        if lesson["status"] == "resolved":
            slot["resolved"] += 1
        elif lesson["status"] in ("recurred", "escalated"):
            slot["recurred"] += 1
        elif lesson["status"] == "retired":
            slot["retired"] += 1
    failure_tally = sorted(tally_out.values(), key=lambda s: (-s["occurrences"], s["cause"]))

    single_symbol_survivors = [
        {"method": row["method"], "horizon_bars": row["horizon_bars"]}
        for record in round_records if record["name"] == "validation"
        for row in record["candidates"]
        if row["status"] == "sample_local_only_single_symbol"]
    if not round_records and retired:
        verdict = "all_candidates_excluded_by_prior_lessons"
    elif validated:
        verdict = "validated_on_supplied_data_still_needs_fresh_unseen_validation"
    elif single_symbol_survivors:
        verdict = "survived_the_recent_slice_but_a_second_symbol_is_required"
    elif validation_done:
        verdict = "no_candidate_survived_validation"
    elif survivors and run_validation:
        verdict = "promising_but_unvalidated"
    elif survivors:
        verdict = "promising_but_no_validation_round_was_run"
    else:
        verdict = "no_candidate_survived_the_failure_gates"

    return {
        "mode": "failure_driven_self_correction",
        "version": VERSION,
        "symbol": symbol_key,
        "sources": [{"symbol": s["symbol"], "bars": len(s["bars"]),
                     "has_volume": s["has_volume"]} for s in sources],
        "config": dict(sorted(config.items())),
        "candidates_tested": len(candidates),
        "methods": methods,
        "horizons": horizons,
        "rounds": round_records,
        "lessons": lessons,
        "failure_tally": failure_tally,
        "resolved_lessons": [
            {"lesson_uid": l["lesson_uid"], "method": l["method"],
             "horizon_bars": l["horizon_bars"], "cause": l["cause"],
             "resolved_in_round": l["resolved_in_round"], "avoid": l["avoid"],
             "remedy": l["remedy"]}
            for l in lessons if l["status"] == "resolved"],
        "retired_candidates": sorted(retired.values(),
                                     key=lambda r: (r["method"], r["horizon_bars"])),
        "validated_candidates": validated,
        "single_symbol_survivors": single_symbol_survivors,
        "verdict": verdict,
        "goal_80": {
            "target_accuracy_pct": float(config["target_accuracy_pct"]),
            "goal_established": False,
            "reason": ("A single self-correction run can never establish the project "
                       "target: that needs 1000+ real hidden-future attempts per "
                       "candidate, positive net after 10 bps, a Wilson lower bound at "
                       "the target and fresh validation on unseen symbols and days."),
        },
        "prior_lessons_used": [lsn.get("lesson_uid") for lsn in prior],
        "honesty": [
            "Signals use completed bars only; the forward return is read after the call is fixed.",
            "Every metric is reported with its attempt count and coverage.",
            "Costs are subtracted from every attempt; gross and net are both shown.",
            "A retired candidate is excluded with its reason, not quietly dropped.",
            "Regime labels are causal (trailing data), so no regime is chosen after the result.",
            "The 80% target is a goal; this run never claims it is reached.",
        ],
        "next_actions": _next_actions(lessons, retired, sources, failure_tally),
        "warning": ("Historical hidden-future research only. Not investment advice, "
                    "not a live edge, and never evidence toward the 80% goal unless "
                    "the GOALS.md gates are met on unseen data."),
    }



def _next_actions(lessons: list[dict], retired: dict, sources: list[dict],
                  failure_tally: list[dict]) -> list[str]:
    actions: list[str] = []
    if retired and not lessons:
        actions.append("Every candidate for this symbol was already retired by stored lessons. "
                       "Clear the lesson ledger (POST /api/lessons/clear) only if you have genuinely "
                       "new data or a new method — otherwise the memory is doing its job.")
        return actions
    causes = {row["cause"] for row in failure_tally}
    if any(c in causes for c in ("single_symbol_only", "selection_bias")):
        actions.append("Import a second lawful series and re-run: one symbol is a case study, not a law.")
    if "insufficient_attempts" in causes or "wide_confidence_interval" in causes:
        actions.append("Supply a longer history so each candidate can reach at least 300 separated attempts.")
    if "cost_eaten_edge" in causes:
        actions.append("Keep the cost-aware filter on: only trade when the causal expected move pays for costs.")
    if "walk_forward_degraded" in causes:
        actions.append("Judge the recent slice separately; do not pool a decaying edge into one number.")
    if "volume_missing" in causes:
        actions.append("Use price-only methods on volume-less data; never synthesise volume.")
    if retired:
        actions.append(f"{len(retired)} candidate(s) are retired and remembered; later runs skip them automatically.")
    if not actions:
        actions.append("Collect fresh unseen data before drawing any conclusion from this sample.")
    actions.append("Zoom out: more symbols, more days and an untouched final holdout are the only real promotion test.")
    return actions


# ---------------------------------------------------------------------------
# 7. Reusable lesson state (for carrying memory across runs)
# ---------------------------------------------------------------------------

def lessons_for_carry_over(lessons: list[dict]) -> list[dict]:
    """Only the states that must change a later test are carried over."""
    out = []
    for lesson in lessons:
        if lesson.get("status") in ("resolved", "recurred", "escalated", "retired"):
            out.append({
                "lesson_uid": lesson.get("lesson_uid"),
                "method": lesson.get("method"),
                "horizon_bars": lesson.get("horizon_bars"),
                "cause": lesson.get("cause"),
                "status": lesson.get("status"),
                "avoid": lesson.get("avoid"),
                "patch": lesson.get("patch") or {},
            })
    return out


def self_correction_spec() -> dict:
    return {
        "name": "Atlas Failure Memory — self-correcting research loop",
        "version": VERSION,
        "loop": [
            "screen every method x horizon on completed bars",
            "diagnose each failure against an explicit cause library",
            "turn every cause into an avoid-rule plus an implemented remedy",
            "re-test only what can still be saved, with the avoid-rules applied",
            "resolved -> keep the fix; recurred -> retire and remember",
            "validate survivors on the recent slice and a second symbol",
        ],
        "cause_library": cause_library(),
        "config_keys": sorted(DEFAULT_CONFIG),
        "verdicts": {
            "validated_on_supplied_data_still_needs_fresh_unseen_validation":
                "survived the supplied screen, recent slice and second symbol (if any)",
            "survived_the_recent_slice_but_a_second_symbol_is_required":
                "held up on the recent slice of one symbol only — still a case study, not a law",
            "all_candidates_excluded_by_prior_lessons":
                "stored lessons already retired every requested candidate for this symbol",
            "no_candidate_survived_validation":
                "nothing held up out of sample on the supplied data",
            "promising_but_unvalidated": "no validation round was run",
            "no_candidate_survived_the_failure_gates":
                "every candidate failed a blocker cause and was retired with a reason",
        },
        "limits": [
            "Research only; not financial advice and not a live execution path.",
            "The 80% target can never be established by this module alone.",
            "A retired candidate is a measured negative result, not a bug.",
        ],
    }


def demo_self_correction(*, rounds: int = MAX_ROUNDS) -> dict:
    """Deterministic synthetic run used by --demo and the web UI."""
    primary = ml.generate_demo_bars("1m", count=1500, seed=15)
    second = ml.generate_demo_bars("1m", count=1200, seed=27)
    result = run_self_correction(
        [{"symbol": "SYNTH-1m-A", "bars": primary},
         {"symbol": "SYNTH-1m-B", "bars": second}],
        methods=["minute_vwap_reversion", "minute_ema_ribbon", "minute_rsi2_snapback",
                 "minute_orb_breakout", "atlas_minute_pulse", "atlas_pressure_wave"],
        horizons=(3, 5, 15), rounds=rounds)
    result["source"] = ("deterministic SYNTHETIC 1m bars (seeds 15/27) — a software "
                        "check of the loop, never market evidence")
    result["source_is_synthetic"] = True
    return result
