import Link from "next/link";
import { NETCAST_GITHUB_URL, NETCAST_LIVE_URL } from "@/lib/siteConfig";

export function SiteTopBar() {
  return (
    <header className="sticky top-0 z-[100] border-b border-white/[0.06] bg-[#030712]/90 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-10">
        <Link
          href="/"
          className="text-sm font-semibold tracking-tight text-zinc-200 transition hover:text-cyan-300"
        >
          NetCast
        </Link>
        <nav className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1 text-xs sm:text-sm">
          <a
            href={NETCAST_LIVE_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-cyan-400/95 underline decoration-cyan-500/35 underline-offset-2 hover:text-cyan-300"
          >
            Live (Vercel)
          </a>
          <a
            href={NETCAST_GITHUB_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="font-medium text-zinc-400 underline decoration-zinc-600 underline-offset-2 hover:text-zinc-200"
          >
            GitHub
          </a>
          <Link
            href="/search"
            className="rounded-lg border border-white/15 bg-white/[0.06] px-3 py-1.5 font-semibold text-zinc-100 transition hover:border-cyan-500/30 hover:bg-white/10"
          >
            Link search
          </Link>
        </nav>
      </div>
    </header>
  );
}
