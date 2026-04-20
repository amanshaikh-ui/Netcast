from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ProductInput:
    """One row from the input CSV."""

    brand: str
    sku: str
    product_name: str = ""

    def normalized_brand(self) -> str:
        return self.brand.strip()

    def primary_query(self) -> str:
        parts = [self.normalized_brand(), self.sku.strip()]
        if self.product_name.strip():
            parts.append(self.product_name.strip())
        return " ".join(parts)


@dataclass
class CandidateLink:
    """A discovered URL before final ranking."""

    media: str  # Youtube, Tiktok, Reddit, Facebook, Instagram
    brand: str
    url: str
    sku: str
    product_name: str
    title: str = ""
    snippet: str = ""
    score: float = 0.0
    source_query: str = ""
    author_handle: str = ""
    evidence_extra: str = ""


@dataclass
class PipelineResult:
    rows: list[CandidateLink] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: Run metadata: objective, archetype, coverage_prediction, crawl_budgets, explanation, discovery_events, …
    meta: dict[str, object] = field(default_factory=dict)
