import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const backend = (process.env.SPECTREX_API_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8765").replace(/\/$/, "");
    return [{ source: "/science/api/:path*", destination: `${backend}/api/:path*` }];
  },
  // Pin the tracing root to this project (avoids "multiple lockfiles"
  // warnings when other lockfiles exist in the home directory).
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
