/**
 * Marketing / demo: set NEXT_PUBLIC_EXPLAINER_VIDEO_URL to a Google Drive file link
 * (https://drive.google.com/file/d/FILE_ID/view) or paste-ready embed URL.
 */

export const NETCAST_GITHUB_URL = "https://github.com/amanshaikh-ui/Netcast";

/** Production / preview URL — update if the Vercel project domain changes. */
export const NETCAST_LIVE_URL =
  "https://netcast-4f1pp79re-aman7756068021s-projects.vercel.app/";

/** Example product shown on the home page and default single-product fields on /search. */
export const EXAMPLE_BRAND = "SharkNinja";
export const EXAMPLE_SKU = "IZ562H";
export const EXAMPLE_PRODUCT_NAME =
  "Shark Pro Cordless Vacuum with Clean Sense IQ";

export function getExplainerEmbedSrc(): string | null {
  const raw = process.env.NEXT_PUBLIC_EXPLAINER_VIDEO_URL?.trim();
  if (!raw) return null;
  const drive = raw.match(/drive\.google\.com\/file\/d\/([^/]+)/i);
  if (drive) {
    return `https://drive.google.com/file/d/${drive[1]}/preview`;
  }
  return raw;
}
