"""Lightweight HTML fetch for og:title / description to enrich candidates before ranking."""

from __future__ import annotations

import asyncio
import re
from html import unescape

import httpx

from linksearch.crawl4ai_merge import merge_from_html
from linksearch.models import CandidateLink

_OG_TITLE = re.compile(
    r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_OG_DESC = re.compile(
    r'<meta[^>]+property=["\']og:description["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_TITLE_TAG = re.compile(r"<title[^>]*>([^<]{1,500})</title>", re.I)


async def enrich_candidate_snippet(
    client: httpx.AsyncClient, c: CandidateLink, timeout: float = 8.0
) -> None:
    """Merge Open Graph / title into evidence fields for scoring."""
    url = c.url.strip()
    if not url.startswith("http"):
        return
    try:
        r = await client.get(
            url,
            follow_redirects=True,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        if r.status_code >= 400:
            return
        html = r.text[:800_000]
    except Exception:
        return

    merge_from_html(c, html)

    title = ""
    desc = ""
    m = _OG_TITLE.search(html)
    if m:
        title = unescape(m.group(1).strip())
    if not title:
        m2 = _TITLE_TAG.search(html)
        if m2:
            title = unescape(m2.group(1).strip())
    m3 = _OG_DESC.search(html)
    if m3:
        desc = unescape(m3.group(1).strip())

    if title:
        c.title = title[:500] if not c.title.strip() else f"{c.title[:200]} | {title[:200]}"
    if desc:
        c.snippet = (
            f"{c.snippet} {desc}"[:2000] if c.snippet else desc
        )[:2000]


async def enrich_candidates_parallel(
    client: httpx.AsyncClient,
    candidates: list[CandidateLink],
    max_concurrent: int = 5,
) -> None:
    if not candidates:
        return
    sem = asyncio.Semaphore(max_concurrent)

    async def one(c: CandidateLink) -> None:
        async with sem:
            await enrich_candidate_snippet(client, c)

    await asyncio.gather(*(one(c) for c in candidates))
