"""Query packs and zero-yield retries for native TikTok/Instagram layers."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from linksearch.observability import AdapterObservation
from linksearch.runtime_geo import get_runtime_region

if TYPE_CHECKING:
    from linksearch.aliases import ProductAliases
    from linksearch.config import Settings
    from linksearch.models import CandidateLink, ProductInput

logger = logging.getLogger(__name__)


def build_tiktok_retry_packs(
    pa: "ProductAliases", product_queries: list[str]
) -> list[tuple[str, list[str]]]:
    """Ordered packs: primary -> alternate -> family language -> hashtag-heavy."""
    hashtag_heavy: list[str] = []
    for h in pa.hashtags[:6]:
        token = h.lstrip("#").strip()
        if len(token) >= 2:
            hashtag_heavy.append(f"{token} TikTok review")
            hashtag_heavy.append(f"#{token} unboxing")
    packs: list[tuple[str, list[str]]] = [
        ("primary", list(pa.pass1_queries[:8])),
        ("alternate", list(pa.pass2_queries[:10])),
        ("family_lang", list(pa.family_queries[:8])),
        ("hashtag_heavy", hashtag_heavy[:10] or [f"{pa.brand} {pa.sku} review"[:200]]),
    ]
    # Drop empty packs
    out: list[tuple[str, list[str]]] = []
    for label, qs in packs:
        clean = [q.strip() for q in qs if q and q.strip()]
        if clean:
            out.append((label, clean))
    return out


def build_instagram_retry_packs(
    pa: "ProductAliases", product_queries: list[str]
) -> list[tuple[str, list[str]]]:
    """Profile resolution uses multiple guesses internally; packs vary hashtag emphasis."""
    hq: list[str] = []
    for h in pa.hashtags[:8]:
        token = h.lstrip("#").strip()
        if len(token) >= 2:
            hq.append(token)
    packs: list[tuple[str, list[str]]] = [
        ("primary", list(pa.pass1_queries[:6])),
        ("alternate", list(pa.pass2_queries[:8])),
        ("family_lang", list(pa.family_queries[:6])),
        ("hashtag_heavy", hq[:8] or [pa.compact_sku_slug or pa.brand]),
    ]
    out: list[tuple[str, list[str]]] = []
    for label, qs in packs:
        clean = [str(q).strip() for q in qs if q and str(q).strip()]
        if clean:
            out.append((label, clean))
    return out


async def run_tiktok_native_with_retries(
    settings: "Settings",
    product: "ProductInput",
    queries: list[str],
    pa: "ProductAliases",
) -> tuple[list["CandidateLink"], list[dict[str, object]]]:
    """Native TikTok with pack retries; stops at first non-empty result (recall-first)."""
    from linksearch.platforms.tiktok_playwright_v3 import search_tiktok_playwright_v3_sync
    from linksearch.platforms.tiktok_direct import search_tiktok_direct

    region = get_runtime_region()
    packs = build_tiktok_retry_packs(pa, queries)
    observations: list[dict[str, object]] = []

    if getattr(settings, "tiktok_playwright_v3", False):
        all_cands: list = []
        for retry_idx, (label, pack) in enumerate(packs):
            q_used = pack[0] if pack else ""
            obs = AdapterObservation(
                query_used=q_used[:400],
                adapter_name="tiktok_playwright_v3",
                runtime_region=region,
                retry_count=retry_idx,
                extra={"pack": label, "pack_size": len(pack)},
            )
            try:
                cands, o2 = await asyncio.to_thread(
                    search_tiktok_playwright_v3_sync,
                    settings,
                    product,
                    pack,
                    obs,
                )
            except Exception as e:
                logger.warning("TikTok playwright v3: %s", e)
                obs.rejection_reason = str(e)[:300]
                observations.append(obs.to_dict())
                continue
            obs = o2
            observations.append(obs.to_dict())
            if cands:
                all_cands.extend(cands)
                break
        return all_cands, observations

    # TikTokApi path: one pack at a time via query_override inside search_tiktok_direct
    all_cands = []
    for retry_idx, (label, pack) in enumerate(packs):
        obs = AdapterObservation(
            query_used=(pack[0] if pack else "")[:400],
            adapter_name="tiktok_direct",
            runtime_region=region,
            retry_count=retry_idx,
            extra={"pack": label},
        )
        try:
            cands = await search_tiktok_direct(
                settings, product, queries, pa, query_override=pack
            )
        except Exception as e:
            obs.rejection_reason = str(e)[:300]
            observations.append(obs.to_dict())
            continue
        obs.candidates_extracted = len(cands)
        observations.append(obs.to_dict())
        if cands:
            all_cands = cands
            break
    return all_cands, observations


async def run_instagram_native_with_retries(
    settings: "Settings",
    product: "ProductInput",
    queries: list[str],
    pa: "ProductAliases",
) -> tuple[list["CandidateLink"], list[dict[str, object]]]:
    from linksearch.platforms.instagram_native_v2 import search_instagram_native_v2_sync

    region = get_runtime_region()
    packs = build_instagram_retry_packs(pa, queries)
    observations: list[dict[str, object]] = []

    for retry_idx, (label, hint_queries) in enumerate(packs):
        obs = AdapterObservation(
            query_used=(hint_queries[0] if hint_queries else "")[:400],
            adapter_name="instagram_native_v2",
            runtime_region=region,
            retry_count=retry_idx,
            extra={"pack": label},
        )
        try:

            def _ig_one() -> tuple[list, AdapterObservation]:
                return search_instagram_native_v2_sync(
                    settings,
                    product,
                    queries,
                    pa,
                    hint_queries,
                    obs,
                    try_profile=(retry_idx == 0),
                )

            cands, ob = await asyncio.to_thread(_ig_one)
        except Exception as e:
            obs.rejection_reason = str(e)[:300]
            observations.append(obs.to_dict())
            continue
        observations.append(ob.to_dict())
        if cands:
            return cands, observations

    empty = AdapterObservation(
        adapter_name="instagram_native_v2",
        runtime_region=region,
        rejection_reason="all_retry_packs_empty",
        retry_count=len(packs),
    )
    observations.append(empty.to_dict())
    return [], observations
