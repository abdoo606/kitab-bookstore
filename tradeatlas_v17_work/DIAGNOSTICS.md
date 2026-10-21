# TradeAtlas — Deep Diagnostics (v17)

> تشخيص كل فشل بالعربية أولاً، ثم الإنجليزية. كل سبب له قصة، دليل، وعلاج.

## لماذا diagnostics؟

معظم الأدوات تقول "55% accuracy" وتتوقف. `diagnostics.py` يسأل:

- **لماذا** 55%؟ هل هو خط الأساس؟ تكلفة؟ تحلل؟ تصغير؟
- **ماذا تتجنب** في الاختبار التالي؟
- **ما confidence** العلاج؟

## EXPLANATIONS — 35 سبباً

كل سبب:

```python
EXPLANATIONS["baseline_not_beaten"] == "خط الأساس الساذج جيد على الأقل..."
REMEDY_CONFIDENCE["baseline_not_beaten"] == 0.05  # 5% fix chance → retire
```

Confidence <0.1 → علاج مستحيل → retire فوراً (لا تضيع وقت).
Confidence >0.7 → علاج قابل للتطبيق (مثل `insufficient_attempts` 0.7).

## الواجهة

### explain_failure(cause_id, evidence, evaluation)

```python
diag.explain_failure("asymmetric_payoff_trap", "60% win but net -0.05%", ev)
# → {
#   cause: "asymmetric_payoff_trap",
#   title_ar: "فخ العائد غير المتماثل",
#   explanation_ar: "معدل فوز عالٍ لكن توقع سلبي بسبب تفاوت الأرباح/الخسائر...",
#   explanation_en: "High win rate but negative expectancy...",
#   evidence: "...",
#   remedy_confidence: 0.6,
#   is_fixable: True,
#   is_fatal: False,
#   next_test_avoid_rule: "اشترط توقعاً إيجابياً، ليس معدل فوز.",
#   estimated_fix_success_pct: 60.0,
#   quantitative_context: {accuracy_pct, net_pct, drawdown_pct, interpretation}
# }
```

### diagnose_batch(evaluations, config)

يكشف النمط المنهجي:

```python
diag.diagnose_batch([ev1, ev2, ...], config)
# → {
#   total_evaluations: 35,
#   unique_causes: 5,
#   most_common: [{cause: "baseline_not_beaten", count: 20, explanation: {...}}],
#   primary_failure_mode: "baseline_not_beaten",
#   is_systematic: True,  # قليل من الأسباب يفسر كثيراً من الفشل → إشارة للتغيير الجذري
#   recommendation: "معظم الطرق لا تتفوق على خط الأساس الساذج — جرّب عائلة إشارات مختلفة..."
# }
```

### remedy_verification(before_causes, after_causes, patch)

يتأكد أن العلاج لم يكن مسرحاً:

```python
diag.remedy_verification(
  before=[{"id":"cost_eaten_edge"}],
  after=[{"id":"below_accuracy_target"}],
  patch={"cost_multiple":2.0}
)
# → {
#   fixed: ["cost_eaten_edge"],
#   persisted: [],
#   new_introduced: ["below_accuracy_target"],
#   verdict: "resolved",
#   success: True,
#   confidence: 0.9
# }
# لو عاد نفس السبب → verdict: "recurred", confidence:0.1 → retire
```

### diagnostics_spec()

يُرجع spec inspectable للـUI.

## ثنائية اللغة

| cause | title_ar | title_en |
|---|---|---|
| `no_directional_edge` | لا حافة اتجاهية | No directional edge at all |
| `tail_risk_hidden` | مخاطر ذيلية مخفية | Fat tail / hidden tail risk |
| `microstructure_noise` | ضوضاء البنية الدقيقة | Microstructure noise |

UI يعرض `title_ar` أولاً لو `lang==ar`.

## HTTP

- `GET /api/diagnostics?cause=baseline_not_beaten` → explanation
- `POST /api/diagnostics/explain` {cause, evidence, evaluation, symbol, record:true} → explanation + DB record
- `POST /api/lab/remedy-verify` {before_causes, after_causes, patch} → verification + optional DB

## الاختبارات

- كل 35 سبباً لديه شرح عربي/إنجليزي + confidence.
- `batch_diagnosis` يحدد `dominant_cause`.
- `remedy_verification` يميز `resolved` vs `recurred`.

## الفلسفة

> **الشخص الذي يكرر نفس الاختبار ويتوقع نتيجة مختلفة ليس باحثاً.**
> Diagnostics يمنع ذلك: نفس السبب مرتين = `remedy_failed_twice` → تقاعد دائم + avoid-rule دائم.

`goal_established` يبقى `false` — التشخيص يحسن البحث، ليس السوق.
