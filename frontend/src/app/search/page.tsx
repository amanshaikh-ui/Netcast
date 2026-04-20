"use client";

import { CoverageVisual } from "@/components/CoverageVisual";
import { DiscoveryOceanLoader } from "@/components/DiscoveryOceanLoader";
import {
  ALLOWED_PLATFORMS,
  type PlatformId,
} from "@/lib/platformFilter";
import type { ProductClassification } from "@/lib/types";
import {
  EXAMPLE_BRAND,
  EXAMPLE_PRODUCT_NAME,
  EXAMPLE_SKU,
  NETCAST_GITHUB_URL,
  NETCAST_LIVE_URL,
} from "@/lib/siteConfig";
import { formatThrown, isAbortError } from "@/lib/formatError";
import Link from "next/link";
import type { DragEvent } from "react";
import { useCallback, useEffect, useRef, useState } from "react";

const PLATFORM_LABELS: Record<PlatformId, string> = {
  Youtube: "YouTube",
  YoutubeShorts: "YouTube Shorts",
  Reddit: "Reddit",
  Tiktok: "TikTok",
  Facebook: "Facebook",
  Instagram: "Instagram",
};

type Row = {
  media: string;
  brand: string;
  url: string;
  sku: string;
  productName: string;
  score?: number;
};

const PLATFORMS = [
  { name: "YouTube", color: "from-red-400/90 to-red-600/80" },
  { name: "Shorts", color: "from-rose-400/90 to-red-500/75" },
  { name: "Reddit", color: "from-orange-400/90 to-orange-600/80" },
  { name: "TikTok", color: "from-cyan-400/90 to-cyan-600/80" },
  { name: "Facebook", color: "from-blue-400/90 to-blue-600/80" },
  { name: "Instagram", color: "from-pink-400/90 to-purple-600/80" },
];

function mediaBadgeClass(media: string): string {
  const m = media.toLowerCase();
  if (m.includes("youtubeshorts")) {
    return "border-rose-500/35 bg-rose-500/15 text-rose-100";
  }
  if (m.includes("youtube")) return "border-red-500/35 bg-red-500/15 text-red-200";
  if (m.includes("tiktok")) return "border-cyan-500/35 bg-cyan-500/15 text-cyan-200";
  if (m.includes("reddit")) return "border-orange-500/35 bg-orange-500/15 text-orange-200";
  if (m.includes("facebook")) return "border-blue-500/35 bg-blue-500/15 text-blue-200";
  if (m.includes("instagram")) return "border-pink-500/35 bg-pink-500/15 text-pink-200";
  return "border-zinc-500/35 bg-zinc-500/15 text-zinc-300";
}

