"""Canonical platform IDs matching CandidateLink.media labels."""

from __future__ import annotations

# Must match CandidateLink.media strings from search modules.
ALLOWED_PLATFORMS: frozenset[str] = frozenset(
    {"Youtube", "YoutubeShorts", "Reddit", "Tiktok", "Facebook", "Instagram"}
)


def normalize_platform_list(raw: list[str] | None) -> list[str] | None:
    """Return None = all platforms; empty after filter = none allowed."""
    if raw is None:
        return None
    seen: set[str] = set()
    out: list[str] = []
    for x in raw:
        t = (x or "").strip()
        if t in ALLOWED_PLATFORMS and t not in seen:
            seen.add(t)
            out.append(t)
    return out


def wants_platform(platforms: list[str] | None, key: str) -> bool:
    """If platforms is None, all enabled. If empty list, nothing enabled."""
    if platforms is None:
        return True
    if len(platforms) == 0:
        return False
    return key in platforms
