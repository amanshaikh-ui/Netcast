# NetCast

NetCast finds **public** social links for product research from **Brand**, **SKU**, and optional **product name**. It searches YouTube, YouTube Shorts, Reddit, TikTok, Facebook, and Instagram, then returns rows you can export as CSV (`Media`, `Brand`, `URL`, `SKU`, `Product Name`).

There are two ways to use it: the **web app** (recommended) and an optional **Python CLI** for batch CSV from the terminal.

### Features

- **One search, many networks** — pick YouTube, Shorts, Reddit, TikTok, Facebook, Instagram (checkboxes in the UI).
- **Single product or CSV batch** — paste a row or upload a sheet (`Brand` + `SKU`, optional product name).
- **Export** — download results as CSV in the TTI-style columns above.
- **Smarter queries (optional)** — if you set a **Groq** API key, the app can propose better search phrases and optional reranking.
- **CLI for automation** — same pipeline from the terminal for large or scheduled jobs.

### Why YouTube Data API (and other paid APIs) aren’t required by default

NetCast is built so you can **run without Google Cloud billing, YouTube API quotas, or Custom Search setup** unless you choose to add them.

- **YouTube** — the tool can use **yt-dlp** (Innertube search, no API key) on a machine where `yt-dlp` is installed, and/or **web-style discovery** (DuckDuckGo / HTML fallbacks) in the hosted app. The **YouTube Data API v3** is **optional**: add `YOUTUBE_API_KEY` only if you want official search results and quota limits work for you.
- **Google Programmable Search (CSE)** — **off by default**. Turning it on needs a CSE key *and* a Custom Search Engine ID; it’s there if you want Google’s index on top of DDG-based search, not as a hard dependency.
- **Other platforms** — TikTok / Meta don’t give a simple “search every public SKU post” API for this use case, so the app leans on **public web search** (`site:tiktok.com`, etc.) and optional extras (direct/Playwright) on your own machine—not on serverless hosts.

**Summary:** APIs are **supported when you add keys**; defaults favor **fewer accounts, fewer keys, and fewer quota surprises**—at the cost of relying on search indexes and scraping-friendly paths, which can be noisier or rate-limited than a first-party API.

---

## Web app (Next.js)

From the repo root:

```bash
cd frontend
npm install
```

Copy `frontend/.env.local.example` to `frontend/.env.local` (or rename it).

Edit `.env.local` if you have API keys (YouTube, Groq, Google CSE, etc.) — none are strictly required to try the app locally.

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Use **Link search** to run a query or upload a CSV.

**Deploy (Vercel):** connect this repo and set **Root Directory** to `frontend`. Copy variables from `frontend/.env.local.example` into Vercel **Environment Variables**. Do not set Install Command to `npm install --prefix frontend` if Root Directory is already `frontend`. TikTok’s Python path is off on serverless; discovery still uses web search / optional CSE.

---

## Python CLI (optional)

Use this for scripted runs and the same env ideas as in `.env.example` at the repo root.

```bash
python -m venv .venv
```

On Windows: `.\.venv\Scripts\activate` — on macOS/Linux: `source .venv/bin/activate`

```bash
pip install -e ".[dev]"
linksearch -i sample_input.csv -o output_links.csv
```

Optional extras (TikTok/Instagram direct, Playwright, etc.): `pip install -e ".[direct]"` — see `pyproject.toml` and `.env.example` for details.

---

## Tests

```bash
pytest
```

---

## License

MIT
