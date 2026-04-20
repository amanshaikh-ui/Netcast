"""Tests for CSE natural-language queries and URL filtering."""

from linksearch.models import ProductInput
from linksearch.platforms.google_cse import (
    MAX_CSE_QUERIES_PER_SITE,
    build_platform_search_queries,
    url_matches_site_host,
)


def test_build_platform_search_queries_quoted_sku_first():
    p = ProductInput(brand="Ryobi", sku="R4331", product_name="Router")
    qs = build_platform_search_queries("Tiktok", p, ['Ryobi "R4331" review'])
    assert qs[0] == 'Tiktok Ryobi "R4331"'
    assert not any(q.startswith("site:") for q in qs)
    assert len(qs) <= MAX_CSE_QUERIES_PER_SITE


def test_build_platform_search_queries_dedupes():
    p = ProductInput(brand="Ryobi", sku="R4331", product_name="")
    primary = p.primary_query()
    qs = build_platform_search_queries("Instagram", p, [primary])
    seen = set()
    for q in qs:
        assert q.lower() not in seen
        seen.add(q.lower())


def test_build_platform_search_queries_no_brand():
    p = ProductInput(brand="", sku="ABC123", product_name="")
    qs = build_platform_search_queries("Facebook", p, [])
    assert qs[0] == 'Facebook "ABC123"'


def test_url_matches_site_host():
    assert url_matches_site_host("https://www.tiktok.com/@x/video/1", "tiktok.com")
    assert url_matches_site_host("https://tiktok.com/foo", "tiktok.com")
    assert not url_matches_site_host("https://google.com/search?q=tiktok", "tiktok.com")
    assert url_matches_site_host("https://m.facebook.com/story.php", "facebook.com")
