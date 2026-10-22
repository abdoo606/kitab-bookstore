"""
TradeAtlas v17 — Deep Diagnostics
Explains WHY a candidate failed in human-readable form,
quantifies remedy confidence, and predicts next-test success.
"""

from __future__ import annotations

import math
import statistics

VERSION = "17.0"

EXPLANATIONS = {
    "no_evaluable_origins": "السلسلة قصيرة جداً - لا يوجد تاريخ كافٍ لوضع أي نقطة اختبار. الحل: استيراد تاريخ أطول قانونياً.",
    "short_history": "عدد الأعمدة لا يدعم الميزان والاحتمالات. لا تقلل الاحتساب لتبدو السلسلة قابلة للتقييم.",
    "all_scores_abstained": "الطريقة لم تتحدث أبداً - كل النتيجة صفر/غائبة. إما العتبة عالية جداً أو الطريقة لا تناسب هذا الأصل.",
    "insufficient_attempts": "عدد المحاولات قليل جداً للحكم. العينات الصغيرة تتأرجح بالصدفة وحدها.",
    "coverage_too_low": "معدل عالٍ على شريحة صغيرة جداً ليس استراتيجية. يجب نشر الدقة بجانب التغطية دائماً.",
    "cost_eaten_edge": "الحافة الإجمالية اختفت بعد التكاليف. لا تقتبس أبداً الدقة الإجمالية كقابلة للتداول.",
    "cost_filter_starved_sample": "مرشح التكلفة أزال معظم العينة. علاج يُجوّع عينته ليس علاجاً.",
    "below_accuracy_target": "تحت هدف 80% للمشروع. المسافة صادقة وليست مقبضاً لضبطه.",
    "no_directional_edge": "الدقة عند أو تحت رمي العملة. لا تلبس رمي العملة بمؤشرات إضافية.",
    "baseline_not_beaten": "خط الأساس الساذج جيد على الأقل. إذا فازت العملة الثابتة/الزخم، الطريقة لا تضيف شيئاً هنا.",
    "negative_net_after_costs": "توقع سلبي بعد التكاليف. الطريقة ذات التوقع السلبي لا تصبح إيجابية بوصفها بشكل أفضل.",
    "overfit_single_horizon": "الحافة تعيش في خلية أفق واحدة فقط - توقيع كلاسيكي لانتقاء الكرز.",
    "walk_forward_degraded": "الشريحة اللاحقة أسوأ بكثير من السابقة. رقم واحد مجمّع يخفي التحلل.",
    "regime_dependence": "نظام واحد حمل النتيجة بينما خسر الآخر. لا تجمع الأنظمة بصمت.",
    "drawdown_too_deep": "مسار التراجع تجاوز الحد. الدقة بدون رقم تراجع هي نصف نتيجة.",
    "wide_confidence_interval": "فترة الثقة واسعة جداً لاستنتاج أي شيء. العينة لا تثبت لا الحافة ولا عدمها.",
    "single_symbol_only": "رمز واحد فقط تم توفيره - دراسة حالة، ليست قانوناً للسوق.",
    "selection_bias": "الفائز تم اختياره بين متسابقين كثيرين - الرقم مضخم بالاختيار.",
    "volume_missing": "طريقة تعتمد على الحجم على سلسلة بدون حجم. لا تخترع الحجم أبداً.",
    "cost_below_floor": "افتراض التكلفة تحت الحد الأدنى للبحث. اختبارات صفر التكلفة تلمّع كل فكرة عالية التردد.",
    "remedy_failed_twice": "العلاج طُبق وعاد السبب - دليل، ليس سوء حظ.",
    # v17 new causes
    "autocorrelation_trap": "ارتباط ذاتي متسلسل يخدع عدّ الاتجاه. الحركة التالية تبدو متوقعة لكنها ضوضاء بنية.",
    "volatility_regime_shift": "تغير نظام التذبذب كسر العتبة. ما كان حافة في تذبذب منخفض صار ضجيجاً في تذبذب عالٍ.",
    "liquidity_illusion": "فترات حجم منخفض تُحسب كحافة. السيولة الوهمية تختفي عند التنفيذ الحقيقي.",
    "overparameterized_signal": "الطريقة تملك معاملات كثيرة لحجم العينة. كل معامل إضافي يزيد خطر الحفظ عن ظهر قلب.",
    "multiple_testing_bias": "اختبار متعدد بدون تصحيح - p-hacking عبر مرشحين كثيرين. أفضل صف هو الأكثر تحيزاً.",
    "non_stationary_drift": "الانجراف تغير عبر الزمن. ما كان متوسطاً ثابتاً انزاح.",
    "microstructure_noise": "ضوضاء البنية الدقيقة (ارتداد العرض/الطلب) في أفق 1 يخفي الإشارة الحقيقية.",
    "asymmetric_payoff_trap": "معدل فوز عالٍ لكن توقع سلبي بسبب تفاوت الأرباح/الخسائر. الفوز كثيراً وخسارة أكثر ليس حافة.",
    "tail_risk_hidden": "مخاطر ذيلية مخفية - خسائر قصوى تختبئ في الذيل ولا تظهر في المتوسط.",
    "correlation_breakdown": "ارتباط الطرق انهار - التجميع يضاعف نفس الرهان بدل تنويعه.",
    "concept_drift": "انجراف المفهوم - قواعد السوق تغيرت عبر العينة الطويلة.",
    "horizon_mismatch": "عدم تطابق الأفق - الإشارة معايرة لأفق مختلف عن المُختبر.",
    "threshold_overfit": "العتبة مضبوطة لضوضاء العينة. العتبة المثلى في الماضي نادراً ما تكون مثلى في المستقبل.",
    "sample_contamination": "تلوث العينة - نوافذ متداخلة تسرب المستقبل إلى الماضي.",
}

