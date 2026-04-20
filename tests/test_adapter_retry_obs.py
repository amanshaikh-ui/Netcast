"""Pack builders and observation schema (no network)."""

from linksearch.adapter_retry import build_instagram_retry_packs, build_tiktok_retry_packs
from linksearch.aliases import build_product_aliases
from linksearch.models import ProductInput
from linksearch.observability import AdapterObservation


def test_build_tiktok_packs_non_empty() -> None:
    p = ProductInput(brand="Acme", sku="X-1", product_name="Leaf Blower")
    pa = build_product_aliases(p)
    packs = build_tiktok_retry_packs(pa, [])
    labels = [x[0] for x in packs]
    assert "primary" in labels
    assert all(len(qs) > 0 for _, qs in packs)


def test_build_instagram_packs() -> None:
    p = ProductInput(brand="Acme", sku="Y2", product_name="Tool")
    pa = build_product_aliases(p)
    packs = build_instagram_retry_packs(pa, [])
    assert len(packs) >= 1


def test_adapter_observation_to_dict() -> None:
    o = AdapterObservation(
        query_used="q",
        adapter_name="test",
        runtime_region="US",
        visible_results_count=2,
        network_payload_count=5,
        candidates_extracted=2,
        candidates_rejected=1,
        rejection_reason="",
        seeds_expanded=0,
        retry_count=1,
        extra={"k": 1},
    )
    d = o.to_dict()
    assert d["adapter_name"] == "test"
    assert d["network_payload_count"] == 5
    assert d["extra"]["k"] == 1
