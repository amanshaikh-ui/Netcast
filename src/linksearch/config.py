from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    youtube_api_key: str = ""
    google_cse_api_key: str = ""
    google_cse_id: str = ""
    groq_api_key: str = ""
    groq_model: str = "llama-3.3-70b-versatile"

    reddit_user_agent: str = Field(
        default="SocialMediaLinkCollector/1.0 (Educational project; +https://example.com)"
    )

    max_results_per_platform: int = 5
    request_timeout_seconds: float = 30.0

    #: Use Innertube search via yt-dlp (no YouTube Data API key). Merges with API results when both run.
    youtube_use_ytdlp: bool = True
    #: Google Programmable Search (TikTok/Facebook/Instagram). Default off — use direct TikTok/Instagram + yt-dlp instead.
    google_cse_enabled: bool = False

    #: Direct TikTok video search (install: pip install -e ".[direct]" and playwright install chromium). Default on.
    tiktok_direct_enabled: bool = True
    tiktok_ms_token: str = ""
    tiktok_browser: str = "chromium"
    #: Use Playwright-native TikTok adapter v3 (search page + XHR). Default off — also needs ``pip install playwright``.
    tiktok_playwright_v3: bool = False
    tiktok_playwright_scroll_rounds: int = 6
    tiktok_playwright_headed: bool = False
    tiktok_playwright_expand_profile: bool = True

    #: Instagram hashtag crawl via instaloader (install: pip install -e ".[direct]"). Default on.
    instagram_direct_enabled: bool = True
    instagram_session_file: str = ""
    #: Use profile-first Instagram v2 (username guesses + reel/p links; hashtag fallback).
    instagram_profile_first_v2: bool = True
    #: Seed expansion budget (v3): split between TikTok handle expansion and IG profile pull.
    seed_expansion_budget_units: int = 20
    seed_expand_v3_enabled: bool = True
    seed_expand_hashtag_cluster: bool = False

    #: DuckDuckGo ``site:`` search for TikTok / Facebook / Instagram (no Google CSE). Default on.
    ddg_social_enabled: bool = True

    #: Playwright async scrape of a single Facebook Page (open + /videos + scroll). Default off.
    facebook_playwright_enabled: bool = False
    #: Full Page URL, e.g. ``https://www.facebook.com/ninjakitchen``. Empty = derive from brand slug.
    facebook_page_url: str = ""

    #: Brave Search API fallback (native + DDG first). Set ``BRAVE_SEARCH_ENABLED=true`` and API key.
    brave_search_enabled: bool = False
    brave_search_api_key: str = ""

    #: Legacy: early SKU narrowing (reduces recall). Off by default — use evidence scoring instead.
    strict_sku_filter: bool = False

    def youtube_enabled(self) -> bool:
        return bool(self.youtube_api_key.strip())

    def cse_enabled(self) -> bool:
        if not self.google_cse_enabled:
            return False
        return bool(self.google_cse_api_key.strip() and self.google_cse_id.strip())

    def groq_enabled(self) -> bool:
        return bool(self.groq_api_key.strip())


def load_settings() -> Settings:
    return Settings()
