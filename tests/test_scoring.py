from linksearch.models import CandidateLink, ProductInput
from linksearch.scoring import (
    apply_heuristic_and_sort,
    heuristic_score,
    normalize_media_label,
)


def test_heuristic_prefers_sku_in_title():
    p = ProductInput(brand="Ryobi", sku="P322K1N", product_name="Nailer Kit")
    high = heuristic_score(p, "Ryobi P322K1N nailer review", "")
    low = heuristic_score(p, "Random cordless tools chat", "")
    assert high > low


def test_normalize_media_from_url():
    assert normalize_media_label("https://www.youtube.com/watch?v=abc", "X") == "Youtube"


def test_apply_heuristic_sorts():
    p = ProductInput(brand="Ryobi", sku="ABC123", product_name="")
    cands = [
        CandidateLink(
            media="Reddit",
            brand="Ryobi",
            url="https://www.reddit.com/r/x/1",
            sku="ABC123",
            product_name="",
            title="unrelated",
            snippet="",
        ),
        CandidateLink(
            media="Reddit",
            brand="Ryobi",
            url="https://www.reddit.com/r/x/2",
            sku="ABC123",
            product_name="",
            title="Ryobi ABC123 review",
            snippet="",
        ),
    ]
    out = apply_heuristic_and_sort(p, cands)
    assert out[0].url.endswith("/2")
