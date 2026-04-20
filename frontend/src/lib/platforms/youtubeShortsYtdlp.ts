import { execFile } from "node:child_process";
import { promisify } from "node:util";

import type { CandidateLink, ProductInput, SearchSettings } from "../types";
import { primaryQuery } from "../scoring";

const execFileAsync = promisify(execFile);

/** YouTube web: Type = Shorts (matches Shorts chip on /results). */
const SHORTS_SEARCH_SP = "EgIQCQ==";

export type ShortsDateRange = {
  /** Inclusive, YYYY-MM-DD */
  after?: string;
  /** Inclusive, YYYY-MM-DD */
  before?: string;
};

function shortsResultsUrl(searchQuery: string): string {
  const u = new URL("https://www.youtube.com/results");
  u.searchParams.set("search_query", searchQuery.trim());
  u.searchParams.set("sp", SHORTS_SEARCH_SP);
  return u.toString();
}

function normalizeShortsUrl(raw: string | undefined, id: string): string | null {
  if (raw && typeof raw === "string" && raw.includes("/shorts/")) {
    try {
      const p = new URL(raw).pathname.split("/shorts/")[1]?.split("/")[0];
      if (p && p.length === 11) return `https://www.youtube.com/shorts/${p}`;
    } catch {
      /* fall through */
    }
  }
  if (id.length === 11) return `https://www.youtube.com/shorts/${id}`;
  return null;
}

function parsePlaylistJson(raw: string): CandidateLink[] {
  const info = JSON.parse(raw) as {
    _type?: string;
    entries?: unknown[];
    id?: string;
    title?: string;
    url?: string;
    description?: string;
  };
  let entries: unknown[];
  if (info._type === "playlist") {
    entries = (info.entries ?? []).filter(Boolean);
  } else if (info.id || info.url) {
    entries = [info];
  } else {
    entries = [];
  }
  const out: CandidateLink[] = [];
  for (const ent of entries) {
    if (!ent || typeof ent !== "object") continue;
    const e = ent as Record<string, unknown>;
    const id = typeof e.id === "string" ? e.id : "";
    const title = String(e.title ?? "");
    const rawUrl = typeof e.url === "string" ? e.url : undefined;
    const url = normalizeShortsUrl(rawUrl, id);
    if (!url) continue;
    out.push({
      media: "YoutubeShorts",
      brand: "",
      url,
      sku: "",
      productName: "",
      title,
      snippet: String(e.description ?? "").slice(0, 500),
      score: 0,
    });
  }
  return out;
}

async function runYtdlpStdout(args: string[]): Promise<string | null> {
  const attempts: { cmd: string; argv: string[] }[] = [
    { cmd: process.env.YTDLP_BIN || "yt-dlp", argv: args },
    { cmd: "python", argv: ["-m", "yt_dlp", ...args] },
    { cmd: "py", argv: ["-m", "yt_dlp", ...args] },
  ];
  for (const { cmd, argv } of attempts) {
    try {
      const { stdout } = await execFileAsync(cmd, argv, {
        timeout: 90_000,
        maxBuffer: 25 * 1024 * 1024,
        windowsHide: true,
      });
      return stdout.toString();
    } catch {
      /* try next */
    }
  }
  return null;
}

/** yt-dlp upload_date as YYYYMMDD */
async function fetchUploadDateYmd(shortUrl: string): Promise<string | null> {
  const args = [
    shortUrl,
    "--skip-download",
    "--print",
    "%(upload_date)s",
    "--no-warnings",
    "--quiet",
  ];
  const out = await runYtdlpStdout(args);
  const line = out?.trim();
  if (!line || !/^\d{8}$/.test(line)) return null;
  return line;
}

function isoToYmd(iso: string): string {
  return iso.replace(/-/g, "");
}

async function filterRowsByUploadDate(
  rows: CandidateLink[],
  range: ShortsDateRange,
  cap: number
): Promise<CandidateLink[]> {
  const after = range.after ? isoToYmd(range.after) : null;
  const before = range.before ? isoToYmd(range.before) : null;
  if (!after && !before) return rows.slice(0, cap);

  const out: CandidateLink[] = [];
  for (const row of rows) {
    const ud = await fetchUploadDateYmd(row.url);
    if (!ud) continue;
    if (after && ud < after) continue;
    if (before && ud > before) continue;
    out.push(row);
    if (out.length >= cap) break;
  }
  return out;
}

/**
 * YouTube Shorts only: /results with Shorts type filter (not generic ytsearch).
 * Optional upload-date range: fetches per-video metadata (yt-dlp) so results match the window.
 */
export async function searchYoutubeShortsYtdlp(
  settings: SearchSettings,
  product: ProductInput,
  queries: string[],
  dateRange?: ShortsDateRange
): Promise<CandidateLink[]> {
  if (!settings.youtubeUseYtdlp) return [];
  const cap = settings.maxResultsPerPlatform;
  const base = (queries.length
    ? queries.slice(0, 3).join(" ")
    : primaryQuery(product)
  )
    .trim()
    .slice(0, 200);
  if (!base) return [];
  const qText = base;
  const pageUrl = shortsResultsUrl(qText);

  const hasDate =
    Boolean(dateRange?.after?.trim()) || Boolean(dateRange?.before?.trim());
  const playlistEnd = hasDate ? Math.min(Math.max(cap * 10, 24), 50) : cap;

  const args = [
    pageUrl,
    "-J",
    "--flat-playlist",
    "--no-download",
    "--no-warnings",
    "--quiet",
    "--playlist-end",
    String(playlistEnd),
  ];
  const stdout = await runYtdlpStdout(args);
  if (!stdout) return [];

  try {
    let rows = parsePlaylistJson(stdout);
    const brand = product.brand.trim();
    const sku = product.sku.trim();
    const productName = product.productName.trim();
    rows = rows.map((r) => ({
      ...r,
      brand,
      sku,
      productName,
      sourceQuery: qText,
    }));

    if (hasDate && dateRange) {
      const after = dateRange.after?.trim();
      const before = dateRange.before?.trim();
      rows = await filterRowsByUploadDate(
        rows,
        {
          after: after || undefined,
          before: before || undefined,
        },
        cap
      );
    } else {
      rows = rows.slice(0, cap);
    }
    return rows;
  } catch {
    return [];
  }
}
