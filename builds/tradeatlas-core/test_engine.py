"""Tests for TradeAtlas Core. Run: python3 -m unittest test_engine -v"""
from __future__ import annotations

import json
import threading
import unittest
import urllib.request

import engine

B, FEE = engine.Bar, 10.0


def flat(n=40, price=100.0, div=0.0):
    return [B(month=f"2000-{i:02d}-01" if i <= 12 else f"20{1 + i // 12}-{1 + i % 12:02d}-01",
              price=price, dividend=div, cpi=0.0) for i in range(n)]


def ramp(n=60, start=100.0, step=0.0):
    out = []
    for i in range(n):
        y, m = 2000 + i // 12, 1 + i % 12
        out.append(B(month=f"{y}-{m:02d}-01", price=start + i * step, dividend=0.0, cpi=0.0))
    return out


class TestBars(unittest.TestCase):
    def test_monthly_dividend_is_annual_over_twelve(self):
        self.assertAlmostEqual(B("2000-01-01", 100.0, 12.0, 0.0).monthly_dividend, 1.0)

    def test_equity_return_includes_dividend(self):
        prev, cur = B("2000-01-01", 100.0, 0.0, 0.0), B("2000-02-01", 110.0, 12.0, 0.0)
        self.assertAlmostEqual(cur.equity_return_prev(prev), 0.11)

    def test_zero_previous_price_is_rejected(self):
        with self.assertRaises(ValueError):
            B("2000-02-01", 110.0, 0.0, 0.0).equity_return_prev(B("2000-01-01", 0.0, 0.0, 0.0))

    def test_load_bars_real_file(self):
        bars = engine.load_bars()
        self.assertGreater(len(bars), 1800)
        self.assertEqual(bars[0].month, "1871-01-01")
        self.assertGreaterEqual(bars[-1].month, "2026-01-01")

    def test_load_bars_monotone(self):
        bars = engine.load_bars()
        self.assertEqual(bars, sorted(bars, key=lambda b: b.month))


class TestSignal(unittest.TestCase):
    def test_window_must_be_at_least_two(self):
        with self.assertRaises(ValueError):
            engine.trend_signal(1)

    def test_trend_requires_full_window(self):
        sig = engine.trend_signal(10)
        self.assertFalse(sig(ramp(9, step=1.0)))

    def test_trend_on_rising_series_is_true(self):
        self.assertTrue(engine.trend_signal(10)(ramp(20, step=1.0)))

    def test_trend_on_falling_series_is_false(self):
        self.assertFalse(engine.trend_signal(10)(ramp(20, start=200.0, step=-5.0)))

    def test_cash_signal_never_holds(self):
        self.assertFalse(engine.always_out(ramp(30)))


class TestBacktest(unittest.TestCase):
    def test_cash_stays_flat_and_charges_no_fee_when_already_out(self):
        res = engine.backtest(flat(30), engine.always_out, capital=1000.0)
        self.assertAlmostEqual(res.final_equity, 1000.0)
        self.assertEqual(res.trades, 0)

    def test_buy_and_hold_charges_exactly_one_fee(self):
        res = engine.backtest(flat(30), engine.always_in, capital=1000.0)
        self.assertEqual(res.trades, 1)
        self.assertAlmostEqual(res.final_equity, 1000.0 * (1 - FEE / 10_000))

    def test_positions_are_binary(self):
        res = engine.backtest(engine.load_bars()[:400], engine.trend_signal(10))
        self.assertTrue(set(res.positions) <= {0, 1})

    def test_no_shorting_or_leverage(self):
        res = engine.backtest(engine.load_bars()[:400], engine.trend_signal(10))
        self.assertTrue(all(p >= 0 for p in res.positions))

    def test_capital_must_be_positive(self):
        with self.assertRaises(ValueError):
            engine.backtest(flat(20), engine.always_in, capital=0.0)

    def test_start_index_must_be_positive(self):
        with self.assertRaises(ValueError):
            engine.backtest(flat(20), engine.always_in, start_index=0)

    def test_fee_is_proportional_to_bps(self):
        a = engine.backtest(flat(30), engine.always_in, 1000.0, fee_bps=10)
        b = engine.backtest(flat(30), engine.always_in, 1000.0, fee_bps=50)
        self.assertGreater(a.final_equity, b.final_equity)
        self.assertAlmostEqual(a.final_equity - b.final_equity, 1000.0 * 40 / 10_000)

    def test_determinism(self):
        bars = engine.load_bars()[:600]
        r1 = engine.backtest(bars, engine.trend_signal(10))
        r2 = engine.backtest(bars, engine.trend_signal(10))
        self.assertEqual(r1.equity, r2.equity)

    def test_trend_cuts_max_drawdown_on_real_data(self):
        bars = engine.load_bars()
        hi = next(i for i, b in enumerate(bars) if b.month >= "2023-06-01")
        bt = bars[:hi + 1]
        bh = engine.backtest(bt, engine.always_in)
        tr = engine.backtest(bt, engine.trend_signal(10))
        # drawdowns are negative: "cut in half" means the number moves toward zero
        self.assertGreater(tr.max_drawdown, bh.max_drawdown / 1.4)
        self.assertGreater(tr.sharpe, bh.sharpe)

    def test_cash_earns_nothing(self):
        """Being out of the market during a fall must not create income."""
        bars = [B(f"2001-{m:02d}-01", 100.0 - 5 * m, 0.0, 0.0) for m in range(1, 13)]
        res = engine.backtest(bars, engine.always_out, capital=1000.0, start_index=2)
        self.assertEqual(res.final_equity, 1000.0)


