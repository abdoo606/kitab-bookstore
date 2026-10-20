#!/usr/bin/env python3
"""Evidence-first service request triage. Never auto-sends or labels a lead verified."""
import argparse
import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

UA = 'ServiceRequestResearch/1.0'
MAX_BYTES = 5_000_000
REQUEST = re.compile(r'request for proposals|\brfp\b|inviting.{0,90}proposals|seeking.{0,100}(?:vendor|partner|agency|freelancer)|need.{0,60}(?:website|developer)|مطلوب.{0,60}(?:موقع|مبرمج)|طلب عروض|نبحث عن.{0,80}(?:مستقل|مطوّر|مطور|مبرمج|مصمم)|نحتاج.{0,60}(?:موقع|تنفيذ|إنشاء)|أريد.{0,60}(?:موقع|إنشاء موقع|تصميم موقع)', re.I)
SERVICE = re.compile(r'website|web design|web development|redesign|software|wordpress|api integration|موقع|برمج', re.I)
JOB = re.compile(r'full.time position|annual salary|employee benefits|apply for this job|job description|employment opportunity|راتب شهري|وظيفة', re.I)
SELLER = re.compile(r'our portfolio|our case studies|hire me|we offer web|our web design services|معرض أعمال|نقدم خدمات', re.I)
DEADLINE = re.compile(r'proposal.{0,45}(?:due|deadline)|(?:proposals?|responses?|bids?).{0,65}(?:submitted|received).{0,100}(?:by|before|later than)|آخر موعد.{0,30}(?:تقديم|عروض)', re.I)
DATE = re.compile(r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:st|nd|rd|th)?\s*,?\s*20\d{2}\b|\b20\d{2}-\d{2}-\d{2}\b', re.I)
EMAIL = re.compile(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}')
LINK = re.compile(r'\brfp\b|request.for.proposal|solicitation|procurement|website.redesign|طلب.عروض', re.I)


def canonical(url):
    p = urlsplit(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Only unauthenticated HTTP(S) source URLs supported')
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
         if not k.lower().startswith('utm_') and k not in ('fbclid', 'gclid')]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or '/', urlencode(sorted(q)), ''))


def clean_lines(text):
    return [' '.join(re.sub(r'[*_#]', '', x).split()) for x in text.splitlines() if x.strip()]


def dates_in(text):
    found = set()
    for match in DATE.findall(text):
        value = re.sub(r'(\d)(st|nd|rd|th)', r'\1', match, flags=re.I).replace(',', '')
        for fmt in ('%B %d %Y', '%Y-%m-%d'):
            try:
                found.add(datetime.strptime(value, fmt).date().isoformat())
                break
            except ValueError:
                pass
    return sorted(found)


