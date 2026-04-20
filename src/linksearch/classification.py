"""
Structured classification for API consumers: product_type, expected_platforms,
missing_platforms_reason (slug keys). Does not imply every platform will have links.
"""

from __future__ import annotations

# Canonical API slugs (lowercase)
LABEL_TO_SLUG = {
    "Youtube": "youtube",
    "YoutubeShorts": "youtube_shorts",
    "Reddit": "reddit",
    "Tiktok": "tiktok",
    "Instagram": "instagram",
    "Facebook": "facebook",
}

SLUG_TO_LABEL = {v: k for k, v in LABEL_TO_SLUG.items()}

ORDER = ("Youtube", "YoutubeShorts", "Reddit", "Tiktok", "Instagram", "Facebook")


def label_to_slug(label: str) -> str:
    return LABEL_TO_SLUG.get(label, label.lower())


def expected_platform_slugs(
    coverage: dict[str, str],
    requested_labels: set[str],
) -> list[str]:
    """
    Platforms where we predict non-trivial public indexing (high/medium),
    intersected with what the user asked to search.
    """
    out: list[str] = []
    for lab in ORDER:
        if lab not in requested_labels:
            continue
        li = coverage.get(lab, "medium")
        if li in ("high", "medium"):
            out.append(LABEL_TO_SLUG[lab])
    if not out:
        for lab in ORDER:
            if lab in requested_labels:
                out.append(LABEL_TO_SLUG[lab])
    return out


def missing_platform_reasons(
    found_labels: set[str],
    requested_labels: set[str],
    coverage: dict[str, str],
    archetype: str,
    cap_by_label: dict[str, int],
) -> dict[str, str]:
    """Short reasons keyed by slug (e.g. instagram) for requested-but-empty platforms."""
    missing = requested_labels - found_labels
    out: dict[str, str] = {}
    for lab in ORDER:
        if lab not in missing:
            continue
        slug = LABEL_TO_SLUG[lab]
        if cap_by_label.get(lab, 0) <= 0:
            out[slug] = "crawl skipped (low predicted yield for this product)"
            continue
        li = coverage.get(lab, "medium")
        if lab == "Facebook":
            out[slug] = (
                "weak discoverability"
                if li != "low"
                else "low public coverage"
            )
        elif lab in ("Tiktok", "Instagram"):
            out[slug] = "low public coverage" if li == "low" else "weak text match vs thumbnail-heavy posts"
        elif lab == "Reddit":
            out[slug] = "subreddit timing / niche posts" if li != "low" else "low public coverage"
        elif lab in ("Youtube", "YoutubeShorts"):
            out[slug] = "thin descriptions or niche uploads" if li != "low" else "low public coverage"
        else:
            out[slug] = "low public coverage"
        if archetype == "social_heavy" and lab == "Facebook":
            out[slug] = "weak discoverability"
    return out


def build_classification_block(
    found_labels: set[str],
    requested_labels: set[str],
    coverage: dict[str, str],
    archetype: str,
    cap_by_label: dict[str, int],
) -> dict[str, object]:
    return {
        "product_type": archetype,
        "expected_platforms": expected_platform_slugs(coverage, requested_labels),
        "missing_platforms_reason": missing_platform_reasons(
            found_labels, requested_labels, coverage, archetype, cap_by_label
        ),
    }


def social_heavy_zero_tiktok_warn(
    archetype: str,
    requested_labels: set[str],
    found_labels: set[str],
    tiktok_row_count: int,
) -> tuple[bool, str | None]:
    """Reserved hook; user-facing DEBUG TikTok note disabled (no noisy warnings in UI)."""
    return False, None
