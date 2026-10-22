"""TradeAtlas Core — CLI and HTTP API (standard library only)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import analysis
import engine

WINDOWS = {
    "full": ("1871-01", "2023-06"),
    "1993": ("1993-01", "2023-06"),
    "2003": ("2003-01", "2023-06"),
    "recent": ("2003-01", "2026-09"),   # price only: dividends stop after 2023-06
}

STRATEGIES = {
    "buyhold": engine.always_in,
    "trend10": engine.trend_signal(10),
    "trend12": engine.trend_signal(12),
    "trend10vix": engine.trend_vix(10, 30.0),
    "cash": engine.always_out,
}

VIX_ERA = ("1990-02", "2023-06")
DATA_VIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "vix_daily.csv")
MA_WINDOW = 10
VIX_CAP = 30.0


def window_bars(name: str):
    bars = engine.load_bars(vix_path=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "data", "vix_daily.csv"))
    if name not in WINDOWS:
        raise ValueError(f"unknown window {name!r}; choose from {sorted(WINDOWS)}")
    start, end = WINDOWS[name]
    lo = next(i for i, b in enumerate(bars) if b.month >= start + "-01")
    hi = next((i for i, b in enumerate(bars) if b.month > end + "-01"), len(bars)) - 1
    return bars, bars[lo:hi + 1]


def live_signal() -> dict:
    """The signal a subscriber would act on now.

    The engine's rule is: the decision taken at the close of month t is the
    position held during month t+1. So the position for the month after the last
    complete observation is `signal(bars)`, with no peeking at the new month.
    """
    bars = engine.load_bars(vix_path=DATA_VIX)
    last = bars[-1]
    ma = sum(b.price for b in bars[-MA_WINDOW:]) / MA_WINDOW
    trend_ok = engine.trend_signal(MA_WINDOW)(bars)
    vix_ok = last.vix is not None and last.vix <= VIX_CAP
    position = "IN" if (trend_ok and vix_ok) else "OUT"

    year, month = int(last.month[:4]), int(last.month[5:7])
    next_ym = f"{year + 1:04d}-01" if month == 12 else f"{year:04d}-{month + 1:02d}"

    reasons = []
    reasons.append(f"price {last.price:,.2f} vs {MA_WINDOW}-month average {ma:,.2f} "
                   f"({(last.price / ma - 1) * 100:+.1f}%)")
    reasons.append(f"VIX {last.vix:.2f} vs cap {VIX_CAP:g} " if last.vix is not None
                   else "VIX missing (treated as unsafe) ")
    if not trend_ok:
        reasons.append("trend filter is off")
    if not vix_ok:
        reasons.append("fear filter is off")

    return {
        "as_of": last.month[:7],
        "decision_for": next_ym,
        "position": position,
        "trend_ok": bool(trend_ok),
        "vix_ok": bool(vix_ok),
        "price": round(last.price, 2),
        "ma10": round(ma, 2),
        "distance_to_ma_pct": round((last.price / ma - 1) * 100, 2),
        "vix": last.vix,
        "vix_cap": VIX_CAP,
        "flip_price": round(ma, 2),
        "dividend_caveat": "dividends are only available to 2023-06; later months are price-only",
        "reasons": reasons,
        "rule": f"hold equity while price > {MA_WINDOW}-month average AND VIX <= {VIX_CAP:g}; "
                "otherwise cash; one switch costs 10 bps",
    }


def run_one(window: str, strategy: str, capital: float, fee_bps: float) -> dict:
    _, bt = window_bars(window)
    if strategy not in STRATEGIES:
        raise ValueError(f"unknown strategy {strategy!r}; choose from {sorted(STRATEGIES)}")
    res = engine.backtest(bt, STRATEGIES[strategy], capital=capital, fee_bps=fee_bps)
    out = engine.summary(res, strategy)
    out["window"] = window
    out["fee_bps"] = fee_bps
    out["price_only"] = window == "recent"
    return out


def cmd_demo(_args) -> int:
    print(f"{'window':10s} {'strategy':9s} {'final equity':>16s} {'CAGR':>8s} {'Sharpe':>7s} {'MaxDD':>8s} {'in market':>10s}")
    print("-" * 76)
    for w in ("full", "1993", "2003", "recent"):
        for s in ("buyhold", "trend10"):
            r = run_one(w, s, 1000.0, 10.0)
            print(f"{w:10s} {s:9s} ${r['final_equity']:>15,.0f} {r['cagr_pct']:>7.2f}% "
                  f"{r['sharpe']:>7.2f} {r['max_drawdown_pct']:>7.2f}% {r['time_in_market_pct']:>9.1f}%")
        print()
    return 0


def cmd_truncation(_args) -> int:
    _, bt = window_bars("full")
    for name in ("trend10", "buyhold"):
        t = engine.truncation_test(bt, STRATEGIES[name])
        print(f"{name:9s} {t['checked']:>4d} cutoffs · mismatches {len(t['mismatches'])} · "
              f"max equity delta {t['max_equity_delta']:.6f} · {t['verdict']}")
    return 0


def research_payload() -> dict:
    bars, _ = window_bars("full")
    seg = analysis.slice_window(bars, *VIX_ERA)
    out = {"window": {"start": VIX_ERA[0], "end": VIX_ERA[1]}, "walk_forward": [], "sweep": [],
           "bootstrap": {}, "headline": []}

    for name in ("buyhold", "trend10", "trend10vix"):
        r = engine.backtest(seg, STRATEGIES[name])
        out["headline"].append(engine.summary(r, name))

    for name, factory in (("trend10", lambda: engine.trend_signal(10)),
                          ("trend10vix", lambda: engine.trend_vix(10, 30.0))):
        splits = analysis.walk_forward(
            bars, factory,
            [("IS", "1990-02-01", "2006-12-31"), ("OOS", "2007-01-01", "2023-06-01")])
        out["walk_forward"].append({"strategy": name, "splits": [sp.as_dict() for sp in splits]})

    out["sweep"] = analysis.parameter_sweep(seg, windows=range(6, 15), vix_caps=(None, 30.0))
    out["sweep_stability"] = {
        "plain": analysis.sweep_stability([r for r in out["sweep"] if r["vix_cap"] is None]),
        "vix30": analysis.sweep_stability([r for r in out["sweep"] if r["vix_cap"] == 30.0]),
    }

    res = engine.backtest(seg, STRATEGIES["trend10vix"])
    out["bootstrap"] = analysis.block_bootstrap(analysis.monthly_returns(res), n_paths=2000, block=12)

    out["cost_sensitivity"] = analysis.cost_sensitivity(
        seg, lambda: engine.trend_vix(10, 30.0), cost_bps=(10.0, 20.0, 30.0, 50.0, 100.0))
    out["deflated_sharpe"] = analysis.deflated_sharpe(
        analysis.monthly_returns(res), [r["sharpe"] for r in out["sweep"]])
    return out


def cmd_research(_args) -> int:
    d = research_payload()
    print(f"VIX era {d['window']['start']} → {d['window']['end']}\n")
    print(f"{'strategy':12s} {'final':>10s} {'CAGR':>7s} {'Sharpe':>7s} {'MDD':>8s} {'in mkt':>7s}")
    for r in d["headline"]:
        print(f"{r['label']:12s} ${r['final_equity']:>9,.0f} {r['cagr_pct']:>6.2f}% "
              f"{r['sharpe']:>7.2f} {r['max_drawdown_pct']:>7.2f}% {r['time_in_market_pct']:>6.1f}%")
    print("\nwalk-forward")
    for blk in d["walk_forward"]:
        for sp in blk["splits"]:
            print(f"  {blk['strategy']:11s} {sp['label']:4s} {sp['segment']}  CAGR {sp['cagr_pct']:>5.2f}%  "
                  f"Sharpe {sp['sharpe']:>4.2f}  MDD {sp['max_drawdown_pct']:>7.2f}%")
    print("\nparameter stability (MA 6..14)")
    for k, st in d["sweep_stability"].items():
        print(f"  {k:5s} CAGR min {st['min']:.2f} median {st['median']:.2f} max {st['max']:.2f} "
              f"(spread {st['spread']:.2f} pts)")
    b = d["bootstrap"]
    print(f"\nblock bootstrap · {b['paths']} paths · {b['block_months']}-month blocks")
    print(f"  final equity p05 ${b['final_p05']:,.0f} · p50 ${b['final_p50']:,.0f} · p95 ${b['final_p95']:,.0f}")
    print(f"  max drawdown p05 {b['dd_p05']:.2f}% · p50 {b['dd_p50']:.2f}% · p95 {b['dd_p95']:.2f}%")
    print(f"  P(final < capital) = {b['probability_of_loss']:.2%}")

    print("\nall-in cost sensitivity (commission + slippage, trend10vix)")
    for r in d["cost_sensitivity"]:
        print(f"  {r['all_in_bps']:>5.0f} bps  final ${r['final_equity']:>9,.0f}  "
              f"CAGR {r['cagr_pct']:>5.2f}%  Sharpe {r['sharpe']:>4.2f}  "
              f"MDD {r['max_drawdown_pct']:>7.2f}%  trades {r['trades']}")

    dsr = d["deflated_sharpe"]
    print(f"\ndeflated Sharpe ratio · {dsr['trials']} rules tried on this window")
    print(f"  winner Sharpe {dsr['sharpe_annual']:.2f} (annualised) vs expected-max "
          f"under the null {dsr['sr0_annual']:.2f}")
    print(f"  skew {dsr['skew']:.2f} · kurtosis {dsr['kurtosis']:.2f} · "
          f"P(true Sharpe > 0) = {dsr['dsr']:.4%}  (z = {dsr['z']:+.2f})")
    return 0


def cmd_signal(_args) -> int:
    d = live_signal()
    print(f"TradeAtlas signal for {d['decision_for']}  (data through {d['as_of']})")
    print(f"  position: {d['position']}")
    for line in d["reasons"]:
        print(f"  - {line}")
    print(f"  rule: {d['rule']}")
    return 0


def cmd_backtest(args) -> int:
    print(json.dumps(run_one(args.window, args.strategy, args.capital, args.fee_bps), indent=2))
    return 0


def make_server(host: str = "0.0.0.0", port: int = 8820) -> ThreadingHTTPServer:
    """Build the HTTP server without starting it (used by cmd_serve and the tests)."""

    class Handler(BaseHTTPRequestHandler):
        def _json(self, code: int, payload: dict) -> None:
            body = json.dumps(payload, indent=2).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *a):  # keep the console quiet
            pass

        def do_GET(self):  # noqa: N802
            u = urlparse(self.path)
            q = {k: v[0] for k, v in parse_qs(u.query).items()}
            try:
                if u.path == "/":
                    rows = []
                    for w in ("full", "1993", "2003", "recent"):
                        for st in ("buyhold", "trend10"):
                            r = run_one(w, st, 1000.0, 10.0)
                            rows.append(
                                f"<tr><td>{w}</td><td>{st}</td>"
                                f"<td class=n>${r['final_equity']:,.0f}</td>"
                                f"<td class=n>{r['cagr_pct']:.2f}%</td>"
                                f"<td class=n>{r['sharpe']:.2f}</td>"
                                f"<td class=n>{r['max_drawdown_pct']:.2f}%</td>"
                                f"<td class=n>{r['time_in_market_pct']:.1f}%</td></tr>")
                    vix_rows = []
                    _, allbars = window_bars("full")
                    seg = analysis.slice_window(allbars, "1990-02", "2023-06")
                    for st in ("buyhold", "trend10", "trend10vix"):
                        r = engine.backtest(seg, STRATEGIES[st])
                        vix_rows.append(
                            f"<tr><td>{st}</td><td class=n>${r.final_equity:,.0f}</td>"
                            f"<td class=n>{r.cagr * 100:.2f}%</td><td class=n>{r.sharpe:.2f}</td>"
                            f"<td class=n>{r.max_drawdown * 100:.2f}%</td>"
                            f"<td class=n>{r.time_in_market * 100:.1f}%</td></tr>")
                    boot = analysis.block_bootstrap(analysis.monthly_returns(
                        engine.backtest(seg, STRATEGIES["trend10vix"])), n_paths=800, block=12)
                    proofer = engine.truncation_test(window_bars("full")[1], STRATEGIES["trend10"])
                    sig = live_signal()
                    html = f"""<!doctype html><meta charset=utf-8>
