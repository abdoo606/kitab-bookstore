"""SQLite market/research database for TradeAtlas v15.

The database stores market bars the user lawfully imports, transparent
halal-screen evidence, pooled hidden-future research results, and — new in
v15 — the **failure memory**: every diagnosed failure, the avoid-rule it
produced and whether its remedy worked. It does not store broker
credentials, payment instruments, deposits or orders.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import sqlite3
import threading
from pathlib import Path

import marketlab as ml

DB_VERSION = 2
TIMEFRAME_LABELS = tuple(ml.TIMEFRAMES) + ("1mo", "source")


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _iso_time(timestamp: int | None) -> str | None:
    if timestamp is None:
        return None
    return dt.datetime.fromtimestamp(int(timestamp), tz=dt.timezone.utc).isoformat().replace("+00:00", "Z")


class MarketDatabase:
    """Small, local, inspectable SQLite database (Python standard library)."""

    def __init__(self, path: str | os.PathLike = "tradeatlas.db"):
        self.path = str(path)
        self.lock = threading.RLock()
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        with self.lock, self.conn:
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self.conn.execute("PRAGMA foreign_keys=ON")
            self._create_schema()

    def _create_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS instruments (
                symbol TEXT PRIMARY KEY,
                name TEXT DEFAULT '',
                asset_type TEXT DEFAULT 'unknown',
                exchange TEXT DEFAULT '',
                currency TEXT DEFAULT '',
                country TEXT DEFAULT '',
                sector TEXT DEFAULT '',
                source TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bars (
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                t INTEGER NOT NULL,
                o REAL NOT NULL,
                h REAL NOT NULL,
                l REAL NOT NULL,
                c REAL NOT NULL,
                v REAL NOT NULL DEFAULT 0,
                source TEXT DEFAULT '',
                imported_at TEXT NOT NULL,
                PRIMARY KEY(symbol, timeframe, t)
            );
            CREATE INDEX IF NOT EXISTS idx_bars_symbol_tf_t ON bars(symbol, timeframe, t);
            CREATE INDEX IF NOT EXISTS idx_bars_t ON bars(t);
            CREATE TABLE IF NOT EXISTS data_imports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                source TEXT DEFAULT '',
                bars_count INTEGER NOT NULL,
                first_t INTEGER,
                last_t INTEGER,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS halal_profiles (
                symbol TEXT PRIMARY KEY,
                asset_type TEXT NOT NULL,
                status TEXT NOT NULL,
                preset TEXT NOT NULL,
                profile_json TEXT NOT NULL,
                screen_json TEXT NOT NULL,
                source_note TEXT DEFAULT '',
                financials_as_of TEXT DEFAULT '',
                review_expires_at TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS halal_screen_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                asset_type TEXT NOT NULL,
                status TEXT NOT NULL,
                preset TEXT NOT NULL,
                profile_json TEXT NOT NULL,
                screen_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS research_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                params_json TEXT NOT NULL,
                summary_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS method_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                horizon_bars INTEGER NOT NULL,
                method TEXT NOT NULL,
                attempts INTEGER NOT NULL,
                accuracy_pct REAL,
                mean_net_10bps REAL,
                mean_net_25bps REAL,
                is_best_on_series INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(run_id) REFERENCES research_runs(id)
            );
            CREATE INDEX IF NOT EXISTS idx_scores_run_method ON method_scores(run_id, method);
            CREATE TABLE IF NOT EXISTS self_correction_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT NOT NULL,
                symbol_key TEXT NOT NULL,
                verdict TEXT NOT NULL,
                candidates INTEGER NOT NULL,
                rounds INTEGER NOT NULL,
                summary_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS research_trials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                round_no INTEGER NOT NULL,
                name TEXT NOT NULL,
                causes_json TEXT NOT NULL,
                retired_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(run_id) REFERENCES self_correction_runs(run_id)
            );
            CREATE INDEX IF NOT EXISTS idx_trials_run ON research_trials(run_id, round_no);
            CREATE TABLE IF NOT EXISTS research_lessons (
                lesson_uid TEXT NOT NULL,
                symbol_key TEXT NOT NULL,
                method TEXT NOT NULL,
                horizon_bars INTEGER NOT NULL,
                cause TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                evidence TEXT DEFAULT '',
                avoid TEXT DEFAULT '',
                remedy TEXT DEFAULT '',
                patch_json TEXT NOT NULL DEFAULT '{}',
                round_seen INTEGER NOT NULL DEFAULT 0,
                resolved_in_round INTEGER,
                run_id INTEGER,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(lesson_uid, symbol_key)
            );
            CREATE INDEX IF NOT EXISTS idx_lessons_symbol ON research_lessons(symbol_key, status);
            CREATE INDEX IF NOT EXISTS idx_lessons_cause ON research_lessons(cause);
            CREATE TABLE IF NOT EXISTS bot_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                symbol TEXT DEFAULT '',
                action TEXT DEFAULT '',
                latest_bar_time TEXT DEFAULT '',
                decision_json TEXT NOT NULL
            );
            """
        )
        self.conn.execute(
            "INSERT INTO meta(key,value) VALUES('db_version',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (str(DB_VERSION),),
        )

    def close(self) -> None:
        with self.lock:
            self.conn.close()

    def _symbol(self, value) -> str:
        return ml._paper_symbol(value)

    def upsert_instrument(self, data: dict) -> dict:
        if not isinstance(data, dict):
            raise ValueError("instrument must be an object")
        symbol = self._symbol(data.get("symbol"))
        row = {
            "symbol": symbol,
            "name": str(data.get("name") or data.get("company_name") or "")[:180],
            "asset_type": str(data.get("asset_type") or "unknown").strip().lower()[:40],
            "exchange": str(data.get("exchange") or "")[:80],
            "currency": str(data.get("currency") or "")[:20].upper(),
            "country": str(data.get("country") or "")[:80],
            "sector": str(data.get("sector") or "")[:120],
            "source": str(data.get("source") or data.get("source_note") or "")[:300],
            "updated_at": _now(),
        }
        with self.lock, self.conn:
            self.conn.execute(
                """
                INSERT INTO instruments(symbol,name,asset_type,exchange,currency,country,sector,source,updated_at)
                VALUES(:symbol,:name,:asset_type,:exchange,:currency,:country,:sector,:source,:updated_at)
                ON CONFLICT(symbol) DO UPDATE SET
                    name=excluded.name, asset_type=excluded.asset_type, exchange=excluded.exchange,
                    currency=excluded.currency, country=excluded.country, sector=excluded.sector,
                    source=excluded.source, updated_at=excluded.updated_at
                """,
                row,
            )
        return row

    def import_bars(self, *, symbol: str, timeframe: str, bars, source: str = "",
                    instrument: dict | None = None) -> dict:
        symbol = self._symbol(symbol)
        timeframe = str(timeframe or "source")
        if timeframe not in TIMEFRAME_LABELS:
            raise ValueError(f"unsupported database timeframe '{timeframe}'")
        if isinstance(bars, dict) and "csv" in bars:
            clean = ml.parse_csv(str(bars["csv"]))
        elif isinstance(bars, dict) and "csv_text" in bars:
            clean = ml.parse_csv(str(bars["csv_text"]))
        elif isinstance(bars, dict) and "bars" in bars:
            clean = ml.normalize_bars(bars["bars"])
        elif isinstance(bars, str):
            clean = ml.parse_csv(bars)
        else:
            clean = ml.normalize_bars(bars)
        if instrument:
            payload = dict(instrument)
            payload.setdefault("symbol", symbol)
            self.upsert_instrument(payload)
        else:
            self.upsert_instrument({"symbol": symbol, "source": source})
        now = _now()
        rows = [
            (symbol, timeframe, int(bar["t"]), float(bar["o"]), float(bar["h"]),
             float(bar["l"]), float(bar["c"]), float(bar.get("v") or 0.0), str(source or "")[:300], now)
            for bar in clean
        ]
        with self.lock, self.conn:
            self.conn.executemany(
                """
                INSERT INTO bars(symbol,timeframe,t,o,h,l,c,v,source,imported_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol,timeframe,t) DO UPDATE SET
                    o=excluded.o,h=excluded.h,l=excluded.l,c=excluded.c,v=excluded.v,
                    source=excluded.source,imported_at=excluded.imported_at
                """,
                rows,
            )
            first_t = int(clean[0]["t"]) if clean else None
            last_t = int(clean[-1]["t"]) if clean else None
            cursor = self.conn.execute(
                "INSERT INTO data_imports(symbol,timeframe,source,bars_count,first_t,last_t,created_at) VALUES(?,?,?,?,?,?,?)",
                (symbol, timeframe, str(source or "")[:300], len(rows), first_t, last_t, now),
            )
            import_id = int(cursor.lastrowid)
        return {
            "import_id": import_id, "symbol": symbol, "timeframe": timeframe,
            "bars_imported_or_updated": len(rows),
            "first_bar_time": _iso_time(first_t), "last_bar_time": _iso_time(last_t),
            "source": str(source or "")[:300],
        }

    def get_bars(self, symbol: str, timeframe: str, *, limit: int | None = None) -> list[dict]:
        symbol = self._symbol(symbol)
        timeframe = str(timeframe or "source")
        query = "SELECT t,o,h,l,c,v FROM bars WHERE symbol=? AND timeframe=? ORDER BY t DESC"
        params: tuple = (symbol, timeframe)
        if limit is not None:
            query += " LIMIT ?"
            params += (max(1, min(100_000, int(limit))),)
        with self.lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in reversed(rows)]

    def list_series(self) -> list[dict]:
        with self.lock:
            rows = self.conn.execute(
                """
                SELECT b.symbol,b.timeframe,COUNT(*) AS bars,MIN(b.t) AS first_t,MAX(b.t) AS last_t,
                       i.name,i.asset_type,i.exchange,i.currency,i.country,i.sector,i.source
                FROM bars b LEFT JOIN instruments i ON i.symbol=b.symbol
                GROUP BY b.symbol,b.timeframe ORDER BY b.symbol,b.timeframe
                """
            ).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["first_bar_time"] = _iso_time(item.pop("first_t"))
            item["last_bar_time"] = _iso_time(item.pop("last_t"))
            out.append(item)
        return out

    def stats(self) -> dict:
        with self.lock:
            counts = {}
            for table in ("instruments", "bars", "data_imports", "halal_profiles",
                          "halal_screen_history", "research_runs", "method_scores", "bot_events",
                          "self_correction_runs", "research_trials", "research_lessons"):
                counts[table] = int(self.conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            by_asset = [dict(r) for r in self.conn.execute(
                "SELECT asset_type,COUNT(*) AS instruments FROM instruments GROUP BY asset_type ORDER BY asset_type")]
            by_timeframe = [dict(r) for r in self.conn.execute(
                "SELECT timeframe,COUNT(*) AS bars,COUNT(DISTINCT symbol) AS symbols FROM bars GROUP BY timeframe ORDER BY timeframe")]
            halal = [dict(r) for r in self.conn.execute(
                "SELECT status,COUNT(*) AS profiles FROM halal_profiles GROUP BY status ORDER BY status")]
            lesson_status = [dict(r) for r in self.conn.execute(
                "SELECT status,COUNT(*) AS lessons FROM research_lessons GROUP BY status ORDER BY status")]
            page_count = int(self.conn.execute("PRAGMA page_count").fetchone()[0])
            page_size = int(self.conn.execute("PRAGMA page_size").fetchone()[0])
        file_bytes = 0
        if self.path != ":memory:" and os.path.exists(self.path):
            file_bytes = os.path.getsize(self.path)
        return {
            "database": "SQLite (local file)",
            "db_version": DB_VERSION,
            "path": self.path,
            "file_bytes": file_bytes,
            "logical_bytes": page_count * page_size,
            "counts": counts,
            "by_asset_type": by_asset,
            "by_timeframe": by_timeframe,
            "halal_by_status": halal,
            "failure_memory": {
                "lessons": counts.get("research_lessons", 0),
                "runs": counts.get("self_correction_runs", 0),
                "trials": counts.get("research_trials", 0),
                "by_status": lesson_status,
                "top_causes": self.lesson_tally()[:8],
            },
            "series": self.list_series(),
            "contains_broker_credentials": False,
            "contains_payment_instruments": False,
            "warning": "Stored accuracy is historical research on imported samples, not future performance.",
        }

    def save_halal_profile(self, profile: dict, *, preset: str = "strict") -> dict:
        result = ml.screen_halal_asset(profile, preset=preset)
        normalized = result["profile"]
        self.upsert_instrument({
            "symbol": result["symbol"], "name": normalized.get("company_name") or "",
            "asset_type": normalized.get("asset_type") or "unknown",
            "sector": normalized.get("sector") or "",
            "source": normalized.get("source_note") or "",
        })
        now = _now()
        profile_json = json.dumps(normalized, ensure_ascii=False)
        screen_json = json.dumps(result, ensure_ascii=False)
        with self.lock, self.conn:
            self.conn.execute(
                """
                INSERT INTO halal_profiles(symbol,asset_type,status,preset,profile_json,screen_json,source_note,financials_as_of,review_expires_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(symbol) DO UPDATE SET asset_type=excluded.asset_type,status=excluded.status,
                    preset=excluded.preset,profile_json=excluded.profile_json,screen_json=excluded.screen_json,
                    source_note=excluded.source_note,financials_as_of=excluded.financials_as_of,
                    review_expires_at=excluded.review_expires_at,updated_at=excluded.updated_at
                """,
                (result["symbol"], normalized.get("asset_type") or "", result["status"], preset,
                 profile_json, screen_json, normalized.get("source_note") or "",
                 normalized.get("financials_as_of") or "", normalized.get("review_expires_at") or "", now),
            )
            self.conn.execute(
                "INSERT INTO halal_screen_history(symbol,asset_type,status,preset,profile_json,screen_json,created_at) VALUES(?,?,?,?,?,?,?)",
                (result["symbol"], normalized.get("asset_type") or "", result["status"], preset,
                 profile_json, screen_json, now),
            )
        return result

    def list_halal_profiles(self, *, status: str | None = None) -> list[dict]:
        query = "SELECT symbol,asset_type,status,preset,profile_json,screen_json,updated_at FROM halal_profiles"
        params: tuple = ()
        if status:
            query += " WHERE status=?"
            params = (str(status),)
        query += " ORDER BY symbol"
        with self.lock:
            rows = self.conn.execute(query, params).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["profile"] = json.loads(item.pop("profile_json"))
            item["screen"] = json.loads(item.pop("screen_json"))
            out.append(item)
        return out

    def seed_bundled_data(self, root: str | os.PathLike) -> dict:
        base = Path(root) / "real-data"
        files = [
            ("AAPL", "Apple Inc. (bundled historical sample)", "stock", "NASDAQ", "USD", "United States",
             "1d", "aapl-daily-2015-2017.plotly.csv", "Public Plotly datasets sample; see REAL-DATA-NOTICE.md"),
            ("MSFT", "Microsoft (bundled monthly sample)", "stock", "NASDAQ", "USD", "United States",
             "1mo", "vega-msft-monthly-2000-2010.csv", "Public Vega datasets monthly close-only sample; see REAL-DATA-NOTICE.md"),
            ("AAPL", "Apple Inc. (bundled monthly sample)", "stock", "NASDAQ", "USD", "United States",
             "1mo", "vega-aapl-monthly-2000-2010.csv", "Public Vega datasets monthly close-only sample; see REAL-DATA-NOTICE.md"),
            ("AMZN", "Amazon (bundled monthly sample)", "stock", "NASDAQ", "USD", "United States",
             "1mo", "vega-amzn-monthly-2000-2010.csv", "Public Vega datasets monthly close-only sample; see REAL-DATA-NOTICE.md"),
            ("GOOG", "Google/Alphabet (bundled monthly sample)", "stock", "NASDAQ", "USD", "United States",
             "1mo", "vega-goog-monthly-2000-2010.csv", "Public Vega datasets monthly close-only sample; see REAL-DATA-NOTICE.md"),
            ("IBM", "IBM (bundled monthly sample)", "stock", "NYSE", "USD", "United States",
             "1mo", "vega-ibm-monthly-2000-2010.csv", "Public Vega datasets monthly close-only sample; see REAL-DATA-NOTICE.md"),
        ]
        imports = []
        for symbol, name, asset_type, exchange, currency, country, timeframe, filename, source in files:
            path = base / filename
            if not path.exists():
                continue
            bars = ml.parse_csv(path.read_text(encoding="utf-8"))
            imports.append(self.import_bars(
                symbol=symbol, timeframe=timeframe, bars=bars, source=source,
                instrument={"symbol": symbol, "name": name, "asset_type": asset_type,
                            "exchange": exchange, "currency": currency, "country": country,
                            "source": source}))
        return {"seeded": imports, "stats": self.stats()}

    def record_bot_decisions(self, decisions: list[dict]) -> int:
        now = _now()
        rows = [
            (now, str(d.get("symbol") or ""), str(d.get("action") or ""),
             str(d.get("latest_bar_time") or ""), json.dumps(d, ensure_ascii=False))
            for d in decisions or []
        ]
        if rows:
            with self.lock, self.conn:
                self.conn.executemany(
                    "INSERT INTO bot_events(created_at,symbol,action,latest_bar_time,decision_json) VALUES(?,?,?,?,?)",
                    rows)
        return len(rows)

    def research_all(self, *, attempts: int = 100, top_n: int = 30) -> dict:
        attempts = max(10, min(1000, int(attempts)))
        created = _now()
        params = {"tradeatlas_version": "14.0", "attempts_requested": attempts, "top_n": int(top_n),
                  "rule": "hidden-future ensemble per stored series; monthly series use horizon 3/min_history 60 and at most 40 attempts; 1m/5m/15m series use min_history 240 and also store v14 minute-method rows at horizon 5",
                  "accuracy_target_pct": 80.0, "accuracy_goal_established": False}
        with self.lock, self.conn:
            cursor = self.conn.execute(
                "INSERT INTO research_runs(created_at,params_json,summary_json) VALUES(?,?,?)",
                (created, json.dumps(params), "{}"))
            run_id = int(cursor.lastrowid)
        series_results = []
        score_rows = []
        for series in self.list_series():
            symbol, timeframe = series["symbol"], series["timeframe"]
            bars = self.get_bars(symbol, timeframe)
            if len(bars) < 100:
                series_results.append({"symbol": symbol, "timeframe": timeframe,
                                       "error": "needs at least 100 bars", "bars": len(bars)})
                continue
            horizon = 3 if timeframe == "1mo" else 5
            is_minute = timeframe in {"1m", "5m", "15m"}
            min_history = 240 if is_minute else 200 if len(bars) >= 300 else 60
            use_attempts = attempts if len(bars) >= 300 else min(attempts, 40)
            result = ml.ensemble_forecast_eval(
                bars, attempts=use_attempts, horizon=horizon, top_n=int(top_n),
                min_history=min_history)
            if "error" in result:
                series_results.append({"symbol": symbol, "timeframe": timeframe,
                                       "bars": len(bars), "error": result["error"]})
                continue
            accuracy = result.get("direction_accuracy_pct") or {}
            attempts_by_method = result.get("method_attempts") or {}
            costs = {int(row.get("round_trip_cost_bps") or 0): row for row in result.get("cost_analysis") or []}
            best = result.get("best_method_on_this_sample")
            for method, acc in accuracy.items():
                made = int(attempts_by_method.get(method) or 0)
                if method in {"agreement_only", "consensus_3plus"}:
                    made = int(result.get("agreement_attempts") if method == "agreement_only"
                               else result.get("consensus_3plus_attempts") or 0)
                if made <= 0:
                    continue
                c10 = (costs.get(10) or {}).get(method) or {}
                c25 = (costs.get(25) or {}).get(method) or {}
                score_rows.append((
                    run_id, symbol, timeframe, int(horizon), method, made,
                    float(acc) if acc is not None else None,
                    c10.get("mean_net_pct_per_trade"), c25.get("mean_net_pct_per_trade"),
                    1 if method == best else 0))
            minute_summary = None
            if is_minute:
                minute_result = ml.minute_forecast_eval(
                    bars, attempts=min(use_attempts, 1000), horizons=(horizon,),
                    min_history=min_history)
                minute_row = next((r for r in minute_result.get("horizons") or []
                                   if r.get("horizon_bars") == horizon and "methods" in r), None)
                if minute_row:
                    minute_methods = {}
                    for method, row in (minute_row.get("methods") or {}).items():
                        if not (method.startswith("minute_") or method.startswith("atlas_minute_pulse")
                                or method == "momentum_1bar"):
                            continue
                        made = int(row.get("attempts_made") or 0)
                        if made <= 0:
                            continue
                        minute_methods[method] = row
                        score_rows.append((
                            run_id, symbol, timeframe, int(horizon), method, made,
                            row.get("direction_accuracy_pct"),
                            row.get("mean_net_pct_per_trade_10bps"),
                            row.get("mean_net_pct_per_trade_25bps"), 0))
                    minute_summary = {
                        "methods": minute_methods,
                        "goal_80_assessment": minute_result.get("goal_80_assessment"),
                    }
            series_results.append({
                "symbol": symbol, "timeframe": timeframe, "bars": len(bars),
                "attempts_made": result.get("attempts_made"), "horizon_bars": horizon,
                "best_method_on_this_sample": best,
                "selected_accuracy_pct": {k: accuracy.get(k) for k in (
                    "analog_median", "momentum_5bar", "multiscale_trend", "kalman_trend",
                    "omni_direct_consensus", "hull_trend", "atlas_fusion_v12", "ultimate_trend",
                    "atlas_pressure_wave", "atlas_regime_compass", "atlas_phoenix_fusion",
                    "majority_vote_v8", "atlas_meta_hedge", "atlas_online_logistic", "adaptive_selector")},
                "minute_research": minute_summary,
            })
        with self.lock, self.conn:
            self.conn.executemany(
                """
                INSERT INTO method_scores(run_id,symbol,timeframe,horizon_bars,method,attempts,accuracy_pct,mean_net_10bps,mean_net_25bps,is_best_on_series)
                VALUES(?,?,?,?,?,?,?,?,?,?)
                """, score_rows)
        leaderboard = self.leaderboard(run_id=run_id, limit=100)
        summary = {
            "run_id": run_id, "created_at": created, "params": params,
            "series": series_results, "leaderboard": leaderboard,
            "warning": "Pooled historical samples are correlated and can be survivor-biased. The leaderboard is not a forecast of future accuracy and cannot manufacture an 80% universal rate. Minute rows additionally omit live spread/order-book/latency effects.",
        }
        with self.lock, self.conn:
            self.conn.execute("UPDATE research_runs SET summary_json=? WHERE id=?",
                              (json.dumps(summary, ensure_ascii=False), run_id))
        return summary

    def leaderboard(self, *, run_id: int | None = None, limit: int = 30) -> list[dict]:
        with self.lock:
            if run_id is None:
                row = self.conn.execute("SELECT MAX(id) AS id FROM research_runs").fetchone()
                run_id = int(row["id"]) if row and row["id"] is not None else None
            if run_id is None:
                return []
            rows = self.conn.execute(
                """
                SELECT method,SUM(attempts) AS attempts,
                       SUM(COALESCE(accuracy_pct,0)*attempts)/NULLIF(SUM(CASE WHEN accuracy_pct IS NOT NULL THEN attempts ELSE 0 END),0) AS weighted_accuracy_pct,
                       SUM(COALESCE(mean_net_10bps,0)*attempts)/NULLIF(SUM(attempts),0) AS weighted_mean_net_10bps,
                       SUM(COALESCE(mean_net_25bps,0)*attempts)/NULLIF(SUM(attempts),0) AS weighted_mean_net_25bps,
                       SUM(is_best_on_series) AS series_wins,COUNT(DISTINCT symbol || '|' || timeframe) AS series_count
                FROM method_scores WHERE run_id=? GROUP BY method
                ORDER BY weighted_accuracy_pct DESC, weighted_mean_net_10bps DESC LIMIT ?
                """, (int(run_id), max(1, min(100, int(limit))))).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["run_id"] = int(run_id)
            for key in ("weighted_accuracy_pct", "weighted_mean_net_10bps", "weighted_mean_net_25bps"):
                item[key] = None if item.get(key) is None else round(float(item[key]), 3)
            out.append(item)
        return out

    # ---------------- v15 failure memory ----------------

    def save_self_correction(self, result: dict) -> dict:
        """Persist a self-correction run, its trials and its lesson ledger.

        Lessons are upserted on (lesson_uid, symbol_key) so the same failure
        keeps one stable identity across runs; a later run that fixes it can
        upgrade the row to ``resolved`` instead of creating a duplicate.
        """
        if not isinstance(result, dict) or result.get("mode") != "failure_driven_self_correction":
            raise ValueError("not a self-correction result")
        symbol = str(result.get("symbol") or "series")
        summary = {
            "verdict": result.get("verdict"),
            "failure_tally": result.get("failure_tally") or [],
            "retired_candidates": result.get("retired_candidates") or [],
            "validated_candidates": result.get("validated_candidates") or [],
            "single_symbol_survivors": result.get("single_symbol_survivors") or [],
            "goal_80": result.get("goal_80") or {},
            "next_actions": result.get("next_actions") or [],
            "sources": result.get("sources") or [],
            "provenance": result.get("provenance"),
            "source_label": result.get("source_label"),
            "warning": result.get("warning") or "",
        }
        created = _now()
        with self.lock, self.conn:
            cursor = self.conn.execute(
                """INSERT INTO self_correction_runs
                   (created_at,symbol,symbol_key,verdict,candidates,rounds,summary_json)
                   VALUES(?,?,?,?,?,?,?)""",
                (created, symbol, symbol, str(result.get("verdict") or ""),
                 int(result.get("candidates_tested") or 0), len(result.get("rounds") or []),
                 json.dumps(summary, ensure_ascii=False)),
            )
            run_id = int(cursor.lastrowid)
            for record in result.get("rounds") or []:
                self.conn.execute(
                    """INSERT INTO research_trials
                       (run_id,round_no,name,causes_json,retired_json,created_at)
                       VALUES(?,?,?,?,?,?)""",
                    (run_id, int(record.get("round") or 0), str(record.get("name") or ""),
                     json.dumps(record.get("causes_tally") or {}, ensure_ascii=False),
                     json.dumps(record.get("retired") or [], ensure_ascii=False), created),
                )
            saved = 0
            for lesson in result.get("lessons") or []:
                self._upsert_lesson(lesson, symbol_key=symbol, run_id=run_id, created=created)
                saved += 1
        return {"run_id": run_id, "symbol": symbol, "lessons_saved": saved,
                "trials_saved": len(result.get("rounds") or []),
                "verdict": result.get("verdict")}

    def _upsert_lesson(self, lesson: dict, *, symbol_key: str, run_id: int | None,
                       created: str) -> None:
        self.conn.execute(
            """INSERT INTO research_lessons
               (lesson_uid,symbol_key,method,horizon_bars,cause,severity,status,evidence,
                avoid,remedy,patch_json,round_seen,resolved_in_round,run_id,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(lesson_uid,symbol_key) DO UPDATE SET
                 status=excluded.status,
                 evidence=excluded.evidence,
                 patch_json=excluded.patch_json,
                 round_seen=MIN(research_lessons.round_seen, excluded.round_seen),
                 resolved_in_round=COALESCE(excluded.resolved_in_round,
                                            research_lessons.resolved_in_round),
                 run_id=excluded.run_id,
                 updated_at=excluded.updated_at""",
            (str(lesson.get("lesson_uid") or ""), symbol_key, str(lesson.get("method") or ""),
             int(lesson.get("horizon_bars") or 0), str(lesson.get("cause") or ""),
             str(lesson.get("severity") or ""), str(lesson.get("status") or "observed"),
             str(lesson.get("evidence") or ""), str(lesson.get("avoid") or ""),
             str(lesson.get("remedy") or ""),
             json.dumps(lesson.get("patch") or {}, ensure_ascii=False),
             int(lesson.get("round_seen") or 0), lesson.get("resolved_in_round"),
             run_id, created),
        )

    def self_correction_lessons(self, *, symbol: str | None = None,
                                status: str | None = None, limit: int = 200) -> list[dict]:
        query = ("SELECT lesson_uid,symbol_key,method,horizon_bars,cause,severity,status,"
                 "evidence,avoid,remedy,patch_json,round_seen,resolved_in_round,run_id,updated_at "
                 "FROM research_lessons")
        clauses, params = [], []
        if symbol:
            clauses.append("symbol_key=?")
            params.append(str(symbol))
        if status:
            clauses.append("status=?")
            params.append(str(status))
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC, cause LIMIT ?"
        params.append(max(1, min(2000, int(limit))))
        with self.lock:
            rows = self.conn.execute(query, params).fetchall()
        out = []
        for row in rows:
            item = dict(row)
            item["patch"] = json.loads(item.pop("patch_json") or "{}")
            out.append(item)
        return out

    def lesson_tally(self, *, symbol: str | None = None) -> list[dict]:
        query = ("SELECT cause,severity,COUNT(*) AS lessons,"
                 "SUM(CASE WHEN status='resolved' THEN 1 ELSE 0 END) AS resolved,"
                 "SUM(CASE WHEN status IN ('recurred','escalated') THEN 1 ELSE 0 END) AS recurred,"
                 "SUM(CASE WHEN status='retired' THEN 1 ELSE 0 END) AS retired "
                 "FROM research_lessons")
        params: list = []
        if symbol:
            query += " WHERE symbol_key=?"
            params.append(str(symbol))
        query += " GROUP BY cause,severity ORDER BY lessons DESC, cause"
        with self.lock:
            rows = self.conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def latest_self_correction(self) -> dict | None:
        with self.lock:
            row = self.conn.execute(
                "SELECT run_id,created_at,symbol,verdict,candidates,rounds,summary_json "
                "FROM self_correction_runs ORDER BY run_id DESC LIMIT 1").fetchone()
        if not row:
            return None
        return {"run_id": int(row["run_id"]), "created_at": row["created_at"],
                "symbol": row["symbol"], "verdict": row["verdict"],
                "candidates": int(row["candidates"] or 0), "rounds": int(row["rounds"] or 0),
                "summary": json.loads(row["summary_json"])}

    def clear_lessons(self, *, symbol: str | None = None) -> dict:
        """Forget lessons. Only meaningful after genuinely new data or methods."""
        with self.lock, self.conn:
            if symbol:
                cursor = self.conn.execute("DELETE FROM research_lessons WHERE symbol_key=?", (str(symbol),))
            else:
                cursor = self.conn.execute("DELETE FROM research_lessons")
        return {"cleared": int(cursor.rowcount or 0), "symbol": symbol}

    def lessons_for_carry_over(self, symbol: str) -> list[dict]:
        """Only the lesson states that must change the next test on this symbol."""
        return self.self_correction_lessons(symbol=symbol, limit=2000)

    def latest_research(self) -> dict | None:
        with self.lock:
            row = self.conn.execute(
                "SELECT id,created_at,params_json,summary_json FROM research_runs ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return None
        return {"run_id": int(row["id"]), "created_at": row["created_at"],
                "params": json.loads(row["params_json"]), "summary": json.loads(row["summary_json"])}
