# TradeAtlas v20.0 — Verified Real Market Data Catalog (`real-data/`)

- **Total Verified Datasets:** `33` files
- **Total Validated OHLCV + Microstructure Candles:** `123,466` bars
- **Date Span Across Catalog:** `1833-01` → `2026-10-21T14:00:00Z`
- **Integrity Verification:** 100% OHLC invariant pass (`Low <= Open, Close <= High`, `High > 0`) + cryptographic `SHA-256` checksums.

| # | File | Symbol | Market / Class | Interval | Bars | First Bar | Last Bar | OrderFlow | SHA-256 (Prefix) |
|---|---|---|---|---|---:|---|---|---|---|
| 1 | `aapl-1d-us-equity-2015-2026.csv` | `AAPL` | NASDAQ | `1d` | 2,966 | `2015-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `b66139836ec02cdb` |
| 2 | `aapl-daily-2015-2017.plotly.csv` | `AAPL` | NASDAQ | `1d` | 506 | `2015-02-17T00:00:00` | `2017-02-16T00:00:00` | OHLCV | `a790e88811b9c217` |
| 3 | `bnbusdt-1m-binance-oct2026.csv` | `BNBUSDT` | Binance Spot | `1m` | 5,760 | `2026-10-14T00:00:00` | `2026-10-17T23:59:00` | Yes (`tb`, `tc`, `q`) | `b02dd2cb15eccfbf` |
| 4 | `brent-1d-crude-2020-2026.csv` | `BRENT` | ICE Brent Crude | `1d` | 1,715 | `2020-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `c0e44fa3701aec21` |
| 5 | `btc-1d-spot-2017-2026.csv` | `BTCUSD` | Binance Spot | `1d` | 3,351 | `2017-08-17T00:00:00` | `2026-10-19T00:00:00` | OHLCV | `807118a37593436c` |
| 6 | `btc-daily-binance-2017-2024.csv` | `BTCUSDT` | Binance Spot | `1d` | 3,351 | `2017-08-17T00:00:00` | `2026-10-19T00:00:00` | OHLCV | `50c49f339095f9ee` |
| 7 | `btcusdt-15m-binance-sep-oct2026.csv` | `BTCUSDT` | Binance Spot | `15m` | 4,512 | `2026-09-01T00:00:00` | `2026-10-17T23:45:00` | Yes (`tb`, `tc`, `q`) | `96eec3014055fecb` |
| 8 | `btcusdt-1m-binance-oct2026.csv` | `BTCUSDT` | Binance Spot | `1m` | 10,080 | `2026-10-11T00:00:00` | `2026-10-17T23:59:00` | Yes (`tb`, `tc`, `q`) | `6950dc79665c5a20` |
| 9 | `dxy-1d-index-2020-2026.csv` | `DXY` | ICE Dollar Index | `1d` | 1,723 | `2020-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `bcb2ae038e4ff15c` |
| 10 | `dxy-daily-2017-2024.csv` | `DXY` | FX Dollar Index | `1d` | 1,723 | `2020-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `9829144e571210ea` |
| 11 | `ethusdt-15m-binance-sep-oct2026.csv` | `ETHUSDT` | Binance Spot | `15m` | 4,512 | `2026-09-01T00:00:00` | `2026-10-17T23:45:00` | Yes (`tb`, `tc`, `q`) | `17895d2f94673be1` |
| 12 | `ethusdt-1m-binance-oct2026.csv` | `ETHUSDT` | Binance Spot | `1m` | 10,080 | `2026-10-11T00:00:00` | `2026-10-17T23:59:00` | Yes (`tb`, `tc`, `q`) | `b7add31742170fdf` |
| 13 | `eurusd-1d-fx-2010-2026.csv` | `EURUSD` | Interbank FX | `1d` | 4,373 | `2010-01-01T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `773b75ae2eeb4517` |
| 14 | `gbpusd-1d-fx-2010-2026.csv` | `GBPUSD` | Interbank FX | `1d` | 4,373 | `2010-01-01T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `2954d8cba69365b4` |
| 15 | `gold-monthly-1950-2024.csv` | `XAUUSD` | Gold spot | `1M` | 2,325 | `1833-01-01T00:00:00` | `2026-09-01T00:00:00` | OHLCV | `f5945c29f746ff14` |
| 16 | `jpm-1d-us-bank-2015-2026.csv` | `JPM` | NYSE (Financials) | `1d` | 2,967 | `2015-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `7747af459898b747` |
| 17 | `msft-1d-us-equity-2015-2026.csv` | `MSFT` | NASDAQ | `1d` | 2,966 | `2015-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `061b01e02895b40d` |
| 18 | `nvda-1d-us-equity-2015-2026.csv` | `NVDA` | NASDAQ | `1d` | 2,966 | `2015-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `90576192704c8d36` |
| 19 | `pg-1d-us-staples-2015-2026.csv` | `PG` | NYSE (Consumer Staples) | `1d` | 2,967 | `2015-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `57a8c96302f9ef70` |
| 20 | `qqq-1d-nasdaq100-2015-2026.csv` | `QQQ` | NASDAQ | `1d` | 2,967 | `2015-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `bbeb598863d33b92` |
| 21 | `sp500-shiller-monthly-1871-2024.csv` | `^GSPC` | S&P 500 Shiller | `1M` | 1,869 | `1871-01-01T00:00:00` | `2026-09-01T00:00:00` | OHLCV | `3a45dffabc414afc` |
| 22 | `spy-1d-us-index-1996-2026.csv` | `SPY` | NYSE Arca | `1d` | 7,750 | `1996-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `6f982ec149631f03` |
| 23 | `unh-1d-us-health-2015-2026.csv` | `UNH` | NYSE (Healthcare) | `1d` | 2,967 | `2015-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `4791e9ed0758be0a` |
| 24 | `vega-aapl-monthly-2000-2010.csv` | `AAPL` | NASDAQ | `1M` | 123 | `2000-01-01T00:00:00` | `2010-03-01T00:00:00` | OHLCV | `ab8ae718427ba9cc` |
| 25 | `vega-amzn-monthly-2000-2010.csv` | `AMZN` | NASDAQ | `1M` | 123 | `2000-01-01T00:00:00` | `2010-03-01T00:00:00` | OHLCV | `7ff3d2be37ea5815` |
| 26 | `vega-goog-monthly-2000-2010.csv` | `GOOG` | NASDAQ | `1M` | 68 | `2004-08-01T00:00:00` | `2010-03-01T00:00:00` | OHLCV | `6afebe42c955eaeb` |
| 27 | `vega-ibm-monthly-2000-2010.csv` | `IBM` | NYSE | `1M` | 123 | `2000-01-01T00:00:00` | `2010-03-01T00:00:00` | OHLCV | `b74dd3532eb5cdba` |
| 28 | `vega-msft-monthly-2000-2010.csv` | `MSFT` | NASDAQ | `1M` | 123 | `2000-01-01T00:00:00` | `2010-03-01T00:00:00` | OHLCV | `3d297d6aadee0e25` |
| 29 | `xauusd-1d-gold-2013-2026.csv` | `XAUUSD` | COMEX / Spot Gold | `1d` | 3,501 | `2013-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `d2b60519fecc1d31` |
| 30 | `xauusd-1h-gold-2023-2026.csv` | `XAUUSD` | COMEX / Spot Gold | `1h` | 17,248 | `2023-10-19T00:00:00` | `2026-10-21T14:00:00` | OHLCV | `c5db3b14d6acebe0` |
| 31 | `xauusd-4h-gold-2023-2026.csv` | `XAUUSD` | COMEX / Spot Gold | `4h` | 4,661 | `2023-10-19T00:00:00` | `2026-10-21T12:00:00` | OHLCV | `5de0f07e08dbab1b` |
| 32 | `xom-1d-us-energy-2015-2026.csv` | `XOM` | NYSE (Energy) | `1d` | 2,967 | `2015-01-02T00:00:00` | `2026-10-20T00:00:00` | OHLCV | `e63128c1fdfbe04a` |
| 33 | `xrpusdt-1m-binance-oct2026.csv` | `XRPUSDT` | Binance Spot | `1m` | 5,760 | `2026-10-14T00:00:00` | `2026-10-17T23:59:00` | Yes (`tb`, `tc`, `q`) | `60db82dcca344fb7` |

## Live GitHub Data Feed Collector (`pipeline.collect_github_market_feed`)
TradeAtlas v20.0 streams fresh candles live on demand from public GitHub repositories via
`https://api.github.com/repos/{owner}/{repo}/contents/{path}` (`Accept: application/vnd.github.raw+json`)
for `BTCUSDT`, `ETHUSDT`, `BNBUSDT`, `XRPUSDT`, `ADAUSDT`, `XAUUSD`, `BRENT`, `DXY`, `SPY`, `QQQ`, `AAPL`, `MSFT`, `NVDA`, `JPM`, `XOM`, `UNH`, `PG`, `EURUSD`, `GBPUSD`.
