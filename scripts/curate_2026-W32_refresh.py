#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Refresh the published 2026-W32 edition with items collected on 9 August.

The 8 August edition already curated 96 records from the opening 30-day run.
This script preserves that judgement, merges five later reports of stories
already selected, and adds the four distinct developments from the 22 new
items. New items are referenced by their position in the current, identically
sorted pending queue so their source metadata and URLs stay collected data.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PENDING = ROOT / "digests" / "pending.json"
EDITION = ROOT / "digests" / "2026-W32.json"

V = "vehicles"

# (pending index, English title, summary, brands)
NEW_RECORDS = [
    (1, "Knaus Nordwind is a new all-season luxury caravan",
     "Campingtrend reports that Knaus is bringing back the Nordwind as a luxury caravan intended for year-round use.",
     ["Knaus"]),
    (24, "Adria completely reworks its Twin campervan for 2026",
     "The revised Twin brings more daylight, a new interior, updated technology and a new White Edition 2 variant.",
     ["Adria"]),
    (13, "Eifelland tests the practical limits of an electric campervan",
     "promobil tests the Eifelland Relax on Nissan's Interstar-e, one of the early electric campers claiming usable range, and finds its everyday practicality remains open to question.",
     ["Eifelland", "Nissan"]),
    (18, "McLouis updates several camper and van ranges for 2027",
     "CamperOnLine reports model-year changes across several McLouis ranges and vehicle categories for the 2027 season.",
     ["McLouis"]),
]

# Existing curated title: pending indexes of later reports of that same story.
DUPLICATES = {
    "Dethleffs Just Van T5 is a compact low-profile with van feel": [0, 2],
    "Hobby Prestige T offered in three layouts for model year 2027": [5],
    "Sunlight puts new low-profiles on the Ford Transit with revised layouts": [9],
    "Lume Ranger is a compact caravan aimed at campervan owners": [10],
}


def main() -> int:
    pending = json.loads(PENDING.read_text(encoding="utf-8"))
    items = pending["items"]
    items.sort(key=lambda item: (item["published"] or "0000"), reverse=True)
    edition = json.loads(EDITION.read_text(encoding="utf-8"))

    by_title = {item["title"]: item for item in edition["items"]}
    duplicate_count = 0
    for title, indexes in DUPLICATES.items():
        record = by_title[title]
        sources = {record["source"], *record.get("also", [])}
        sources.update(items[index]["source"] for index in indexes)
        record["also"] = sorted(sources - {record["source"]})
        duplicate_count += len(indexes)

    for index, title, summary, brands in NEW_RECORDS:
        source = items[index]
        edition["items"].append({
            "id": source["id"],
            "category": V,
            "competitor": False,
            "pick": False,
            "brands": brands,
            "title": title,
            "title_original": source["title"] if source["lang"] != "en" else "",
            "summary": summary,
            "why": None,
            "url": source["url"],
            "source": source["source"],
            "lang": source["lang"],
            "country": source["country"],
            "published": source["published"][:10],
            "also": [],
        })

    order = {"vehicles": 0, "accessories": 1, "competitor": 2, "industry": 3}
    edition["items"].sort(key=lambda item: (order[item["category"]], item["published"] or "0000"), reverse=False)
    grouped = {category: [] for category in order}
    for item in edition["items"]:
        grouped[item["category"]].append(item)
    edition["items"] = [
        item
        for category in order
        for item in sorted(grouped[category], key=lambda item: item["published"] or "0000", reverse=True)
    ]

    newly_collected = 22
    edition["published_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    edition["window"]["to"] = max(item["published"] for item in items if item["published"])[:10]
    edition["collected"] += newly_collected
    edition["selected"] = len(edition["items"])
    edition["merged"] += duplicate_count
    edition["dropped"] += newly_collected - len(NEW_RECORDS) - duplicate_count
    edition["sources_ok"] = pending["sources_ok"]
    edition["sources_failed"] = pending["sources_failed"]
    edition["sources_warned"] = pending["sources_warned"]

    EDITION.write_text(json.dumps(edition, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("edition 2026-W32 refreshed")
    print(f"  collected {edition['collected']}")
    print(f"  selected  {edition['selected']}")
    print(f"  merged    {edition['merged']} duplicate reports")
    print(f"  dropped   {edition['dropped']} as out of scope")
    print(f"  sources   {edition['sources_ok']} ok, {len(edition['sources_failed'])} failed")
    print(f"wrote {EDITION.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
