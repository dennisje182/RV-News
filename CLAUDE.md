# RV News — agent handover

Read this before changing anything in `RV News/`. It records intent and the
reasoning behind decisions that look arbitrary but are not.

**This project is unrelated to the SKU forecasting work described in the parent
`MyProjects/CLAUDE.md`.** None of the forecasting rules apply here: there are no
workbooks, no openpyxl, no OEM/AM scope split, no cannibalization model.

Four documents, no overlap:

| Document | Audience | Contains |
|---|---|---|
| `README.md` | Dennis | How to refresh, share, and add a source |
| `AGENTS.md` | non-Claude agents (Codex etc.) | Setup, commands, and what they cannot do |
| `.claude/skills/rv-news-refresh/SKILL.md` | agent, weekly | The step-by-step edition procedure |
| this file | agent, on arrival | Intent, architecture, and why |

**This folder is self-contained.** Its skill and `launch.json` live in
`RV News/.claude/`, not at the parent level, so the whole project can be copied
or cloned on its own without losing the refresh procedure.

---

## 1. Intent

A weekly monitor of the European RV industry for Thetford's product-management
team: new vehicles from OEMs, accessories and components, competitor moves, and
market data. Those four categories are the user's own, chosen explicitly.

The job it does: **let a product manager see in about a minute what happened in
the industry this week, and what it means for Thetford.** It is not a link dump
and not a clipping archive. The editorial layer — translation, deduplication,
category, and the "why it matters for Thetford" notes — is the product. The
collector is plumbing.

Built 7 August 2026. First edition `2026-W32`.

## 2. Constraints that shaped everything

- **Dennis is a product manager, not a developer**, and is both the user and the
  maintainer. Anything requiring environment setup, dependency management, or a
  deploy step will rot. Hence `uv` inline script metadata: the scripts install
  their own dependencies on first run and there is no venv to manage.
- **Delivery is GitHub Pages**, so every colleague can open one stable link without
  a Claude or GitHub account. A push to `main` deploys the committed `build/`
  folder through GitHub Actions. The page remains a **single self-contained file**
  so it can also be shared as an offline snapshot.
- **Weekly cadence**, chosen by the user. See §6 on why this nearly broke the tool.
- **The brand is not ours to invent.** Colour, type, and the sunburst come from the
  "Thetford Design System" project in Claude Design (projectId
  `019dfe69-077d-7041-adf2-13c4b2ad0b13`, readable with the `DesignSync` tool).
  `brand/tokens.css` mirrors it. Do not add brand values that are not in it.
- **No API key anywhere.** Curation happens in an agent session, so there is no
  per-article cost and nothing to sign up for.

## 3. Pipeline

Three stages, deliberately separate so a failure in one is legible:

```
sources.yaml ──► collect.py ──► archive/items.json     (everything ever seen)
                     │
                     └───────►  digests/pending.json   (collected, not yet curated)
                                     │
                        curate_<edition>.py            (judgement — the product)
                                     │
                                     ▼
                            digests/<edition>.json      (a curated edition)
                                     │
                                 build.py               (inlines assets)
                                     │
                                     ▼
                            build/index.html ──► GitHub Pages (same URL every time)
```

`collect.py` decides nothing about relevance beyond a date window. `curate_*.py`
holds all judgement. `build.py` holds all presentation. Keep it that way — the
temptation to put keyword filtering in the collector is how this kind of tool
starts silently dropping the interesting items.

## 4. File map

```
CLAUDE.md                 this file
README.md                 user-facing instructions (Dennis)
sources.yaml              24 verified sources; the one file meant for hand editing
scripts/collect.py        fetch, paginate, dedupe, archive, health-check   (419 ln)
scripts/curate_*.py       one per edition; the audit trail of what was chosen
scripts/build.py          render + base64-inline into one HTML file        (399 ln)
scripts/dashboard.js      search and filter behaviour                      (135 ln)
brand/tokens.css          mirror of the Thetford design system             (156 ln)
brand/dashboard.css       page styles built on those tokens                (511 ln)
brand/fonts/*.woff2       Barlow, 5 weights x latin + latin-ext, 126 KB total
brand/img/logo.png        WHITE wordmark — used, for the navy masthead
brand/img/logo-dark.png   black wordmark — unused, kept for a light-masthead variant
brand/img/sunburst.svg    signature mark, used as the masthead watermark
archive/items.json        every article ever collected
digests/pending.json      accumulating queue awaiting curation
digests/2026-W32.json     published edition
build/index.html          the GitHub Pages payload (~360 KB self-contained)
```

