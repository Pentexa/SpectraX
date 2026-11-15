import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { Panorama } from "@/components/home/Panorama";
import { SiteHeader } from "@/components/layout/SiteHeader";

export const metadata: Metadata = {
  title: "SPECTRAX & SPHEREX",
  description: "Explore the SPHEREx infrared sky and compare observations across time with SpectraX.",
};

const atlasKeys = new Set(["ra", "dec", "fov", "target", "view", "mode", "epoch_a", "epoch_b", "gaia", "wise"]);

export default async function HomePage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = Object.entries(await searchParams);
  if (query.some(([key]) => atlasKeys.has(key) || /^archive_[a-h]$/.test(key))) {
    const atlasParams = new URLSearchParams();
    for (const [key, value] of query) {
      if (Array.isArray(value)) value.forEach((item) => atlasParams.append(key, item));
      else if (value !== undefined) atlasParams.append(key, value);
    }
    redirect(`/atlas?${atlasParams}`);
  }

  return (
    <div className="flex min-h-svh flex-col bg-void">
      <SiteHeader />
      <main className="relative isolate flex flex-1 items-end overflow-hidden">
        <Panorama />
        <div className="mx-auto w-full max-w-[1440px] px-6 pb-24 pt-28 sm:px-12 sm:pb-24 lg:px-20 lg:pb-28">
          <h1 className="flex flex-wrap gap-x-[0.22em] text-[clamp(3.25rem,8.5vw,9rem)] leading-[0.94] font-semibold tracking-[-0.065em] text-[#f3f8ff]">
            <span>SPECTRAX</span>{" "}
            <span className="whitespace-nowrap"><span className="text-cyan-bright">&amp;</span> SPHEREX</span>
          </h1>
          <p className="mt-6 max-w-lg text-[15px] leading-relaxed text-[#deebf7] sm:text-[17px]">
            Explore the sky in 102 infrared bands and compare observations across time.
          </p>
          <Link className="mt-7 inline-flex min-h-12 items-center gap-4 rounded-sm border border-cyan-bright bg-cyan-bright px-5 text-[13px] font-semibold text-[#07121b] transition-colors hover:bg-white focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-white"
            href="/atlas">
            Open sky atlas <span aria-hidden="true">↗</span>
          </Link>
        </div>
        <a href="https://www.jpl.nasa.gov/images/pia26600-spherexs-first-all-sky-map/"
          className="absolute bottom-6 left-6 text-[10px] text-[#c2d2e2] underline decoration-white/40 underline-offset-4 hover:text-white sm:bottom-10 sm:left-12 lg:left-20">
          Panorama · NASA/JPL-Caltech
        </a>
      </main>
    </div>
  );
}
