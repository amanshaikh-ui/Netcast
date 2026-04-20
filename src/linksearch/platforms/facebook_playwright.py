"""
Optional Facebook Page scrape via Playwright (async): page + /videos, scroll, link harvest.

Requires: pip install playwright && playwright install chromium

Set FACEBOOK_PLAYWRIGHT_ENABLED=true. Set FACEBOOK_PAGE_URL for the exact Page URL;
otherwise https://www.facebook.com/<slug> is derived from brand (often wrong).
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from linksearch.models import CandidateLink, ProductInput

if TYPE_CHECKING:
    from linksearch.config import Settings

logger = logging.getLogger(__name__)

_FB_HINTS = ("/videos/", "/watch/", "/reel/", "/posts/")


def facebook_page_url_for_product(settings: "Settings", product: ProductInput) -> str | None:
    raw = (getattr(settings, "facebook_page_url", None) or "").strip()
    if raw:
        return raw.rstrip("/")
    slug = re.sub(r"[^a-zA-Z0-9.]", "", product.normalized_brand().lower())[:80]
    return f"https://www.facebook.com/{slug}" if len(slug) >= 2 else None


async def scrape_facebook_videos(page_url: str) -> list[str]:
    """Load a Page, try /videos, scroll, return deduped video/post-like URLs."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.warning("playwright not installed; skip Facebook Playwright")
        return []

    results: list[str] = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(page_url, wait_until="domcontentloaded", timeout=60_000)
            await page.wait_for_timeout(3000)
            try:
                await page.goto(
                    page_url.rstrip("/") + "/videos",
                    wait_until="domcontentloaded",
                    timeout=60_000,
                )
                await page.wait_for_timeout(3000)
            except Exception as e:
                logger.debug("facebook /videos: %s", e)

            for _ in range(5):
                await page.mouse.wheel(0, 5000)
                await page.wait_for_timeout(1500)

            links = await page.locator("a").evaluate_all(
                "(els) => els.map((e) => e.href).filter(Boolean)"
            )
            for link in links:
                if link and "facebook.com" in link and any(h in link for h in _FB_HINTS):
                    results.append(link.split("?")[0])
            return list(dict.fromkeys(results))
        finally:
            await browser.close()


async def search_facebook_playwright(
    settings: "Settings",
    product: ProductInput,
    *,
    result_cap: int,
) -> list[CandidateLink]:
    page_url = facebook_page_url_for_product(settings, product)
    if not page_url:
        return []
    urls = await scrape_facebook_videos(page_url)
    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    out: list[CandidateLink] = []
    for url in urls[: max(1, result_cap * 3)]:
        out.append(
            CandidateLink(
                media="Facebook",
                brand=brand,
                url=url,
                sku=sku,
                product_name=pname,
                title="",
                snippet="",
                source_query=f"facebook_playwright:{page_url}",
            )
        )
        if len(out) >= result_cap * 2:
            break
    return out[: max(1, result_cap * 2)]


if __name__ == "__main__":
    import asyncio

    async def _main() -> None:
        data = await scrape_facebook_videos("https://www.facebook.com/ninjakitchen")
        print(f"Found {len(data)} links")
        for d in data[:20]:
            print(d)

    asyncio.run(_main())