Country flag SVGs were downloaded early and **deliberately removed**: text country
labels are clearer at the size used and match the brand's plain-spoken tone, and
Spain's flag alone was 230 KB. Do not reintroduce them without a reason.

## 5. Hard rules

Breaking any of these produces a page that looks fine locally and fails once
published, or quietly violates the brand.

- **Inline everything.** No external stylesheet, font URL, script or image.
  `build.py` base64-inlines fonts, logo and sunburst, keeping the page portable as
  a single-file offline snapshot.
- **Emit non-ASCII as numeric entities.** This protects the page when it is
  embedded or forwarded through systems with poor charset handling. `build.py`
  escapes markup above U+007F and folds CSS and JS to ASCII.
- **Deploy the committed `build/` folder** by pushing to `main`. GitHub Pages
  keeps the canonical URL stable, so colleagues never need a new link.
- **Never alter the logo or sunburst aspect ratio** (brand rule). The masthead is a
  column flex container, so the logo needs `align-self: flex-start`; without it
  `align-items: stretch` pulled it to 1072px wide and squashed it.
- **Brand tone:** sentence case, plain-spoken, **no emoji, no exclamation marks**.
  Applies to every word on the page.
- **Do not colour-code the four categories.** See §6.
- **Keep the coverage note honest.** It states collected / selected / merged /
  dropped counts and separates sourced fact from editorial judgement. Update the
  numbers; never quietly drop a failed source from it.

## 6. Decision log

**Weekly collection required backwards pagination.** Most of these feeds expose
only their latest ~10 articles and the busiest, reisemobil-international.de, posts
5–8 per day — one page holds under two days. A naive weekly poll would have
silently lost roughly 80% of new-model coverage while appearing healthy. The
`pages:` field walks `?paged=N` until items fall outside the window or the site
re-serves page 1. On the first real run this turned 10 items into 50 from that one
source. **If you make collection less frequent, raise `pages` to match.**

**Health checks are on item count and article age, not HTTP status.** Several real
sources (`civd.de/feed/`, `campingtrend.nl/feed/`, `thetford.com/en/feed/`,
`baileyofbristol.co.uk/feed/`) return HTTP 200 with well-formed RSS, correct
channel metadata, a fresh `lastBuildDate`, and **zero items**. A status-code check
reads those as a quiet week forever. `stale_after_days` is per-source because
industry associations publish in seasonal bursts — warning on CIVD every summer
would train the reader to ignore warnings.

**Categories are not colour-coded.** The four brand-derived hues were run through
the dataviz palette validator and navy + green failed as data colours (outside
the lightness band, chroma below the floor — they read grey as marks). That
pointed at a better answer rather than a workaround: categories are already
separated by section heading and named on a text chip, so hues would be redundant
colour. Colour now does exactly two jobs — amber `#E0A100` marks competitor items
as **status** (always with the word "Competitor", never colour alone) and Thetford
blue marks interactive state. This also avoids the rainbow-dashboard look.

**Link text uses blue-700, not the primary blue.** Measured, not eyeballed:
`#0086CD` on white is 3.97:1 — fine for fills and marks, below AA for body-size
text. Link text uses `#005A8A` (7.42:1). In dark mode the accent lifts to
`#80C2E6` on navy (7.95:1). Filled chips use blue-700 so white labels clear AA.

**Dark mode is its own steps, and its cards need borders.** Navy `#00273C` is the
design system's own dark surface, so the dark theme is grounded there rather than
inverted. Surface-to-ground separation is only 1.15:1, which is why `.tile`,
`.pick`, and `.note` carry a hairline border — remove it and cards dissolve into
the background in dark mode.

**Theme token blocks are order-sensitive. Do not reorder them.** A media query
adds no specificity, so a plain `:root` block placed *after*
`@media (prefers-color-scheme: dark)` silently overrides it. That shipped once:
the light defaults for `--accent-tint`, `--accent-text`, `--accent-fill`, and
`--color-surface-raised` sat after the dark block, so under OS dark mode the
"why it matters" callout kept a light blue background while inheriting light
text, and was unreadable. The light `:root` block must stay first, the dark media
query second, and the `[data-theme]` blocks last.

