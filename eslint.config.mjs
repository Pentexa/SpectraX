import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  // Global ignores must be a standalone object to apply to every file,
  // including this config file itself.
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      ".next-dev/**",
      "out/**",
      "next-env.d.ts",
      "eslint.config.mjs",
      // Vendored third-party runtime (minified ESM bundle).
      "public/vendor/**",
    ],
  },
  // Framework + TypeScript rule sets (Next.js).
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default eslintConfig;
