"""
Gedetailleerde analyse van standpunten: zoekt naar concrete issues waar
partijen van mening kunnen verschillen, en bepaalt de positie (positief/neutraal/negatief)
per partij per issue, puur gebaseerd op de gescrapede teksten.
"""

import json
import os
import re

DATA_DIR = "data/partijen"

# Concrete standpunten/issues waar partijen over kunnen verschillen.
# Per issue: zoektermen EN positie-indicatoren (voor/tegen/neutraal).
# De positie wordt bepaald door aanwezigheid van specifieke formuleringen in de tekst.
ISSUES = [
    {
        "id": "afslag_a9",
        "label": "Aanleg afslag A9",
        "categorie": "Verkeer",
        "zoektermen": ["afslag a9", "aansluiting a9"],
        "positief": ["aanleg afslag a9", "voortvarend", "essentieel", "realiseren", "blijvende inzet", "afslag a9, de bouw"],
        "negatief": ["geen afslag", "tegen de a9", "aantasting", "25% extra verkeer", "verdriedubbeling"],
        "neutraal": [],
    },
    {
        "id": "knip_kanaalweg",
        "label": "Knip Kanaalweg (afsluiten doorgaand verkeer)",
        "categorie": "Verkeer",
        "zoektermen": ["kanaalweg", "knip"],
        "positief": [],
        "negatief": ["geen knip", "vermijden van extra belasting", "afsluiten van de kanaalweg"],
        "neutraal": ["aanpassen van de kanaalweg"],
    },
    {
        "id": "woningbouw_zandzoom",
        "label": "Woningbouw in Zandzoom",
        "categorie": "Wonen",
        "zoektermen": ["zandzoom"],
        "positief": ["zandzoom moet nu", "voortvarend", "prioriteit geven aan uitvoering", "bouw van woningen in de zandzoom", "snelle ontwikkeling"],
        "negatief": ["uitbreiding van het bebouwde areaal", "enorme aantasting", "25%", "verlies"],
        "neutraal": [],
    },
    {
        "id": "sociale_huur",
        "label": "Meer sociale huurwoningen",
        "categorie": "Wonen",
        "zoektermen": ["sociale huur", "sociale bouw", "betaalbaar"],
        "positief": ["40% betaalbaar", "meer sociale huur", "40% sociale bouw", "sociale huurwoningen", "verhogen naar 30%"],
        "negatief": [],
        "neutraal": ["goede mix", "minimaal 10%"],
    },
    {
        "id": "bouwhoogte",
        "label": "Hoogbouw toestaan",
        "categorie": "Wonen",
        "zoektermen": ["hoogbouw", "bouwhoogte", "driehoog", "verdieping"],
        "positief": [],
        "negatief": ["geen verdere hoogbouw", "geen massale hoogbouw", "driehoog", "dorps karakter"],
        "neutraal": [],
    },
    {
        "id": "fusie",
        "label": "Bestuurlijke fusie (BUCH-gemeenten samenvoegen)",
        "categorie": "Bestuur",
        "zoektermen": ["fusie", "herindeling", "buch"],
        "positief": ["open voor een eventuele fusie", "fusie met een of meer"],
        "negatief": ["niet overgaan tot een bestuurlijke fusie", "niet samensmelten", "visie, geen fusie", "fusie zal de oplossing niet brengen", "geen doel op zich"],
        "neutraal": ["mogelijke fusie", "fusie of geen fusie", "zelfstandig blijven, samenwerken"],
    },
    {
        "id": "zelfstandig_heiloo",
        "label": "Heiloo zelfstandig houden",
        "categorie": "Bestuur",
        "zoektermen": ["zelfstandig", "eigen identiteit"],
        "positief": ["bestuurlijk zelfstandig", "zelfstandig waar het kan", "eigen gemeente"],
        "negatief": [],
        "neutraal": ["zelfstandig blijven, samenwerken", "fusie of geen fusie"],
    },
    {
        "id": "aardgasvrij",
        "label": "Verplicht van het aardgas af",
        "categorie": "Duurzaamheid",
        "zoektermen": ["aardgas", "gas af", "van het gas", "gasvrij"],
        "positief": ["nieuwbouw van het gas af"],
        "negatief": ["zonder mensen te verplichten", "tegen verplicht aardgasvrij", "niet onder dwang", "gasweigeraar", "van het gasweigeraar"],
        "neutraal": ["warmte transitie", "aardgasvrije wijken", "klimaatdoelen"],
    },
    {
        "id": "windmolens",
        "label": "Windmolens in/bij Heiloo",
        "categorie": "Duurzaamheid",
        "zoektermen": ["windmolen", "windturbine", "windenergie"],
        "positief": ["extra windturbine"],
        "negatief": ["geen confetti van windmolens", "gehaktmolen"],
        "neutraal": ["clustering daar waar"],
    },
    {
        "id": "zonnepanelen",
        "label": "Zonnepanelen en zonne-energie stimuleren",
        "categorie": "Duurzaamheid",
        "zoektermen": ["zonnepaneel", "zonnepanelen", "zonneweide", "zon op dak"],
        "positief": ["zonnepanelen langs de a9", "zon op dak", "meer zonnepanelen"],
        "negatief": ["geen zonnevelden", "geen confetti"],
        "neutraal": [],
    },
    {
        "id": "ozb_verhogen",
        "label": "OZB/lokale lasten verhogen",
        "categorie": "Financiën",
        "zoektermen": ["ozb", "lasten", "belasting"],
        "positief": ["verhogen van de ozb"],
        "negatief": [
            "geen grote stijging van de lasten",
            "zuinig omgaan met overheidsgeld",
            "tegen verhoging van de ozb",
            "tegen verhoging van de lokale lasten",
            "lasten niet verder verhogen",
            "geen hogere lasten voor inwoners"
        ],
        "neutraal": ["sterkste schouders, zwaarste lasten"],
    },
    {
        "id": "participatie",
        "label": "Meer burgerparticipatie/inspraak",
        "categorie": "Bestuur",
        "zoektermen": ["participatie", "inspraak", "burgerberaad", "meepraten", "meebeslissen"],
        "positief": ["sterk voorstander", "burgerberaden", "dorpsbijeenkomsten", "meebeslissen", "samen ontwerpen", "zeggenschap", "echte inbreng", "meer mogelijkheden", "klankborden"],
        "negatief": [],
        "neutraal": ["participatie tekort", "laat geïnformeerd", "participatiemaatschappij"],
    },
    {
        "id": "looplein",
        "label": "Revitalisatie Loo-plein/centrum",
        "categorie": "Voorzieningen",
        "zoektermen": ["loo-plein", "looplein", "winkelcentrum"],
        "positief": ["revitalisatie", "moderniseren", "bruisende ontmoetingsplekken", "sterk en vitaal centrum", "gezellig"],
        "negatief": ["stokpaardjes", "poppenkast"],
        "neutraal": [],
    },
    {
        "id": "baafje",
        "label": "Behoud Zwembad het Baafje",
        "categorie": "Voorzieningen",
        "zoektermen": ["baafje", "zwembad"],
        "positief": ["behoud van het baafje", "baafje open", "toekomst voor zwembad"],
        "negatief": [],
        "neutraal": ["faillissement"],
    },
    {
        "id": "groen_behoud",
        "label": "Behoud groene karakter Heiloo",
        "categorie": "Groen",
        "zoektermen": ["groene ring", "groen karakter", "groenbeleid", "biodiversiteit", "groene"],
        "positief": ["groene ring compleet", "biodiversiteit versterken", "behoud van het groen", "ecologisch groenbeleid", "groen investeren", "groen herstellen", "groene wijken", "groene buurten", "groene gemeente", "onder druk", "aantasting van de groene ruimte"],
        "negatief": [],
        "neutraal": [],
    },
    {
        "id": "fiets",
        "label": "Meer ruimte voor fietsers",
        "categorie": "Verkeer",
        "zoektermen": ["fiets", "fietser", "fietsstraat", "fietsverbinding"],
        "positief": ["meer ruimte voor fietsers", "fietsdorp", "fietsstraat", "veilige fietsverbinding", "fietsveilig"],
        "negatief": [],
        "neutraal": [],
    },
]