It also shows how to test a theme properly: verifying with
`data-theme="dark"` passes even when this is broken, because that selector
outranks bare `:root`. **Always check the OS-preference path too** — set the
emulated colour scheme and read the computed values back, rather than trusting
the toggle.

**Curation references items by index, not by retyped text.** `curate_*.py` sorts
`pending.json` by `published` descending (stable sort, so indexes are
reproducible) and refers to items positionally. Titles, URLs, sources, and dates
come from collected data. Retyping 96 URLs by hand is where errors would enter.
**Do not re-run `collect.py` between dumping the triage list and running the
curation script** — new articles shift the indexes.

**The pending queue accumulates.** An earlier version overwrote `pending.json`
each run, so collecting twice before curating silently discarded the queue.
Now new items merge into it and it is only cleared when an edition is published.

**New-vehicle coverage comes from trade press, not OEMs.** Of ~30 European
manufacturer sites checked, exactly one (Volkswagen) publishes a usable feed. The
German trade press covers launches faster than the OEMs announce them, so this is
a substitution, not a gap. Prefer adding a trade title over scraping an OEM.

**Google News is kept despite poor weekly yield.** Its results are not date-sorted
and skew heavily archival — the competitor query returned 80 items of which one
fell inside a 10-day window. It stays because Truma, Alde, Webasto, Vitrifrigo,
and Fiamma publish no usable feeds at all, and Fiamma's own site has an expired
TLS certificate. Treat it as a monthly net.

**The first edition used a 30-day window** (`--days 30`) so it had substance;
routine runs use `--days 10`, which overlaps the previous week deliberately.

## 7. Source quirks worth not rediscovering

These cost real research time to establish. All verified 7 August 2026.

- Three of the best feeds are **not** at the conventional path: promobil is
  `/rss/all` (no `/feed/`; `/rss/news` was abandoned in 2025), CIVD needs
  `?post_type=news`, Campingtrend needs `/nieuws/feed/`.
- MFN investor-relations feeds **require `?lang=en`** or every Dometic and Thule
  release arrives twice, English and Swedish. They carry financial and regulatory
  news only — never product launches.
- `camperprofessional.de` declares `en-US` while serving German. **Never route on
  a feed's declared language**; `sources.yaml` states it by hand.
- Most WordPress feeds put the full article in `content:encoded` and only an
  excerpt in `description` — `entry_text()` prefers the former.
  `reisemobil-international.de` ships **empty** descriptions (`title_only: true`).
- Knaus Tabbert is the one OEM scrape, chosen because it pre-labels its releases
  ("New products" / "Financial news"). Its rows carry dates **inside the title
  text** as `DD.MM.YYYY`, which the curation step parses out.
- Dead ends: `ecf-europe.org` does not exist (it is `e-c-f.com`); `caravaning.de`
  and `camping-cars-caravans.de` have been absorbed into their stablemates;
  `sog.de` is an unrelated ERP vendor; `webasto.com`'s newsroom needs a headless
  browser. Bot-blocked but probably real: outandaboutlive.co.uk, adria-mobil.com,
  vitrifrigo.com, dometicgroup.com.

## 7a. Running it on another machine or another agent

Made portable on 8 August 2026 after being built on macOS. Three genuine bugs
were found and fixed; see `AGENTS.md` for the rules that keep them fixed.

- **`%-d` in `strftime`** appeared three times in `build.py`. It is a glibc/BSD
  flag — Windows raises `ValueError`, so the build died outright. Month names are
  now spelled out, which also stops `%b`/`%B` localising to German on a German
  Windows machine and putting "Okt" on an English page.
- **Ten `read_text` / `write_text` calls had no explicit encoding.** Python falls
  back to the locale encoding, cp1252 on most Windows installs. Measured: these
  files *decode* under cp1252 without raising and come out corrupted — "España"
  becomes "EspaÃ±a". Silent corruption, not a crash, which is worse. All calls now
  pin `encoding="utf-8"`.
- **Five source names contain em dashes and get printed.** A cp1252 console
  raises `UnicodeEncodeError` on the first one and takes the run down, so both
  scripts reconfigure stdout to UTF-8 with `errors="replace"`.

Two more that only surface across machines:

