import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  /** Monorepo: repo has root + frontend lockfiles; trace from repo root on Vercel. */
  outputFileTracingRoot: path.join(__dirname, ".."),
};

export default nextConfig;
