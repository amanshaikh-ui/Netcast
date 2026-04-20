export interface ProductInput {
  brand: string;
  sku: string;
  productName: string;
}

export interface CandidateLink {
  media: string;
  brand: string;
  url: string;
  sku: string;
  productName: string;
  title: string;
  snippet: string;
  score: number;
  sourceQuery?: string;
  /** TikTok @handle or Instagram/Facebook slug when inferrable from URL */
  authorHandle?: string;
  /** Extra text from OG/meta/OCR merged into evidence scoring */
  evidenceExtra?: string;
}

export interface SearchSettings {
  youtubeApiKey: string;
  /** Innertube search via yt-dlp when true (no YouTube Data API key required for this path). */
  youtubeUseYtdlp: boolean;
  /** When false, skip Google Programmable Search (TikTok / Facebook / Instagram CSE). */
  googleCseEnabled: boolean;
  /** DuckDuckGo site: search for TT/FB/IG (no Google CSE). Default on. */
  ddgSocialEnabled: boolean;
  /** Run Python `tiktok_direct_stdio` subprocess when TikTok is selected (same as CLI direct TikTok). Default on; set false to skip. */
  tiktokDirectPython: boolean;
  /** Per-media bucket: prefer rows whose title+snippet contain SKU when any match exists. Default on; set false for looser captions. */
  strictSkuFilter: boolean;
  googleCseApiKey: string;
  googleCseId: string;
  groqApiKey: string;
  groqModel: string;
  redditUserAgent: string;
  maxResultsPerPlatform: number;
  requestTimeoutSeconds: number;
}

/** Aligned with Python API: snake_case keys for classification block. */
export interface ProductClassification {
  product_type: string;
  expected_platforms: string[];
  missing_platforms_reason: Record<string, string>;
}

export interface PipelineMeta {
  objective?: string;
  productArchetype?: string;
  platformCoverageLikelihood?: Record<string, string>;
  crawlBudgets?: Record<string, string>;
  foundPlatforms?: string[];
  missingPlatforms?: string[];
  explanation?: string;
  classification?: ProductClassification;
  /** True when archetype is social_heavy, TikTok was requested, and zero TikTok rows returned. */
  debug_social_heavy_zero_tiktok?: boolean;
  /** Batch CSV: number of products processed; classification may reflect first row only. */
  batchProductCount?: number;
  /** Full meta per product when batch CSV was used. */
  perProduct?: PipelineMeta[];
}

export interface PipelineResult {
  rows: CandidateLink[];
  warnings: string[];
  meta?: PipelineMeta | { perProduct: PipelineMeta[] };
}

/** Optional per-run tuning (API → pipeline). Dates are YYYY-MM-DD (Shorts upload date filter). */
export interface PipelineRunOptions {
  shortsDateAfter?: string;
  shortsDateBefore?: string;
}
