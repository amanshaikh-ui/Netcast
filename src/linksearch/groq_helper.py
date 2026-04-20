from __future__ import annotations

import json
import re

from groq import Groq

from linksearch.aliases import ProductAliases, build_product_aliases
from linksearch.config import Settings
from linksearch.models import CandidateLink, ProductInput


def build_search_queries(
    settings: Settings,
    product: ProductInput,
    aliases: ProductAliases | None = None,
) -> list[str]:
    """Return ordered search phrases (aliases first); uses Groq when configured."""
    pa = aliases or build_product_aliases(product)
    fallback = list(pa.all_search_queries)
    if not fallback:
        fallback = [
            product.primary_query(),
            f"{product.normalized_brand()} {product.sku.strip()}",
            product.sku.strip(),
        ]
    if not settings.groq_enabled():
        return _dedupe_keep_order(fallback)

    client = Groq(api_key=settings.groq_api_key)
    alias_preview = ", ".join(pa.hashtags[:8] + pa.pass1_queries[:5])
    prompt = f"""You help find social media posts about a retail product.
Given:
- Brand: {product.normalized_brand()}
- SKU: {product.sku.strip()}
- Product name: {product.product_name.strip() or "(unknown)"}
- Suggested aliases / hashtags / short phrases: {alias_preview}

Return a JSON object with key "queries": an array of 4 to 8 SHORT search query strings
for TikTok Instagram Facebook YouTube style search. Prefer short nicknames, model codes,
hashtag-style tokens without the #, review/unboxing phrases — NOT only the full catalog title.
No explanation, JSON only."""

    try:
        chat = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=400,
        )
        text = (chat.choices[0].message.content or "").strip()
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            obj = json.loads(m.group())
            arr = obj.get("queries") if isinstance(obj, dict) else None
            if isinstance(arr, list):
                cleaned = [str(x).strip() for x in arr if str(x).strip()]
                return _dedupe_keep_order(cleaned + fallback)
    except Exception:
        pass
    return _dedupe_keep_order(fallback)


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out[:48]


def groq_rerank_candidates(
    settings: Settings,
    product: ProductInput,
    candidates: list[CandidateLink],
    top_n: int,
) -> list[CandidateLink]:
    """Optional second pass: Groq assigns 0.0-1.0 relevance; merges with heuristic score."""
    if not settings.groq_enabled() or not candidates:
        return candidates[:top_n]

    client = Groq(api_key=settings.groq_api_key)
    slim = [
        {
            "i": i,
            "media": c.media,
            "url": c.url,
            "title": c.title[:400],
            "snippet": c.snippet[:400],
        }
        for i, c in enumerate(candidates[:25])
    ]
    prompt = f"""Product: brand={product.normalized_brand()} sku={product.sku.strip()} name={product.product_name.strip()}
Candidates (JSON): {json.dumps(slim)}
Return JSON object {{"scores": [{{"i": number, "score": number between 0 and 1}}]}} with one score per candidate index i.
Score by likely relevance to this exact product (not generic brand chat). JSON only."""

    try:
        chat = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=800,
        )
        text = (chat.choices[0].message.content or "").strip()
        m = re.search(r"\{[\s\S]*\}", text)
        if not m:
            return candidates[:top_n]
        obj = json.loads(m.group())
        scores_list = obj.get("scores") if isinstance(obj, dict) else None
        if not isinstance(scores_list, list):
            return candidates[:top_n]
        bonus: dict[int, float] = {}
        for s in scores_list:
            if not isinstance(s, dict):
                continue
            try:
                i = int(s.get("i"))
                bonus[i] = float(s.get("score", 0.0))
            except (TypeError, ValueError):
                continue
        for i, c in enumerate(candidates[:25]):
            c.score = float(c.score) + 2.0 * bonus.get(i, 0.0)
    except Exception:
        return candidates[:top_n]

    candidates = sorted(candidates, key=lambda x: x.score, reverse=True)
    return candidates[:top_n]
