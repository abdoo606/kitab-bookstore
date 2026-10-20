import unittest
from datetime import date
from scrape_clients import classify
class MarketplaceTests(unittest.TestCase):
 def test_buyer_open(self):
  s={'url':'https://www.freelancer.com/projects/web-design/example','buyer_section_only':True,'captured_on':'2026-10-20'}
  r=classify('Website Design\n$250-750 USD\nOpen for bidding\nEnds in 6 days',s,date(2026,10,20))
  self.assertEqual(r['status'],'platform_reports_open_review')
  self.assertEqual(r['budget_evidence'],['$250-750 USD'])
  self.assertEqual(r['deadline_dates'],[])
  self.assertFalse(r['verified'])
 def test_unscoped_page_not_promoted(self):
  r=classify('Website Design\nOpen for bidding',{'url':'https://www.freelancer.com/projects/web-design/example'},date(2026,10,20))
  self.assertEqual(r['status'],'not_service_request')
 def test_stale_snapshot(self):
  s={'url':'https://www.freelancer.com/projects/web-design/example','buyer_section_only':True,'captured_on':'2026-10-19'}
  self.assertEqual(classify('Website Design\nOpen for bidding',s,date(2026,10,20))['status'],'stale_platform_snapshot_review')
