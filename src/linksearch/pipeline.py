from __future__ import annotations

import asyncio
import logging
import re
from collections import defaultdict

import httpx

from linksearch.adapter_retry import (
    run_instagram_native_with_retries,
    run_tiktok_native_with_retries,
)
from linksearch.aliases import build_product_aliases, expand_queries_with_seed
from linksearch.brave_social import search_site_brave
from linksearch.canonical_url import canonicalize_social_url
from linksearch.classification import build_classification_block
from linksearch.config import Settings, load_settings
from linksearch.evidence_fetch import enrich_candidates_parallel
from linksearch.explain_results import build_explanation
from linksearch.groq_helper import build_search_queries, groq_rerank_candidates
from linksearch.models import CandidateLink, PipelineResult, ProductInput
from linksearch.orchestration import budget_to_ddg_queries, build_crawl_plan, effective_cap
from linksearch.platform_filter import normalize_platform_list, wants_platform
from linksearch.platforms.ddg_social import (
    search_facebook_ddg,
    search_instagram_ddg,
    search_tiktok_ddg,
)
from linksearch.platforms.google_cse import (
    search_facebook_cse,
    search_instagram_cse,
    search_tiktok_cse,
)
from linksearch.platforms.instagram_direct import search_instagram_direct_sync
from linksearch.platforms.reddit import search_reddit
from linksearch.runtime_geo import get_runtime_region, india_geo_warning_message
from linksearch.seed_expand_v3 import seed_expansion_v3
from linksearch.platforms.youtube_merged import search_youtube_merged
from linksearch.platforms.youtube_shorts_ytdlp import search_youtube_shorts_ytdlp_sync
from linksearch.scoring import apply_heuristic_and_sort
from linksearch.seed_expand import (
    expand_instagram_profile_posts_sync,
    expand_tiktok_around_handles,
)

logger = logging.getLogger(__name__)

OBJECTIVE = "maximize_realistic_public_coverage"


def _st(settings: Settings, cap: int) -> Settings:
    return settings.model_copy(update={"max_results_per_platform": max(1, cap)})


def _requested_platform_ids(platforms: list[str] | None) -> set[str]:
    if platforms is None:
        return {
            "Youtube",
            "YoutubeShorts",
            "Reddit",
            "Tiktok",
            "Facebook",
            "Instagram",
        }
    return set(platforms)


