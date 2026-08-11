---
name: rv-news-refresh
description: Produce a new edition of the RV News dashboard: collect European RV industry news from the verified feed list, curate it into four categories with English summaries and why-it-matters notes, build the branded page, then deploy it through GitHub Pages.
when_to_use: Use when a new weekly edition of RV News is wanted, or when Dennis asks to refresh, update, or rerun the RV industry news monitor.
allowed-tools: Bash, Read, Write, Edit
---

Work in `RV News/`. All scripts are self-installing via `uv`. No environment
setup, no API key.

## 1. Collect

```
uv run scripts/collect.py --days 10
```

Use `--days 10` for a normal weekly run. It overlaps the previous week so a
late-published article is not missed. Use a wider window after a gap.

Read the run report before continuing:

- **Failed sources:** report them to Dennis. One dead feed is normal; three
  suggests something changed.
- **"feed is valid but contains no items":** the content may have moved to a
  custom post type. Try `?post_type=news` or a section path such as
  `/nieuws/feed/` before writing the source off.
- **"stale: newest item is N days old":** the publisher may have abandoned the
  feed. Check before trusting it. Seasonal sources already have a raised
  threshold via `stale_after_days`.
- **Zero items from an association feed in summer:** this is normal. CIVD, UNI
  VDL and ASEICAR publish in bursts around CMT in January and Caravan Salon in
  late August.

The pending queue accumulates, so collecting twice before curating is safe.

## 2. Curate

Dump the queued titles compactly, showing index, date, source, language and
title. Triage on titles first. Read the source text only for items that survive
triage.

Write `scripts/curate_<edition>.py`, modelled on the previous edition's script.
Reference items by their index in the sorted pending list instead of retyping
titles and URLs. Sort identically, published descending and stable, or the
indexes shift.

For each selected item, decide:

- **category:** `vehicles`, `accessories`, `competitor` or `industry`
- **competitor flag:** Dometic, Truma, Alde, Webasto, Vitrifrigo, Fiamma, Thule,
  Airxcel, Mestic or Victron
- **English title and summary:** translate; most sources are not English
- **brands mentioned**
- **duplicates:** merge the strongest version and record the others as "also
  covered by"

Pick three to five editor's picks and write a "why it matters for Thetford" note
for each. Anchor these in Thetford's product space: sanitation, refrigeration,
cooking, water and climate, and in what would change a decision. "Truma is
claiming the in-cabin control layer" is useful. "This is interesting for the
industry" is not.

If a chosen pick came from Google News, open its Google News link in a browser
and wait for the original publisher page. Add its final direct URL as
`"article_url": "https://..."` in the curated record. Keep the collected Google
News `url` and source name unchanged for provenance. The image step uses
`article_url`, because Google News does not reliably expose the original page to
an HTTP client.

Drop without guilt: travel features, campsite guides, prize draws and
competitions, consumer listicles, obituaries, road accidents, and US or
Australian trade news with no European read-through.

## 3. Cache editor-pick images

After the curation script has created the edition, fetch a lead image for each
editor's pick:

```
uv run scripts/fetch_pick_images.py <edition>
```

It reads each chosen article's `og:image` or `twitter:image`, stores a compressed
local JPEG under `assets/picks/`, and records that local path in the edition. It
never hotlinks an image, so the built page remains self-contained. If a publisher
does not expose an image, the affected pick stays full-width without a placeholder.

## 4. Build and deploy

```
uv run scripts/build.py
```

Review `build/index.html` in a browser. Then commit and push it to `main`. The
`Deploy RV News` GitHub Actions workflow publishes the `build/` folder to the
stable GitHub Pages URL. Check that action has completed successfully before
reporting the edition live.

## Rules that are easy to get wrong

- **Never colour-code the four categories.** They are already separated by
  section and named on a chip. Amber marks competitor items as a status, always
  with the word "Competitor", and Thetford blue is the single interactive accent.
- **Brand tone:** sentence case, plain-spoken, no emoji and no exclamation
  marks. This comes from the Thetford design system and applies to every word on
  the page.
- **Do not alter the logo or sunburst aspect ratio.** The masthead is a column
  flex container, so the logo needs `align-self: flex-start` or it stretches.
- **Everything must be inlined.** `build.py` base64-inlines fonts, logos and
  sunburst so the page remains a portable offline snapshot. Do not add a remote
  stylesheet, font URL or image.
- **Non-ASCII is emitted as numeric entities.** This protects the page when it
  is embedded or forwarded through systems with poor charset handling. Keep CSS
  and JS ASCII.
- **Keep the coverage note honest.** It states how many articles were collected,
  selected, merged and dropped, and separates sourced facts from editorial
  judgement. Update the numbers; never quietly drop a failed source.

## Adding a source

Edit `sources.yaml`, one block per source. Verify that a candidate feed returns
real dated items before adding it, and record why it earned a slot. European RV
manufacturers almost never publish feeds; of roughly 30 checked, only Volkswagen
had one. Prefer a trade title over an OEM newsroom scrape.