REMEDY_CONFIDENCE = {
    "no_evaluable_origins": 0.0,
    "short_history": 0.1,
    "all_scores_abstained": 0.4,
    "insufficient_attempts": 0.7,
    "coverage_too_low": 0.6,
    "cost_eaten_edge": 0.65,
    "cost_filter_starved_sample": 0.5,
    "below_accuracy_target": 0.0,
    "no_directional_edge": 0.05,
    "baseline_not_beaten": 0.05,
    "negative_net_after_costs": 0.05,
    "overfit_single_horizon": 0.55,
    "walk_forward_degraded": 0.6,
    "regime_dependence": 0.6,
    "drawdown_too_deep": 0.5,
    "wide_confidence_interval": 0.7,
    "single_symbol_only": 0.8,
    "selection_bias": 0.75,
    "volume_missing": 0.0,
    "cost_below_floor": 0.85,
    "remedy_failed_twice": 0.0,
    "autocorrelation_trap": 0.5,
    "volatility_regime_shift": 0.55,
    "liquidity_illusion": 0.6,
    "overparameterized_signal": 0.4,
    "multiple_testing_bias": 0.75,
    "non_stationary_drift": 0.5,
    "microstructure_noise": 0.65,
    "asymmetric_payoff_trap": 0.6,
    "tail_risk_hidden": 0.5,
    "correlation_breakdown": 0.55,
    "concept_drift": 0.45,
    "horizon_mismatch": 0.6,
    "threshold_overfit": 0.6,
    "sample_contamination": 0.7,
}

def explain_failure(cause_id: str, evidence: str, evaluation: dict | None = None) -> dict:
    """Return deep explanation for a failure cause."""
    base = EXPLANATIONS.get(cause_id, "سبب غير موثق بعد - يحتاج تحليل يدوي.")
    confidence = REMEDY_CONFIDENCE.get(cause_id, 0.5)

    detail = {
        "cause": cause_id,
        "title_ar": _arabic_title(cause_id),
        "explanation_ar": base,
        "explanation_en": _english_explanation(cause_id),
        "evidence": evidence,
        "remedy_confidence": confidence,
        "is_fixable": confidence > 0.3,
        "is_fatal": confidence < 0.1,
        "next_test_avoid_rule": _avoid_rule(cause_id),
        "estimated_fix_success_pct": round(confidence * 100, 1),
    }

    if evaluation:
        # Add quantitative context
        acc = evaluation.get("direction_accuracy_pct")
        net = evaluation.get("mean_net_pct")
        dd = evaluation.get("max_drawdown_pct")
        cov = evaluation.get("coverage_pct")
        detail["quantitative_context"] = {
            "accuracy_pct": acc,
            "net_pct": net,
            "drawdown_pct": dd,
            "coverage_pct": cov,
            "attempts": evaluation.get("attempts_made"),
            "interpretation": _interpret_numbers(acc, net, dd, cov, cause_id),
        }

    return detail

