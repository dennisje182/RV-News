# RV News

A weekly monitor of the European RV industry for Thetford product management:
new vehicles from OEMs, accessories and components, competitor moves, and market
data. It collects from 23 verified trade sources in six languages, translates and
sorts what matters, and publishes a Thetford-branded page you can share with
colleagues by link.

## Getting a new edition

Ask Claude Code, in this folder:

> refresh RV News

That runs the `rv-news-refresh` skill end to end: collect, curate, build,
republish. It takes a few minutes, most of which is the reading. The link stays
the same, so colleagues never need a new one.

You do not need a Python environment, an account, or an API key. The scripts
install what they need on first run via `uv`.

## Sharing it with your team

The published page is **private until you share it**. Open it and use the share
menu on the page. After that, every refresh updates the same link.

## Adding or removing a source

Open `sources.yaml`. It is a plain list — one block per source, with a comment
above each explaining why it is there. To stop using one, add `disabled: true`
under it rather than deleting it, so the note about why it was added survives.

If you spot a publication that should be in here, just say so and Claude will
check whether it publishes a usable feed before adding it.

## Working on it from another computer

The whole project is one self-contained folder — copy or clone `RV News/` and
everything comes with it, including the refresh instructions. It runs the same on
Windows, macOS, and Linux. The only thing to install is
[`uv`](https://docs.astral.sh/uv/); the scripts pull their own dependencies on
first run.

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Two things to know before you rely on it at work:

**Publishing only works from Claude Code.** Collecting, curating, and building
work in any coding agent, ChatGPT Codex included. Updating the shared link does
not — that needs Claude's Artifact tool. From a different machine or
conversation, give Claude the URL in `digests/PUBLISHED.txt` and ask it to
republish to *that* artifact, otherwise you get a second link and have to ask
everyone to re-bookmark.

**A work network may block the feeds.** Corporate proxies that inspect encrypted
traffic can make the collector reject certificates, and some publishers may be
blocked outright. If lots of sources fail at once at the office but work at home,
that is the network rather than the tool.

## What is in the folder

```
sources.yaml            the source list — the one file worth editing by hand
scripts/collect.py      fetches the feeds, archives everything it finds
scripts/curate_*.py     one per edition: what was selected, and why
scripts/build.py        renders the branded, self-contained page
scripts/dashboard.js    the search and filter behaviour
brand/                  Thetford tokens, Barlow fonts, logo, sunburst
archive/items.json      every article ever collected, so nothing is lost
digests/pending.json    collected but not yet curated
digests/2026-W32.json   a published edition
build/index.html        the page that gets published
```

## Things worth knowing

**New-vehicle news comes from trade press, not manufacturers.** Around 30
European OEM sites were checked and exactly one (Volkswagen) publishes a
machine-readable feed. The German trade press covers launches faster than the
OEMs announce them, so this is a substitution rather than a gap.

**The collector pages backwards through each feed.** Most of these feeds only
expose their latest 10 articles, and the busiest posts 5–8 per day — a single
page holds under two days. Weekly collection would otherwise silently miss most
new-model coverage.

**A feed returning nothing is treated as a problem, not a quiet week.** Several
real sources serve a valid, fresh-looking RSS document with zero items in it.
The collector reports on item count and article age, not just HTTP status.

**Google News is a monthly net, not a weekly feed.** Its results are not sorted
by date and skew heavily archival — one query returned 80 items of which one was
inside a 10-day window. It is included because Truma, Alde, Webasto, Vitrifrigo
and Fiamma publish no usable feeds at all.

**Sourced facts and judgement are kept separate.** Titles, dates, sources and
links come straight from publishers. English summaries are translations, and the
category, the competitor flag and every "why it matters" note are editorial
judgement. The page says so, and reports how many articles were collected,
selected, merged and dropped.

**Colours were measured, not chosen by eye.** Thetford blue on white is 3.97:1 —
fine for fills, too low for body-size link text — so link text uses blue-700 at
7.42:1, and the dark theme lifts the accent to blue-300 on navy. The four
categories are deliberately not colour-coded; colour marks competitor items and
interactive state only.

## Known limitations

- **Google News items show the publisher only from the next edition onward.**
  Edition 2026-W32 lists the aggregator as the source for those items. The fix is
  in `collect.py` but only applies to newly collected articles.
- **The Knaus Tabbert scrape depends on their page layout.** If they redesign,
  the collector will report that the selector matched nothing rather than fail
  quietly. Its rows also carry dates inside the title text rather than as
  metadata, which the curation step parses out.
- **Refreshing is a command you run, not a schedule.** Scheduling it on your Mac
  would only fire when the laptop is awake and the app is open, which is not
  dependable for a Monday morning. Server-side automation is possible but is a
  different setup — hosted, and needing an API key.
- **Fiamma's own site cannot be read at all.** Their TLS certificate is expired,
  so they are covered only via trade press.
