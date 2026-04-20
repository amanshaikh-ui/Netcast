import { formatThrown } from "@/lib/formatError";
import { parseProductCsv } from "@/lib/parseCsv";
import { runPipeline } from "@/lib/pipeline";
import type { PipelineMeta, PipelineResult, ProductInput } from "@/lib/types";
import { NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 120;

/** Batch runs return `meta: { perProduct }` — lift first product meta + batch count for the UI. */
function enrichMetaForClient(result: PipelineResult): PipelineResult {
  const meta = result.meta;
  if (!meta || !("perProduct" in meta)) return result;
  const pp = (meta as { perProduct: PipelineMeta[] }).perProduct;
  if (!Array.isArray(pp) || pp.length === 0) return result;
  const first = pp[0]!;
  return {
    ...result,
    meta: {
      ...first,
      classification: first.classification,
      explanation: first.explanation,
      batchProductCount: pp.length,
      perProduct: pp,
    },
  };
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as {
      products?: ProductInput[];
      csv?: string;
      useGroqRerank?: boolean;
      /** Subset: Youtube | Reddit | Tiktok | Facebook | Instagram */
      platforms?: string[];
      /** YYYY-MM-DD — filter YouTube Shorts by upload date (inclusive) */
      shortsDateAfter?: string;
      shortsDateBefore?: string;
    };

    let list: ProductInput[] = [];

    if (body.products?.length) {
      list = body.products
        .map((p) => ({
          brand: String(p.brand ?? "").trim(),
          sku: String(p.sku ?? "").trim(),
          productName: String(
            (p as { productName?: string; product_name?: string }).productName ??
              (p as { product_name?: string }).product_name ??
              ""
          ).trim(),
        }))
        .filter((p) => p.brand && p.sku);
    } else if (typeof body.csv === "string" && body.csv.trim()) {
      list = parseProductCsv(body.csv);
    } else {
      return NextResponse.json(
        {
          error:
            "Send JSON with products: [{ brand, sku, productName? }] or csv: string (CSV: Brand & SKU required; product name optional)",
        },
        { status: 400 }
      );
    }

    if (!list.length) {
      return NextResponse.json(
        {
          error:
            "No valid CSV rows. Use a header row with Brand and SKU (Product Name optional), or two columns: Brand, SKU. Tab or comma separated.",
        },
        { status: 400 }
      );
    }

    const useGroqRerank = body.useGroqRerank !== false;
    const platforms =
      body.platforms === undefined
        ? undefined
        : Array.isArray(body.platforms)
          ? body.platforms.map((x) => String(x).trim())
          : undefined;
    const trimOrUndef = (s: unknown) => {
      const t = typeof s === "string" ? s.trim() : "";
      return t || undefined;
    };
    const result = await runPipeline(list, useGroqRerank, platforms, {
      shortsDateAfter: trimOrUndef(body.shortsDateAfter),
      shortsDateBefore: trimOrUndef(body.shortsDateBefore),
    });
    return NextResponse.json(enrichMetaForClient(result));
  } catch (e) {
    return NextResponse.json({ error: formatThrown(e) }, { status: 500 });
  }
}
