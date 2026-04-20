import type { ProductAliases } from "./aliases";
import type { CandidateLink, ProductInput, SearchSettings } from "./types";
import { primaryQuery } from "./scoring";

function dedupeKeepOrder(items: string[], cap = 48): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const x of items) {
    const k = x.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(x);
    if (out.length >= cap) break;
  }
  return out;
}

export async function buildSearchQueries(
  settings: SearchSettings,
  product: ProductInput,
  aliases?: ProductAliases
): Promise<string[]> {
  const pa = aliases;
  const base = primaryQuery(product);
  const fallback = dedupeKeepOrder(
    pa?.allSearchQueries?.length
      ? [...pa.allSearchQueries]
      : [base, `${product.brand.trim()} ${product.sku.trim()}`, product.sku.trim()]
  );
  if (!settings.groqApiKey) return fallback;

  const aliasPreview = [
    ...(pa?.hashtags.slice(0, 8) ?? []),
    ...(pa?.pass1Queries.slice(0, 5) ?? []),
    ...(pa?.familyQueries?.slice(0, 4) ?? []),
  ].join(", ");

  const prompt = `You help find social media posts about a retail product.
Given:
- Brand: ${product.brand.trim()}
- SKU: ${product.sku.trim()}
- Product name: ${product.productName.trim() || "(unknown)"}
- Suggested aliases / hashtags / short phrases: ${aliasPreview || "(none)"}

Return a JSON object with key "queries": an array of 4 to 8 SHORT search query strings
for TikTok Instagram Facebook YouTube style search. Prefer short nicknames, model codes,
hashtag-style tokens without the #, review/unboxing phrases — NOT only the full catalog title.
JSON only.`;

  try {
    const r = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${settings.groqApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: settings.groqModel,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.2,
        max_tokens: 400,
      }),
      next: { revalidate: 0 },
    });
    const data = (await r.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const text = data.choices?.[0]?.message?.content?.trim() ?? "";
    const m = text.match(/\{[\s\S]*\}/);
    if (m) {
      const obj = JSON.parse(m[0]) as { queries?: unknown };
      const arr = obj.queries;
      if (Array.isArray(arr)) {
        const cleaned = arr
          .map((x) => String(x).trim())
          .filter(Boolean);
        return dedupeKeepOrder([...cleaned, ...fallback]);
      }
    }
  } catch {
    /* fallback */
  }
  return fallback;
}

export async function groqRerankCandidates(
  settings: SearchSettings,
  product: ProductInput,
  candidates: CandidateLink[],
  topN: number
): Promise<CandidateLink[]> {
  if (!settings.groqApiKey || !candidates.length) {
    return candidates.slice(0, topN);
  }

  const slim = candidates.slice(0, 25).map((c, i) => ({
    i,
    media: c.media,
    url: c.url,
    title: c.title.slice(0, 400),
    snippet: c.snippet.slice(0, 400),
  }));

  const prompt = `Product: brand=${product.brand.trim()} sku=${product.sku.trim()} name=${product.productName.trim()}
Candidates (JSON): ${JSON.stringify(slim)}
Return JSON object {"scores": [{"i": number, "score": number between 0 and 1}]} with one score per candidate index i.
Score by likely relevance to this exact product (not generic brand chat). JSON only.`;

  try {
    const r = await fetch("https://api.groq.com/openai/v1/chat/completions", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${settings.groqApiKey}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: settings.groqModel,
        messages: [{ role: "user", content: prompt }],
        temperature: 0.1,
        max_tokens: 800,
      }),
      next: { revalidate: 0 },
    });
    const data = (await r.json()) as {
      choices?: Array<{ message?: { content?: string } }>;
    };
    const text = data.choices?.[0]?.message?.content?.trim() ?? "";
    const m = text.match(/\{[\s\S]*\}/);
    if (!m) return candidates.slice(0, topN);
    const obj = JSON.parse(m[0]) as {
      scores?: Array<{ i?: number; score?: number }>;
    };
    const scoresList = obj.scores;
    if (!Array.isArray(scoresList)) return candidates.slice(0, topN);

    const bonus = new Map<number, number>();
    for (const s of scoresList) {
      if (typeof s.i === "number" && typeof s.score === "number") {
        bonus.set(s.i, s.score);
      }
    }

    const adjusted = candidates.map((c, idx) => {
      if (idx >= 25) return c;
      const b = bonus.get(idx) ?? 0;
      return { ...c, score: c.score + 2 * b };
    });
    adjusted.sort((a, b) => b.score - a.score);
    return adjusted.slice(0, topN);
  } catch {
    return candidates.slice(0, topN);
  }
}
