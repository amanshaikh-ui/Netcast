from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx

from linksearch.config import Settings
from linksearch.models import CandidateLink, ProductInput

logger = logging.getLogger(__name__)

CSE_URL = "https://www.googleapis.com/customsearch/v1"

SITE_TIKTOK = "tiktok.com"
SITE_FACEBOOK = "facebook.com"
SITE_INSTAGRAM = "instagram.com"

# Cap CSE calls per product per platform (each call uses API quota).
MAX_CSE_QUERIES_PER_SITE = 4


def _sanitize_sku_for_quote(sku: str) -> str:
    return sku.strip().replace('"', "")


def _dedupe_search_queries(candidates: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for c in candidates:
        t = c.strip()
        if not t:
            continue
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t[:350])
    return out


def url_matches_site_host(url: str, site_host: str) -> bool:
    """Hostname is site_host or a subdomain of it (e.g. www.tiktok.com)."""
    try:
        h = (urlparse(url).hostname or "").lower()
        s = site_host.lower()
        return h == s or h.endswith("." + s)
    except Exception:
        return False


def build_platform_search_queries(
    platform_keyword: str,
    product: ProductInput,
    queries: list[str],
) -> list[str]:
    """Natural-language queries like Tiktok Ryobi \"R4331\" (no site:)."""
    brand = product.normalized_brand()
    sku = _sanitize_sku_for_quote(product.sku)
    kw = platform_keyword.strip()
    candidates: list[str] = []

    if sku:
        if brand:
            candidates.append(f'{kw} {brand} "{sku}"'[:350])
        else:
            candidates.append(f'{kw} "{sku}"'[:350])

    for q in queries[:3]:
        t = q.strip()
        if not t:
            continue
        candidates.append(f"{kw} {t}"[:350])

    candidates.append(f"{kw} {product.primary_query()}"[:350])

    return _dedupe_search_queries(candidates)[:MAX_CSE_QUERIES_PER_SITE]


async def _cse_query(
    client: httpx.AsyncClient,
    settings: Settings,
    search_q: str,
    num: int,
) -> list[dict]:
    params = {
        "key": settings.google_cse_api_key,
        "cx": settings.google_cse_id,
        "q": search_q,
        "num": min(10, max(1, num)),
    }
    r = await client.get(CSE_URL, params=params)
    r.raise_for_status()
    data = r.json()
    return list((data.get("items") or []))


async def search_site(
    client: httpx.AsyncClient,
    settings: Settings,
    product: ProductInput,
    queries: list[str],
    site_host: str,
    platform_keyword: str,
    media_label: str,
) -> list[CandidateLink]:
    if not settings.cse_enabled():
        return []

    search_queries = build_platform_search_queries(platform_keyword, product, queries)
    cap = settings.max_results_per_platform
    out: list[CandidateLink] = []
    seen: set[str] = set()

    for search_q in search_queries:
        if len(out) >= cap:
            break
        try:
            items = await _cse_query(client, settings, search_q, 10)
        except Exception as e:
            logger.warning("CSE query failed (%s): %s", search_q[:80], e)
            continue

        for it in items:
            if len(out) >= cap:
                break
            url = it.get("link") or ""
            title = it.get("title") or ""
            snippet = it.get("snippet") or ""
            if not url or url in seen:
                continue
            if not url_matches_site_host(url, site_host):
                continue
            seen.add(url)
            out.append(
                CandidateLink(
                    media=media_label,
                    brand=product.normalized_brand(),
                    url=url,
                    sku=product.sku.strip(),
                    product_name=product.product_name.strip(),
                    title=title,
                    snippet=snippet,
                    source_query=search_q,
                )
            )

    return out


async def search_tiktok_cse(
    client: httpx.AsyncClient, settings: Settings, product: ProductInput, queries: list[str]
) -> list[CandidateLink]:
    return await search_site(
        client, settings, product, queries, SITE_TIKTOK, "Tiktok", "Tiktok"
    )


async def search_facebook_cse(
    client: httpx.AsyncClient, settings: Settings, product: ProductInput, queries: list[str]
) -> list[CandidateLink]:
    return await search_site(
        client, settings, product, queries, SITE_FACEBOOK, "Facebook", "Facebook"
    )


async def search_instagram_cse(
    client: httpx.AsyncClient, settings: Settings, product: ProductInput, queries: list[str]
) -> list[CandidateLink]:
    return await search_site(
        client, settings, product, queries, SITE_INSTAGRAM, "Instagram", "Instagram"
    )