def load_all_data():
    """Laad alle partij-data."""
    partijen = {}
    for fname in sorted(os.listdir(DATA_DIR)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(DATA_DIR, fname), "r", encoding="utf-8") as f:
            data = json.load(f)
        naam = data["partij"]
        all_text = "\n".join(p["text"] for p in data["pages"])
        partijen[naam] = {
            "text": all_text,
            "lower": all_text.lower(),
            "pages": data["pages"],
        }
    return partijen


def find_context(text_lower, full_text, term, context_chars=250):
    """Vind de context rond een zoekterm."""
    idx = text_lower.find(term)
    if idx == -1:
        return None
    start = max(0, idx - context_chars)
    end = min(len(full_text), idx + len(term) + context_chars)
    return full_text[start:end].replace("\n", " ").strip()


def determine_stance(text_lower, issue):
    """Bepaal de positie van een partij op basis van aanwezige formuleringen."""
    # Check of het issue überhaupt voorkomt
    mentioned = any(term in text_lower for term in issue["zoektermen"])
    if not mentioned:
        return "niet_genoemd", None, []

    # Tel positieve en negatieve indicatoren
    pos_matches = [p for p in issue["positief"] if p in text_lower]
    neg_matches = [n for n in issue["negatief"] if n in text_lower]
    neu_matches = [n for n in issue["neutraal"] if n in text_lower]

    # Bepaal positie
    if pos_matches and not neg_matches:
        return "positief", pos_matches, neg_matches
    elif neg_matches and not pos_matches:
        return "negatief", pos_matches, neg_matches
    elif pos_matches and neg_matches:
        # Beide: genuanceerd/gemengd
        return "gemengd", pos_matches, neg_matches
    elif neu_matches:
        return "neutraal", pos_matches, neg_matches
    else:
        # Genoemd maar geen duidelijke positie
        return "genoemd", pos_matches, neg_matches