def _arabic_title(cause_id: str) -> str:
    titles = {
        "no_evaluable_origins": "لا يوجد تاريخ قابل للتقييم",
        "short_history": "تاريخ قصير",
        "all_scores_abstained": "الطريقة صامتة تماماً",
        "insufficient_attempts": "محاولات غير كافية",
        "coverage_too_low": "تغطية منخفضة جداً",
        "cost_eaten_edge": "التكلفة أكلت الحافة",
        "cost_filter_starved_sample": "مرشح التكلفة جوّع العينة",
        "below_accuracy_target": "تحت هدف 80%",
        "no_directional_edge": "لا حافة اتجاهية",
        "baseline_not_beaten": "خط الأساس فاز",
        "negative_net_after_costs": "توقع سلبي بعد التكاليف",
        "overfit_single_horizon": "حفظ عن ظهر قلب لأفق واحد",
        "walk_forward_degraded": "تحلل عبر الزمن",
        "regime_dependence": "اعتماد على نظام واحد",
        "drawdown_too_deep": "تراجع عميق",
        "wide_confidence_interval": "فترة ثقة واسعة",
        "single_symbol_only": "رمز واحد فقط",
        "selection_bias": "تحيز الاختيار",
        "volume_missing": "حجم مفقود",
        "cost_below_floor": "تكلفة تحت الحد",
        "remedy_failed_twice": "العلاج فشل مرتين",
        "autocorrelation_trap": "فخ الارتباط الذاتي",
        "volatility_regime_shift": "تغير نظام التذبذب",
        "liquidity_illusion": "وهم السيولة",
        "overparameterized_signal": "إشارة مفرطة المعاملات",
        "multiple_testing_bias": "تحيز الاختبار المتعدد",
        "non_stationary_drift": "انجراف غير ثابت",
        "microstructure_noise": "ضوضاء البنية الدقيقة",
        "asymmetric_payoff_trap": "فخ العائد غير المتماثل",
        "tail_risk_hidden": "مخاطر ذيلية مخفية",
        "correlation_breakdown": "انهيار الارتباط",
        "concept_drift": "انجراف المفهوم",
        "horizon_mismatch": "عدم تطابق الأفق",
        "threshold_overfit": "حفظ العتبة",
        "sample_contamination": "تلوث العينة",
    }
    return titles.get(cause_id, cause_id)

def _english_explanation(cause_id: str) -> str:
    m = {
        "no_evaluable_origins": "Not enough history to place any test origin.",
        "short_history": "Bar count too short for warm-up + horizon + attempts.",
        "all_scores_abstained": "Method never fired - threshold too high or method unsuitable for this asset.",
        "insufficient_attempts": "Too few attempts for a verdict; small samples swing by chance.",
        "coverage_too_low": "High rate on tiny slice is not a strategy.",
        "cost_eaten_edge": "Gross edge disappeared after costs; gross is not tradable.",
        "cost_filter_starved_sample": "Cost filter removed too much data; remedy starved itself.",
        "below_accuracy_target": "Below 80% target; honest gap, not a knob to tune.",
        "no_directional_edge": "At or below coin flip.",
        "baseline_not_beaten": "Naive baseline matched or won.",
        "negative_net_after_costs": "Negative expectancy after costs.",
        "overfit_single_horizon": "Edge lives in one horizon cell only.",
        "walk_forward_degraded": "Later slice much worse than earlier.",
        "regime_dependence": "One regime carried the result.",
        "drawdown_too_deep": "Cumulative path fell past limit.",
        "wide_confidence_interval": "Wilson interval too wide.",
        "single_symbol_only": "Only one symbol supplied.",
        "selection_bias": "Best of many raced contestants.",
        "volume_missing": "Volume method on zero-volume bars.",
        "cost_below_floor": "Cost assumption below research floor.",
        "remedy_failed_twice": "Remedy applied and cause returned.",
        "autocorrelation_trap": "Serial autocorrelation fools direction count.",
        "volatility_regime_shift": "Volatility regime shift broke the threshold.",
        "liquidity_illusion": "Low-volume periods counted as edge.",
        "overparameterized_signal": "Too many parameters for sample size.",
        "multiple_testing_bias": "Multiple testing without correction.",
        "non_stationary_drift": "Drift changed over time.",
        "microstructure_noise": "Bid-ask bounce at horizon 1 hides signal.",
        "asymmetric_payoff_trap": "High win rate but negative expectancy due to payoff asymmetry.",
        "tail_risk_hidden": "Extreme losses hidden in tail.",
        "correlation_breakdown": "Correlation between methods broke ensemble.",
        "concept_drift": "Market concept drifted over long sample.",
        "horizon_mismatch": "Signal calibrated for different horizon.",
        "threshold_overfit": "Threshold tuned to sample noise.",
        "sample_contamination": "Overlapping windows leak future.",
    }
    return m.get(cause_id, cause_id)