<title>TradeAtlas Core</title>
<style>body{{background:#0b0f14;color:#e7edf5;font:15px ui-sans-serif,system-ui;
 margin:0;padding:28px}}h1{{font-size:20px;margin:0 0 4px}}
p.s{{color:#8fa1b6;margin:0 0 18px;font-size:13px}}
table{{border-collapse:collapse;width:100%;max-width:860px}}
th,td{{text-align:left;padding:8px 10px;border-bottom:1px solid #1f2937;font-size:13px}}
th{{color:#8fa1b6;font-size:11px;text-transform:uppercase;letter-spacing:.8px}}
td.n{{font-family:ui-monospace,Menlo,monospace;text-align:right}}
.ok{{color:#35c88a}}.tag{{display:inline-block;border:1px solid #1f2937;border-radius:99px;
 padding:3px 9px;font-size:12px;color:#8fa1b6;margin-right:6px}}
.foot{{color:#8fa1b6;font-size:12px;margin-top:18px;max-width:860px}}
.sig{{border:1px solid #1f2937;border-radius:12px;padding:14px 18px;margin:14px 0 22px;max-width:860px}}
.sig .k{{font-size:11px;color:#8fa1b6;text-transform:uppercase;letter-spacing:.8px}}
.sig .v{{font-size:30px;font-weight:600;color:#35c88a;margin:2px 0}}
.sig .m{{font-size:13px;color:#c7d2df}}</style>
<h1>TradeAtlas Core</h1>
<p class=s><span class=tag>long-only spot</span><span class=tag>10 bps per switch</span>
<span class=tag>cash earns 0%</span><span class=tag>Shiller monthly, 1871&ndash;2026</span></p>
<div class=sig><div class=k>signal for {sig['decision_for']}</div>
<div class=v>{sig['position']}</div>
<div class=m>price {sig['price']:,.2f} · 10m avg {sig['ma10']:,.2f} ({sig['distance_to_ma_pct']:+.1f}%) · VIX {sig['vix']:.2f} (cap {sig['vix_cap']:g})</div></div>
<table><tr><th>window</th><th>strategy</th><th>final equity</th><th>CAGR</th><th>Sharpe</th>
<th>max DD</th><th>in market</th></tr>{''.join(rows)}</table>
<h2 style="font-size:15px;margin:26px 0 8px">VIX era, 1990-02 → 2023-06</h2>
<table><tr><th>strategy</th><th>final equity</th><th>CAGR</th><th>Sharpe</th><th>max DD</th><th>in market</th></tr>
{''.join(vix_rows)}</table>
<p class=foot>Block bootstrap, 800 paths, 12-month blocks: final equity p05
${boot['final_p05']:,.0f} · p50 ${boot['final_p50']:,.0f} · p95 ${boot['final_p95']:,.0f};
max drawdown p50 {boot['dd_p50']:.2f}%.</p>
<p class=foot>No-lookahead proof: {proofer['checked']} truncation cutoffs,
mismatches <b class=ok>{len(proofer['mismatches'])}</b>,
largest equity difference <b class=ok>{proofer['max_equity_delta']:.6f}</b>.
API: <code>/api/backtest?window=1993&amp;strategy=trend10</code></p>"""
                    body = html.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(body)))
                    self.end_headers()
                    self.wfile.write(body)
                elif u.path in ("/health", "/api/health"):
                    self._json(200, {"ok": True, "service": "tradeatlas-core",
                                     "windows": sorted(WINDOWS), "strategies": sorted(STRATEGIES)})
                elif u.path == "/api/backtest":
                    self._json(200, run_one(q.get("window", "1993"),
                                            q.get("strategy", "trend10"),
                                            float(q.get("capital", 1000)),
                                            float(q.get("fee_bps", 10))))
                elif u.path == "/api/truncation":
                    _, bt = window_bars(q.get("window", "full"))
                    self._json(200, engine.truncation_test(bt, STRATEGIES.get(q.get("strategy", "trend10"),
                                                                             engine.trend_signal(10))))
                elif u.path == "/api/research":
                    self._json(200, research_payload())
                elif u.path in ("/api/signal", "/signal"):
                    self._json(200, live_signal())
                elif u.path == "/api/windows":
                    self._json(200, {k: {"start": v[0], "end": v[1]} for k, v in WINDOWS.items()})
                else:
                    self._json(404, {"error": "not found", "paths": ["/api/health", "/api/backtest",
                                                                     "/api/truncation", "/api/windows"]})
            except Exception as exc:  # noqa: BLE001 - reported to the caller
                self._json(400, {"error": str(exc)})

    return ThreadingHTTPServer((host, port), Handler)


def cmd_serve(args) -> int:
    srv = make_server(args.host, args.port)
    print(f"TradeAtlas Core on http://{args.host}:{args.port}  (ctrl-c to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="tradeatlas", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("demo", help="print the four windows x two strategies").set_defaults(fn=cmd_demo)
    sub.add_parser("truncation", help="prove no lookahead").set_defaults(fn=cmd_truncation)
    sub.add_parser("research", help="walk-forward, parameter stability, bootstrap").set_defaults(fn=cmd_research)
    sub.add_parser("signal", help="the position to hold next month").set_defaults(fn=cmd_signal)

    b = sub.add_parser("backtest", help="one backtest as json")
    b.add_argument("--window", default="1993", choices=sorted(WINDOWS))
    b.add_argument("--strategy", default="trend10", choices=sorted(STRATEGIES))
    b.add_argument("--capital", type=float, default=1000.0)
    b.add_argument("--fee-bps", dest="fee_bps", type=float, default=10.0)
    b.set_defaults(fn=cmd_backtest)

    s = sub.add_parser("serve", help="http api")
    s.add_argument("--port", type=int, default=8820)
    s.add_argument("--host", default="0.0.0.0")
    s.set_defaults(fn=cmd_serve)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
