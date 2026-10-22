#!/usr/bin/env python3
import unittest
from halal_gold_haven_compounder_v35 import (
    run_gold_haven_spot_v35,
    verify_zero_lookahead_truncation_v35,
)


class TestTradeAtlasV35GoldHaven(unittest.TestCase):
    def test_01_reaches_1_87_million_usd_and_1_72m_bullion_shield(self):
        res = run_gold_haven_spot_v35(capital=1000.0, start_year=2018)
        self.assertGreater(res["gold_miner_turbo_mode"]["final_equity_usd"], 1870000.0)
        self.assertGreater(res["physical_gold_bullion_shield_mode"]["final_equity_usd"], 1720000.0)
        self.assertGreaterEqual(res["gold_miner_turbo_mode"]["sharpe_ratio"], 1.97)
        self.assertGreater(res["physical_gold_bullion_shield_mode"]["max_drawdown_pct"], -38.0)

    def test_02_zero_lookahead_truncation(self):
        self.assertEqual(verify_zero_lookahead_truncation_v35(), 0.0)


if __name__ == "__main__":
    unittest.main()
