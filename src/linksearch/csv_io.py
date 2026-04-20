from __future__ import annotations

import csv
from pathlib import Path

from linksearch.models import CandidateLink, ProductInput


INPUT_COLUMNS = ("brand", "sku", "product name")
OUTPUT_COLUMNS = ("Media", "Brand", "URL", "SKU", "Product Name")


def _normalize_header(h: str) -> str:
    return h.strip().lower()


def read_products(path: Path) -> list[ProductInput]:
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise ValueError("CSV has no header row.")

    fieldmap = {_normalize_header(f): f for f in reader.fieldnames if f}

    def col(*names: str) -> str | None:
        for name in names:
            key = _normalize_header(name)
            if key in fieldmap:
                return fieldmap[key]
        return None

    b = col("brand", "brand name", "manufacturer")
    s = col("sku", "model", "part number", "item sku", "mpn")
    p = col("product name", "product", "title", "description", "name")
    if not b or not s:
        raise ValueError(
            "Input CSV must include Brand and SKU columns (case-insensitive). "
            "Product name is optional."
        )

    rows: list[ProductInput] = []
    for raw in reader:
        brand = (raw.get(b) or "").strip()
        sku = (raw.get(s) or "").strip()
        pname = (raw.get(p) or "").strip() if p else ""
        if not brand or not sku:
            continue
        rows.append(ProductInput(brand=brand, sku=sku, product_name=pname))
    if not rows:
        raise ValueError("No data rows found (Brand and SKU required).")
    return rows


def write_results(path: Path, rows: list[CandidateLink]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(OUTPUT_COLUMNS)
        for r in rows:
            w.writerow(
                [
                    r.media,
                    r.brand,
                    r.url,
                    r.sku,
                    r.product_name,
                ]
            )
