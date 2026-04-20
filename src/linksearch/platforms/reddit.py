from __future__ import annotations

import httpx

from linksearch.config import Settings
from linksearch.models import CandidateLink, ProductInput


REDDIT_SEARCH = "https://www.reddit.com/search.json"


async def search_reddit(
    client: httpx.AsyncClient,
    settings: Settings,
    product: ProductInput,
    queries: list[str],
) -> list[CandidateLink]:
    headers = {"User-Agent": settings.reddit_user_agent}
    out: list[CandidateLink] = []
    seen: set[str] = set()
    # Reddit's search often returns very few hits for brand+SKU alone; include product name when present.
    base_q = product.primary_query()[:300]
    params = {
        "q": base_q[:300],
        "limit": min(25, settings.max_results_per_platform * 3),
        "sort": "relevance",
        "raw_json": 1,
    }
    r = await client.get(REDDIT_SEARCH, params=params, headers=headers)
    if r.status_code == 429:
        return out
    r.raise_for_status()
    data = r.json()
    children = ((data.get("data") or {}).get("children")) or []
    for ch in children:
        d = ch.get("data") or {}
        permalink = d.get("permalink") or ""
        title = d.get("title") or ""
        selftext = (d.get("selftext") or "")[:500]
        if not permalink:
            continue
        url = f"https://www.reddit.com{permalink}".split("?")[0]
        if url in seen:
            continue
        seen.add(url)
        out.append(
            CandidateLink(
                media="Reddit",
                brand=product.normalized_brand(),
                url=url,
                sku=product.sku.strip(),
                product_name=product.product_name.strip(),
                title=title,
                snippet=selftext,
                source_query=base_q,
            )
        )
        if len(out) >= settings.max_results_per_platform * 2:
            break
    return out
