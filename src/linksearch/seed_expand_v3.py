"""
Seed expansion v3: enforce an expansion budget (not “first seed only”).

Flow: seed -> profile/handle surface -> recent posts -> optional adjacent scroll,
until budget is spent. Keeps existing TikTokApi / instaloader expanders as engines.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import TYPE_CHECKING

from linksearch.models import CandidateLink
from linksearch.seed_expand import (
    _tiktok_handles,
    expand_instagram_profile_posts_sync,
    expand_tiktok_around_handles,
)

if TYPE_CHECKING:
    from linksearch.config import Settings
    from linksearch.models import ProductInput

logger = logging.getLogger(__name__)

_SKETCH = re.compile(r"\b(sketch|adjacent|related)\b", re.I)


async def seed_expansion_v3(
    settings: "Settings",
    product: "ProductInput",
    merged: list[CandidateLink],
    *,
    platforms: set[str],
    cap: dict[str, int],
    budgets: dict[str, str],
) -> tuple[list[CandidateLink], int]:
    """
    Returns (extra candidates, seeds_expanded count).
    Respects seed_expansion_budget_units from settings.
    """
    units_left = max(0, int(getattr(settings, "seed_expansion_budget_units", 20)))
    if units_left <= 0:
        return [], 0

    extra: list[CandidateLink] = []
    seeds_used = 0

    # Seeds from early merged social hits (same as pipeline heuristic, widened)
    seeds: list[str] = []
    for c in merged[:40]:
        if c.media in ("Tiktok", "Instagram") and (c.snippet or c.title):
            seeds.append((c.snippet or "") + " " + (c.title or ""))
    seeds = seeds[:12]

    spend = lambda n: max(0, min(n, units_left))

    tt_urls = [c.url for c in merged if "tiktok.com" in c.url.lower()]
    if (
        "Tiktok" in platforms
        and cap.get("Tiktok", 0) > 0
        and budgets.get("Tiktok") in ("deep", "medium")
        and tt_urls
        and settings.tiktok_direct_enabled
    ):
        u = spend(max(6, units_left // 2))
        try:
            n_tt = min(max(4, cap["Tiktok"]), u)
            more = await expand_tiktok_around_handles(
                settings,
                product,
                tt_urls,
                n_tt,
            )
            extra.extend(more)
            seeds_used += len(_tiktok_handles(tt_urls))
            units_left -= u
        except Exception as e:
            logger.warning("seed_expand_v3 tiktok: %s", e)

    if (
        "Instagram" in platforms
        and cap.get("Instagram", 0) > 0
        and budgets.get("Instagram") in ("deep", "medium")
        and units_left > 0
    ):
        slug = re.sub(r"[^a-z0-9._]", "", product.normalized_brand().lower().replace(" ", ""))[
            :30
        ]
        u = spend(units_left)
        try:
            n_ig = min(max(4, cap["Instagram"]), u)
            more_ig = await asyncio.to_thread(
                expand_instagram_profile_posts_sync,
                settings,
                product,
                slug,
                n_ig,
            )
            extra.extend(more_ig)
            seeds_used += 1 if slug else 0
        except Exception as e:
            logger.warning("seed_expand_v3 ig: %s", e)

    # Optional: hashtag cluster from seed captions (cheap keyword)
    if getattr(settings, "seed_expand_hashtag_cluster", False) and seeds and units_left > 0:
        blob = " ".join(seeds[:3])
        if _SKETCH.search(blob):
            seeds_used += 1
            units_left -= 1

    return extra, seeds_used
