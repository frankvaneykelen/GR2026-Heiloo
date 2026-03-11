"""
Scraper voor standpunten van politieke partijen in Heiloo.
Bezoekt de websites, volgt relevante links, en slaat de content op.
Blijft strikt binnen de Heiloo-specifieke URL-prefix per partij.
"""

import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os

import time
import json

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8",
}

# Elke partij heeft een start URL en een URL-prefix waarbinnen we blijven.
# Zo voorkomen we dat we naar landelijke partijpagina's navigeren.
PARTIJEN = {
    "Heiloo-2000": {
        "start": "https://www.heiloo-2000.nl/",
        "prefix": "https://www.heiloo-2000.nl/",
    },
    "GroenLinks-PvdA": {
        "start": "https://heiloo.groenlinkspvda.nl/",
        "prefix": "https://heiloo.groenlinkspvda.nl/",
    },
    "VVD": {
        "start": "https://www.vvd.nl/gemeente-heiloo/",
        "prefix": "https://www.vvd.nl/gemeente-heiloo/",
    },
    "D66": {
        "start": "https://d66.nl/heiloo/",
        "prefix": "https://d66.nl/heiloo/",
    },
    "Gemeentebelangen Heiloo": {
        "start": "https://www.gemeentebelangenheiloo.nl/",
        "prefix": "https://www.gemeentebelangenheiloo.nl/",
    },
    "CDA": {
        "start": "https://www.cda.nl/noord-holland/heiloo/",
        "prefix": "https://www.cda.nl/noord-holland/heiloo/",
    },
}

OUTPUT_DIR = "data/partijen"

# Paden die we overslaan (geen inhoudelijke standpunten)
SKIP_PATTERNS = [
    "/cookie", "/privacy", "/disclaimer", "/wp-content/",
    "/wp-admin/", "/wp-login", "/feed/", "/tag/", "/author/",
    "/mensen/", "/mens/", "/onze-mensen/", "/alle-mensen/",
    "/kandidaten/", "/kandidaten-", "/profielen/",
]

# Regex for numbered page slugs like /1080903_gemeenteraads-vergadering-11-2022
# Also skip old election pages, vote results, and algemene beschouwingen
SKIP_REGEX = re.compile(
    r"/\d{5,}_"                                        # numbered slugs
    r"|/algemene-beschouwingen-"                        # algemene beschouwingen
    r"|/gemeenteraadsverkiezingen-(?!2026)"             # old election years (not 2026)
    r"|/verkiezingsuitslagen-"                          # vote results
)


def get_page(url, timeout=15):
    """Haal een pagina op met error handling."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        return resp.text
    except Exception as e:
        print(f"  FOUT bij ophalen {url}: {e}")
        return None


def extract_text(html):
    """Extraheer leesbare tekst uit HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Verwijder scripts, styles, nav, footer, header
    for tag in soup(["script", "style", "nav", "footer", "header", "iframe", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator="\n", strip=True)
    # Verwijder excessieve lege regels
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_links(html, current_url, url_prefix):
    """Extraheer alle links die binnen de URL-prefix vallen."""
    soup = BeautifulSoup(html, "lxml")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(current_url, href)
        parsed = urlparse(full_url)

        # Geen downloads
        if parsed.path.endswith((".pdf", ".jpg", ".png", ".gif", ".zip", ".doc", ".docx")):
            continue

        # Schoon de URL op (verwijder fragment en query)
        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"

        # STRIKT: alleen links die binnen de prefix vallen
        if not clean_url.startswith(url_prefix):
            continue

        # Skip niet-inhoudelijke paden
        lower_path = parsed.path.lower()
        if any(skip in lower_path for skip in SKIP_PATTERNS):
            continue
        if SKIP_REGEX.search(lower_path):
            continue

        links.add(clean_url)

    return links


def scrape_partij(naam, start_url, url_prefix, max_pages=50):
    """Scrape een partij-website en verzamel standpunten, strikt binnen prefix."""
    print(f"\n{'='*60}")
    print(f"Scraping: {naam}")
    print(f"  Start: {start_url}")
    print(f"  Prefix: {url_prefix}")
    print(f"{'='*60}")

    visited = set()
    to_visit = {start_url}
    all_content = []
    pages_scraped = 0

    while to_visit and pages_scraped < max_pages:
        url = to_visit.pop()
        # Normaliseer: met en zonder trailing slash als "bezocht"
        normalized = url.rstrip("/")
        if normalized in visited:
            continue
        visited.add(normalized)

        html = get_page(url)
        if not html:
            continue

        pages_scraped += 1
        text = extract_text(html)

        if len(text) > 100:  # Alleen pagina's met substantiële content
            all_content.append({
                "url": url,
                "text": text
            })
            print(f"  [{pages_scraped}] {url} ({len(text)} chars)")

        # Zoek nieuwe links, strikt binnen prefix
        links = extract_links(html, url, url_prefix)
        for link in links:
            if link.rstrip("/") not in visited:
                to_visit.add(link)

        time.sleep(0.5)  # Beleefd scrapen

    print(f"  Totaal: {pages_scraped} pagina's gescraped, {len(all_content)} met content")
    return all_content


def save_partij_data(naam, content):
    """Sla de gescrapede data op in een bestand."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", naam)

    # Sla op als tekst bestand
    txt_path = os.path.join(OUTPUT_DIR, f"{safe_name}.txt")
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(f"# Standpunten {naam}\n")
        f.write(f"# Gescraped op: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"# Aantal pagina's: {len(content)}\n\n")
        for page in content:
            f.write(f"\n{'='*60}\n")
            f.write(f"Bron: {page['url']}\n")
            f.write(f"{'='*60}\n\n")
            f.write(page["text"])
            f.write("\n\n")

    # Sla ook op als JSON voor verdere verwerking
    json_path = os.path.join(OUTPUT_DIR, f"{safe_name}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({
            "partij": naam,
            "scraped_at": time.strftime("%Y-%m-%d %H:%M"),
            "pages": content
        }, f, ensure_ascii=False, indent=2)

    print(f"  Opgeslagen: {txt_path} en {json_path}")
    return txt_path


def main():
    print("=" * 60)
    print("Standpunten Scraper - Gemeenteraad Heiloo 2026")
    print("=" * 60)

    for naam, config in PARTIJEN.items():
        content = scrape_partij(naam, config["start"], config["prefix"])
        save_partij_data(naam, content)

    print("\n\nAlle partijen gescraped!")
    print(f"Data opgeslagen in: {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
