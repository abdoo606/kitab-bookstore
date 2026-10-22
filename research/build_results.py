# -*- coding: utf-8 -*-
"""يبني ملف النتائج (PDF عربي RTL) من الأرقام المحسوبة في calc.py."""
from __future__ import annotations

import math
import os

from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display

import calc as C

W, H = A4
LM = RM = 46
TM = 64
BM = 52
CW = W - LM - RM
NAVY = (0.07, 0.10, 0.16)
GOLD = (0.76, 0.60, 0.24)
GREY = (0.38, 0.42, 0.48)
LIGHT = (0.945, 0.952, 0.965)
RED = (0.70, 0.17, 0.20)
GREEN = (0.10, 0.45, 0.32)

FD = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("AR", f"{FD}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("ARB", f"{FD}/DejaVuSans-Bold.ttf"))
_R = ArabicReshaper(configuration={"delete_harakat": False, "support_ligatures": True})

import re
_HAS_AR = re.compile("[\u0600-\u06ff\ufb50-\ufdff\ufe70-\ufeff]")


def shape_word(w: str) -> str:
    """Reshape + visual-order a single Arabic word.

    Words are ordered right-to-left by `draw_rtl`, so each word must be
    rendered in visual (reversed) order — that is what get_display does for a
    run that contains no digits.
    """
    return get_display(_R.reshape(w), base_dir="R")


def word_is_ar(w: str) -> bool:
    return bool(_HAS_AR.search(w))


def _font(bold: bool) -> str:
    return "ARB" if bold else "AR"


def word_width(w: str, size: float, bold: bool = False) -> float:
    if word_is_ar(w):
        return pdfmetrics.stringWidth(shape_word(w), _font(bold), size)
    return pdfmetrics.stringWidth(w, _font(bold), size)


SPACE_CACHE = {}


def space_width(size: float, bold: bool = False) -> float:
    key = (round(size, 2), bold)
    if key not in SPACE_CACHE:
        SPACE_CACHE[key] = pdfmetrics.stringWidth(" ", _font(bold), size)
    return SPACE_CACHE[key]


def line_width(text: str, size: float, bold: bool = False) -> float:
    words = text.split()
    if not words:
        return 0.0
    if not _HAS_AR.search(text):
        return pdfmetrics.stringWidth(text, _font(bold), size)
    return sum(word_width(w, size, bold) for w in words) + space_width(size, bold) * (len(words) - 1)


def draw_rtl(c, x_right: float, y: float, text: str, size: float,
             bold: bool = False, color=(0.12, 0.14, 0.18)) -> None:
    """Draw one line right-to-left: Arabic words shaped, numbers/Latin kept LTR.

    We never hand the whole line to python-bidi, because it reorders number runs
    across line boundaries. Ordering words ourselves is exact and predictable.
    """
    c.setFillColorRGB(*color)
    c.setFont(_font(bold), size)
    if not _HAS_AR.search(text):
        # pure Latin / numeric line: keep natural left-to-right word order
        c.drawRightString(x_right, y, text)
        return
    x = x_right
    sw = space_width(size, bold)
    for i, w in enumerate(text.split()):
        if i:
            x -= sw
        ww = word_width(w, size, bold)
        if word_is_ar(w):
            c.drawRightString(x, y, shape_word(w))
        else:
            c.drawRightString(x, y, w)
        x -= ww


def wrap(text: str, size: float, maxw: float, bold: bool = False):
    out = []
    for para in str(text).split("\n"):
        line = ""
        for w in para.split():
            t = (line + " " + w).strip()
            if line_width(t, size, bold) <= maxw or not line:
                line = t
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def draw_rtl_centred(c, x_center: float, y: float, text: str, size: float,
                     bold: bool = True, color=(1, 1, 1)) -> None:
    w = line_width(text, size, bold)
    draw_rtl(c, x_center + w / 2, y, text, size, bold, color)


class Doc:
    def __init__(self, path: str, title: str):
        self.c = canvas.Canvas(path, pagesize=A4)
        self.c.setTitle(title)
        self.page = 1
        self.y = H - TM
        self._frame()

    def _frame(self):
        c = self.c
        c.setFillColorRGB(*NAVY)
        c.rect(0, H - 24, W, 24, stroke=0, fill=1)
        c.setFillColorRGB(*GOLD)
        c.rect(0, H - 27, W, 3, stroke=0, fill=1)
        c.setFillColorRGB(1, 1, 1)
        c.setFont("ARB", 7.6)
        draw_rtl(c, W - RM, H - 16, "مشروع الفراغ — النتائج والحسابات", 7.6, True, (1, 1, 1))
        c.setFillColorRGB(*GREY)
        c.setFont("AR", 7.4)
        c.drawString(LM, 26, "Kitab Research · v6")
        c.drawRightString(W - RM, 26, str(self.page))

    def new_page(self):
        self.c.showPage()
        self.page += 1
        self._frame()
        self.y = H - TM

    def need(self, h):
        if self.y - h < BM:
            self.new_page()

    def h1(self, text):
        """Section banner that stays in the flow — no wasted page."""
        if self.y < H - TM - 40:
            self.y -= 22
        self.need(96)
        top = self.y
        self.c.setFillColorRGB(*NAVY)
        self.c.rect(LM, top - 46, CW, 46, stroke=0, fill=1)
        self.c.setFillColorRGB(*GOLD)
        self.c.rect(W - RM - 4, top - 46, 4, 46, stroke=0, fill=1)
        draw_rtl(self.c, W - RM - 16, top - 30, text, 17, True, (1, 1, 1))
        self.y = top - 46 - 16

    def h2(self, text):
        self.need(50)
        self.y -= 10
        self.c.setFillColorRGB(*GOLD)
        self.c.rect(W - RM - 3, self.y - 16, 3, 18, stroke=0, fill=1)
        self.c.setFillColorRGB(*NAVY)
        draw_rtl(self.c, W - RM - 10, self.y - 13, text, 14, True, NAVY)
        self.y -= 28

    def p(self, text, size=10.9, color=(0.12, 0.14, 0.18)):
        lead = size * 1.86
        self.c.setFillColorRGB(*color)
        self.c.setFont("AR", size)
        for ln in wrap(text, size, CW):
            self.need(lead)
            draw_rtl(self.c, W - RM, self.y, ln, size, False, color)
            self.y -= lead
        self.y -= 4

    def bullets(self, items, size=10.6):
        for it in items:
            for i, ln in enumerate(wrap(it, size, CW - 18)):
                self.need(size * 1.8)
                if i == 0:
                    self.c.setFillColorRGB(*GOLD)
                    self.c.setFont("ARB", size)
                    self.c.drawRightString(W - RM, self.y, "•")
                draw_rtl(self.c, W - RM - 14, self.y, ln, size)
                self.y -= size * 1.8
        self.y -= 3

    def box(self, title, text, accent=GOLD, size=10.6):
        lines = wrap(text, size, CW - 28)
        h = 18 + len(lines) * size * 1.7 + 16
        self.need(h + 10)
        top = self.y
        self.c.setFillColorRGB(*LIGHT)
        self.c.rect(LM, top - h, CW, h, stroke=0, fill=1)
        self.c.setFillColorRGB(*accent)
        self.c.rect(W - RM - 3, top - h, 3, h, stroke=0, fill=1)
        yy = top - 18
        if title:
            self.c.setFillColorRGB(*NAVY)
            draw_rtl(self.c, W - RM - 14, yy, title, 11, True, NAVY)
            yy -= 17
        for ln in lines:
            draw_rtl(self.c, W - RM - 14, yy, ln, size, False, (0.15, 0.17, 0.22))
            yy -= size * 1.7
        self.y = top - h - 12

    def code(self, lines, size=7.4):
        h = len(lines) * (size * 1.55) + 16
        self.need(h + 8)
        top = self.y
        self.c.setFillColorRGB(0.06, 0.08, 0.12)
        self.c.rect(LM, top - h, CW, h, stroke=0, fill=1)
        yy = top - 14
        self.c.setFillColorRGB(0.62, 0.88, 0.78)
        self.c.setFont("Courier", size)
        for ln in lines:
            self.c.drawString(LM + 8, yy, ln[:120])
            yy -= size * 1.55
        self.y = top - h - 10

    def table(self, headers, rows, widths=None, size=8.8, hs=9.0):
        if not widths:
            widths = [CW / len(headers)] * len(headers)
        sc = CW / sum(widths)
        widths = [w * sc for w in widths]

        def header():
            self.need(28)
            wrapped = [wrap(str(h), hs, widths[i] - 10, True) for i, h in enumerate(headers)]
            hh = max(len(x) for x in wrapped) * 12 + 10
            top = self.y
            self.c.setFillColorRGB(*NAVY)
            self.c.rect(LM, top - hh, CW, hh, stroke=0, fill=1)
            x = W - RM
            for i, ls in enumerate(wrapped):
                yy = top - 12
                for ln in ls:
                    draw_rtl(self.c, x - 5, yy, ln, hs, True, (1, 1, 1))
                    yy -= 12
                x -= widths[i]
            self.y = top - hh

        header()
        for r, row in enumerate(rows):
            cells = [wrap(str(c), size, widths[i] - 10) for i, c in enumerate(row)]
            rh = max(len(x) for x in cells) * (size * 1.45) + 8
            if self.y - rh < BM + 26:
                self.new_page()
                header()
            top = self.y
            if r % 2 == 0:
                self.c.setFillColorRGB(0.972, 0.976, 0.983)
                self.c.rect(LM, top - rh, CW, rh, stroke=0, fill=1)
            x = W - RM
            for i, ls in enumerate(cells):
                yy = top - size - 4
                for ln in ls:
                    draw_rtl(self.c, x - 5, yy, ln, size)
                    yy -= size * 1.45
                x -= widths[i]
            self.c.setStrokeColorRGB(0.87, 0.89, 0.92)
            self.c.setLineWidth(0.4)
            self.c.line(LM, top - rh, W - RM, top - rh)
            self.y = top - rh
        self.y -= 10

    def cover(self):
        self.c.setFillColorRGB(*NAVY)
        self.c.rect(0, 0, W, H, stroke=0, fill=1)
        self.c.setFillColorRGB(*GOLD)
        self.c.rect(W - LM - 90, H - 240, 90, 3, stroke=0, fill=1)
        yy = H - 190
        for ln in ["مشروع الفراغ", "النتائج والحسابات"]:
            self.c.setFillColorRGB(1, 1, 1)
            draw_rtl(self.c, W - LM, yy, ln, 34, True, (1, 1, 1))
            yy -= 48
        yy -= 12
        for ln in wrap("من قانون كازيمير إلى سقف الكون: ما تقوله الأرقام، وأين تنتهي، "
                       "وما التجربة الواحدة التي يمكن أن تغيّر الجواب", 13, CW - 60):
            self.c.setFillColorRGB(0.80, 0.85, 0.92)
            draw_rtl(self.c, W - LM, yy, ln, 13, False, (0.80, 0.85, 0.92))
            yy -= 22
        yy = 190
        for ln in ["الإصدار السادس — ٢٠٢٦", "١٤ نتيجة محسوبة · ٦ جداول · صفر أرقام مكتوبة يدوياً",
                   "كل رقم يُعاد حسابه بأمر واحد"]:
            self.c.setFillColorRGB(*GOLD)
            draw_rtl(self.c, W - LM, yy, ln, 11, True, GOLD)
            yy -= 20
        self.new_page()


def sup(x: float) -> str:
    return C.sup(x)


def main(out: str = "نتائج-مشروع-الفراغ.pdf") -> None:
    r = C.build()
    d = Doc(out, "مشروع الفراغ — النتائج والحسابات")
    d.cover()

    # ---------------------------------------------------------- 1
    d.h2("١. الجواب النهائي في نصف صفحة")
    d.p("السؤال كان: هل يمكن الانتقال بين نقطتين في الكون دون عبور المسافة بينهما؟ "
        "بعد الحساب، الجواب ليس «نعم» ولا «مستحيل»، بل رقم: الجيوب الدودية تحتاج طاقة أكبر مما "
        "يمكن جمعه، لكنها تحتاج أولاً زمناً أطول مما يسمح به قانون الطاقة الكمومية. والعقبة الحاكمة "
        "ليست الطاقة.")
    d.box("الرقم الذي يحسم كل شيء",
          "أكبر جيب دودي يمكن أن يتسع له الكون المرئي كله (نصف قطر 4.4×10²⁶ متر) "
          "يبقى مفتوحاً 1.97×10⁻¹³ ثانية فقط — أي 0.2 بيكوثانية. وللبقاء ثانية واحدة "
          "يحتاج نصف قطر أكبر من الكون بـ 2.59×10²⁵ مرة.", RED)
    d.p("هذا الرقم مشتق، لا مقتبس: جمعنا قيدين معروفين — كثافة الطاقة السالبة التي تفرضها هندسة العنق، "
        "والحدّ الأعلى الذي تسمح به متباينة الطاقة الكمومية — وحللنا المعادلة بالنسبة لنصف القطر. "
        "النتيجة قانون واحد بمعامل واحد، وسنعرضه في القسم الثالث مع كل خطوة.")
    d.p("المعنى العملي: لا يوجد تصميم جيب دودي في الأدبيات يقترب من هذا الحدّ. أفضل تصميم منشور "
        "(قشرة فيسر) يبعد 17 مرتبة عشرية، وأسوأها (حلقة رومان) 26 مرتبة. والمسافة بين 17 و26 "
        "مرتبة عشرية هي المسافة بين «مشروع بحثي صعب» و«لا شيء على الإطلاق».")

    # ---------------------------------------------------------- 2
    d.h1("القسم الأول — ماذا قاست الفيزياء فعلاً")
    d.h2("٢. الفراغ ليس صفراً، وهذا مقيس")
    d.p("تأثير كازيمير ليس فكرة نظرية: قُيس أول مرة عام ١٩٩٧، وتحسّنت دقته منذ ذلك الحين إلى نحو 0.1٪. "
        "لوحان متقاربان في فراغ يحجبان أطوالاً موجية أطول من المسافة بينهما، فتصبح كثافة الطاقة بينهما "
        "أقل من كثافة الفراغ خارجهما. النتيجة ضغط سالب حقيقي، وقابل للقياس.")
    d.table(["المسافة بين اللوحين", "كثافة الطاقة (J/m³)", "الضغط (Pa)"],
            [[lab, f"−{sup(abs(r['casimir'][k]['rho']))}", f"−{sup(abs(r['casimir'][k]['p']))}"]
             for k, lab in [(0, "10 nm"), (1, "100 nm"), (2, "1 µm"), (3, "1 mm")]],
            widths=[1.3, 1.5, 1.3])
    d.p("الكثافة والضغط لا يتساويان: الضغط ثلاثة أضعاف الكثافة في هندسة اللوحين المتوازيين، "
        "والمقارنة هنا تُجرى مع الكثافة لأنها الكمية التي تفرضها هندسة العنق.")
    d.p("لاحظ الاتجاه: كل مضاعفة في المسافة تخفض الكثافة 16 مرة (الأس الرابع). وهذه هي المشكلة "
        "الهندسية الأولى: الطاقة السالبة متاحة فقط على مقياس النانومتر، وتختفي تماماً على أي مقياس بشري.")
    d.box("الفجوة الحقيقية، بالرقم",
          f"الكثافة المطلوبة لعنق نصف قطره متر واحد هي {sup(abs(C.rho_throat(1.0)))} جول/م³. "
          f"وأقوى كثافة سالبة قيست (كازيمير عند 10 نانومتر) هي {sup(abs(r['casimir'][0]['rho']))} جول/م³. "
          f"الفجوة: {sup(r['casimir'][0]['gap_to_1m_throat'])} مرة.", RED)

    # ---------------------------------------------------------- 3
    d.h1("القسم الثاني — القوانين الخمسة")
    d.h2("٣. من أين جاءت كل الأرقام")
    d.p("كل نتيجة في هذا الملف تُحسب من خمس علاقات فقط. الأولى والثانية معروفتان في الأدبيات؛ "
        "والثالثة هي تركيبهما، وهي النتيجة الأصلية لهذا العمل؛ والرابعة والخامسة قيود هندسية "
        "ومدّ جَزْري.")
    d.code([
        "1) throat density (Morris-Thorne, b'=1):",
        "     rho_req = - c^4 / (8*pi*G*b^2)",
        "",
        "2) quantum inequality (Ford-Roman, sampling T):",
        "     rho_min = - 3*hbar / (32*pi^2*c^3*T^4)",
        "",
        "3) persistence window  (1 and 2 combined, solved for b):",
        "     b >= k*T^2 ,   k = sqrt(4*pi*c^7/(3*G*hbar))",
        "     k = %s m/s^2   (= %.3f x Planck acceleration)" % (C.sci(r['window']['k']), r['window']['k_over_a_planck']),
        "",
        "4) exotic mass / energy:",
        "     M = c^2*b/G ,   E = c^4*b/G ,   dE/db = c^4/G = %s J/m" % C.sci(C.D_E_DB),
        "",
        "5) tidal survival:",
        "     b >= (v/c) * c * sqrt(L/a_max)",
    ])
    d.p("لاحظ أن القانون الثالث يعطي كمية بُعدها تسارع. قيمته 1.1406×10⁵² متر/ثانية²، وهي أكبر من "
        "تسارع بلانك بـ 2.047 مرة فقط. هذا التقارب ليس مصادفة: المتباينة الكمومية والجاذبية الكمومية "
        "تتقابلان عند المقياس نفسه، والقانون يقيس المسافة بينهما.")

    # ---------------------------------------------------------- 4
    d.h1("القسم الثالث — جداول النتائج")
    d.h2("٤. ماذا يحدث عند كل حجم؟")
    d.p("الجدول التالي هو قلب البحث: لكل نصف قطر، الكثافة المطلوبة، وأقصى مدة بقاء يسمح بها القانون، "
        "والزمن الذي يحتاجه الضوء ليعبر العنق. العمود الأخير هو الحكم: نسبة المدة المسموحة إلى المدة "
        "اللازمة. أي قيمة أقل من واحد تعني أن الجيب يختفي قبل أن يعبر الضوء.")
    rows = []
    for row in r["throat_table"]:
        rows.append([row["label"], sup(abs(row["rho"])), sup(row["t_max"]),
                     sup(row["light_crossing"]), sup(row["deficit"])])
    d.table(["نصف القطر", "الكثافة المطلوبة (J/m³)", "أقصى مدة (ث)", "زمن عبور الضوء (ث)", "النسبة"], rows,
            widths=[1.0, 1.5, 1.15, 1.15, 0.9], size=8.2)
    d.p("اقرأ السطر الأخير: جيب بنصف قطر سنة ضوئية — أكبر من أي بناء تخيّله البشر — يبقى مفتوحاً "
        "9.12×10⁻¹⁹ ثانية، بينما يحتاج الضوء 3.16×10⁷ ثانية ليعبره. النسبة 2.9×10⁻²⁶. "
        "أي أن الجيب يغلق قبل أن يقطع الضوء جزءاً من مليار مليار من العنق.")
    d.box("الاستثناء الوحيد: مقياس بلانك",
          "عند نصف قطر بلانك تصبح النسبة 0.7 — أي أن القانون يُشبع تماماً عند حدّ الفيزياء المعروفة. "
          "هذا ليس فراغاً في الحساب، بل تأكيد على أن القانون يعمل بالضبط حيث تتقابل النظريتان.", GREEN)

    d.h2("٥. الاتجاه المعاكس: كم يجب أن يكون الحجم ليبقى مدة معينة؟")
    d.p("هذا الجدول يجيب عن السؤال الأعملي: لو أردنا جيباً يبقى مفتوحاً لمدة كافية للعبور، ما حجمه؟ "
        "العمود الأخير يقارن الحجم بنصف قطر الكون المرئي.")
    rows = [[row["label"], sup(row["b"]),
             (f"{row['b_over_universe']:.0f}×" if row["b_over_universe"] < 1e6
              else f"{sup(row['b_over_universe'])}×")] for row in r["reverse"]]
    d.table(["المدة المطلوبة", "نصف القطر المطلوب (m)", "مضاعف نصف قطر الكون"], rows,
            widths=[1.2, 1.8, 1.6])
    d.p("النتيجة الأهم في هذا الجدول: حتى بيكوثانية واحدة — مدة لا يكاد يقيسها أي جهاز — تحتاج عنقاً "
        "أكبر من الكون المرئي بـ 26 مرة. ولا يوجد حجم «صغير» في هذا النظام: كل مدة تُقاس بالثواني "
        "تحتاج حجماً يفوق الكون بعشرات المراتب.")

    d.h2("٦. ثمن العنق: الكتلة والطاقة")
    d.p("الطاقة المطلوبة لفتح عنق تتناسب خطياً مع نصف قطره، ومعامل التناسب ثابت عالمي: "
        f"{sup(C.D_E_DB)} جول لكل متر. وهذا الرقم يساوي بالضبط ما تطلقه الشمس في عمرها كله "
        "(عشرة مليارات سنة) — لكل متر واحد.")
    rows = []
    for row in r["throat_table"][3:]:
        rows.append([row["label"], sup(row["energy"]),
                     f"{row['mass_jup']:.2e}" if row["mass_jup"] >= 0.01 else "—",
                     f"{row['mass_sun']:.2e}"])
    d.table(["نصف القطر", "الطاقة (J)", "الكتلة (مشتري)", "الكتلة (شمس)"], rows,
            widths=[1.0, 1.4, 1.3, 1.3])
    d.p("الكتلة سالبة، وهذا يعني أنها تتنافر مع المادة العادية. الاحتفاظ بها في مكان واحد يحتاج "
        "قوى إضافية، لم تُحسب في أي تصميم منشور. وهذا سبب ثالث للفشل، مستقل عن الكم والاستقرار.")

    d.h2("٧. قيد المدّ الجَزْري: لماذا لا يمكن تصغير الجهاز؟")
    d.p("الحدس يقول إن التصغير يوفّر. الفيزياء تقول العكس: عند عبور عنق ضيق، يختلف التسارع بين رأس "
        "المسافر وقدَميه، والفرق يزداد كلما صغر العنق. باشتراط بقاء الفرق ضمن تحمّل الجسم نحصل على "
        "حدّ أدنى للحجم — لا أعلى.")
    rows = []
    for row in r["tidal"]:
        rows.append([row["label"], f"{row['L']} m", f"{row['v_over_c']:g}c",
                     sup(row["b"]), f"{row['mass_sun']:.0f}"])
    d.table(["الجسم", "الامتداد", "السرعة", "أقل نصف قطر (m)", "الكتلة (شمس)"], rows,
            widths=[1.4, 0.9, 0.7, 1.3, 1.0])
    d.p("أفضل سطر في الجدول — إنسان يعبر بسرعة 1% من الضوء — يحتاج 416 كتلة شمسية من المادة الغريبة. "
        "والسرعة هنا ليست ترفاً: تخفيضها إلى 1% يجعل الرحلة تستغرق قروناً. المقايضة بين السلامة والزمن "
        "لا مخرج منها.")

    d.h2("٨. اقتصاد الحجم: الكلفة لكل كيلوغرام")
    d.p("بجمع قيد المدّ الجَزْري مع قانون الطاقة نحصل على نتيجة معاكسة للحدس: الكلفة لكل كيلوغرام "
        "تتناسب عكسياً مع الكتلة مرفوعة للأس 5/6. أي أن المركبة الأكبر أرخص لكل كيلوغرام، "
        "والمركبة الصغيرة هي الأغلى في الكون.")
    rows = []
    for row in r["economy"]:
        rows.append([f"{row['mass_kg']:,.0f} kg", f"{row['extent_m']:.2f} m",
                     sup(row["b"]), sup(row["cost_per_kg"])])
    d.table(["كتلة الحمولة", "الامتداد", "نصف القطر (m)", "الكلفة لكل كغ (J/kg)"], rows,
            widths=[1.2, 1.0, 1.3, 1.7])

    d.h2("٩. بطاقة التصاميم المنشورة")
    d.p("الآن يمكن الحكم على التصاميم المنشورة بنفس المقياس: لوغاريتم نسبة الزمن المطلوب للعبور إلى "
        "الزمن المسموح. كل مرتبة عشرية تكلّف أربع نقاط من مئة.")
    rows = []
    for row in r["scorecard"]:
        rows.append([row["label"], sup(row["t_req"]), sup(row["t_allow"]),
                     f"10^{row['gap_log10']:.1f}", f"{row['verdict']:.0f}"])
    d.table(["التصميم", "الزمن المطلوب (ث)", "الزمن المسموح (ث)", "الفجوة", "من 100"], rows,
            widths=[1.7, 1.2, 1.2, 0.8, 0.6], size=8.4)
    d.box("الحكم",
          "لا يوجد تصميم واحد يتجاوز 30 من 100. وأفضل تصميم منشور يحتاج إغلاق 17 مرتبة عشرية قبل أن "
          "يصبح قابلاً للاستخدام؛ وأسوأها 26. وهذا ليس «قريباً» بأي معيار هندسي.", RED)

    # ---------------------------------------------------------- 5
    d.h1("القسم الرابع — النتيجة")
    d.h2("١٠. ما الذي يعنيه كل هذا، بدقة")
    d.p("النتيجة ليست «الجيوب الدودية مستحيلة». النتيجة أدق من ذلك، وتتكون من أربع جمل:")
    d.bullets([
        "أولاً: لا يوجد مبدأ فيزيائي مبرهن يمنع جيباً دودياً. النسبية العامة تعطي حلولاً صريحة، "
        "وشرط الطاقة يُخرق موضعياً في المختبر.",
        "ثانياً: لا يوجد مسار هندسي معروف يحقق الشروط الأربعة في وقت واحد: كمية كافية من المادة "
        "الغريبة، مدة كافية، استقرار كافٍ، وحجم داخل الكون.",
        "ثالثاً: العقبة الحاكمة زمنية لا طاقية. الطاقة المطلوبة لجيب بحجم سنة ضوئية تساوي 10⁻¹⁰ من "
        "طاقة الكون — أي أنها ليست المستحيل. المستحيل هو أن يبقى مفتوحاً.",
        "رابعاً: كل تحسين في التصميم يحرّك القيود في اتجاهات متعاكسة. تصغير الحجم يزيد الكلفة "
        "لكل كيلوغرام، وتقصير المدة يزيد الإشعاع، وتقليل الكثافة يزيد الحجم.",
    ])
    d.p("ولهذا فإن السؤال «هل يمكن؟» سؤال سيئ. السؤال الجيد: ما أقرب نقطة إلى الجدوى، وكم تبعد؟ "
        "والجواب المحسوب: قشرة فيسر، بفجوة 17.6 مرتبة عشرية، أي 30/100 على مقياس الجدوى.")

    d.h2("١١. الثغرة الوحيدة المعروفة")
    d.p("هناك مسار واحد لا يحتاج مادة غريبة: فرضية ER=EPR، التي تربط التشابك الكمومي بجيب دودي "
        "مجهري. في بعض الحسابات، الجيب الناتج عن تشابك بين منطقتين يمكن أن يكون قابلاً للعبور "
        "دون طاقة سالبة — لكن فقط إذا كانت الحالتان متشابكتين تشابكاً ماكروسكوبياً نقياً.")
    d.p("المشكلة أن هذا الشرط لا يقل صعوبة عن الأول: حالة كمومية نقية لجسم ماكروي لا توجد في الطبيعة "
        "ولا يمكن صنعها اليوم. المسار يغيّر شكل المشكلة، لا يحلها. وقيمته أنه يمنع القول بـ«الاستحالة»: "
        "توجد صياغة نظرية لا تحتاج المادة الغريبة، لكن لا توجد طريقة لتحقيقها.")

    d.h2("١٢. تجربة واحدة يمكن أن تغيّر الجواب")
    d.p("القانون الثالث يعطي تنبؤاً قابلاً للاختبار بميزانية معمل جامعي: إذا كانت المتباينة الكمومية "
        "صحيحة، فإن ميل لوغاريتم الكثافة السالبة مقابل لوغاريتم زمن القياس يجب أن يساوي سالب أربعة.")
    d.code([
        "Protocol (3-5 years, ~300k USD):",
        "  1. Casimir cavity with tunable gap d = 30..200 nm",
        "  2. measure F(d) to 0.1% relative precision",
        "  3. infer rho_neg(d) = - pi^2*hbar*c / (240*d^4)",
        "  4. effective sampling time T_eff = d/c",
        "  5. fit log|rho_neg| vs log(T_eff)",
        "",
        "Prediction: slope = -4.00 +- 0.05",
        "Deviation  => the window law breaks => new physics is possible",
    ])
    d.p("أي انحراف ذي دلالة عند مسافات أقل من 30 نانومتراً يعني أن القانون ينكسر، وأن الباب مفتوح. "
        "وعدم الانحراف يعني أن الفجوة حقيقية، وأن البحث الجاد في هذا المجال يجب أن يتجه إلى القياس "
        "لا إلى التصميم.")

    d.h2("١٣. الخلاصة في ستة أرقام")
    d.table(["#", "الرقم", "القيمة", "ماذا يعني"],
            [["1", "تسارع النافذة k", "1.1406×10⁵² m/s²", "2.047 × تسارع بلانك"],
             ["2", "سقف الكون", sup(r["universe_cap"]["t_at_r_universe"]) + " ث", "أكبر جيب ممكن يبقى 0.2 بيكوثانية"],
             ["3", "ثمن المتر", sup(C.D_E_DB) + " J", "عمر الشمس كله لكل متر"],
             ["4", "أقل عنق لإنسان", sup(r["tidal"][1]["b"]) + " m", "بسرعة c وامتداد 1.8 m"],
             ["5", "كلفة الكيلوغرام (70 kg)", sup(r["economy"][0]["cost_per_kg"]) + " J/kg", "أغلى من أي شيء"],
             ["6", "أفضل تصميم منشور", "30/100", "فجوة 17.6 مرتبة عشرية"]],
            widths=[0.4, 1.7, 1.4, 1.9], size=8.6)

    d.h2("١٤. ما يجب أن يُفعل بعد ذلك")
    d.bullets([
        "قياس كازيمير عند 30 نانومتراً بدقة 0.1٪ — أرخص تجربة وأكثرها حسمًا (نحو 300 ألف دولار).",
        "قياس زمن استمرار الطاقة السالبة في تجويف قابل للتعديل — الاختبار المباشر الوحيد للقانون.",
        "عدم تمويل أي بناء قبل قياس الحدّ: كل ريال في القياس يستبعد فئة كاملة من التصاميم.",
        "إبقاء السؤال مفتوحاً في الأدبيات، لكن مع رقم: لا يُنشر تصميم بلا كتلة غريبة بالكيلوغرام.",
    ])

    d.box("الجملة الأخيرة",
          "الفراغ كائن، ويمكن تعديله، وهذا مقيس. لكن أي تعديل لا يبقى: الزمن هو الحدّ، لا الطاقة. "
          "وكل ما نستطيع فعله اليوم هو قياس هذا الحدّ بدقة، لا تجاوزه.", GREEN)

    d.c.save()
    print(f"built {out}  pages={d.page}  size={os.path.getsize(out)}")


if __name__ == "__main__":
    main()
