import Link from "next/link";
import { getExplainerEmbedSrc } from "@/lib/siteConfig";

const FEATURES = [
  {
    title: "Multi-network discovery",
    desc: "Query YouTube, YouTube Shorts, Reddit, TikTok, Facebook, and Instagram in one run — pick only the networks you care about.",
    accent: "from-cyan-500/20 to-violet-500/10",
  },
  {
    title: "Real Shorts + date window",
    desc: "Shorts use YouTube’s Shorts search filter (not mixed uploads). Optionally narrow by upload date for Shorts only.",
    accent: "from-rose-500/20 to-red-500/10",
  },
  {
    title: "CSV at scale",
    desc: "Drop a spreadsheet export: batch many SKUs and download a combined link CSV for research or enrichment.",
    accent: "from-emerald-500/20 to-cyan-500/10",
  },
  {
    title: "Coverage intelligence",
    desc: "See predicted coverage, crawl depth hints, and which platforms came back empty — with exportable classification JSON.",
    accent: "from-violet-500/20 to-fuchsia-500/10",
  },
];

export default function HomePage() {
  const explainerSrc = getExplainerEmbedSrc();

  return (
    <div className="relative z-10 min-h-screen overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-20%,rgba(34,211,238,0.18),transparent)]" />
      <div className="pointer-events-none absolute -right-40 top-40 h-96 w-96 rounded-full bg-fuchsia-600/10 blur-3xl" />
      <div className="pointer-events-none absolute -left-32 bottom-20 h-80 w-80 rounded-full bg-cyan-600/10 blur-3xl" />

      <div className="relative mx-auto max-w-6xl px-4 pb-24 pt-14 sm:px-6 lg:px-10">
        <header className="text-center">
          <p className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-cyan-300/90">
            NetCast
          </p>
          <h1 className="bg-gradient-to-br from-white via-zinc-100 to-zinc-500 bg-clip-text text-5xl font-black tracking-tight text-transparent sm:text-6xl md:text-7xl">
            SKU in.
            <br />
            <span className="text-gradient">Social links out.</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-zinc-400 sm:text-xl">
            Cast a net across public posts and videos for your products — tuned for
            research, cataloging, and competitive visibility.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link
              href="/search"
              className="btn-shine inline-flex rounded-2xl px-8 py-4 text-base font-bold text-white shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-500/30"
            >
              Let&apos;s start
            </Link>
            <a
              href="#features"
              className="rounded-2xl border border-white/15 bg-white/5 px-6 py-4 text-sm font-semibold text-zinc-200 transition hover:bg-white/10"
            >
              Explore features
            </a>
          </div>
        </header>

        <section
          id="features"
          className="mt-24 scroll-mt-24 border-t border-white/[0.06] pt-20"
        >
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
            What NetCast does
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-sm text-zinc-500">
            Built for teams that need trustworthy outbound links — not just keyword
            noise.
          </p>
          <div className="mt-12 grid gap-5 sm:grid-cols-2">
            {FEATURES.map((f) => (
              <div
                key={f.title}
                className={`rounded-3xl border border-white/[0.08] bg-gradient-to-br ${f.accent} p-6 ring-1 ring-white/[0.05] transition hover:border-cyan-500/20`}
              >
                <h3 className="text-lg font-semibold text-white">{f.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-zinc-400">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-24 border-t border-white/[0.06] pt-20">
          <h2 className="text-center text-2xl font-bold text-white sm:text-3xl">
            See it in action
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-sm text-zinc-500">
            Walkthrough of the project — add your Google Drive video URL via{" "}
            <code className="rounded bg-zinc-800/80 px-1.5 py-0.5 font-mono text-[11px] text-cyan-200/90">
              NEXT_PUBLIC_EXPLAINER_VIDEO_URL
            </code>{" "}
            in your environment.
          </p>
          <div className="mx-auto mt-10 max-w-4xl overflow-hidden rounded-3xl border border-white/10 bg-black/40 ring-1 ring-white/[0.06]">
            {explainerSrc ? (
              <div className="aspect-video w-full">
                <iframe
                  title="NetCast explainer"
                  src={explainerSrc}
                  className="h-full w-full"
                  allow="autoplay; fullscreen; picture-in-picture"
                  allowFullScreen
                />
              </div>
            ) : (
              <div className="flex aspect-video flex-col items-center justify-center gap-3 px-6 text-center">
                <div className="rounded-2xl border border-dashed border-zinc-600 bg-zinc-900/50 px-6 py-12">
                  <p className="text-sm font-medium text-zinc-400">
                    Explainer video placeholder
                  </p>
                  <p className="mt-2 max-w-md text-xs text-zinc-600">
                    Set{" "}
                    <span className="font-mono text-zinc-500">
                      NEXT_PUBLIC_EXPLAINER_VIDEO_URL
                    </span>{" "}
                    to your Google Drive file link (e.g.{" "}
                    <span className="break-all text-zinc-500">
                      https://drive.google.com/file/d/…/view
                    </span>
                    ). The app embeds it automatically.
                  </p>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="mt-24 text-center">
          <p className="text-sm text-zinc-500">
            Ready to run a discovery pass?
          </p>
          <Link
            href="/search"
            className="mt-4 inline-flex rounded-2xl border border-cyan-500/30 bg-cyan-500/10 px-8 py-3.5 text-sm font-bold text-cyan-100 transition hover:bg-cyan-500/20"
          >
            Open the discovery console →
          </Link>
        </section>

        <footer className="mt-20 border-t border-white/[0.06] pt-10 text-center text-xs text-zinc-600">
          Keys and APIs stay server-side · NetCast
        </footer>
      </div>
    </div>
  );
}
