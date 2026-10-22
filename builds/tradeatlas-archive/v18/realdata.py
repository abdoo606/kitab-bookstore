"""
TradeAtlas Real Data — v18.0 Real Market Infusion
Honest multi-asset historical data ingestion with provenance.

Research software only. Not financial advice. goal_established false forever.
Version: 18.0 — Real Data Revolution
"""
from __future__ import annotations

import csv
import io
import pathlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Any

VERSION = "18.0"
DB_VERSION = 5  # bump for real_data_catalog table

# Provenance registry — every bundled file has a record
PROVENANCE = {
    "aapl-daily-2015-2017.plotly.csv": {
        "symbol": "AAPL",
        "market": "NASDAQ",
        "interval": "1d",
        "bars": 506,
        "range": "2015-02-17 → 2017-02-16",
        "source": "plotly/datasets finance-charts-apple.csv blob 7b1bab3",
        "fetched": "2026-10-21 GitHub API",
        "license": "MIT (plotly sample)",
        "type": "daily_ohlcv_adjusted",
    },
    "vega-aapl-monthly-2000-2010.csv": {
        "symbol": "AAPL",
        "market": "NASDAQ",
        "interval": "1M",
        "bars": 123,
        "range": "2000-01 → 2010-03",
        "source": "vega/vega-datasets data/stocks.csv blob 58e2ce1",
        "fetched": "2026-10-21 GitHub API",
        "license": "BSD (vega)",
        "type": "monthly_close_only",
    },
    "vega-amzn-monthly-2000-2010.csv": {
        "symbol": "AMZN",
        "market": "NASDAQ",
        "interval": "1M",
        "bars": 123,
        "range": "2000-01 → 2010-03",
        "source": "vega/vega-datasets",
        "license": "BSD",
        "type": "monthly_close_only",
    },
    "vega-goog-monthly-2000-2010.csv": {
        "symbol": "GOOG",
        "market": "NASDAQ",
        "interval": "1M",
        "bars": 68,
        "range": "2004-08 → 2010-03",
        "source": "vega/vega-datasets",
        "license": "BSD",
        "type": "monthly_close_only",
    },
    "vega-ibm-monthly-2000-2010.csv": {
        "symbol": "IBM",
        "market": "NYSE",
        "interval": "1M",
        "bars": 123,
        "range": "2000-01 → 2010-03",
        "source": "vega/vega-datasets",
        "license": "BSD",
        "type": "monthly_close_only",
    },
    "vega-msft-monthly-2000-2010.csv": {
        "symbol": "MSFT",
        "market": "NASDAQ",
        "interval": "1M",
        "bars": 123,
        "range": "2000-01 → 2010-03",
        "source": "vega/vega-datasets",
        "license": "BSD",
        "type": "monthly_close_only",
    },
    "btc-daily-binance-2017-2024.csv": {
        "symbol": "BTCUSDT",
        "market": "Binance Spot",
        "interval": "1d",
        "bars": 3352,
        "range": "2017-08-17 → 2024-10-21",
        "source": "jptrustlearning/btc btc_prices.csv — Binance API primary, yfinance fallback, CC",
        "fetched": "2026-10-21 via codeload github api",
        "license": "MIT",
        "type": "daily_ohlcv_crypto",
    },
    "sp500-shiller-monthly-1871-2024.csv": {
        "symbol": "^GSPC",
        "market": "S&P 500 Shiller",
        "interval": "1M",
        "bars": 1870,
        "range": "1871-01 → 2024-09",
        "source": "datasets/s-and-p-500 data/data.csv — Shiller + FRED",
        "fetched": "2026-10-21",
        "license": "Open Data (Shiller/FRED)",
        "type": "monthly_index",
    },
    "gold-monthly-1950-2024.csv": {
        "symbol": "XAUUSD",
        "market": "Gold spot",
        "interval": "1M",
        "bars": 2326,
        "range": "1833-01 → 2024-09 (monthly) — usable 1950→",
        "source": "datasets/gold-prices data/monthly.csv — World Gold Council via FRED",
        "fetched": "2026-10-21",
        "license": "ODC",
        "type": "monthly_gold",
    },
    "dxy-daily-2017-2024.csv": {
        "symbol": "DXY",
        "market": "FX Dollar Index",
        "interval": "1d",
        "bars": 1724,
        "range": "2020-01-02 → 2024-10-?? (from btc repo dxy_prices.csv)",
        "source": "jptrustlearning/btc dxy_prices.csv",
        "fetched": "2026-10-21",
        "license": "MIT",
        "type": "daily_fx_index",
    },
}

# Known Thai headers mapping
THAI_HEADER_MAP = {
    "วันที่": "date",
    "ราคาเปิด": "open",
    "ราคาสูงสุด": "high",
    "ราคาต่ำสุด": "low",
    "ราคาปิด": "close",
    "ปริมาณซื้อขาย": "volume",
}

def _strip_bom(text: str) -> str:
    if text.startswith("\ufeff"):
        return text[1:]
    return text

def detect_format(header: List[str]) -> str:
    h = [x.strip() for x in header]
    h_lower = [x.lower() for x in h]
    # Thai BTC/DXY
    if "วันที่" in h or any("ราคา" in x for x in h):
        return "thai_ohlcv"
    if h_lower == ["date", "price"]:
        return "gold_monthly"
    if "sp500" in h_lower or "consumer price index" in h_lower:
        return "shiller_sp500"
    if h_lower[:5] == ["date", "open", "high", "low", "close"]:
        return "standard_ohlcv"
    if "adjusted" in " ".join(h_lower):
        return "plotly_aapl"
    return "unknown"

