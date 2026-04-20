"""Canonical URLs for dedupe after evidence (strip tracking params, normalize paths)."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

_UTM_KEYS = frozenset(
    k
    for k in (
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
    )
)


def canonicalize_social_url(url: str) -> str:
    try:
        p = urlparse(url.strip())
    except Exception:
        return url
    if not p.scheme:
        return url
    host = (p.netloc or "").lower()
    path = p.path or ""

    # TikTok video ID
    m = re.search(r"/video/(\d+)", path)
    if "tiktok.com" in host and m:
        path = f"/video/{m.group(1)}"
        return urlunparse((p.scheme, host, path, "", "", ""))

    # Instagram reel or p/
    m = re.search(r"/(p|reel|tv)/([^/?]+)", path)
    if "instagram.com" in host and m:
        path = f"/{m.group(1)}/{m.group(2)}"
        return urlunparse((p.scheme, host, path, "", "", ""))

    # YouTube /shorts/VIDEO_ID
    m_shorts = re.search(r"/shorts/([^/?]+)", path)
    if "youtube.com" in host and m_shorts:
        path = f"/shorts/{m_shorts.group(1)}"
        return urlunparse((p.scheme, host, path, "", "", ""))

    # YouTube watch v=
    if "youtube.com" in host or "youtu.be" in host:
        q = parse_qs(p.query)
        if "v" in q and q["v"]:
            nv = {k: v for k, v in q.items() if k not in _UTM_KEYS}
            if "v" not in nv:
                nv["v"] = q["v"]
            q2 = urlencode({k: v[0] for k, v in nv.items() if k == "v" or k not in _UTM_KEYS})
            return urlunparse((p.scheme, host, p.path, "", q2, ""))

    # Strip known tracking query params
    q = parse_qs(p.query)
    kept = {k: v for k, v in q.items() if k.lower() not in _UTM_KEYS}
    q2 = urlencode({k: v[0] for k, v in kept.items()}) if kept else ""
    return urlunparse((p.scheme, host, path, p.params, q2, ""))
