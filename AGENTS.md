# RV News — agent instructions

Weekly monitor of the European RV industry for Thetford's product-management
team. Collects from 23 verified trade sources in six languages, curates them into
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

## Publishing — read this if you are not Claude Code

The page is delivered as a **Claude Artifact** at a stable URL that Dennis has
already shared with his team. Republishing requires Claude Code's `Artifact` tool.

- **Claude Code, any machine:** publish `build/index.html`. From a conversation
  that did not originally publish it, pass the existing artifact URL as the `url`
  argument or you will mint a new link and Dennis will have to reshare.
  The current one is in `digests/PUBLISHED.txt`.
- **Codex or any other agent:** you can collect, curate, and build, but you
  **cannot** republish to that URL. Build the file and hand it over — it is fully
  self-contained, so it works from a file share, an email attachment, or
  SharePoint with no assets alongside it. Say clearly that the shared Artifact
  link is now behind the local build until someone republishes it.

Do not invent a second distribution channel without asking. One stale link is a
smaller problem than two links that disagree.

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

- **Inline every asset.** Artifacts block all external requests. `build.py`
  base64-inlines fonts, logo, and sunburst. No CDN, no remote font, no fetch.
- **Emit non-ASCII markup as numeric entities.** The Artifact host owns `<head>`,
  so our charset can land too late. `build.py` handles this; keep CSS and JS ASCII.
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
build/index.html     the artifact payload
```