def classify(text, source, as_of):
    lines = clean_lines(text)
    full = '\n'.join(lines)
    demand = [x for x in lines if REQUEST.search(x)]
    service = bool(SERVICE.search(full))
    # Marketplace excerpts must be explicitly scoped to the buyer section,
    # otherwise bidder advertisements can contaminate the evidence.
    host = urlsplit(source['url']).hostname or ''
    path = urlsplit(source['url']).path
    marketplace = (((host == 'freelancer.com' or host.endswith('.freelancer.com')) and '/projects/' in path)
                   or (host in ('mostaql.com', 'www.mostaql.com') and '/project/' in path))
    buyer_section = marketplace and source.get('buyer_section_only') is True
    plain = [re.sub(r'[\u064b-\u0652]', '', x) for x in lines]  # strip Arabic diacritics, e.g. مُغلق -> مغلق
    closed_states = ('in progress', 'closed', 'awarded to', 'مغلق', 'اكتمل', 'قيد التنفيذ')
    open_line = next((x for x, p in zip(lines, plain) if re.fullmatch(r'Open for bidding', x, re.I) or p == 'مفتوح'), None) if buyer_section else None
    closed_line = next((x for x, p in zip(lines, plain) if p.rstrip(':').lower() in closed_states), None) if buyer_section else None
    availability = [x for x, p in zip(lines, plain) if re.fullmatch(r'Open for bidding|Ends in \d+ days?', x, re.I) or p.rstrip(':').lower() in ('مفتوح',) + closed_states] if buyer_section else []
    if open_line and service:
        demand.append(open_line)
    deadline_evidence, deadlines = [], set()
    for i, line in enumerate(lines):
        if DEADLINE.search(line):
            block = line
            if not dates_in(block) and i + 1 < len(lines):
                block += ' ' + lines[i + 1]
            ds = dates_in(block)
            if ds:
                deadlines.update(ds)
                deadline_evidence.append(block[:700])
    dates = sorted(deadlines)
    status = 'not_service_request'
    if service and demand:
        status = 'needs_deadline_review'
        if len(dates) > 1:
            status = 'conflicting_deadlines_review'
        elif dates:
            d = date.fromisoformat(dates[0])
            status = 'expired' if d < as_of else ('due_today_time_review' if d == as_of else 'future_deadline_needs_review')
    elif JOB.search(full):
        status = 'employment_excluded'
    elif SELLER.search(full):
        status = 'seller_or_portfolio_excluded'
    # Recruitment language wins over generic "need a developer" signals.
    if JOB.search(full) and not re.search(r'request for proposals|\brfp\b|طلب عروض', full, re.I):
        status = 'employment_excluded'
    if re.search(r'(?:this (?:rfp|solicitation)|procurement) (?:is |has been )?(?:cancelled|canceled|closed)', full, re.I):
        status = 'closed_or_cancelled'
    if closed_line and status != 'not_service_request':
        # Platform reports the post awarded/in-progress/closed; bidding is not available.
        status = 'closed_or_cancelled'
    if buyer_section and status == 'needs_deadline_review' and open_line:
        status = ('platform_reports_open_review' if source.get('captured_on', '')[:10] == as_of.isoformat()
                  else 'stale_platform_snapshot_review')
    budgets, used = [], set()
    for i, x in enumerate(lines):
        if re.search(r'budget|ميزانية', x, re.I):
            block = x
            if not re.search(r'\$|USD|EUR|GBP|INR|₹|دولار|يورو', block) and i + 1 < len(lines):
                block += ' ' + lines[i + 1]  # e.g. Mostaql puts the amount on the line after الميزانية
                used.add(i + 1)
            if re.search(r'\$|USD|EUR|GBP|INR|₹|دولار|يورو', block):
                budgets.append(block)
    if buyer_section:
        budgets += [x for j, x in enumerate(lines) if j not in used and re.fullmatch(r'[$€£₹]\s*[\d,.]+\s*[-–]\s*[$€£₹]?\s*[\d,.]+(?:\s*(?:USD|EUR|GBP|INR))?', x)]
    budgets = list(dict.fromkeys(budgets))
    emails = sorted(set(EMAIL.findall(full)))
    contacts = [x for x in lines if EMAIL.search(x)]
    blockers = [x for x in lines if re.search(r'client references|three.{0,40}case studies|insurance|years.{0,25}experience|federal|in.house expertise|mandatory|samples of.{0,30}work|past work|strong portfolio|proven experience|شروط|خبرة|نماذج.{0,25}أعمال|أعمالك السابقة|أعمال سابقة', x, re.I)]
    url = canonical(source['url'])
    return dict(id='S-' + hashlib.sha256(url.encode()).hexdigest()[:12],
                organization=source.get('organization', ''), source_url=url,
                source_kind=source.get('source_kind', 'unverified'),
                as_of=as_of.isoformat(), status=status, verified=False,
                deadline_dates=dates, deadline_evidence=deadline_evidence,
                availability_evidence=availability,
                request_evidence=demand[:5], budget_evidence=budgets[:5],
                contact_candidates=emails, contact_evidence=contacts[:10],
                qualification_evidence=blockers[:12],
                fit='requirements_review_needed' if blockers else 'not_assessed',
                payment_currency_confirmed='', country='', estimated_value='',
                source_sha256=hashlib.sha256(text.encode()).hexdigest(),
                retrieval_mode=source.get('retrieval_mode', ''),
                captured_on=source.get('captured_on', ''),
                content_scope=source.get('content_scope', 'full_response'),
                outreach_status=source.get('outreach_status', 'not_sent'),
                next_action='Review full source, amendments, eligibility, contact role and timezone before proposing. No automatic outreach.')


