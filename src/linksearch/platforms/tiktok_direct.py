from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

from linksearch.models import CandidateLink, ProductInput

if TYPE_CHECKING:
    from linksearch.config import Settings
    from linksearch.aliases import ProductAliases

logger = logging.getLogger(__name__)


def _query_strings_for_tiktok(
    product: ProductInput, queries: list[str], aliases: "ProductAliases | None" = None,
) -> list[str]:
    from linksearch.aliases import build_product_aliases

    pa = aliases or build_product_aliases(product)
    ordered: list[str] = []
    for block in (pa.pass1_queries, pa.pass2_queries, queries):
        for q in block:
            t = (q or "").strip()[:200]
            if t:
                ordered.append(t)
    seen: set[str] = set()
    out: list[str] = []
    for q in ordered:
        k = q.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(q)
    return out[:14]


async def search_tiktok_direct(
    settings: Settings,
    product: ProductInput,
    queries: list[str],
    aliases: "ProductAliases | None" = None,
    *,
    query_override: list[str] | None = None,
) -> list[CandidateLink]:
    """
    Direct TikTok video search via TikTokApi + Playwright (optional extra: pip install -e ".[direct]").
    Set TIKTOK_DIRECT_ENABLED=true and install playwright (chromium).
    """
    if not settings.tiktok_direct_enabled:
        return []
    try:
        from TikTokApi import TikTokApi
    except ImportError:
        logger.warning("TikTokApi not installed; skip direct TikTok search (pip install -e '.[direct]').")
        return []

    cap = max(1, settings.max_results_per_platform * 3)
    if query_override is not None:
        seen: set[str] = set()
        queue = []
        for q in query_override:
            t = (q or "").strip()[:200]
            if t and t.lower() not in seen:
                seen.add(t.lower())
                queue.append(t)
    else:
        queue = _query_strings_for_tiktok(product, queries, aliases)
    if not queue:
        return []

    ms = (settings.tiktok_ms_token or os.environ.get("TIKTOK_MS_TOKEN") or "").strip() or None
    browser = (settings.tiktok_browser or os.environ.get("TIKTOK_BROWSER") or "chromium").strip()

    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    out: list[CandidateLink] = []
    seen: set[str] = set()

    try:
        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[ms] if ms else None,
                num_sessions=1,
                sleep_after=3,
                browser=browser,
            )
            for q_text in queue:
                if len(out) >= cap:
                    break
                remaining = cap - len(out)
                if remaining <= 0:
                    break
                async for video in api.search.search_type(
                    q_text, "item", count=min(remaining, settings.max_results_per_platform + 5)
                ):
                    url = getattr(video, "url", None) or ""
                    if not url and getattr(video, "as_dict", None):
                        url = (
                            str(video.as_dict.get("share_url") or "")
                            or str(
                                (video.as_dict.get("video", {}) or {}).get("share_url") or ""
                            )
                        )
                    if not url and getattr(video, "id", None):
                        url = f"https://www.tiktok.com/video/{video.id}"
                    if not url or url in seen:
                        continue
                    title = ""
                    desc = ""
                    if getattr(video, "as_dict", None):
                        title = str(video.as_dict.get("desc") or "")[:300]
                        desc = title
                    seen.add(url)
                    out.append(
                        CandidateLink(
                            media="Tiktok",
                            brand=brand,
                            url=url,
                            sku=sku,
                            product_name=pname,
                            title=title,
                            snippet=desc,
                            source_query=q_text,
                        )
                    )
                    if len(out) >= cap:
                        break
    except Exception as e:
        logger.warning("Direct TikTok search failed: %s", e)

    return out[: settings.max_results_per_platform * 2]
