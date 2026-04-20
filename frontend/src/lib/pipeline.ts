import { buildProductAliases } from "./aliases";
import { canonicalizeSocialUrl } from "./canonicalUrl";
import {
  cseEnabled,
  groqEnabled,
  loadSearchSettings,
  youtubeEnabled,
} from "./env";
import { enrichCandidatesForSocial } from "./evidence";
import { buildSearchQueries, groqRerankCandidates } from "./groq";
import { buildClassification } from "./classification";
import { buildCrawlPlans, buildExplanation } from "./coveragePrediction";
import {
  ALLOWED_PLATFORMS,
  normalizePlatformList,
  wantsPlatform,
  type PlatformId,
} from "./platformFilter";
import {
  searchFacebook,
  searchInstagram,
  searchTiktok,
} from "./platforms/googleCse";
import {
  searchFacebookDdg,
  searchInstagramDdg,
  searchTiktokDdg,
} from "./platforms/ddgSocial";
import { searchReddit } from "./platforms/reddit";
import { searchYoutubeMerged } from "./platforms/youtubeMerged";
import { searchYoutubeShortsYtdlp } from "./platforms/youtubeShortsYtdlp";
import { searchTiktokDirectPython } from "./platforms/tiktokDirectPython";
import { applyHeuristicAndSort } from "./scoring";
import type {
  CandidateLink,
  PipelineMeta,
  PipelineResult,
  ProductInput,
  PipelineRunOptions,
} from "./types";

async function discoverForProduct(
  product: ProductInput,
  useGroqRerank: boolean,
  platforms?: string[],
  options?: PipelineRunOptions
): Promise<{ rows: CandidateLink[]; warnings: string[]; meta?: PipelineMeta }> {
  const settings = loadSearchSettings();
  const warnings: string[] = [];
  const pa = buildProductAliases(product);
  const queries = await buildSearchQueries(settings, product, pa);
  const norm = normalizePlatformList(platforms);
  const { archetype, coverage, budgets } = buildCrawlPlans(product);

  if (norm !== undefined && norm.length === 0) {
    return {
      rows: [],
      warnings: ["Select at least one platform."],
      meta: undefined,
    };
  }

  type Entry = { name: string; run: () => Promise<CandidateLink[]> };
  const entries: Entry[] = [];

  /* Native / direct sources first, then DDG, then CSE last. */
  if (wantsPlatform(norm, "Youtube" as PlatformId)) {
    entries.push({
      name: "youtube",
      run: () => searchYoutubeMerged(settings, product, queries),
    });
  }
  if (wantsPlatform(norm, "YoutubeShorts" as PlatformId)) {
    entries.push({
      name: "youtube_shorts_ytdlp",
      run: () =>
        searchYoutubeShortsYtdlp(settings, product, queries, {
          after: options?.shortsDateAfter,
          before: options?.shortsDateBefore,
        }),
    });
  }
  if (wantsPlatform(norm, "Reddit" as PlatformId)) {
    entries.push({
      name: "reddit",
      run: () => searchReddit(settings, product),
    });
  }
  if (wantsPlatform(norm, "Tiktok" as PlatformId) && settings.tiktokDirectPython) {
    entries.push({
      name: "tiktok_direct_python",
      run: () => searchTiktokDirectPython(settings, product, queries),
    });
  }
  if (wantsPlatform(norm, "Tiktok" as PlatformId)) {
    entries.push({
      name: "tiktok_ddg",
      run: () => searchTiktokDdg(settings, product, queries),
    });
  }
  if (wantsPlatform(norm, "Facebook" as PlatformId)) {
    entries.push({
      name: "facebook_ddg",
      run: () => searchFacebookDdg(settings, product, queries),
    });
  }
  if (wantsPlatform(norm, "Instagram" as PlatformId)) {
    entries.push({
      name: "instagram_ddg",
      run: () => searchInstagramDdg(settings, product, queries),
    });
  }
  if (wantsPlatform(norm, "Tiktok" as PlatformId)) {
    entries.push({
      name: "tiktok_cse",
      run: () => searchTiktok(settings, product, queries),
    });
  }
  if (wantsPlatform(norm, "Facebook" as PlatformId)) {
    entries.push({
      name: "facebook_cse",
      run: () => searchFacebook(settings, product, queries),
    });
  }
  if (wantsPlatform(norm, "Instagram" as PlatformId)) {
    entries.push({
      name: "instagram_cse",
      run: () => searchInstagram(settings, product, queries),
    });
  }

  if (entries.length === 0) {
    const requested = new Set(
      norm !== undefined && norm.length > 0 ? norm : [...ALLOWED_PLATFORMS]
    );
    const classification = buildClassification(
      new Set(),
      requested,
      coverage,
      archetype,
      budgets,
      settings.maxResultsPerPlatform
    );
    const w = [`${product.sku}: No matching sources for selected platforms.`];
    return {
      rows: [],
      warnings: w,
      meta: {
        objective: "maximize_realistic_public_coverage",
        productArchetype: archetype,
        platformCoverageLikelihood: coverage as Record<string, string>,
        crawlBudgets: Object.fromEntries(
          Object.entries(budgets).map(([k, v]) => [k, v as string])
        ),
        foundPlatforms: [],
        missingPlatforms: [...requested].sort(),
        explanation: buildExplanation(new Set(), requested, coverage, archetype),
        classification,
        debug_social_heavy_zero_tiktok: false,
      },
    };
  }

  const results = await Promise.allSettled(entries.map((e) => e.run()));
  const merged: CandidateLink[] = [];
  results.forEach((res, i) => {
    const name = entries[i]?.name ?? "unknown";
    if (res.status === "fulfilled") {
      merged.push(...res.value);
    } else {
      const reason =
        res.reason instanceof Error ? res.reason.message : String(res.reason);
      warnings.push(`${product.sku} [${name}]: ${reason}`);
    }
  });

  const enrichCap = Math.min(
    merged.length,
    Math.max(1, settings.maxResultsPerPlatform * 15)
  );
  const head = merged.slice(0, enrichCap);
  const tail = merged.slice(enrichCap);
  const enriched = await enrichCandidatesForSocial(head, 5);
  const withEvidence = [...enriched, ...tail];

  const byMedia = new Map<string, CandidateLink[]>();
  for (const c of withEvidence) {
    const list = byMedia.get(c.media) ?? [];
    list.push(c);
    byMedia.set(c.media, list);
  }

  const perCap = settings.maxResultsPerPlatform;
  const final: CandidateLink[] = [];
  for (const [, items] of byMedia) {
    let ranked = applyHeuristicAndSort(product, items, pa);

    if (settings.strictSkuFilter && product.sku.trim()) {
      const skuLower = product.sku.trim().toLowerCase();
      const skuMatches = ranked.filter((c) =>
        `${c.title} ${c.snippet}`.toLowerCase().includes(skuLower)
      );
      ranked = skuMatches.length > 0 ? skuMatches : ranked;
    }

    if (useGroqRerank && groqEnabled(settings)) {
      ranked = await groqRerankCandidates(settings, product, ranked, perCap * 2);
    } else {
      ranked = ranked.slice(0, perCap * 2);
    }
    final.push(...ranked);
  }

  const best = new Map<string, CandidateLink>();
  for (const c of final.sort((a, b) => b.score - a.score)) {
    const key = canonicalizeSocialUrl(c.url);
    const old = best.get(key);
    if (!old || c.score > old.score) best.set(key, c);
  }
  const deduped = [...best.values()].sort((a, b) => {
    if (a.media !== b.media) return a.media.localeCompare(b.media);
    return b.score - a.score;
  });

  const requested = new Set(
    norm !== undefined && norm.length > 0 ? norm : [...ALLOWED_PLATFORMS]
  );
  const found = new Set(deduped.map((c) => c.media));
  const classification = buildClassification(
    found,
    requested,
    coverage,
    archetype,
    budgets,
    settings.maxResultsPerPlatform
  );
  const meta: PipelineMeta = {
    objective: "maximize_realistic_public_coverage",
    productArchetype: archetype,
    platformCoverageLikelihood: coverage as Record<string, string>,
    crawlBudgets: Object.fromEntries(
      Object.entries(budgets).map(([k, v]) => [k, v as string])
    ),
    foundPlatforms: [...found].sort(),
    missingPlatforms: [...requested].filter((x) => !found.has(x)).sort(),
    explanation: buildExplanation(found, requested, coverage, archetype),
    classification,
    debug_social_heavy_zero_tiktok: false,
  };

  return { rows: deduped, warnings, meta };
}

