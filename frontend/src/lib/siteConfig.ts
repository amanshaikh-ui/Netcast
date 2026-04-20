/**
 * Marketing / demo: set NEXT_PUBLIC_EXPLAINER_VIDEO_URL to a Google Drive file link
 * (https://drive.google.com/file/d/FILE_ID/view) or paste-ready embed URL.
 */

export function getExplainerEmbedSrc(): string | null {
  const raw = process.env.NEXT_PUBLIC_EXPLAINER_VIDEO_URL?.trim();
  if (!raw) return null;
  const drive = raw.match(/drive\.google\.com\/file\/d\/([^/]+)/i);
  if (drive) {
    return `https://drive.google.com/file/d/${drive[1]}/preview`;
  }
  return raw;
}
