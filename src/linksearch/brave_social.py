"""Brave Search API as fallback web discovery (after native + DDG). Requires BRAVE_SEARCH_API_KEY."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

import httpx

from linksearch.models import CandidateLink, ProductInput
from linksearch.platforms.google_cse import url_matches_site_host

if TYPE_CHECKING:
    from linksearch.config import Settings

logger = logging.getLogger(__name__)

BRAVE_WEB = "https://api.search.brave.com/res/v1/web/search"
BRAVE_DELAY = 0.35


async def search_site_brave(
    client: httpx.AsyncClient,
    settings: Settings,
    product: ProductInput,
    queries: list[str],
    site_host: str,
    media_label: str,
    max_queries: int = 4,
    result_cap: int = 5,
) -> list[CandidateLink]:
    key = settings.brave_search_api_key.strip()
    if not key or not settings.brave_search_enabled:
        return []

    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    out: list[CandidateLink] = []
    seen: set[str] = set()

    qlist: list[str] = []
    for q in queries[: max_queries * 3]:
        t = q.strip()
        if t:
            qlist.append(f"{t} site:{site_host}")
    qlist = qlist[:max_queries]

    for full_q in qlist:
        if len(out) >= result_cap:
            break
        try:
            await asyncio.sleep(BRAVE_DELAY)
            r = await client.get(
                BRAVE_WEB,
                headers={
                    "X-Subscription-Token": key,
                    "Accept": "application/json",
                },
                params={"q": full_q[:400], "count": min(10, result_cap + 3)},
                timeout=20.0,
            )
            if r.status_code >= 400:
                continue
            data = r.json()
            web = data.get("web", {}) if isinstance(data, dict) else {}
            results = web.get("results", []) if isinstance(web, dict) else []
        except Exception as e:
            logger.warning("Brave search failed (%s): %s", full_q[:60], e)
            continue

        for item in results:
            if len(out) >= result_cap:
                break
            if not isinstance(item, dict):
                continue
            url = str(item.get("url") or "").strip()
            if not url or url in seen:
                continue
            if not url_matches_site_host(url, site_host):
                continue
            seen.add(url)
            title = str(item.get("title") or "")
            desc = str(item.get("description") or "")[:500]
            out.append(
                CandidateLink(
                    media=media_label,
                    brand=brand,
                    url=url,
                    sku=sku,
                    product_name=pname,
                    title=title,
                    snippet=desc,
                    source_query=f"brave:{full_q[:200]}",
                )
            )

    return out
