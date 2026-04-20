"""TikTok adapter: native TikTokApi/Playwright search first; DDG/CSE are fallbacks in pipeline."""

from linksearch.platforms.tiktok_direct import search_tiktok_direct

__all__ = ["search_tiktok_direct"]
