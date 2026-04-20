"""Instagram adapter: hashtag/profile-oriented direct crawl first; DDG/CSE in pipeline order after."""

from linksearch.platforms.instagram_direct import search_instagram_direct_sync

__all__ = ["search_instagram_direct_sync"]
