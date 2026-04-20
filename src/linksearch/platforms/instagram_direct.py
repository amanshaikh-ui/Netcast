from __future__ import annotations

import logging
import re
from itertools import islice
from typing import TYPE_CHECKING

from linksearch.models import CandidateLink, ProductInput

if TYPE_CHECKING:
    from linksearch.config import Settings
    from linksearch.aliases import ProductAliases

logger = logging.getLogger(__name__)


def _hashtag_from_product(product: ProductInput, queries: list[str]) -> str:
    """Build a simple hashtag token (letters/digits only)."""
    raw = f"{product.normalized_brand()}{product.sku.strip()}"
    tag = re.sub(r"[^a-zA-Z0-9]", "", raw).lower()[:30]
    if len(tag) >= 3:
        return tag
    alt = re.sub(r"[^a-zA-Z0-9]", "", product.sku.strip()).lower()[:30]
    if len(alt) >= 2:
        return alt
    if queries:
        return re.sub(r"[^a-zA-Z0-9]", "", queries[0]).lower()[:30]
    return "product"


def _hashtag_slugs_for_instagram(
    product: ProductInput,
    queries: list[str],
    aliases: "ProductAliases | None" = None,
) -> list[str]:
    from linksearch.aliases import build_product_aliases

    pa = aliases or build_product_aliases(product)
    slugs: list[str] = []
    for h in pa.hashtags:
        s = h.lstrip("#").strip()
        if len(s) >= 2:
            slugs.append(s[:30])
    for q in queries[:10]:
        s = re.sub(r"[^a-zA-Z0-9]", "", q).lower()[:30]
        if len(s) >= 3:
            slugs.append(s)
    primary = _hashtag_from_product(product, queries)
    slugs.insert(0, primary)
    seen: set[str] = set()
    out: list[str] = []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out[:8]


def search_instagram_direct_sync(
    settings: Settings,
    product: ProductInput,
    queries: list[str],
    aliases: "ProductAliases | None" = None,
) -> list[CandidateLink]:
    """
    Hashtag-first Instagram discovery (native). Tries several tags from aliases + SKU slug.
    Set INSTAGRAM_DIRECT_ENABLED=true; session helps reliability.
    """
    if not settings.instagram_direct_enabled:
        return []
    try:
        import instaloader
    except ImportError:
        logger.warning("instaloader not installed; skip direct Instagram (pip install -e '.[direct]').")
        return []

    cap = max(1, settings.max_results_per_platform * 2)
    tags = _hashtag_slugs_for_instagram(product, queries, aliases)

    L = instaloader.Instaloader(quiet=True, max_connection_attempts=1)
    session = settings.instagram_session_file.strip()
    if session:
        try:
            L.load_session_from_file(session)
        except Exception as e:
            logger.warning("Instagram session file not loaded (%s): %s", session, e)

    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    out: list[CandidateLink] = []
    seen: set[str] = set()

    for tag in tags:
        if len(out) >= cap:
            break
        try:
            hashtag = instaloader.Hashtag.from_name(L.context, tag)
            for post in islice(hashtag.get_posts(), cap * 2):
                if len(out) >= cap:
                    break
                url = f"https://www.instagram.com/p/{post.shortcode}/"
                if url in seen:
                    continue
                seen.add(url)
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
                        source_query=f"#{tag}",
                    )
                )
        except Exception as e:
            logger.warning("Direct Instagram hashtag search failed (#%s): %s", tag, e)
            continue

    return out[: settings.max_results_per_platform * 2]
