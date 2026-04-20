"use client";

import type { PlatformId } from "@/lib/platformFilter";
import type { ProductClassification } from "@/lib/types";

const LABEL: Record<PlatformId, string> = {
  Youtube: "YouTube",
  YoutubeShorts: "Shorts",
  Reddit: "Reddit",
  Tiktok: "TikTok",
  Facebook: "Facebook",
  Instagram: "Instagram",
};

const SLUG: Record<PlatformId, string> = {
  Youtube: "youtube",
  YoutubeShorts: "youtube_shorts",
  Reddit: "reddit",
  Tiktok: "tiktok",
  Facebook: "facebook",
  Instagram: "instagram",
};

const BAR: Record<PlatformId, string> = {
  Youtube: "from-red-500/90 to-red-600/70",
  YoutubeShorts: "from-rose-500/90 to-red-500/70",
  Reddit: "from-orange-500/90 to-orange-600/70",
  Tiktok: "from-cyan-500/90 to-cyan-600/70",
  Facebook: "from-blue-500/90 to-blue-600/70",
  Instagram: "from-pink-500/90 to-purple-600/70",
};

type RowLike = { media: string };

function countForPlatform(rows: RowLike[], id: PlatformId): number {
  return rows.filter((r) => r.media === id).length;
}

export function CoverageVisual({
  rows,
  selectedPlatforms,
  classification,
}: {
  rows: RowLike[];
  selectedPlatforms: PlatformId[];
  classification: ProductClassification | null;
}) {
  const reasons = classification?.missing_platforms_reason ?? {};
  const counts = selectedPlatforms.map((id) => ({
    id,
    label: LABEL[id],
    n: countForPlatform(rows, id),
    reason: reasons[SLUG[id]],
  }));
  const maxN = Math.max(1, ...counts.map((c) => c.n));

  return (
    <div className="space-y-3">
      <p className="text-[11px] leading-relaxed text-zinc-400">
        Bar height = links found per network (this run). Hover a bar for a short
        note when count is zero.
      </p>
      <div className="flex flex-wrap items-end justify-between gap-3 sm:gap-4">
        {counts.map(({ id, label, n, reason }) => {
          const pct = Math.max(6, (n / maxN) * 100);
          const title =
            n > 0
              ? `${n} link${n === 1 ? "" : "s"} on ${label}`
              : reason
                ? `${label}: ${reason}`
                : `${label}: no links this run`;
          return (
            <div
              key={id}
              className="flex min-w-[72px] flex-1 flex-col items-center gap-2"
              title={title}
            >
              <div className="flex h-36 w-full max-w-[100px] items-end justify-center rounded-t-lg bg-white/[0.04] px-1 pt-2 ring-1 ring-white/[0.06]">
                <div
                  className={`w-full max-w-[56px] rounded-t-md bg-gradient-to-t ${BAR[id]} shadow-lg transition-all`}
                  style={{ height: `${pct}%` }}
                  aria-hidden
                />
              </div>
              <span className="text-center text-[10px] font-semibold uppercase tracking-wide text-zinc-400">
                {label}
              </span>
              <span className="font-mono text-xs tabular-nums text-zinc-300">
                {n}
              </span>
            </div>
          );
        })}
      </div>
      {classification?.product_type && (
        <p className="text-[11px] text-zinc-500">
          Product type:{" "}
          <span className="text-zinc-400">{classification.product_type}</span>
        </p>
      )}
    </div>
  );
}
