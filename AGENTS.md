# RV News — agent instructions

Weekly monitor of the European RV industry for Thetford's product-management
team. Collects from 24 verified trade sources in six languages, curates them into
four categories with English summaries, and renders one self-contained HTML page.

**`CLAUDE.md` in this folder is the full handover — intent, architecture, and the
reasoning behind decisions that look arbitrary. Read it before changing anything.**
This file is the short version plus the things specific to running outside Claude
Code.

## Setup

Nothing to install but [`uv`](https://docs.astral.sh/uv/). The scripts declare
their own dependencies inline (PEP 723) and resolve them on first run. No venv,
no requirements.txt, no API key.

```
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Python 3.11+. Everything else is handled by `uv run`.

## The three commands

```
uv run scripts/collect.py --days 10     # fetch feeds -> digests/pending.json
uv run scripts/build.py                 # render      -> build/index.html
python3 -m http.server 4173 --directory build    # preview (use `python` on Windows)
```

Between those two sits curation, which is the actual product and is done by the
agent, not by a script. The procedure is in
`.claude/skills/rv-news-refresh/SKILL.md` — read it even if your runtime does not
support skills, because it describes the editorial standard.

## Publishing

The canonical page is GitHub Pages:

  https://dennisje182.github.io/RV-News/

The `.github/workflows/deploy-pages.yml` workflow deploys `build/` on every push
to `main`. Colleagues need only this link, not a Claude or GitHub account.

### The normal workflow

1. `uv run scripts/collect.py --days 10`
2. Curate, writing `scripts/curate_<edition>.py` per the skill file.
3. `uv run scripts/build.py`
4. Open `build/index.html` in a browser and actually look at it.
5. Commit and push the edition to `main`.
6. Check that the `Deploy RV News` GitHub Actions run succeeds. The canonical
   link updates when that deployment finishes.

`build/index.html` remains self-contained. It can be emailed or dropped in
SharePoint as an offline snapshot, but GitHub Pages is the canonical link.

## Cross-platform rules

These were real bugs, fixed on 8 August 2026. Do not reintroduce them.

- **Never use `%-d` / `%-m` in `strftime`.** That is a glibc/BSD flag; Windows
  wants `%#d` and raises `ValueError` on `%-d`. Month names are spelled out in
  `build.py` on purpose — it also avoids `%b`/`%B` localising to German on a
  German Windows machine.
- **Always pass `encoding="utf-8"` to `read_text` / `write_text`.** Python
  defaults to the locale encoding. On Windows that is usually cp1252, which
  decodes these files without raising but silently corrupts them — "España"
  becomes "EspaÃ±a" and the mangled text ends up on the page.
- **`sys.stdout.reconfigure(encoding="utf-8", errors="replace")` stays.** Five
  source names contain em dashes and a cp1252 console raises
  `UnicodeEncodeError` on the first one, killing the run.
- **Use `pathlib`, never string path concatenation or a hardcoded `/`.**
- The `#!/usr/bin/env -S uv run --script` shebangs are ignored on Windows, which
  is harmless — invoke via `uv run` on every platform.

## Hard rules that are not about platforms

- **Inline every asset.** `build.py` base64-inlines fonts, logos and sunburst.
  This keeps the page portable as a single-file offline snapshot. No CDN, remote
  font or fetch.
- **Emit non-ASCII markup as numeric entities.** `build.py` handles this; keep
  CSS and JS ASCII so the page is robust when embedded or forwarded.
- **Brand:** sentence case, plain-spoken, **no emoji, no exclamation marks**.
  Never alter the logo or sunburst aspect ratio. Colour is not used to encode the
  four categories — see the decision log in `CLAUDE.md` for why.
- **Do not put relevance filtering in `collect.py`.** It collects; judgement
  belongs in curation. Keyword filters are how this kind of tool starts silently
  dropping the interesting items.
- **Do not re-run `collect.py` between dumping the triage list and running the
  curation script** — curation references items by index and new articles shift them.

## Layout

```
sources.yaml         the source list; the one file meant for hand editing
scripts/collect.py   fetch, paginate, dedupe, archive, health-check
scripts/curate_*.py  one per edition; the audit trail of what was chosen and why
scripts/build.py     render + inline into a single HTML file
brand/               Thetford tokens, Barlow fonts, logo, sunburst
archive/ digests/    everything ever collected; queued and published editions
build/index.html     the GitHub Pages payload and offline snapshot
```
