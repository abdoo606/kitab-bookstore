import unittest
import market_knowledge_brain_v30 as v30


class TestTradeAtlasV30KnowledgeBrain(unittest.TestCase):
    def test_corpus_expanded_knowledge_integrity(self):
        kb = v30.get_market_knowledge_brain_v30(top_etfs=12)
        self.assertEqual(kb["version"], "30.0")
        cs = kb["corpus_summary"]
        self.assertGreaterEqual(cs["total_distinct_market_and_macro_series"], 680)
        self.assertGreaterEqual(cs["total_authentic_historical_observations"], 1_240_000)
        self.assertGreaterEqual(cs["sp500_fundamental_dossiers_count"], 500)
        self.assertGreaterEqual(cs["global_rotation_etfs_count"], 150)
        self.assertEqual(cs["synthetic_bars_used"], 0)
        self.assertEqual(len(kb["us_vs_global_11_sector_matrix"]), 11)
        self.assertEqual(len(kb["empirical_market_laws"]), 5)

    def test_v30_pure_halal_spot_exceeds_100pct_cagr(self):
        res = v30.run_knowledge_spot_sniper_v30(capital_usd=1000.0, mode="knowledge_trifecta_spot_100", start_year=2018)
        self.assertTrue(res["halal_spot_only"])
        self.assertEqual(res["max_gross_exposure_x"], 1.0)
        self.assertEqual(res["margin_interest_riba_usd"], 0.0)
        self.assertGreater(res["cagr_annual_pct"], 100.0)
        self.assertGreater(res["final_balance_usd"], 350_000.0)
        self.assertGreater(res["sharpe_ratio"], 1.60)

        oos = v30.run_knowledge_spot_sniper_v30(capital_usd=1000.0, mode="breadth_thrust_sniper_100", start_year=2023)
        self.assertGreater(oos["cagr_annual_pct"], 125.0)
        self.assertGreater(oos["sharpe_ratio"], 1.85)

    def test_stock_deep_knowledge_dossier_and_zero_lookahead(self):
        d = v30.get_stock_deep_knowledge_v30("NVDA", capital_usd=2500.0, currency="USD")
        self.assertEqual(d["symbol"], "NVDA")
        self.assertTrue(d["shariah_spot_screening"]["halal_spot_eligible"])
        self.assertGreaterEqual(len(d["empirical_price_intelligence"]["top_sympathy_sector_peers"]), 3)
        self.assertGreater(d["actionable_spot_order_plan"]["last_close_usd"], 0.0)

        audit = v30.verify_zero_lookahead_v30(shock_year=2024)
        self.assertTrue(audit["verified_zero_lookahead"])
        self.assertEqual(audit["max_pre_shock_equity_delta"], 0.0)
        self.assertTrue(audit["identical_weights_every_day"])


if __name__ == "__main__":
    unittest.main()
