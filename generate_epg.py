#!/usr/bin/env python3
"""Unofficial Greek terrestrial XMLTV with real Digea programme artwork URLs."""
from __future__ import annotations

import argparse
import gzip
import json
import re
import unicodedata
from datetime import datetime, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo
from collections import Counter
import official_artwork
import ert_schedule

TZ = ZoneInfo("Europe/Athens")
BASE = "https://www.digea.gr"
API = BASE + "/el/api/epg/"
UA = "Mozilla/5.0 (compatible; NovaTV-Artwork-EPG/1.0; non-commercial-testing)"
MAX_RESPONSE = 14_000_000
TIMEOUT = 30

# Public Digea show pictures inspected on 16 October 2026.
# Artwork remains hosted by Digea; no images are redistributed.
STATIC_ART = {
    "DEAL": "https://www.digea.gr/sites/default/files/styles/tv_show/public/2026-10/deal-giorgos-thanailakis.jpg?itok=Q-t4FFVm",
    "HOUSE": "https://www.digea.gr/sites/default/files/styles/tv_show/public/2026-01/house-2.jpg?itok=77MGZz6H",
    "ΝΤΕΡΤΙ": "https://www.digea.gr/sites/default/files/styles/tv_show/public/2026-09/nterti.jpg?itok=PZ-W-2mH",
    "ΜΠΛΕ ΩΡΕΣ": "https://www.digea.gr/sites/default/files/styles/tv_show/public/2026-09/untitled-700-x-450-px-450-x-700-px.png?itok=dFLzjvvV",
    "GNTM 7": "https://www.digea.gr/sites/default/files/styles/tv_show/public/2026-09/untitled-design-20.png?itok=-S9wftBd",
    "10 ΠΑΝΤΟΥ": "https://www.digea.gr/sites/default/files/styles/tv_show/public/2026-09/10-pantoy-2026.jpg?itok=6bxXWqow",
    "ΔΥΟ ΜΑΥΡΑ ΠΟΥΚΑΜΙΣΑ": "https://www.digea.gr/sites/default/files/styles/tv_show/public/2026-09/dyo-mayra-poykamisa.jpg?itok=OAoHK64M",
}

ALIASES = {
    "ALPHA": ("ALPHA HD", "ALPHA TV"),
    "ANT1": ("ANT1 HD", "ΑΝΤ1"),
    "MEGA": ("MEGA HD", "MEGA CHANNEL"),
    "STAR": ("STAR HD",),
    "ΣΚΑΪ": ("SKAI", "SKAI HD", "ΣΚΑΪ HD"),
    "SKAI": ("SKAI HD", "ΣΚΑΪ"),
    "OPEN": ("OPEN TV", "OPEN HD"),
    "ΜΑΚ TV": ("MAK TV", "MAKTV"),
}


