"""
Analyse van gescrapede standpunten van politieke partijen in Heiloo.
Extraheert thema's en standpunten per partij, puur gebaseerd op de gescrapede data.
Genereert een vergelijkingswebsite.
"""

import json
import os
import re
from collections import defaultdict

DATA_DIR = "data/partijen"
OUTPUT_DIR = "data"

# Thema-mapping: zoekwoorden -> genormaliseerd thema
# We gebruiken dit om content van verschillende partijen onder dezelfde thema's te groeperen
THEMA_MAPPING = {
    "Wonen": [
        "wonen", "woningbouw", "woningen", "huurwoningen", "starterswoning",
        "nieuwbouw", "zandzoom", "leefomgeving", "leefbaarheid", "buurten",
        "huurders", "sociale huur", "woningmarkt", "woningvoorraad", "inbreiding",
        "tiny house", "knarrenhof", "woningcorporat",
    ],
    "Duurzaamheid en milieu": [
        "duurzaam", "klimaat", "energietransitie", "zonnepanelen", "isolat",
        "energiebespar", "aardgasvrij", "co2", "circulair", "milieu",
        "schone lucht", "luchtkwaliteit",
    ],
    "Groen en natuur": [
        "groen", "natuur", "biodiversiteit", "ecologisch", "bomen",
        "groene ring", "groenbeleid", "groenvoorziening",
    ],
    "Zorg en welzijn": [
        "zorg", "welzijn", "vergrijzing", "eenzaamheid", "psychisch",
        "wijkteam", "mantelzorg", "ouderen", "ggz", "wmo",
        "gezondheid", "preventie",
    ],
    "Onderwijs": [
        "onderwijs", "school", "scholier", "basisschool", "kinderopvang",
        "ikc", "kind centrum", "leerling", "onderwijs",
    ],
    "Sport, cultuur en recreatie": [
        "sport", "cultuur", "kunst", "recreatie", "toerisme",
        "sporthal", "zwembad", "muziekschool", "bibliotheek",
        "vereniging", "het baafje",
    ],
    "Jeugd en jongeren": [
        "jeugd", "jongeren", "jonge", "starter", "jongere",
        "jeugdzorg", "jongerenwerk",
    ],
    "Verkeer en mobiliteit": [
        "verkeer", "mobiliteit", "fiets", "auto", "openbaar vervoer",
        "ov", "a9", "afslag", "parkeer", "vervoer", "infrastructuur",
        "stationsplein", "bereikbaar",
    ],
    "Economie en ondernemers": [
        "economi", "ondernemer", "mkb", "winkel", "bedrijv",
        "werkgelegenheid", "werk", "inkomen", "lokale economie",
        "ondernemersklimaat",
    ],
    "Financiën": [
        "financieel", "financien", "financiën", "begroting", "belasting",
        "ozb", "gemeentefonds", "bezuiniging", "investering",
    ],
    "Bestuur en participatie": [
        "bestuur", "participatie", "inspraak", "democratie", "buch",
        "fusie", "zelfstandig", "samenwerking", "herindeling",
        "bestuurskracht", "burgerberaad", "referendum",
    ],
    "Veiligheid": [
        "veiligheid", "veilig", "politie", "wijkagent", "handhav",
        "criminaliteit", "overlast",
    ],
    "Sociaal beleid": [
        "sociaal", "armoede", "minima", "bestaanszekerheid",
        "inclusie", "toegankelijk", "gelijke kansen", "bijstand",
        "schuld", "meedoen",
    ],
    "Voorzieningen": [
        "voorziening", "maatschappelijk", "basisvoorziening",
        "dorpshuis", "wijkcentrum",
    ],
}

