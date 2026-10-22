# TradeAtlas Pro v26.0 — Institutional Portfolio Autopilot, Walk-Forward Anti-Overfit & Live Zakat Governance

## New Institutional Upgrades in v26.0
1. **Black-Litterman + Inverse-Volatility Risk-Parity Optimizer (`GET /api/v26/portfolio-optimizer`)**
   - Blends trailing covariance across all 10 real bundled market assets with explicit conviction views (`NVDA`, `XAUUSD`, `QQQ`), enforcing 100% Halal `1.0x` spot compliance and exact dollar sizing.
2. **Multi-Era Walk-Forward Anti-Overfitting Auditor (`GET /api/v26/walkforward-audit`)**
   - Verifies out-of-sample compounding across 2018, 2020, and 2022 unseen regimes with zero parameter cherry-picking.
3. **Live Gold-Anchored Zakat (`85g XAUUSD Nisab`) & Tax Reserve Engine (`GET /api/v26/wealth-governance`)**
   - Anchors the `85g` 24K Gold Nisab directly to real `XAUUSD` market closes, calculating exact `2.5%` Zakat + optional tax reserve across `USD / EUR / TRY / SAR / AED`.
