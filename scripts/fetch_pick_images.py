#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4", "pillow", "requests", "truststore"]
# ///
"""Cache the lead image from each editor's pick as a small local JPEG.

Run after curation and before build:
    uv run scripts/fetch_pick_images.py 2026-W32

The dashboard only reads the resulting local files. It never hotlinks images,
so build/index.html stays a self-contained offline snapshot.
"""

import io
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import requests
import truststore
from bs4 import BeautifulSoup
from PIL import Image, ImageOps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Corporate networks often inspect TLS with a certificate trusted by Windows but
# not bundled by certifi, which requests uses by default.
truststore.inject_into_ssl()

ROOT = Path(__file__).resolve().parent.parent
DIGESTS = ROOT / "digests"
IMAGE_DIR = ROOT / "assets" / "picks"
USER_AGENT = "RV-News internal dashboard image fetcher/1.0"
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024
MAX_SIZE = (640, 480)


def edition_path() -> Path:
    wanted = sys.argv[1] if len(sys.argv) > 1 else None
    editions = sorted(DIGESTS.glob("*-W*.json"))
    if not editions:
        sys.exit("error: no curated edition found")
    path = next((p for p in editions if p.stem == wanted), None) if wanted else editions[-1]
    if path is None:
        sys.exit(f"error: edition {wanted} not found")
    return path


def meta_image(article_url: str, session: requests.Session) -> str | None:
    response = session.get(article_url, timeout=20)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    for attrs in ({"property": "og:image"}, {"name": "twitter:image"},
                  {"property": "twitter:image"}):
        tag = soup.find("meta", attrs=attrs)
        if tag and tag.get("content"):
            return urljoin(response.url, tag["content"].strip())
    return None


def download_jpeg(image_url: str, dest: Path, session: requests.Session) -> None:
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
        dest.parent.mkdir(parents=True, exist_ok=True)
        image.save(dest, "JPEG", quality=82, optimize=True, progressive=True)


def main() -> int:
    path = edition_path()
    edition = json.loads(path.read_text(encoding="utf-8"))
    picks = [item for item in edition["items"] if item.get("pick")]
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    saved, failed = 0, []

    for item in picks:
        dest = IMAGE_DIR / f"{item['id']}.jpg"
        existing_image = item.get("image")
        try:
            image_url = meta_image(item["url"], session)
            if not image_url:
                raise ValueError("no og:image or twitter:image found")
            download_jpeg(image_url, dest, session)
            item["image"] = dest.relative_to(ROOT).as_posix()
            saved += 1
            print(f"  saved {item['title']}")
        except (requests.RequestException, ValueError, OSError) as exc:
            if not existing_image or not (ROOT / existing_image).is_file():
                item.pop("image", None)
            failed.append(f"{item['title']}: {exc}")
            print(f"  skipped {item['title']}: {exc}")

    path.write_text(json.dumps(edition, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"cached {saved}/{len(picks)} editor-pick images")
    if failed:
        print(f"  {len(failed)} image(s) unavailable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
