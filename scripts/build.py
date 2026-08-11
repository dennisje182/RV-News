#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Build the RV News dashboard: one self-contained HTML file.

GitHub Pages deploys the generated file, while the same file is also used as an
offline snapshot. Fonts, logos and the sunburst are base64-inlined so it remains
portable with no assets beside it.

Run:  uv run scripts/build.py          newest edition in digests/
      uv run scripts/build.py 2026-W32 a specific edition
"""

import base64
import html
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

# Source names printed in the build report contain em dashes; a cp1252 Windows
# console would raise UnicodeEncodeError on them.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "brand"
COMPANY_LOGOS = BRAND / "img" / "company-logos"
PICK_IMAGES = ROOT / "assets" / "picks"
COMPANY_LOGO_OVERRIDES = {
    "Thetford": BRAND / "img" / "logo-dark.png",
}
SOURCE_LOGOS = {
    "promobil": COMPANY_LOGOS / "promobil.svg",
}
DIGESTS = ROOT / "digests"
OUT = ROOT / "build" / "index.html"

CATEGORIES = [
    ("vehicles",    "New vehicles",            "Launches and model-year updates from OEMs"),
    ("accessories", "Accessories & components","Supplier products, testing and fitment"),
    ("competitor",  "Competitor watch",        "Product and financial news from direct competitors"),
    ("industry",    "Industry & market",       "Results, registrations, consolidation and shows"),
]
CAT_LABEL = {k: v for k, v, _ in CATEGORIES}

COUNTRY_LABEL = {
    "de": "Germany", "nl": "Netherlands", "gb": "UK", "fr": "France",
    "it": "Italy", "es": "Spain", "se": "Sweden", "eu": "Europe-wide",
}
LANG_LABEL = {
    "de": "German", "nl": "Dutch", "fr": "French", "it": "Italian",
    "es": "Spanish", "sv": "Swedish", "en": "English",
}
# Long feed names read badly in a dense register.
SOURCE_LABEL = {
    "Google News DE — competitor products": "Google News (DE)",
    "Google News EN — listed OEMs and suppliers": "Google News (EN)",
    "Google News DE — new model announcements": "Google News (DE)",
    "Google News — Thetford coverage": "Google News",
    "CIVD (German industry association)": "CIVD",
    "UNI VDL (French industry association)": "UNI VDL",
    "ASEICAR (Spanish trade association)": "ASEICAR",
    "Dometic Group (investor relations)": "Dometic IR",
    "Thule Group (investor relations)": "Thule IR",
    "Knaus Tabbert press releases": "Knaus Tabbert",
    "Motor1 España — camper": "Motor1 ES",
    "Camper Professional DE": "Camper Professional",
}

MIME = {".woff2": "font/woff2", ".png": "image/png", ".svg": "image/svg+xml",
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

# Some embedding and forwarding tools handle charset declarations poorly. Every
# non-ASCII character in markup is therefore emitted as a numeric character
# reference. Entities are not interpreted inside <style> or <script>, so CSS and
# JS get typographic characters folded to ASCII instead.
TYPOGRAPHIC = {
    "—": "--", "–": "-", "’": "'", "‘": "'",
    "“": '"', "”": '"', "…": "...", " ": " ",
    "·": "-", "→": "->", "≤": "<=", "≥": ">=",
}


def entity_escape(markup: str) -> str:
    return "".join(c if ord(c) < 128 else f"&#x{ord(c):X};" for c in markup)


def asciify(code: str, label: str) -> str:
    for bad, good in TYPOGRAPHIC.items():
        code = code.replace(bad, good)
    leftover = sorted({c for c in code if ord(c) > 127})
    if leftover:
        print(f"  note: {label} still contains non-ASCII {leftover[:6]}; "
              f"left as UTF-8 and dependent on the host charset")
    return code


def e(text) -> str:
    """Escape for HTML text and quoted attributes."""
    return html.escape(str(text or ""), quote=True)


def data_uri(path: Path) -> str:
    mime = MIME.get(path.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def inline_fonts(css: str) -> str:
    """Swap url('fonts/x.woff2') for the encoded font itself."""
    missing = []

    def swap(m):
        rel = m.group(1)
        f = BRAND / rel
        if not f.exists():
            missing.append(rel)
            return m.group(0)
        return f"url({data_uri(f)})"

    out = re.sub(r"url\(['\"]?(fonts/[^'\")]+)['\"]?\)", swap, css)
    if missing:
        sys.exit(f"error: font files missing from {BRAND}: {', '.join(sorted(set(missing)))}")
    return out


# Month names are spelled out rather than taken from strftime for two reasons:
# the no-padding flag differs by platform (%-d is glibc/BSD, %#d is Windows, and
# %-d raises ValueError there), and %b/%B are locale-dependent, so a German
# Windows machine would render "Okt" on an otherwise English page.
MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]


def pretty_date(iso: str) -> str:
    if not iso:
        return ""
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return iso
    return f"{d.day} {MONTHS_SHORT[d.month - 1]}"


def long_date(iso: str) -> str:
    try:
        d = datetime.strptime(iso, "%Y-%m-%d")
    except ValueError:
        return iso
    return f"{d.day} {MONTHS_LONG[d.month - 1]} {d.year}"


def search_blob(it: dict) -> str:
    bits = [it["title"], it.get("title_original", ""), it.get("summary", ""),
            it.get("why") or "", it["source"], CAT_LABEL[it["category"]],
            COUNTRY_LABEL.get(it["country"], ""), " ".join(it.get("brands") or []),
            " ".join(it.get("also") or [])]
    return re.sub(r"\s+", " ", " ".join(bits)).lower()


def badges(it: dict) -> str:
    out = []
    if it.get("competitor"):
        out.append('<span class="badge badge--competitor">Competitor</span>')
    for b in (it.get("brands") or [])[:3]:
        out.append(f'<span class="badge badge--brand">{e(b)}</span>')
    country = COUNTRY_LABEL.get(it["country"], it["country"].upper())
    out.append(f'<span class="badge badge--country">{e(country)}</span>')
    return "".join(out)


def brand_slug(brand: str) -> str:
    """Return the local asset name for a brand, independent of accents."""
    folded = unicodedata.normalize("NFKD", brand).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "-", folded.lower()).strip("-")


def brand_initials(brand: str) -> str:
    """A restrained fallback until an approved company logo is added locally."""
    parts = re.findall(r"[A-Za-z0-9]+", brand_slug(brand))
    return "".join(part[0] for part in parts[:2]).upper() or "?"


def logo_is_wide(asset: Path) -> bool:
    """Detect SVG wordmarks that need a horizontal frame at this small size."""
    if asset.suffix.lower() != ".svg":
        return False
    match = re.search(r'viewBox=["\']\s*[\d.-]+\s+[\d.-]+\s+([\d.-]+)\s+([\d.-]+)',
                      asset.read_text(encoding="utf-8"))
    return bool(match and float(match.group(1)) / float(match.group(2)) > 1.7)


def logo_needs_dark_frame(asset: Path) -> bool:
    """Identify light SVG wordmarks that disappear on the standard white tile."""
    if asset.suffix.lower() != ".svg":
        return False
    markup = asset.read_text(encoding="utf-8")
    return bool(re.search(r'fill=["\'](?:#(?:fff|ffffff)|white)["\']', markup, re.I))


def logo_uri(asset: Path) -> str:
    """Return an inlined company-logo URI, preserving embedded raster artwork."""
    if asset.suffix.lower() == ".svg":
        markup = asset.read_text(encoding="utf-8")
        embedded = re.search(r'href="(data:image/(?:png|jpeg);base64,[^"]+)"', markup)
        if embedded:
            return embedded.group(1)
    return data_uri(asset)


def brand_mark(it: dict) -> str:
    """Render the lead company as an embedded logo or a labelled monogram.

    The company-assets directory is deliberately local. Every logo needs to be
    traceable before it is used, and local assets keep the offline snapshot whole.
    """
    brands = it.get("brands") or []
    if not brands:
        asset = SOURCE_LOGOS.get(it["source"])
        if not asset or not asset.exists():
            return ""
        publisher = SOURCE_LABEL.get(it["source"], it["source"])
        title = e(f"Publisher: {publisher}")
        return (f'<span class="brand-mark brand-mark--logo" '
                f'title="{title}">'
                f'<img src="{logo_uri(asset)}" alt=""></span>')
    brand = brands[0]
    slug = brand_slug(brand)
    asset = COMPANY_LOGO_OVERRIDES.get(brand)
    if asset is None:
        asset = next((COMPANY_LOGOS / f"{slug}{suffix}"
                      for suffix in (".svg", ".png", ".jpg", ".jpeg")
                      if (COMPANY_LOGOS / f"{slug}{suffix}").exists()), None)
    title = e(f"Lead company: {brand}")
    if asset:
        shape = " brand-mark--wide" if brand == "Thetford" or logo_is_wide(asset) else ""
        frame = " brand-mark--on-dark" if logo_needs_dark_frame(asset) else ""
        return (f'<span class="brand-mark brand-mark--logo{shape}{frame}" title="{title}">'
                f'<img src="{logo_uri(asset)}" alt=""></span>')
    return (f'<span class="brand-mark" title="{title}" aria-hidden="true">'
            f'{e(brand_initials(brand))}</span>')


def pick_image(it: dict) -> str:
    """Render a locally cached article image for an editor's pick, if present."""
    image = it.get("image")
    if not image:
        return ""
    asset = (ROOT / image).resolve()
    if PICK_IMAGES.resolve() not in asset.parents or not asset.is_file():
        print(f"  note: pick image missing or outside assets/picks for {it['id']}")
        return ""
    return (f'<a class="pick__image" href="{e(it["url"])}" target="_blank" '
            f'rel="noopener noreferrer"><img src="{data_uri(asset)}" '
            f'alt="{e(it["title"])}"></a>')