async def discover_for_product(
    client: httpx.AsyncClient,
    settings: Settings,
    product: ProductInput,
    use_groq_rerank: bool,
    platforms: list[str] | None = None,
) -> tuple[list[CandidateLink], list[str], dict[str, object]]:
    warnings: list[str] = []
    pa = build_product_aliases(product)
    queries = build_search_queries(settings, product, pa)
    platforms = normalize_platform_list(platforms)
    archetype, coverage, budgets = build_crawl_plan(product)
    requested = _requested_platform_ids(platforms)

    discovery_events: list[dict[str, object]] = []
    adapter_observations: list[dict[str, object]] = []

    geo_warn = india_geo_warning_message()
    if geo_warn:
        warnings.append(geo_warn)

    def log_event(
        source: str,
        platform: str,
        *,
        pass_no: int = 1,
        count: int = 0,
        extra: str = "",
    ) -> None:
        discovery_events.append(
            {
                "source": source,
                "platform": platform,
                "pass": pass_no,
                "candidates_added": count,
                "budget": budgets.get(platform, "medium"),
                "note": extra,
            }
        )

    if platforms is not None and len(platforms) == 0:
        return [], [f"{product.sku}: No platforms selected."], {}

    cap: dict[str, int] = {
        k: effective_cap(settings.max_results_per_platform, b) for k, b in budgets.items()
    }

    async def instagram_native_async(st: Settings) -> list[CandidateLink]:
        if getattr(st, "instagram_profile_first_v2", True):
            cands, obs = await run_instagram_native_with_retries(
                st, product, queries, pa
            )
            adapter_observations.extend(obs)
            return cands
        return await asyncio.to_thread(
            search_instagram_direct_sync, st, product, queries, pa
        )

    async def tiktok_ddg_async() -> list[CandidateLink]:
        b = budgets["Tiktok"]
        mq = budget_to_ddg_queries(b)
        if mq <= 0 or cap["Tiktok"] <= 0:
            return []
        rc = cap["Tiktok"]
        return await asyncio.to_thread(
            search_tiktok_ddg,
            settings,
            product,
            queries,
            max_queries=mq,
            result_cap=rc,
        )

    async def facebook_ddg_async() -> list[CandidateLink]:
        b = budgets["Facebook"]
        mq = budget_to_ddg_queries(b)
        if mq <= 0 or cap["Facebook"] <= 0:
            return []
        return await asyncio.to_thread(
            search_facebook_ddg,
            settings,
            product,
            queries,
            max_queries=mq,
            result_cap=cap["Facebook"],
        )

    async def instagram_ddg_async() -> list[CandidateLink]:
        b = budgets["Instagram"]
        mq = budget_to_ddg_queries(b)
        if mq <= 0 or cap["Instagram"] <= 0:
            return []
        return await asyncio.to_thread(
            search_instagram_ddg,
            settings,
            product,
            queries,
            max_queries=mq,
            result_cap=cap["Instagram"],
        )

    specs: list[tuple[str, object]] = []

    if wants_platform(platforms, "Youtube") and cap["Youtube"] > 0:
        st = _st(settings, cap["Youtube"])
        specs.append(
            ("youtube", search_youtube_merged(client, st, product, queries))
        )
    if wants_platform(platforms, "YoutubeShorts") and cap.get("YoutubeShorts", 0) > 0:
        st = _st(settings, cap["YoutubeShorts"])
        specs.append(
            (
                "youtube_shorts_ytdlp",
                asyncio.to_thread(
                    search_youtube_shorts_ytdlp_sync, st, product, queries
                ),
            )
        )
    if wants_platform(platforms, "Reddit") and cap["Reddit"] > 0:
        st = _st(settings, cap["Reddit"])
        specs.append(("reddit", search_reddit(client, st, product, queries)))

    if wants_platform(platforms, "Tiktok") and cap["Tiktok"] > 0:
        st = _st(settings, cap["Tiktok"])

        async def tiktok_native_async() -> list[CandidateLink]:
            cands, obs = await run_tiktok_native_with_retries(
                st, product, queries, pa
            )
            adapter_observations.extend(obs)
            return cands

        specs.append(("tiktok_native", tiktok_native_async()))
    if wants_platform(platforms, "Instagram") and cap["Instagram"] > 0:
        st = _st(settings, cap["Instagram"])
        specs.append(("instagram_native", instagram_native_async(st)))

    if wants_platform(platforms, "Tiktok") and cap["Tiktok"] > 0:
        specs.append(("tiktok_ddg", tiktok_ddg_async()))
    if wants_platform(platforms, "Facebook") and cap["Facebook"] > 0:
        specs.append(("facebook_ddg", facebook_ddg_async()))
    if (
        wants_platform(platforms, "Facebook")
        and cap["Facebook"] > 0
        and settings.facebook_playwright_enabled
    ):

        async def facebook_playwright_async() -> list[CandidateLink]:
            from linksearch.platforms.facebook_playwright import search_facebook_playwright

            return await search_facebook_playwright(
                settings, product, result_cap=cap["Facebook"]
            )

        specs.append(("facebook_playwright", facebook_playwright_async()))
    if wants_platform(platforms, "Instagram") and cap["Instagram"] > 0:
        specs.append(("instagram_ddg", instagram_ddg_async()))

    if wants_platform(platforms, "Tiktok") and cap["Tiktok"] > 0 and settings.brave_search_enabled:

        async def brave_tt() -> list[CandidateLink]:
            return await search_site_brave(
                client,
                settings,
                product,
                queries,
                "tiktok.com",
                "Tiktok",
                max_queries=min(4, budget_to_ddg_queries(budgets["Tiktok"]) or 1),
                result_cap=max(1, cap["Tiktok"]),
            )

        specs.append(("brave_tiktok", brave_tt()))

    if wants_platform(platforms, "Facebook") and cap["Facebook"] > 0 and settings.brave_search_enabled:

        async def brave_fb() -> list[CandidateLink]:
            return await search_site_brave(
                client,
                settings,
                product,
                queries,
                "facebook.com",
                "Facebook",
                max_queries=min(3, budget_to_ddg_queries(budgets["Facebook"]) or 1),
                result_cap=cap["Facebook"],
            )

        specs.append(("brave_facebook", brave_fb()))

    if wants_platform(platforms, "Instagram") and cap["Instagram"] > 0 and settings.brave_search_enabled:

        async def brave_ig() -> list[CandidateLink]:
            return await search_site_brave(
                client,
                settings,
                product,
                queries,
                "instagram.com",
                "Instagram",
                max_queries=min(3, budget_to_ddg_queries(budgets["Instagram"]) or 1),
                result_cap=cap["Instagram"],
            )

        specs.append(("brave_instagram", brave_ig()))

    if wants_platform(platforms, "Tiktok") and cap["Tiktok"] > 0:
        st = _st(settings, cap["Tiktok"])
        specs.append(
            ("tiktok_cse", search_tiktok_cse(client, st, product, queries))
        )
    if wants_platform(platforms, "Facebook") and cap["Facebook"] > 0:
        st = _st(settings, cap["Facebook"])
        specs.append(
            ("facebook_cse", search_facebook_cse(client, st, product, queries))
        )
    if wants_platform(platforms, "Instagram") and cap["Instagram"] > 0:
        st = _st(settings, cap["Instagram"])
        specs.append(
            ("instagram_cse", search_instagram_cse(client, st, product, queries))
        )

    if not specs:
        return [], [f"{product.sku}: No matching sources for selected platforms."], {}

    tasks = [s[1] for s in specs]
    names = [s[0] for s in specs]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    merged: list[CandidateLink] = []
    for name, res in zip(names, results):
        if isinstance(res, Exception):
            warnings.append(f"{product.sku} [{name}]: {res}")
            logger.warning("%s failed: %s", name, res)
            log_event(name, _plat_from_task(name), count=0, extra=str(res)[:120])
            continue
        n = len(res)
        merged.extend(res)
        log_event(
            name,
            _plat_from_task(name),
            count=n,
            extra="pass1_native_or_fallback",
        )

    seeds: list[str] = []
    for c in merged[:15]:
        if c.media in ("Tiktok", "Instagram") and (c.snippet or c.title):
            seeds.append((c.snippet or "") + " " + (c.title or ""))
    if seeds:
        expand_queries_with_seed(pa, seeds, cap=10)

    if getattr(settings, "seed_expand_v3_enabled", True):
        try:
            more_seed, seeds_n = await seed_expansion_v3(
                settings,
                product,
                merged,
                platforms=requested,
                cap=cap,
                budgets=budgets,
            )
            merged.extend(more_seed)
            log_event(
                "seed_expand_v3",
                "Tiktok",
                pass_no=2,
                count=len(more_seed),
                extra=f"seeds:{seeds_n}",
            )
        except Exception as e:
            warnings.append(f"{product.sku} [seed_expand_v3]: {e}")
    else:
        tt_urls = [c.url for c in merged if "tiktok.com" in c.url.lower()]
        if (
            wants_platform(platforms, "Tiktok")
            and cap["Tiktok"] > 0
            and budgets["Tiktok"] in ("deep", "medium")
            and tt_urls
        ):
            try:
                more_tt = await expand_tiktok_around_handles(
                    settings,
                    product,
                    tt_urls,
                    min(10, cap["Tiktok"]),
                )
                merged.extend(more_tt)
                log_event(
                    "seed_expand_tiktok",
                    "Tiktok",
                    pass_no=2,
                    count=len(more_tt),
                    extra="handle_search",
                )
            except Exception as e:
                warnings.append(f"{product.sku} [seed_expand_tiktok]: {e}")

        if (
            wants_platform(platforms, "Instagram")
            and cap["Instagram"] > 0
            and budgets["Instagram"] in ("deep", "medium")
        ):
            slug = re.sub(
                r"[^a-z0-9._]", "", product.normalized_brand().lower().replace(" ", "")
            )[:30]
            try:
                more_ig = await asyncio.to_thread(
                    expand_instagram_profile_posts_sync,
                    settings,
                    product,
                    slug,
                    min(8, cap["Instagram"]),
                )
                merged.extend(more_ig)
                log_event(
                    "seed_expand_instagram",
                    "Instagram",
                    pass_no=2,
                    count=len(more_ig),
                    extra=f"profile:{slug}",
                )
            except Exception as e:
                warnings.append(f"{product.sku} [seed_expand_instagram]: {e}")

    social = ("tiktok.com", "instagram.com", "facebook.com")
    to_enrich = [c for c in merged if any(h in c.url.lower() for h in social)]
    await enrich_candidates_parallel(
        client, to_enrich[: max(1, settings.max_results_per_platform * 15)]
    )

    by_media: dict[str, list[CandidateLink]] = defaultdict(list)
    for c in merged:
        by_media[c.media].append(c)

    final: list[CandidateLink] = []
    per_cap = settings.max_results_per_platform
    for media, items in by_media.items():
        ranked = apply_heuristic_and_sort(product, items, pa)
        if settings.strict_sku_filter and product.sku.strip():
            sku_lower = product.sku.strip().lower()
            sku_matches = [
                c
                for c in ranked
                if f"{c.title} {c.snippet}".lower().find(sku_lower) != -1
            ]
            ranked = sku_matches if sku_matches else ranked
        if use_groq_rerank and settings.groq_enabled():
            ranked = groq_rerank_candidates(settings, product, ranked, per_cap * 2)
        for c in ranked[: per_cap * 2]:
            final.append(c)

    best: dict[str, CandidateLink] = {}
    for c in sorted(final, key=lambda x: float(x.score), reverse=True):
        key = canonicalize_social_url(c.url)
        old = best.get(key)
        if old is None or float(c.score) > float(old.score):
            best[key] = c

    deduped = sorted(best.values(), key=lambda x: (x.media, -float(x.score)))
    found_platforms = {c.media for c in deduped}
    explanation = build_explanation(found_platforms, requested, coverage, archetype)
    classification = build_classification_block(
        found_platforms, requested, coverage, archetype, cap
    )
    meta: dict[str, object] = {
        "objective": OBJECTIVE,
        "product_archetype": archetype,
        "platform_coverage_likelihood": {k: v for k, v in coverage.items()},
        "crawl_budgets": {k: str(v) for k, v in budgets.items()},
        "effective_caps": {k: v for k, v in cap.items()},
        "found_platforms": sorted(found_platforms),
        "missing_platforms": sorted(requested - found_platforms),
        "explanation": explanation,
        "classification": classification,
        "debug_social_heavy_zero_tiktok": False,
        "discovery_events": discovery_events[:200],
        "adapter_observations": adapter_observations[:300],
        "runtime_region": get_runtime_region(),
    }

    return deduped, warnings, meta


