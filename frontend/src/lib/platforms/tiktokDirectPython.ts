import { spawn } from "child_process";
import { join } from "path";
import type { CandidateLink, ProductInput, SearchSettings } from "../types";

function pythonpathForRepoRoot(root: string): string {
  const src = join(root, "src");
  const cur = process.env.PYTHONPATH?.trim();
  if (!cur) return src;
  return process.platform === "win32" ? `${src};${cur}` : `${src}:${cur}`;
}

/**
 * Runs the same TikTok direct path as the Python CLI via stdio JSON
 * (`python -m linksearch.tiktok_direct_stdio`). Requires editable install
 * or PYTHONPATH including `src` from the monorepo root.
 */
export async function searchTiktokDirectPython(
  settings: SearchSettings,
  product: ProductInput,
  queries: string[]
): Promise<CandidateLink[]> {
  if (!settings.tiktokDirectPython) return [];

  const root = join(process.cwd(), "..");
  const pythonBin = process.env.PYTHON_BIN?.trim() || "python";
  const payload = JSON.stringify({
    brand: product.brand,
    sku: product.sku,
    productName: product.productName,
    queries,
  });

  return new Promise((resolve, reject) => {
    const child = spawn(pythonBin, ["-m", "linksearch.tiktok_direct_stdio"], {
      cwd: root,
      stdio: ["pipe", "pipe", "pipe"],
      windowsHide: true,
      env: {
        ...process.env,
        PYTHONPATH: pythonpathForRepoRoot(root),
      },
    });

    let stdout = "";
    let stderr = "";
    const timeoutMs = 180_000;
    const timer = setTimeout(() => {
      child.kill();
    }, timeoutMs);

    child.stdout?.on("data", (d: Buffer) => {
      stdout += d.toString("utf8");
    });
    child.stderr?.on("data", (d: Buffer) => {
      stderr += d.toString("utf8");
    });
    child.on("error", (err) => {
      clearTimeout(timer);
      reject(err);
    });
    child.on("close", (code) => {
      clearTimeout(timer);
      try {
        const parsed = JSON.parse(stdout.trim() || "[]") as unknown;
        if (!Array.isArray(parsed)) {
          resolve([]);
          return;
        }
        const rows: CandidateLink[] = parsed.map((row: Record<string, unknown>) => ({
          media: String(row.media ?? "tiktok"),
          brand: String(row.brand ?? ""),
          url: String(row.url ?? ""),
          sku: String(row.sku ?? ""),
          productName: String(row.productName ?? row.product_name ?? ""),
          title: String(row.title ?? ""),
          snippet: String(row.snippet ?? ""),
          score: typeof row.score === "number" ? row.score : 0,
          authorHandle:
            typeof row.authorHandle === "string"
              ? row.authorHandle
              : typeof row.author_handle === "string"
                ? row.author_handle
                : undefined,
          sourceQuery:
            typeof row.sourceQuery === "string"
              ? row.sourceQuery
              : typeof row.source_query === "string"
                ? row.source_query
                : undefined,
        }));
        resolve(rows);
      } catch {
        if (code !== 0 && stderr) {
          reject(new Error(stderr.slice(0, 500)));
        } else {
          resolve([]);
        }
      }
    });

    child.stdin?.write(payload, "utf8");
    child.stdin?.end();
  });
}
