"""Crawl budgets (skip/light/medium/deep) from coverage likelihood + product archetype."""

from __future__ import annotations

from typing import Literal

from linksearch.coverage_prediction import Likelihood, classify_product_archetype, predict_platform_coverage
from linksearch.models import ProductInput

Budget = Literal["skip", "light", "medium", "deep"]

_DEPTH_MULT: dict[Budget, float] = {
    "skip": 0.0,
    "light": 0.45,
    "medium": 1.0,
    "deep": 1.65,
}


def likelihood_to_budget(
    likelihood: Likelihood,
    archetype: str,
    platform: str,
) -> Budget:
    if likelihood == "low" and archetype == "low_social" and platform == "Facebook":
        return "skip"
    if likelihood == "low" and platform in ("Facebook", "Instagram"):
        if archetype == "low_social" and platform == "Facebook":
            return "skip"
        return "light"
    if likelihood == "high" and archetype in ("social_heavy", "medium_social"):
        if platform in ("Youtube", "YoutubeShorts", "Tiktok"):
            return "deep"
        return "medium"
    if likelihood == "medium":
        return "medium"
    return "light"


def build_crawl_plan(product: ProductInput) -> tuple[str, dict[str, Likelihood], dict[str, Budget]]:
    archetype = classify_product_archetype(product)
    cov = predict_platform_coverage(product, archetype)
    budgets: dict[str, Budget] = {}
    for plat, li in cov.items():
        budgets[plat] = likelihood_to_budget(li, archetype, plat)
    return archetype, cov, budgets


def effective_cap(base_cap: int, budget: Budget) -> int:
    m = _DEPTH_MULT[budget]
    if m <= 0:
        return 0
    return max(1, int(round(base_cap * m)))


def budget_to_ddg_queries(budget: Budget) -> int:
    """More DDG query variants when crawl depth is higher."""
    return {"skip": 0, "light": 2, "medium": 4, "deep": 6}.get(budget, 4)
