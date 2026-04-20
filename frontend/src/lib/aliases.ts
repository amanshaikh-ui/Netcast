import type { ProductInput } from "./types";
import { primaryQuery } from "./scoring";

function slugCompact(s: string, maxLen = 40): string {
  return s.replace(/[^a-zA-Z0-9]+/g, "").toLowerCase().slice(0, maxLen);
}

function normalizeName(name: string): string {
  return name.trim().toLowerCase().replace(/\s+/g, " ");
}

function tokensNoStop(s: string): string[] {
  const stop = new Set(
    "the a an and or for with from kit tool tools cordless battery volt".split(" ")
  );
  const out: string[] = [];
  for (const t of s.toLowerCase().split(/[^\w]+/)) {
    if (t.length > 1 && !stop.has(t)) out.push(t);
  }
  return out;
}

export interface ProductAliases {
  pass1Queries: string[];
  pass2Queries: string[];
  familyQueries: string[];
  hashtags: string[];
  allSearchQueries: string[];
}

function dedupe(qs: string[], cap?: number): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const q of qs) {
    const t = q.split(/\s+/).join(" ").trim();
    if (!t) continue;
    const k = t.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(t.slice(0, 400));
    if (cap !== undefined && out.length >= cap) break;
  }
  return out;
}

export function buildProductAliases(p: ProductInput): ProductAliases {
  const brand = p.brand.trim();
  const sku = p.sku.trim();
  const pname = p.productName.trim();
  const normName = pname ? normalizeName(pname) : "";

  const compactSku = slugCompact(sku, 24) || sku.toLowerCase();
  const hashtags: string[] = [];
  for (const h of [
    slugCompact(brand, 20),
    compactSku,
    slugCompact(`${brand}${sku}`, 30),
    normName ? slugCompact(`${brand}${normName.replace(/\s/g, "")}`, 35) : "",
  ]) {
    if (h.length >= 2) hashtags.push(`#${h}`);
  }

  const pass1: string[] = [];
  if (brand && normName) {
    pass1.push(`${brand} ${normName}`);
    pass1.push(normName);
  }
  if (brand && sku) pass1.push(`${brand} ${sku}`);
  if (sku) pass1.push(sku);
  if (brand) pass1.push(`${brand} product review`);
  const prim = primaryQuery(p);
  if (prim && !pass1.includes(prim)) pass1.unshift(prim);

  const tails = ["review", "unboxing", "demo", "first look", "worth it", "vs"] as const;
  const pass2: string[] = [];
  if (brand && normName) {
    const short = tokensNoStop(normName).slice(0, 5).join(" ");
    if (short) {
      pass2.push(`${short} ${tails[0]}`);
      pass2.push(`${brand} ${short} ${tails[4]}`);
    }
  }
  if (brand) {
    for (const t of tails) pass2.push(`${brand} ${t}`);
  }
  if (sku) pass2.push(`${sku} review`);

  const family: string[] = [];
  if (brand && normName) {
    const toks = tokensNoStop(normName);
    if (toks.length >= 2) {
      family.push(`${brand} ${toks.slice(0, 5).join(" ")}`);
      family.push(toks.slice(0, 4).join(" "));
    }
    if (normName.includes("cfm") || normName.includes("volt"))
      family.push(`${brand} leaf blower`);
  }
  if (brand) family.push(`${brand} blower review`);

  const allFlat = dedupe(
    [...pass1, ...pass2, ...dedupe(family, 10), ...hashtags, prim].filter(Boolean) as string[],
    56
  );

  return {
    pass1Queries: dedupe(pass1, 12),
    pass2Queries: dedupe(pass2, 16),
    familyQueries: dedupe(family, 10),
    hashtags: dedupe(hashtags, 12),
    allSearchQueries: allFlat,
  };
}
