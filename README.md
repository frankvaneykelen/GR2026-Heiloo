# GR2026 Heiloo

| Partij | Website |
|--------|---------|
| Heiloo-2000 | https://www.heiloo-2000.nl/ |
| GROENLINKS/Partij van de Arbeid (PvdA) | https://heiloo.groenlinkspvda.nl/ |
| VVD | https://www.vvd.nl/gemeente-heiloo/ |
| D66 | https://d66.nl/heiloo/ |
| Gemeentebelangen Heiloo | https://www.gemeentebelangenheiloo.nl/ |
| CDA | https://www.cda.nl/noord-holland/heiloo/ |

## Getting Started

### Prerequisites

- Python 3.10+ (project developed and tested on Python 3.10; earlier versions may work but are not officially supported)

### Installation

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install requests beautifulsoup4 lxml
```

### Usage

1. **Scrape party websites** — fetches positions and saves them to `data/partijen/`:
   ```bash
   python scrape_partijen.py
   ```

2. **Analyze positions by theme** — groups scraped data into themes and saves to `data/`:
   ```bash
   python analyse_standpunten.py
   ```

3. **TL;DR stance analysis** — detects for/against/neutral per specific issue:
   ```bash
   python analyse_tldr.py
   ```

4. **Generate comparison website** — builds `docs/index.html` with a TL;DR heatmap, theme matrix, and per-theme detail view:
   ```bash
   python analyse_standpunten.py
   ```

5. Open `docs/index.html` in your browser to view the comparison.