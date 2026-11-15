import path from "path";
import type { NextConfig } from "next";
import { PHASE_DEVELOPMENT_SERVER } from "next/constants";

const nextConfig = (phase: string): NextConfig => ({
  // Keep production builds from replacing files the running dev server uses.
  distDir: phase === PHASE_DEVELOPMENT_SERVER ? ".next-dev" : ".next",
  reactStrictMode: true,
  experimental: {
    // The first request for an uncached SPHEREx cube can take up to 240 seconds.
    proxyTimeout: 270_000,
  },
  async rewrites() {
    const backend = (process.env.SPECTREX_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8765").replace(/\/$/, "");
    return [{ source: "/science/api/:path*", destination: `${backend}/api/:path*` }];
  },
  // Pin the tracing root to this project (avoids "multiple lockfiles"
  // warnings when other lockfiles exist in the home directory).
  outputFileTracingRoot: path.join(__dirname),
});

export default nextConfig;
