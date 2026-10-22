#!/usr/bin/env python3
import unittest
from million_dollar_halal_compounder_v33 import (
    run_superconvex_million_spot_v33,
    run_usdt_vault_profit_skim_v33,
    verify_zero_lookahead_truncation_v33,
)


class TestTradeAtlasV33MillionCompounder(unittest.TestCase):
    def test_01_breaks_one_million_usd_pure_halal_spot_with_lower_drawdown(self):
        res = run_superconvex_million_spot_v33(capital=1000.0, start_year=2018, currency="USD")
        self.assertGreater(res["final_equity_usd"], 1040000.0)
        self.assertGreater(res["annualized_cagr_pct"], 129.0)
        self.assertGreaterEqual(res["sharpe_ratio"], 1.85)
        self.assertGreater(res["max_drawdown_pct"], -38.0)

    def test_02_strict_zero_lookahead_truncation_invariance_and_usdt_vault(self):
        diff = verify_zero_lookahead_truncation_v33()
        self.assertEqual(diff, 0.0)
        vault = run_usdt_vault_profit_skim_v33(capital=1000.0, skim_pct=0.15)
        self.assertGreater(vault["permanently_locked_usdt_vault"], 25000.0)
        self.assertGreater(vault["profit_lock_transfers_count"], 5)


if __name__ == "__main__":
    unittest.main()
