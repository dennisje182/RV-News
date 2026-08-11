#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = ["beautifulsoup4", "curl-cffi", "pillow", "pyyaml"]
# ///
"""Cache lead-brand logos from verified official websites.

Run after curation and before build:
    uv run scripts/fetch_brand_logos.py 2026-W32

Only sites listed in brand_sources.yaml are queried. The script first looks for
the organisation logo declared by the official site, then its header logo, then
its favicon. It never changes article selection, and missing logos remain a
labelled monogram in the dashboard.
"""

import io
import json
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import urljoin

import yaml
from bs4 import BeautifulSoup
from curl_cffi import requests
from curl_cffi.requests.exceptions import RequestException
from PIL import Image, ImageOps

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
DIGESTS = ROOT / "digests"
SOURCES = ROOT / "brand_sources.yaml"
LOGOS = ROOT / "brand" / "img" / "company-logos"
USER_AGENT = "RVNewsLogoCache/1.0 (internal industry monitoring; +https://www.thetford-europe.com)"
MAX_DOWNLOAD_BYTES = 3 * 1024 * 1024
MAX_RASTER_SIZE = (512, 256)


def slug(brand: str) -> str:
    folded = unicodedata.normalize("NFKD", brand).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def edition_path() -> Path:
    wanted = sys.argv[1] if len(sys.argv) > 1 else None
    editions = sorted(DIGESTS.glob("*-W*.json"))
    if not editions:
        sys.exit("error: no curated edition found")
    path = next((p for p in editions if p.stem == wanted), None) if wanted else editions[-1]
    if path is None:
        sys.exit(f"error: edition {wanted} not found")
    return path


def local_logo(brand: str) -> Path | None:
    return next((LOGOS / f"{slug(brand)}{suffix}"
                 for suffix in (".svg", ".png", ".jpg", ".jpeg", ".webp")
                 if (LOGOS / f"{slug(brand)}{suffix}").is_file()), None)


def json_logos(value) -> list[str]:
    if isinstance(value, dict):
        found = []
        for key, child in value.items():
            if key == "logo":
                if isinstance(child, str):
                    found.append(child)
                elif isinstance(child, dict) and isinstance(child.get("url"), str):
                    found.append(child["url"])
            found.extend(json_logos(child))
        return found
    if isinstance(value, list):
        return [logo for child in value for logo in json_logos(child)]
    return []


def candidates(page: str, site_url: str, brand: str) -> list[str]:
    soup = BeautifulSoup(page, "html.parser")
    urls = []
    for tag in soup.select('[itemprop="logo"], meta[property="og:logo"], meta[name="logo"]'):
        value = tag.get("content") or tag.get("src")
        if value:
            urls.append(value)
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            urls.extend(json_logos(json.loads(tag.get_text())))
        except (TypeError, ValueError):
            continue
    brand_folded = slug(brand).replace("-", "")
    for tag in soup.select("header img, [class*=header] img, [class*=logo] img"):
        value = tag.get("src") or tag.get("data-src")
        marker = slug(" ".join((tag.get("alt") or "", " ".join(tag.get("class") or []))))
        if value and (brand_folded in marker.replace("-", "") or "logo" in marker):
            urls.append(value)
    for tag in soup.select('link[rel~="icon"], link[rel="shortcut icon"]'):
        if tag.get("href"):
            urls.append(tag["href"])
    deduped = []
    for value in urls:
        candidate = urljoin(site_url, value.strip())
        if candidate.startswith(("http://", "https://")) and candidate not in deduped:
            deduped.append(candidate)
    return deduped


def download(candidate: str, destination: Path, session: requests.Session) -> None:
    response = session.get(candidate, timeout=25, stream=True, verify=False)
    response.raise_for_status()
    chunks, total = [], 0
    for chunk in response.iter_content(65536):
        total += len(chunk)
        if total > MAX_DOWNLOAD_BYTES:
            raise ValueError("logo exceeds 3 MB limit")
        chunks.append(chunk)
    payload = b"".join(chunks)
    if b"<svg" in payload[:2048].lower():
        destination.with_suffix(".svg").write_bytes(payload)
        return
    with Image.open(io.BytesIO(payload)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")
        if min(image.size) < 16 or max(image.size) < 32:
            raise ValueError(f"image is too small to be a usable logo ({image.width}x{image.height})")
        image.thumbnail(MAX_RASTER_SIZE, Image.Resampling.LANCZOS)
        destination.with_suffix(".png").parent.mkdir(parents=True, exist_ok=True)
        image.save(destination.with_suffix(".png"), "PNG", optimize=True)


def main() -> int:
    path = edition_path()
    edition = json.loads(path.read_text(encoding="utf-8"))
    mapping = yaml.safe_load(SOURCES.read_text(encoding="utf-8")) or {}
    sites = mapping.get("brands", {})
    brands = sorted({item["brands"][0] for item in edition["items"] if item.get("brands")})
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    cached, missing, unavailable = 0, [], []

    for brand in brands:
        if local_logo(brand):
            continue
        site = sites.get(brand)
        if not site:
            missing.append(brand)
            continue
        try:
            # The corporate proxy substitutes its own TLS certificate. These are
            # public, explicitly listed official brand sites, and the downloaded
            # image is still screened for a usable logo before it is saved.
            page = session.get(site, timeout=25, verify=False, impersonate="chrome")
            page.raise_for_status()
            destination = LOGOS / slug(brand)
            errors = []
            for candidate in candidates(page.text, page.url, brand):
                try:
                    download(candidate, destination, session)
                    print(f"  cached {brand} from {site}")
                    cached += 1
                    break
                except (RequestException, ValueError, OSError) as exc:
                    errors.append(str(exc))
            else:
                raise ValueError(errors[-1] if errors else "no logo candidate found")
        except (RequestException, ValueError, OSError) as exc:
            unavailable.append(f"{brand}: {exc}")
            print(f"  unavailable {brand}: {exc}")

    print(f"cached {cached} lead-brand logo(s)")
    if missing:
        print("  no verified website: " + ", ".join(missing))
    if unavailable:
        print(f"  {len(unavailable)} official site(s) did not yield a usable logo")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
