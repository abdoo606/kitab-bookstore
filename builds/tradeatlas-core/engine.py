"""TradeAtlas Core — engine for long-only, fee-charged, no-lookahead backtests.

Design rules (these are enforced by tests, not by comments):
  * a decision made at month t may only read data up to and including t;
  * the order implied by that decision is filled at month t+1, never at t;
  * every position change costs `fee_bps` (default 10 bps);
  * cash earns nothing (no interest income — the product is long-only spot);
  * no leverage, no shorting, no derivatives.

Data source: Robert Shiller's monthly S&P 500 series (price, dividends, CPI),
vendored at data/sp500_shiller.csv so a run is reproducible offline.
"""
from __future__ import annotations

import csv
import math
import os
from dataclasses import dataclass
from typing import Callable, Iterable, Sequence

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA = os.path.join(HERE, "data", "sp500_shiller.csv")

FEE_BPS_DEFAULT = 10.0


@dataclass(frozen=True)
class Bar:
    """One monthly observation. `dividend` is the 12-month moving total per share."""

    month: str          # ISO date of the month start, e.g. "2023-06-01"
    price: float
    dividend: float
    cpi: float
    vix: float | None = None   # month-end VIX close, when the series is loaded

    @property
    def monthly_dividend(self) -> float:
        # Shiller's D column is a 12-month moving total; one month of income is D/12.
        # Dividing is the conservative reading: if the column were already monthly,
        # we understate dividends by 12x rather than overstate them.
        return self.dividend / 12.0

    def equity_return_prev(self, prev: "Bar") -> float:
        """Total return of holding equity from `prev` to `self`."""
        if prev.price <= 0:
            raise ValueError("non-positive price")
        return (self.price + self.monthly_dividend - prev.price) / prev.price


def load_vix(path: str) -> dict[str, float]:
    """Month-end VIX close, keyed by YYYY-MM. Daily file, last observation in each month."""
    out: dict[str, float] = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            day = (row.get("DATE") or "").strip()
            if len(day) < 7:
                continue
            try:
                close = float(row["CLOSE"])
            except (KeyError, ValueError):
                continue
            out[day[:7]] = close      # later rows overwrite earlier ones: last day wins
    return out


def load_bars(path: str = DEFAULT_DATA, vix_path: str | None = None) -> list[Bar]:
    bars: list[Bar] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                price = float(row["SP500"])
            except (KeyError, ValueError):
                continue
            if price <= 0:
                continue
            bars.append(Bar(
                month=row["Date"],
                price=price,
                dividend=_f(row.get("Dividend")),
                cpi=_f(row.get("Consumer Price Index")),
            ))
    if len(bars) < 24:
        raise ValueError(f"not enough usable rows in {path}")
    if vix_path:
        vix = load_vix(vix_path)
        bars = [Bar(b.month, b.price, b.dividend, b.cpi, vix.get(b.month[:7])) for b in bars]
    return bars


def _f(v: str | None) -> float:
    try:
        return float(v) if v not in (None, "") else 0.0
    except ValueError:
        return 0.0


# ---------------------------------------------------------------------------
# signals — each receives bars[:t+1] and returns True (hold equity) or False
# ---------------------------------------------------------------------------

def trend_signal(window: int = 10) -> Callable[[Sequence[Bar]], bool]:
    """Hold equity while the price is above its `window`-month moving average."""
    if window < 2:
        raise ValueError("window must be >= 2")

    def signal(history: Sequence[Bar]) -> bool:
        if len(history) < window:
            return False
        ma = sum(b.price for b in history[-window:]) / window
        return history[-1].price > ma

    return signal


def trend_vix(window: int = 10, vix_cap: float = 30.0) -> Callable[[Sequence[Bar]], bool]:
    """Trend filter with a fear filter: hold only when VIX is at or below `vix_cap`.

    A month without a VIX observation is treated as *not* holdable, which is the
    conservative direction: it can only reduce exposure.
    """
    if window < 2:
        raise ValueError("window must be >= 2")
    if vix_cap <= 0:
        raise ValueError("vix_cap must be positive")
    trend = trend_signal(window)

    def signal(history: Sequence[Bar]) -> bool:
        last = history[-1]
        if last.vix is None or last.vix > vix_cap:
            return False
        return trend(history)

    return signal


def always_in(_history: Sequence[Bar]) -> bool:
    return True


def always_out(_history: Sequence[Bar]) -> bool:
    return False


# ---------------------------------------------------------------------------
# backtest
# ---------------------------------------------------------------------------

@dataclass
class Result:
    months: list[str]
    equity: list[float]          # portfolio value, starts at `capital`
    positions: list[int]         # exposure held during that month (0 or 1)
    trades: int
    fees_paid: float

    # metrics, filled by `metrics()`
    total_return: float = 0.0
    cagr: float = 0.0
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    time_in_market: float = 0.0
    years: float = 0.0
    final_equity: float = 0.0