def render_row(it: dict) -> str:
    original = ""
    if it.get("title_original") and it["lang"] != "en":
        lang = LANG_LABEL.get(it["lang"], it["lang"].upper())
        original = (f'<p class="row__original">{e(lang)} original: '
                    f'{e(it["title_original"])}</p>')
    summary = f'<p class="row__summary">{e(it["summary"])}</p>' if it.get("summary") else ""
    also = ""
    if it.get("also"):
        names = ", ".join(SOURCE_LABEL.get(a, a) for a in it["also"])
        also = f'<p class="row__original">Also covered by {e(names)}</p>'
    source = SOURCE_LABEL.get(it["source"], it["source"])
    return f"""<article class="row" data-item data-cat="{e(it['category'])}"
 data-country="{e(it['country'])}" data-competitor="{'1' if it.get('competitor') else '0'}"
 data-text="{e(search_blob(it))}">
 <div class="row__rail"><div class="row__date">{e(pretty_date(it['published']))}</div>{brand_mark(it)}</div>
 <div class="row__body">
  <div class="row__meta"><span class="row__source">{e(source)}</span>{badges(it)}</div>
  <h4 class="row__title"><a href="{e(it['url'])}" target="_blank" rel="noopener noreferrer">{e(it['title'])}</a></h4>
  {summary}{original}{also}
 </div>
</article>"""


