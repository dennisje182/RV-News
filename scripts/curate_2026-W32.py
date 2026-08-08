#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""
Curation for edition 2026-W32 — a throwaway script.

Judgement lives here: what is worth reading, what it says in English, what it
means for Thetford, and which of the four categories it belongs to. Items are
referenced by their position in pending.json (sorted newest-first) so that
titles, URLs, sources and dates come from the collected data rather than being
retyped, which is where transcription errors would otherwise creep in.

Duplicates are merged: one story, one entry, with the other outlets that ran it
recorded as "also covered by". Everything not listed here was judged out of
scope — mostly travel features, campsite guides, prize draws, consumer
listicles, and US/Australian trade news.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PENDING = ROOT / "digests" / "pending.json"

V, A, C, I = "vehicles", "accessories", "competitor", "industry"

# (index, category, is_competitor, brands, english title, summary, why-it-matters, duplicate indexes)
PICKS = [
    (260, A, False, ["Thetford"],
     "Thetford presents the next chapter of motorhome refrigeration",
     "Camper Professional's German trade audience gets Thetford's own framing of its "
     "next-generation fridge technology for motorhomes.",
     "This is your announcement, read back to you as the German trade press received it. "
     "Worth checking whether the framing that landed is the framing intended, and noting "
     "that it ran in the B2B title OEM purchasing teams actually read.",
     []),

    (185, C, True, ["Truma"],
     "Truma pushes further into digital control with the iNet X Panel 2",
     "A second-generation connected control panel, positioned as less integration work for "
     "manufacturers and more remote control for owners. Independent German coverage was "
     "more measured than the launch material, setting out what the panel does not do.",
     "Truma is making a claim on the in-cabin digital interface — the layer that decides "
     "which appliances a customer sees and controls in one place. If the panel becomes the "
     "default OEM fit, appliances outside it risk being operated as second-class devices.",
     [188, 206]),

    (8, I, False, ["Knaus Tabbert"],
     "Knaus Tabbert H1 2026: revenue down 11.9% to EUR 503.9m, EBIT back to EUR 21.8m",
     "Half-year revenue fell to EUR 503.9m while EBIT swung positive to EUR 21.8m. Analysts "
     "responded with a buy rating and a EUR 23 price target.",
     "The clearest read available on the German market: a listed bellwether selling "
     "materially fewer units while restoring margin. That pattern — protecting price over "
     "volume — is the one that matters for component order forecasts, because it means "
     "lower build volumes are being planned deliberately rather than reluctantly.",
     [12, 27, 29, 35, 5, 192]),

    (38, V, False, ["Bürstner"],
     "Bürstner expands motorhomes at Caravan Salon while withdrawing from caravans",
     "Bürstner arrives at Caravan Salon with a broadened motorhome line-up and confirmation "
     "that it is leaving the caravan segment.",
     "An OEM exiting caravans removes caravan-fitted component volume outright rather than "
     "shifting it to a competitor. Worth sizing against your own caravan-side fitment before "
     "the show, and watching whether other mid-market brands follow.",
     []),

    (56, A, False, [],
     "German press examines why absorber fridges struggle in high summer heat",
     "promobil sets out why absorption fridges lose performance in heat, alongside an Italian "
     "buying guide walking readers through choosing between cooling technologies.",
     "Two outlets in two markets scrutinising absorption cooling performance in the same "
     "fortnight, in your core category, while compressor alternatives gain shelf space. This "
     "is the argument that shapes how dealers explain the technology on the forecourt.",
     [87]),
]

