import type { CandidateLink, ProductInput, SearchSettings } from "../types";
import { primaryQuery } from "../scoring";

const REDDIT_SEARCH = "https://www.reddit.com/search.json";

async function redditFetch(
  settings: SearchSettings,
  q: string,
  cap: number
): Promise<{ url: string; title: string; snippet: string }[]> {
  const params = new URLSearchParams({
    q,
    limit: String(Math.min(25, cap)),
    sort: "relevance",
    raw_json: "1",
  });
  const r = await fetch(`${REDDIT_SEARCH}?${params}`, {
    headers: { "User-Agent": settings.redditUserAgent },
    next: { revalidate: 0 },
  });
  if (r.status === 429) return [];
  if (!r.ok) throw new Error(`Reddit ${r.status}: ${await r.text()}`);
  const data = (await r.json()) as {
    data?: { children?: Array<{ data?: Record<string, unknown> }> };
  };
  const children = data.data?.children ?? [];
  const seen = new Set<string>();
  const out: { url: string; title: string; snippet: string }[] = [];
  for (const ch of children) {
    const d = ch.data ?? {};
    const permalink = String(d.permalink ?? "");
    if (!permalink) continue;
    const url = `https://www.reddit.com${permalink}`.split("?")[0];
    if (seen.has(url)) continue;
    seen.add(url);
    out.push({
      url,
      title: String(d.title ?? ""),
      snippet: String(d.selftext ?? "").slice(0, 500),
    });
  }
  return out;
}

export async function searchReddit(
  settings: SearchSettings,
  product: ProductInput
): Promise<CandidateLink[]> {
  const sku = product.sku.trim();
  const brand = product.brand.trim();
  const cap = settings.maxResultsPerPlatform * 3;

  // Fix 2: Use quoted SKU so Reddit must match it exactly.
  // Fix 4: Two-pass — strict first, broad fallback if < 2 results.
  const strictQ = sku ? `"${sku}" ${brand}` : primaryQuery(product).slice(0, 300);
  const broadQ = primaryQuery(product).slice(0, 300);

  let hits = await redditFetch(settings, strictQ, cap);

  // Fall back to broad query when strict yields too few results
  if (hits.length < 2 && strictQ !== broadQ) {
    hits = await redditFetch(settings, broadQ, cap);
  }

  const seen = new Set<string>();
  const out: CandidateLink[] = [];
  for (const h of hits) {
    if (seen.has(h.url)) continue;
    seen.add(h.url);
    out.push({
      media: "Reddit",
      brand,
      url: h.url,
      sku,
      productName: product.productName.trim(),
      title: h.title,
      snippet: h.snippet,
      score: 0,
      sourceQuery: strictQ,
    });
    if (out.length >= settings.maxResultsPerPlatform * 2) break;
  }
  return out;
}