def render_pick(it: dict) -> str:
    original = ""
    if it.get("title_original") and it["lang"] != "en":
        lang = LANG_LABEL.get(it["lang"], it["lang"].upper())
        original = f'<p class="row__original">{e(lang)} original: {e(it["title_original"])}</p>'
    also = ""
    if it.get("also"):
        names = ", ".join(SOURCE_LABEL.get(a, a) for a in it["also"])
        also = f'<p class="row__original">Also covered by {e(names)}</p>'
    why = ""
    if it.get("why"):
        why = (f'<div class="pick__why"><p class="eyebrow">Why it matters for Thetford</p>'
               f'<p>{e(it["why"])}</p></div>')
    source = SOURCE_LABEL.get(it["source"], it["source"])
    image = pick_image(it)
    no_image = " pick--no-image" if not image else ""
    return f"""<article class="pick{no_image}" data-item data-cat="{e(it['category'])}"
 data-country="{e(it['country'])}" data-competitor="{'1' if it.get('competitor') else '0'}"
 data-text="{e(search_blob(it))}">
 <div class="pick__content">
  <div class="pick__meta"><span class="row__source">{e(source)}</span>
   <span class="row__date">{e(pretty_date(it['published']))}</span>{badges(it)}</div>
  <h3 class="pick__title"><a href="{e(it['url'])}" target="_blank" rel="noopener noreferrer">{e(it['title'])}</a></h3>
  <p class="pick__summary">{e(it['summary'])}</p>
  {original}{also}{why}
 </div>
 {image}
</article>"""


