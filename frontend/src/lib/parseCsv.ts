import { parse } from "csv-parse/sync";
import type { ProductInput } from "./types";

/** Map normalized header text to our field (only first match wins per row). */
function mapHeaderToField(key: string): "brand" | "sku" | "productName" | null {
  const k = key
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
  const brandKeys = new Set([
    "brand",
    "brand name",
    "manufacturer",
    "make",
    "company",
  ]);
  const skuKeys = new Set([
    "sku",
    "item sku",
    "model",
    "model number",
    "part number",
    "part #",
    "part no",
    "item",
    "mpn",
  ]);
  const nameKeys = new Set([
    "product name",
    "product",
    "productname",
    "title",
    "description",
    "item name",
    "name",
    "product title",
  ]);
  if (brandKeys.has(k)) return "brand";
  if (skuKeys.has(k)) return "sku";
  if (nameKeys.has(k)) return "productName";
  return null;
}

function inferDelimiter(text: string): string {
  const line = text.split(/\r?\n/).find((l) => l.trim().length > 0) ?? "";
  const tabParts = line.split("\t").length;
  const commaParts = line.split(",").length;
  const semiParts = line.split(";").length;
  if (tabParts >= 3 && tabParts > commaParts) return "\t";
  if (semiParts >= 3 && semiParts > commaParts && semiParts > tabParts) return ";";
  return ",";
}

/** First row looks like labels (not data) for headerless fallback. */
function looksLikeHeaderRow(cells: string[]): boolean {
  const joined = cells.join(" ").toLowerCase();
  return (
    /\bbrand\b/.test(joined) &&
    /\b(sku|model|part)\b/.test(joined) &&
    cells.length >= 2
  );
}

function rowsFromMatrix(matrix: string[][]): ProductInput[] {
  const out: ProductInput[] = [];
  let start = 0;
  if (matrix.length > 0 && looksLikeHeaderRow(matrix[0]!.map((c) => c.trim()))) {
    start = 1;
  }
  for (let i = start; i < matrix.length; i++) {
    const row = matrix[i]!;
    if (row.length < 2) continue;
    const brand = (row[0] ?? "").trim();
    const sku = (row[1] ?? "").trim();
    const productName = (row[2] ?? "").trim();
    if (!brand || !sku) continue;
    out.push({ brand, sku, productName });
  }
  return out;
}

/**
 * Parse CSV with columns Brand, SKU, and optional Product Name (flexible names).
 * Product name may be omitted — brand + SKU are enough.
 */
export function parseProductCsv(text: string): ProductInput[] {
  const trimmed = text.trim();
  if (!trimmed) return [];

  const delimiter = inferDelimiter(trimmed);

  const parseOpts = {
    columns: true as const,
    skip_empty_lines: true,
    trim: true,
    relax_column_count: true,
    relax_quotes: true,
    bom: true,
    delimiter,
  };

  let raw: Record<string, string>[] = [];
  try {
    raw = parse(trimmed, parseOpts) as Record<string, string>[];
  } catch {
    raw = [];
  }

  const rows: ProductInput[] = [];

  for (const r of raw) {
    const acc: { brand?: string; sku?: string; productName?: string } = {};
    for (const [k, v] of Object.entries(r)) {
      const field = mapHeaderToField(k);
      if (!field) continue;
      const val = String(v ?? "").trim();
      if (field === "brand") {
        if (val) acc.brand = val;
      } else if (field === "sku") {
        if (val) acc.sku = val;
      } else if (field === "productName") {
        acc.productName = val;
      }
    }
    const brand = acc.brand ?? "";
    const sku = acc.sku ?? "";
    if (!brand || !sku) continue;
    rows.push({
      brand,
      sku,
      productName: acc.productName ?? "",
    });
  }

  if (rows.length > 0) return rows;

  /* Fallback: no usable headers — try fixed columns: Brand, SKU, [optional name] */
  let matrix: string[][] = [];
  try {
    matrix = parse(trimmed, {
      columns: false,
      skip_empty_lines: true,
      trim: true,
      relax_column_count: true,
      relax_quotes: true,
      bom: true,
      delimiter,
    }) as string[][];
  } catch {
    return [];
  }

  return rowsFromMatrix(matrix);
}
