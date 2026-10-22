import unittest
import macro_shock_compounder_v32 as v32


class TestTradeAtlasV32MacroCompounder(unittest.TestCase):
    def test_01_macro_crisis_shield_surpasses_640k_pure_spot(self):
        res = v32.run_macro_crisis_shield_spot_v32(capital=1000.0, monthly_deposit_usd=0.0, start_year=2018)
        self.assertGreater(res["final_equity_usd"], 640_000.0)
        self.assertGreater(res["annualized_cagr_pct"], 116.0)
        self.assertGreaterEqual(res["sharpe_ratio"], 1.78)
        self.assertGreater(res["max_drawdown_pct"], -43.0)
        self.assertEqual(res["lookahead_leakage_diff"], 0.0)

    def test_02_monthly_savings_wealth_builder_and_pre_trade_gate(self):
        dca = v32.run_macro_crisis_shield_spot_v32(capital=1000.0, monthly_deposit_usd=100.0, start_year=2023, currency="USD")
        self.assertGreater(dca["final_equity_usd"], dca["total_contributed"] * 3.0)
        gate = v32.evaluate_pre_trade_sharia_gate_v32(symbol="NVDA", capital=2500.0)
        self.assertEqual(gate["passed_checks"], 5)


if __name__ == "__main__":
    unittest.main()
