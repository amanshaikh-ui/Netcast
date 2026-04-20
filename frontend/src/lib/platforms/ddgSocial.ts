import { search, SafeSearchType } from "duck-duck-scrape";

import type { CandidateLink, ProductInput, SearchSettings } from "../types";
import {
  buildPlatformSearchQueries,
  urlMatchesSiteHost,
} from "./googleCse";

const MAX_DDG_QUERIES = 4;
const DDG_MS = 350;

function sleep(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}

async function searchSiteDdg(
  settings: SearchSettings,
  product: ProductInput,
  queries: string[],
  siteHost: string,
  platformKeyword: string,
  mediaLabel: string
): Promise<CandidateLink[]> {
  if (!settings.ddgSocialEnabled) return [];

  const searchQueries = buildPlatformSearchQueries(
    platformKeyword,
    product,
    queries
  ).slice(0, MAX_DDG_QUERIES);
  const cap = settings.maxResultsPerPlatform;
  const out: CandidateLink[] = [];
  const seen = new Set<string>();
  const brand = product.brand.trim();
  const sku = product.sku.trim();
  const productName = product.productName.trim();

  for (const q of searchQueries) {
    if (out.length >= cap) break;
    const fullQ = `site:${siteHost} ${q}`.slice(0, 400);
    try {
      await sleep(DDG_MS);
      const data = await search(fullQ, {
        safeSearch: SafeSearchType.MODERATE,
      });
      for (const r of data.results ?? []) {
        if (out.length >= cap) break;
        const url = String(r.url ?? "").trim();
        if (!url || seen.has(url)) continue;
        if (!urlMatchesSiteHost(url, siteHost)) continue;
        seen.add(url);
        out.push({
          media: mediaLabel,
          brand,
          url,
          sku,
          productName,
          title: String(r.title ?? ""),
          snippet: String(r.description ?? "").replace(/<\/?b>/gi, "").slice(0, 500),
          score: 0,
          sourceQuery: fullQ,
        });
      }
    } catch {
      /* DDG may rate-limit or block; continue */
    }
  }

  return out;
}

export function searchTiktokDdg(
  s: SearchSettings,
  p: ProductInput,
  q: string[]
) {
  return searchSiteDdg(s, p, q, "tiktok.com", "Tiktok", "Tiktok");
}

export function searchFacebookDdg(
  s: SearchSettings,
  p: ProductInput,
  q: string[]
) {
  return searchSiteDdg(s, p, q, "facebook.com", "Facebook", "Facebook");
}

export function searchInstagramDdg(
  s: SearchSettings,
  p: ProductInput,
  q: string[]
) {
  return searchSiteDdg(s, p, q, "instagram.com", "Instagram", "Instagram");
}

/** YouTube via DuckDuckGo `site:youtube.com` — works without API key or yt-dlp (e.g. Vercel). */
export function searchYoutubeDdg(
  s: SearchSettings,
  p: ProductInput,
  q: string[]
) {
  return searchSiteDdg(s, p, q, "youtube.com", "YouTube", "Youtube");
}

/** Shorts-shaped URLs only (`/shorts/`). Pairs with DDG when yt-dlp is unavailable. */
export async function searchYoutubeShortsDdg(
  s: SearchSettings,
  p: ProductInput,
  q: string[]
): Promise<CandidateLink[]> {
  const rows = await searchSiteDdg(
    s,
    p,
    q,
    "youtube.com",
    "YouTube Shorts",
    "YoutubeShorts"
  );
  return rows.filter((r) => /\/shorts\//i.test(r.url));
}
