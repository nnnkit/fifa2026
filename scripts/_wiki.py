"""MediaWiki API client with on-disk caching.

Wikipedia is the primary, factual, free, well-licensed source for squad data.
The API is friendly if you set a User-Agent and don't hammer it.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import requests

API = "https://en.wikipedia.org/w/api.php"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
UA = "fifa2026squads-research/0.1 (contact: iankit17@gmail.com)"

CACHE_DIR = Path(__file__).resolve().parent.parent / ".cache" / "wiki"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

_session = requests.Session()
_session.headers.update({"User-Agent": UA, "Accept": "application/json"})

_last_call = 0.0
_RATE_LIMIT_SECONDS = 0.5


def _throttle() -> None:
    global _last_call
    delta = time.time() - _last_call
    if delta < _RATE_LIMIT_SECONDS:
        time.sleep(_RATE_LIMIT_SECONDS - delta)
    _last_call = time.time()


def _cache_key(endpoint: str, params: dict[str, Any]) -> Path:
    blob = endpoint + "?" + urlencode(sorted(params.items()))
    h = hashlib.sha256(blob.encode()).hexdigest()[:24]
    return CACHE_DIR / f"{h}.json"


def get(endpoint: str = API, *, cache: bool = True, **params: Any) -> dict:
    params.setdefault("format", "json")
    params.setdefault("formatversion", "2")
    key = _cache_key(endpoint, params)
    if cache and key.exists():
        return json.loads(key.read_text())
    last_exc: requests.RequestException | None = None
    for attempt in range(3):
        _throttle()
        try:
            resp = _session.get(endpoint, params=params, timeout=45)
            break
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    else:
        if last_exc:
            raise last_exc
        return {}
    resp.raise_for_status()
    data = resp.json()
    if cache:
        key.write_text(json.dumps(data))
    return data


def page_exists(title: str) -> bool:
    data = get(action="query", titles=title, redirects=1)
    pages = data.get("query", {}).get("pages", [])
    return bool(pages) and not pages[0].get("missing")


def parse_html(title: str) -> str | None:
    """Return rendered HTML for a Wikipedia article title, or None if missing."""
    try:
        data = get(action="parse", page=title, prop="text", redirects=1)
    except requests.HTTPError:
        return None
    text = data.get("parse", {}).get("text")
    if isinstance(text, dict):
        text = text.get("*")
    return text


def category_members(category: str, *, limit: int = 100) -> list[str]:
    """Return article titles inside a category (no subcategories)."""
    cont: dict[str, str] = {}
    out: list[str] = []
    while True:
        data = get(
            action="query",
            list="categorymembers",
            cmtitle=category,
            cmlimit=limit,
            cmtype="page",
            **cont,
        )
        for m in data.get("query", {}).get("categorymembers", []):
            out.append(m["title"])
        cont = data.get("continue", {})
        if not cont:
            break
    return out


def page_wikidata_id(title: str) -> str | None:
    data = get(action="query", titles=title, prop="pageprops", redirects=1)
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    return pages[0].get("pageprops", {}).get("wikibase_item")


def page_lead_image_filename(title: str) -> str | None:
    """Return the Commons filename of a Wikipedia page's lead/infobox image.

    Fallback for players whose Wikidata entity doesn't yet have a P18 claim
    but whose Wikipedia article has a photo in the infobox.
    """
    data = get(
        action="query",
        titles=title,
        prop="pageimages",
        piprop="name",
        redirects=1,
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return None
    return pages[0].get("pageimage")  # raw filename, no "File:" prefix


def commons_image_info(filename: str) -> dict | None:
    """Resolve a Commons file (e.g. 'Lionel Messi 2018.jpg') to URL + license."""
    if filename.lower().startswith("file:"):
        title = filename
    else:
        title = "File:" + filename
    data = get(
        endpoint=COMMONS_API,
        action="query",
        titles=title,
        prop="imageinfo",
        iiprop="url|extmetadata|mime|size",
        iiurlwidth=800,
    )
    pages = data.get("query", {}).get("pages", [])
    if not pages or pages[0].get("missing"):
        return None
    infos = pages[0].get("imageinfo", [])
    if not infos:
        return None
    info = infos[0]
    meta = info.get("extmetadata", {})

    def m(key: str) -> str | None:
        v = meta.get(key, {}).get("value")
        return v if isinstance(v, str) else None

    return {
        "filename": title.replace("File:", ""),
        "url": info.get("url"),
        "thumb_url": info.get("thumburl"),
        "width": info.get("width"),
        "height": info.get("height"),
        "mime": info.get("mime"),
        "license": m("LicenseShortName"),
        "license_url": m("LicenseUrl"),
        "artist": m("Artist"),
        "credit": m("Credit"),
        "description": m("ImageDescription"),
        "permission": m("Permission"),
    }


def download_file(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    last_exc: requests.RequestException | None = None
    for attempt in range(3):
        _throttle()
        try:
            resp = _session.get(url, timeout=90, stream=True)
            break
        except requests.RequestException as exc:
            last_exc = exc
            if attempt == 2:
                raise
            time.sleep(2 * (attempt + 1))
    else:
        if last_exc:
            raise last_exc
        return
    resp.raise_for_status()
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("wb") as fh:
        for chunk in resp.iter_content(8192):
            fh.write(chunk)
