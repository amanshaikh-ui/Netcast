import { buildProductAliases, type ProductAliases } from "./aliases";
import type { CandidateLink, ProductInput } from "./types";

const REVIEW_WORDS = new Set([
  "review",
  "unboxing",
  "demo",
  "first look",
  "worth it",
  "vs",
  "comparison",
]);

const COMPETITORS = ["dewalt", "milwaukee", "makita", "bosch"];

export function primaryQuery(p: ProductInput): string {
  const parts = [p.brand.trim(), p.sku.trim()];
  if (p.productName.trim()) parts.push(p.productName.trim());
  return parts.join(" ");
}

export function extractAuthorHandle(url: string): string {
  const u = url.toLowerCase();
  let m = /tiktok\.com\/@([^/?#]+)/.exec(u);
  if (m) return m[1].toLowerCase();
  m = /instagram\.com\/([^/?#]+)/.exec(u);
  if (m && !["p", "reel", "tv", "stories"].includes(m[1])) {
    return m[1].toLowerCase().replace(/^@/, "");
  }
  m = /facebook\.com\/([^/?#]+)/.exec(u);
  if (m && !["watch", "reel", "groups", "share", "story.php"].includes(m[1])) {
    return m[1].toLowerCase();
  }
  return "";
}

export function evidenceBasedScore(
  product: ProductInput,
  aliases: ProductAliases,
  c: CandidateLink
): number {
  const blob = `${c.title} ${c.snippet} ${c.evidenceExtra ?? ""}`.toLowerCase();
  const sku = product.sku.trim().toLowerCase();
  const brand = product.brand.trim().toLowerCase();
  let score = 0;

  if (sku && blob.includes(sku)) score += 10;
  else if (sku && new RegExp(sku.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).test(blob)) {
    score += 7;
  }

  const pq = primaryQuery(product).toLowerCase();
  if (pq.length > 5 && blob.includes(pq)) score += 8;

  let aliasHit = false;
  for (const phrase of [
    ...aliases.pass1Queries.slice(0, 8),
    ...aliases.familyQueries.slice(0, 6),
    ...aliases.pass2Queries.slice(0, 8),
  ]) {
    const pl = phrase.toLowerCase().trim();
    if (pl.length > 4 && blob.includes(pl)) {
      score += 6;
      aliasHit = true;
      break;
    }
  }
  if (!aliasHit) {
    for (const h of aliases.hashtags) {
      const hx = h.toLowerCase().replace(/^#/, "");
      if (hx.length > 2 && (blob.includes(hx) || blob.includes(`#${hx}`))) {
        score += 6;
        break;
      }
    }
  }

  if (brand && sku && blob.includes(brand) && blob.includes(sku)) score += 5;

  for (const h of aliases.hashtags) {
    if (blob.includes(h.toLowerCase())) {
      score += 4;
      break;
    }
  }

  const handle = c.authorHandle ?? extractAuthorHandle(c.url);
  if (handle && brand && brand.replace(/\s/g, "") && handle.replace(/_/g, "").includes(brand.replace(/\s/g, ""))) {
    score += 3;
  }

  for (const w of REVIEW_WORDS) {
    if (blob.includes(w)) {
      score += 2;
      break;
    }
  }

  const path = (() => {
    try {
      return new URL(c.url).pathname.toLowerCase();
    } catch {
      return "";
    }
  })();
  if (path.includes("/reel/") || path.includes("/video/") || path.includes("/watch")) {
    score += 2;
  }

  if (brand) {
    for (const comp of COMPETITORS) {
      if (blob.includes(comp) && !blob.includes(brand)) {
        score -= 5;
        break;
      }
    }
  }

  return score;
}

export function applyAccountAffinity(product: ProductInput, candidates: CandidateLink[]): void {
  const brand = product.brand.trim().toLowerCase();
  if (!brand || candidates.length < 2) return;

  const byHandle = new Map<string, CandidateLink[]>();
  for (const c of candidates) {
    const h = (c.authorHandle ?? extractAuthorHandle(c.url)).toLowerCase();
    if (!h) continue;
    const list = byHandle.get(h) ?? [];
    list.push(c);
    byHandle.set(h, list);
  }

  for (const [, rows] of byHandle) {
    if (rows.length < 2) continue;
    const hits = rows.filter((c) =>
      `${c.title} ${c.snippet}`.toLowerCase().includes(brand)
    ).length;
    if (hits >= 2) {
      const bonus = Math.min(9, 3 * (hits - 1));
      for (const c of rows) {
        if (`${c.title} ${c.snippet}`.toLowerCase().includes(brand)) {
          c.score = c.score + bonus;
        }
      }
    }
  }
}

export function normalizeMediaLabel(url: string, defaultMedia: string): string {
  try {
    const u = new URL(url);
    const host = u.hostname.toLowerCase();
    const path = (u.pathname || "").toLowerCase();
    if (host.includes("youtube.com") && path.includes("/shorts/")) return "YoutubeShorts";
    if (host.includes("youtube.com") || host.includes("youtu.be")) return "Youtube";
    if (host.includes("tiktok.com")) return "Tiktok";
    if (host.includes("reddit.com")) return "Reddit";
    if (host.includes("facebook.com")) return "Facebook";
    if (host.includes("instagram.com")) return "Instagram";
  } catch {
    /* ignore */
  }
  return defaultMedia;
}

function applyCreatorTopicalityPenalty(
  product: ProductInput,
  candidates: CandidateLink[]
): void {
  const brand = product.brand.trim().toLowerCase();
  const comps = ["dewalt", "milwaukee", "makita", "bosch"];
  const byHandle = new Map<string, CandidateLink[]>();
  for (const c of candidates) {
    const h = (c.authorHandle ?? extractAuthorHandle(c.url)).toLowerCase();
    if (!h) continue;
    const list = byHandle.get(h) ?? [];
    list.push(c);
    byHandle.set(h, list);
  }
  for (const rows of byHandle.values()) {
    if (rows.length < 2) continue;
    const blob = rows.map((c) => `${c.title} ${c.snippet}`.toLowerCase()).join(" ");
    const ch = comps.filter((co) => blob.includes(co)).length;
    const bh = blob.includes(brand) ? 1 : 0;
    if (ch >= 2 && bh === 0) {
      for (const c of rows) c.score -= 4;
    }
  }
}

export function applyHeuristicAndSort(
  product: ProductInput,
  candidates: CandidateLink[],
  aliases?: ProductAliases
): CandidateLink[] {
  const pa = aliases ?? buildProductAliases(product);
  const scored = candidates.map((c) => {
    const authorHandle = extractAuthorHandle(c.url);
    const next: CandidateLink = {
      ...c,
      media: normalizeMediaLabel(c.url, c.media),
      authorHandle,
      score: evidenceBasedScore(product, pa, { ...c, authorHandle }),
    };
    return next;
  });
  applyAccountAffinity(product, scored);
  applyCreatorTopicalityPenalty(product, scored);
  scored.sort((a, b) => b.score - a.score);
  return scored;
}

/** @deprecated Use evidenceBasedScore; kept for tests importing heuristic naming */
export function heuristicScore(
  product: ProductInput,
  title: string,
  snippet: string
): number {
  const pa = buildProductAliases(product);
  return evidenceBasedScore(
    product,
    pa,
    { media: "", brand: "", url: "", sku: "", productName: "", title, snippet, score: 0 }
  );
}