- **Generated files pin `newline="\n"`.** Python's text mode translates newlines
  to the host convention, so a page built on Windows was 1,775 bytes larger than
  the identical page built on macOS — one per line. Git reported the file as
  changed while showing "no content changes found", which is a confusing thing to
  hand a non-developer.
- **The build must be reproducible.** Country filter chips were ordered by item
  count alone, starting from a set, and set iteration order varies per process.
  France and the UK both had 7 items, so they swapped places at random between
  builds. Any ordering derived from a set needs a tiebreaker.

`uv`, `feedparser`, `requests`, `beautifulsoup4`, `lxml`, and `pyyaml` are all
cross-platform, and paths use `pathlib` throughout. The `#!/usr/bin/env -S uv run
--script` shebangs are inert on Windows; invoke through `uv run` everywhere.

**Verified on Windows 11 with uv 0.12.3 on 8 August 2026**: all 24 sources
collected with no failures, non-ASCII source names printed correctly, the archive
transferred through Git intact (151 of 159 items recognised as already seen), and
`build.py` produced a file byte-identical to the macOS build.

**GitHub Pages is the publication route.** After building, commit and push to
`main`; the `Deploy RV News` workflow publishes `build/` to the stable link.
Check that action has succeeded before treating the live page as updated.

**A corporate laptop may break collection** in ways that are not this project's
fault: a TLS-inspecting proxy makes `requests` reject certificates, and some of
these publishers may be blocked outright. If many sources fail at once with
certificate or connection errors on a work network but succeed elsewhere, that is
the network, not the collector.

## 8. Verifying a change

`build.py` prints size and per-category counts. The page is intentionally kept
small enough to stay convenient to share as a self-contained offline snapshot.

To check behaviour, serve `build/` and drive it with JavaScript rather than
screenshots:

```bash
python3 -m http.server 4173 --directory "RV News/build"
```

A `.claude/launch.json` entry named `rv-news` exists for `preview_start`. **The
browser pane's compositor stopped producing frames after programmatic scrolling
during this build** — screenshots went blank while the DOM was provably fine. If
that happens, verify with `javascript_tool` (`elementFromPoint`, computed styles,
visible-row counts) instead of burning time on the renderer.

The functional checks worth repeating after touching `dashboard.js`: each category
filter's count matches its tile; clicking an active chip clears it; multi-word
search narrows rather than widens; no-match shows the empty state and hides all
group headings; reset clears the URL hash; and a hash like
`#cat=competitor&country=de` restores that view on load, since shareable filtered
links are a feature.

## 9. Known limitations

- **Google News items in edition 2026-W32 name the aggregator, not the publisher.**
  `collect.py` now captures the publisher from the ` - Publisher` suffix, but only
  for newly collected articles, so this self-corrects from the next edition.
- **The Knaus Tabbert scrape is layout-dependent.** It reports a selector that
  matched nothing rather than failing silently, and its selector currently also
  catches the page's own "Press releases" nav link, which curation drops by hand.
  Tightening that selector is a small, worthwhile fix.
- **Refresh is a command, not a schedule.** Local scheduling would only fire with
  the laptop awake and the app open — not dependable for a Monday morning.
  Server-side automation is possible but is a different build: hosted, and it
  would need an API key, which changes the no-key property in §2.
- **`archive/items.json` is a flat JSON file.** Fine for years at ~150 items a
  week; if it ever gets slow, SQLite is the move, not sharding.
- **Category 2 (accessories) rests on few sources** — mainly Campingtrend,
  promobil, and Victron. It is the weakest coverage and the best place to add.

## 10. Extending it

- **Add a source:** a block in `sources.yaml`. Verify it returns real dated items
  first, and record why it earned a slot. Set `pages:` if it posts more than
  roughly twice a day.
- **Add a trend chart:** deliberately omitted. With one edition there was no trend
  to plot, and faking one with a single data point would have been dishonest. From
  three or four editions, items-per-category-per-week becomes worth showing — read
  the `dataviz` skill first and validate any palette with its script.
- **Change the layout:** rows are intentionally dense hairline-divided records
  rather than cards, because the register runs to ~50 items in the vehicles
  section and cards would triple its height.
- **Translate the whole page:** the audience is a pan-European team, so English is
  the deliberate common language even though most sources are not English. Every
  translated item shows its original headline for verification.
