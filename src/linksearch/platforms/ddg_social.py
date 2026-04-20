from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from linksearch.models import CandidateLink, ProductInput
from linksearch.platforms.google_cse import (
    build_platform_search_queries,
    url_matches_site_host,
)

if TYPE_CHECKING:
    from linksearch.config import Settings

logger = logging.getLogger(__name__)

MAX_DDG_QUERIES_PER_SITE = 4
DDG_DELAY_SECONDS = 0.35


def search_site_ddg_sync(
    settings: Settings,
    product: ProductInput,
    queries: list[str],
    site_host: str,
    platform_keyword: str,
    media_label: str,
    *,
    max_queries: int | None = None,
    result_cap: int | None = None,
) -> list[CandidateLink]:
    """
    Discover links via DuckDuckGo text search (free, no Google Custom Search API).
    Keeps URLs whose host matches ``site_host``.
    """
    if not settings.ddg_social_enabled:
        return []
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        logger.warning(
            "duckduckgo-search not installed; skip DDG social search (pip install duckduckgo-search)."
        )
        return []

    mq_limit = max_queries if max_queries is not None else MAX_DDG_QUERIES_PER_SITE
    search_queries = build_platform_search_queries(platform_keyword, product, queries)[
        :mq_limit
    ]
    if not search_queries:
        return []

    cap = max(1, result_cap if result_cap is not None else settings.max_results_per_platform)
    out: list[CandidateLink] = []
    seen: set[str] = set()
    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()

    for q in search_queries:
        if len(out) >= cap:
            break
        full_q = f"site:{site_host} {q}"[:400]
        try:
            time.sleep(DDG_DELAY_SECONDS)
            with DDGS() as ddgs:
                raw = ddgs.text(full_q, max_results=min(20, cap * 3))
                results = list(raw) if raw is not None else []
        except Exception as e:
            logger.warning("DDG search failed (%s): %s", full_q[:80], e)
            continue

        for r in results:
            if len(out) >= cap:
                break
            if not isinstance(r, dict):
                continue
            url = str(r.get("href") or r.get("url") or "").strip()
            if not url or url in seen:
                continue
            if not url_matches_site_host(url, site_host):
                continue
            seen.add(url)
            title = str(r.get("title") or "")
            body = str(r.get("body") or "")[:500]
            out.append(
                CandidateLink(
                    media=media_label,
                    brand=brand,
                    url=url,
                    sku=sku,
                    product_name=pname,
                    title=title,
                    snippet=body,
                    source_query=full_q,
                )
            )

    return out


def search_tiktok_ddg(
    settings: Settings,
    product: ProductInput,
    queries: list[str],
    *,
    max_queries: int | None = None,
    result_cap: int | None = None,
) -> list[CandidateLink]:
    return search_site_ddg_sync(
        settings,
        product,
        queries,
        "tiktok.com",
        "Tiktok",
        "Tiktok",
        max_queries=max_queries,
        result_cap=result_cap,
    )


def search_facebook_ddg(
    settings: Settings,
    product: ProductInput,
    queries: list[str],
    *,
    max_queries: int | None = None,
    result_cap: int | None = None,
) -> list[CandidateLink]:
    return search_site_ddg_sync(
        settings,
        product,
        queries,
        "facebook.com",
        "Facebook",
        "Facebook",
        max_queries=max_queries,
        result_cap=result_cap,
    )


def search_instagram_ddg(
    settings: Settings,
    product: ProductInput,
    queries: list[str],
    *,
    max_queries: int | None = None,
    result_cap: int | None = None,
) -> list[CandidateLink]:
    return search_site_ddg_sync(
        settings,
        product,
        queries,
        "instagram.com",
        "Instagram",
        "Instagram",
        max_queries=max_queries,
        result_cap=result_cap,
    )
