from __future__ import annotations

import httpx

from linksearch.config import Settings
from linksearch.models import CandidateLink, ProductInput


YOUTUBE_SEARCH = "https://www.googleapis.com/youtube/v3/search"


async def search_youtube(
    client: httpx.AsyncClient,
    settings: Settings,
    product: ProductInput,
    queries: list[str],
) -> list[CandidateLink]:
    if not settings.youtube_enabled():
        return []
    key = settings.youtube_api_key
    out: list[CandidateLink] = []
    seen: set[str] = set()
    q_text = " ".join(queries[:3]) if queries else product.primary_query()
    params = {
        "part": "snippet",
        "type": "video",
        "maxResults": settings.max_results_per_platform,
        "q": q_text[:280],
        "key": key,
    }
    r = await client.get(YOUTUBE_SEARCH, params=params)
    r.raise_for_status()
    data = r.json()
    for item in data.get("items") or []:
        vid = (item.get("id") or {}).get("videoId")
        sn = item.get("snippet") or {}
        title = sn.get("title") or ""
        desc = sn.get("description") or ""
        if not vid:
            continue
        url = f"https://www.youtube.com/watch?v={vid}"
        if url in seen:
            continue
        seen.add(url)
        out.append(
            CandidateLink(
                media="Youtube",
                brand=product.normalized_brand(),
                url=url,
                sku=product.sku.strip(),
                product_name=product.product_name.strip(),
                title=title,
                snippet=desc[:500],
                source_query=q_text,
            )
        )
    return out
