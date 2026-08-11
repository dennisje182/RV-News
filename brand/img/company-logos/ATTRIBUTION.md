# Company-logo sources

The builder embeds these local copies into the single-file dashboard. They are
not fetched by the reader's browser.

| Asset | Brand | Source | Licence |
| --- | --- | --- | --- |
| `volkswagen.svg` | Volkswagen | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Volkswagen_logo_2019.svg) | Public domain |
| `fendt.svg` | Fendt Caravan | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Fendt-Caravan_Logo-2020-2.svg) | CC BY-SA 4.0 |
| `burstner.svg` | Bürstner | [Bürstner public website](https://www.buerstner.com/_default_upload_bucket/buerstner-relaunch-logo_1.svg) | Brand asset supplied by the company |
| `promobil.svg` | promobil | [promobil public website](https://www.promobil.de/img/pro/logo-banner.svg) | Brand asset supplied by the publisher |
| `truma.svg` | Truma | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Truma_firmenlogo.jpg) | Compact embedded copy of Truma's CC BY-SA 3.0 logo |
| `thule.svg` | Thule | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Thule_Brand_Logo_03.2023.svg) | Current company mark, public-domain text logo |
| `westfalia.svg` | Westfalia | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Westfalia_Van_Conversion_logo.svg) | Vector based on the company's public RV mark, public-domain text logo |

## Only real logo files belong here

An asset must be a genuine vector or raster copy of the company's own mark. Do
not approximate a logotype by setting the company name in a substitute typeface —
that misrepresents a real company's trademark, and `<text>` in an SVG renders
differently depending on the fonts the reader happens to have.

`knaus-tabbert.svg` was removed on 9 August 2026 for exactly this. It set "KNAUS
TABBERT" in Arial with a hand-drawn swoosh, and carried a corrupted glyph
fragment that rendered as stray marks under the wordmark.

When no genuine asset is available, add nothing. `brand_initials()` in
`build.py` falls back to a neutral monogram, which is the honest outcome and is
what the code comments already say should happen.

### Wanted, if a genuine file can be sourced
- Knaus Tabbert — currently shows a "KT" monogram
- Dometic — currently shows a "D" monogram
- Fiamma — currently shows an "F" monogram
- Victron Energy — currently shows a "V" monogram
- Webasto — currently shows a "W" monogram
- promobil — the current `logo-banner.svg` is a small square badge that is
  illegible at 30px; a horizontal wordmark would read properly
- Truma — the current file is a JPEG wrapped in SVG, so it is lossy and has no
  transparency; an SVG or transparent PNG would be better