def _plat_from_task(name: str) -> str:
    if "youtube_shorts" in name:
        return "YoutubeShorts"
    if "youtube" in name:
        return "Youtube"
    if "reddit" in name:
        return "Reddit"
    if "tiktok" in name or name == "brave_tiktok":
        return "Tiktok"
    if "facebook" in name or name == "brave_facebook" or name == "facebook_playwright":
        return "Facebook"
    if "instagram" in name or name == "brave_instagram":
        return "Instagram"
    return "Unknown"


async def run_pipeline(
    products: list[ProductInput],
    settings: Settings | None = None,
    use_groq_rerank: bool = True,
    platforms: list[str] | None = None,
) -> PipelineResult:
    settings = settings or load_settings()
    np = normalize_platform_list(platforms)
    out_rows: list[CandidateLink] = []
    all_warnings: list[str] = []
    run_meta: list[dict[str, object]] = []

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        for p in products:
            rows, w, m = await discover_for_product(
                client, settings, p, use_groq_rerank, platforms=platforms
            )
            out_rows.extend(rows)
            all_warnings.extend(w)
            run_meta.append({"sku": p.sku, **m})

    top_meta: dict[str, object] = {
        "objective": OBJECTIVE,
        "per_product": run_meta,
    }
    if len(run_meta) == 1:
        top_meta.update(run_meta[0])  # type: ignore[arg-type]

    if wants_platform(np, "Youtube") and not settings.youtube_enabled():
        all_warnings.append(
            "YOUTUBE_API_KEY not set; YouTube Data API disabled. "
            "If YOUTUBE_USE_YTDLP is true (default), yt-dlp still searches YouTube."
        )
    if wants_platform(np, "YoutubeShorts") and not settings.youtube_use_ytdlp:
        all_warnings.append(
            "YOUTUBE_USE_YTDLP is false; YouTube Shorts discovery (yt-dlp) is skipped."
        )
    if settings.google_cse_enabled and not settings.cse_enabled():
        if wants_platform(np, "Tiktok") or wants_platform(np, "Facebook") or wants_platform(
            np, "Instagram"
        ):
            all_warnings.append(
                "GOOGLE_CSE_API_KEY / GOOGLE_CSE_ID not set; TikTok, Facebook, Instagram (CSE) skipped."
            )
    return PipelineResult(rows=out_rows, warnings=all_warnings, meta=top_meta)
