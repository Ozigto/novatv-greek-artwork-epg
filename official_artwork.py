"""Read *real programme images* from official Greek television schedule pages.

Matches are intentionally conservative: an image is associated with a show's
own text on the broadcaster site, and is subsequently accepted only on that
same channel. No generic internet image search or guessed fallback pictures.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from html import unescape
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; NovaTV-Greek-EPG/1.1; programme-artwork-test)"
SOURCES = {
    "alpha": ("https://www.alphatv.gr/programma/",),
    "star": ("https://www.star.gr/tv/programma",),
    "open": ("https://www.tvopen.gr/schedule",),
    "ert1": ("https://www.ert.gr/tv/program/ert1/",),
    "ert2": ("https://www.ert.gr/tv/program/ert2/",),
    "ert3": ("https://www.ert.gr/tv/program/ert3/",),
    "ertcosmos": ("https://www.ert.gr/tv/program/ert-cosmos/",),
}
TRUSTED_IMAGE_HOSTS = {
    "alpha": ("alphatv.gr",),
    "star": ("star.gr",),
    "open": ("opentv-static.siliconweb.com", "tvopen.gr"),
    "ert1": ("ert.gr", "ertflix.gr"),
    "ert2": ("ert.gr", "ertflix.gr"),
    "ert3": ("ert.gr", "ertflix.gr"),
    "ertcosmos": ("ert.gr", "ertflix.gr"),
}
CHANNEL_ALIASES = {
    "ALPHA": "alpha", "STAR": "star", "OPEN BEYOND": "open",
    "OPEN": "open", "ERT1": "ert1", "ΕΡΤ1": "ert1",
    "ERT2": "ert2", "ΕΡΤ2": "ert2", "ERT3": "ert3",
    "ΕΡΤ3": "ert3", "ERT COSMOS": "ertcosmos",
    "ERT WORLD": "ertcosmos", "ΕΡΤ WORLD": "ertcosmos",
}
# Only exceptionally strong, non-ambiguous titles. Never cross channels.
ALIASES = {
    "star": {
        "GREECE S NEXT TOP MODEL": "GNTM 7",
        "GNTM": "GNTM 7",
    }
}

def canonical(value: str) -> str:
    t = unescape(value or "").replace("’", "'").replace("΄", "'")
    t = re.sub(r"^\s*\[K(?:8|12|16|18)?\]\s*", "", t, flags=re.I)
    t = re.sub(r"\s*\((?:Ε|E|R|ΕΠΑΝΑΛΗΨΗ)\)\s*$", "", t, flags=re.I)
    t = re.sub(r",\s*(?:[IVX]{1,5}|[0-9]{1,2})(?=\s*(?:\(|$))", "", t, flags=re.I)
    t = re.sub(r"\s*(?:\||–|-)\s*(?:ΕΠΕΙΣΟΔΙΟ|EPISODE|ΕΠ\.?)[ .]*(?:\d+).*", "", t, flags=re.I)
    t = "".join(c for c in unicodedata.normalize("NFD", t.upper()) if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^A-ZΑ-Ω0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def source_for_channel(name: str) -> str | None:
    raw = canonical(name)
    raw = re.sub(r"\s+HD$", "", raw)
    return CHANNEL_ALIASES.get(raw)


def image_url(img, base: str, source: str) -> str | None:
    candidates = []
    for att in ("data-src", "data-lazy-src", "data-original", "src"):
        if img.get(att):
            candidates.append(img[att])
    for att in ("data-srcset", "srcset"):
        if img.get(att):
            candidates.extend(entry.strip().split()[0] for entry in img[att].split(","))
    for picture in img.parents:
        if picture.name == "picture":
            for el in picture.find_all("source", recursive=False):
                for att in ("srcset", "data-srcset"):
                    if el.get(att):
                        candidates.extend(entry.strip().split()[0] for entry in el[att].split(","))
            break
        if picture.name in ("main", "body", "html"):
            break
    for raw in candidates:
        url = urljoin(base, str(raw).strip())
        p = urlsplit(url)
        if p.scheme != "https" or not p.hostname:
            continue
        host = p.hostname.lower()
        if not any(host == x or host.endswith("." + x) for x in TRUSTED_IMAGE_HOSTS[source]):
            continue
        if not (".jpg" in p.path.lower() or ".jpeg" in p.path.lower()
                or ".png" in p.path.lower() or ".webp" in p.path.lower()
                or "/images/" in p.path.lower() or "/imghandler/" in p.path.lower()):
            continue
        if any(tag in p.path.lower() for tag in ("/logo", "/icon", "placeholder", "pixel.gif", "avatar")):
            continue
        return url
    return None


def associated_titles(img, source: str) -> list[str]:
    result = []
    alt = (img.get("alt") or "").strip()
    if alt:
        result.append(alt)
    # Prefer the tightest programme card containing this image and one title.
    cur = img
    for _ in range(7):
        cur = cur.parent
        if cur is None or cur.name in ("body", "html", "main"):
            break
        headlines = cur.find_all(["h2", "h3", "h4", "h5"], limit=5)
        if len(headlines) > 3 or len(cur.find_all("img", limit=6)) > 5:
            continue
        for el in headlines:
            title = el.get_text(" ", strip=True)
            if title and len(title) < 130:
                result.append(title)
        if headlines:
            break
    if source == "star":
        # Star uses file names as image alt, and proper titles in card headings.
        result = [t for t in result if not re.search(r"\b(?:1920|1080|JPG|PNG|2025|2026|2027)\b", t, re.I)
                  and not re.search(r"[_/]", t)]
    return result


@dataclass
class ArtworkResult:
    images: dict[str, dict[str, str]]
    counts: dict[str, int]
    errors: dict[str, str]


def collect(timeout: int = 20) -> ArtworkResult:
    images = {}
    counts = {}
    errors = {}
    for source, urls in SOURCES.items():
        titles = {}
        for base in urls:
            try:
                request = Request(base, headers={"User-Agent": UA, "Accept": "text/html"})
                with urlopen(request, timeout=timeout) as response:
                    html = response.read(4_000_000).decode("utf-8", "replace")
                soup = BeautifulSoup(html, "html.parser")
                for img in soup.find_all("img"):
                    url = image_url(img, base, source)
                    if not url:
                        continue
                    for label in associated_titles(img, source):
                        key = canonical(label)
                        # Avoid matching generic alt labels ("image", "rate", numbers).
                        if len(key) < 4 or key in {"IMAGE", "RATE", "LIVE", "STAR", "ALPHA", "EPG"}:
                            continue
                        titles.setdefault(key, url)
                for before, after in ALIASES.get(source, {}).items():
                    b = canonical(before)
                    if b in titles:
                        titles.setdefault(canonical(after), titles[b])
            except Exception as exc:
                errors[source] = type(exc).__name__ + ": " + str(exc)[:140]
        images[source] = titles
        counts[source] = len(titles)
    return ArtworkResult(images, counts, errors)
