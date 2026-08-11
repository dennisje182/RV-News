# RV News

A weekly monitor of the European RV industry for Thetford product management:
new vehicles from OEMs, accessories and components, competitor moves, and market
data. It collects from 24 verified trade sources in six languages, translates and
sorts what matters, then publishes a Thetford-branded page colleagues can open by
link.

## Getting a new edition

Ask your coding agent, in this folder:

> refresh RV News

That follows the `rv-news-refresh` procedure: collect, curate, cache the selected
editor-pick images and build. It takes
a few minutes, most of which is the reading. Commit and push the completed
edition to update the shared page.

You do not need a Python environment, an account or an API key. The scripts
install what they need on first run via `uv`.

## Sharing it with your team

The canonical page is GitHub Pages:

  https://dennisje182.github.io/RV-News/

Colleagues need only this link, not a Claude or GitHub account. Every push to
`main` triggers the `Deploy RV News` GitHub Actions workflow, which publishes the
committed `build/` folder. Check that workflow has completed successfully before
telling colleagues a refresh is live.

### The offline fallback

`build/index.html` is genuinely self-contained: one file, no internet needed,
with fonts and logos embedded. Email it or drop it in SharePoint when an offline
snapshot is useful. Each copy is a snapshot, so GitHub Pages remains the
canonical version.

## Adding or removing a source

Open `sources.yaml`. It is a plain list, one block per source, with a comment
above each explaining why it is there. To stop using one, add `disabled: true`
under it rather than deleting it, so the note about why it was added survives.

If you spot a publication that should be in here, ask the agent to verify that it
publishes a usable feed before adding it.

## Working on it from another computer

The whole project is one self-contained folder. Copy or clone `RV News/` and the
refresh procedure comes with it. It runs on Windows, macOS and Linux. The only
thing to install is [`uv`](https://docs.astral.sh/uv/); the scripts pull their
own dependencies on first run.

```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Working at the office with Codex

Codex can run the whole edition: collect, curate, build, commit and push. The
GitHub Pages deployment then updates the shared link automatically. The required
workflow is in `AGENTS.md`.

Before pushing, review `build/index.html` in a browser. After pushing, check the
`Deploy RV News` action has succeeded. A work network may block the feeds:
corporate proxies that inspect encrypted traffic can make the collector reject
certificates, and some publishers may be blocked outright.

## What is in the folder

```
sources.yaml            the source list, the one file worth editing by hand
scripts/collect.py      fetches the feeds and archives everything it finds
scripts/curate_*.py     one per edition: what was selected, and why
scripts/fetch_pick_images.py  saves lead images for editor's picks
scripts/build.py        renders the branded, self-contained page
scripts/dashboard.js    the search and filter behaviour
brand/                  Thetford tokens, Barlow fonts, logo and sunburst
archive/items.json      every article ever collected, so nothing is lost
digests/pending.json    collected but not yet curated
digests/2026-W32.json   a published edition
build/index.html        the page published to GitHub Pages
```

## Things worth knowing

**New-vehicle news comes from trade press, not manufacturers.** Around 30
European OEM sites were checked and exactly one, Volkswagen, publishes a
machine-readable feed. The German trade press covers launches faster than the
OEMs announce them, so this is a substitution rather than a gap.

**The collector pages backwards through each feed.** Most feeds expose only their
latest 10 articles, and the busiest posts 5 to 8 per day. A weekly collection
would otherwise silently miss most new-model coverage.

**A feed returning nothing is treated as a problem, not a quiet week.** Several
real sources serve a valid, fresh-looking RSS document with zero items in it. The
collector reports on item count and article age, not just HTTP status.

**Google News is a monthly net, not a weekly feed.** Its results are not sorted
by date and skew heavily archival. It is included because Truma, Alde, Webasto,
Vitrifrigo and Fiamma publish no usable feeds at all.

**Sourced facts and judgement are kept separate.** Titles, dates, sources and
links come straight from publishers. English summaries are translations, and the
category, competitor flag and every "why it matters" note are editorial
judgement. The page reports how many articles were collected, selected, merged
and dropped.

## Known limitations

- Google News items show the publisher only from the next edition onward.
- The Knaus Tabbert scrape depends on their page layout. If they redesign, the
  collector reports that its selector matched nothing rather than failing quietly.
- Refreshing is a command, not a schedule. Local scheduling would run only while
  the laptop is awake and the app is open.
- Fiamma's own site cannot be read at all because its TLS certificate is expired,
  so it is covered only via trade press.
