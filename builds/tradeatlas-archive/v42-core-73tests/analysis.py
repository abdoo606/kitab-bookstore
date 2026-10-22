"""Robustness checks — the part that decides whether a backtest is a result or a story.

Every function here uses only `engine`, so the same no-lookahead contract applies.
"""
from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Callable, Sequence

import engine

Signal = Callable[[Sequence[engine.Bar]], bool]


def slice_window(bars: Sequence[engine.Bar], start: str, end: str) -> list[engine.Bar]:
    """Inclusive on both ends. Accepts "YYYY-MM" or "YYYY-MM-DD" without surprises."""
    lo_ym, hi_ym = start[:7], end[:7]
    lo = next((i for i, b in enumerate(bars) if b.month[:7] >= lo_ym), len(bars))
    hi = next((i for i, b in enumerate(bars) if b.month[:7] > hi_ym), len(bars))
    return list(bars[lo:hi])


def monthly_returns(res: engine.Result) -> list[float]:
    return [res.equity[i] / res.equity[i - 1] - 1.0 for i in range(1, len(res.equity))]


# ---------------------------------------------------------------------------
# walk-forward: fit on one era, report on the next
# ---------------------------------------------------------------------------

@dataclass
class Split:
    label: str
    start: str
    end: str
    result: engine.Result

    def as_dict(self) -> dict:
        s = engine.summary(self.result, self.label)
        s["segment"] = f"{self.start[:7]}→{self.end[:7]}"
        return s


def walk_forward(
    bars: Sequence[engine.Bar],
    signal_factory: Callable[[], Signal],
    splits: Sequence[tuple[str, str, str]],
    capital: float = 1000.0,
    fee_bps: float = engine.FEE_BPS_DEFAULT,
) -> list[Split]:
    out = []
    for label, start, end in splits:
        seg = slice_window(bars, start, end)
        if len(seg) < 24:
            continue
        res = engine.backtest(seg, signal_factory(), capital=capital, fee_bps=fee_bps)
        out.append(Split(label=label, start=start, end=end, result=res))
    return out


# ---------------------------------------------------------------------------
# parameter sweep: is the chosen window a cliff or a plateau?
# ---------------------------------------------------------------------------

def parameter_sweep(
    bars: Sequence[engine.Bar],
    windows: Sequence[int] = tuple(range(4, 15)),
    vix_caps: Sequence[float | None] = (None, 30.0),
    capital: float = 1000.0,
    fee_bps: float = engine.FEE_BPS_DEFAULT,
) -> list[dict]:
    rows = []
    for cap in vix_caps:
        for w in windows:
            sig = engine.trend_vix(w, cap) if cap else engine.trend_signal(w)
            res = engine.backtest(bars, sig, capital=capital, fee_bps=fee_bps)
            s = engine.summary(res, f"ma{w}" + (f"+vix{cap:g}" if cap else ""))
            s["ma_window"] = w
            s["vix_cap"] = cap
            rows.append(s)
    return rows


def sweep_stability(rows: Sequence[dict], metric: str = "cagr_pct") -> dict:
    vals = [r[metric] for r in rows]
    return {
        "metric": metric,
        "n": len(vals),
        "min": round(min(vals), 3),
        "median": round(statistics.median(vals), 3),
        "max": round(max(vals), 3),
        "spread": round(max(vals) - min(vals), 3),
        "best_is_not_median": abs(max(vals) - statistics.median(vals)) > 0,
    }


# ---------------------------------------------------------------------------
# execution costs: what happens when the fill is worse than the close
# ---------------------------------------------------------------------------

def cost_sensitivity(
    bars: Sequence[engine.Bar],
    signal_factory: Callable[[], Signal],
    cost_bps: Sequence[float] = (10.0, 20.0, 30.0, 50.0, 100.0),
    capital: float = 1000.0,
) -> list[dict]:
    """Re-run one strategy at several all-in cost levels (commission + slippage).

    The default backtest charges 10 bps. A real fill also pays the spread and
    market impact, so the honest question is not "what does 10 bps give" but
    "how much cost can this rule absorb before it stops adding value".
    """
    rows = []
    for bps in cost_bps:
        if bps < 0:
            raise ValueError("cost cannot be negative")
        res = engine.backtest(bars, signal_factory(), capital=capital, fee_bps=bps)
        row = engine.summary(res, f"all-in {bps:g} bps")
        row["all_in_bps"] = bps
        row["trades"] = res.trades
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# multiple testing: the sweep tried many rules, so how surprising is the winner?
# ---------------------------------------------------------------------------

def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Inverse standard normal (Acklam's rational approximation, |err| < 1e-9)."""
    if not 0.0 < p < 1.0:
        raise ValueError("p must be in (0, 1)")
    a = (-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00)
    b = (-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01)
    c = (-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00)
    d = (7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00)
    plow, phigh = 0.02425, 1.0 - 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    if p > phigh:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)


