from __future__ import annotations

import re
from urllib.parse import urlparse

from linksearch.models import CandidateLink, ProductInput


def _tokens(s: str) -> set[str]:
    s = re.sub(r"[^\w\s]", " ", s.lower())
    return {t for t in s.split() if len(t) > 1}


def heuristic_score(product: ProductInput, title: str, snippet: str) -> float:
    """Lightweight relevance score using SKU/brand/product tokens in title+snippet."""
    blob = f"{title} {snippet}".lower()
    sku = product.sku.strip().lower()
    brand = product.normalized_brand().lower()
    score = 0.0

    if sku and sku in blob:
        score += 3.0
    elif sku:
        # partial SKU match (alphanumeric runs)
        if re.search(re.escape(sku), blob):
            score += 2.5

    if brand and brand in blob:
        score += 1.5

    pname_tokens = _tokens(product.product_name)
    if pname_tokens:
        blob_tokens = _tokens(blob)
        overlap = len(pname_tokens & blob_tokens)
        score += min(2.0, 0.4 * overlap)

    return score


def normalize_media_label(url: str, default_media: str) -> str:
    """Map URL host to output Media label matching TTI sample casing."""
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return default_media
    if "youtube.com" in host or "youtu.be" in host:
        if "/shorts/" in (urlparse(url).path or "").lower():
            return "YoutubeShorts"
        return "Youtube"
    if "tiktok.com" in host:
        return "Tiktok"
    if "reddit.com" in host:
        return "Reddit"
    if "facebook.com" in host:
        return "Facebook"
    if "instagram.com" in host:
        return "Instagram"
    return default_media


def apply_heuristic_and_sort(
    product: ProductInput,
    candidates: list[CandidateLink],
    aliases: object | None = None,
) -> list[CandidateLink]:
    """Stage-2 evidence scoring (aliases + boosts); stage-1 discovery is intentionally broad."""
    from linksearch.scoring_evidence import score_and_sort_candidates

    return score_and_sort_candidates(product, candidates, aliases)  # type: ignore[arg-type]