def main() -> int:
    editions = sorted(DIGESTS.glob("*-W*.json"))
    if not editions:
        sys.exit(f"error: no curated editions in {DIGESTS}. Run collection and curation first.")

    wanted = sys.argv[1] if len(sys.argv) > 1 else None
    path = next((p for p in editions if p.stem == wanted), None) if wanted else editions[-1]
    if path is None:
        sys.exit(f"error: edition {wanted} not found. Available: "
                 f"{', '.join(p.stem for p in editions)}")

    ed = json.loads(path.read_text(encoding="utf-8"))
    items = ed["items"]
    picks = [i for i in items if i.get("pick")]
    rest = [i for i in items if not i.get("pick")]

    # ---- assets ------------------------------------------------------------
    tokens = inline_fonts((BRAND / "tokens.css").read_text(encoding="utf-8"))
    page_css = (BRAND / "dashboard.css").read_text(encoding="utf-8")
    js = (ROOT / "scripts" / "dashboard.js").read_text(encoding="utf-8")
    logo = data_uri(BRAND / "img" / "logo.png")            # white wordmark, for the navy masthead
    sunburst = data_uri(BRAND / "img" / "sunburst.svg")

    # ---- tiles -------------------------------------------------------------
    counts = {k: sum(1 for i in items if i["category"] == k) for k, _, _ in CATEGORIES}
    tiles = []
    for key, label, note in CATEGORIES:
        flag = " tile--flag" if key == "competitor" else ""
        tiles.append(f"""<button type="button" class="tile{flag}" data-tile="{e(key)}" aria-pressed="false">
 <span class="tile__label">{e(label)}</span>
 <span class="tile__value">{counts[key]}</span>
 <span class="tile__note">{e(note)}</span>
</button>""")

    # ---- filters -----------------------------------------------------------
    cat_chips = ['<button type="button" class="chip" data-filter="cat" data-filter-value="all"'
                 ' aria-pressed="true">All</button>']
    for key, label, _ in CATEGORIES:
        cat_chips.append(f'<button type="button" class="chip" data-filter="cat" '
                         f'data-filter-value="{e(key)}" aria-pressed="false">{e(label)} '
                         f'<span class="chip__count">{counts[key]}</span></button>')

    # Sort by count, then by name. The country code breaks ties on purpose: this
    # starts from a set, whose iteration order varies per process, so a
    # count-only key would order equal-sized countries differently on each build
    # and make an unchanged page look modified in git every time.
    present = sorted({i["country"] for i in items},
                     key=lambda c: (-sum(1 for i in items if i["country"] == c), c))
    country_chips = ['<button type="button" class="chip" data-filter="country" '
                     'data-filter-value="all" aria-pressed="true">Everywhere</button>']
    for c in present:
        n = sum(1 for i in items if i["country"] == c)
        country_chips.append(f'<button type="button" class="chip" data-filter="country" '
                             f'data-filter-value="{e(c)}" aria-pressed="false">'
                             f'{e(COUNTRY_LABEL.get(c, c.upper()))} '
                             f'<span class="chip__count">{n}</span></button>')

    # ---- register ----------------------------------------------------------
    groups = []
    for key, label, note in CATEGORIES:
        rows = [render_row(i) for i in rest if i["category"] == key]
        if not rows:
            continue
        groups.append(f"""<section class="cat" data-group>
 <div class="cat__head"><h3>{e(label)}</h3>
  <span class="cat__count" data-group-count>{len(rows)} items</span></div>
 {''.join(rows)}
</section>""")

    # ---- coverage ----------------------------------------------------------
    failed = ed.get("sources_failed") or []
    warned = ed.get("sources_warned") or []
    problems = ""
    if failed or warned:
        lis = "".join(f"<li>{e(x['source'])} — {e(x.get('error') or x.get('warn'))}</li>"
                      for x in failed + warned)
        problems = f"<ul>{lis}</ul>"
    coverage_class = "note note--warn" if failed else "note"

    picks_section = ""
    if picks:
        picks_section = f"""<section class="section" data-group>
 <div class="section__head"><h2>What matters this week</h2><span class="section__rule"></span></div>
 <div class="picks">{''.join(render_pick(i) for i in picks)}</div>
</section>"""

    others = [p.stem for p in editions if p != path]
    previous = ""
    if others:
        rows_html = "".join(
            f'<div class="edition-row"><span class="edition-row__id">{e(o)}</span>'
            f'<span class="edition-row__meta">in the project archive</span></div>'
            for o in reversed(others))
        previous = f"""<section class="section">
 <div class="section__head"><h2>Earlier editions</h2><span class="section__rule"></span></div>
 <div class="editions">{rows_html}</div>
</section>"""

    gen = datetime.fromisoformat(ed["published_at"])
    generated = f"{gen.day} {MONTHS_LONG[gen.month - 1]} {gen.year}"
    window = f"{long_date(ed['window']['from'])} to {long_date(ed['window']['to'])}"

    doc = f"""<meta charset="utf-8">
<title>RV News — European RV industry monitor</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="Weekly monitor of the European RV industry for Thetford product management.">
<style>
__CSS__
</style>

<header class="masthead">
 <div class="wrap masthead__inner">
  <img class="masthead__logo" src="{logo}" alt="Thetford">
  <h1 class="masthead__title">RV News</h1>
  <p class="masthead__standfirst">What happened in the European RV industry, read for product
   management: new vehicles, components, competitor moves and market data.</p>
  <div class="masthead__edition">
   <strong>Edition {e(ed['edition'])}</strong>
   <span>{e(window)}</span>
   <span>{ed['selected']} items from {ed['sources_ok']} sources</span>
  </div>
 </div>
</header>

<main class="wrap">
 <div class="summary">{''.join(tiles)}</div>

 {picks_section}

 <div class="controls">
  <div class="wrap controls__inner">
   <div class="search">
    <label class="sr-only" for="q">Search these items</label>
    <input id="q" type="search" placeholder="Search brand, model or keyword" autocomplete="off">
   </div>
   <div class="chipset">{''.join(cat_chips)}</div>
   <div class="chipset">{''.join(country_chips)}</div>
   <p class="controls__status" id="status">Showing all {len(items)} items</p>
  </div>
 </div>

 <div id="register">{''.join(groups)}</div>

 <div class="empty" id="empty" hidden>
  <p>Nothing matches those filters.</p>
  <button type="button" class="chip" id="reset">Clear filters</button>
 </div>

 <section class="section">
  <div class="section__head"><h2>How this edition was put together</h2><span class="section__rule"></span></div>
  <div class="{coverage_class}">
   <h3>Coverage and judgement</h3>
   <p>{ed['collected']} articles were collected from {ed['sources_ok']} sources over
    {e(window)}. {ed['selected']} were selected, {ed['merged']} duplicate reports of the same
    story were merged into the entry that covered it best, and {ed['dropped']} were set aside as
    out of scope — travel features, campsite guides, prize draws, consumer round-ups and
    non-European trade news.</p>
   <p>Article titles, dates, sources and links are taken directly from the publishers.
    English titles and summaries are translations, and the category, the competitor flag and
    every "why it matters" note are editorial judgement rather than anything the source said.</p>
   {problems}
  </div>
 </section>

 {previous}
</main>

<footer class="wrap footer">
 <p>Built {e(generated)} for Thetford product management. Colour, type and the sunburst come
  from the Thetford design system; contrast pairs were measured rather than eyeballed.</p>
 <p>European RV manufacturers publish almost no machine-readable feeds, so new-vehicle coverage
  comes from the trade press rather than from OEM newsrooms. Feeds also expose only their most
  recent articles, so the collector pages backwards through each one to avoid missing the
  fast-moving titles.</p>
 <p>To add or remove a source, edit sources.yaml in the project folder.</p>
</footer>

<script>
__JS__
</script>"""

    # Escape the markup first, then drop in CSS and JS, which must not be
    # entity-escaped because neither language interprets HTML entities.
    css_block = asciify(f"{tokens}\n:root {{ --sunburst: url({sunburst}); }}\n{page_css}", "CSS")
    doc = entity_escape(doc).replace("__CSS__", css_block).replace("__JS__", asciify(js, "JS"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(doc, encoding="utf-8", newline="\n")
    kb = OUT.stat().st_size / 1024
    print(f"built {OUT.relative_to(ROOT)} from {path.name}")
    print(f"  {len(items)} items ({len(picks)} picks) · {kb:.0f} KB self-contained")
    for key, label, _ in CATEGORIES:
        print(f"    {label:<26} {counts[key]}")
    if kb > 16 * 1024:
        print("  WARNING page exceeds 16 MB and is cumbersome to share as one file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
