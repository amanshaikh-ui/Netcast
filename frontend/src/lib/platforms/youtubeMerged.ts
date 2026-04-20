import type { CandidateLink, ProductInput, SearchSettings } from "../types";
import { searchYoutubeDdg } from "./ddgSocial";
import { searchYoutube } from "./youtube";
import { searchYoutubeYtdlp } from "./youtubeYtdlp";

export async function searchYoutubeMerged(
  settings: SearchSettings,
  product: ProductInput,
  queries: string[]
): Promise<CandidateLink[]> {
  const [api, ytdlp, ddg] = await Promise.all([
    searchYoutube(settings, product, queries),
    searchYoutubeYtdlp(settings, product, queries),
    searchYoutubeDdg(settings, product, queries),
  ]);
  const seen = new Set<string>();
  const merged: CandidateLink[] = [];
  for (const x of [...api, ...ytdlp, ...ddg]) {
    if (seen.has(x.url)) continue;
    seen.add(x.url);
    merged.push(x);
  }
  return merged;
}
