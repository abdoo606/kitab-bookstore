"""Tests for the robustness layer. Run: python3 -m unittest test_analysis -v"""
from __future__ import annotations

import unittest

import analysis as A
import engine

VIX = "data/vix_daily.csv"


class TestVixSeries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bars = engine.load_bars(vix_path=VIX)

    def test_vix_is_merged_only_where_it_exists(self):
        first = next(b.month for b in self.bars if b.vix is not None)
        self.assertEqual(first, "1990-01-01")
        self.assertIsNone(self.bars[0].vix)

    def test_month_end_value_is_the_last_print_of_the_month(self):
        march = next(b for b in self.bars if b.month == "2020-03-01")
        self.assertAlmostEqual(march.vix, 53.54, places=2)

    def test_every_vix_month_is_plausible(self):
        vals = [b.vix for b in self.bars if b.vix is not None]
        self.assertGreater(len(vals), 400)
        self.assertGreater(min(vals), 5.0)
        self.assertLess(max(vals), 100.0)

    def test_loading_without_vix_leaves_it_empty(self):
        self.assertTrue(all(b.vix is None for b in engine.load_bars()))


class TestVixSignal(unittest.TestCase):
    def bar(self, vix):
        return engine.Bar("2020-01-01", 100.0, 0.0, 0.0, vix)

    def history(self, vix_last, n=12):
        out = [engine.Bar("2019-01-01", 100.0, 0.0, 0.0, 15.0) for _ in range(n - 1)]
        out.append(self.bar(vix_last))
        return out

    def test_cap_must_be_positive(self):
        with self.assertRaises(ValueError):
            engine.trend_vix(10, 0)

    def test_missing_vix_blocks_exposure(self):
        self.assertFalse(engine.trend_vix(10, 30.0)(self.history(None)))

    def test_high_vix_blocks_exposure(self):
        self.assertFalse(engine.trend_vix(10, 30.0)(self.history(45.0)))

    def test_low_vix_allows_exposure_when_trend_is_up(self):
        hist = [engine.Bar(f"2019-{i:02d}-01", 100.0 + i, 0.0, 0.0, 15.0) for i in range(1, 13)]
        self.assertTrue(engine.trend_vix(10, 30.0)(hist))


class TestWalkForward(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bars = engine.load_bars(vix_path=VIX)

    def test_segments_are_disjoint_and_ordered(self):
        splits = A.walk_forward(self.bars, lambda: engine.trend_signal(10),
                                [("IS", "1871-01-01", "1950-12-31"), ("OOS", "1951-01-01", "2023-06-01")])
        self.assertEqual(len(splits), 2)
        self.assertLess(splits[0].end, splits[1].start)
        self.assertGreater(splits[1].result.final_equity, 0)

    def test_short_segment_is_skipped_not_crashed(self):
        splits = A.walk_forward(self.bars, lambda: engine.trend_signal(10),
                                [("tiny", "2020-01-01", "2020-06-01")])
        self.assertEqual(splits, [])


class TestSweep(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bars = engine.load_bars(vix_path=VIX)
        cls.seg = A.slice_window(bars, "1990-02-01", "2023-06-01")
        cls.rows = A.parameter_sweep(cls.seg, windows=range(8, 12), vix_caps=(None, 30.0))

    def test_row_count(self):
        self.assertEqual(len(self.rows), 4 * 2)

    def test_every_window_is_profitable_in_this_sample(self):
        self.assertTrue(all(r["final_equity"] > 1000 for r in self.rows))

    def test_stability_bounds(self):
        st = A.sweep_stability(self.rows, "cagr_pct")
        self.assertLessEqual(st["min"], st["median"])
        self.assertLessEqual(st["median"], st["max"])

    def test_vix_cap_reduces_drawdown_across_windows(self):
        for w in range(8, 12):
            plain = next(r for r in self.rows if r["ma_window"] == w and r["vix_cap"] is None)
            capped = next(r for r in self.rows if r["ma_window"] == w and r["vix_cap"] == 30.0)
            self.assertGreater(capped["max_drawdown_pct"], plain["max_drawdown_pct"],
                               f"window {w}: capped drawdown should be shallower")


class TestBootstrap(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bars = engine.load_bars(vix_path=VIX)
        seg = A.slice_window(bars, "1990-02-01", "2023-06-01")
        res = engine.backtest(seg, engine.trend_vix(10, 30.0))
        cls.rets = A.monthly_returns(res)

    def test_returns_length(self):
        self.assertGreater(len(self.rets), 300)

    def test_same_seed_same_answer(self):
        a = A.block_bootstrap(self.rets, n_paths=200, seed=7)
        b = A.block_bootstrap(self.rets, n_paths=200, seed=7)
        self.assertEqual(a, b)

    def test_different_seed_moves_the_median(self):
        a = A.block_bootstrap(self.rets, n_paths=300, seed=1)
        b = A.block_bootstrap(self.rets, n_paths=300, seed=2)
        self.assertNotEqual(a["final_p50"], b["final_p50"])

    def test_percentiles_are_ordered(self):
        bs = A.block_bootstrap(self.rets, n_paths=500)
        self.assertLessEqual(bs["final_p05"], bs["final_p50"])
        self.assertLessEqual(bs["final_p50"], bs["final_p95"])
        self.assertLessEqual(bs["dd_p05"], bs["dd_p50"])

    def test_probability_of_loss_is_a_probability(self):
        bs = A.block_bootstrap(self.rets, n_paths=200)
        self.assertGreaterEqual(bs["probability_of_loss"], 0.0)
        self.assertLessEqual(bs["probability_of_loss"], 1.0)

    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            A.block_bootstrap([])


if __name__ == "__main__":
    unittest.main(verbosity=2)
