import path from "path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Pin the tracing root to this project (avoids "multiple lockfiles"
  // warnings when other lockfiles exist in the home directory).
  outputFileTracingRoot: path.join(__dirname),
};

export default nextConfig;
