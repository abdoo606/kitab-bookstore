"""Robustness checks — the part that decides whether a backtest is a result or a story.

Every function here uses only `engine`, so the same no-lookahead contract applies.
"""
from __future__ import annotations

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