export default function SearchPage() {
  const [brand, setBrand] = useState(EXAMPLE_BRAND);
  const [sku, setSku] = useState(EXAMPLE_SKU);
  const [productName, setProductName] = useState(EXAMPLE_PRODUCT_NAME);
  const [csvText, setCsvText] = useState("");
  const [csvFileName, setCsvFileName] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [showPaste, setShowPaste] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<"single" | "csv">("single");
  const [loading, setLoading] = useState(false);
  const [rows, setRows] = useState<Row[]>([]);
  const [classification, setClassification] = useState<ProductClassification | null>(
    null
  );
  const [showCoverageChart, setShowCoverageChart] = useState(false);
  const [batchProductCount, setBatchProductCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const useGroqRerank = true;
  const [platformSel, setPlatformSel] = useState<Record<PlatformId, boolean>>(
    () =>
      Object.fromEntries(
        ALLOWED_PLATFORMS.map((p) => [p, true])
      ) as Record<PlatformId, boolean>
  );
  const [shortsDateAfter, setShortsDateAfter] = useState("");
  const [shortsDateBefore, setShortsDateBefore] = useState("");

  const mountedRef = useRef(true);
  const searchAbortRef = useRef<AbortController | null>(null);
  /** Only the latest search run may clear loading (avoids stale finally after rapid re-clicks). */
  const searchSeqRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      searchAbortRef.current?.abort();
    };
  }, []);

  /** Optional ?brand=&sku=&productName= from home “example” link. */
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const b = params.get("brand")?.trim();
    const s = params.get("sku")?.trim();
    const p = params.get("productName")?.trim();
    if (b) setBrand(b);
    if (s) setSku(s);
    if (p) setProductName(p);
  }, []);

  const ingestFile = useCallback((file: File) => {
    setCsvFileName(file.name);
    const reader = new FileReader();
    reader.onload = () => {
      setCsvText(String(reader.result ?? ""));
      setError(null);
    };
    reader.onerror = () => {
      setError("Could not read the file. Try saving as UTF-8 CSV and upload again.");
    };
    reader.readAsText(file);
  }, []);

  const onDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      setDragActive(false);
      const f = e.dataTransfer.files?.[0];
      if (f) ingestFile(f);
    },
    [ingestFile]
  );

  const runSearch = useCallback(async () => {
    if (mode === "csv" && !csvText.trim()) {
      setError("Upload a .csv file or paste your sheet data first.");
      return;
    }
    const selectedPlatforms = ALLOWED_PLATFORMS.filter((p) => platformSel[p]);
    if (selectedPlatforms.length === 0) {
      setError("Select at least one platform.");
      return;
    }
    if (shortsDateAfter && shortsDateBefore && shortsDateAfter > shortsDateBefore) {
      setError("Shorts “From” date must be on or before “To”.");
      return;
    }
    searchAbortRef.current?.abort();
    const ac = new AbortController();
    searchAbortRef.current = ac;
    const seq = ++searchSeqRef.current;

    setLoading(true);
    setError(null);
    setClassification(null);
    setShowCoverageChart(false);
    setBatchProductCount(null);
    setRows([]);
    try {
      const base = {
        useGroqRerank,
        platforms: selectedPlatforms,
        ...(platformSel.YoutubeShorts &&
        (shortsDateAfter || shortsDateBefore)
          ? {
              shortsDateAfter: shortsDateAfter || undefined,
              shortsDateBefore: shortsDateBefore || undefined,
            }
          : {}),
      };
      const body =
        mode === "single"
          ? {
              products: [{ brand, sku, productName }],
              ...base,
            }
          : { csv: csvText, ...base };

      const res = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: ac.signal,
      });

      if (!mountedRef.current || seq !== searchSeqRef.current) return;

      let raw: unknown;
      try {
        raw = await res.json();
      } catch {
        if (
          !mountedRef.current ||
          seq !== searchSeqRef.current ||
          ac.signal.aborted
        ) {
          return;
        }
        setError(`Invalid response from server (${res.status}). Try again.`);
        return;
      }

      const payload = raw as {
        rows?: unknown;
        warnings?: unknown;
        error?: unknown;
        meta?: {
          explanation?: string;
          batchProductCount?: number;
          classification?: ProductClassification;
        };
      };

      if (!res.ok) {
        if (!mountedRef.current || seq !== searchSeqRef.current) return;
        const msg =
          typeof payload.error === "string" && payload.error.trim()
            ? payload.error
            : `Request failed (${res.status})`;
        setError(msg);
        return;
      }

      if (!mountedRef.current || seq !== searchSeqRef.current || ac.signal.aborted) {
        return;
      }

      const rowsIn = Array.isArray(payload.rows) ? payload.rows : [];
      const normalizedRows: Row[] = rowsIn.map((item) => {
        const r = item as Record<string, unknown>;
        return {
          media: String(r.media ?? ""),
          brand: String(r.brand ?? ""),
          url: String(r.url ?? ""),
          sku: String(r.sku ?? ""),
          productName: String(
            r.productName ?? r.product_name ?? ""
          ),
          score: typeof r.score === "number" ? r.score : undefined,
        };
      });

      setRows(normalizedRows);
      const cls = payload.meta?.classification ?? null;
      setClassification(cls);
      setBatchProductCount(
        typeof payload.meta?.batchProductCount === "number"
          ? payload.meta.batchProductCount
          : null
      );
      setShowCoverageChart(true);
    } catch (err: unknown) {
      if (isAbortError(err)) return;
      if (mountedRef.current && seq === searchSeqRef.current) {
        setError(formatThrown(err));
      }
    } finally {
      if (mountedRef.current && seq === searchSeqRef.current) {
        setLoading(false);
      }
    }
  }, [
    brand,
    sku,
    productName,
    csvText,
    mode,
    platformSel,
    useGroqRerank,
    shortsDateAfter,
    shortsDateBefore,
  ]);

  const downloadCsv = useCallback(() => {
    const header = ["Media", "Brand", "URL", "SKU", "Product Name"];
    const lines = [
      header.join(","),
      ...rows.map((r) =>
        [
          escapeCsv(r.media),
          escapeCsv(r.brand),
          escapeCsv(r.url),
          escapeCsv(r.sku),
          escapeCsv(r.productName),
        ].join(",")
      ),
    ];
    const blob = new Blob([lines.join("\r\n")], {
      type: "text/csv;charset=utf-8",
    });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "social_links.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }, [rows]);

  const dataRowHint = csvText.trim()
    ? Math.max(0, csvText.trim().split(/\r?\n/).length - 1)
    : 0;

  return (
    <div className="relative z-10 min-h-screen">
      <DiscoveryOceanLoader active={loading} />
      <div className="mx-auto max-w-7xl px-4 pb-20 pt-12 sm:px-6 lg:px-10">
        <nav className="mb-8 flex justify-center sm:justify-start">
          <Link
            href="/"
            className="text-sm font-medium text-zinc-500 transition hover:text-cyan-400/90"
          >
            ← Home
          </Link>
        </nav>
        {/* Hero */}
        <header className="mb-12 text-center sm:mb-16">
          <div
            className="mb-6 flex flex-wrap items-center justify-center gap-2"
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "0.5rem",
              justifyContent: "center",
              alignItems: "center",
            }}
          >
            {PLATFORMS.map((p) => (
              <span
                key={p.name}
                className={`rounded-full bg-gradient-to-r px-3 py-1 text-[11px] font-semibold uppercase tracking-wider text-white shadow-lg ${p.color}`}
              >
                {p.name}
              </span>
            ))}
          </div>
          <h1 className="mt-3 text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            <span className="text-gradient">NetCast</span>
          </h1>
          <p
            className="mt-2 text-sm font-semibold uppercase tracking-[0.22em]"
            style={{ color: "rgba(103,232,249,0.75)" }}
          >
            Social link intelligence
          </p>
          <p className="mx-auto mt-4 max-w-xl text-base leading-relaxed text-zinc-400 sm:text-lg">
            SKU in. Links out. Every major network — instantly.
          </p>
        </header>

        <div className="grid gap-8 lg:grid-cols-[minmax(0,420px)_1fr] lg:items-start xl:gap-12">
          {/* Control panel */}
          <section className="glass-strong space-y-6 rounded-3xl p-6 sm:p-8">
            <div className="flex rounded-2xl bg-black/30 p-1.5 ring-1 ring-white/10">
              <button
                type="button"
                onClick={() => setMode("single")}
                className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                  mode === "single"
                    ? "bg-white/10 text-white shadow-lg ring-1 ring-cyan-500/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Single product
              </button>
              <button
                type="button"
                onClick={() => setMode("csv")}
                className={`flex-1 rounded-xl px-4 py-3 text-sm font-semibold transition ${
                  mode === "csv"
                    ? "bg-white/10 text-white shadow-lg ring-1 ring-violet-500/30"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                Sheet / CSV batch
              </button>
            </div>

            {mode === "single" ? (
              <div className="space-y-5">
                <Field
                  label="Brand"
                  value={brand}
                  onChange={(v) => setBrand(v)}
                  placeholder="e.g. Ryobi"
                />
                <Field
                  label="SKU"
                  value={sku}
                  onChange={(v) => setSku(v)}
                  placeholder="e.g. RYI6522"
                />
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-500">
                    Product name
                  </label>
                  <textarea
                    value={productName}
                    onChange={(e) => setProductName(e.target.value)}
                    rows={3}
                    className="input-glow w-full resize-none rounded-2xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
                    placeholder="Optional — helps search quality"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-5">
                <input
                  ref={fileRef}
                  type="file"
                  accept=".csv,text/csv,.txt"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0];
                    if (f) ingestFile(f);
                  }}
                />

                <div
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") fileRef.current?.click();
                  }}
                  onDragEnter={(e) => {
                    e.preventDefault();
                    setDragActive(true);
                  }}
                  onDragLeave={() => setDragActive(false)}
                  onDragOver={(e: DragEvent<HTMLDivElement>) =>
                    e.preventDefault()
                  }
                  onDrop={onDrop}
                  onClick={() => fileRef.current?.click()}
                  className={`group cursor-pointer rounded-2xl border-2 border-dashed px-6 py-12 text-center transition ${
                    dragActive
                      ? "border-cyan-400/60 bg-cyan-500/10"
                      : "border-white/15 bg-black/25 hover:border-cyan-500/40 hover:bg-cyan-500/5"
                  }`}
                >
                  <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-cyan-500/20 to-violet-500/20 ring-1 ring-white/10">
                    <svg
                      className="h-7 w-7 text-cyan-300"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                      />
                    </svg>
                  </div>
                  <p className="font-semibold text-white">
                    Drop your CSV or spreadsheet export
                  </p>
                  <p className="mt-2 text-sm text-zinc-500">
                    Export from Excel / Google Sheets as{" "}
                    <span className="text-cyan-400/90">.csv</span> — or click to
                    browse
                  </p>
                  <p className="mt-4 font-mono text-[11px] text-zinc-600">
                    Headers: Brand, SKU (Product Name optional) — comma, tab, or semicolon
                  </p>
                </div>

                {csvFileName && (
                  <div className="flex items-center justify-between rounded-xl bg-emerald-500/10 px-4 py-3 ring-1 ring-emerald-500/25">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="h-2 w-2 shrink-0 rounded-full bg-emerald-400" />
                      <span className="truncate text-sm font-medium text-emerald-200/90">
                        {csvFileName}
                      </span>
                    </div>
                    <span className="shrink-0 text-xs text-emerald-400/80">
                      ~{dataRowHint} data rows
                    </span>
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => setShowPaste((v) => !v)}
                  className="w-full text-center text-sm text-zinc-500 underline decoration-zinc-600 underline-offset-4 hover:text-cyan-400/90"
                >
                  {showPaste ? "Hide paste area" : "Or paste from clipboard"}
                </button>

                {showPaste && (
                  <div>
                    <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-500">
                      Paste CSV (from sheet)
                    </label>
                    <textarea
                      value={csvText}
                      onChange={(e) => {
                        setCsvText(e.target.value);
                        setCsvFileName(null);
                      }}
                      rows={8}
                      className="input-glow w-full rounded-2xl border border-white/10 bg-black/50 px-4 py-3 font-mono text-xs leading-relaxed text-zinc-200 placeholder:text-zinc-600 focus:outline-none"
                      placeholder={`Brand,SKU\nRyobi,RYI6522\nAcme,X-1,"Optional product name"`}
                    />
                  </div>
                )}
              </div>
            )}

            <div className="space-y-2">
              <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500">
                Platforms
              </p>
              <div className="flex flex-wrap gap-3">
                {ALLOWED_PLATFORMS.map((id) => (
                  <label
                    key={id}
                    className="flex cursor-pointer items-center gap-2 rounded-xl border border-white/10 bg-black/25 px-3 py-2 text-sm text-zinc-200 transition hover:border-cyan-500/30 hover:bg-white/[0.04]"
                  >
                    <input
                      type="checkbox"
                      checked={platformSel[id]}
                      onChange={() =>
                        setPlatformSel((s) => ({ ...s, [id]: !s[id] }))
                      }
                      className="h-4 w-4 rounded border-white/20 bg-zinc-900 text-cyan-500 focus:ring-cyan-500/40"
                    />
                    <span>{PLATFORM_LABELS[id]}</span>
                  </label>
                ))}
              </div>
              <p className="text-[11px] text-zinc-600">
                Only checked networks are searched. Uncheck to skip a platform.
              </p>
            </div>

            {platformSel.YoutubeShorts && (
              <div className="space-y-3 rounded-2xl border border-rose-500/20 bg-rose-950/15 px-4 py-4 ring-1 ring-rose-500/10">
                <p className="text-xs font-semibold uppercase tracking-wider text-rose-200/90">
                  YouTube Shorts — upload date
                </p>
                <p className="text-[11px] leading-relaxed text-zinc-500">
                  Optional. Limits Shorts to uploads between these dates (inclusive). Uses
                  per-video metadata; leave blank for no date filter.
                </p>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div>
                    <label className="mb-1.5 block text-[11px] font-medium text-zinc-500">
                      From
                    </label>
                    <input
                      type="date"
                      value={shortsDateAfter}
                      onChange={(e) => setShortsDateAfter(e.target.value)}
                      className="input-glow w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-zinc-100 focus:outline-none"
                    />
                  </div>
                  <div>
                    <label className="mb-1.5 block text-[11px] font-medium text-zinc-500">
                      To
                    </label>
                    <input
                      type="date"
                      value={shortsDateBefore}
                      onChange={(e) => setShortsDateBefore(e.target.value)}
                      className="input-glow w-full rounded-xl border border-white/10 bg-black/40 px-3 py-2.5 text-sm text-zinc-100 focus:outline-none"
                    />
                  </div>
                </div>
              </div>
            )}

            <button
              type="button"
              disabled={loading}
              onClick={() => {
                void runSearch();
              }}
              className="btn-shine relative w-full overflow-hidden rounded-2xl px-6 py-4 text-sm font-bold text-white transition disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Casting the net…" : "Cast the net"}
            </button>
          </section>

          {/* Results */}
          <section className="space-y-5">
            {error != null && error !== "" && (
              <div className="rounded-2xl border border-rose-500/30 bg-rose-950/40 px-5 py-4 text-sm text-rose-100 ring-1 ring-rose-500/20">
                {String(error)}
              </div>
            )}
            {showCoverageChart && (
              <div className="rounded-2xl border border-cyan-500/20 bg-cyan-950/20 px-5 py-4 ring-1 ring-cyan-500/15">
                <p className="mb-3 font-semibold text-cyan-200">Coverage overview</p>
                {batchProductCount != null && batchProductCount > 1 && (
                  <p className="mb-3 text-[11px] leading-relaxed text-cyan-100/80">
                    Batch: {batchProductCount} products — table lists all links; chart
                    aggregates this run. Classification below reflects the{" "}
                    <span className="font-medium">first</span> product in the file.
                  </p>
                )}
                <CoverageVisual
                  rows={rows}
                  selectedPlatforms={ALLOWED_PLATFORMS.filter((p) => platformSel[p])}
                  classification={classification}
                />
                {classification && (
                  <details className="mt-4 border-t border-white/[0.06] pt-3 text-violet-200/90">
                    <summary className="cursor-pointer text-xs font-semibold text-violet-300/95 hover:text-violet-200">
                      Raw classification (JSON)
                    </summary>
                    <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap font-mono text-[10px] text-violet-100/85">
                      {safeJsonForUi(classification)}
                    </pre>
                  </details>
                )}
              </div>
            )}

            <div className="flex flex-wrap items-center justify-between gap-4">
              <h2 className="text-xl font-semibold text-white">
                Results{" "}
                <span className="text-zinc-500">({rows.length})</span>
              </h2>
              {rows.length > 0 && (
                <button
                  type="button"
                  onClick={() => downloadCsv()}
                  className="rounded-xl border border-white/15 bg-white/5 px-4 py-2 text-sm font-medium text-white transition hover:bg-white/10"
                >
                  Download CSV
                </button>
              )}
            </div>

            <div className="glass overflow-hidden rounded-3xl ring-1 ring-white/10">
              <div className="max-h-[min(560px,70vh)] overflow-auto">
                <table className="w-full min-w-[680px] text-left text-sm">
                  <thead className="sticky top-0 z-[1] bg-zinc-950/95 text-[11px] font-bold uppercase tracking-widest text-zinc-500 backdrop-blur-md">
                    <tr>
                      <th className="px-5 py-4">Media</th>
                      <th className="px-5 py-4">Brand</th>
                      <th className="px-5 py-4">URL</th>
                      <th className="px-5 py-4">SKU</th>
                      <th className="px-5 py-4">Product</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/[0.06]">
                    {!loading && rows.length === 0 && (
                      <tr>
                        <td
                          colSpan={5}
                          className="px-5 py-16 text-center text-zinc-500"
                        >
                          Results appear here — run a search to populate the
                          grid.
                        </td>
                      </tr>
                    )}
                    {!loading &&
                      rows.map((r, i) => (
                        <tr
                          key={`${r.url}-${i}`}
                          className="transition hover:bg-white/[0.03]"
                        >
                          <td className="whitespace-nowrap px-5 py-3">
                            <span
                              className={`inline-flex rounded-lg border px-2.5 py-1 text-xs font-semibold ${mediaBadgeClass(r.media)}`}
                            >
                              {r.media}
                            </span>
                          </td>
                          <td className="px-5 py-3 text-zinc-200">{r.brand}</td>
                          <td className="max-w-md break-all px-5 py-3">
                            <a
                              href={r.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-cyan-400/95 underline decoration-cyan-500/30 underline-offset-2 hover:text-cyan-300"
                            >
                              {r.url}
                            </a>
                          </td>
                          <td className="whitespace-nowrap px-5 py-3 font-mono text-xs text-zinc-400">
                            {r.sku}
                          </td>
                          <td className="max-w-[200px] truncate px-5 py-3 text-zinc-500">
                            {r.productName}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </div>

        <footer className="mt-16 text-center text-xs text-zinc-600">
          <p>Keys live server-side · Built for product &amp; social research</p>
          <p className="mt-3 flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
            <a
              href={NETCAST_LIVE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-500/90 underline decoration-cyan-500/40 underline-offset-2 hover:text-cyan-400"
            >
              Live app (Vercel)
            </a>
            <span className="text-zinc-700">·</span>
            <a
              href={NETCAST_GITHUB_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-zinc-400 underline decoration-zinc-600 underline-offset-2 hover:text-zinc-300"
            >
              GitHub
            </a>
          </p>
        </footer>
      </div>
    </div>
  );
}

function safeJsonForUi(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return "(unable to serialize)";
  }
}

function Field({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div>
      <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-zinc-500">
        {label}
      </label>
      <input
        value={value}
        onChange={(e) => {
          onChange(e.currentTarget.value);
        }}
        placeholder={placeholder}
        className="input-glow w-full rounded-2xl border border-white/10 bg-black/40 px-4 py-3 text-sm text-zinc-100 placeholder:text-zinc-600 focus:outline-none"
      />
    </div>
  );
}

function escapeCsv(s: string): string {
  if (/[",\r\n]/.test(s)) {
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}
