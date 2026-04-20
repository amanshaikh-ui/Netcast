import type { CandidateLink, ProductInput, SearchSettings } from "../types";
import { primaryQuery } from "../scoring";

const YOUTUBE_SEARCH = "https://www.googleapis.com/youtube/v3/search";

export async function searchYoutube(
  settings: SearchSettings,
  product: ProductInput,
  queries: string[]
): Promise<CandidateLink[]> {
  if (!settings.youtubeApiKey) return [];
  const qText = queries.length ? queries.slice(0, 3).join(" ") : primaryQuery(product);
  const params = new URLSearchParams({
    part: "snippet",
    type: "video",
    maxResults: String(settings.maxResultsPerPlatform),
    q: qText.slice(0, 280),
    key: settings.youtubeApiKey,
  });
  const r = await fetch(`${YOUTUBE_SEARCH}?${params}`, {
    next: { revalidate: 0 },
  });
  if (!r.ok) throw new Error(`YouTube ${r.status}: ${await r.text()}`);
  const data = (await r.json()) as {
    items?: Array<{
      id?: { videoId?: string };
      snippet?: { title?: string; description?: string };
    }>;
  };
  const out: CandidateLink[] = [];
  const seen = new Set<string>();
  for (const item of data.items ?? []) {
    const vid = item.id?.videoId;
    const sn = item.snippet ?? {};
    if (!vid) continue;
    const url = `https://www.youtube.com/watch?v=${vid}`;
    if (seen.has(url)) continue;
    seen.add(url);
    out.push({
      media: "Youtube",
      brand: product.brand.trim(),
      url,
      sku: product.sku.trim(),
      productName: product.productName.trim(),
      title: sn.title ?? "",
      snippet: (sn.description ?? "").slice(0, 500),
      score: 0,
      sourceQuery: qText,
    });
  }
  return out;
}
