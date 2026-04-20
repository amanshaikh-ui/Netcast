# Social Media Link Discovery



Automates discovery of **public** social links for product research: given **Brand**, **SKU**, and optional **Product name**, it searches **YouTube**, **Reddit**, **TikTok**, **Facebook**, and **Instagram** and writes a CSV aligned with the TTI sample format.



**Default strategy:** **No Google Custom Search API** (`GOOGLE_CSE_ENABLED` default **false**). The pipeline uses **DuckDuckGo** `site:` queries (`DDG_SOCIAL_ENABLED` default **true**, dependency `duckduckgo-search`) for TikTok / Facebook / Instagram links, **yt-dlp** for YouTube Innertube, **Reddit**, and optional **direct TikTok / Instagram** when `pip install -e ".[direct]"` + Playwright / instaloader are installed. Enable **CSE** only if you explicitly want Google Programmable Search too (`GOOGLE_CSE_ENABLED=true` + keys).



## Output columns



`Media`, `Brand`, `URL`, `SKU`, `Product Name`



## Setup



1. **Python 3.11+**



2. Create a virtual environment and install:



```bash

cd "c:\Users\admin\Desktop\link search"

python -m venv .venv

.\.venv\Scripts\activate

pip install -e ".[dev]"

```



3. **Recommended for TikTok + Instagram direct search** (optional extras):



```bash

pip install -e ".[direct]"

playwright install chromium

```



4. Copy `.env.example` to `.env` and adjust:



| Variable | Purpose |

|----------|---------|