def _parse_date_flexible(s: str) -> datetime:
    s = s.strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m", "%Y/%m/%d", "%m/%d/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    # Try YYYY-MM
    m = re.match(r"(\d{4})-(\d{1,2})$", s)
    if m:
        return datetime(int(m.group(1)), int(m.group(2)), 1, tzinfo=timezone.utc)
    raise ValueError(f"Unparseable date: {s}")

def normalize_to_bars(rows: List[Dict[str, str]], fmt: str) -> List[Dict[str, Any]]:
    bars = []
    for r in rows:
        try:
            if fmt == "thai_ohlcv":
                # Thai header mapped
                mapped = {THAI_HEADER_MAP.get(k.strip(), k.strip()): v for k, v in r.items()}
                dt = _parse_date_flexible(mapped["date"])
                o = float(mapped["open"].replace(",", ""))
                h = float(mapped["high"].replace(",", ""))
                l = float(mapped["low"].replace(",", ""))
                c = float(mapped["close"].replace(",", ""))
                vol = float(mapped.get("volume", "0").replace(",", "") or 0)
                bars.append({"t": dt.isoformat(), "o": o, "h": h, "l": l, "c": c, "v": vol})
            elif fmt == "shiller_sp500":
                dt = _parse_date_flexible(r["Date"] if "Date" in r else r["date"])
                price = float(r.get("SP500") or r.get("sp500") or r.get("S&P500") or "0")
                if price == 0:
                    continue
                # monthly index — synthesize OHLC as price
                bars.append({"t": dt.isoformat(), "o": price, "h": price, "l": price, "c": price, "v": 0})
            elif fmt == "gold_monthly":
                dt = _parse_date_flexible(r["Date"])
                price = float(r["Price"].replace(",", ""))
                bars.append({"t": dt.isoformat(), "o": price, "h": price, "l": price, "c": price, "v": 0})
            elif fmt == "standard_ohlcv":
                dt = _parse_date_flexible(r["Date"] if "Date" in r else r["date"])
                o = float(r.get("Open") or r.get("open") or r.get("open_price") or "0")
                h = float(r.get("High") or r.get("high") or "0")
                l = float(r.get("Low") or r.get("low") or "0")
                c = float(r.get("Close") or r.get("close") or r.get("close_price") or "0")
                vol = float(r.get("Volume") or r.get("volume") or r.get("Vol") or "0")
                bars.append({"t": dt.isoformat(), "o": o, "h": h, "l": l, "c": c, "v": vol})
            else:
                # generic fallback: try to find close column
                dt = None
                for k in ("date", "Date", "timestamp", "Timestamp", "datetime", "time"):
                    if k in r:
                        try:
                            dt = _parse_date_flexible(r[k])
                            break
                        except: pass
                if not dt:
                    continue
                # find price
                price = None
                for k in ("Close", "close", "Price", "price", "close_price", "c"):
                    if k in r:
                        try:
                            price = float(str(r[k]).replace(",", ""))
                            break
                        except: pass
                if price is None:
                    continue
                bars.append({"t": dt.isoformat(), "o": price, "h": price, "l": price, "c": price, "v": 0})
        except Exception:
            continue
    # sort by time
    bars.sort(key=lambda b: b["t"])
    return bars

def load_csv_text(text: str) -> List[Dict[str, Any]]:
    text = _strip_bom(text)
    # handle Thai BOM utf-8-sig already stripped
    sio = io.StringIO(text)
    reader = csv.DictReader(sio)
    if reader.fieldnames is None:
        return []
    fmt = detect_format(reader.fieldnames)
    rows = list(reader)
    return normalize_to_bars(rows, fmt)

def load_csv_file(path: str | pathlib.Path) -> List[Dict[str, Any]]:
    p = pathlib.Path(path)
    # utf-8-sig handles BOM
    txt = p.read_text(encoding="utf-8-sig")
    return load_csv_text(txt)

def list_real_datasets(base_dir: str = "real-data") -> List[Dict[str, Any]]:
    base = pathlib.Path(base_dir)
    out = []
    if not base.exists():
        return out
    for f in sorted(base.glob("*.csv")):
        name = f.name
        prov = PROVENANCE.get(name, {})
        try:
            bars = load_csv_file(f)
            out.append({
                "file": name,
                "path": str(f),
                "bars": len(bars),
                "first": bars[0]["t"] if bars else None,
                "last": bars[-1]["t"] if bars else None,
                "provenance": prov,
                "status": "ok" if bars else "empty",
            })
        except Exception as e:
            out.append({"file": name, "path": str(f), "bars": 0, "error": str(e), "provenance": prov, "status": "error"})
    return out

def validate_bars(bars: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not bars:
        return {"valid": False, "reason": "empty", "bars": 0}
    bad = 0
    for b in bars:
        if not (b["l"] <= b["o"] <= b["h"] and b["l"] <= b["c"] <= b["h"] and b["h"] >= b["l"] and b["h"]>0):
            bad += 1
    return {"valid": bad == 0, "bars": len(bars), "invalid_ohlc": bad, "first": bars[0]["t"], "last": bars[-1]["t"]}

def realdata_spec() -> Dict[str, Any]:
    return {
        "version": VERSION,
        "assets": len(PROVENANCE),
        "formats": ["thai_ohlcv", "shiller_sp500", "gold_monthly", "standard_ohlcv"],
        "provenance_tracked": True,
        "warning": "Historical data only. Past bars do not predict future bars.",
    }