def _avoid_rule(cause_id: str) -> str:
    rules = {
        "no_evaluable_origins": "استيراد تاريخ أطول؛ لا تقلل الاحتساب.",
        "short_history": "أمدّ السلسلة؛ وإلا أبقِ المرشح متقاعداً.",
        "all_scores_abstained": "خفّض عتبة الامتناع مرة واحدة؛ وإلا تقاعد.",
        "insufficient_attempts": "ضاعف ميزانية المحاولات؛ وإلا تقاعد.",
        "coverage_too_low": "خفّض العتبة وأعد قياس التغطية.",
        "cost_eaten_edge": "تداول فقط عندما الدفعة المتوقعة >= 2x التكلفة.",
        "cost_filter_starved_sample": "رخّي المرشح إلى 1.0x؛ تقاعد إذا بقي مجوّعاً.",
        "below_accuracy_target": "حافظ على الفجوة مرئية - الهدف ليس مقبضاً.",
        "no_directional_edge": "تقاعد؛ لا تغيّر الاسم.",
        "baseline_not_beaten": "تقاعد؛ خط الأساس هو المرجع.",
        "negative_net_after_costs": "تقاعد وأبلغ الخسارة.",
        "overfit_single_horizon": "اطلب من الآفاق المجاورة البقاء ضمن 8 نقاط.",
        "walk_forward_degraded": "احكم على الشريحة الحديثة فقط.",
        "regime_dependence": "اطلب من كلا النظامين أن يكونا غير خاسرين.",
        "drawdown_too_deep": "تخطّى التداولات الرقيقة.",
        "wide_confidence_interval": "المزيد من المحاولات؛ وإلا أبقِه غير مثبت.",
        "single_symbol_only": "رمز ثانٍ مطلوب.",
        "selection_bias": "شريحة محتجزة + رمز ثانٍ قبل الادعاء.",
        "volume_missing": "تقاعد طريقة الحجم؛ لا تخترع الحجم.",
        "cost_below_floor": "ارفع إلى الحد الأدنى وأعد التقييم.",
        "remedy_failed_twice": "تقاعد دائماً واحتفظ بقاعدة التجنب.",
        "autocorrelation_trap": "تطبيق تصحيح الارتباط الذاتي والتمهيد.",
        "volatility_regime_shift": "تطبيع حسب التذبذب.",
        "liquidity_illusion": "مرشح حد أدنى للحجم.",
        "overparameterized_signal": "تبسيط الإشارة؛ تقليل المعاملات.",
        "multiple_testing_bias": "تصحيح بونفيروني/FDR.",
        "non_stationary_drift": "إزالة الاتجاه والتطبيع.",
        "microstructure_noise": "تجاهل أفق 1؛ استخدم 3+.",
        "asymmetric_payoff_trap": "اشترط توقعاً إيجابياً، ليس معدل فوز.",
        "tail_risk_hidden": "افحص الذيل؛ اشترط متانة الذيل.",
        "correlation_breakdown": "اختر طرقاً متنوعة غير مرتبطة.",
        "concept_drift": "اختبر استقراراً زمنياً.",
        "horizon_mismatch": "طابق معايرة الأفق مع الاختبار.",
        "threshold_overfit": "تحقق متقاطع للعتبة.",
        "sample_contamination": "زيادة الفصل بين النوافذ.",
    }
    return rules.get(cause_id, "راجع التوثيق.")

