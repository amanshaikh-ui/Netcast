"""
Seed-and-expand: after initial hits, pull more TikTok/IG content (same author / profile).
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING

from linksearch.models import CandidateLink, ProductInput

if TYPE_CHECKING:
    from linksearch.config import Settings

logger = logging.getLogger(__name__)

_HANDLE_TT = re.compile(r"tiktok\.com/@([^/?#]+)", re.I)


def _tiktok_handles(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        m = _HANDLE_TT.search(u)
        if m:
            h = m.group(1).lower()
            if h not in seen:
                seen.add(h)
                out.append(h)
    return out[:3]


async def expand_tiktok_around_handles(
    settings: Settings,
    product: ProductInput,
    seed_urls: list[str],
    result_cap: int,
) -> list[CandidateLink]:
    if result_cap <= 0 or not settings.tiktok_direct_enabled:
        return []
    try:
        from TikTokApi import TikTokApi
    except ImportError:
        return []

    handles = _tiktok_handles(seed_urls)
    if not handles:
        return []

    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    out: list[CandidateLink] = []
    seen: set[str] = set()

    ms = (settings.tiktok_ms_token or os.environ.get("TIKTOK_MS_TOKEN") or "").strip() or None
    browser = (settings.tiktok_browser or os.environ.get("TIKTOK_BROWSER") or "chromium").strip()

    try:
        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[ms] if ms else None,
                num_sessions=1,
                sleep_after=2,
                browser=browser,
            )
            for handle in handles:
                if len(out) >= result_cap:
                    break
                q_text = f"@{handle} {brand}"[:200]
                try:
                    async for video in api.search.search_type(
                        q_text, "item", count=min(12, result_cap + 5)
                    ):
                        if len(out) >= result_cap:
                            break
                        url = getattr(video, "url", None) or ""
                        if not url and getattr(video, "as_dict", None):
                            url = str(video.as_dict.get("share_url") or "") or ""
                        if not url and getattr(video, "id", None):
                            url = f"https://www.tiktok.com/video/{video.id}"
                        if not url or url in seen:
                            continue
                        title = ""
                        if getattr(video, "as_dict", None):
                            title = str(video.as_dict.get("desc") or "")[:300]
                        seen.add(url)
                        out.append(
                            CandidateLink(
                                media="Tiktok",
                                brand=brand,
                                url=url,
                                sku=sku,
                                product_name=pname,
                                title=title,
                                snippet=title,
                                source_query=f"seed_expand:{q_text}",
                            )
                        )
                except Exception as e:
                    logger.debug("TikTok seed expand %s: %s", handle, e)
    except Exception as e:
        logger.warning("Seed TikTok expand failed: %s", e)

    return out[:result_cap]


def expand_instagram_profile_posts_sync(
    settings: Settings,
    product: ProductInput,
    brand_slug: str,
    result_cap: int,
) -> list[CandidateLink]:
    if result_cap <= 0 or not settings.instagram_direct_enabled:
        return []
    try:
        import instaloader
    except ImportError:
        return []

    slug = re.sub(r"[^a-zA-Z0-9._]", "", brand_slug).lower().strip(".")
    if len(slug) < 2:
        return []

    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    out: list[CandidateLink] = []

    L = instaloader.Instaloader(quiet=True, max_connection_attempts=1)
    session = settings.instagram_session_file.strip()
    if session:
        try:
            L.load_session_from_file(session)
        except Exception:
            pass

    try:
        prof = instaloader.Profile.from_username(L.context, slug)
    except Exception as e:
        logger.debug("IG profile %s: %s", slug, e)
        return []

    try:
        for i, post in enumerate(prof.get_posts()):
            if i >= result_cap:
                break
            url = f"https://www.instagram.com/p/{post.shortcode}/"
            cap_txt = post.caption or ""
            out.append(
                CandidateLink(
                    media="Instagram",
                    brand=brand,
                    url=url,
                    sku=sku,
                    product_name=pname,
                    title=cap_txt[:200],
                    snippet=str(cap_txt)[:500],
                    source_query=f"seed_expand:profile:{slug}",
                )
            )
    except Exception as e:
        logger.warning("IG profile expand %s: %s", slug, e)

    return out
