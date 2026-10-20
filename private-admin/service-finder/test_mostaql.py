import unittest
from datetime import date
from scrape_clients import classify

OPEN_AR = ('إنشاء موقع إلكتروني\n'
           'نبحث عن مستقل محترف لتصميم وتنفيذ موقع إلكتروني عصري ومتجاوب. يرجى إرسال نماذج من أعمالك السابقة.\n'
           'حالة المشروع\nمفتوح\nالميزانية\n$100.00 - $250.00\nمدة التنفيذ\n3 أيام')
MOSTAQL = {'url': 'https://mostaql.com/project/1284608-example', 'buyer_section_only': True, 'captured_on': '2026-10-20'}


class MostaqlTests(unittest.TestCase):
    def test_mostaql_open_arabic(self):
        r = classify(OPEN_AR, MOSTAQL, date(2026, 10, 20))
        self.assertEqual(r['status'], 'platform_reports_open_review')
        self.assertEqual(r['budget_evidence'], ['الميزانية $100.00 - $250.00'])
        self.assertIn('مفتوح', r['availability_evidence'])
        self.assertEqual(r['deadline_dates'], [])
        self.assertFalse(r['verified'])

    def test_mostaql_samples_are_qualification_evidence(self):
        self.assertEqual(classify(OPEN_AR, MOSTAQL, date(2026, 10, 20))['fit'], 'requirements_review_needed')

    def test_mostaql_closed_with_diacritic(self):
        text = OPEN_AR.replace('\nمفتوح\n', '\nمُغلق\n')
        r = classify(text, MOSTAQL, date(2026, 10, 20))
        self.assertEqual(r['status'], 'closed_or_cancelled')
        self.assertIn('مُغلق', r['availability_evidence'])

    def test_mostaql_unscoped_not_promoted(self):
        r = classify(OPEN_AR, {'url': 'https://mostaql.com/project/1284608-example'}, date(2026, 10, 20))
        self.assertEqual(r['status'], 'needs_deadline_review')
        self.assertEqual(r['availability_evidence'], [])

    def test_freelancer_awarded_is_closed(self):
        s = {'url': 'https://www.freelancer.com/projects/web-design/example', 'buyer_section_only': True, 'captured_on': '2026-10-20'}
        r = classify('Website Design\n$250-750 USD\nIn Progress\nI need a website for my consulting business.\nAwarded to:', s, date(2026, 10, 20))
        self.assertEqual(r['status'], 'closed_or_cancelled')


if __name__ == '__main__':
    unittest.main()
