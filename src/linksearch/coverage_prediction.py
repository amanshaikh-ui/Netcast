"""
Heuristic platform coverage likelihood (high / medium / low) — sets crawl depth expectations,
not a guarantee of links. Used with product archetype for crawl budgets.
"""

from __future__ import annotations

import re
from typing import Literal

from linksearch.models import ProductInput

Likelihood = Literal["high", "medium", "low"]

_SOCIAL_HEAVY = frozenset(
    """beauty makeup skincare hair phone iphone android kitchen gadget lifestyle
    fitness yoga sneaker shoe apparel fashion perfume cologne game gaming headset
    """.split()
)
_MEDIUM = frozenset(
    """tool drill mower vacuum blower washer dryer appliance refrigerator tv speaker
    laptop tablet watch earbuds blender air fryer bike bicycle car auto
    """.split()
)
_LOW = frozenset(
    """industrial part oem gasket bearing bulk sku component replacement filter element
    fastener rivet seal hydraulic pneumatic
    """.split()
)
_FB_LOW = frozenset(
    """gen z tiktok teen beauty phone gaming""".split()
)  # informal signal only


def classify_product_archetype(product: ProductInput) -> str:
    blob = f"{product.normalized_brand()} {product.sku} {product.product_name}".lower()
    toks = set(re.split(r"[^\w]+", blob)) - {""}
    if toks & _SOCIAL_HEAVY:
        return "social_heavy"
    if toks & _LOW or (len(product.sku.strip()) > 12 and re.match(r"^[A-Z0-9\-]+$", product.sku.strip())):
        return "low_social"
    if toks & _MEDIUM:
        return "medium_social"
    return "medium_social"


def predict_platform_coverage(product: ProductInput, archetype: str) -> dict[str, Likelihood]:
    """Per-platform public-indexing likelihood for this product category (heuristic)."""
    pn = product.product_name.lower()
    blob = f"{pn} {product.sku.lower()}"

    def yt() -> Likelihood:
        if archetype == "social_heavy":
            return "high"
        if "review" in pn or "how to" in pn or archetype == "medium_social":
            return "medium"
        if archetype == "low_social":
            return "low"
        return "medium"

    def reddit_() -> Likelihood:
        if any(x in blob for x in ("gaming", "pc", "gpu", "laptop", "phone", "android", "tool", "car")):
            return "high"
        if archetype == "low_social":
            return "low"
        return "medium"

    def tiktok_() -> Likelihood:
        if archetype == "social_heavy":
            return "high"
        if archetype == "low_social":
            return "low"
        return "medium"

    def ig() -> Likelihood:
        if archetype == "social_heavy":
            return "high"
        if archetype == "low_social":
            return "low"
        return "medium"

    def fb() -> Likelihood:
        if archetype == "social_heavy" and not any(t in blob for t in _FB_LOW):
            return "medium"
        if archetype == "low_social":
            return "low"
        return "low" if archetype == "social_heavy" else "medium"

    return {
        "Youtube": yt(),
        "YoutubeShorts": yt(),
        "Reddit": reddit_(),
        "Tiktok": tiktok_(),
        "Instagram": ig(),
        "Facebook": fb(),
    }
