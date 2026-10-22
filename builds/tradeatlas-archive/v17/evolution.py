"""
TradeAtlas v17 — Evolution Tracker
Tracks how the research process evolves across generations:
- Generation-by-generation improvement
- Failure resolution rate
- Remedy reuse effectiveness
- Predictive avoidance
"""

from __future__ import annotations

import hashlib
import json
import math
import time

VERSION = "17.0"

GENERATION_KINDS = ("screen", "remedy", "validation", "auto_research", "holdout")

def generation_id(symbol: str, round_no: int, cause: str = "") -> str:
    raw = f"{VERSION}|{symbol}|{round_no}|{cause}|{time.time_ns()}".encode()
    return "gen-" + hashlib.sha1(raw).hexdigest()[:12]

def compute_evolution_metrics(history: list[dict]) -> dict:
    """
    history: list of run results (each from run_self_correction or pooled evidence)
    Returns evolution across runs.
    """
    if not history:
        return {
            "generations": 0,
            "total_lessons": 0,
            "resolved_rate": 0.0,
            "retirement_rate": 0.0,
            "avoidance_efficiency": 0.0,
            "accuracy_trend": [],
            "coverage_trend": [],
            "net_trend": [],
            "lesson_reuse_count": 0,
        }

    total_lessons = sum(len(h.get("lessons", [])) for h in history)
    resolved = sum(len([l for l in h.get("lessons", []) if l.get("status") == "resolved"]) for h in history)
    retired_candidates = sum(len(h.get("retired_candidates", [])) for h in history)

    # avoidance: how many prior lessons prevented retesting dead candidates
    prior_used = sum(len(h.get("prior_lessons_used", [])) for h in history)

    # trends
    accuracy_trend = []
    coverage_trend = []
    net_trend = []
    for h in history:
        # Try multiple sources for accuracy
        acc = None
        if "best_pooled_candidate" in h and h["best_pooled_candidate"]:
            acc = h["best_pooled_candidate"].get("accuracy_pct")
        elif "rounds" in h:
            for rnd in h["rounds"]:
                for cand in rnd.get("candidates", []):
                    if cand.get("direction_accuracy_pct") is not None:
                        acc = cand["direction_accuracy_pct"]
                        break
        if acc is not None:
            accuracy_trend.append(acc)

    total = len(history) if history else 1
    return {
        "generations": len(history),
        "total_lessons": total_lessons,
        "resolved_rate": round(resolved / max(1, total_lessons), 4) if total_lessons else 0.0,
        "retirement_rate": round(retired_candidates / max(1, total_lessons), 4) if total_lessons else 0.0,
        "avoidance_efficiency": round(prior_used / max(1, total), 4),
        "accuracy_trend": accuracy_trend[-10:],
        "coverage_trend": coverage_trend,
        "net_trend": net_trend,
        "lesson_reuse_count": prior_used,
        "improvement_signal": _improvement_signal(accuracy_trend),
        "is_learning": resolved > 0 or prior_used > 0,
        "verdict": _evolution_verdict(resolved, total_lessons, accuracy_trend),
    }

def _improvement_signal(trend: list[float]) -> str:
    if len(trend) < 2:
        return "insufficient_data"
    # Simple linear regression slope
    n = len(trend)
    x = list(range(n))
    mean_x = sum(x) / n
    mean_y = sum(trend) / n
    num = sum((x[i] - mean_x) * (trend[i] - mean_y) for i in range(n))
    den = sum((x[i] - mean_x) ** 2 for i in range(n))
    if den == 0:
        return "flat"
    slope = num / den
    if slope > 0.5:
        return "improving"
    if slope < -0.5:
        return "degrading"
    return "flat"

def _evolution_verdict(resolved: int, total: int, trend: list) -> str:
    if total == 0:
        return "no_history"
    if resolved / max(1, total) > 0.2:
        return "learning_effectively"
    if len(trend) >= 3 and all(trend[i] <= trend[i+1] for i in range(len(trend)-1)):
        return "steady_improvement"
    if resolved == 0 and total > 10:
        return "needs_new_approaches"
    return "early_learning"

