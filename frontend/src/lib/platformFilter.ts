/** Canonical IDs — must match CandidateLink.media from search modules. */
export const ALLOWED_PLATFORMS = [
  "Youtube",
  "YoutubeShorts",
  "Reddit",
  "Tiktok",
  "Facebook",
  "Instagram",
] as const;

export type PlatformId = (typeof ALLOWED_PLATFORMS)[number];

const ALLOWED = new Set<string>(ALLOWED_PLATFORMS);

/** `undefined` = all platforms (API/client omitted). Empty = none selected. */
export function normalizePlatformList(
  raw: string[] | undefined | null
): string[] | undefined {
  if (raw === undefined || raw === null) return undefined;
  const seen = new Set<string>();
  const out: string[] = [];
  for (const x of raw) {
    const t = String(x).trim();
    if (ALLOWED.has(t) && !seen.has(t)) {
      seen.add(t);
      out.push(t);
    }
  }
  return out;
}

export function wantsPlatform(
  platforms: string[] | undefined,
  key: PlatformId
): boolean {
  if (platforms === undefined) return true;
  if (platforms.length === 0) return false;
  return platforms.includes(key);
}
