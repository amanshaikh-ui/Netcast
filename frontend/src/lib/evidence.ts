import type { CandidateLink } from "./types";

const OG_TITLE =
  /<meta[^>]+property=["']og:title["'][^>]+content=["']([^"']+)["']/i;
const OG_DESC =
  /<meta[^>]+property=["']og:description["'][^>]+content=["']([^"']+)["']/i;
const TITLE_TAG = /<title[^>]*>([^<]{1,500})<\/title>/i;

function unescapeHtml(s: string): string {
  return s
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'");
}

export async function enrichCandidateEvidence(c: CandidateLink): Promise<CandidateLink> {
  const url = c.url.trim();
  if (!url.startsWith("http")) return c;
  const social =
    url.includes("tiktok.com") ||
    url.includes("instagram.com") ||
    url.includes("facebook.com");
  if (!social) return c;

  try {
    const r = await fetch(url, {
      method: "GET",
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
        Accept: "text/html",
      },
      signal: AbortSignal.timeout(8000),
    });
    if (!r.ok) return c;
    const html = (await r.text()).slice(0, 800_000);

    let title = "";
    let desc = "";
    let m = OG_TITLE.exec(html);
    if (m) title = unescapeHtml(m[1].trim());
    if (!title) {
      const t = TITLE_TAG.exec(html);
      if (t) title = unescapeHtml(t[1].trim());
    }
    m = OG_DESC.exec(html);
    if (m) desc = unescapeHtml(m[1].trim());

    const extra = [title, desc].filter(Boolean).join(" | ").slice(0, 1200);
    const snippet = [c.snippet, desc].filter(Boolean).join(" ").slice(0, 2000);
    return {
      ...c,
      title: c.title?.trim() || title.slice(0, 500),
      snippet,
      evidenceExtra: extra,
    };
  } catch {
    return c;
  }
}

export async function enrichCandidatesForSocial(
  candidates: CandidateLink[],
  maxConcurrent = 5
): Promise<CandidateLink[]> {
  if (!candidates.length) return [];
  const out: CandidateLink[] = [];
  for (let i = 0; i < candidates.length; i += maxConcurrent) {
    const batch = candidates.slice(i, i + maxConcurrent);
    const done = await Promise.all(batch.map((c) => enrichCandidateEvidence(c)));
    out.push(...done);
  }
  return out;
}