REGISTER = [
    # ---------------------------------------------------------- competitor ----
    (200, C, True, ["Truma"], "Truma extends on-board safety with MonoControl CS R for Campingaz cylinders",
     "A gas pressure regulator with crash sensor, now covering Campingaz bottles.", None, []),
    (276, C, True, ["Webasto"], "Webasto shows new air heaters and a revised air conditioner",
     "Refreshed heating and climate line for greater travel comfort.", None, []),
    (265, C, True, ["Dometic"], "Dometic Q2 2026: stable sales in a volatile market",
     "Interim report for the second quarter, with management describing sales as stable "
     "against volatile conditions. Berenberg maintained its buy rating.", None, [236, 262, 293, 237]),
    (223, C, True, ["Thule"], "Thule interim report for Q2 2026", "Second-quarter results, April to June.", None, [290]),
    (32, C, True, ["Airxcel"], "Airxcel expands its dealer, distributor and service sales team",
     "The RV climate and appliance group adds commercial headcount.", None, []),
    (190, C, True, ["Truma", "GOK"], "GOK GasControl beats Truma's GS8 on one feature, German test finds",
     "A head-to-head on remote gas shut-off devices.", None, []),
    (166, C, True, ["Dometic", "Cadac"], "Cadac and Dometic launch the Van Cook FFD",
     "A co-branded cooking unit aimed at van conversions.", None, [216]),
    (103, C, True, ["Dometic"], "Dometic CFX3 35 and CFX5 45 compressor cool boxes reviewed",
     "German tests of the compact CFX3 35 and the CFX5 45, plus a wider compressor cool box "
     "group test claiming cooling to minus 20 degrees.", None, [263, 277]),
    (81, C, True, ["Mestic"], "Mestic launches inverter rooftop air conditioners",
     "Energy-efficient cooling and heating, pitched on quiet running.", None, []),
    (122, C, True, ["Fiamma"], "Fiamma launches an award initiative with a contemporary art museum",
     "A brand and sponsorship play rather than a product move.", None, []),
    (121, C, True, ["Victron"], "Victron releases VictronConnect v6.40",
     "Update to the configuration and monitoring app for its power electronics.", None, []),

    # -------------------------------------------------------- accessories ----
    (258, A, False, ["E-Trailer"], "E-Trailer system puts power, gas and water levels on one screen",
     "Tank and supply monitoring consolidated into a single connected display.", None, []),
    (89, A, False, ["GOK"], "GOK Caramatic series supplies gas while driving", "Regulator range for use in motion.", None, []),
    (272, A, False, [], "Five foldable solar panels compared for off-grid campers",
     "Overview of flexible solar options for self-sufficient touring.", None, []),
    (10, A, False, ["Maxxis"], "Maxxis RAZR AT-S all-season tyre for all-wheel-drive campers", "", None, []),
    (123, A, False, [], "flat-jack Camper 2.0 tyre air cushions for levelling", "", None, []),
    (169, A, False, [], "Three wireless reversing cameras for campers compared", "", None, []),
    (186, A, False, [], "Six CEE cable reels tested", "Mains hook-up leads in a practical test.", None, []),
    (161, A, False, ["Scanstrut"], "Scanstrut to show exterior utility connection products at Caravan Salon",
     "External service connections for vehicle exteriors.", None, []),
    (88, A, False, ["CamperBoards"], "CamperBoards offers made-to-measure table solutions", "", None, []),
    (275, A, False, ["LotusGrill"], "LotusGrill Hybrid Classic runs on gas or charcoal", "", None, []),
    (147, A, False, ["Xiaomi"], "Xiaomi shows a Sky Nomad N90 Camping Edition with lift roof and bed",
     "A consumer-electronics brand appearing in the camping-vehicle space.", None, []),

    # ------------------------------------------------------------ industry ----
    (298, I, False, ["Trigano"], "Trigano group revenue up 1.6% in Q3",
     "Modest growth for Europe's largest leisure-vehicle group.", None, [104, 106]),
    (285, I, False, [], "German camping market stays strong but shows first notes of caution",
     "Campingwirtschaft reports continued strength alongside early warning signals.", None, []),
    (160, I, False, ["ACSI"], "Dutch campsite overnight stays up 22.5% through May",
     "ACSI figures for the season to end of May.", None, []),
    (230, I, False, [], "France confirms its pull with European motorhome travellers",
     "The French industry association reports on inbound motorhome tourism.", None, []),
    (22, I, False, [], "Crit'Air low-emission stickers are required for motorhomes in France",
     "Regulatory reminder on the French environmental windscreen sticker.", None, []),
    (302, I, False, ["Knaus Tabbert"], "Knaus Tabbert reorganises its management team as part of its transformation", "", None, []),
    (241, I, False, ["Niesmann"], "Niesmann Caravaning becomes a shareholder in Caravaning Center Bad Kreuznach",
     "Retail consolidation in Germany.", None, []),
    (219, I, False, ["Camec"], "Aussie Traveller agrees to acquire Camec",
     "Consolidation among RV component suppliers, in Australia.", None, []),
    (261, I, False, [], "JB Group acquires Network RV", "Aftermarket and dealer-services consolidation.", None, []),
    (205, I, False, ["Lippert"], "Lippert marks ten years in Europe",
     "The components group reflects on a decade of European operations.", None, [220]),
    (234, I, False, ["Dexko"], "Eric McGinnis appointed Dexko chief executive",
     "Leadership change at the chassis and running-gear group.", None, []),
    (212, I, False, ["Stellantis"], "Stellantis Pro One holds its European light-commercial-vehicle lead",
     "Base-vehicle market share position maintained.", None, []),
    (291, I, False, ["Volkswagen"], "Fernando Badia takes over European and international sales at VW Commercial Vehicles", "", None, []),
    (252, I, False, [], "Caravan Salon promises the widest variety of caravans on show",
     "Organiser positioning ahead of the Düsseldorf show in late August.", None, [82]),
    (225, I, False, [], "The 60th Salon des Véhicules de Loisirs", "France's leisure-vehicle show reaches its 60th edition.", None, []),
    (117, I, False, ["Fiat"], "The Fiat Ducato turns 45",
     "Anniversary of the base vehicle underpinning much of the European market.", None, [141]),
    (148, I, False, [], "United States records more than 25,000 RV shipments in June",
     "US shipment data, useful only as a global demand signal.", None, []),
    (140, I, False, ["Volkswagen"], "Broekhuis becomes an official Volkswagen California dealer in the Netherlands", "", None, []),
    (194, I, False, ["Dethleffs"], "Dethleffs adds dealers in Brabant and Friesland", "", None, []),

    # ------------------------------------------------------------ vehicles ----
    (303, V, False, ["Knaus Tabbert", "Knaus", "Weinsberg"], "Knaus Tabbert presents its 2027 model-year range", "", None, [16, 112, 229]),
    (128, V, False, ["Mercedes-Benz"], "New Mercedes-Benz Marco Polo arrives as a smarter everyday campervan", "", None, [130, 132]),
    (202, V, False, ["Volkswagen"], "Volkswagen Transporter can now be ordered as a plug-in hybrid",
     "Electrified base vehicle reaching the conversion market.", None, []),
    (251, V, False, ["Ford"], "Ford withdraws the Nugget campervan from the UK", "", None, []),
    (259, V, False, ["Volkswagen"], "VW Grand California gains off-grid capability, and the Grand California adds solar",
     "Crafter-based campervan pushed further towards self-sufficiency.", None, [193]),
    (58, V, False, ["Carthago"], "Carthago keeps innovation and stability as its focus for 2026/27", "", None, [73]),
    (114, V, False, ["Carthago"], "Carthago renews its topliners and adds a C2-tourer with face-to-face lounge", "", None, [18, 107]),
    (72, V, False, ["Adria"], "Adria upgrades its Fiat Ducato-based Coral and Matrix ranges for 2027", "", None, []),
    (177, V, False, ["Adria"], "Adria Alpina caravan gets a complete makeover", "", None, []),
    (158, V, False, ["Bürstner"], "Bürstner Signature moves onto a Mercedes base", "", None, [46]),
    (76, V, False, ["Bürstner"], "Bürstner Habiton 6.1 Sprinter camper adds a transverse bed", "", None, [125]),
    (85, V, False, ["Corigon"], "Corigon Pure eco low-profiles get a new design, and the range expands",
     "Erwin Hymer Group's newer brand broadens layouts, adds diesel heating and a drop-down bed.", None, [145]),
    (120, V, False, ["Laika"], "Laika moves its Kreos range onto a Mercedes Sprinter for 2027", "", None, [65, 40, 75]),
    (50, V, False, ["Hobby"], "Hobby De Luxe 2027 gets a new design, kitchen and heavy-duty supports", "", None, [118, 171]),
    (51, V, False, ["Hobby"], "Hobby Prestige T offered in three layouts for model year 2027", "", None, [119, 99]),
    (67, V, False, ["Fendt"], "Fendt Bianco stays the widest range with 16 layouts", "", None, []),
    (247, V, False, ["Fendt"], "Fendt Apero adds the Activ 465 GE twin-bed caravan", "", None, [137]),
    (184, V, False, ["Tabbert"], "Tabbert brings back the Vivaldi for model year 2027", "", None, [57]),
    (30, V, False, ["Weinsberg"], "Weinsberg CaraBus renews its living space for model year 2027", "", None, [279]),
    (180, V, False, ["LMC"], "LMC renews the Tracer and expands Innovan Pure for 2027", "", None, []),
    (94, V, False, ["Kip"], "Kip Kompakt lift-roof caravan fully renewed with an outdoor kitchen", "", None, []),
    (49, V, False, ["Bruder"], "Bruder ADX-21 off-road caravan adds living comfort", "", None, []),
    (52, V, False, ["Lume"], "Lume Ranger is a compact caravan aimed at campervan owners", "", None, []),
    (60, V, False, ["Carado"], "Carado T335 Edition27 makes the bathroom the centrepiece",
     "An OEM using the washroom as the headline feature of a model-year update.", None, []),
    (17, V, False, ["Dethleffs"], "Dethleffs Trend I 7027 takes a radical turn with a new layout", "", None, []),
    (78, V, False, ["Dethleffs"], "Dethleffs Just Van T5 is a compact low-profile with van feel", "", None, []),
    (127, V, False, ["Westfalia"], "Westfalia marks 50 years of the Sven Hedin with a jubilee camper", "", None, []),
    (129, V, False, ["Westfalia"], "New Westfalia Nansen offers room for family and luggage", "", None, []),
    (257, V, False, ["Westfalia"], "Westfalia Columbus Liner on Fiat Ducato to debut at Caravan Salon", "", None, [178]),
    (210, V, False, ["Niesmann+Bischoff"], "Niesmann+Bischoff makes the iSmove more self-sufficient for 2027", "", None, [181, 204]),
    (233, V, False, ["Pilote"], "Pilote's 2027 A-class range gets a new front end and more comfort", "", None, [151, 295, 21]),
    (255, V, False, ["Pilote", "Joa"], "Joa by Pilote is the underestimated budget brand shaking up the German market", "", None, []),
    (131, V, False, ["Sunlight"], "Sunlight puts new low-profiles on the Ford Transit with revised layouts", "", None, [79]),
    (98, V, False, ["Forster"], "Forster modernises its motorhome range with new design and interiors",
     "Includes an eight-berth alcove model at aggressive pricing and the sub-EUR 50,000 Vantasy.", None, [174, 159]),
    (37, V, False, ["Pössl"], "Pössl presents one of the most ingenious camper vans of the year", "", None, [77, 199]),
    (66, V, False, ["Etrusco"], "Narrow Etrusco V 6.8 adds a second layout and an optional drop-down bed",
     "The V 6.8 SCF turns the couples' van into a family motorhome.", None, [7, 222]),
    (170, V, False, ["Etrusco"], "Etrusco CV 640 PB+ balances comfort against practicality", "", None, [175]),
    (3, V, False, ["Flowcamper"], "Flowcamper shows the Max Autark Grande", "", None, []),
    (91, V, False, ["Ciclope"], "Ciclope Mencía brings off-road ability on a Ford base", "", None, []),
    (6, V, False, ["Offtrack"], "Offtrack Camper Verge", "", None, []),
    (235, V, False, ["Morelo"], "Morelo Palace luxury liner for 2027", "", None, []),
    (249, V, False, ["Frankia"], "Frankia Final Edition brings luxury equipment from EUR 139,990", "", None, [244]),
    (280, V, False, ["Rimor"], "Rimor's 2027 range targets comfort", "", None, []),
    (284, V, False, ["Hymer"], "Hymer GT-S Mediterranee", "", None, []),
    (19, V, False, ["Malibu"], "Malibu Relax gains an adjustable-height bed",
     "The Relax 640 LE XR uses an electric bed to free up a large garage.", None, [64]),
    (62, V, False, ["Sun Living"], "Sun Living 20 Edition targets value", "", None, []),
    (93, V, False, ["Ahorn"], "Ahorn Camp Eclipse edition joins the range", "", None, [96, 97]),
    (68, V, False, [], "Nine campervans with a rear drop-down bed, and why the layout is trending for 2027",
     "A layout trend piece rather than a single launch.", None, []),
    (108, V, False, [], "2027 model-year price lists published for seventeen brands",
     "CampingCarLeSite has posted new-vehicle pricing for Adria, Bavaria, Bürstner, Carado, "
     "Challenger, Chausson, CI, Eden Camp, Etrusco, Laika, McLouis, Mobilvetta, Pilote, Rimor, "
     "Roller Team and Sunlight. Useful as a pricing reference rather than as news.",
     None, [109, 110, 111, 113, 115, 116, 149, 152, 153, 154, 155, 156, 157, 163, 164]),
    (1, V, False, [], "Reisemobil International's rolling list of 2027 model entries",
     "The title logs new model-year variants continuously — Notin Envol 719JF, Chausson X640, "
     "Benimar Yrteo 885, Giottiline Siena 340, Itineo Cozi PM740, Fleurette Florium Belixter 73, "
     "Rapido C66i Optimum Line, Tabbert Puccini Finest and others. Individually thin, "
     "collectively the fastest launch signal available.",
     None, [2, 4, 20, 33, 34, 45, 57, 289, 253, 264, 142]),
]


