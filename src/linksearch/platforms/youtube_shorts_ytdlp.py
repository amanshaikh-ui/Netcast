"""YouTube Shorts discovery via yt-dlp using YouTube's Shorts search filter (real Shorts)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING
from urllib.parse import urlencode, urlparse

from linksearch.models import CandidateLink, ProductInput

if TYPE_CHECKING:
    from linksearch.config import Settings

logger = logging.getLogger(__name__)

# YouTube web search: Type = Shorts (not plain "ytsearch" + keyword — that returns mixed videos).
# Same filter as opening Results with the Shorts chip; see yt-dlp YoutubeSearchURLIE / issue #16010.
_SHORTS_SEARCH_SP = "EgIQCQ=="


def _shorts_results_url(search_query: str) -> str:
    q = search_query.strip()
    if not q:
        return ""
    return "https://www.youtube.com/results?" + urlencode(
        {"search_query": q, "sp": _SHORTS_SEARCH_SP}
    )


def _shorts_watch_url(url: str) -> str | None:
    """Normalize to https://www.youtube.com/shorts/VIDEO_ID when possible."""
    if not url or not isinstance(url, str):
        return None
    u = url.strip()
    if "/shorts/" in u.lower():
        try:
            p = urlparse(u)
            path = p.path or ""
            if "/shorts/" in path.lower():
                vid = path.split("/shorts/", 1)[-1].strip("/").split("/")[0]
                if len(vid) == 11:
                    return f"https://www.youtube.com/shorts/{vid}"
        except Exception:
            pass
        return u.split("&")[0]
    return None


def _env_date_range() -> tuple[str | None, str | None]:
    """CLI / server env: YOUTUBE_SHORTS_DATE_AFTER, YOUTUBE_SHORTS_DATE_BEFORE (YYYY-MM-DD)."""
    a = os.environ.get("YOUTUBE_SHORTS_DATE_AFTER", "").strip()
    b = os.environ.get("YOUTUBE_SHORTS_DATE_BEFORE", "").strip()
    if not a and not b:
        return None, None
    return (a or None, b or None)


def _iso_to_ymd(iso: str) -> str:
    return iso.replace("-", "")[:8]


def _upload_date_ydl(short_url: str, timeout: float) -> str | None:
    """Return upload_date as YYYYMMDD via yt-dlp --print."""
    tail = [
        short_url,
        "--skip-download",
        "--print",
        "%(upload_date)s",
        "--no-warnings",
        "--quiet",
    ]
    candidates: list[list[str]] = []
    if shutil.which("yt-dlp"):
        candidates.append(["yt-dlp", *tail])
    candidates.append([sys.executable, "-m", "yt_dlp", *tail])
    for cmd in candidates:
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=max(15.0, timeout),
            )
            line = (r.stdout or "").strip()
            if len(line) == 8 and line.isdigit():
                return line
        except Exception:
            continue
    return None


def search_youtube_shorts_ytdlp_sync(
    settings: "Settings",
    product: ProductInput,
    queries: list[str],
) -> list[CandidateLink]:
    """Search YouTube Shorts only; emit https://www.youtube.com/shorts/VIDEO_ID links."""
    if not settings.youtube_use_ytdlp:
        return []
    try:
        import yt_dlp
    except ImportError:
        logger.warning("yt-dlp is not installed; skip YouTube Shorts search.")
        return []

    cap = max(1, settings.max_results_per_platform)
    base = " ".join(queries[:3]) if queries else product.primary_query()
    base = base.strip()[:200]
    if not base:
        return []
    q_text = base
    page_url = _shorts_results_url(q_text)
    if not page_url:
        return []

    d_after_raw, d_before_raw = _env_date_range()
    has_date = bool(d_after_raw or d_before_raw)
    max_collect = min(max(cap * 10, 24), 50) if has_date else cap
    after_ymd = _iso_to_ymd(d_after_raw) if d_after_raw else None
    before_ymd = _iso_to_ymd(d_before_raw) if d_before_raw else None

    ydl_opts: dict = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
        "playlistend": max_collect,
        "socket_timeout": min(60.0, max(15.0, settings.request_timeout_seconds + 15)),
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(page_url, download=False)
    except Exception as e:
        logger.warning("yt-dlp YouTube Shorts search failed: %s", e)
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
        vid_s = str(vid).strip() if vid is not None else ""
        title = str(ent.get("title") or "")
        raw_url = ent.get("url")
        u = _shorts_watch_url(str(raw_url)) if raw_url else None
        if not u and len(vid_s) == 11:
            u = f"https://www.youtube.com/shorts/{vid_s}"
        if not u:
            continue
        if u in seen:
            continue
        seen.add(u)
        out.append(
            CandidateLink(
                media="YoutubeShorts",
                brand=brand,
                url=u,
                sku=sku,
                product_name=pname,
                title=title,
                snippet=str(ent.get("description") or "")[:500],
                source_query=q_text,
            )
        )
        if len(out) >= max_collect:
            break

    if not has_date:
        return out[:cap]

    tout = min(60.0, max(15.0, settings.request_timeout_seconds + 15))
    filtered: list[CandidateLink] = []
    for c in out:
        ud = _upload_date_ydl(c.url, tout)
        if not ud:
            continue
        if after_ymd and ud < after_ymd:
            continue
        if before_ymd and ud > before_ymd:
            continue
        filtered.append(c)
        if len(filtered) >= cap:
            break
    return filtered
