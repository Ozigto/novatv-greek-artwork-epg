"""Official ERT programme guide: XMLTV channel and programme metadata with images.

Parses the public articles on ert.gr's schedule pages; relies on the
data-start-time attributes used by ERT's documented page representation.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup

from official_artwork import canonical, image_url

ATHENS = ZoneInfo("Europe/Athens")
ERT_CHANNELS = {
    "ert1": ("ERT1", "ert1"),
    "ert2": ("ERT2", "ert2"),
    "ert3": ("ERT3", "ert3"),
    "ertcosmos": ("ERT COSMOS", "ert-cosmos"),
}


def parse_page(html: str, base: str, source: str) -> tuple[list[dict], dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    events = []
    imgs = {}
    for article in soup.select("article[data-start-time]"):
        raw = article.get("data-start-time", "").strip()
        if not raw:
            continue
        title_el = article.select_one("strong.section-title")
        if not title_el:
            continue
        title = title_el.get_text(" ", strip=True)
        if not title:
            continue
        end = (article.get("data-end-time") or "").strip()
        try:
            start_dt = datetime.fromisoformat(raw)
            end_dt = datetime.fromisoformat(end) if end else start_dt + timedelta(minutes=30)
            if start_dt.tzinfo is None:
                start_dt = start_dt.replace(tzinfo=ATHENS)
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=ATHENS)
            if end_dt <= start_dt:
                end_dt = start_dt + timedelta(minutes=30)
        except (ValueError, TypeError, OverflowError):
            continue
        desc_el = article.select_one(".fs-ms")
        desc = desc_el.get_text(" ", strip=True) if desc_el else ""
        slug = ERT_CHANNELS[source][1]
        event = {
            "channel_id": "ert-" + slug,
            "actual_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "title": title,
            "synopsis": desc,
        }
        events.append(event)
        for img in article.find_all("img"):
            candidate = image_url(img, base, source)
            if candidate:
                imgs.setdefault(canonical(title), candidate)
                break
    return events, imgs


def collect(days: int, today: datetime) -> tuple[list[dict], list[dict], dict, dict]:
    channels = []
    events = []
    images = {source: {} for source in ERT_CHANNELS}
    errors = {}
    for source, (name, slug) in ERT_CHANNELS.items():
        received = 0
        for n in range(days):
            date = (today + timedelta(days=n)).date()
            base = f"https://www.ert.gr/tv/program/{slug}/"
            url = base + "?" + urlencode({"dt": date.isoformat()})
            try:
                req = Request(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; NovaTV-Greek-EPG/1.1)",
                    "Accept": "text/html"})
                with urlopen(req, timeout=24) as resp:
                    html = resp.read(5_000_000).decode("utf-8", "replace")
                page_events, pics = parse_page(html, url, source)
                # Reject unexpectedly wrong-day page responses.
                page_events = [e for e in page_events
                               if datetime.fromisoformat(e["actual_time"]).date() == date]
                if not page_events:
                    errors[f"{source}:{date}"] = "No dated programme entries"
                    continue
                for e in page_events:
                    events.append(e)
                images[source].update(pics)
                received += len(page_events)
            except Exception as exc:
                errors[f"{source}:{date}"] = type(exc).__name__ + ": " + str(exc)[:110]
        if received:
            channels.append({"id": "ert-" + slug, "name": name})
    return channels, events, images, errors
