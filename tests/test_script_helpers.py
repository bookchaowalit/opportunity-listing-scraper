"""Offline tests for helper functions in the root scrape_* scripts."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import scrape_fb_local


class EmailPrivacyTests(unittest.TestCase):
    def test_mask_email_hides_local_part(self):
        self.assertEqual(
            scrape_fb_local.mask_email("jane.doe@company.co.th"), "j***@company.co.th"
        )
        self.assertEqual(scrape_fb_local.mask_email("not-an-email"), "***")

    def test_contact_data_stays_inside_repository(self):
        self.assertEqual(scrape_fb_local.DATA_DIR, ROOT / "data")

    def test_extract_emails_skips_generic_and_placeholder_addresses(self):
        text = "Send CV to hr@acme.com or jane@acme.com, see test@example.com"
        self.assertEqual(
            scrape_fb_local.extract_emails_from_text(text), ["jane@acme.com"]
        )


if __name__ == "__main__":
    unittest.main()
