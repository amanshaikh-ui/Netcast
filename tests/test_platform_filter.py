from linksearch.platform_filter import (
    ALLOWED_PLATFORMS,
    normalize_platform_list,
    wants_platform,
)


def test_normalize_none_is_all():
    assert normalize_platform_list(None) is None


def test_normalize_filters_unknown():
    out = normalize_platform_list(["Youtube", "bogus", "Reddit"])
    assert out == ["Youtube", "Reddit"]


def test_wants_none_means_all():
    assert wants_platform(None, "Youtube") is True


def test_wants_empty_none():
    assert wants_platform([], "Youtube") is False


def test_allowed_count():
    assert len(ALLOWED_PLATFORMS) == 6
