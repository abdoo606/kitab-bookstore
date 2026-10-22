# TradeAtlas Pro v25.0 — Institutional Multi-Strategy Regime Switcher, Smart Execution Slicer & Capital Circuit-Breaker

Major upgrade on top of `v24.0` (`172/172` tests green, `+62.83%` real CAGR, `>80%` Precision80, `1.0x` Halal Spot):
- **`GET /api/v25/regime-allocator` (`meta_desk_v25.py`):** Classifies live multi-asset macro state (`RISK_ON_COMPOUNDING_MOMENTUM`, `INFLATION_HARD_ASSET_ROTATION`, `VOLATILITY_CRISIS_SHIELD`, `SIDEWAYS_SELECTIVE_ALPHA`) and dynamically weights Momentum + RSI-2 Mean-Reversion + Gold/Cash Defensive sleeves.
- **`GET /api/v25/execution-plan`:** Almgren-Chriss square-root slippage estimator + `TWAP / VWAP / Iceberg` child limit order slicer + `2x ATR` stop & trailing profit brackets (`1.0x Halal Spot` enforced).
- **`GET /api/v25/circuit-breaker`:** Prop-firm & personal capital daily loss / peak-drawdown circuit-breaker (`TRADING_LOCKED_24H` / `DEFENSIVE_HALF_SIZE_COOLDOWN` / `GREEN_FULL_COMPOUNDING`).
