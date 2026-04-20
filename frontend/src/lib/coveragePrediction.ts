import type { ProductInput } from "./types";

export type Likelihood = "high" | "medium" | "low";

const SOCIAL_HEAVY = new Set(
  "beauty makeup skincare hair phone iphone android kitchen gadget lifestyle fitness yoga sneaker".split(" ")
);
const MEDIUM = new Set(
  "tool drill mower vacuum blower washer dryer appliance tv speaker laptop watch earbuds".split(" ")
);
const LOW = new Set(
  "industrial part oem gasket bearing bulk component replacement filter fastener rivet seal hydraulic".split(" ")
);

export function classifyProductArchetype(p: ProductInput): string {
  const blob = `${p.brand} ${p.sku} ${p.productName}`.toLowerCase();
  const toks = new Set(blob.split(/[^\w]+/).filter(Boolean));
  if ([...toks].some((t) => SOCIAL_HEAVY.has(t))) return "social_heavy";
  if (p.sku.trim().length > 12 && /^[A-Z0-9\-]+$/i.test(p.sku.trim())) return "low_social";
  if ([...toks].some((t) => LOW.has(t))) return "low_social";
  if ([...toks].some((t) => MEDIUM.has(t))) return "medium_social";
  return "medium_social";
}

export function predictPlatformCoverage(
  p: ProductInput,
  archetype: string
): Record<string, Likelihood> {
  const pn = p.productName.toLowerCase();
  const yt =
    archetype === "social_heavy"
      ? "high"
      : archetype === "low_social"
        ? "low"
        : "medium";
  return {
    Youtube: yt,
    YoutubeShorts: yt,
    Reddit: /gaming|pc|gpu|tool|phone|car/.test(pn) ? "high" : archetype === "low_social" ? "low" : "medium",
    Tiktok:
      archetype === "social_heavy" ? "high" : archetype === "low_social" ? "low" : "medium",
    Instagram:
      archetype === "social_heavy" ? "high" : archetype === "low_social" ? "low" : "medium",
    Facebook:
      archetype === "social_heavy"
        ? "medium"
        : archetype === "low_social"
          ? "low"
          : "medium",
  };
}

export type Budget = "skip" | "light" | "medium" | "deep";

const DEPTH: Record<Budget, number> = {
  skip: 0,
  light: 0.45,
  medium: 1,
  deep: 1.65,
};

export function likelihoodToBudget(
  likelihood: Likelihood,
  archetype: string,
  platform: string
): Budget {
  if (likelihood === "low" && archetype === "low_social" && platform === "Facebook")
    return "skip";
  if (
    likelihood === "high" &&
    (platform === "Youtube" || platform === "YoutubeShorts" || platform === "Tiktok")
  )
    return archetype === "social_heavy" || archetype === "medium_social" ? "deep" : "medium";
  if (likelihood === "medium") return "medium";
  return "light";
}

export function buildCrawlPlans(p: ProductInput): {
  archetype: string;
  coverage: Record<string, Likelihood>;
  budgets: Record<string, Budget>;
} {
  const archetype = classifyProductArchetype(p);
  const coverage = predictPlatformCoverage(p, archetype);
  const budgets: Record<string, Budget> = {};
  for (const plat of Object.keys(coverage)) {
    budgets[plat] = likelihoodToBudget(coverage[plat], archetype, plat);
  }
  return { archetype, coverage, budgets };
}

export function effectiveCap(base: number, budget: Budget): number {
  const m = DEPTH[budget];
  if (m <= 0) return 0;
  return Math.max(1, Math.round(base * m));
}

/** Short summary for meta; detailed per-platform reasons live in `classification`. */
export function buildExplanation(
  found: Set<string>,
  requested: Set<string>,
  coverage: Record<string, Likelihood>,
  archetype: string
): string {
  const missing = [...requested].filter((x) => !found.has(x));
  if (!missing.length) {
    return `Archetype ${archetype}: all requested platforms returned at least one link. Public discovery varies by SKU—see the chart for counts.`;
  }
  return `Archetype ${archetype}: no links for ${missing.join(", ")} this run—common for niche SKUs. Use the coverage chart and classification for details.`;
}
