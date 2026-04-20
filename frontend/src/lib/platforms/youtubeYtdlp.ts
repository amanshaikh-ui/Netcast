import { execFile } from "node:child_process";
import { promisify } from "node:util";

import type { CandidateLink, ProductInput, SearchSettings } from "../types";
import { primaryQuery } from "../scoring";

const execFileAsync = promisify(execFile);

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
    let url = String(e.url ?? "");
    if (!url && id) url = `https://www.youtube.com/watch?v=${id}`;
    if (!url) continue;
    out.push({
      media: "Youtube",
      brand: "", // filled by caller
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

async function runYtdlpJson(args: string[]): Promise<string | null> {
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

/**
 * YouTube search via yt-dlp (Innertube). Requires `yt-dlp` on PATH or Python with yt-dlp installed.
 */
export async function searchYoutubeYtdlp(
  settings: SearchSettings,
  product: ProductInput,
  queries: string[]
): Promise<CandidateLink[]> {
  if (!settings.youtubeUseYtdlp) return [];
  const cap = settings.maxResultsPerPlatform;
  const qText = (queries.length
    ? queries.slice(0, 3).join(" ")
    : primaryQuery(product)
  )
    .trim()
    .slice(0, 200);
  if (!qText) return [];

  const args = [
    `ytsearch${cap}:${qText}`,
    "-J",
    "--flat-playlist",
    "--no-download",
    "--no-warnings",
    "--quiet",
  ];
  const stdout = await runYtdlpJson(args);
  if (!stdout) return [];

  try {
    const rows = parsePlaylistJson(stdout);
    const brand = product.brand.trim();
    const sku = product.sku.trim();
    const productName = product.productName.trim();
    return rows.map((r) => ({
      ...r,
      brand,
      sku,
      productName,
      sourceQuery: qText,
    }));
  } catch {
    return [];
  }
}