def _interpret_numbers(acc, net, dd, cov, cause_id) -> str:
    parts = []
    if acc is not None:
        if acc <= 50:
            parts.append(f"دقة {acc:.1f}% لا تتجاوز العملة - لا حافة.")
        elif acc < 60:
            parts.append(f"دقة {acc:.1f}% ضعيفة - أقل من خط أساس ساذج غالباً.")
        elif acc < 80:
            parts.append(f"دقة {acc:.1f}% متوسطة - بعيدة عن هدف 80%.")
        else:
            parts.append(f"دقة {acc:.1f}% عالية - تحتاج تحقق خارجي.")
    if net is not None and net < 0:
        parts.append(f"توقع {net:+.3f}% سلبي - الطريقة تخسر بعد التكاليف.")
    if dd is not None and dd > 20:
        parts.append(f"تراجع {dd:.1f}% عميق - مسار محفوف بالمخاطر.")
    if cov is not None and cov < 20:
        parts.append(f"تغطية {cov:.1f}% منخفضة - شريحة صغيرة جداً.")
    return " ".join(parts) if parts else "أرقام ضمن الحدود."

def diagnose_batch(evaluations: list[dict], config: dict) -> dict:
    """Diagnose a batch of evaluations, return aggregated insights."""
    from collections import Counter
    all_causes = []
    for ev in evaluations:
        # Lazy import to avoid circular
        import selfcorrect as sc
        causes = sc.diagnose(ev, config)
        all_causes.extend(causes)

    counter = Counter(c["id"] for c in all_causes)
    most_common = counter.most_common(3)

    return {
        "total_evaluations": len(evaluations),
        "total_causes": len(all_causes),
        "unique_causes": len(counter),
        "most_common": [{"cause": c, "count": n, "explanation": explain_failure(c, "")} for c, n in most_common],
        "cause_distribution": dict(counter),
        "primary_failure_mode": most_common[0][0] if most_common else None,
        "is_systematic": len(counter) < len(evaluations) * 0.5,  # few causes explain many failures
        "recommendation": _batch_recommendation(counter, evaluations),
    }

def _batch_recommendation(counter, evaluations) -> str:
    if not counter:
        return "لا أخطاء - استمر في الاختبار على بيانات جديدة غير مرئية."
    top = counter.most_common(1)[0][0] if counter else None
    if top in ("baseline_not_beaten", "no_directional_edge"):
        return "معظم الطرق لا تتفوق على خط الأساس الساذج - جرّب عائلة إشارات مختلفة أو أصل مختلف."
    if top == "cost_eaten_edge":
        return "التكاليف تلتهم الحواف - فعّل مرشح التكلفة المتوقع (cost_multiple=2.0) أو ارفع الأفق."
    if top in ("insufficient_attempts", "wide_confidence_interval"):
        return "العينات صغيرة جداً - استورد تاريخاً أطول قبل استخلاص استنتاجات."
    if top in ("walk_forward_degraded", "regime_dependence", "concept_drift"):
        return "تحلل عبر الزمن/الأنظمة - احكم على الشريحة الحديثة منفصلة واختبر عبر أنظمة متعددة."
    return f"النمط السائد هو {top} - طبّق العلاج الموثق له قبل الجولة التالية."

def remedy_verification(before_causes: list[dict], after_causes: list[dict], remedy_patch: dict) -> dict:
    """
    Verify if a remedy actually worked.
    Compare causes before and after applying patch.
    """
    before_ids = {c["id"] for c in before_causes}
    after_ids = {c["id"] for c in after_causes}

    fixed = before_ids - after_ids
    persisted = before_ids & after_ids
    new_causes = after_ids - before_ids

    success = len(fixed) > 0 and len(persisted) == 0
    partial = len(fixed) > 0 and len(persisted) > 0

    return {
        "remedy_patch": remedy_patch,
        "before_causes": list(before_ids),
        "after_causes": list(after_ids),
        "fixed": list(fixed),
        "persisted": list(persisted),
        "new_introduced": list(new_causes),
        "success": success,
        "partial_success": partial,
        "failed": len(fixed) == 0 and len(persisted) > 0,
        "verdict": "resolved" if success else "partially_resolved" if partial else "recurred" if persisted else "no_change",
        "confidence": 0.9 if success else 0.5 if partial else 0.1,
    }

def diagnostics_spec() -> dict:
    return {
        "name": "Atlas Deep Diagnostics",
        "version": VERSION,
        "capabilities": [
            "explain_failure_ar_en",
            "quantitative_context",
            "remedy_confidence_scoring",
            "batch_diagnosis",
            "remedy_verification",
            "arabic_first_explanations",
        ],
        "languages": ["ar", "en"],
        "honesty": "Diagnostics explain process failures, not market predictions. Confidence scores are about remedy applicability, not future profits.",
    }
