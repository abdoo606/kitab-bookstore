import unittest
from datetime import date
from unittest.mock import patch
from scrape_clients import classify, canonical, safe_cell, Fetcher

TODAY = date(2026, 10, 20)
SOURCE = {'url': 'https://example.org/rfp', 'organization': 'Test fixture'}

def result(text):
    return classify(text, SOURCE, TODAY)

class ClassificationTests(unittest.TestCase):
    def test_future(self):
        r = result('Request for Proposals: website redesign\nProposals due: November 2, 2026')
        self.assertEqual(r['status'], 'future_deadline_needs_review')
        self.assertFalse(r['verified'])
    def test_expired_not_launch(self):
        self.assertEqual(result('RFP website redesign\nProposals due: October 12, 2026\nLaunch: March 1, 2027')['status'], 'expired')
    def test_questions_not_deadline(self):
        r = result('RFP website\nQuestions due: October 15, 2026\nProposals due: November 2, 2026')
        self.assertEqual(r['deadline_dates'], ['2026-11-02'])
    def test_conflict(self):
        self.assertEqual(result('RFP website\nProposals due: November 2, 2026\nProposal submission deadline: November 9, 2026')['status'], 'conflicting_deadlines_review')
    def test_missing_deadline(self):
        self.assertEqual(result('Request for Proposals website redesign')['status'], 'needs_deadline_review')
    def test_same_day(self):
        self.assertEqual(result('RFP website\nProposals due: October 20, 2026')['status'], 'due_today_time_review')
    def test_employment(self):
        self.assertEqual(result('We need a developer for our website. Full-time position. Employee benefits.')['status'], 'employment_excluded')
    def test_seller(self):
        self.assertEqual(result('Our portfolio. We offer web design services.')['status'], 'seller_or_portfolio_excluded')
    def test_no_budget_invention(self):
        r = result('RFP website\nWe have a budget. Contact info@example.org')
        self.assertEqual(r['budget_evidence'], [])
        self.assertEqual(r['contact_candidates'], ['info@example.org'])
        self.assertEqual(r['estimated_value'], '')
    def test_budget_is_evidence(self):
        self.assertEqual(result('RFP website\nAnticipated budget $20,000 to $25,000')['budget_evidence'], ['Anticipated budget $20,000 to $25,000'])
    def test_qualifications(self):
        self.assertEqual(result('RFP website\nThree client references and insurance required.')['fit'], 'requirements_review_needed')
    def test_cancelled(self):
        self.assertEqual(result('RFP website\nThis RFP is cancelled\nProposals due: November 2, 2026')['status'], 'closed_or_cancelled')
    def test_split_deadline(self):
        self.assertEqual(result('RFP website\nProposal submission deadline\nNovember 9, 2026')['deadline_dates'], ['2026-11-09'])
    def test_canonical(self):
        self.assertEqual(canonical('https://EXAMPLE.org/rfp?utm_source=x&id=2#x'), 'https://example.org/rfp?id=2')
    def test_no_auth_urls(self):
        with self.assertRaises(ValueError):
            canonical('https://user:password@example.org/rfp')
    def test_csv_injection(self):
        self.assertEqual(safe_cell('=HYPERLINK("evil")')[0], "'")
        self.assertEqual(safe_cell(' \t+SUM(1,2)')[0], "'")
    def test_network_allowlist(self):
        with self.assertRaisesRegex(ValueError, 'allowlist'):
            Fetcher(allowed_hosts={'github.com'}).validate('https://example.org/')
    def test_private_address(self):
        with patch('socket.getaddrinfo', return_value=[(2, 1, 6, '', ('127.0.0.1', 80))]):
            with self.assertRaisesRegex(ValueError, 'Non-public'):
                Fetcher().validate('https://example.org/')
    def test_arabic_request_no_english_date(self):
        self.assertEqual(result('مطلوب مبرمج لبناء موقع')['status'], 'needs_deadline_review')

class FetchTests(unittest.TestCase):
    def test_robots_denial(self):
        f = Fetcher(delay=0)
        with patch.object(f, 'validate', side_effect=lambda x: x), patch.object(f, 'raw', return_value=(b'User-agent: *\nDisallow: /', 'text/plain')) as raw:
            with self.assertRaisesRegex(ValueError, 'robots'):
                f.get('https://example.org/rfp')
            self.assertEqual(raw.call_count, 1)

    def test_html_and_link_scope(self):
        f = Fetcher(delay=0)
        html = b'<main><h1>Request for Proposals website redesign</h1><p>Proposals due: November 2, 2026</p><a href="/rfp/details">RFP details</a><a href="https://other.org/rfp">RFP</a></main><footer>wrong@example.org</footer>'
        with patch.object(f, 'validate', side_effect=lambda x: x), patch.object(f, 'raw', side_effect=[(b'User-agent: *\nAllow: /', 'text/plain'), (html, 'text/html')]):
            text, links = f.get('https://example.org/rfp')
            self.assertNotIn('wrong@example.org', text)
            self.assertEqual(links, ['https://example.org/rfp/details'])

    def test_unsupported_type(self):
        f = Fetcher(delay=0)
        with patch.object(f, 'validate', side_effect=lambda x: x), patch.object(f, 'raw', side_effect=[(b'User-agent: *\nAllow: /', 'text/plain'), (b'image', 'image/png')]):
            with self.assertRaisesRegex(ValueError, 'Unsupported'):
                f.get('https://example.org/rfp')

if __name__ == '__main__':
    unittest.main()
