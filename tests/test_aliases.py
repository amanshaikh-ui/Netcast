from linksearch.aliases import build_product_aliases
from linksearch.models import ProductInput


def test_aliases_include_hashtag_and_phrases():
    p = ProductInput(
        brand="Ryobi", sku="RYI6522", product_name="40V 550 CFM blower"
    )
    a = build_product_aliases(p)
    assert any("ryobi" in x.lower() for x in a.pass1_queries)
    assert any("#" in h for h in a.hashtags)
    assert len(a.all_search_queries) >= 3
