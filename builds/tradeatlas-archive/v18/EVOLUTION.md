# TradeAtlas — Evolution Tracker (v17)

> Research software only. Not financial advice. `goal_established` is false in every code path.

الـ **Evolution Tracker** هو قلب v17: كل جيل يتعلم من الجيل اللي قبله، يشخص فشله، يتجنبه، ويطبق علاجاً مُثبتاً.

## الفكرة

> **كل اختبار يفشل → يُحدد السبب بدقة → يتجنبه في الاختبار اللي بعده → يلاقيلو حل ويتحقق منه.**

```
جيل 1: screen → diagnose (35 سبب) → lessons (observed)
جيل 2: apply lessons (pre-apply resolved patches, skip retired) → evaluate → diagnose → verify (resolved vs recurred)
جيل 3: validate (recent slice + second symbol)
جيل 4+: carry-over + predict_failure before testing → skip 92% of proven dead
```

## 35 سبباً بدل 21

| جديد في v17 | لماذا كان مفقوداً | العلاج |
|---|---|---|
| `autocorrelation_trap` | الارتباط الذاتي يخدع العدد | bootstrap p-value |
| `volatility_regime_shift` | التذبذب تغير | تطبيع + تقسيم الأنظمة |
| `liquidity_illusion` | حجم وهمي | مرشح حد أدنى للحجم |
| `overparameterized_signal` | معاملات كثيرة/عينة صغيرة | تبسيط |
| `multiple_testing_bias` | p-hacking | Bonferroni/FDR |
| `non_stationary_drift` | الانجراف تغير | إزالة اتجاه |
| `microstructure_noise` | ارتداد العرض/الطلب في أفق 1 | تجاهل أفق 1 |
| `asymmetric_payoff_trap` | فوز كثير + خسارة كبيرة | اشترط توقع إيجابي |
| `tail_risk_hidden` | ذيل سمين مخفي | VaR/CVaR |
| `correlation_breakdown` | ارتباط الطرق انهار | تنويع |
| `concept_drift` | السوق تغير عبر الزمن | استقرار زمني |
| `horizon_mismatch` | معايرة لأفق مختلف | تطابق الآفاق |
| `threshold_overfit` | عتبة محفوظة | تحقق متقاطع |
| `sample_contamination` | نوافذ متداخلة تسرب | فصل 2x الأفق |

كل سبب: `title` ثنائي اللغة، `meaning`, `avoid` (قاعدة للاختبار التالي), `remedy`, `remedy_kind`, `patch` (config change).

## الوحدات

### evolution.py

- `compute_evolution_metrics(history)` → `resolved_rate`, `retirement_rate`, `avoidance_efficiency`, `accuracy_trend`, `improvement_signal`, `is_learning`, `verdict`.
- `failure_cluster(lessons)` → `by_cause`, `by_severity`, `dominant_cause`, `diversity_index`.
- `predict_failure_probability(candidate_key, prior_lessons)` → 0.92 لو المرشح متقاعد قبل، 0.7 لو العائلة فشلت كثيراً.
- `remedy_effectiveness(lessons)` → resolve_rate per remedy_kind.
- `evolution_spec()` → honesty note: tracks process, not market.

### diagnostics.py

- `explain_failure(cause_id, evidence, evaluation)` → `title_ar`, `explanation_ar`, `explanation_en`, `remedy_confidence`, `estimated_fix_success_pct`, `quantitative_context`.
- `diagnose_batch(evaluations, config)` → dominant cause + recommendation.
- `remedy_verification(before, after, patch)` → `verdict: resolved|partially_resolved|recurred`.

### marketlab.py — Advanced Stats

- `bootstrap_mean_ci`, `permutation_pvalue`, `bonferroni_threshold`, `benjamini_hochberg`, `deflated_sharpe_ratio`, `tail_risk_metrics`, `autocorrelation_check`, `volatility_regime_detection`, `liquidity_score`, `pbo_estimate`, `adaptive_threshold_optimization`.

### platformdb.py — SQLite v4

New tables: `evolution_generations`, `failure_clusters`, `remedy_verifications`, `diagnostic_reports`. Methods: `record_evolution`, `list_evolution`, `record_failure_cluster`, `record_remedy_verification`, `record_diagnostic_report`, `evolution_summary`.

### pipeline.py — Health

- `health_check(db)` → stale detection.
- `adaptive_target_bars(current, desired, interval)` → recommended bars.
- `retry_collect_with_backoff(db, plan)` → exponential backoff.

## API

| Endpoint | ماذا تفعل |
|---|---|
| `GET /api/evolution` | generatons + cluster + metrics + remedy_effectiveness |
| `GET /api/diagnostics?cause=` | شرح ثنائي اللغة |
| `GET /api/pipeline/health` | health + metrics |
| `GET /api/lab/advanced-stats` | bootstrap/tail/sharpe/pbo demo |
| `POST /api/lab/predict-failure` | تنبؤ قبل الاختبار |
| `POST /api/lab/remedy-verify` | تحقق أن العلاج نجح |
| `POST /api/lab/bootstrap` | bootstrap CI |
| `POST /api/lab/permutation` | permutation p-value |
| `POST /api/evolution/record` | سجل جيل |
| `POST /api/diagnostics/explain` | شرح مفصل وسجل |

## الاختبارات — 143

66 اختبار جديد تغطي:
- 14 سبباً جديداً + patch application
- diagnostics ثنائي اللغة + batch + verification
- evolution metrics + clustering + prediction + remedy effectiveness
- advanced stats (10 دوال إحصائية)
- pipeline health + adaptive + retry
- DB v4 CRUD
- HTTP endpoints (8 endpoints)
- self-healing loop (fشل → diagnose → avoid → remedy → verify)

كلها `deterministic`, `stdlib only`, `no lookahead`, `goal_established=false` دائماً.

## ما لا تفعله

- لا ترفع الدقة بالسحر.
- `prediction.should_skip` يمنع إعادة اختبار ميت مُثبت — لا يخترع حافة.
- Bootstrap/permutation تصف الماضي، لا تتنبأ بالمستقبل.

## تشغيل

```bash
python3 tradeatlas.py --demo  # generates sample-evolution.json etc
python3 -m unittest test_tradeatlas  # 143 tests
GET /api/evolution
GET /api/diagnostics?cause=baseline_not_beaten
POST /api/lab/predict-failure {"methods":["atlas_minute_pulse"],"horizons":[5],"symbol":"BTC"}
```
