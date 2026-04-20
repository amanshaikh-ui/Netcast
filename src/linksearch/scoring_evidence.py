"""Evidence-first scoring: SKU and aliases boost relevance, not a hard gate."""

from __future__ import annotations

import re
from urllib.parse import urlparse

from linksearch.aliases import ProductAliases, build_product_aliases
from linksearch.models import CandidateLink, ProductInput

_REVIEW_WORDS = frozenset(
    ("review", "unboxing", "demo", "first look", "worth it", "vs", "comparison")
)


def extract_author_handle(url: str, media: str) -> str:
    u = url.lower()
    m = re.search(r"tiktok\.com/@([^/?#]+)", u)
    if m:
        return m.group(1).lower()
    m = re.search(r"instagram\.com/([^/?#]+)", u)
    if m and m.group(1) not in ("p", "reel", "tv", "stories"):
        return m.group(1).lower().lstrip("@")
    m = re.search(r"facebook\.com/([^/?#]+)", u)
    if m and m.group(1) not in ("watch", "reel", "groups", "share", "story.php"):
        return m.group(1).lower()
    return ""


def evidence_based_score(
    product: ProductInput,
    aliases: ProductAliases,
    title: str,
    snippet: str,
    url: str,
    media: str,
    ocr_blob: str = "",
) -> float:
    blob = f"{title} {snippet} {ocr_blob}".lower()
    sku = product.sku.strip().lower()
    brand = product.normalized_brand().lower()
    score = 0.0

    if sku and sku in blob:
        score += 10.0
    elif sku and re.search(re.escape(sku), blob):
        score += 7.0

    pq = product.primary_query().strip().lower()
    if pq and len(pq) > 5 and pq in blob:
        score += 8.0

    alias_matched = False
    for phrase in aliases.pass1_queries[:8] + aliases.family_queries[:6] + aliases.pass2_queries[:8]:
        pl = phrase.lower().strip()
        if len(pl) > 4 and pl in blob:
            score += 6.0
            alias_matched = True
            break
    if not alias_matched:
        for h in aliases.hashtags:
            hx = h.lower().lstrip("#")
            if len(hx) > 2 and (hx in blob or f"#{hx}" in blob):
                score += 6.0
                break

    if brand and sku and brand in blob and sku in blob:
        score += 5.0

    for h in aliases.hashtags:
        hx = h.lower()
        if hx in blob:
            score += 4.0
            break

    handle = extract_author_handle(url, media)
    if handle and brand and brand.replace(" ", "") in handle.replace("_", ""):
        score += 3.0

    for w in _REVIEW_WORDS:
        if w in blob:
            score += 2.0
            break

    path = (urlparse(url).path or "").lower()
    if "/reel/" in path or "/video/" in path or "/watch" in path:
        score += 2.0

    competitors = ("dewalt", "milwaukee", "makita", "bosch")
    if brand:
        for comp in competitors:
            if comp in blob and brand not in blob:
                score -= 5.0
                break

    return score


def apply_account_affinity(
    product: ProductInput, candidates: list[CandidateLink]
) -> None:
    """Boost scores when the same handle repeatedly mentions the brand."""
    brand = product.normalized_brand().lower()
    if not brand or len(candidates) < 2:
        return

    by_handle: dict[str, list[CandidateLink]] = {}
    for c in candidates:
        h = (c.author_handle or extract_author_handle(c.url, c.media)).lower()
        if not h:
            continue
        by_handle.setdefault(h, []).append(c)

    for handle, rows in by_handle.items():
        if len(rows) < 2:
            continue
        hits = sum(
            1
            for c in rows
            if brand in f"{c.title} {c.snippet}".lower()
        )
        if hits >= 2:
            bonus = min(9.0, 3.0 * (hits - 1))
            for c in rows:
                if brand in f"{c.title} {c.snippet}".lower():
                    c.score = float(c.score) + bonus


def score_and_sort_candidates(
    product: ProductInput,
    candidates: list[CandidateLink],
    aliases: ProductAliases | None = None,
) -> list[CandidateLink]:
    from linksearch.scoring import normalize_media_label

    pa = aliases or build_product_aliases(product)
    for c in candidates:
        c.media = normalize_media_label(c.url, c.media)
        c.author_handle = extract_author_handle(c.url, c.media)
        extra = (c.evidence_extra or "").strip()
        c.score = evidence_based_score(
            product,
            pa,
            c.title,
            c.snippet,
            c.url,
            c.media,
            ocr_blob=extra,
        )

    apply_account_affinity(product, candidates)
    apply_creator_topicality_penalty(product, candidates)
    candidates.sort(key=lambda x: float(x.score), reverse=True)
    return candidates


def apply_creator_topicality_penalty(
    product: ProductInput, candidates: list[CandidateLink]
) -> None:
    """Penalty when a creator cluster looks off-category (competitors, no brand)."""
    brand = product.normalized_brand().lower()
    comps = ("dewalt", "milwaukee", "makita", "bosch")
    by_handle: dict[str, list[CandidateLink]] = {}
    for c in candidates:
        h = (c.author_handle or extract_author_handle(c.url, c.media)).lower()
        if not h:
            continue
        by_handle.setdefault(h, []).append(c)

    for rows in by_handle.values():
        if len(rows) < 2:
            continue
        blob = " ".join(f"{c.title} {c.snippet}".lower() for c in rows)
        ch = sum(1 for co in comps if co in blob)
        bh = 1 if brand in blob else 0
        if ch >= 2 and bh == 0:
            for c in rows:
                c.score = float(c.score) - 4.0
