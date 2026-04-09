#!/usr/bin/env python3
"""
Compare current vs previous Anatel data snapshot to find new certifications.

Usage:
  python analyze.py                  # compare HEAD vs HEAD~1
  python analyze.py --days 7         # compare HEAD vs 7 days ago
  python analyze.py --brand SAMSUNG  # filter by brand
  python analyze.py --output json    # output as JSON instead of table
"""

import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime, timedelta
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
CONFIG_DIR = ROOT / "config"

CSV_FILE = "data/watched_brands.csv"


def git_show(ref: str, path: str) -> str | None:
    """Get file content at a specific git ref."""
    try:
        result = subprocess.run(
            ["git", "show", f"{ref}:{path}"],
            capture_output=True, text=True, cwd=ROOT
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def read_csv_rows(text: str) -> list[dict]:
    reader = csv.DictReader(StringIO(text))
    return list(reader)


def read_current_csv() -> list[dict]:
    path = DATA_DIR / "watched_brands.csv"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def find_new_models(current: list[dict], previous: list[dict]) -> list[dict]:
    """Find models in current that don't exist in previous."""
    prev_models = {(r["brand"], r["modelo"]) for r in previous}

    seen = set()
    new_items = []
    for row in current:
        key = (row["brand"], row["modelo"])
        if key not in prev_models and key not in seen:
            seen.add(key)
            new_items.append(row)

    return new_items


def deduplicate_by_model(rows: list[dict]) -> list[dict]:
    """Keep one row per (brand, modelo), preferring rows with nome_comercial."""
    best = {}
    for row in rows:
        key = (row["brand"], row["modelo"])
        if key not in best or (row.get("nome_comercial") and not best[key].get("nome_comercial")):
            best[key] = row
    return sorted(best.values(), key=lambda r: (r["brand"], r.get("data_homologacao", "")))


def format_table(items: list[dict]) -> str:
    """Format as a readable table."""
    if not items:
        return "No new certifications found."

    lines = []
    lines.append(f"{'Brand':<10} {'Model':<20} {'Commercial Name':<25} {'Date':<12} {'Type':<30}")
    lines.append("─" * 97)

    current_brand = None
    for item in items:
        brand = item.get("brand", "")
        if brand != current_brand:
            if current_brand is not None:
                lines.append("")
            current_brand = brand

        lines.append(
            f"{brand:<10} "
            f"{item.get('modelo', ''):<20} "
            f"{item.get('nome_comercial', ''):<25} "
            f"{item.get('data_homologacao', ''):<12} "
            f"{item.get('tipo_produto', ''):<30}"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze new Anatel certifications")
    parser.add_argument("--days", type=int, default=None, help="Compare with N days ago")
    parser.add_argument("--brand", type=str, default=None, help="Filter by brand")
    parser.add_argument("--output", choices=["table", "json", "markdown"], default="table")
    parser.add_argument("--ref", type=str, default="HEAD~1", help="Git ref to compare against")
    args = parser.parse_args()

    # Pull latest
    subprocess.run(["git", "pull", "--ff-only"], cwd=ROOT, capture_output=True)

    # Read current data
    current = read_current_csv()
    if not current:
        print("ERROR: No current data found. Run fetch_anatel.py first.", file=sys.stderr)
        sys.exit(1)

    # Read previous data
    ref = args.ref
    if args.days:
        # Find commit from N days ago
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
        result = subprocess.run(
            ["git", "log", f"--since={since}", "--format=%H", "--reverse", "--", CSV_FILE],
            capture_output=True, text=True, cwd=ROOT
        )
        commits = result.stdout.strip().split("\n")
        ref = commits[0] if commits and commits[0] else "HEAD~1"

    prev_text = git_show(ref, CSV_FILE)
    if not prev_text:
        print(f"No previous data at {ref}. Showing all current entries as new.\n")
        previous = []
    else:
        previous = read_csv_rows(prev_text)

    # Find new models
    new_items = find_new_models(current, previous)
    new_items = deduplicate_by_model(new_items)

    # Filter by brand
    if args.brand:
        new_items = [r for r in new_items if r["brand"].upper() == args.brand.upper()]

    # Output
    if args.output == "json":
        print(json.dumps(new_items, indent=2, ensure_ascii=False))
    elif args.output == "markdown":
        if not new_items:
            print("Sem novos produtos certificados.")
        else:
            print(f"## Novos Produtos Certificados ({len(new_items)} modelos)\n")
            print(f"| Brand | Modelo | Nome Comercial | Data | Tipo |")
            print(f"|-------|--------|---------------|------|------|")
            for item in new_items:
                print(f"| {item['brand']} | {item['modelo']} | {item.get('nome_comercial', '')} | {item['data_homologacao']} | {item['tipo_produto']} |")
    else:
        print(f"\n=== New Certifications (vs {ref}) ===\n")
        print(format_table(new_items))
        print(f"\n--- Summary ---")
        print(f"Total new models: {len(new_items)}")
        by_brand = {}
        for item in new_items:
            by_brand.setdefault(item["brand"], []).append(item)
        for brand, items in sorted(by_brand.items()):
            print(f"  {brand}: {len(items)} new")


if __name__ == "__main__":
    main()
