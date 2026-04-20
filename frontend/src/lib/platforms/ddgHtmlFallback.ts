/**
 * duck-duck-scrape often returns nothing on serverless/datacenter IPs.
 * These fallbacks use the same HTML endpoints a browser would hit.
 */

export type HtmlSearchHit = {
  url: string;
  title: string;
  description: string;
};

const UA =
  "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36";

function stripTags(s: string): string {
  return s.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
}

export function normalizeRedirectUrl(href: string): string {
  let h = href.replace(/&amp;/g, "&").trim();
  if (h.startsWith("//")) h = `https:${h}`;
  try {
    const u = new URL(h);
    if (u.hostname.includes("duckduckgo.com") && u.pathname.includes("/l/")) {
      const uddg = u.searchParams.get("uddg");
      if (uddg) return decodeURIComponent(uddg);
    }
  } catch {
    /* keep */
  }
  if (!/^https?:\/\//i.test(h)) return "";
  return h;
}

function parseDdgResultAnchors(html: string): HtmlSearchHit[] {
  const out: HtmlSearchHit[] = [];
  const seen = new Set<string>();
  const patterns = [
    /<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi,
    /<a[^>]+href="([^"]+)"[^>]+class="[^"]*result__a[^"]*"[^>]*>([\s\S]*?)<\/a>/gi,
    /<a[^>]+class="[^"]*result-link[^"]*"[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi,
  ];
  for (const re of patterns) {
    let m: RegExpExecArray | null;
    re.lastIndex = 0;
    while ((m = re.exec(html)) !== null) {
      const url = normalizeRedirectUrl(m[1]);
      if (!url) continue;
      if (seen.has(url)) continue;
      seen.add(url);
      out.push({
        url,
        title: stripTags(m[2]).slice(0, 400),
        description: "",
      });
    }
  }
  return out;
}

/** DuckDuckGo classic HTML form (POST). */
export async function ddgHtmlPostSearch(query: string): Promise<HtmlSearchHit[]> {
  const body = new URLSearchParams({ q: query });
  try {
    const r = await fetch("https://html.duckduckgo.com/html/", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": UA,
        Accept: "text/html,application/xhtml+xml",
      },
      body: body.toString(),
      signal: AbortSignal.timeout(28_000),
      cache: "no-store",
    });
    if (!r.ok) return [];
    const html = await r.text();
    return parseDdgResultAnchors(html);
  } catch {
    return [];
  }
}

/** Bing web results (HTML) — often works when DDG blocks datacenter IPs. */
export async function bingHtmlSearch(query: string): Promise<HtmlSearchHit[]> {
  const url = `https://www.bing.com/search?q=${encodeURIComponent(query)}`;
  try {
    const r = await fetch(url, {
      headers: {
        "User-Agent": UA,
        Accept: "text/html",
      },
      signal: AbortSignal.timeout(28_000),
      cache: "no-store",
    });
    if (!r.ok) return [];
    const html = await r.text();
    const out: HtmlSearchHit[] = [];
    const seen = new Set<string>();
    const re = /<li class="b_algo"[^>]*>[\s\S]*?<h2[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>([\s\S]*?)<\/a>/gi;
    let m: RegExpExecArray | null;
    while ((m = re.exec(html)) !== null) {
      const u = m[1].replace(/&amp;/g, "&");
      if (!/^https?:\/\//i.test(u) || seen.has(u)) continue;
      seen.add(u);
      out.push({
        url: u,
        title: stripTags(m[2]).slice(0, 400),
        description: "",
      });
    }
    return out;
  } catch {
    return [];
  }
}

/** DDG HTML + Bing HTML, deduped — use alongside or instead of duck-duck-scrape. */
export async function searchHtmlStack(query: string): Promise<HtmlSearchHit[]> {
  const seen = new Set<string>();
  const merged: HtmlSearchHit[] = [];

  const push = (hits: HtmlSearchHit[]) => {
    for (const h of hits) {
      const u = h.url.trim();
      if (!u || seen.has(u)) continue;
      seen.add(u);
      merged.push(h);
    }
  };

  push(await ddgHtmlPostSearch(query));
  push(await bingHtmlSearch(query));

  return merged;
}
