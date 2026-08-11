#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4", "pillow", "requests", "truststore"]
# ///
"""Prepare image-complete RV News candidates for the private SharePoint review queue.

Run after collection:
    uv run scripts/stage_weekly_review.py --output "C:\\...\\RV News Automation\\Incoming"

The script stages image-complete source material for a no-AI SharePoint review
workflow. It never modifies pending.json or marks an article published.
"""

import argparse
import io
import json
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
import truststore
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

truststore.inject_into_ssl()

ROOT = Path(__file__).resolve().parent.parent
PENDING = ROOT / "digests" / "pending.json"
USER_AGENT = "RV-News SharePoint review staging/1.0"
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MAX_SIZE = (640, 480)


def edition_name(today: date | None = None) -> str:
    iso = (today or date.today()).isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def load_items(path: Path) -> list[dict]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(loaded, dict):
        return loaded.get("items", [])
    if isinstance(loaded, list):
        return loaded
    raise ValueError(f"{path} has no item list")


def direct_article_url(url: str, session: requests.Session) -> str:
    response = session.get(url, timeout=20, allow_redirects=True)
    response.raise_for_status()
    final_url = response.url
    if urlparse(final_url).netloc.lower() == "news.google.com":
        raise ValueError("Google News did not resolve to an original publisher")
    return final_url


def meta_image(article_url: str, session: requests.Session) -> str:
    response = session.get(article_url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for attrs in ({"property": "og:image"}, {"name": "twitter:image"},
                  {"property": "twitter:image"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return urljoin(response.url, tag["content"].strip())
    raise ValueError("no og:image or twitter:image found")


def save_image(image_url: str, destination: Path, session: requests.Session) -> None:
    response = session.get(image_url, timeout=30, stream=True)
    response.raise_for_status()
    chunks, total = [], 0
    for chunk in response.iter_content(65536):
        total += len(chunk)
        if total > MAX_DOWNLOAD_BYTES:
            raise ValueError(f"image exceeds {MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB limit")
        chunks.append(chunk)
    with Image.open(io.BytesIO(b"".join(chunks))) as source:
        image = ImageOps.exif_transpose(source).convert("RGB")
        image.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
        destination.parent.mkdir(parents=True, exist_ok=True)
        image.save(destination, "JPEG", quality=82, optimize=True, progressive=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Stage image-complete RV News candidates for SharePoint.")
    parser.add_argument("--input", type=Path, default=PENDING,
                        help="pending or curated edition JSON to stage")
    parser.add_argument("--output", type=Path, required=True,
                        help="private, synced SharePoint Incoming folder")
    parser.add_argument("--edition", default=edition_name(), help="edition identifier, e.g. 2026-W33")
    parser.add_argument("--max-input", type=int, default=12,
                        help="maximum image-complete articles prepared as raw review cards")
    parser.add_argument("--review-cards", type=int, default=12,
                        help="number of review cards the flow should create")
    parser.add_argument("--overwrite", action="store_true", help="replace an existing weekly manifest")
    args = parser.parse_args()

    if args.max_input < args.review_cards or args.review_cards < 1:
        sys.exit("error: max-input must be at least review-cards, and review-cards must be positive")
    if not args.input.is_file():
        sys.exit(f"error: input not found: {args.input}")

    weekly_folder = args.output / args.edition
    manifest_path = weekly_folder / "manifest.json"
    if manifest_path.exists() and not args.overwrite:
        sys.exit(f"error: {manifest_path} already exists; use --overwrite only after checking the flow result")

    items = load_items(args.input)
    items.sort(key=lambda item: (item.get("published") or "", item.get("source") or ""), reverse=True)
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT

    candidates, skipped = [], []
    for item in items:
        if len(candidates) >= args.max_input:
            break
        item_id = item.get("id")
        source_url = item.get("article_url") or item.get("url")
        if not item_id or not source_url:
            skipped.append({"id": item_id, "reason": "missing article ID or URL"})
            continue
        try:
            article_url = direct_article_url(source_url, session)
            image_url = meta_image(article_url, session)
            image_name = f"{item_id}.jpg"
            save_image(image_url, weekly_folder / "images" / image_name, session)
            excerpt = " ".join((item.get("summary_raw") or "").split())
            candidates.append({
                "article_id": item_id,
                "article_url": article_url,
                "title_original": item.get("title", ""),
                "title": item.get("title", ""),
                "source": item.get("source", ""),
                "language": item.get("lang", ""),
                "published": item.get("published"),
                "source_excerpt": excerpt,
                "category": "Unclassified",
                "summary": excerpt or "Source text needs editorial review.",
                "why_it_matters": "Editorial review required before publishing.",
                "status": "Review",
                "image_file": f"images/{image_name}",
            })
            print(f"  staged {item.get('title', item_id)}")
        except (requests.RequestException, ValueError, OSError) as exc:
            skipped.append({"id": item_id, "title": item.get("title", ""), "reason": str(exc)})
            print(f"  skipped {item.get('title', item_id)}: {exc}")

    if not candidates:
        sys.exit("error: no image-complete candidates could be staged")

    manifest = {
        "schema_version": 1,
        "edition": args.edition,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "review_cards": args.review_cards,
        "status": "ready_for_raw_review",
        "review_mode": "raw_no_ai",
        "source_input": args.input.name,
        "candidates": candidates,
        "image_exceptions": skipped,
    }
    weekly_folder.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8", newline="\n")
    print(f"\nwrote {manifest_path}")
    print(f"  {len(candidates)} image-complete raw candidates for {args.review_cards} review cards")
    print(f"  {len(skipped)} image exception(s), retained outside the publish-ready set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
