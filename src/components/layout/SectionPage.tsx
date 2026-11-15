import type { ReactNode } from "react";
import type { NavSectionId } from "@/lib/constants/nav";
import { SiteFooter } from "./SiteFooter";
import { SiteHeader } from "./SiteHeader";

export const sectionCard = "min-w-0 rounded-sm border border-border-panel bg-panel p-5 sm:p-6";
export const sectionCopy = "text-[13px] leading-relaxed text-[#a7b9ca]";
export const sectionLink = "inline-flex min-h-10 items-center rounded-sm border border-[#354b61] bg-[#15202b] px-3 font-mono text-[11px] text-cyan-bright transition-colors hover:border-cyan hover:bg-[#192a38]";

export function SectionPage({ section, title, intro, children }: {
  section: Exclude<NavSectionId, "map">;
  title: string;
  intro: string;
  children: ReactNode;
}) {
  return (
    <div className="flex min-h-dvh flex-col bg-[radial-gradient(ellipse_at_50%_0%,#162333_0%,#090d12_58%)]">
      <SiteHeader activeSection={section} />
      <main className="mx-auto w-full max-w-[1160px] flex-1 px-4 pb-12 pt-9 sm:px-7 sm:pt-14">
        <div className="mb-6 border-b border-border-subtle pb-6 sm:mb-8 sm:pb-8">
          <div className="mb-4 h-px w-12 bg-cyan" aria-hidden="true" />
          <h1 className="text-[clamp(2.75rem,6vw,4.5rem)] font-semibold leading-[1.05] tracking-[-0.04em] text-[#eef4fa]">
            {title}
          </h1>
          <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[#a7b9ca] sm:mt-4 sm:text-base">{intro}</p>
        </div>
        {children}
      </main>
      <SiteFooter />
    </div>
  );
}
