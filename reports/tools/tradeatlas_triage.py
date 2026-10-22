#!/usr/bin/env python3
"""
TradeAtlas zip triage — يفحص نسخ TradeAtlas ويرتّبها حسب الصلاحية الفعلية.

المشكلة التي يحلّها: نسخ v40/41/42 (Core) حجمها 0.7% من v35، ولا أحد يعرف
إن كانت patch فوق v35 أم نسخ ناقصة. السكربت لا يخمّن: يفك، يشغّل، ويقيس.

الاستخدام:
    python3 reports/tools/tradeatlas_triage.py ~/Downloads/TradeAtlas-*.zip
    python3 reports/tools/tradeatlas_triage.py ~/Downloads --timeout 90 --json out.json

ما يفعله لكل ملف:
  1. zipfile.testzip()        -> سلامة الأرشيف
  2. فك في مجلد مؤقت           -> يعزل كل نسخة
  3. جرد المحتوى              -> عدد الملفات، هل فيه أصول/بيانات/واجهة
  4. تشغيل الاختبارات          -> python3 -m unittest discover (بدون شبكة)
  5. تصنيف                    -> FULL / CORE-PATCH / BROKEN

لا يعدّل أي ملف أصلي. لا يستخدم الشبكة. كل شيء داخل tempfile.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass, field, asdict

ASSET_EXT = {
    ".csv", ".parquet", ".db", ".sqlite", ".sqlite3", ".json", ".h5", ".feather",
    ".pkl", ".npy", ".npz", ".xlsx", ".html", ".css", ".js", ".woff", ".woff2",
    ".ttf", ".png", ".jpg", ".svg",
}
TEST_RE = re.compile(r"(^test_.*\.py$)|(_test\.py$)", re.IGNORECASE)
FIELD_RE = re.compile(r"(v\d{1,2})", re.IGNORECASE)
ASSERT_RE = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)", re.MULTILINE)


@dataclass
class Result:
    zip: str
    name: str
    version: int | None = None
    size_mb: float = 0.0
    zip_ok: bool = False
    files: int = 0
    py_files: int = 0
    test_files: int = 0
    declared_tests: int | None = None
    discovered_tests: int = 0
    tests_run: int = 0
    tests_ok: bool = False
    has_assets: bool = False
    seconds: float = 0.0
    verdict: str = "UNKNOWN"
    note: str = ""
    tail: str = ""
    rank: float = field(default=0.0, compare=False)


def declared_test_count(name: str) -> int | None:
    """v40-authentic-32-tests / 94of94 / 52_tests -> العدد المُعلن في الاسم"""
    m = re.search(r"(\d{1,3})\s*(?:of\s*\d{1,3})?\s*[-_]?tests?", name, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d{1,3})\s*of\s*(\d{1,3})", name)
    if m:
        return int(m.group(2))
    return None


def version_of(name: str) -> int | None:
    m = FIELD_RE.search(name)
    return int(m.group(1)[1:]) if m else None


def count_asserts(root: str) -> int:
    n = 0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            if TEST_RE.search(f):
                try:
                    with open(os.path.join(dirpath, f), encoding="utf-8", errors="ignore") as fh:
                        n += len(ASSERT_RE.findall(fh.read()))
                except OSError:
                    pass
    return n


def run_tests(root: str, timeout: int) -> tuple[int, bool, str]:
    """يشغّل الاختبارات في جذر النسخة. يرجع (عدد المُنفَّذ, نجح؟, مقتطف من المخرجات)."""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    # جرّب discover أولاً، ثم fallback إلى تشغيل كل ملف اختبار مباشرة.
    attempts = [["-m", "unittest", "discover", "-v"]]
    for dirpath, _d, files in os.walk(root):
        for f in sorted(files):
            if TEST_RE.search(f) and f.endswith(".py"):
                rel = os.path.relpath(os.path.join(dirpath, f), root)
                attempts.append([rel[:-3].replace(os.sep, ".")])
    for args in attempts:
        try:
            p = subprocess.run(
                [sys.executable, *args], cwd=root, env=env, timeout=timeout,
                capture_output=True, text=True,
            )
        except subprocess.TimeoutExpired:
            return 0, False, f"TIMEOUT after {timeout}s"
        out = (p.stdout or "") + (p.stderr or "")
        ran = re.search(r"Ran (\d+) tests?", out)
        if ran:
            n = int(ran.group(1))
            ok = p.returncode == 0 and "OK" in out
            if n:
                return n, ok, out[-1200:]
        if "NO TESTS RAN" in out.upper() or not ran:
            continue
    return 0, False, "no runnable tests found"


def triage(path: str, timeout: int, keep: str | None = None) -> Result:
    name = os.path.basename(path)
    r = Result(zip=path, name=name)
    r.version = version_of(name)
    r.declared_tests = declared_test_count(name)
    try:
        r.size_mb = round(os.path.getsize(path) / 1_048_576, 2)
    except OSError:
        r.note = "unreadable file"
        r.verdict = "BROKEN"
        return r

    if not zipfile.is_zipfile(path):
        r.note = "not a zip archive"
        r.verdict = "BROKEN"
        return r

    with zipfile.ZipFile(path) as zf:
        r.zip_ok = zf.testzip() is None
        if not r.zip_ok:
            r.note = "corrupt member inside archive"
            r.verdict = "BROKEN"
            return r
        names = zf.namelist()
        r.files = len([n for n in names if not n.endswith("/")])
        r.has_assets = any(os.path.splitext(n)[1].lower() in ASSET_EXT for n in names)

        tmp = tempfile.mkdtemp(prefix="ta-triage-")
        try:
            zf.extractall(tmp)
            root = tmp
            entries = [e for e in os.listdir(tmp) if not e.startswith("__MACOSX")]
            if len(entries) == 1 and os.path.isdir(os.path.join(tmp, entries[0])):
                root = os.path.join(tmp, entries[0])

            for dirpath, _d, files in os.walk(root):
                for f in files:
                    if f.endswith(".py"):
                        r.py_files += 1
                    if TEST_RE.search(f):
                        r.test_files += 1

            r.discovered_tests = count_asserts(root)
            import time
            t0 = time.time()
            r.tests_run, r.tests_ok, r.tail = run_tests(root, timeout)
            r.seconds = round(time.time() - t0, 1)

            if keep:
                os.makedirs(keep, exist_ok=True)
                dest = os.path.join(keep, re.sub(r"[^\w.\-]+", "_", name[:-4]))
                if os.path.exists(dest):
                    shutil.rmtree(dest)
                shutil.copytree(root, dest)
                r.note = f"extracted -> {dest}"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # التصنيف — الترتيب مهم: النجاح الفعلي هو الحكم، لا الحجم.
    if not r.zip_ok:
        r.verdict = "BROKEN"
    elif r.py_files == 0:
        r.verdict = "BROKEN"
        r.note = (r.note + " | " if r.note else "") + "no python code"
    elif r.tests_run and r.tests_ok:
        r.verdict = "FULL"
        if r.size_mb < 5 and not r.has_assets:
            r.note = (r.note + " | " if r.note else "") + "code-only: صغير بلا أصول، تأكد أنه يشمل التشغيل الكامل"
    elif r.tests_run:
        r.verdict = "PARTIAL"
        r.note = (r.note + " | " if r.note else "") + "اختبارات تعمل لكن هناك فشل — اقرأ tail"
    else:
        r.verdict = "CORE-PATCH"
        r.note = (r.note + " | " if r.note else "") + "لا اختبارات قابلة للتشغيل: يحتاج build كامل كأساس"

    # ترتيب: الأفضل = ينجح + أكبر تغطية + أحدث إصدار
    r.rank = (
        (1000 if r.verdict == "FULL" else 300 if r.verdict == "PARTIAL" else 0)
        + min(r.tests_run, 300)
        + (r.version or 0)
    )
    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="فحص وترتيب نسخ TradeAtlas")
    ap.add_argument("paths", nargs="+", help="ملفات zip أو مجلد يحتويها")
    ap.add_argument("--timeout", type=int, default=120, help="ثوانٍ كحد أقصى لكل نسخة")
    ap.add_argument("--json", metavar="FILE", help="حفظ النتائج JSON")
    ap.add_argument("--keep", metavar="DIR", help="نسخ النسخ المستخرجة إلى هذا المجلد للمراجعة")
    args = ap.parse_args()

    targets: list[str] = []
    for p in args.paths:
        if os.path.isdir(p):
            targets += [
                os.path.join(p, f) for f in sorted(os.listdir(p))
                if f.lower().endswith(".zip")
            ]
        elif os.path.exists(p):
            targets.append(p)
        else:
            print(f"!! not found: {p}", file=sys.stderr)

    if not targets:
        print("لا توجد ملفات zip للفحص.", file=sys.stderr)
        return 2

    results = []
    for path in targets:
        print(f"→ {os.path.basename(path)} ...", end="", flush=True)
        r = triage(path, args.timeout, args.keep)
        print(f" {r.verdict} ({r.tests_run} tests)")
        results.append(r)

    results.sort(key=lambda r: r.rank, reverse=True)

    print("\n" + "=" * 108)
    print(f"{'#':<3}{'الملف':<52}{'MB':>7}{'Py':>5}{'Tests':>7}{'OK':>4}  {'الحكم'}")
    print("=" * 108)
    for i, r in enumerate(results, 1):
        name = (r.name[:49] + "...") if len(r.name) > 52 else r.name
        ok = "✓" if r.tests_ok else "✗"
        print(f"{i:<3}{name:<52}{r.size_mb:>7.1f}{r.py_files:>5}{r.tests_run:>7}{ok:>4}  {r.verdict}")
        if r.declared_tests and r.declared_tests != r.tests_run:
            print(f"   ⚠️ الاسم يدّعي {r.declared_tests} اختباراً، المُنفَّذ {r.tests_run}")
        if r.note:
            print(f"   · {r.note}")
    print("=" * 108)

    full = [r for r in results if r.verdict == "FULL"]
    if full:
        best = full[0]
        print(f"\n✅ الأساس الموصى به: {best.name}  ({best.size_mb} MB · {best.tests_run} اختبار ناجح)")
        patches = [r for r in results if r.verdict == "CORE-PATCH"]
        if patches:
            print("   ثم ادمج انتقائياً فوقه: " + ", ".join(p.name for p in patches))
            print("   (قبل الدمج: تأكد أن ملفات الـ patch لا تستبدل ملفات v35 بالكامل)")
    else:
        print("\n❌ لا توجد نسخة كاملة تنجح اختباراتها. لا تدمج شيئاً قبل إصلاح الأساس.")

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump([asdict(r) for r in results], fh, ensure_ascii=False, indent=2)
        print(f"\nJSON: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
