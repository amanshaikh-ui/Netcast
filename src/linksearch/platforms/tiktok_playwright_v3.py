"""
TikTok adapter v3: Playwright-native search, scroll, XHR tap, /video/ extraction,
guest/login blocker detection, optional profile expansion from first @handle.

Requires: pip install playwright && playwright install chromium
"""

from __future__ import annotations

import logging
import os
import re
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from linksearch.models import CandidateLink, ProductInput
from linksearch.observability import AdapterObservation

if TYPE_CHECKING:
    from linksearch.config import Settings

logger = logging.getLogger(__name__)

_VIDEO_URL = re.compile(r"https?://(?:www\.)?tiktok\.com/@[^/]+/video/\d+", re.I)
_VIDEO_PATH = re.compile(r"/@[^/]+/video/\d+", re.I)
_HANDLE = re.compile(r"@([\w.]{2,64})")


def _tiktok_playwright_debug_enabled() -> bool:
    v = (os.environ.get("TIKTOK_PLAYWRIGHT_DEBUG") or "").strip().lower()
    return v in ("1", "true", "yes")


def _debug_dump_page(page, network_hits: list[str], label: str) -> None:
    """Hard debug: PAGE_LENGTH, body sample, link counts, block signals, network hits."""
    if not _tiktok_playwright_debug_enabled():
        return
    print(f"\n=== TIKTOK DEBUG START ({label}) ===", flush=True)
    try:
        content = page.content()
        print("PAGE_LENGTH:", len(content), flush=True)
    except Exception as e:
        print("PAGE_LENGTH: <error>", e, flush=True)
        return
    try:
        body_text = page.locator("body").inner_text(timeout=15_000)
        print("BODY_TEXT_SAMPLE:", body_text[:1000].replace("\n", " "), flush=True)
    except Exception as e:
        body_text = ""
        print("BODY_TEXT_SAMPLE: <error>", e, flush=True)
    try:
        video_links = page.locator("a[href*='/video/']").evaluate_all(
            "(els) => els.map((e) => e.href)"
        )
        print("VIDEO_LINKS_FOUND:", len(video_links), flush=True)
        print("VIDEO_LINKS_SAMPLE:", video_links[:10], flush=True)
    except Exception as e:
        print("VIDEO_LINKS_FOUND: <error>", e, flush=True)
    try:
        all_links = page.locator("a").evaluate_all(
            "(els) => els.map((e) => e.href).filter(Boolean)"
        )
        print("ALL_LINKS_FOUND:", len(all_links), flush=True)
        print("ALL_LINKS_SAMPLE:", all_links[:20], flush=True)
    except Exception as e:
        print("ALL_LINKS_FOUND: <error>", e, flush=True)
    try:
        print("CURRENT_URL:", page.url, flush=True)
    except Exception:
        pass
    lower_text = (body_text or "").lower()
    block_signals = [
        "log in",
        "login",
        "sign up",
        "signup",
        "captcha",
        "verify",
        "not available",
        "govt. of india",
        "block 59",
        "decided to block",
    ]
    matched = [s for s in block_signals if s in lower_text]
    print("BLOCK_SIGNALS:", matched, flush=True)
    print("NETWORK_HITS_COUNT:", len(network_hits), flush=True)
    print("NETWORK_HITS_SAMPLE:", network_hits[:20], flush=True)
    print(f"=== TIKTOK DEBUG END ({label}) ===\n", flush=True)


def _detect_blocker(page) -> bool:
    try:
        login = page.get_by_text(re.compile(r"log\s*in|sign\s*up", re.I))
        if login.count() > 0:
            return True
        c = page.locator(
            r"text=/captcha|verify\s+you.*human|access\s+denied|something\s+went\s+wrong/i"
        )
        if c.count() > 0:
            return True
    except Exception:
        pass
    return False


def _collect_video_links(page, seen: set[str], network_urls: list[str]) -> list[str]:
    found: list[str] = []
    for u in network_urls:
        for m in _VIDEO_URL.finditer(u):
            url = m.group(0).split("?")[0]
            if url not in seen:
                seen.add(url)
                found.append(url)
    try:
        for loc in page.locator('a[href*="/video/"]').all()[:80]:
            try:
                href = loc.get_attribute("href") or ""
                if "/video/" not in href:
                    continue
                if not href.startswith("http"):
                    href = "https://www.tiktok.com" + href
                href = href.split("?")[0]
                if href not in seen:
                    seen.add(href)
                    found.append(href)
            except Exception:
                continue
    except Exception:
        pass
    try:
        html = page.content()
        for m in _VIDEO_PATH.finditer(html):
            u = "https://www.tiktok.com" + m.group(0)
            if u not in seen:
                seen.add(u)
                found.append(u)
    except Exception:
        pass
    return found


