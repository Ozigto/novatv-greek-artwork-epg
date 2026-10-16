"""Offline regression checks (do not depend on Digea availability)."""
import gzip
import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET

import generate_epg as g


class XMLTVTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 16, 21, tzinfo=ZoneInfo("Europe/Athens"))
        self.channels = [
            {"id": "101", "name": "ALPHA", "img": "/logos/alpha.png"},
            {"id": "102", "name": "MEGA"},
        ]
        self.events = [
            {"channel_id": "101", "actual_time": "2026-10-16T21:00:00",
             "end_time": "2026-10-16T22:00:00", "title": "Deal", "synopsis": "Παιχνίδι"},
            {"channel_id": "102", "actual_time": "2026-10-16T21:00:00",
             "end_time": "2026-10-16T22:00:00", "title": "Άλλη σειρά"},
        ]

    def test_real_artwork_is_programme_level(self):
        xml, meta = g.build_xml(self.channels, self.events,
                                {g.normalize_title("Deal"): g.STATIC_ART["DEAL"]}, self.now)
        root = ET.fromstring(xml)
        self.assertEqual(meta["channels"], 2)
        self.assertEqual(meta["programmes"], 2)
        self.assertEqual(meta["programmes_with_artwork"], 1)
        self.assertEqual(root.find(".//programme[@channel='digea-101']/icon").get("src"),
                         g.STATIC_ART["DEAL"])
        self.assertIsNone(root.find(".//programme[@channel='digea-102']/icon"))
        self.assertIsNotNone(root.find(".//channel[@id='digea-101']/display-name[.='ALPHA HD']"))
        self.assertEqual(ET.fromstring(gzip.decompress(gzip.compress(xml))).tag, "tv")

    def test_no_artwork_fails_instead_of_misleading_feed(self):
        with self.assertRaisesRegex(ValueError, "artwork-free"):
            g.build_xml(self.channels, self.events, {}, self.now)

    def test_image_link_host_safety(self):
        self.assertEqual(g.normalize_title("Deal"), g.normalize_title("DEAL"))
        self.assertFalse(g.valid_image("https://www.digea.gr.bad.example/sites/default/files/styles/tv_show/a.jpg"))
        self.assertTrue(g.valid_image(g.STATIC_ART["DEAL"]))


if __name__ == "__main__":
    unittest.main()
