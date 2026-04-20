"""
Standalone TikTok search debug (sync Playwright). Hardcoded query — does not run full pipeline.

Run from repo root:
  .venv\\Scripts\\python.exe scripts/tiktok_playwright_debug.py
"""

from __future__ import annotations

import sys
from urllib.parse import quote_plus

try:
    from playwright.sync_api import sync_playwright
except ImportError as e:
    print("playwright not installed:", e, file=sys.stderr)
    sys.exit(1)

TEST_QUERY = "ninja creami"


def debug_dump(page, network_hits: list[str], label: str) -> None:
    print(f"\n=== TIKTOK DEBUG START ({label}) ===")

    content = page.content()
    print("PAGE_LENGTH:", len(content))

    body_text = page.locator("body").inner_text(timeout=15_000)
    print("BODY_TEXT_SAMPLE:", body_text[:1000].replace("\n", " "))

    video_links = page.locator("a[href*='/video/']").evaluate_all(
        "(els) => els.map((e) => e.href)"
    )
    print("VIDEO_LINKS_FOUND:", len(video_links))
    print("VIDEO_LINKS_SAMPLE:", video_links[:10])

    all_links = page.locator("a").evaluate_all("(els) => els.map((e) => e.href).filter(Boolean)")
    print("ALL_LINKS_FOUND:", len(all_links))
    print("ALL_LINKS_SAMPLE:", all_links[:20])

    print("CURRENT_URL:", page.url)

    lower_text = body_text.lower()
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
    print("BLOCK_SIGNALS:", matched)

    print("NETWORK_HITS_COUNT:", len(network_hits))
    print("NETWORK_HITS_SAMPLE:", network_hits[:20])

    print(f"=== TIKTOK DEBUG END ({label}) ===\n")


def main() -> None:
    network_hits: list[str] = []

    def handle_response(response) -> None:
        url = response.url.lower()
        if "tiktok" in url and any(
            k in url for k in ["api", "search", "item", "recommend", "video"]
        ):
            network_hits.append(response.url)

    test_query = TEST_QUERY
    url = f"https://www.tiktok.com/search?q={quote_plus(test_query)}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="en-US",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        page = context.new_page()
        page.on("response", handle_response)

        page.goto(url, wait_until="domcontentloaded", timeout=60_000)

        debug_dump(page, network_hits, "after goto")

        for i in range(5):
            page.mouse.wheel(0, 5000)
            page.wait_for_timeout(1500)

        debug_dump(page, network_hits, "after scroll")

        context.close()
        browser.close()

    print("\n--- Summary (use AFTER SCROLL values as primary) ---")
    print("See second block above for PAGE_LENGTH, BODY_TEXT_SAMPLE, VIDEO_LINKS_*, etc.")


if __name__ == "__main__":
    main()