def search_tiktok_playwright_v3_sync(
    settings: "Settings",
    product: ProductInput,
    query_pack: list[str],
    base_obs: AdapterObservation | None = None,
) -> tuple[list[CandidateLink], AdapterObservation]:
    """Sync API for asyncio.to_thread. One pack per call; caller handles retries."""
    obs = base_obs or AdapterObservation(adapter_name="tiktok_playwright_v3")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        obs.rejection_reason = "playwright_not_installed"
        return [], obs

    if not query_pack:
        obs.rejection_reason = "empty_query_pack"
        return [], obs

    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    cap = max(1, settings.max_results_per_platform * 3)
    q = query_pack[0][:200]
    obs.query_used = q

    network_payload_count = 0
    network_urls: list[str] = []
    network_hits: list[str] = []
    visible_results_count = 0
    candidates: list[CandidateLink] = []
    seen: set[str] = set()

    def on_response(response) -> None:
        nonlocal network_payload_count
        try:
            u = response.url
            ul = u.lower()
            if "tiktok" in ul and any(
                k in ul for k in ["api", "search", "item", "recommend", "video"]
            ):
                network_hits.append(u)
            if ("tiktok.com" in u) and (
                "/api/" in u or "aweme" in u or "search" in u or "item" in u
            ):
                network_payload_count += 1
                if response.status == 200:
                    try:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct:
                            txt = response.text()
                            if len(txt) < 80_000:
                                network_urls.append(txt)
                            else:
                                network_urls.append(u)
                        else:
                            network_urls.append(u)
                    except Exception:
                        network_urls.append(u)
        except Exception:
            pass

    scroll_rounds = int(getattr(settings, "tiktok_playwright_scroll_rounds", 6) or 6)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=not getattr(settings, "tiktok_playwright_headed", False)
        )
        context = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.on("response", on_response)

        search_url = f"https://www.tiktok.com/search?q={quote_plus(q)}"
        try:
            page.goto(search_url, wait_until="domcontentloaded", timeout=45000)
        except Exception as e:
            obs.rejection_reason = f"goto:{e}"[:300]
            context.close()
            browser.close()
            return [], obs

        _debug_dump_page(page, network_hits, "after goto")

        try:
            page.wait_for_response(
                lambda r: r.url.startswith("https://www.tiktok.com") and "api" in r.url,
                timeout=12000,
            )
        except Exception:
            pass

        if _detect_blocker(page):
            obs.rejection_reason = "guest_or_login_wall"
            obs.visible_results_count = 0
            obs.network_payload_count = network_payload_count

        aggressive = os.environ.get("TIKTOK_PLAYWRIGHT_AGGRESSIVE_SCROLL", "").lower() in (
            "1",
            "true",
            "yes",
        ) or _tiktok_playwright_debug_enabled()

        if aggressive:
            for _ in range(5):
                page.mouse.wheel(0, 5000)
                page.wait_for_timeout(1500)
        else:
            for _ in range(scroll_rounds):
                found = _collect_video_links(page, seen, network_urls)
                visible_results_count = max(visible_results_count, len(found))
                page.mouse.wheel(0, 2200)
                page.wait_for_timeout(600)

        _debug_dump_page(page, network_hits, "after scroll")

        found = _collect_video_links(page, seen, network_urls)[: cap + 5]
        visible_results_count = max(visible_results_count, len(found))

        handles: list[str] = []
        try:
            body = page.locator("body").inner_text(timeout=5000)
            for m in _HANDLE.finditer(body):
                h = m.group(1).lower()
                if h not in handles:
                    handles.append(h)
        except Exception:
            pass

        for url in found:
            if len(candidates) >= cap:
                break
            candidates.append(
                CandidateLink(
                    media="Tiktok",
                    brand=brand,
                    url=url,
                    sku=sku,
                    product_name=pname,
                    title="",
                    snippet="",
                    source_query=f"pw_v3:{q}",
                )
            )

        seeds_expanded = 0
        if handles and len(candidates) < cap and getattr(
            settings, "tiktok_playwright_expand_profile", True
        ):
            h0 = handles[0]
            try:
                prof = f"https://www.tiktok.com/@{h0}"
                page.goto(prof, wait_until="domcontentloaded", timeout=35000)
                try:
                    page.wait_for_response(
                        lambda r: h0 in r.url or "item" in r.url,
                        timeout=10000,
                    )
                except Exception:
                    pass
                for _ in range(min(4, scroll_rounds)):
                    extra = _collect_video_links(page, seen, network_urls)
                    for url in extra:
                        if len(candidates) >= cap:
                            break
                        if url not in {c.url for c in candidates}:
                            candidates.append(
                                CandidateLink(
                                    media="Tiktok",
                                    brand=brand,
                                    url=url,
                                    sku=sku,
                                    product_name=pname,
                                    title="",
                                    snippet="",
                                    source_query=f"pw_v3_profile:{h0}",
                                )
                            )
                            seeds_expanded += 1
                    page.mouse.wheel(0, 2400)
                    page.wait_for_timeout(500)
            except Exception as e:
                logger.debug("TT profile expand: %s", e)

        obs.visible_results_count = visible_results_count
        obs.network_payload_count = network_payload_count
        obs.candidates_extracted = len(candidates)
        obs.seeds_expanded = seeds_expanded
        if not candidates and not obs.rejection_reason:
            obs.rejection_reason = "no_video_links_in_ui_or_xhr"

        context.close()
        browser.close()

    return candidates[: settings.max_results_per_platform * 2], obs