# Per partij: welke URL-patronen bevatten standpunten (vs. bijv. profielen, contact, etc.)
STANDPUNTEN_URL_PATTERNS = {
    "Heiloo-2000": ["/verkiezingsprogramma", "/vereniging", "/algemeen"],
    "GroenLinks-PvdA": ["/standpunten", "/thema/", "/gemeenteraadsverkiezing"],
    "VVD": ["/standpunten", "/verkiezingsprogramma", "/pijlers/", "/nieuws/verkiezingsprogramma", "/nieuws/aardgasvrij", "/nieuws/klimaatbeleid", "/nieuws/parkeren", "/nieuws/heiloo-gaat-investeren"],
    "D66": ["/verkiezingsprogramma", "/standpunten"],
    "Gemeentebelangen Heiloo": ["/speerpunten", "/verkiezingsprogramma", "/beginselverklaring", "/uitgangspunten", "/algemene-beschouwingen"],
    "CDA": ["/themas", "/programma"],
}


def load_partij_data(partij_naam):
    """Laad de JSON data voor een partij."""
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", partij_naam)
    path = os.path.join(DATA_DIR, f"{safe_name}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def filter_standpunten_pages(data, partij_naam):
    """Filter alleen pagina's die standpunten bevatten."""
    patterns = STANDPUNTEN_URL_PATTERNS.get(partij_naam, [])
    relevant_pages = []

    for page in data["pages"]:
        url = page["url"].lower()
        # Check of de URL een relevant patroon bevat
        if any(pat in url for pat in patterns):
            relevant_pages.append(page)
        # Of de homepage als er geen betere bronnen zijn
        elif url.rstrip("/") == data["pages"][0]["url"].rstrip("/"):
            relevant_pages.append(page)

    # Als er geen specifieke standpunten-pagina's zijn, neem alle pagina's
    if not relevant_pages:
        relevant_pages = data["pages"]

    return relevant_pages


def extract_standpunten_for_thema(pages, thema, keywords):
    """Zoek in de pagina's naar tekst die bij een thema hoort."""
    found_snippets = []

    for page in pages:
        text = page["text"]
        text_lower = text.lower()

        # Check of deze pagina relevant is voor dit thema
        relevance_score = sum(1 for kw in keywords if kw in text_lower)
        if relevance_score < 1:
            continue

        # Zoek relevante paragrafen
        # Split op dubbele newlines of op koppen-achtige patronen
        paragraphs = re.split(r'\n(?=[A-Z•\-\d])', text)

        for para in paragraphs:
            para_lower = para.lower().strip()
            if len(para_lower) < 30:
                continue

            # Check of deze paragraaf relevant is voor het thema
            para_relevance = sum(1 for kw in keywords if kw in para_lower)
            if para_relevance >= 1:
                # Schoon op
                clean = para.strip()
                if len(clean) > 30 and clean not in [s["tekst"] for s in found_snippets]:
                    found_snippets.append({
                        "tekst": clean,
                        "bron": page["url"],
                        "relevance": para_relevance,
                    })

    # Sorteer op relevantie, neem de meest relevante stukken
    found_snippets.sort(key=lambda x: x["relevance"], reverse=True)
    return found_snippets[:8]  # Max 8 snippets per thema per partij


def deduplicate_snippets(snippets):
    """Verwijder duplicaten en overlappende teksten."""
    if not snippets:
        return snippets

    unique = []
    seen_texts = set()

    for s in snippets:
        # Neem de eerste 100 chars als key om near-duplicates te vangen
        key = s["tekst"][:100].lower().strip()
        if key not in seen_texts:
            seen_texts.add(key)
            unique.append(s)

    return unique


def analyse_partijen():
    """Hoofdanalyse: lees alle data, extraheer standpunten per thema per partij."""
    partijen_namen = [
        "Heiloo-2000", "GroenLinks-PvdA", "VVD", "D66",
        "Gemeentebelangen Heiloo", "CDA"
    ]

    # Laad alle data
    all_data = {}
    for naam in partijen_namen:
        data = load_partij_data(naam)
        if data:
            pages = filter_standpunten_pages(data, naam)
            all_data[naam] = pages
            print(f"  {naam}: {len(pages)} relevante pagina's van {len(data['pages'])} totaal")

    # Analyseer per thema
    thema_analyse = {}
    for thema, keywords in THEMA_MAPPING.items():
        thema_data = {}
        has_content = False

        for naam in partijen_namen:
            if naam not in all_data:
                continue

            snippets = extract_standpunten_for_thema(all_data[naam], thema, keywords)
            snippets = deduplicate_snippets(snippets)

            if snippets:
                has_content = True
                thema_data[naam] = snippets

        if has_content:
            thema_analyse[thema] = thema_data

    return partijen_namen, thema_analyse


def save_analyse(partijen_namen, thema_analyse):
    """Sla de analyse op als JSON."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    output = {
        "partijen": partijen_namen,
        "themas": {}
    }

    for thema, partij_data in thema_analyse.items():
        output["themas"][thema] = {}
        partijen_met_standpunt = []
        for naam, snippets in partij_data.items():
            output["themas"][thema][naam] = [
                {"tekst": s["tekst"], "bron": s["bron"]}
                for s in snippets
            ]
            partijen_met_standpunt.append(naam)
        output["themas"][thema]["_partijen"] = partijen_met_standpunt

    path = os.path.join(OUTPUT_DIR, "analyse_standpunten.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\nAnalyse opgeslagen: {path}")

    # Maak ook een leesbare samenvatting
    txt_path = os.path.join(OUTPUT_DIR, "analyse_standpunten.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("ANALYSE STANDPUNTEN - GEMEENTERAAD HEILOO 2026\n")
        f.write("=" * 60 + "\n\n")
        f.write("Gebaseerd op gescrapede data van partij-websites.\n")
        f.write("Geen interpretatie, alleen originele teksten.\n\n")

        for thema, partij_data in thema_analyse.items():
            f.write(f"\n{'='*60}\n")
            f.write(f"THEMA: {thema}\n")
            f.write(f"Partijen met standpunten: {', '.join(partij_data.keys())}\n")
            f.write(f"{'='*60}\n\n")

            for naam, snippets in partij_data.items():
                f.write(f"  --- {naam} ---\n")
                for s in snippets[:3]:  # Max 3 in de txt versie
                    tekst = s["tekst"][:300]
                    if len(s["tekst"]) > 300:
                        tekst += "..."
                    f.write(f"  {tekst}\n")
                    f.write(f"  (Bron: {s['bron']})\n\n")

    print(f"Leesbare samenvatting: {txt_path}")
    return output


def generate_website(partijen_namen, thema_analyse):
    """Genereer een statische HTML vergelijkingswebsite."""
    os.makedirs("docs", exist_ok=True)

    # Kleuren per partij
    partij_kleuren = {
        "Heiloo-2000": "#FFD700",
        "GroenLinks-PvdA": "#4CAF50",
        "VVD": "#FF6600",
        "D66": "#00A651",
        "Gemeentebelangen Heiloo": "#2196F3",
        "CDA": "#007B5F",
    }

    partij_urls = {
        "Heiloo-2000": "https://www.heiloo-2000.nl/",
        "GroenLinks-PvdA": "https://heiloo.groenlinkspvda.nl/",
        "VVD": "https://www.vvd.nl/gemeente-heiloo/",
        "D66": "https://d66.nl/heiloo/",
        "Gemeentebelangen Heiloo": "https://www.gemeentebelangenheiloo.nl/",
        "CDA": "https://www.cda.nl/noord-holland/heiloo/",
    }

    # Laad TLDR data
    tldr_data = None
    tldr_path = os.path.join("data", "tldr_analyse.json")
    if os.path.exists(tldr_path):
        with open(tldr_path, "r", encoding="utf-8") as f:
            tldr_data = json.load(f)

    # Bouw de matrix data
    thema_namen = list(thema_analyse.keys())

    # Matrix: welke partij heeft een standpunt over welk thema
    matrix_rows = []
    for thema in thema_namen:
        row = {"thema": thema, "partijen": {}}
        for naam in partijen_namen:
            if naam in thema_analyse.get(thema, {}):
                row["partijen"][naam] = True
            else:
                row["partijen"][naam] = False
        matrix_rows.append(row)

    # Genereer HTML
    html = generate_html(partijen_namen, partij_kleuren, partij_urls,
                         thema_namen, thema_analyse, matrix_rows, tldr_data)

    path = os.path.join("docs", "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nWebsite gegenereerd: {path}")
    return path


def escape_html(text):
    """Escape HTML special characters."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def generate_html(partijen_namen, kleuren, urls, thema_namen, thema_analyse, matrix_rows, tldr_data=None):
    """Genereer de volledige HTML pagina."""

    # TLDR heatmap tabel
    tldr_section = ""
    if tldr_data:
        stance_kleuren = {
            "positief": "#2e7d32",
            "negatief": "#c62828",
            "neutraal": "#757575",
            "gemengd": "#e65100",
            "genoemd": "#90a4ae",
            "niet_genoemd": "#eeeeee",
        }
        stance_labels = {
            "positief": "VOOR",
            "negatief": "TEGEN",
            "neutraal": "Neutraal",
            "gemengd": "Gemengd",
            "genoemd": "Genoemd",
            "niet_genoemd": "—",
        }

        # Groepeer issues per categorie
        categorien = {}
        for issue in tldr_data.get("issues", []):
            cat = issue.get("categorie", "Overig")
            if cat not in categorien:
                categorien[cat] = []
            categorien[cat].append(issue)

        tldr_headers = "".join(
            f'<th style="background-color: {kleuren.get(p, "#666")}; color: white; padding: 6px 4px; font-size: 0.78em; min-width: 60px;">{escape_html(p)}</th>'
            for p in partijen_namen
        )

        tldr_body = ""
        for cat, issues in categorien.items():
            tldr_body += f'<tr><td colspan="{len(partijen_namen) + 1}" class="categorie-header">{escape_html(cat)}</td></tr>\n'
            for issue in issues:
                cells = ""
                for p in partijen_namen:
                    stance_info = issue.get("partijen", {}).get(p, {})
                    stance = stance_info.get("stance", "niet_genoemd")
                    kleur = stance_kleuren.get(stance, "#eeeeee")
                    label = stance_labels.get(stance, "—")
                    tekst_color = "white" if stance in ("positief", "negatief", "gemengd") else ("#fff" if stance == "genoemd" else "#999")
                    tooltip = escape_html(stance_info.get("context", "") or "Geen data gevonden")
                    cells += f'<td class="tldr-cell" style="background-color: {kleur}; color: {tekst_color};" data-tip="{tooltip}">{label}</td>'
                tldr_body += f'<tr><td class="issue-label">{escape_html(issue["label"])}</td>{cells}</tr>\n'

        tldr_section = f'''
        <div id="view-tldr" class="view-section active">
            <h2>Geen tijd om alles te lezen? Scan hier waar de partijen staan!</h2>
            <p class="mobile-hint">&#128241; Deze tabel werkt op een telefoon het beste in landschapsmodus (horizontaal).</p>
            <p style="margin: 10px 0; color: var(--text-light);">
                Hover over een cel voor een citaat uit de bron. Kleuren:
                <span class="tldr-legend" style="background:#2e7d32;">VOOR</span>
                <span class="tldr-legend" style="background:#c62828;">TEGEN</span>
                <span class="tldr-legend" style="background:#e65100;">Gemengd</span>
                <span class="tldr-legend" style="background:#757575;">Neutraal</span>
                <span class="tldr-legend" style="background:#90a4ae;">Genoemd</span>
                <span class="tldr-legend" style="background:#eeeeee; color:#999;">—</span>
            </p>
            <div class="matrix-container">
                <table class="matrix-table tldr-table">
                    <thead>
                        <tr>
                            <th style="text-align:left; background: #f5f5f5; min-width:140px;">Onderwerp</th>
                            {tldr_headers}
                        </tr>
                    </thead>
                    <tbody>
                        {tldr_body}
                    </tbody>
                </table>
            </div>
        </div>'''

    # Matrix tabel
    matrix_headers = "".join(
        f'<th style="background-color: {kleuren.get(p, "#666")}; color: white; writing-mode: vertical-rl; text-orientation: mixed; padding: 10px 6px; font-size: 0.85em; min-width: 40px;">{escape_html(p)}</th>'
        for p in partijen_namen
    )

    matrix_body = ""
    for row in matrix_rows:
        thema_id = row["thema"].lower().replace(" ", "-").replace(",", "").replace("ë", "e").replace("ö","o")
        cells = ""
        for p in partijen_namen:
            if row["partijen"].get(p):
                cells += f'<td class="has-standpunt" title="{escape_html(p)} heeft standpunten over {escape_html(row["thema"])}">&#10003;</td>'
            else:
                cells += '<td class="no-standpunt">-</td>'
        matrix_body += f'<tr><td class="thema-label"><a href="#thema-{thema_id}">{escape_html(row["thema"])}</a></td>{cells}</tr>\n'

    # Thema secties
    thema_sections = ""
    for thema in thema_namen:
        thema_id = thema.lower().replace(" ", "-").replace(",", "").replace("ë", "e").replace("ö","o")
        partij_data = thema_analyse.get(thema, {})

        partij_cards = ""
        for naam in partijen_namen:
            if naam not in partij_data:
                continue
            snippets = partij_data[naam]
            kleur = kleuren.get(naam, "#666")
            url = urls.get(naam, "#")

            content_items = ""
            for s in snippets[:4]:  # Max 4 per partij per thema
                tekst = s["tekst"]
                bron_url = escape_html(s["bron"])
                # Beperk lengte voor leesbaarheid
                if len(tekst) > 500:
                    tekst = tekst[:500] + "..."
                content_items += f'''
                <div class="standpunt-item">
                    <p>{escape_html(tekst)}</p>
                    <a href="{bron_url}" target="_blank" rel="noopener noreferrer" class="bron-link">Bron &rarr;</a>
                </div>'''

            partij_cards += f'''
            <div class="partij-card">
                <div class="partij-card-header" style="background-color: {kleur};">
                    <h4><a href="{escape_html(url)}" target="_blank" rel="noopener noreferrer">{escape_html(naam)}</a></h4>
                </div>
                <div class="partij-card-body">
                    {content_items}
                </div>
            </div>'''

        # Welke partijen hebben WEL en welke NIET een standpunt
        partijen_met = [p for p in partijen_namen if p in partij_data]
        partijen_zonder = [p for p in partijen_namen if p not in partij_data]

        badges = ""
        for p in partijen_met:
            badges += f'<span class="badge badge-yes" style="background-color: {kleuren.get(p, "#666")};">{escape_html(p)}</span> '
        for p in partijen_zonder:
            badges += f'<span class="badge badge-no">{escape_html(p)}</span> '

        thema_sections += f'''
        <section class="thema-section" id="thema-{thema_id}">
            <h3>{escape_html(thema)}</h3>
            <div class="thema-badges">{badges}</div>
            <div class="partij-cards-grid">
                {partij_cards}
            </div>
        </section>'''

    # Navigatie links
    nav_links = ""
    for thema in thema_namen:
        thema_id = thema.lower().replace(" ", "-").replace(",", "").replace("ë", "e").replace("ö","o")
        nav_links += f'<a href="#thema-{thema_id}" class="nav-link">{escape_html(thema)}</a>\n'

    html = f'''<!DOCTYPE html>
<html lang="nl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Standpunten Vergelijking - Gemeenteraad Heiloo 2026</title>
    <style>
        :root {{
            --bg: #f5f5f5;
            --card-bg: #ffffff;
            --text: #333;
            --text-light: #666;
            --border: #ddd;
            --accent: #2196F3;
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.6;
        }}

        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

        header {{
            background: linear-gradient(135deg, #1a237e, #283593);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        header h1 {{ font-size: 2em; margin-bottom: 10px; }}
        header p {{ opacity: 0.85; font-size: 1.1em; }}

        .disclaimer {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 8px;
            padding: 16px;
            margin: 20px 0;
            font-size: 0.9em;
            color: #856404;
        }}

        /* Navigation */
        .view-toggle {{
            display: flex;
            gap: 10px;
            margin: 20px 0;
            flex-wrap: wrap;
        }}
        .view-toggle button {{
            padding: 10px 20px;
            border: 2px solid var(--accent);
            background: white;
            color: var(--accent);
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.2s;
        }}
        .view-toggle button.active {{
            background: var(--accent);
            color: white;
        }}
        .view-toggle button:hover {{
            background: var(--accent);
            color: white;
        }}

        /* Thema navigation */
        .thema-nav {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin: 20px 0;
            padding: 16px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .nav-link {{
            padding: 6px 14px;
            background: #e3f2fd;
            color: #1565c0;
            border-radius: 20px;
            text-decoration: none;
            font-size: 0.85em;
            transition: all 0.2s;
        }}
        .nav-link:hover {{
            background: #1565c0;
            color: white;
        }}

        /* Matrix styles */
        .matrix-container {{
            overflow-x: auto;
            margin: 20px 0;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .matrix-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.9em;
        }}
        .matrix-table th, .matrix-table td {{
            border: 1px solid var(--border);
            padding: 8px;
            text-align: center;
        }}
        .thema-label {{
            text-align: left !important;
            font-weight: 600;
            min-width: 200px;
            padding: 10px !important;
        }}
        .thema-label a {{
            color: var(--text);
            text-decoration: none;
        }}
        .thema-label a:hover {{
            color: var(--accent);
            text-decoration: underline;
        }}
        .has-standpunt {{
            background: #e8f5e9;
            color: #2e7d32;
            font-weight: bold;
            font-size: 1.2em;
        }}
        .no-standpunt {{
            background: #fafafa;
            color: #ccc;
        }}

        /* Thema sections */
        .thema-section {{
            margin: 30px 0;
            padding: 24px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .thema-section h3 {{
            font-size: 1.4em;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid var(--border);
        }}

        .thema-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            margin-bottom: 16px;
        }}
        .badge {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: 600;
            color: white;
        }}
        .badge-no {{
            background: #e0e0e0;
            color: #999;
        }}

        .partij-cards-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 16px;
        }}

        .partij-card {{
            border: 1px solid var(--border);
            border-radius: 8px;
            overflow: hidden;
        }}
        .partij-card-header {{
            padding: 10px 16px;
            color: white;
        }}
        .partij-card-header h4 {{
            margin: 0;
            font-size: 1em;
        }}
        .partij-card-header a {{
            color: white;
            text-decoration: none;
        }}
        .partij-card-header a:hover {{
            text-decoration: underline;
        }}
        .partij-card-body {{
            padding: 12px 16px;
        }}

        .standpunt-item {{
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .standpunt-item:last-child {{
            border-bottom: none;
            margin-bottom: 0;
            padding-bottom: 0;
        }}
        .standpunt-item p {{
            font-size: 0.9em;
            white-space: pre-line;
            margin-bottom: 4px;
        }}
        .bron-link {{
            font-size: 0.8em;
            color: var(--accent);
            text-decoration: none;
        }}
        .bron-link:hover {{
            text-decoration: underline;
        }}

        /* View sections */
        .view-section {{ display: none; }}
        .view-section.active {{ display: block; }}

        /* TLDR heatmap */
        .tldr-table td.tldr-cell {{
            font-weight: 700;
            font-size: 0.8em;
            padding: 5px 3px;
            cursor: help;
            border: 1px solid #e0e0e0;
            position: relative;
        }}
        .tldr-tooltip {{
            display: none;
            position: fixed;
            background: #333;
            color: #fff;
            padding: 10px 14px;
            border-radius: 6px;
            font-size: 0.82em;
            font-weight: 400;
            max-width: 360px;
            line-height: 1.5;
            z-index: 1000;
            pointer-events: none;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            word-break: break-word;
        }}
        .tldr-tooltip.visible {{ display: block; }}
        .tldr-legend {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            color: white;
            font-size: 0.8em;
            margin: 0 2px;
        }}
        .categorie-header {{
            background: #e3f2fd !important;
            font-weight: 700;
            text-align: left !important;
            padding: 6px 8px !important;
            font-size: 0.88em;
            color: #1565c0;
        }}
        .issue-label {{
            text-align: left !important;
            font-weight: 600;
            padding: 5px 6px !important;
            min-width: 140px;
            font-size: 0.82em;
        }}

        footer {{
            text-align: center;
            padding: 30px;
            color: var(--text-light);
            font-size: 0.85em;
        }}

        .mobile-hint {{
            display: none;
            margin: 8px 0;
            padding: 8px 12px;
            background: #fff3e0;
            border: 1px solid #ffe0b2;
            border-radius: 6px;
            color: #e65100;
            font-size: 0.85em;
        }}

        @media (max-width: 768px) {{
            .partij-cards-grid {{
                grid-template-columns: 1fr;
            }}
            header h1 {{ font-size: 1.4em; }}
            .mobile-hint {{ display: block; }}
        }}
        @media (max-height: 500px) and (orientation: landscape) {{
            .container {{ padding: 8px; }}
            .tldr-table td.tldr-cell {{ padding: 3px 2px; font-size: 0.75em; }}
            .issue-label {{ padding: 3px 4px !important; min-width: 110px; font-size: 0.75em; }}
            .categorie-header {{ padding: 4px 6px !important; font-size: 0.82em; }}
            .tldr-table th {{ padding: 4px 2px; font-size: 0.72em; min-width: 50px !important; }}
            .mobile-hint {{ display: none; }}
        }}
    </style>
</head>
<body>
    <header>
        <h1>Standpunten Vergelijking</h1>
        <p>Gemeenteraadsverkiezingen Heiloo 2026</p>
    </header>

    <div class="container">
        <div class="disclaimer">
            <strong>Let op:</strong> Alle standpunten op deze pagina zijn direct overgenomen van de websites van de deelnemende partijen.
            Er is niets toegevoegd, geïnterpreteerd of voorspeld. Klik op "Bron" bij elk standpunt om de originele pagina te bekijken.
            De indeling in thema&rsquo;s is automatisch gemaakt op basis van trefwoorden.
        </div>

        <div class="view-toggle">
            <button class="active" onclick="showView('tldr')">TL;DR Vergelijking</button>
            <button onclick="showView('matrix')">Matrix overzicht</button>
            <button onclick="showView('themas')">Per thema vergelijken</button>
        </div>

        <!-- TLDR VIEW -->
        {tldr_section}

        <!-- MATRIX VIEW -->
        <div id="view-matrix" class="view-section">
            <h2>Overzicht: welke partij heeft standpunten over welk thema?</h2>
            <p style="margin: 10px 0; color: var(--text-light);">Klik op een thema om de standpunten te lezen.</p>
            <div class="matrix-container">
                <table class="matrix-table">
                    <thead>
                        <tr>
                            <th style="text-align:left; background: #f5f5f5;">Thema</th>
                            {matrix_headers}
                        </tr>
                    </thead>
                    <tbody>
                        {matrix_body}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- THEMA VIEW -->
        <div id="view-themas" class="view-section">
            <h2>Standpunten per thema</h2>
            <div class="thema-nav">
                {nav_links}
            </div>
            {thema_sections}
        </div>
    </div>

    <footer>
        <p>Gegenereerd op basis van openbare informatie van partij-websites. Geen interpretatie of voorspelling.</p>
        <p>Bronnen: {', '.join(f'<a href="{escape_html(u)}" target="_blank" rel="noopener noreferrer">{escape_html(n)}</a>' for n, u in urls.items())}</p>
        <p style="margin-top: 8px;">Open source &mdash; <a href="https://github.com/frankvaneykelen/GR2026-Heiloo" target="_blank" rel="noopener noreferrer">bekijk de broncode</a> of <a href="https://github.com/frankvaneykelen/GR2026-Heiloo/issues" target="_blank" rel="noopener noreferrer">meld een probleem</a>.</p>
    </footer>

    <script>
        function showView(view) {{
            document.querySelectorAll('.view-section').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.view-toggle button').forEach(el => el.classList.remove('active'));
            document.getElementById('view-' + view).classList.add('active');
            event.target.classList.add('active');
        }}

        // Als er een anchor in de URL ziet die naar een thema verwijst, schakel naar thema-view
        if (window.location.hash && window.location.hash.startsWith('#thema-')) {{
            showView('themas');
        }}

        // Klik op thema in matrix -> ga naar thema view
        document.querySelectorAll('.thema-label a').forEach(link => {{
            link.addEventListener('click', function(e) {{
                showView('themas');
                // Update active button
                document.querySelectorAll('.view-toggle button').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.view-toggle button')[1].classList.add('active');
            }});
        }});

        // TLDR tooltip (hover + tap)
        (function() {{
            var tip = document.createElement('div');
            tip.className = 'tldr-tooltip';
            document.body.appendChild(tip);
            var active = null;

            function showTip(cell, x, y) {{
                var text = cell.getAttribute('data-tip');
                if (!text || text === 'Geen data gevonden') return;
                tip.textContent = text;
                tip.classList.add('visible');
                // Position: prefer below-right of cursor/tap, but keep on screen
                var vw = window.innerWidth, vh = window.innerHeight;
                var left = Math.min(x + 10, vw - 380);
                var top = y + 16;
                if (left < 8) left = 8;
                if (top + tip.offsetHeight > vh - 8) top = y - tip.offsetHeight - 10;
                tip.style.left = left + 'px';
                tip.style.top = top + 'px';
                active = cell;
            }}

            function hideTip() {{
                tip.classList.remove('visible');
                active = null;
            }}

            // Desktop hover
            document.querySelectorAll('.tldr-cell[data-tip]').forEach(function(cell) {{
                cell.addEventListener('mouseenter', function(e) {{
                    showTip(cell, e.clientX, e.clientY);
                }});
                cell.addEventListener('mousemove', function(e) {{
                    if (active === cell) {{
                        var vw = window.innerWidth;
                        var left = Math.min(e.clientX + 10, vw - 380);
                        if (left < 8) left = 8;
                        tip.style.left = left + 'px';
                        tip.style.top = (e.clientY + 16) + 'px';
                    }}
                }});
                cell.addEventListener('mouseleave', hideTip);
            }});

            // Mobile tap
            document.addEventListener('click', function(e) {{
                var cell = e.target.closest('.tldr-cell[data-tip]');
                if (cell) {{
                    if (active === cell) {{ hideTip(); return; }}
                    var rect = cell.getBoundingClientRect();
                    showTip(cell, rect.left, rect.bottom);
                }} else {{
                    hideTip();
                }}
            }});
        }})();
    </script>
</body>
</html>'''
    return html


def main():
    print("=" * 60)
    print("Analyse Standpunten - Gemeenteraad Heiloo 2026")
    print("=" * 60)

    partijen_namen, thema_analyse = analyse_partijen()

    print(f"\nThema's gevonden: {len(thema_analyse)}")
    for thema, partij_data in thema_analyse.items():
        partijen = list(partij_data.keys())
        print(f"  {thema}: {len(partijen)} partijen ({', '.join(partijen)})")

    # Sla analyse op
    save_analyse(partijen_namen, thema_analyse)

    # Genereer website
    generate_website(partijen_namen, thema_analyse)

    print("\nKlaar! Open docs/index.html in je browser.")


if __name__ == "__main__":
    main()
