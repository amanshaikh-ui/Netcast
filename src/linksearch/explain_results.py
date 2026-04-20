"""Human-readable explanations when some platforms have no links."""

from __future__ import annotations

def build_explanation(
    found_platforms: set[str],
    requested_platforms: set[str],
    coverage: dict[str, str],
    archetype: str,
) -> str:
    """Short summary; per-platform reasons are in classification.missing_platforms_reason."""
    missing = sorted(requested_platforms - found_platforms)
    if not missing:
        return (
            f"Archetype {archetype}: all requested platforms returned at least one link "
            "this run. Public discovery varies by SKU—see classification for structure."
        )
    return (
        f"Archetype {archetype}: no links for {', '.join(missing)} this run—"
        "common for niche SKUs. See classification JSON for platform-level reasons."
    )