def moments(xs: Sequence[float]) -> tuple[float, float]:
    """Sample skewness and raw kurtosis (a normal distribution gives 3.0)."""
    n = len(xs)
    if n < 2:
        raise ValueError("need at least two observations")
    mean = sum(xs) / n
    m2 = sum((x - mean) ** 2 for x in xs) / n
    if m2 <= 0:
        return 0.0, 3.0
    sd = math.sqrt(m2)
    skew = sum((x - mean) ** 3 for x in xs) / n / sd ** 3
    kurt = sum((x - mean) ** 4 for x in xs) / n / sd ** 4
    return skew, kurt


def deflated_sharpe(
    returns: Sequence[float],
    trial_sharpes: Sequence[float],
    n_obs: int | None = None,
) -> dict:
    """Deflated Sharpe ratio — Bailey & López de Prado (2014).

    A parameter sweep that picks the best of N rules produces a maximum that is
    biased upward by construction. The DSR asks: given how many rules were tried
    and how dispersed their Sharpe ratios were, what is the probability that the
    winner's true Sharpe ratio is above zero? `trial_sharpes` are annualised, as
    printed by `engine.summary`.
    """
    n = n_obs if n_obs is not None else len(returns)
    if n < 3:
        raise ValueError("need at least three observations")
    if not trial_sharpes:
        raise ValueError("need the Sharpe ratios of the trials")

    mean = sum(returns) / len(returns)
    var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1) if len(returns) > 1 else 0.0
    sd = math.sqrt(var)
    if sd <= 1e-12:            # floating-point dust is still no dispersion
        raise ValueError("returns have no dispersion")
    sr = mean / sd                              # per-month Sharpe, not annualised

    trials = [s / math.sqrt(12.0) for s in trial_sharpes]   # annualised -> monthly
    count = len(trials)
    var_sr = statistics.variance(trials) if count > 1 else 0.0
    gamma = 0.5772156649015329                  # Euler-Mascheroni
    if count > 1 and var_sr > 0:
        sr0 = math.sqrt(var_sr) * (
            (1.0 - gamma) * norm_ppf(1.0 - 1.0 / count)
            + gamma * norm_ppf(1.0 - 1.0 / (count * math.e))
        )
    else:
        sr0 = 0.0

    skew, kurt = moments(returns)
    denom = 1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr * sr
    if denom <= 0:
        denom = 1e-12
    z = (sr - sr0) * math.sqrt(n - 1) / math.sqrt(denom)

    return {
        "trials": count,
        "months": n,
        "sharpe_annual": round(sr * math.sqrt(12.0), 3),
        "sr0_monthly": round(sr0, 4),
        "sr0_annual": round(sr0 * math.sqrt(12.0), 3),
        "skew": round(skew, 3),
        "kurtosis": round(kurt, 3),
        "z": round(z, 3),
        "dsr": round(norm_cdf(z), 6),
    }


# ---------------------------------------------------------------------------
# block bootstrap: how much of the result is the order of the months?
# ---------------------------------------------------------------------------

def block_bootstrap(
    returns: Sequence[float],
    n_paths: int = 2000,
    block: int = 12,
    capital: float = 1000.0,
    seed: int = 20261022,
) -> dict:
    """Resample contiguous blocks of monthly returns, keeping local autocorrelation.

    The point is not to forecast. It is to show how wide the distribution of
    outcomes is for a strategy with exactly these monthly returns.
    """
    if not returns:
        raise ValueError("no returns to resample")
    rng = random.Random(seed)
    n = len(returns)
    finals: list[float] = []
    dds: list[float] = []
    for _ in range(n_paths):
        path: list[float] = []
        while len(path) < n:
            start = rng.randrange(n)
            path.extend(returns[start:start + block])
        path = path[:n]
        eq = capital
        peak, mdd = capital, 0.0
        for r in path:
            eq *= 1.0 + r
            peak = max(peak, eq)
            mdd = min(mdd, eq / peak - 1.0)
        finals.append(eq)
        dds.append(mdd)

    finals.sort()
    dds.sort()

    def pct(xs: list[float], q: float) -> float:
        i = min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))
        return xs[i]

    return {
        "paths": n_paths,
        "block_months": block,
        "final_p05": round(pct(finals, 0.05), 2),
        "final_p50": round(pct(finals, 0.50), 2),
        "final_p95": round(pct(finals, 0.95), 2),
        "dd_p05": round(pct(dds, 0.05) * 100, 2),
        "dd_p50": round(pct(dds, 0.50) * 100, 2),
        "dd_p95": round(pct(dds, 0.95) * 100, 2),
        "probability_of_loss": round(sum(1 for f in finals if f < capital) / len(finals), 4),
    }