| `YOUTUBE_API_KEY` | Optional — [YouTube Data API v3](https://console.cloud.google.com/) key; **not required** if `YOUTUBE_USE_YTDLP=true` (default). |

| `YOUTUBE_USE_YTDLP` | Default **true** — Innertube search via **yt-dlp** (no Google API key). |

| `DDG_SOCIAL_ENABLED` | Default **true** — DuckDuckGo-powered `site:tiktok.com` / `facebook.com` / `instagram.com` discovery (no Google API). Set **false** to disable. |

| `GOOGLE_CSE_ENABLED` | Default **false** — set **true** and provide keys below only if you want **additional** TikTok/Facebook/Instagram via **Google Programmable Search**. |

| `GOOGLE_CSE_API_KEY` | Required only when CSE is enabled — [Custom Search API](https://console.cloud.google.com/). |

| `GOOGLE_CSE_ID` | Required only when CSE is enabled — [Programmable Search Engine](https://programmablesearchengine.google.com/) cx. |

| `TIKTOK_DIRECT_ENABLED` | Default **true** — needs `[direct]` + Playwright; optional `TIKTOK_MS_TOKEN` from tiktok.com cookies. |

| `TIKTOK_DIRECT_PYTHON` | **Web UI:** default **true** — runs the same direct TikTok path as Python via subprocess; set **false** to skip (DDG/CSE only). |

| `STRICT_SKU_FILTER` | Default **true** — per platform, prefer rows whose title+snippet mention the SKU when any do; set **false** so short captions without the SKU are not filtered out. |

| `INSTAGRAM_DIRECT_ENABLED` | Default **true** — needs `[direct]`; optional `INSTAGRAM_SESSION_FILE` for session. |

| `GROQ_API_KEY` | Optional — [Groq Console](https://console.groq.com/) for smarter queries + optional reranking |

| `REDDIT_USER_AGENT` | Required string identifying your app (see [Reddit API rules](https://github.com/reddit-archive/reddit/wiki/api)) |



**Free tiers:** YouTube Data API and Google CSE have daily quotas if you enable them; Groq offers a free tier with rate limits — check current docs before bulk runs.



## Usage



```bash

linksearch -i sample_input.csv -o output_links.csv

# Optional: only some networks (comma-separated, same names as above)

linksearch -i sample_input.csv -o out.csv --platforms "Youtube,Reddit,Tiktok"

```



- `--no-groq-rerank` — skip the second Groq pass (fewer calls, faster).

- `-v` — debug logging.



Without YouTube or CSE keys, you still get **YouTube (yt-dlp)**, **TikTok/Facebook/Instagram via DuckDuckGo**, **direct TikTok/Instagram** (if extras installed), and **Reddit**.



## Web dashboard (Next.js)



1. `cd frontend && npm install`

2. Copy `.env.local.example` to `.env.local` and set env vars (server-side only). **CSE defaults off** unless `GOOGLE_CSE_ENABLED=true`.

3. `npm run dev` → open [http://localhost:3000](http://localhost:3000)

4. Production: `npm run build` then `npm start`, or deploy to **Vercel** (set env vars in the project settings).



**Note:** `POST /api/search` accepts JSON `{ "products": [...] }` or `{ "csv": "..." }` with optional `"platforms": ["Youtube","Reddit","Tiktok","Facebook","Instagram"]` to limit which sources run. On Vercel Hobby, long-running bulk jobs may hit execution time limits — use batch size or a paid plan for large CSVs.



## How it works



1. **Queries** — Groq (if configured) proposes several short search phrases; otherwise brand + SKU + name are used.

2. **YouTube** — **yt-dlp** Innertube search (`ytsearch…`) by default (`YOUTUBE_USE_YTDLP`); optional **YouTube Data API** when `YOUTUBE_API_KEY` is set. The Next.js app shells out to `yt-dlp` or `python -m yt_dlp` when available.

3. **Reddit** — public `search.json` with a proper `User-Agent`.

4. **TikTok (direct)** — TikTokApi + Playwright when `[direct]` is installed and `TIKTOK_DIRECT_ENABLED=true` (default).

5. **Instagram (direct)** — instaloader hashtag crawl when `[direct]` is installed and `INSTAGRAM_DIRECT_ENABLED=true` (default).

6. **TikTok / Facebook / Instagram (DuckDuckGo)** — default; `site:` text search via **`duckduckgo-search`** (Python) or **`duck-duck-scrape`** (Next.js). May rate-limit or return empty; not affiliated with those platforms.

7. **TikTok / Facebook / Instagram (CSE)** — only if **`GOOGLE_CSE_ENABLED=true`** and both CSE keys are set (optional extra index).

8. **Ranking** — Token overlap heuristics (SKU/brand/product words); optional Groq scores blended in.



## Facebook limitations



Facebook has no stable first-party “search every post by SKU” API in this tool. **DuckDuckGo `site:facebook.com`** and optional **Google CSE** surface only what those search indexes know about. **Options:** (1) rely on **DDG/CSE** for indexed public URLs, (2) use **official Meta APIs** where your use case allows, or (3) accept gaps versus TikTok/YouTube/Reddit.



## Other limitations (be transparent in submissions)



- **Meta** content depends on **search index coverage** (CSE) or **tooling limits** (direct); not all posts are findable.

- **Reddit** may rate-limit; respect `429` and terms of use.

- This tool does **not** log into social networks for bulk discovery except optional session files you supply for Instagram.



## Deploy on Vercel



The UI is the **Next.js app** in **`frontend/`**.



1. Import this repo in [Vercel](https://vercel.com/new) (GitHub integration).

2. **Root Directory:** either **`frontend`** (simplest; Vercel reads `frontend/package.json` with `next`) **or** leave it at **`.`** (repo root). The root **`package.json`** lists `next` so Vercel’s detector succeeds, and **`vercel.json`** runs install/build in **`frontend/`**.

3. **Environment variables:** copy keys from **`frontend/.env.local.example`** into **Project → Settings → Environment Variables** (Production / Preview as needed). On Vercel, set **`TIKTOK_DIRECT_PYTHON=false`** — the serverless runtime does not run the Python/Playwright TikTok subprocess; TikTok still uses DuckDuckGo / CSE when those are enabled.

4. **`/api/search`** uses `maxDuration = 120` seconds. On the **Hobby** plan Vercel caps function duration lower; upgrade to **Pro** if searches time out.



## Tests



```bash

pytest

```



## License



MIT

