"""
Product alias generation: social discovery runs on short phrases and hashtags,
not only the catalog line. Used before all fetchers (DDG, CSE, native).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from linksearch.models import ProductInput

_RE_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]+")


def _slug_compact(s: str, max_len: int = 40) -> str:
    s = _RE_NON_ALNUM.sub("", s.strip().lower())
    return s[:max_len] if s else ""


def _normalize_name(name: str) -> str:
    name = re.sub(r"\s+", " ", name.strip().lower())
    return name


def _tokens_no_stop(s: str) -> list[str]:
    stop = frozenset(
        "the a an and or for with from kit tool tools cordless battery volt".split()
    )
    out: list[str] = []
    for t in re.split(r"[^\w]+", s.lower()):
        if len(t) > 1 and t not in stop:
            out.append(t)
    return out


@dataclass
class ProductAliases:
    brand: str
    sku: str
    normalized_product_name: str
    compact_sku_slug: str
    hashtags: list[str] = field(default_factory=list)
    pass1_queries: list[str] = field(default_factory=list)
    pass2_queries: list[str] = field(default_factory=list)
    pass3_queries: list[str] = field(default_factory=list)
    family_queries: list[str] = field(default_factory=list)
    all_search_queries: list[str] = field(default_factory=list)


def _dedupe(qs: list[str], cap: int | None = None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for q in qs:
        t = " ".join(q.split()).strip()
        if not t:
            continue
        k = t.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(t[:400])
        if cap is not None and len(out) >= cap:
            break
    return out


def build_product_aliases(product: ProductInput) -> ProductAliases:
    brand = product.normalized_brand()
    sku = product.sku.strip()
    pname = product.product_name.strip()
    norm_name = _normalize_name(pname) if pname else ""

    compact_sku = _slug_compact(sku, 24) or sku.lower()

    hashtags: list[str] = []
    for h in (
        _slug_compact(brand, 20),
        compact_sku,
        _slug_compact(f"{brand}{sku}", 30),
        _slug_compact(f"{brand}{norm_name.replace(' ', '')}", 35) if norm_name else "",
    ):
        if len(h) >= 2:
            hashtags.append(f"#{h}")

    # Pass 1 — broad recall
    pass1: list[str] = []
    if brand and norm_name:
        pass1.append(f"{brand} {norm_name}")
        pass1.append(norm_name)
    if brand and sku:
        pass1.append(f"{brand} {sku}")
    if sku:
        pass1.append(sku)
    if brand:
        pass1.append(f"{brand} product review")
    primary = product.primary_query()
    if primary and primary not in pass1:
        pass1.insert(0, primary)

    # Pass 2 — social / intent
    tails = (
        "review",
        "unboxing",
        "demo",
        "first look",
        "worth it",
        "vs",
    )
    pass2: list[str] = []
    if brand and norm_name:
        short = " ".join(_tokens_no_stop(norm_name)[:5])
        if short:
            pass2.append(f"{short} {tails[0]}")
            pass2.append(f"{brand} {short} {tails[4]}")
    if brand:
        for t in tails:
            pass2.append(f"{brand} {t}")
    if sku:
        pass2.append(f"{sku} review")

    family: list[str] = []
    if brand and norm_name:
        toks = _tokens_no_stop(norm_name)
        if len(toks) >= 2:
            family.append(f"{brand} {' '.join(toks[:5])}")
            family.append(" ".join(toks[:4]))
        if "cfm" in norm_name or "volt" in norm_name or "v " in norm_name:
            family.append(f"{brand} leaf blower")
    if brand:
        family.append(f"{brand} blower review")

    # Pass 3 — seed expansion slots (filled at runtime when first hits exist)
    pass3: list[str] = []

    family = _dedupe(family, cap=10)
    all_flat = _dedupe(pass1 + pass2 + family + hashtags + [primary], cap=56)
    pass1 = _dedupe(pass1, cap=12)
    pass2 = _dedupe(pass2, cap=16)

    return ProductAliases(
        brand=brand,
        sku=sku,
        normalized_product_name=norm_name,
        compact_sku_slug=compact_sku,
        hashtags=_dedupe(hashtags, cap=12),
        pass1_queries=pass1,
        pass2_queries=pass2,
        pass3_queries=pass3,
        family_queries=family,
        all_search_queries=all_flat,
    )


def expand_queries_with_seed(
    base: ProductAliases, seed_captions: list[str], cap: int = 8
) -> list[str]:
    """Derive extra queries from captions of first good hits (pass 3)."""
    extra: list[str] = []
    for cap_text in seed_captions[:5]:
        toks = [t for t in _tokens_no_stop(cap_text) if len(t) > 3][:4]
        if toks:
            extra.append(" ".join(toks))
    base.pass3_queries = _dedupe(base.pass3_queries + extra, cap=cap)
    return _dedupe(base.all_search_queries + base.pass3_queries, cap=52)