class Fetcher:
    def __init__(self, delay=2, allowed_hosts=None):
        self.session = requests.Session()
        self.session.headers['User-Agent'] = UA
        self.delay, self.allowed_hosts = delay, allowed_hosts
        self.robots, self.last = {}, {}

    def validate(self, url):
        url = canonical(url)
        host = urlsplit(url).hostname
        if self.allowed_hosts is not None and host not in self.allowed_hosts:
            raise ValueError('Host outside configured network allowlist: ' + host)
        for info in socket.getaddrinfo(host, None):
            if not ipaddress.ip_address(info[4][0]).is_global:
                raise ValueError('Non-public target denied')
        return url

    def raw(self, url):
        url = self.validate(url)
        host = urlsplit(url).hostname
        time.sleep(max(0, self.delay - (time.monotonic() - self.last.get(host, 0))))
        self.last[host] = time.monotonic()
        with self.session.get(url, timeout=(10, 25), stream=True, allow_redirects=False) as r:
            if 300 <= r.status_code < 400:
                raise ValueError('Redirect needs explicit reviewed seed: ' + urljoin(url, r.headers.get('Location', '')))
            r.raise_for_status()  # Stop on 403/429; no evasion or aggressive retries.
            data = bytearray()
            for chunk in r.iter_content(65536):
                data.extend(chunk)
                if len(data) > MAX_BYTES:
                    raise ValueError('Response exceeds 5 MB cap')
            return bytes(data), r.headers.get('Content-Type', '').lower()

    def get(self, url):
        url = self.validate(url)
        p = urlsplit(url)
        origin = p.scheme + '://' + p.netloc
        if origin not in self.robots:
            robot_url = origin + '/robots.txt'
            rp = RobotFileParser()
            try:
                data, _ = self.raw(robot_url)
                rp.parse(data.decode('utf-8', errors='replace').splitlines())
            except requests.HTTPError as e:
                if e.response.status_code not in (404, 410):
                    raise
                rp.parse([])
            self.robots[origin] = rp
        rp = self.robots[origin]
        if not rp.can_fetch(UA, url):
            raise ValueError('robots.txt disallows this URL')
        self.delay = max(self.delay, rp.crawl_delay(UA) or 0)
        data, mime = self.raw(url)
        if 'application/pdf' in mime:
            reader = PdfReader(io.BytesIO(data))
            if len(reader.pages) > 40:
                raise ValueError('PDF exceeds 40-page cap; manual review needed')
            text = '\n'.join(p.extract_text() or '' for p in reader.pages)
            links = []
        elif 'text/html' in mime:
            soup = BeautifulSoup(data, 'html.parser')
            links = []
            for a in soup.find_all('a', href=True):
                if LINK.search(a.get_text(' ', strip=True) + ' ' + a['href']):
                    try:
                        link = canonical(urljoin(url, a['href']))
                        if urlsplit(link).netloc == p.netloc:
                            links.append(link)
                    except ValueError:
                        pass
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            text = (soup.find('main') or soup.find('article') or soup).get_text('\n', strip=True)
        else:
            raise ValueError('Unsupported Content-Type: ' + mime)
        if len(text.strip()) < 40:
            raise ValueError('Empty/short page or scanned PDF; no usable extraction')
        return text, sorted(set(links))


def safe_cell(value):
    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)
    s = str(value)
    return "'" + s if s.lstrip().startswith(('=', '+', '-', '@')) else s


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sources', type=Path, required=True)
    p.add_argument('--out', type=Path, default=Path('results'))
    p.add_argument('--mode', choices=['snapshot', 'live'], default='snapshot')
    p.add_argument('--as-of', type=date.fromisoformat, default=date.today())
    p.add_argument('--max-pages', type=int, default=30)
    p.add_argument('--depth', type=int, choices=[0, 1, 2], default=1)
    p.add_argument('--allowed-hosts', help='Optional comma-separated network allowlist; exact hosts')
    args = p.parse_args()
    if args.max_pages < 1:
        p.error('--max-pages must be positive')
    seeds = json.loads(args.sources.read_text(encoding='utf-8'))
    queue = [(s, 0) for s in seeds]
    seen, rows, errors = set(), [], []
    fetcher = Fetcher(allowed_hosts=set(args.allowed_hosts.split(',')) if args.allowed_hosts is not None else None)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / 'evidence').mkdir(exist_ok=True)
    while queue and len(seen) < args.max_pages:
        source, depth = queue.pop(0)
        try:
            url = canonical(source['url'])
            if url in seen:
                continue
            seen.add(url)
            source = dict(source, retrieval_mode=args.mode)
            if args.mode == 'snapshot':
                text = (args.sources.parent / source['snapshot']).read_text(encoding='utf-8')
                links = []
            else:
                text, links = fetcher.get(url)
                source['captured_on'] = datetime.now(timezone.utc).isoformat()
                source['content_scope'] = 'full_response'
            row = classify(text, source, args.as_of)
            rows.append(row)
            (args.out / 'evidence' / (row['id'] + '.txt')).write_text(text, encoding='utf-8')
            if depth < args.depth:
                for link in links:
                    # Child pages do not inherit a verified buyer identity or contact status.
                    queue.append(({'url': link, 'source_kind': 'discovered_unverified'}, depth + 1))
        except Exception as e:
            errors.append({'url': source.get('url', ''), 'error_type': type(e).__name__, 'error': str(e)})
    (args.out / 'opportunities.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    fields = list(rows[0]) if rows else ['id', 'source_url', 'status']
    with (args.out / 'opportunities.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: safe_cell(v) for k, v in row.items()} for row in rows)
    summary = {'mode': args.mode, 'as_of': args.as_of.isoformat(), 'attempted': len(seen),
               'records': len(rows), 'errors': errors, 'remaining_queue': len(queue),
               'statuses': {s: sum(r['status'] == s for r in rows) for s in sorted({r['status'] for r in rows})},
               'warning': 'Triage only: not verified clients, not guaranteed paid work. Imported excerpts may omit requirements.'}
    (args.out / 'run.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 2 if errors and not rows else 0


if __name__ == '__main__':
    raise SystemExit(main())