def backtest(
    bars: Sequence[Bar],
    signal: Callable[[Sequence[Bar]], bool],
    capital: float = 1000.0,
    fee_bps: float = FEE_BPS_DEFAULT,
    start_index: int = 10,
) -> Result:
    """Run the strategy. Position for month t+1 is decided from data up to month t."""
    if start_index < 1:
        raise ValueError("start_index must be >= 1")
    if capital <= 0:
        raise ValueError("capital must be positive")
    fee = fee_bps / 10_000.0

    equity = [capital]
    months = [bars[start_index].month]
    positions: list[int] = []
    trades = 0
    fees_paid = 0.0

    position = 0
    for t in range(start_index, len(bars) - 1):
        # decision uses only bars[0..t]
        want = 1 if signal(bars[:t + 1]) else 0
        turnover = abs(want - position)
        cost = equity[-1] * turnover * fee      # charged at the moment of the trade,
        fees_paid += cost                        # never by rewriting a past month
        if turnover:
            trades += 1

        ret = bars[t + 1].equity_return_prev(bars[t])
        equity.append(equity[-1] * (1.0 - turnover * fee) * (1.0 + want * ret))
        positions.append(want)
        months.append(bars[t + 1].month)
        position = want

    res = Result(months=months, equity=equity, positions=positions,
                 trades=trades, fees_paid=fees_paid)
    metrics(res)
    return res


def metrics(res: Result) -> Result:
    eq = res.equity
    res.final_equity = eq[-1]
    res.total_return = eq[-1] / eq[0] - 1.0
    years = len(eq) / 12.0
    res.years = years
    res.cagr = (eq[-1] / eq[0]) ** (1.0 / years) - 1.0 if years > 0 and eq[-1] > 0 else 0.0

    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq))]
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
        sd = math.sqrt(var)
        res.sharpe = (mean / sd) * math.sqrt(12.0) if sd > 0 else 0.0

    peak = eq[0]
    mdd = 0.0
    for v in eq:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    res.max_drawdown = mdd
    res.time_in_market = sum(res.positions) / len(res.positions) if res.positions else 0.0
    return res


# ---------------------------------------------------------------------------
# proof that no future information leaks into a decision
# ---------------------------------------------------------------------------

def truncation_test(
    bars: Sequence[Bar],
    signal: Callable[[Sequence[Bar]], bool],
    capital: float = 1000.0,
    fee_bps: float = FEE_BPS_DEFAULT,
    start_index: int = 10,
    cutoffs: Iterable[int] | None = None,
) -> dict:
    """Re-run the engine on truncated history and compare with the full run.

    For each cutoff c, the run that only knows bars[:c] must produce exactly the
    same positions and the same equity as the full run does at index c-1.
    Any dependence on future bars shows up as a mismatch here.
    """
    full = backtest(bars, signal, capital=capital, fee_bps=fee_bps, start_index=start_index)
    n = len(bars)
    if cutoffs is None:
        step = max(1, (n - start_index - 1) // 120)
        cutoffs = range(start_index + 2, n, step)

    checked = 0
    worst = 0.0
    mismatches: list[dict] = []
    for c in cutoffs:
        if c <= start_index + 1 or c > n:
            continue
        part = backtest(bars[:c], signal, capital=capital, fee_bps=fee_bps,
                        start_index=start_index)
        i_full = c - 1 - start_index      # index of the last month in the partial run
        if i_full >= len(full.equity):
            continue
        d_eq = abs(part.equity[-1] - full.equity[i_full])
        d_pos = abs(part.positions[-1] - full.positions[i_full - 1])
        worst = max(worst, d_eq)
        checked += 1
        if d_eq > 1e-9 or d_pos != 0:
            mismatches.append({"cutoff_index": c, "month": bars[c - 1].month,
                               "equity_delta": d_eq, "position_delta": d_pos})

    return {
        "checked": checked,
        "mismatches": mismatches,
        "max_equity_delta": worst,
        # 0.000000 is what a clean run prints; the value is the measured maximum
        "verdict": "clean" if not mismatches else "LOOKAHEAD DETECTED",
    }


def summary(res: Result, label: str = "") -> dict:
    return {
        "label": label,
        "from": res.months[0][:7],
        "to": res.months[-1][:7],
        "years": round(res.years, 3),
        "capital": round(res.equity[0], 2),
        "final_equity": round(res.final_equity, 2),
        "total_return_pct": round(res.total_return * 100, 2),
        "cagr_pct": round(res.cagr * 100, 2),
        "sharpe": round(res.sharpe, 3),
        "max_drawdown_pct": round(res.max_drawdown * 100, 2),
        "time_in_market_pct": round(res.time_in_market * 100, 1),
        "trades": res.trades,
        "fees_paid_usd": round(res.fees_paid, 2),
    }