def normalize_title(value: str) -> str:
    value = re.sub(r"^\s*\[K(?:8|12|16|18)?\]\s*", "", value or "", flags=re.I)
    value = re.sub(r"\s*\((?:Ε|ΕΠΑΝΑΛΗΨΗ|R)\)\s*$", "", value, flags=re.I)
    value = "".join(ch for ch in unicodedata.normalize("NFD", value.upper())
                    if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", value).strip()


def valid_image(url: str) -> bool:
    u = urlsplit(url)
    return (u.scheme == "https" and u.netloc == "www.digea.gr"
            and u.path.startswith("/sites/default/files/styles/tv_show/"))


def download(url: str, fields: dict | None = None, limit: int = MAX_RESPONSE) -> bytes:
    body = urlencode(fields).encode("utf-8") if fields is not None else None
    headers = {"User-Agent": UA, "Accept": "application/json,text/html;q=0.9,*/*;q=0.7"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    req = Request(url, data=body, headers=headers)
    with urlopen(req, timeout=TIMEOUT) as response:
        result = response.read(limit + 1)
    if len(result) > limit:
        raise ValueError("Response exceeds size cap")
    return result


def api(method: str, fields: dict) -> list[dict]:
    parsed = json.loads(download(API + method, fields).decode("utf-8"))
    if not isinstance(parsed, list):
        raise ValueError("Digea API did not return a list: " + method)
    return [obj for obj in parsed if isinstance(obj, dict)]


class SiteImages(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "img":
            return
        a = dict(attrs)
        title = normalize_title(a.get("alt") or "")
        url = a.get("data-src") or a.get("src") or ""
        if not url and a.get("srcset"):
            url = a["srcset"].split(",")[0].strip().split(" ")[0]
        url = urljoin(BASE, url)
        if title and valid_image(url):
            self.found[title] = url


def find_artwork() -> dict[str, str]:
    images = {normalize_title(k): v for k, v in STATIC_ART.items()}
    try:
        html = download(BASE + "/el", limit=2_500_000).decode("utf-8", "replace")
        parser = SiteImages()
        parser.feed(html)
        images.update(parser.found)
    except (HTTPError, URLError, TimeoutError, ValueError, UnicodeError):
        pass  # Existing verified links remain usable.
    return images


def timestamp(value: str) -> datetime:
    d = datetime.fromisoformat(value)
    return d.replace(tzinfo=TZ) if d.tzinfo is None else d.astimezone(TZ)


def fmt(value: datetime) -> str:
    return value.strftime("%Y%m%d%H%M%S %z")


def build_xml(channels: list[dict], events: list[dict], art: dict[str, str],
              now: datetime, official_images: dict | None = None) -> tuple[bytes, dict]:
    tv = ET.Element("tv", {
        "date": fmt(now), "source-info-name": "Digea.gr (unofficial)",
        "generator-info-name": "NovaTV Greek Artwork EPG"})
    known = set()
    channel_sources = {}
    for channel in channels:
        ident = str(channel.get("id") or "").strip()
        name = str(channel.get("name") or "").strip()
        if not ident or not name or ident in known:
            continue
        known.add(ident)
        channel_sources[ident] = official_artwork.source_for_channel(name)
        el = ET.SubElement(tv, "channel", id="digea-" + ident)
        ET.SubElement(el, "display-name", lang="el").text = name
        for alias in ALIASES.get(name.upper(), ()):
            ET.SubElement(el, "display-name", lang="el").text = alias
        icon = str(channel.get("img") or "")
        resolved = urljoin(BASE, icon)
        if icon and urlsplit(resolved).netloc == "www.digea.gr":
            ET.SubElement(el, "icon", src=resolved)

    prepared = []
    for event in events:
        ident = str(event.get("channel_id") or "").strip()
        if ident not in known or not event.get("actual_time"):
            continue
        title = str(event.get("title") or "").strip()
        if not title:
            continue
        try:
            start = timestamp(str(event["actual_time"]))
            end = timestamp(str(event["end_time"])) if event.get("end_time") else start + timedelta(minutes=30)
            if end <= start:
                end = start + timedelta(minutes=30)
        except (TypeError, KeyError, ValueError, OverflowError):
            continue
        prepared.append((ident, start, end, title, event))

    matched = 0
    matched_by_source = Counter()
    matched_titles = set()
    visited = set()
    for ident, start, end, title, event in sorted(prepared, key=lambda e: (e[0], e[1])):
        unique = (ident, start, title)
        if unique in visited:
            continue
        visited.add(unique)
        el = ET.SubElement(tv, "programme", {
            "start": fmt(start), "stop": fmt(end), "channel": "digea-" + ident})
        ET.SubElement(el, "title", lang="el").text = title
        desc = event.get("long_synopsis") or event.get("synopsis")
        if desc:
            ET.SubElement(el, "desc", lang="el").text = str(desc)
        source = channel_sources.get(ident)
        image = (official_images or {}).get(source, {}).get(official_artwork.canonical(title))
        if image:
            ET.SubElement(el, "icon", src=image)
            matched += 1
            matched_by_source[source] += 1
            matched_titles.add(title)
        else:
            image = art.get(normalize_title(title))
            if image and valid_image(image):
                ET.SubElement(el, "icon", src=image)
                matched += 1
                matched_by_source["digea_fallback"] += 1
                matched_titles.add(title)

    if not known or not visited:
        raise ValueError("No channel/programme data; refusing to publish an empty feed")
    if matched == 0:
        raise ValueError("No programme image matched; refusing artwork-free publication")
    xml = ET.tostring(tv, encoding="utf-8", xml_declaration=True)
    ET.fromstring(xml)
    return xml, {
        "generated_at": now.isoformat(),
        "channels": len(known),
        "programmes": len(visited),
        "programmes_with_artwork": matched,
        "programmes_with_artwork_by_source": dict(matched_by_source),
        "matched_programme_titles": sorted(matched_titles),
        "artwork_source": "Official Greek broadcaster programme images and Digea fallback; channel-scoped title matching",
    }


def generate(outdir: Path, days: int = 5) -> dict:
    now = datetime.now(TZ)
    channels = api("get-channels", {"action": "get_chanels", "lang": "el"})
    events = []
    for n in range(days):
        d = (now + timedelta(days=n)).date()
        events += api("get-events", {"action": "get_events", "date": f"{d.year}-{d.month}-{d.day}"})
    official = official_artwork.collect()
    ert_channels, ert_events, ert_images, ert_errors = ert_schedule.collect(days, now)
    channels.extend(ert_channels)
    events.extend(ert_events)
    for source, pictures in ert_images.items():
        official.images.setdefault(source, {}).update(pictures)
        official.counts[source] = len(official.images[source])
    xml, metadata = build_xml(channels, events, find_artwork(), now, official.images)
    metadata["official_source_title_counts"] = official.counts
    metadata["official_source_errors"] = dict(official.errors, **ert_errors)
    metadata["ert_programmes_collected"] = len(ert_events)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "digea-artwork.xml").write_bytes(xml)
    (outdir / "digea-artwork.xml.gz").write_bytes(gzip.compress(xml, mtime=0))
    (outdir / "status.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("epg"))
    parser.add_argument("--days", type=int, default=5)
    args = parser.parse_args()
    if not 1 <= args.days <= 7:
        parser.error("days must be between 1 and 7")
    print(json.dumps(generate(args.output, args.days), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
