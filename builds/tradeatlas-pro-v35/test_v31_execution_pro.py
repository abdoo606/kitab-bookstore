import unittest
import institutional_execution_v31 as v31


class TestTradeAtlasV31ExecutionPro(unittest.TestCase):
    def test_01_quad_horizon_pure_1x_halal_spot_surpasses_v30(self):
        res = v31.run_quad_horizon_spot_v31(capital=1000.0, start_year=2018, currency="USD")
        self.assertGreater(res["final_equity_usd"], 450_000.0)
        self.assertGreater(res["annualized_cagr_pct"], 107.0)
        self.assertGreaterEqual(res["sharpe_ratio"], 1.69)
        self.assertEqual(res["lookahead_leakage_diff"], 0.0)

    def test_02_three_tranche_scaling_and_breakeven_ratchet(self):
        plan = v31.build_spot_entry_tranche_plan_v31(symbol="NVDA", capital=2500.0, currency="SAR")
        self.assertEqual(plan["currency"], "SAR")
        self.assertEqual(len(plan["tranches"]), 3)
        self.assertAlmostEqual(sum(t["weight_pct"] for t in plan["tranches"]), 100.0, places=2)
        self.assertGreater(
            plan["risk_ratchet_protocol"]["zero_loss_breakeven_ratchet_stop"],
            plan["risk_ratchet_protocol"]["blended_full_entry_price"],
        )

    def test_03_rolling_consistency_audit(self):
        aud = v31.compute_rolling_consistency_audit_v31(capital=1000.0)
        self.assertGreaterEqual(aud["calendar_years_tested"], 9)
        self.assertGreater(aud["annual_gain_to_pain_factor"], 3.0)


if __name__ == "__main__":
    unittest.main()
