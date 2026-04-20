from __future__ import annotations

import asyncio

import httpx

from linksearch.config import Settings
from linksearch.models import CandidateLink, ProductInput
from linksearch.platforms.youtube import search_youtube
from linksearch.platforms.youtube_ytdlp import search_youtube_ytdlp_sync


async def search_youtube_merged(
    client: httpx.AsyncClient,
    settings: Settings,
    product: ProductInput,
    queries: list[str],
) -> list[CandidateLink]:
    """Combine YouTube Data API v3 (if key set) and yt-dlp Innertube search (if enabled)."""
    chunks: list[list[CandidateLink]] = []
    if settings.youtube_enabled():
        chunks.append(await search_youtube(client, settings, product, queries))
    if settings.youtube_use_ytdlp:
        ytdlp = await asyncio.to_thread(
            search_youtube_ytdlp_sync, settings, product, queries
        )
        chunks.append(ytdlp)

    seen: set[str] = set()
    merged: list[CandidateLink] = []
    for lst in chunks:
        for c in lst:
            if c.url not in seen:
                seen.add(c.url)
                merged.append(c)
    return merged