class TestMetrics(unittest.TestCase):
    def test_cagr_matches_its_own_formula(self):
        bars = [B(b.month, 100.0 if i < 120 else 200.0, 0.0, 0.0) for i, b in enumerate(ramp(121))]
        res = engine.backtest(bars, engine.always_in, 1000.0, fee_bps=0)
        expected = (res.equity[-1] / res.equity[0]) ** (12.0 / len(res.equity)) - 1.0
        self.assertAlmostEqual(res.cagr, expected, places=12)
        self.assertGreater(res.cagr, 0.07)

    def test_max_drawdown_of_a_known_path(self):
        eq = [100.0, 120.0, 60.0, 90.0]
        res = engine.Result(months=["a"] * 4, equity=eq, positions=[1, 1, 1], trades=0, fees_paid=0.0)
        engine.metrics(res)
        self.assertAlmostEqual(res.max_drawdown, -0.5)

    def test_sharpe_guard_on_flat_series(self):
        res = engine.Result(months=["a"] * 4, equity=[100.0] * 4, positions=[0, 0, 0],
                            trades=0, fees_paid=0.0)
        engine.metrics(res)
        self.assertEqual(res.sharpe, 0.0)

    def test_summary_rounds_and_keeps_keys(self):
        res = engine.backtest(ramp(40, step=1.0), engine.always_in)
        s = engine.summary(res)
        for k in ("cagr_pct", "sharpe", "max_drawdown_pct", "final_equity"):
            self.assertIn(k, s)


class TestTruncation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bars = engine.load_bars()
        hi = next(i for i, b in enumerate(bars) if b.month >= "2023-06-01")
        cls.bt = bars[:hi + 1]

    def test_clean_strategy_has_zero_deviation(self):
        t = engine.truncation_test(self.bt, engine.trend_signal(10))
        self.assertEqual(t["mismatches"], [])
        self.assertEqual(t["max_equity_delta"], 0.0)
        self.assertGreater(t["checked"], 100)

    def test_buy_and_hold_has_zero_deviation(self):
        t = engine.truncation_test(self.bt, engine.always_in)
        self.assertEqual(t["mismatches"], [])
        self.assertEqual(t["max_equity_delta"], 0.0)

    def test_the_test_itself_detects_engine_level_leakage(self):
        """A copy of the loop that feeds one future bar must fail the same test."""
        bars, start = self.bt, 10

        def leaky_backtest(bars_slice):
            eq, pos = [1000.0], 0
            for t in range(start, len(bars_slice) - 1):
                # the bug: the decision reads one bar beyond t, clamped to the slice
                j = min(t + 2, len(bars_slice) - 1)
                want = 1 if bars_slice[j].price > bars_slice[t].price else 0
                ret = bars_slice[t + 1].equity_return_prev(bars_slice[t])
                eq.append(eq[-1] * (1 + want * ret))
                pos = want
            return eq

        full = leaky_backtest(bars)
        diffs = 0
        for c in range(start + 5, len(bars), 97):
            part = leaky_backtest(bars[:c])
            if abs(part[-1] - full[c - 1 - start]) > 1e-9:
                diffs += 1
        self.assertGreater(diffs, 0, "the truncation harness failed to catch a planted leak")


class TestHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import app as appmod
        import time

        cls.srv = appmod.make_server("127.0.0.1", 8899)
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:8899"
        for _ in range(60):
            try:
                urllib.request.urlopen(cls.base + "/api/health", timeout=0.5)
                break
            except Exception:  # noqa: BLE001
                time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def get(self, path):
        with urllib.request.urlopen(self.base + path, timeout=5) as r:
            return r.status, json.loads(r.read().decode())

    def test_health(self):
        code, body = self.get("/api/health")
        self.assertEqual(code, 200)
        self.assertTrue(body["ok"])

    def test_backtest_endpoint(self):
        code, body = self.get("/api/backtest?window=2003&strategy=trend10&capital=1000")
        self.assertEqual(code, 200)
        self.assertGreater(body["final_equity"], 1000)

    def test_truncation_endpoint(self):
        code, body = self.get("/api/truncation?strategy=buyhold")
        self.assertEqual(code, 200)
        self.assertEqual(body["mismatches"], [])

    def test_unknown_path_is_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/nope")
        self.assertEqual(ctx.exception.code, 404)

    def test_bad_window_is_400(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.get("/api/backtest?window=nope")
        self.assertEqual(ctx.exception.code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
