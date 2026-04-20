# NetCast

NetCast finds **public** social links for product research from **Brand**, **SKU**, and optional **product name**. It searches YouTube, YouTube Shorts, Reddit, TikTok, Facebook, and Instagram, then returns rows you can export as CSV (`Media`, `Brand`, `URL`, `SKU`, `Product Name`).

There are two ways to use it: the **web app** (recommended) and an optional **Python CLI** for batch CSV from the terminal.

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
