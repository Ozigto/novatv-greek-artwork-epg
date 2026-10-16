import unittest
from zoneinfo import ZoneInfo
from datetime import datetime
import ert_schedule


class ErtScheduleTest(unittest.TestCase):
    def test_parses_timed_official_programme_and_image(self):
        html = """
        <html><article data-start-time="2026-10-16 09:00:00+0300"
                      data-end-time="2026-10-16 10:00:00+0300">
        <img src="/wp-content/uploads/2026/10/ertshow.jpg" alt="Πρωίαν σε Είδον"/>
        <strong class="section-title">Πρωίαν σε Είδον</strong>
        <span class="fs-ms">Ελληνικό πρόγραμμα</span>
        </article></html>"""
        events, pictures = ert_schedule.parse_page(
            html, "https://www.ert.gr/tv/program/ert1/", "ert1")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["channel_id"], "ert-ert1")
        self.assertEqual(events[0]["title"], "Πρωίαν σε Είδον")
        self.assertEqual(events[0]["actual_time"], "2026-10-16T09:00:00+03:00")
        self.assertTrue(pictures["ΠΡΩΙΑΝ ΣΕ ΕΙΔΟΝ"].endswith("/2026/10/ertshow.jpg"))

    def test_skips_malformed_show_and_non_broadcaster_image(self):
        html = """
        <article data-start-time="bad">
        <strong class="section-title">Εκπομπή</strong>
        </article>
        <article data-start-time="2026-10-16T11:00:00+03:00"
                 data-end-time="2026-10-16T12:00:00+03:00">
        <strong class="section-title">Αληθινή σειρά</strong>
        <img src="https://bad.example.com/poster.jpg"/>
        </article>"""
        events, images = ert_schedule.parse_page(html,
            "https://www.ert.gr/tv/program/ert1/", "ert1")
        self.assertEqual(len(events), 1)
        self.assertEqual(len(images), 0)


if __name__ == "__main__":
    unittest.main()
