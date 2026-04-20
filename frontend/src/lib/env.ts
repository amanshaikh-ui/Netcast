import type { SearchSettings } from "./types";

export function loadSearchSettings(): SearchSettings {
  const falsy = (v: string | undefined) =>
    v === "0" || v?.toLowerCase() === "false";
  const explicitTrue = (v: string | undefined) =>
    v?.toLowerCase() === "true" || v === "1";
  return {
    youtubeApiKey: process.env.YOUTUBE_API_KEY?.trim() ?? "",
    youtubeUseYtdlp: !falsy(process.env.YOUTUBE_USE_YTDLP),
    /** Default off — set GOOGLE_CSE_ENABLED=true to use Programmable Search. */
    googleCseEnabled: explicitTrue(process.env.GOOGLE_CSE_ENABLED),
    /** Default on — set DDG_SOCIAL_ENABLED=false to skip DuckDuckGo social discovery. */
    ddgSocialEnabled: !falsy(process.env.DDG_SOCIAL_ENABLED),
    /**
     * TikTok via Python subprocess (local only). On Vercel there is no Python — default off
     * unless TIKTOK_DIRECT_PYTHON=true is set explicitly (still unlikely to work serverless).
     */
    tiktokDirectPython:
      process.env.VERCEL === "1"
        ? explicitTrue(process.env.TIKTOK_DIRECT_PYTHON)
        : !falsy(process.env.TIKTOK_DIRECT_PYTHON),
    /** Off unless STRICT_SKU_FILTER=true — prefer evidence scoring (alias/SKU boosts) instead. */
    strictSkuFilter: explicitTrue(process.env.STRICT_SKU_FILTER),
    googleCseApiKey: process.env.GOOGLE_CSE_API_KEY?.trim() ?? "",
    googleCseId: process.env.GOOGLE_CSE_ID?.trim() ?? "",
    groqApiKey: process.env.GROQ_API_KEY?.trim() ?? "",
    groqModel: process.env.GROQ_MODEL?.trim() || "llama-3.3-70b-versatile",
    redditUserAgent:
      process.env.REDDIT_USER_AGENT?.trim() ||
      "SocialMediaLinkCollector/1.0 (Educational; contact: https://example.com)",
    maxResultsPerPlatform: Math.max(
      1,
      parseInt(process.env.MAX_RESULTS_PER_PLATFORM ?? "5", 10) || 5
    ),
    requestTimeoutSeconds:
      parseFloat(process.env.REQUEST_TIMEOUT_SECONDS ?? "30") || 30,
  };
}

export function youtubeEnabled(s: SearchSettings): boolean {
  return Boolean(s.youtubeApiKey);
}

export function cseEnabled(s: SearchSettings): boolean {
  if (!s.googleCseEnabled) return false;
  return Boolean(s.googleCseApiKey && s.googleCseId);
}

export function groqEnabled(s: SearchSettings): boolean {
  return Boolean(s.groqApiKey);
}