export async function runPipeline(
  products: ProductInput[],
  useGroqRerank = true,
  platforms?: string[],
  options?: PipelineRunOptions
): Promise<PipelineResult> {
  const settings = loadSearchSettings();
  const norm = normalizePlatformList(platforms);
  const rows: CandidateLink[] = [];
  const warnings: string[] = [];
  const metas: PipelineMeta[] = [];

  for (const p of products) {
    const { rows: r, warnings: w, meta } = await discoverForProduct(
      p,
      useGroqRerank,
      platforms,
      options
    );
    rows.push(...r);
    warnings.push(...w);
    if (meta) metas.push(meta);
  }

  if (
    wantsPlatform(norm, "Youtube" as PlatformId) &&
    !youtubeEnabled(settings)
  ) {
    warnings.push(
      "YOUTUBE_API_KEY not set; YouTube Data API disabled. If YOUTUBE_USE_YTDLP is true (default), yt-dlp still searches YouTube when the binary is available."
    );
  }
  if (
    wantsPlatform(norm, "YoutubeShorts" as PlatformId) &&
    !settings.youtubeUseYtdlp
  ) {
    warnings.push(
      "YOUTUBE_USE_YTDLP is false; YouTube Shorts discovery (yt-dlp) is skipped."
    );
  }
  if (settings.googleCseEnabled && !cseEnabled(settings)) {
    if (
      wantsPlatform(norm, "Tiktok" as PlatformId) ||
      wantsPlatform(norm, "Facebook" as PlatformId) ||
      wantsPlatform(norm, "Instagram" as PlatformId)
    ) {
      warnings.push(
        "GOOGLE_CSE_API_KEY / GOOGLE_CSE_ID not set; TikTok, Facebook, Instagram (CSE) skipped."
      );
    }
  }

  return {
    rows,
    warnings,
    meta:
      metas.length === 1
        ? metas[0]
        : metas.length > 1
          ? { perProduct: metas }
          : undefined,
  };
}
