import { effectiveCap, type Budget } from "./coveragePrediction";

const LABEL_TO_SLUG: Record<string, string> = {
  Youtube: "youtube",
  YoutubeShorts: "youtube_shorts",
  Reddit: "reddit",
  Tiktok: "tiktok",
  Instagram: "instagram",
  Facebook: "facebook",
};

const ORDER = [
  "Youtube",
  "YoutubeShorts",
  "Reddit",
  "Tiktok",
  "Instagram",
  "Facebook",
] as const;

export function expectedPlatformSlugs(
  coverage: Record<string, string>,
  requested: Set<string>
): string[] {
  const out: string[] = [];
  for (const lab of ORDER) {
    if (!requested.has(lab)) continue;
    const li = coverage[lab] ?? "medium";
    if (li === "high" || li === "medium") {
      out.push(LABEL_TO_SLUG[lab]);
    }
  }
  if (!out.length) {
    for (const lab of ORDER) {
      if (requested.has(lab)) out.push(LABEL_TO_SLUG[lab]);
    }
  }
  return out;
}

export function missingPlatformReasons(
  found: Set<string>,
  requested: Set<string>,
  coverage: Record<string, string>,
  archetype: string,
  capByLabel: Record<string, number>
): Record<string, string> {
  const missing = [...requested].filter((x) => !found.has(x));
  const out: Record<string, string> = {};
  for (const lab of ORDER) {
    if (!missing.includes(lab)) continue;
    const slug = LABEL_TO_SLUG[lab];
    if ((capByLabel[lab] ?? 0) <= 0) {
      out[slug] = "crawl skipped (low predicted yield for this product)";
      continue;
    }
    const li = coverage[lab] ?? "medium";
    if (lab === "Facebook") {
      out[slug] = li === "low" ? "low public coverage" : "weak discoverability";
    } else if (lab === "Tiktok" || lab === "Instagram") {
      out[slug] =
        li === "low"
          ? "low public coverage"
          : "weak text match vs thumbnail-heavy posts";
    } else if (lab === "Reddit") {
      out[slug] =
        li === "low" ? "low public coverage" : "subreddit timing / niche posts";
    } else {
      out[slug] =
        li === "low" ? "low public coverage" : "thin descriptions or niche uploads";
    }
    if (archetype === "social_heavy" && lab === "Facebook") {
      out[slug] = "weak discoverability";
    }
  }
  return out;
}

export function buildClassification(
  found: Set<string>,
  requested: Set<string>,
  coverage: Record<string, string>,
  archetype: string,
  budgets: Record<string, Budget>,
  baseCap: number
): {
  product_type: string;
  expected_platforms: string[];
  missing_platforms_reason: Record<string, string>;
} {
  const capByLabel: Record<string, number> = {};
  for (const lab of ORDER) {
    const b = budgets[lab];
    if (b) capByLabel[lab] = effectiveCap(baseCap, b);
  }
  return {
    product_type: archetype,
    expected_platforms: expectedPlatformSlugs(coverage, requested),
    missing_platforms_reason: missingPlatformReasons(
      found,
      requested,
      coverage,
      archetype,
      capByLabel
    ),
  };
}

