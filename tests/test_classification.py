from linksearch.classification import (
    build_classification_block,
    expected_platform_slugs,
    social_heavy_zero_tiktok_warn,
)
from linksearch.coverage_prediction import predict_platform_coverage
from linksearch.models import ProductInput


def test_expected_platforms_uses_high_medium():
    p = ProductInput(brand="Test", sku="X", product_name="beauty serum")
    cov = predict_platform_coverage(p, "social_heavy")
    req = {"Youtube", "Tiktok", "Facebook"}
    ex = expected_platform_slugs(cov, req)
    assert "youtube" in ex and "tiktok" in ex


def test_social_heavy_zero_tiktok_warn_disabled():
    """User-facing DEBUG TikTok note is off; hook stays no-op."""
    req = {"Tiktok", "Youtube"}
    found = {"Youtube"}
    ok, msg = social_heavy_zero_tiktok_warn("social_heavy", req, found, 0)
    assert ok is False and msg is None


def test_build_classification_shape():
    p = ProductInput(brand="Ryobi", sku="A", product_name="drill")
    cov = predict_platform_coverage(p, "medium_social")
    cls = build_classification_block(set(), set(cov.keys()), cov, "medium_social", {k: 3 for k in cov})
    assert cls["product_type"] == "medium_social"
    assert "expected_platforms" in cls and isinstance(cls["expected_platforms"], list)
    assert "missing_platforms_reason" in cls
