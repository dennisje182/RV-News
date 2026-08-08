#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["feedparser", "requests", "pyyaml", "beautifulsoup4", "lxml"]
# ///
"""
RV News collector.

Reads sources.yaml, fetches every source, and writes any article it has not
seen before into two places:

  archive/items.json      permanent record of everything ever collected
  digests/pending.json    only the new items, for this week's curation

Run it with:      uv run scripts/collect.py
Useful flags:     --days 14        widen the date window
                  --source NAME    test a single source
                  --dry-run        fetch and report, write nothing

Deliberately dumb: this script decides nothing about relevance beyond a date
window and an obvious-junk filter. Choosing what matters, translating, and
categorising is done during curation, where judgement is actually available.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

import feedparser
import requests
import yaml
from bs4 import BeautifulSoup

# Several source names contain an em dash, and a legacy Windows console runs
# cp1252, where printing one raises UnicodeEncodeError and takes down the whole
# run. Force UTF-8 out and degrade rather than crash if the terminal cannot.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
SOURCES = ROOT / "sources.yaml"
ARCHIVE = ROOT / "archive" / "items.json"
PENDING = ROOT / "digests" / "pending.json"

UA = "RVNewsCollector/1.0 (internal industry monitoring; +https://www.thetford-europe.com)"
TIMEOUT = 25
WORKERS = 8

# Query params that carry no meaning for identity, only tracking.
JUNK_PARAMS = re.compile(r"^(utm_|fbclid|gclid|mc_|ref_?$|source$|at_medium|at_campaign)", re.I)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def canonical_url(url: str) -> str:
    """Strip tracking noise so the same article is not archived twice."""
    if not url:
        return ""
    url = url.strip()
    try:
        p = urlparse(url)
    except ValueError:
        return url
    keep = [(k, v) for k, v in parse_qsl(p.query) if not JUNK_PARAMS.match(k)]
    path = p.path.rstrip("/") or "/"
    netloc = p.netloc.lower().removeprefix("www.")
    return urlunparse(("https", netloc, path, "", urlencode(keep), ""))


def item_id(url: str, title: str) -> str:
    basis = canonical_url(url) or title.strip().lower()
    return hashlib.sha1(basis.encode("utf-8", "replace")).hexdigest()[:16]


def clean_text(raw: str, limit: int = 700) -> str:
    """Feed summaries are full of markup and boilerplate. Flatten to plain text."""
    if not raw:
        return ""
    text = BeautifulSoup(raw, "lxml").get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(Der Beitrag|The post)\s.*?(erschien zuerst auf|appeared first on)\s.*$", "", text)
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0] + "…"


def entry_date(entry) -> str | None:
    for key in ("published_parsed", "updated_parsed", "created_parsed"):
        tm = entry.get(key)
        if tm:
            try:
                return datetime(*tm[:6], tzinfo=timezone.utc).isoformat()
            except (TypeError, ValueError):
                continue
    return None


def split_publisher_suffix(title: str) -> tuple[str, str]:
    """
    Google News appends ' - Publisher' to every headline. Return the clean title
    and the publisher separately: the publisher is the outlet that actually
    wrote the story, which is more useful on the dashboard than "Google News".
    """
    m = re.search(r"^(.*?)\s+[-–|]\s+([^-–|]{2,40})$", title.strip())
    if not m:
        return title.strip(), ""
    return m.group(1).strip(), m.group(2).strip()


# --------------------------------------------------------------------------
# fetching
# --------------------------------------------------------------------------

@dataclass
class Result:
    source: str
    ok: bool
    count: int = 0
    error: str = ""
    warn: str = ""
    pages_read: int = 1
    items: list[dict] = field(default_factory=list)


def entry_text(e) -> str:
    """
    Prefer content:encoded. Most WordPress feeds put the full article there and
    leave only a short excerpt in description, so reading description first
    quietly throws away most of the text.
    """
    for c in e.get("content") or []:
        value = (c or {}).get("value")
        if value:
            return value
    return e.get("summary") or e.get("description") or ""


def paged_url(url: str, page: int) -> str:
    """WordPress feeds serve older items at ?paged=N."""
    if page <= 1:
        return url
    p = urlparse(url)
    q = dict(parse_qsl(p.query))
    q["paged"] = str(page)
    return urlunparse(p._replace(query=urlencode(q)))


def fetch_rss(src: dict, session: requests.Session, cutoff: datetime) -> Result:
    name = src["name"]
    max_pages = max(1, int(src.get("pages", 1)))

    entries, seen_links, pages_read = [], set(), 0
    for page in range(1, max_pages + 1):
        resp = session.get(paged_url(src["url"], page), timeout=TIMEOUT,
                           headers={"User-Agent": UA})
        if page > 1 and resp.status_code >= 400:
            break                                  # no more history, not an error
        resp.raise_for_status()
        parsed = feedparser.parse(resp.content)
        pages_read = page

        if page == 1:
            if parsed.bozo and not parsed.entries:
                raise ValueError(f"unparseable feed ({parsed.get('bozo_exception', 'unknown')})")
            if not parsed.entries:
                # HTTP 200, well-formed RSS, fresh lastBuildDate, no items.
                # Several real feeds do this; the content sits in a custom post
                # type. Silence here would look like a healthy quiet week.
                return Result(name, True, 0, warn="feed is valid but contains no items "
                                                 "(wrong post type, or the path has moved)")
        if not parsed.entries:
            break

        # If ?paged is unsupported the site just re-serves page 1. Detect that.
        fresh_on_page = [e for e in parsed.entries if (e.get("link") or "") not in seen_links]
        if page > 1 and not fresh_on_page:
            break
        for e in fresh_on_page:
            seen_links.add(e.get("link") or "")
        entries.extend(fresh_on_page)

        dated = [d for d in (entry_date(e) for e in fresh_on_page) if d]
        if dated and min(datetime.fromisoformat(d) for d in dated) < cutoff:
            break                                  # walked past the window

    items, undated, newest = [], 0, None
    for e in entries:
        link = e.get("link") or ""
        title = (e.get("title") or "").strip()
        if not title or not link:
            continue

        iso = entry_date(e)
        if iso:
            if newest is None or iso > newest:
                newest = iso
            if datetime.fromisoformat(iso) < cutoff:
                continue
        else:
            # No date at all: keep a few, they are usually newest-first.
            undated += 1
            if undated > 5:
                continue

        publisher = ""
        if src.get("google_news"):
            title, publisher = split_publisher_suffix(title)

        items.append({
            "id": item_id(link, title),
            "title": title,
            "publisher": publisher,
            "url": link,
            "canonical": canonical_url(link),
            "summary_raw": "" if src.get("title_only") else clean_text(entry_text(e)),
            "published": iso,
            "source": name,
            "source_type": src.get("type", "rss"),
            "lang": src.get("lang", "en"),
            "country": src.get("country", "eu"),
            "source_categories": src.get("categories", []),
            "tier": src.get("tier", 2),
            "title_only": bool(src.get("title_only")),
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })

    # A feed can serve cleanly for years after the publisher abandoned it.
    # Industry associations publish in seasonal bursts though, so the threshold
    # is per-source: warning on those every summer would train you to ignore it.
    warn = ""
    if newest:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(newest)).days
        limit = int(src.get("stale_after_days", 120))
        if age > limit:
            warn = f"stale: newest item is {age} days old"
    return Result(name, True, len(items), warn=warn, pages_read=pages_read, items=items)


def fetch_scrape(src: dict, session: requests.Session, cutoff: datetime) -> Result:
    """Fallback for sources with no feed but a stable list of links."""
    name = src["name"]
    resp = session.get(src["url"], timeout=TIMEOUT, headers={"User-Agent": UA})
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "lxml")

    nodes = soup.select(src["item_selector"])
    if not nodes:
        raise ValueError(f"selector {src['item_selector']!r} matched nothing (page layout changed?)")

    base = f"{urlparse(src['url']).scheme}://{urlparse(src['url']).netloc}"
    items = []
    for node in nodes[: src.get("limit", 25)]:
        a = node if node.name == "a" else node.find("a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        link = href if href.startswith("http") else base + "/" + href.lstrip("/")
        title = " ".join(a.get_text(" ", strip=True).split())
        if not title or len(title) < 12:
            continue
        items.append({
            "id": item_id(link, title),
            "title": title,
            "url": link,
            "canonical": canonical_url(link),
            "summary_raw": "",
            "published": None,          # scraped pages rarely give a reliable date
            "source": name,
            "source_type": "scrape",
            "lang": src.get("lang", "en"),
            "country": src.get("country", "eu"),
            "source_categories": src.get("categories", []),
            "tier": src.get("tier", 2),
            "title_only": True,
            "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
    return Result(name, True, len(items), items=items)


def fetch_one(src: dict, cutoff: datetime) -> Result:
    name = src.get("name", "?")
    if src.get("disabled"):
        return Result(name, False, error="disabled in sources.yaml")
    try:
        with requests.Session() as s:
            s.max_redirects = 5
            if src.get("type") == "scrape":
                return fetch_scrape(src, s, cutoff)
            return fetch_rss(src, s, cutoff)
    except requests.HTTPError as e:
        return Result(name, False, error=f"HTTP {e.response.status_code}")
    except requests.Timeout:
        return Result(name, False, error=f"timeout after {TIMEOUT}s")
    except Exception as e:                                  # noqa: BLE001 - one bad source must not stop the run
        return Result(name, False, error=f"{type(e).__name__}: {e}"[:160])


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"error: {path} is not valid JSON ({e}). Fix or delete it and re-run.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect European RV industry news.")
    ap.add_argument("--days", type=int, default=10, help="how far back to look (default 10)")
    ap.add_argument("--source", help="only fetch sources whose name contains this")
    ap.add_argument("--dry-run", action="store_true", help="fetch and report, write nothing")
    args = ap.parse_args()

    if not SOURCES.exists():
        sys.exit(f"error: {SOURCES} not found")

    config = yaml.safe_load(SOURCES.read_text(encoding="utf-8")) or {}
    sources = config.get("sources", [])
    if args.source:
        needle = args.source.lower()
        sources = [s for s in sources if needle in s.get("name", "").lower()]
    if not sources:
        sys.exit("error: no sources matched")

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    print(f"Fetching {len(sources)} sources, articles since {cutoff.date()}\n")

    results: list[Result] = []
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futures = {pool.submit(fetch_one, s, cutoff): s for s in sources}
        for fut in as_completed(futures):
            results.append(fut.result())

    results.sort(key=lambda r: (not r.ok, -r.count, r.source))

    # ---- dedupe against the archive -------------------------------------
    archive = load_json(ARCHIVE, [])
    seen_ids = {i["id"] for i in archive}
    seen_titles = {i["title"].strip().lower() for i in archive}

    fresh, dupes = [], 0
    for r in results:
        for item in r.items:
            if item["id"] in seen_ids or item["title"].strip().lower() in seen_titles:
                dupes += 1
                continue
            seen_ids.add(item["id"])
            seen_titles.add(item["title"].strip().lower())
            fresh.append(item)

    fresh.sort(key=lambda i: (i["published"] or "", i["source"]), reverse=True)

    # ---- report ---------------------------------------------------------
    ok = [r for r in results if r.ok]
    bad = [r for r in results if not r.ok]

    print(f"{'source':<38} {'items':>6} {'pages':>6}")
    print("-" * 53)
    for r in ok:
        pages = str(r.pages_read) if r.pages_read > 1 else ""
        print(f"{r.source[:38]:<38} {r.count:>6} {pages:>6}")

    warned = [r for r in ok if r.warn]
    if warned:
        print(f"\n{len(warned)} source(s) need attention:")
        for r in warned:
            print(f"  {r.source[:38]:<38} {r.warn}")
    if bad:
        print(f"\n{len(bad)} source(s) failed:")
        for r in bad:
            print(f"  {r.source[:38]:<38} {r.error}")

    print(f"\nfetched {sum(r.count for r in ok)} in-window items in {time.monotonic()-started:.1f}s")
    print(f"  {dupes} already in archive")
    print(f"  {len(fresh)} new")

    if args.dry_run:
        print("\ndry run: nothing written")
        return 0

    # The pending queue accumulates until an edition is published, so running
    # the collector twice in a row never discards work waiting to be curated.
    prev = load_json(PENDING, {})
    carried = prev.get("items", []) if isinstance(prev, dict) else []
    carried_ids = {i["id"] for i in carried}
    queue = carried + [i for i in fresh if i["id"] not in carried_ids]

    ARCHIVE.parent.mkdir(parents=True, exist_ok=True)
    PENDING.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE.write_text(json.dumps(archive + fresh, ensure_ascii=False, indent=1),
                       encoding="utf-8")
    PENDING.write_text(json.dumps({
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "window_days": args.days,
        "sources_ok": len(ok),
        "sources_failed": [{"source": r.source, "error": r.error} for r in bad],
        "sources_warned": [{"source": r.source, "warn": r.warn} for r in ok if r.warn],
        "items": queue,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    waiting = f" ({len(carried)} carried over)" if carried else ""
    print(f"\nwrote {PENDING.relative_to(ROOT)} — {len(queue)} items to curate{waiting}")
    print(f"      {ARCHIVE.relative_to(ROOT)} — {len(archive)+len(fresh)} total ever seen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