def main() -> int:
    data = json.loads(PENDING.read_text(encoding="utf-8"))
    items = data["items"]
    items.sort(key=lambda i: (i["published"] or "0000"), reverse=True)

    def get(idx: int) -> dict:
        return items[idx]

    def scraped_date(it: dict) -> str | None:
        """Knaus Tabbert's scraped rows carry DD.MM.YYYY inside the title text."""
        m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", it["title"])
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None

    def clean_scraped_title(t: str) -> str:
        return re.sub(r"^\d{2}\.\d{2}\.\d{4}\s*\|\s*[A-Za-z ]+\s*", "", t).strip()

    built, used = [], set()
    for group, is_pick in ((PICKS, True), (REGISTER, False)):
        for idx, cat, comp, brands, title_en, summary_en, why, dupes in group:
            src = get(idx)
            used.add(idx)
            used.update(dupes)
            pub = src["published"] or scraped_date(src)
            original = src["title"]
            if src["source_type"] == "scrape":
                original = clean_scraped_title(original)
            built.append({
                "id": src["id"],
                "category": cat,
                "competitor": comp,
                "pick": is_pick,
                "brands": brands,
                "title": title_en,
                "title_original": original if src["lang"] != "en" else "",
                "summary": summary_en,
                "why": why,
                "url": src["url"],
                "source": src["source"],
                "lang": src["lang"],
                "country": src["country"],
                "published": (pub or "")[:10],
                "also": sorted({get(d)["source"] for d in dupes} - {src["source"]}),
            })

    order = {V: 0, A: 1, C: 2, I: 3}
    built.sort(key=lambda x: (order[x["category"]], x["published"] == "", x["published"]), reverse=False)
    built.sort(key=lambda x: (order[x["category"]], x["published"] or "0000"),
               reverse=False)
    # newest first inside each category
    built.sort(key=lambda x: order[x["category"]])
    by_cat: dict[str, list] = {}
    for b in built:
        by_cat.setdefault(b["category"], []).append(b)
    for cat in by_cat:
        by_cat[cat].sort(key=lambda x: x["published"] or "0000", reverse=True)
    built = [b for cat in (V, A, C, I) for b in by_cat.get(cat, [])]

    now = datetime.now(timezone.utc)
    dates = [i["published"] for i in items if i["published"]]
    edition = {
        "edition": "2026-W32",
        "published_at": now.isoformat(timespec="seconds"),
        "window": {"from": min(dates)[:10], "to": max(dates)[:10]},
        "collected": len(items),
        "selected": len(built),
        "dropped": len(items) - len(used),
        "merged": len(used) - len(built),
        "sources_ok": data.get("sources_ok", 0),
        "sources_failed": data.get("sources_failed", []),
        "sources_warned": data.get("sources_warned", []),
        "items": built,
    }
    out = ROOT / "digests" / "2026-W32.json"
    out.write_text(json.dumps(edition, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    print(f"edition 2026-W32")
    print(f"  collected {edition['collected']}")
    print(f"  selected  {edition['selected']}  ({sum(1 for b in built if b['pick'])} picks)")
    print(f"  merged    {edition['merged']} duplicate reports")
    print(f"  dropped   {edition['dropped']} as out of scope")
    for cat in (V, A, C, I):
        n = len(by_cat.get(cat, []))
        print(f"    {cat:<12} {n}")
    print(f"  competitor-flagged {sum(1 for b in built if b['competitor'])}")
    missing = [b['title'] for b in built if not b['published']]
    if missing:
        print(f"  WARNING no date on {len(missing)}: {missing[:3]}")
    print(f"\nwrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
