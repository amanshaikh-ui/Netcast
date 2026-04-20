"""
Browser-first evidence merge (Crawl4AI-inspired): unify OG + embedded hints before scoring.

Called after raw HTML fetch so scoring still runs only on enriched rows.
"""

from __future__ import annotations

import json
import re
from html import unescape
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from linksearch.models import CandidateLink

_JSONLD = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.I | re.S,
)
_HASHTAG = re.compile(r"#([\w]{2,40})\b")


def merge_from_html(candidate: "CandidateLink", html: str) -> None:
    """Extract caption-like text, hashtags, and JSON-LD hints into title/snippet/evidence_extra."""
    blocks: list[str] = []
    for m in _JSONLD.finditer(html[:400_000]):
        raw = (m.group(1) or "").strip()
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            for k in ("headline", "name", "description", "caption"):
                v = data.get(k)
                if isinstance(v, str) and len(v) > 3:
                    blocks.append(v[:800])
            auth = data.get("author")
            if isinstance(auth, dict) and auth.get("name"):
                candidate.author_handle = str(auth["name"])[:120]
        elif isinstance(data, list):
            for item in data[:3]:
                if isinstance(item, dict) and item.get("description"):
                    blocks.append(str(item["description"])[:800])

    text_for_tags = " ".join(blocks + [candidate.title, candidate.snippet])[:4000]
    tags = sorted(set(t.lower() for t in _HASHTAG.findall(text_for_tags)))
    if tags:
        tag_line = " ".join(f"#{t}" for t in tags[:24])
        candidate.snippet = f"{candidate.snippet} {tag_line}".strip()[:2000]

    if blocks and not candidate.title.strip():
        candidate.title = unescape(blocks[0])[:500]

    if len(blocks) > 1 or tags:
        extra_bits = {"jsonld_fields": len(blocks), "hashtags": tags[:24]}
        prev = (candidate.evidence_extra or "").strip()
        candidate.evidence_extra = (prev + " " + json.dumps(extra_bits))[:4000].strip()