def failure_cluster(lessons: list[dict]) -> dict:
    """
    Cluster lessons by cause family for heatmap.
    Returns tally grouped by severity and remedy_kind.
    """
    by_cause: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_remedy: dict[str, int] = {}
    by_status: dict[str, int] = {}

    for l in lessons:
        cause = l.get("cause", "unknown")
        by_cause[cause] = by_cause.get(cause, 0) + 1
        sev = l.get("severity", "unknown")
        by_severity[sev] = by_severity.get(sev, 0) + 1
        rk = l.get("remedy_kind", "unknown")
        by_remedy[rk] = by_remedy.get(rk, 0) + 1
        st = l.get("status", "unknown")
        by_status[st] = by_status.get(st, 0) + 1

    # Find dominant failure mode
    dominant = max(by_cause, key=lambda k: by_cause[k]) if by_cause else None

    return {
        "by_cause": dict(sorted(by_cause.items(), key=lambda x: -x[1])),
        "by_severity": by_severity,
        "by_remedy_kind": by_remedy,
        "by_status": by_status,
        "dominant_cause": dominant,
        "total": len(lessons),
        "unique_causes": len(by_cause),
        "diversity_index": round(len(by_cause) / max(1, len(lessons)), 3),
    }

def predict_failure_probability(candidate_key: tuple[str, int], prior_lessons: list[dict]) -> dict:
    """
    Before testing a candidate, predict failure likelihood based on prior lessons.
    Returns probability and most likely cause.
    """
    method, horizon = candidate_key
    relevant = [l for l in prior_lessons if l.get("method") == method and l.get("horizon_bars") == horizon]
    # Also check method family
    family_relevant = [l for l in prior_lessons if l.get("method") == method]

    if not prior_lessons:
        return {"probability": 0.5, "confidence": 0.0, "predicted_cause": None, "reason": "no_history"}

    # Count retirements for this exact candidate
    exact_retired = [l for l in relevant if l.get("status") in ("retired", "recurred", "escalated")]
    if exact_retired:
        # This candidate was proven dead before
        return {
            "probability": 0.92,
            "confidence": 0.9,
            "predicted_cause": exact_retired[0].get("cause"),
            "reason": f"exact candidate retired before for {exact_retired[0].get('cause')}",
            "should_skip": True,
        }

    if family_relevant:
        # Check if method family has high failure rate
        retired_family = [l for l in family_relevant if l.get("status") in ("retired", "recurred", "escalated")]
        rate = len(retired_family) / max(1, len(family_relevant))
        if rate > 0.6:
            return {
                "probability": 0.7 + rate * 0.2,
                "confidence": rate,
                "predicted_cause": retired_family[0].get("cause") if retired_family else None,
                "reason": f"method family has {rate:.0%} retirement rate",
                "should_skip": False,
            }

    # General base rate
    total_retired = len([l for l in prior_lessons if l.get("status") in ("retired", "recurred", "escalated")])
    base_rate = total_retired / max(1, len(prior_lessons))
    return {
        "probability": 0.3 + base_rate * 0.4,
        "confidence": 0.3,
        "predicted_cause": None,
        "reason": f"base retirement rate {base_rate:.0%}",
        "should_skip": False,
    }

def evolution_spec() -> dict:
    return {
        "name": "Atlas Evolution Tracker",
        "version": VERSION,
        "tracks": [
            "generation_over_generation_accuracy",
            "failure_resolution_rate",
            "remedy_reuse_and_avoidance",
            "predictive_failure_scoring",
            "cluster_heatmaps",
        ],
        "honesty": "Evolution tracks the research process, not market predictability. Higher resolved_rate means the process learns faster, not that the market is beaten.",
        "goal_established": False,
    }

def remedy_effectiveness(lessons: list[dict], history: list[dict]) -> dict:
    """
    For each remedy_kind, how often did it resolve vs recur?
    """
    by_kind: dict[str, dict] = {}
    for l in lessons:
        kind = l.get("remedy_kind", "unknown")
        slot = by_kind.setdefault(kind, {"total": 0, "resolved": 0, "recurred": 0, "retired": 0, "escalated": 0})
        slot["total"] += 1
        status = l.get("status")
        if status == "resolved":
            slot["resolved"] += 1
        elif status == "recurred":
            slot["recurred"] += 1
        elif status == "retired":
            slot["retired"] += 1
        elif status == "escalated":
            slot["escalated"] += 1

    for kind, slot in by_kind.items():
        slot["resolve_rate"] = round(slot["resolved"] / max(1, slot["total"]), 3)
        slot["failure_rate"] = round((slot["recurred"] + slot["retired"] + slot["escalated"]) / max(1, slot["total"]), 3)

    return {
        "by_remedy_kind": by_kind,
        "best_remedy": max(by_kind, key=lambda k: by_kind[k]["resolve_rate"]) if by_kind else None,
        "worst_remedy": max(by_kind, key=lambda k: by_kind[k]["failure_rate"]) if by_kind else None,
    }
