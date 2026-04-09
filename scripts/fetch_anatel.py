#!/usr/bin/env python3
"""
Download Anatel certified products data and filter to watched brands.

Data source: Anatel open data (updated daily)
- Full dataset: ~47MB CSV with 178k+ rows
- We download, filter to target brands/types, and save a small subset (~100KB)
"""

import csv
import io
import json
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"

URLS = {
    "full": "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos/produtos_certificados.zip",
    "5g": "https://www.anatel.gov.br/dadosabertos/paineis_de_dados/certificacao_de_produtos/celulares_5g_homologados.zip",
}

# CSV field names (semicolon-separated, UTF-8 BOM)
FIELDS = [
    "Data da Homologação",
    "Número de Homologação",
    "Nome do Solicitante",
    "CNPJ do Solicitante",
    "Certificado de Conformidade Técnica",
    "Data do Certificado de Conformidade Técnica",
    "Data de Validade do Certificado",
    "Código de Situação do Certificado",
    "Situação do Certificado",
    "Código de Situação do Requerimento",
    "Situação do Requerimento",
    "Nome do Fabricante",
    "Modelo",
    "Nome Comercial",
    "Categoria do Produto",
    "Tipo do Produto",
    "IC_ANTENA",
    "IC_ATIVO",
    "País do Fabricante",
    "CodUIT",
    "CodISO",
]


def download_zip(url: str) -> bytes:
    """Download a ZIP file and return the CSV content inside it."""
    print(f"Downloading {url} ...")
    req = Request(url, headers={"User-Agent": "anatel-monitor/1.0"})
    with urlopen(req, timeout=120) as resp:
        zip_bytes = resp.read()
    print(f"  Downloaded {len(zip_bytes):,} bytes")

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        csv_name = zf.namelist()[0]
        print(f"  Extracting {csv_name}")
        return zf.read(csv_name)


def load_brands_config() -> dict:
    with open(CONFIG_DIR / "brands.json", encoding="utf-8") as f:
        return json.load(f)


def build_manufacturer_lookup(config: dict) -> dict[str, str]:
    """Map lowercase manufacturer name -> canonical brand name."""
    lookup = {}
    for brand, names in config["watch_brands"].items():
        for name in names:
            lookup[name.lower().strip()] = brand
    return lookup


def filter_rows(csv_bytes: bytes, config: dict) -> list[dict]:
    """Filter CSV to watched brands, excluding battery/charger types."""
    manufacturer_lookup = build_manufacturer_lookup(config)
    exclude_types = set(config.get("exclude_types", []))

    text = csv_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text), delimiter=";")

    filtered = []
    for row in reader:
        fabricante = (row.get("Nome do Fabricante") or "").strip()
        tipo = (row.get("Tipo do Produto") or "").strip()

        brand = manufacturer_lookup.get(fabricante.lower())
        if not brand:
            continue
        if tipo in exclude_types:
            continue

        filtered.append({
            "data_homologacao": row.get("Data da Homologação", "").strip(),
            "numero_homologacao": row.get("Número de Homologação", "").strip(),
            "fabricante": fabricante,
            "brand": brand,
            "modelo": row.get("Modelo", "").strip(),
            "nome_comercial": row.get("Nome Comercial", "").strip(),
            "tipo_produto": tipo,
            "situacao": row.get("Situação do Requerimento", "").strip(),
            "pais": row.get("País do Fabricante", "").strip(),
        })

    return filtered


def save_csv(rows: list[dict], path: Path):
    """Save filtered rows as a clean CSV."""
    if not rows:
        print("  No rows to save!")
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved {len(rows)} rows to {path.name} ({path.stat().st_size:,} bytes)")


def save_5g(csv_bytes: bytes, path: Path):
    """Save 5G phones CSV as-is (already small enough)."""
    text = csv_bytes.decode("utf-8-sig")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    lines = text.strip().count("\n")
    print(f"  Saved {lines} rows to {path.name}")


def main():
    DATA_DIR.mkdir(exist_ok=True)

    config = load_brands_config()

    # 1. Download and filter full dataset
    try:
        full_csv = download_zip(URLS["full"])
        filtered = filter_rows(full_csv, config)
        save_csv(filtered, DATA_DIR / "watched_brands.csv")
        print(f"  Brands found: {sorted(set(r['brand'] for r in filtered))}")
    except Exception as e:
        print(f"ERROR downloading full dataset: {e}", file=sys.stderr)
        sys.exit(1)

    # 2. Download 5G phones data
    try:
        fiveg_csv = download_zip(URLS["5g"])
        save_5g(fiveg_csv, DATA_DIR / "celulares_5g.csv")
    except Exception as e:
        print(f"WARNING: 5G data download failed: {e}", file=sys.stderr)

    # 3. Write metadata
    meta = {
        "last_fetch": datetime.utcnow().isoformat() + "Z",
        "total_filtered_rows": len(filtered),
        "brands": {
            brand: len([r for r in filtered if r["brand"] == brand])
            for brand in sorted(set(r["brand"] for r in filtered))
        },
    }
    with open(DATA_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"\nDone! {meta['total_filtered_rows']} rows across {len(meta['brands'])} brands")


if __name__ == "__main__":
    main()
