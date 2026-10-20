# تشغيل جديد ونتائج عملية — 20 أكتوبر 2026

## النتيجة المفيدة
أفضل طلب راجعناه هو موقع خدمات صغير من ثلاث صفحات. أقرب لقدرتنا من المناقصات المؤسسية، لكن التقديم يحتاج حساب Freelancer وإجراءات المنصة؛ لا توجد جلسة دخول جاهزة هنا ولا إرسال أو قبول أو دفع.

### المرشح الأول — Framer Free template 3-Page Service Business Website
https://www.br.freelancer.com/projects/web-design/Framer-Free-template-Page-Service
Project ID: 40776894
الميزانية المعروضة: 250–750 USD، وليست متوسط عروض المستقلين. الصفحة عرضت Open for bidding وEnds in 6 days عند الجلب؛ لا تاريخ انتهاء مطلق مؤكداً. ظهرت 230 مشاركة عند الجلب، لذا المنافسة عالية.
المطلوب: رئيسية، خدمات، تواصل؛ تصميم متجاوب، سهولة تعديل النصوص، المصدر وتعليمات تسليم، نموذج إرسال بريد محمي من السبام ومختبر. العنوان يشير إلى Framer، لكن النص يقبل HTML/CSS أو WordPress/Webflow أو منشئ آخر؛ اختيار المنصة يحتاج توضيحاً. يطلب أمثلة لمواقع مشابهة؛ لا توجد مراجع عملاء مثبتة لدينا، لذلك يمكن تقديم عينة مستقلة بصفتها الحقيقية لا عملاً سابقاً لعميل.
اقتراح داخلي غير مرسل: 350 USD / أربعة أيام عمل بعد تثبيت النطاق واستلام المحتوى والصلاحيات اللازمة. يشمل جولتي تعديل، لا يشمل شراء الاستضافة أو النطاق أو خدمات البريد. لا نفترض قبول الكريبتو أو الدفع خارج المنصة. عبارة Paid on delivery ليست ضمان دفع ولا إثبات تمويل milestone.

مسودة غير مرسلة:
Hello, I can build your three-page service website with a responsive Home, Services and Contact layout, editable content, and a spam-protected contact form. My proposed fixed scope is USD 350 with two revision rounds, targeting four working days after the content, platform choice and necessary access are agreed. I would confirm your preference for Framer versus another editable approach before starting. Delivery includes source/handoff materials, mobile checks and a real email-delivery test. Domain, hosting and third-party subscriptions are not included. My available code samples are independent review projects, not claimed client redesigns; I can provide a relevant small demo rather than invent client references. Any engagement and payment would follow the platform's process.

### خيار ضعيف — Seven-Page Static HTML Site
https://www.freelancer.com/projects/web-design/Seven-Page-Static-HTML-Site
Project ID: 40775559
المطلوب سبع صفحات ثابتة وواجهة رئيسية قبل المساء. الصفحة تعرض نطاق ₹600–1500 INR بينما نص الطلب يقول Budget INR 2000؛ تعارض يحتاج توضيحاً. ظهر مفتوحاً مع Ends in 6 days و102 عرض عند الجلب. ملائم تقنياً لكن ميزانيته ضعيفة والموعد القصير غير محدد المنطقة الزمنية؛ ليس الأولوية.

## ما شغّلناه فعلياً
1. بحث ويب للوصول إلى طلبات جديدة، ثم جلب صفحات المشروع الفردية بأداة التصفح، وليس الاعتماد على صفحة قوائم الوظائف أو عروض المستقلين.
2. حفظ مقتطفات قسم المشتري فقط في fresh/؛ البيانات مقتطفات وليست صفحات كاملة. لم يُنفّذ زحف requests مباشر بسبب قيود شبكة بيئة بايثون المعروفة.
3. تشغيل السكربت الأصلي على هذه المقتطفات: الأول needs_deadline_review والثاني not_service_request. كشف ذلك نقصاً في فهم منشورات المنصات التي لا تستخدم صيغة RFP.
4. تحديث محدود: يتعرف على Open for bidding فقط لصفحات مشاريع Freelancer ذات مقتطف مشتري معلّم buyer_section_only=true؛ يحفظ الزمن النسبي كما هو دون اختراع تاريخ. يلتقط نطاق العملة في رأس قسم المشتري وINR دون استخدام متوسط عروض المستقلين. النص القديم يصبح stale_platform_snapshot_review في تشغيل بتاريخ لاحق.
5. إعادة التشغيل: سجّلان platform_reports_open_review، وصفر أخطاء تحليل. 25 اختباراً ناجحاً. verified=false دائماً، والأهلية والدفع غير مؤكدين.

## الملفات وإعادة التشغيل
نتيجة ما قبل التعديل: results/fresh-before/
نتيجة ما بعد التعديل: results/fresh/
من مجلد الحزمة بعد تثبيت requirements.txt:
```bash
python -m unittest -v
python scrape_clients.py --sources fresh/sources.json --mode snapshot --as-of 2026-10-20 --out results/replay-fresh
```
المرحلة الجديدة لا تضيف اكتشافاً آلياً عبر محرك بحث ولا دخولاً للمنصة. البحث والجلب تمّا بأدوات التصفح، والفرز بالسكربت. يمكن للوكيل التالي مراجعة المرشح الأول وتجهيز عينة صغيرة أو البحث عن طلب مماثل له قناة تقديم متاحة، بدلاً من العودة للمناقصات المؤسسية أو إعادة مراسلة Iditarod.
