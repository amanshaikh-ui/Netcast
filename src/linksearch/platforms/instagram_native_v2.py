"""
Instagram adapter v2: profile-first (multiple username guesses), /p/ and /reel/ links,
optional session; hashtag discovery only if profile path yields nothing, or as boosted retries.
"""

from __future__ import annotations

import logging
import re
from itertools import islice
from typing import TYPE_CHECKING

from linksearch.models import CandidateLink, ProductInput
from linksearch.observability import AdapterObservation
from linksearch.platforms.instagram_direct import (
    _hashtag_slugs_for_instagram,
    search_instagram_direct_sync,
)

if TYPE_CHECKING:
    from linksearch.aliases import ProductAliases
    from linksearch.config import Settings

logger = logging.getLogger(__name__)


def _username_guesses(pa: "ProductAliases", product: ProductInput) -> list[str]:
    brand = product.normalized_brand()
    guesses: list[str] = []
    slug = re.sub(r"[^a-zA-Z0-9._]", "", brand.replace(" ", "").lower())[:30]
    if len(slug) >= 2:
        guesses.append(slug)
    compact = pa.compact_sku_slug.lower()[:30] if pa.compact_sku_slug else ""
    if len(compact) >= 2 and compact not in guesses:
        guesses.append(compact)
    fused = re.sub(r"[^a-zA-Z0-9._]", "", f"{brand}{product.sku.strip()}".lower())[:30]
    if len(fused) >= 3 and fused not in guesses:
        guesses.append(fused)
    first = product.product_name.strip().split()[:1]
    if first:
        mix = re.sub(r"[^a-zA-Z0-9._]", "", (brand + first[0]).lower())[:30]
        if len(mix) >= 4 and mix not in guesses:
            guesses.append(mix)
    seen: set[str] = set()
    out: list[str] = []
    for g in guesses:
        g2 = g.strip(".")
        if len(g2) < 2:
            continue
        if g2 not in seen:
            seen.add(g2)
            out.append(g2)
    return out[:8]


def _post_url_instagram(post) -> str:
    sc = getattr(post, "shortcode", "") or ""
    if not sc:
        u = getattr(post, "url", None)
        return str(u) if u else ""
    if getattr(post, "is_video", False):
        return f"https://www.instagram.com/reel/{sc}/"
    return f"https://www.instagram.com/p/{sc}/"


def _profile_candidates(
    settings: "Settings",
    product: ProductInput,
    pa: "ProductAliases",
    L,
    cap: int,
) -> tuple[list[CandidateLink], int]:
    """Single pass over username guesses."""
    import instaloader as il

    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    out: list[CandidateLink] = []
    seen: set[str] = set()
    rejected = 0
    guesses = _username_guesses(pa, product)

    for uname in guesses:
        if len(out) >= cap:
            break
        try:
            prof = il.Profile.from_username(L.context, uname)
        except Exception as e:
            rejected += 1
            logger.debug("IG guess %s: %s", uname, e)
            continue
        try:
            for i, post in enumerate(prof.get_posts()):
                if i >= cap * 2 or len(out) >= cap:
                    break
                url = _post_url_instagram(post)
                if not url or url in seen:
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
                        source_query=f"ig_v2:profile:{uname}",
                    )
                )
        except Exception as e:
            logger.warning("IG profile posts %s: %s", uname, e)
            rejected += 1
    return out, rejected


def _hashtag_candidates(
    settings: "Settings",
    product: ProductInput,
    queries: list[str],
    pa: "ProductAliases",
    L,
    cap: int,
    extra_tokens: list[str],
) -> tuple[list[CandidateLink], int]:
    import instaloader as il

    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    out: list[CandidateLink] = []
    seen: set[str] = set()
    rejected = 0

    tags = _hashtag_slugs_for_instagram(product, queries, pa)
    for h in extra_tokens:
        token = re.sub(r"[^a-zA-Z0-9]", "", h.lower())[:30]
        if len(token) >= 3 and token not in tags:
            tags.insert(0, token)

    for tag in tags:
        if len(out) >= cap:
            break
        try:
            hashtag = il.Hashtag.from_name(L.context, tag)
            for post in islice(hashtag.get_posts(), cap * 2):
                if len(out) >= cap:
                    break
                url = _post_url_instagram(post)
                if not url or url in seen:
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
                        source_query=f"ig_v2:hashtag:#{tag}",
                    )
                )
        except Exception as e:
            logger.warning("IG hashtag #%s: %s", tag, e)
            rejected += 1

    return out, rejected


def search_instagram_native_v2_sync(
    settings: "Settings",
    product: ProductInput,
    queries: list[str],
    pa: "ProductAliases",
    hint_queries: list[str],
    base_obs: AdapterObservation | None = None,
    *,
    try_profile: bool = True,
) -> tuple[list[CandidateLink], AdapterObservation]:
    """
    try_profile: first retry round runs profile + hashtag; later rounds only hashtag with hints.
    """
    obs = base_obs or AdapterObservation(adapter_name="instagram_native_v2")
    obs.query_used = (hint_queries[0] if hint_queries else "")[:400]

    if not settings.instagram_direct_enabled:
        obs.rejection_reason = "instagram_direct_disabled"
        return [], obs

    try:
        import instaloader
    except ImportError:
        obs.rejection_reason = "instaloader_not_installed"
        return [], obs

    cap = max(1, settings.max_results_per_platform * 2)
    L = instaloader.Instaloader(quiet=True, max_connection_attempts=1)
    session = settings.instagram_session_file.strip()
    if session:
        try:
            L.load_session_from_file(session)
        except Exception as e:
            logger.debug("IG session: %s", e)

    merged_extra = dict(obs.extra or {})
    merged_extra["username_guesses"] = _username_guesses(pa, product)[:8]
    merged_extra["hint"] = hint_queries[:6]
    merged_extra["try_profile"] = try_profile
    obs.extra = merged_extra

    rej_p = 0
    if try_profile:
        prof_out, rej_p = _profile_candidates(settings, product, pa, L, cap)
        if prof_out:
            obs.candidates_extracted = len(prof_out)
            obs.candidates_rejected = rej_p
            obs.visible_results_count = len(prof_out)
            return prof_out[: settings.max_results_per_platform * 2], obs

    extra_tokens: list[str] = []
    for q in hint_queries:
        t = re.sub(r"[^\w\s]", "", q)
        for part in t.split():
            if len(part) >= 3:
                extra_tokens.append(part)
    hc, rej_h = _hashtag_candidates(settings, product, queries, pa, L, cap, extra_tokens)
    obs.candidates_rejected = rej_p + rej_h
    obs.candidates_extracted = len(hc)
    obs.visible_results_count = len(hc)
    if not hc:
        obs.rejection_reason = "profile_and_hashtag_empty"
    return hc[: settings.max_results_per_platform * 2], obs


def search_instagram_direct_or_v2_sync(
    settings: "Settings",
    product: ProductInput,
    queries: list[str],
    pa: "ProductAliases",
) -> list[CandidateLink]:
    """Legacy single-shot: v2 one-shot with empty hints, or v1 direct."""
    if getattr(settings, "instagram_profile_first_v2", True):
        cands, _ = search_instagram_native_v2_sync(
            settings,
            product,
            queries,
            pa,
            [],
            AdapterObservation(adapter_name="instagram_native_v2"),
        )
        return cands
    return search_instagram_direct_sync(settings, product, queries, pa)
