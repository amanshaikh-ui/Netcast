/** Align with Python canonical_url: stable keys for dedupe after enrichment. */

const UTM = new Set([
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_term",
  "utm_content",
  "fbclid",
  "gclid",
]);

export function canonicalizeSocialUrl(url: string): string {
  try {
    const u = new URL(url.trim());
    const host = u.hostname.toLowerCase();
    const path = u.pathname;

    if (host.includes("tiktok.com")) {
      const m = /\/video\/(\d+)/.exec(path);
      if (m) return `${u.protocol}//${host}/video/${m[1]}`;
    }

    if (host.includes("instagram.com")) {
      const m = /\/(p|reel|tv)\/([^/?]+)/.exec(path);
      if (m) return `${u.protocol}//${host}/${m[1]}/${m[2]}`;
    }

    if (host.includes("youtube.com")) {
      const shorts = /\/shorts\/([^/?]+)/.exec(path);
      if (shorts) {
        return `${u.protocol}//${host}/shorts/${shorts[1]}`;
      }
      const v = u.searchParams.get("v");
      if (v) return `${u.protocol}//${host}${path}?v=${encodeURIComponent(v)}`;
    }

    const params = new URLSearchParams(u.search);
    for (const k of [...params.keys()]) {
      if (UTM.has(k.toLowerCase())) params.delete(k);
    }
    const q = params.toString();
    return `${u.protocol}//${host}${path}${q ? `?${q}` : ""}`;
  } catch {
    return url;
  }
}