def analyse():
    """Voer de volledige standpunten-analyse uit."""
    partijen = load_all_data()
    partij_namen = list(partijen.keys())

    results = []

    for issue in ISSUES:
        issue_result = {
            "id": issue["id"],
            "label": issue["label"],
            "categorie": issue["categorie"],
            "partijen": {},
        }

        for naam in partij_namen:
            data = partijen[naam]
            stance, pos_matches, neg_matches = determine_stance(data["lower"], issue)

            # Zoek de relevante context-tekst
            context = None
            for term in issue["zoektermen"]:
                ctx = find_context(data["lower"], data["text"], term)
                if ctx:
                    context = ctx
                    break

            issue_result["partijen"][naam] = {
                "stance": stance,
                "context": context,
                "pos_matches": pos_matches or [],
                "neg_matches": neg_matches or [],
            }

        results.append(issue_result)

    return partij_namen, results


def save_results(partij_namen, results):
    """Sla de resultaten op."""
    os.makedirs("data", exist_ok=True)

    output = {
        "partijen": partij_namen,
        "issues": results,
    }

    path = os.path.join("data", "tldr_analyse.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"TL;DR analyse opgeslagen: {path}")

    # Print overzicht
    print(f"\n{'':20s}", end="")
    for naam in partij_namen:
        print(f" {naam[:12]:>12s}", end="")
    print()
    print("-" * (20 + 13 * len(partij_namen)))

    for issue in results:
        print(f"{issue['label'][:20]:20s}", end="")
        for naam in partij_namen:
            s = issue["partijen"][naam]["stance"]
            symbols = {
                "positief": "  ✅ VOOR",
                "negatief": "  ❌ TEGEN",
                "gemengd":  "  ⚠️ GEMENGD",
                "neutraal": "  ➖ NEUTR",
                "genoemd":  "  📝 NOEMT",
                "niet_genoemd": "  ⬜ ---",
            }
            print(f" {symbols.get(s, '?'):>12s}", end="")
        print()


def main():
    print("=" * 60)
    print("TL;DR Standpunten Analyse - Gemeenteraad Heiloo 2026")
    print("=" * 60)

    partij_namen, results = analyse()
    save_results(partij_namen, results)


if __name__ == "__main__":
    main()
