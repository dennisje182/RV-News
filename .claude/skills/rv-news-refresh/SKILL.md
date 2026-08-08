---
name: rv-news-refresh
description: Produce a new edition of the RV News dashboard — collect European RV industry news from the verified feed list, curate it into the four categories with English summaries and why-it-matters notes, build the branded page, and republish the Artifact.
when_to_use: Use when a new weekly edition of RV News is wanted, or when Dennis asks to refresh, update, or rerun the RV industry news monitor.
allowed-tools: Bash, Read, Write, Edit, Artifact
---

Work in `RV News/`. All scripts are self-installing via `uv` — no environment
setup, no API key.

## 1. Collect

```
uv run scripts/collect.py --days 10
```

Use `--days 10` for a normal weekly run: it overlaps the previous week so a
late-published article is not missed. Use a wider window after a gap.

Read the run report before continuing. It is not decoration:

- **Failed sources** — report them to Dennis. One dead feed is normal; three
  suggests something changed.
- **"feed is valid but contains no items"** — the feed is serving HTTP 200 with
  well-formed RSS and nothing in it. The content has usually moved to a custom
  post type; try `?post_type=news` or a section path like `/nieuws/feed/` before
  writing the source off.
- **"stale: newest item is N days old"** — the publisher may have abandoned the
  feed. Check before trusting it. Seasonal sources already have a raised
  threshold via `stale_after_days`.
- **Zero items from an association feed in summer is normal.** CIVD, UNI VDL and
  ASEICAR publish in bursts around CMT in January and Caravan Salon in late
  August.

The pending queue accumulates, so collecting twice before curating is safe.

## 2. Curate — this is the part that carries the value

Dump the queued titles compactly (index, date, source, language, title) and
triage on titles first. Do not read 300 full summaries; pull the text only for
the items that survive triage.

Then write `scripts/curate_<edition>.py`, modelled on the previous edition's
script. Reference items **by their index in the sorted pending list** rather than
retyping titles and URLs — that is what keeps links and dates accurate. Sort
identically (`published` descending, stable) or the indexes shift.

For each selected item, decide:

- **category** — `vehicles`, `accessories`, `competitor`, `industry`
- **competitor flag** — Dometic, Truma, Alde, Webasto, Vitrifrigo, Fiamma,
  Thule, Airxcel, Mestic, Victron
- **English title and summary** — translate; most sources are not English
- **brands** mentioned
- **duplicates** — the same story often runs in three outlets. Merge into the
  best version and record the others as "also covered by".

Pick **three to five editor's picks** and write a "why it matters for Thetford"
note for each. Anchor these in Thetford's actual product space — sanitation,
refrigeration, cooking, water, climate — and in what would change a decision.
"Truma is claiming the in-cabin control layer" is useful; "this is interesting
for the industry" is not.

Drop without guilt: travel features, campsite guides, prize draws and
competitions, consumer listicles, obituaries, road accidents, and US or
Australian trade news with no European read-through.

## 3. Build and publish

```
uv run scripts/build.py
```

Then publish with the Artifact tool using the **same file path** so the URL stays
stable and Dennis does not have to reshare the link. Use favicon 🚐 and a label
naming the edition.

## Rules that are easy to get wrong

- **Never colour-code the four categories.** They are already separated by
  section and named on a chip. Colour does exactly two jobs: amber marks
  competitor items as a status (always with the word "Competitor", never colour
  alone), and Thetford blue is the single accent for interactive state.
- **Brand tone: sentence case, plain-spoken, no emoji, no exclamation marks.**
  This comes from the Thetford design system and applies to every word on the
  page.
- **Do not alter the logo or sunburst aspect ratio.** The masthead is a column
  flex container, so the logo needs `align-self: flex-start` or it stretches.
- **Everything must be inlined.** Published Artifacts block all external
  requests. `build.py` base64-inlines fonts, logo and sunburst; do not add a
  remote stylesheet, font URL or image.
- **Non-ASCII is emitted as numeric entities** because the Artifact host owns
  `<head>` and our charset declaration may land too late. Keep CSS and JS ASCII.
- **Keep the coverage note honest.** It states how many articles were collected,
  selected, merged and dropped, and separates sourced facts from editorial
  judgement. Update the numbers, never quietly drop a failed source.

## Adding a source

Edit `sources.yaml` — one block per source, comments explain every field. Verify
a candidate feed actually returns dated items before adding it, and record why
it earned a slot. European RV manufacturers almost never publish feeds; of
roughly 30 checked, only Volkswagen had one, so new-vehicle coverage comes from
trade press. Prefer a trade title over an OEM newsroom scrape.
