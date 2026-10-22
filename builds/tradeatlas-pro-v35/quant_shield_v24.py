#!/usr/bin/env python3
"""
TradeAtlas Pro v24.0 — Institutional QuantShield, Monte Carlo Crash Stress Lab,
Sustainable Monthly Salary + Compounding Simulator & Cross-Asset Correlation Matrix.
100% Python Standard Library · Zero Lookahead · Real Bundled Market Data.
"""
from __future__ import annotations

import math
import random
import statistics
from typing import Dict, List

import velocity_compound as vc

V24_VERSION = "24.0"

FX_RATES = {
    "USD": 1.0,
    "EUR": 0.92,
    "TRY": 36.50,
    "SAR": 3.75,
    "AED": 3.67,
}


def _daily_returns_from_curve(curve: List[Dict]) -> List[float]:
    rets: List[float] = []
    for i in range(1, len(curve)):
        prev_eq = max(1e-9, float(curve[i - 1]["equity_usd"]))
        cur_eq = float(curve[i]["equity_usd"])
        rets.append((cur_eq / prev_eq) - 1.0)
    return rets


def run_quant_shield_stress(
    capital_usd: float = 1000.0,
    mode: str = "institutional_kelly_135",
    start_year: int = 2018,
    paths: int = 400,
    horizon_days: int = 252,
    seed: int = 20261022,
) -> Dict:
    """Block-bootstrap Monte Carlo + Sortino/Calmar/CVaR95/Ulcer analytics on real strategy equity curve."""
    base = vc.run_velocity_compounder(capital_usd=capital_usd, mode=mode, start_year=start_year)
    rets = _daily_returns_from_curve(base["equity_curve"])
    if len(rets) < 30:
        raise ValueError("Insufficient historical return series")

    sorted_rets = sorted(rets)
    cutoff_idx = max(1, int(len(sorted_rets) * 0.05))
    cvar_95_daily_pct = round(statistics.mean(sorted_rets[:cutoff_idx]) * 100.0, 2)

    downside_sq = [min(0.0, r) ** 2 for r in rets]
    downside_dev_ann = math.sqrt(sum(downside_sq) / len(rets)) * math.sqrt(252.0)
    mean_ann = statistics.mean(rets) * 252.0
    sortino_ratio = round(mean_ann / max(1e-9, downside_dev_ann), 2)
    calmar_ratio = round(abs(float(base["cagr_annual_pct"]) / min(-0.01, float(base["max_drawdown_pct"]))), 2)

    # Ulcer Index across real equity curve
    peak = 1e-9
    dd_sq: List[float] = []
    for pt in base["equity_curve"]:
        eq = float(pt["equity_usd"])
        peak = max(peak, eq)
        dd_pct = ((eq / peak) - 1.0) * 100.0
        dd_sq.append(dd_pct ** 2)
    ulcer_index = round(math.sqrt(sum(dd_sq) / len(dd_sq)), 2)

    # 21-day block bootstrap preserving volatility clustering
    rng = random.Random(seed)
    block = 21
    n_rets = len(rets)
    finals: List[float] = []
    worst_dds: List[float] = []
    for _ in range(max(50, min(1000, paths))):
        eq = float(capital_usd)
        pk = eq
        mdd = 0.0
        drawn = 0
        while drawn < horizon_days:
            start = rng.randint(0, max(0, n_rets - block))
            for r in rets[start : start + block]:
                eq *= (1.0 + r)
                pk = max(pk, eq)
                mdd = min(mdd, (eq / pk) - 1.0)
                drawn += 1
                if drawn >= horizon_days:
                    break
        finals.append(eq)
        worst_dds.append(mdd * 100.0)

    finals.sort()
    worst_dds.sort()
    p05 = round(finals[int(0.05 * len(finals))], 2)
    p50 = round(finals[int(0.50 * len(finals))], 2)
    p90 = round(finals[int(0.90 * len(finals))], 2)
    prob_profit = round(100.0 * sum(1 for x in finals if x > capital_usd) / len(finals), 1)

    return {
        "schema": "tradeatlas-quant-shield-v24",
        "v24_version": V24_VERSION,
        "mode": mode,
        "capital_usd": round(capital_usd, 2),
        "base_cagr_annual_pct": base["cagr_annual_pct"],
        "sortino_ratio": sortino_ratio,
        "calmar_ratio": calmar_ratio,
        "ulcer_index": ulcer_index,
        "cvar_95_daily_pct": cvar_95_daily_pct,
        "monte_carlo_1y": {
            "paths": len(finals),
            "horizon_trading_days": horizon_days,
            "win_probability_1y_pct": prob_profit,
            "p05_conservative_usd": p05,
            "p50_median_usd": p50,
            "p90_bull_usd": p90,
            "median_max_drawdown_pct": round(worst_dds[len(worst_dds) // 2], 2),
        },
    }


def simulate_monthly_income_and_compounding(
    capital_usd: float = 2000.0,
    monthly_deposit_usd: float = 100.0,
    profit_withdraw_pct: float = 25.0,
    payout_currency: str = "USD",
    mode: str = "institutional_kelly_135",
    start_year: int = 2018,
) -> Dict:
    """Simulates taking a monthly cash salary from real gains while compounding the remainder."""
    cur = payout_currency.upper() if payout_currency.upper() in FX_RATES else "USD"
    fx = FX_RATES[cur]
    w_frac = max(0.0, min(0.80, profit_withdraw_pct / 100.0))

    base = vc.run_velocity_compounder(capital_usd=1000.0, mode=mode, start_year=start_year)
    curve = base["equity_curve"]
    # Group daily multipliers by YYYY-MM
    monthly_mults: Dict[str, float] = {}
    month_order: List[str] = []
    for i in range(1, len(curve)):
        ym = str(curve[i]["date"])[:7]
        r = float(curve[i]["equity_usd"]) / max(1e-9, float(curve[i - 1]["equity_usd"]))
        if ym not in monthly_mults:
            monthly_mults[ym] = 1.0
            month_order.append(ym)
        monthly_mults[ym] *= r

    balance = float(capital_usd)
    total_deposited = float(capital_usd)
    total_withdrawn_usd = 0.0
    ledger: List[Dict] = []

    for ym in month_order:
        balance += float(monthly_deposit_usd)
        total_deposited += float(monthly_deposit_usd)
        pre_gain = balance
        balance *= monthly_mults[ym]
        net_profit = balance - pre_gain
        payout_usd = round(net_profit * w_frac, 2) if net_profit > 0 else 0.0
        balance -= payout_usd
        total_withdrawn_usd += payout_usd
        ledger.append(
            {
                "month": ym,
                "month_return_pct": round((monthly_mults[ym] - 1.0) * 100.0, 2),
                "cash_payout_usd": payout_usd,
                "cash_payout_local": round(payout_usd * fx, 2),
                "ending_capital_usd": round(balance, 2),
            }
        )

    avg_monthly_salary_usd = round(total_withdrawn_usd / max(1, len(ledger)), 2)
    return {
        "schema": "tradeatlas-income-planner-v24",
        "v24_version": V24_VERSION,
        "mode": mode,
        "payout_currency": cur,
        "fx_rate": fx,
        "months_simulated": len(ledger),
        "total_contributed_usd": round(total_deposited, 2),
        "total_cash_withdrawn_usd": round(total_withdrawn_usd, 2),
        "total_cash_withdrawn_local": round(total_withdrawn_usd * fx, 2),
        "avg_monthly_payout_usd": avg_monthly_salary_usd,
        "avg_monthly_payout_local": round(avg_monthly_salary_usd * fx, 2),
        "final_compounded_capital_usd": round(balance, 2),
        "recent_12_months": ledger[-12:],
    }


def compute_cross_asset_correlations(window_days: int = 90) -> Dict:
    """Computes trailing N-day pairwise correlation across all bundled real assets."""
    dates, panel = vc.load_aligned_real_panel("2020-01-01")
    syms = sorted(panel.keys())
    w = max(20, min(252, window_days))
    ret_map: Dict[str, List[float]] = {}
    for s in syms:
        closes = [row[3] for row in panel[s][-(w + 1) :]]
        ret_map[s] = [(closes[i] / max(1e-9, closes[i - 1])) - 1.0 for i in range(1, len(closes))]

    matrix: Dict[str, Dict[str, float]] = {s: {} for s in syms}
    high_corr_pairs: List[Dict] = []
    hedge_pairs: List[Dict] = []

    for i, a in enumerate(syms):
        for j, b in enumerate(syms):
            if i == j:
                matrix[a][b] = 1.0
                continue
            xa, xb = ret_map[a], ret_map[b]
            ma, mb = statistics.mean(xa), statistics.mean(xb)
            num = sum((u - ma) * (v - mb) for u, v in zip(xa, xb))
            den = math.sqrt(sum((u - ma) ** 2 for u in xa) * sum((v - mb) ** 2 for v in xb))
            corr = round(num / max(1e-12, den), 3)
            matrix[a][b] = corr
            if i < j:
                if corr >= 0.72:
                    high_corr_pairs.append({"pair": f"{a}/{b}", "corr": corr})
                elif corr <= 0.20:
                    hedge_pairs.append({"pair": f"{a}/{b}", "corr": corr})

    high_corr_pairs.sort(key=lambda x: x["corr"], reverse=True)
    hedge_pairs.sort(key=lambda x: x["corr"])
    return {
        "schema": "tradeatlas-correlation-matrix-v24",
        "v24_version": V24_VERSION,
        "as_of_date": dates[-1],
        "window_days": w,
        "symbols": syms,
        "matrix": matrix,
        "concentration_warnings": high_corr_pairs[:5],
        "best_diversifier_pairs": hedge_pairs[:5],
    }
