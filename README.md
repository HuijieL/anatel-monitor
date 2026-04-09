# Anatel Monitor

Track new product certifications from Anatel (Brazil telecom regulator) for competitive intelligence.

## How it works

1. **GitHub Actions** downloads Anatel's open data daily (UTC 12:00 / BRT 09:00)
2. Filters to watched brands: Samsung, Apple, Xiaomi, Honor, OPPO, Vivo/JOVI, JBL
3. Commits filtered CSV to `data/` — git history = time series
4. Local analysis script diffs current vs previous to find new certifications

## Quick start

```bash
# Test locally
python scripts/fetch_anatel.py

# Analyze new products (after at least 2 commits)
python scripts/analyze.py
python scripts/analyze.py --brand SAMSUNG
python scripts/analyze.py --output markdown
```

## Data source

- URL: `anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos/produtos_certificados.zip`
- Format: CSV (semicolon-separated, UTF-8 BOM)
- Updated: Daily
- Auth: None required (public open data)
