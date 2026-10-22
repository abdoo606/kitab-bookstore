#!/usr/bin/env python3
import unittest
from parabolic_million5_compounder_v34 import (
    run_parabolic_million5_spot_v34,
    verify_zero_lookahead_truncation_v34,
)


class TestTradeAtlasV34MillionFiveCompounder(unittest.TestCase):
    def test_01_breaks_1_5_million_usd_pure_1x_halal_spot_with_194_sharpe(self):
        res = run_parabolic_million5_spot_v34(capital=1000.0, start_year=2018, currency="USD")
        self.assertGreater(res["final_equity_usd"], 1510000.0)
        self.assertGreater(res["annualized_cagr_pct"], 139.5)
        self.assertGreaterEqual(res["sharpe_ratio"], 1.94)
        self.assertGreater(res["max_drawdown_pct"], -38.0)

    def test_02_strict_zero_lookahead_truncation_proof(self):
        self.assertEqual(verify_zero_lookahead_truncation_v34(), 0.0)


if __name__ == "__main__":
    unittest.main()
