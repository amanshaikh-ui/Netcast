"""
Stdin JSON / stdout JSON for TikTok direct search (TikTokApi + Playwright).

Used by the Next.js API when TIKTOK_DIRECT_PYTHON=true so the web app can use
the same path as ``pip install -e ".[direct]"``.

Input (stdin): {"brand": str, "sku": str, "productName": str, "queries"?: str[]}
Output (stdout): JSON array of row dicts (CandidateLink fields).
"""

from __future__ import annotations

import asyncio
import json
import sys


async def _run() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        json.dump([], sys.stdout)
        return
    data = json.loads(raw)
    brand = str(data.get("brand") or "").strip()
    sku = str(data.get("sku") or "").strip()
    product_name = str(
        data.get("productName") or data.get("product_name") or ""
    ).strip()
    queries = data.get("queries")

    from linksearch.aliases import build_product_aliases
    from linksearch.config import load_settings
    from linksearch.groq_helper import build_search_queries
    from linksearch.models import ProductInput

    product = ProductInput(brand=brand, sku=sku, product_name=product_name)
    settings = load_settings()

    pa = build_product_aliases(product)
    if queries is None or not isinstance(queries, list):
        queries = build_search_queries(settings, product, pa)
    else:
        queries = [str(x).strip() for x in queries if str(x).strip()]

    try:
        from linksearch.platforms.tiktok_direct import search_tiktok_direct
    except ImportError as e:
        print(f"TikTok direct unavailable: {e}", file=sys.stderr)
        json.dump([], sys.stdout)
        return

    from linksearch.scoring_evidence import extract_author_handle

    rows = await search_tiktok_direct(settings, product, queries, pa)
    out = []
    for r in rows:
        ah = extract_author_handle(r.url, r.media)
        out.append(
            {
                "media": r.media,
                "brand": r.brand,
                "url": r.url,
                "sku": r.sku,
                "productName": r.product_name,
                "title": r.title,
                "snippet": r.snippet,
                "score": r.score,
                "sourceQuery": r.source_query,
                "authorHandle": ah,
            }
        )
    json.dump(out, sys.stdout)


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
