import type { CandidateLink, ProductInput, SearchSettings } from "../types";
import { primaryQuery } from "../scoring";

const CSE_URL = "https://www.googleapis.com/customsearch/v1";

/** Cap CSE calls per product per platform (each call uses API quota). */
const MAX_CSE_QUERIES_PER_SITE = 4;

function sanitizeSkuForQuote(sku: string): string {
  return sku.trim().replace(/"/g, "");
}

function dedupeSearchQueries(candidates: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const c of candidates) {
    const t = c.trim();
    if (!t) continue;
    const k = t.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(t.slice(0, 350));
  }
  return out;
}

/** e.g. tiktok.com matches www.tiktok.com, m.facebook.com matches facebook.com */
export function urlMatchesSiteHost(url: string, siteHost: string): boolean {
  try {
    const h = new URL(url).hostname.toLowerCase();
    const s = siteHost.toLowerCase();
    return h === s || h.endsWith(`.${s}`);
  } catch {
    return false;
  }
}

/**
 * Natural-language Google queries (no `site:`), e.g. `Tiktok Ryobi "R4331"`.
 * Results are filtered to URLs on `siteHost` after retrieval.
 */
export function buildPlatformSearchQueries(
  platformKeyword: string,
  product: ProductInput,
  queries: string[]
): string[] {
  const brand = product.brand.trim();
  const sku = sanitizeSkuForQuote(product.sku);
  const kw = platformKeyword.trim();
  const candidates: string[] = [];

  if (sku) {
    const strict =
      brand.length > 0
        ? `${kw} ${brand} "${sku}"`
        : `${kw} "${sku}"`;
    candidates.push(strict.slice(0, 350));
  }

  for (const q of queries.slice(0, 3)) {
    const t = q.trim();
    if (!t) continue;
    candidates.push(`${kw} ${t}`.slice(0, 350));
  }

  candidates.push(`${kw} ${primaryQuery(product)}`.slice(0, 350));

  return dedupeSearchQueries(candidates).slice(0, MAX_CSE_QUERIES_PER_SITE);
}

async function cseQuery(
  settings: SearchSettings,
  searchQ: string,
  num: number
): Promise<Record<string, unknown>[]> {
  const params = new URLSearchParams({
    key: settings.googleCseApiKey,
    cx: settings.googleCseId,
    q: searchQ,
    num: String(Math.min(10, Math.max(1, num))),
  });
  const r = await fetch(`${CSE_URL}?${params}`, { next: { revalidate: 0 } });
  const text = await r.text();
  let body: { error?: { message?: string }; items?: Record<string, unknown>[] };
  try {
    body = JSON.parse(text) as typeof body;
  } catch {
    throw new Error(`Custom Search: invalid JSON (${r.status})`);
  }
  if (!r.ok) {
    const msg = body.error?.message ?? text.slice(0, 200);
    throw new Error(`Custom Search ${r.status}: ${msg}`);
  }
  return (body.items ?? []) as Record<string, unknown>[];
}

export async function searchSite(
  settings: SearchSettings,
  product: ProductInput,
  queries: string[],
  siteHost: string,
  platformKeyword: string,
  mediaLabel: string
): Promise<CandidateLink[]> {
  if (!settings.googleCseEnabled || !settings.googleCseApiKey || !settings.googleCseId)
    return [];

  const searchQueries = buildPlatformSearchQueries(
    platformKeyword,
    product,
    queries
  );
  const cap = settings.maxResultsPerPlatform;
  const out: CandidateLink[] = [];
  const seen = new Set<string>();

  for (const searchQ of searchQueries) {
    if (out.length >= cap) break;
    let items: Record<string, unknown>[];
    try {
      items = await cseQuery(settings, searchQ, 10);
    } catch {
      continue;
    }
    for (const it of items) {
      if (out.length >= cap) break;
      const url = String(it.link ?? "");
      const title = String(it.title ?? "");
      const snippet = String(it.snippet ?? "");
      if (!url || seen.has(url)) continue;
      if (!urlMatchesSiteHost(url, siteHost)) continue;
      seen.add(url);
      out.push({
        media: mediaLabel,
        brand: product.brand.trim(),
        url,
        sku: product.sku.trim(),
        productName: product.productName.trim(),
        title,
        snippet,
        score: 0,
        sourceQuery: searchQ,
      });
    }
  }

  return out;
}

export function searchTiktok(
  s: SearchSettings,
  p: ProductInput,
  q: string[]
) {
  return searchSite(s, p, q, "tiktok.com", "Tiktok", "Tiktok");
}
export function searchFacebook(
  s: SearchSettings,
  p: ProductInput,
  q: string[]
) {
  return searchSite(s, p, q, "facebook.com", "Facebook", "Facebook");
}
export function searchInstagram(
  s: SearchSettings,
  p: ProductInput,
  q: string[]
) {
  return searchSite(s, p, q, "instagram.com", "Instagram", "Instagram");
}
