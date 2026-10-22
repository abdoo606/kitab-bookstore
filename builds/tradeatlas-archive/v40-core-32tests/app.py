"""TradeAtlas Core — CLI and HTTP API (standard library only)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

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
    "cash": engine.always_out,
}


def window_bars(name: str):
    bars = engine.load_bars()
    if name not in WINDOWS:
        raise ValueError(f"unknown window {name!r}; choose from {sorted(WINDOWS)}")
    start, end = WINDOWS[name]
    lo = next(i for i, b in enumerate(bars) if b.month >= start + "-01")
    hi = next((i for i, b in enumerate(bars) if b.month > end + "-01"), len(bars)) - 1
    return bars, bars[lo:hi + 1]


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
                    proofer = engine.truncation_test(window_bars("full")[1], STRATEGIES["trend10"])
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
.foot{{color:#8fa1b6;font-size:12px;margin-top:18px;max-width:860px}}</style>
<h1>TradeAtlas Core</h1>
<p class=s><span class=tag>long-only spot</span><span class=tag>10 bps per switch</span>
<span class=tag>cash earns 0%</span><span class=tag>Shiller monthly, 1871&ndash;2026</span></p>
<table><tr><th>window</th><th>strategy</th><th>final equity</th><th>CAGR</th><th>Sharpe</th>
<th>max DD</th><th>in market</th></tr>{''.join(rows)}</table>
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
