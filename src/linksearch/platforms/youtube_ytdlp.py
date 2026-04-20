from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from linksearch.models import CandidateLink, ProductInput

if TYPE_CHECKING:
    from linksearch.config import Settings

logger = logging.getLogger(__name__)


def search_youtube_ytdlp_sync(
    settings: Settings,
    product: ProductInput,
    queries: list[str],
) -> list[CandidateLink]:
    """YouTube search via yt-dlp (Innertube). No Google Cloud API key."""
    if not settings.youtube_use_ytdlp:
        return []
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp is not installed; skip Innertube YouTube search.")
        return []

    cap = max(1, settings.max_results_per_platform)
    q_text = " ".join(queries[:3]) if queries else product.primary_query()
    q_text = q_text.strip()[:200]
    if not q_text:
        return []

    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "socket_timeout": min(60.0, max(15.0, settings.request_timeout_seconds + 15)),
    }
    url = f"ytsearch{cap}:{q_text}"
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.warning("yt-dlp YouTube search failed: %s", e)
        return []

    entries: list = []
    if info is None:
        return []
    if info.get("_type") == "playlist":
        entries = [e for e in (info.get("entries") or []) if e]
    else:
        entries = [info]

    out: list[CandidateLink] = []
    seen: set[str] = set()
    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()

    for ent in entries:
        if not isinstance(ent, dict):
            continue
        vid = ent.get("id")
        title = str(ent.get("title") or "")
        u = str(ent.get("url") or "")
        if not u and vid:
            u = f"https://www.youtube.com/watch?v={vid}"
        if not u:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(
            CandidateLink(
                media="Youtube",
                brand=brand,
                url=u,
                sku=sku,
                product_name=pname,
                title=title,
                snippet=str(ent.get("description") or "")[:500],
                source_query=q_text,
            )
        )
        if len(out) >= cap:
            break
    return out
