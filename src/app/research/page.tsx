import type { Metadata } from "next";
import Link from "next/link";
import { SectionPage, sectionCard, sectionCopy, sectionLink } from "@/components/layout/SectionPage";

export const metadata: Metadata = {
  title: "Research · SpectreX",
  description: "Compare observations of the five Planet X and SPHEREx challenge targets.",
};

const targetGroups = [
  {
    title: "Motion across epochs",
    targets: [
      { id: "barnard", name: "Barnard’s Star", description: "Nearby star with high proper motion." },
      { id: "epsilon-indi-b", name: "Epsilon Indi B", description: "Nearby brown dwarf binary. Compare the position of the source across visits." },
      { id: "wise-0855", name: "WISE 0855", description: "Cold, fast-moving brown dwarf. Compare its position against background sources." },
    ],
  },
  {
    title: "Brightness across epochs",
    targets: [
      { id: "rw-aurigae", name: "RW Aurigae", description: "Young variable star. Compare SPHEREx visits alongside the AAVSO optical reference curve." },
      { id: "r-draconis", name: "R Draconis", description: "Long-period variable star. Check the infrared measurement and coverage alongside its optical reference curve." },
    ],
  },
];

export default function ResearchPage() {
  return (
    <SectionPage section="research" title="Research"
      intro="Compare repeated SPHEREx observations of the five targets from the Planet X and SPHEREx challenge.">
      <div className="grid gap-4 md:grid-cols-2 md:gap-6">
        {targetGroups.map((group) => (
          <section key={group.title} className={sectionCard}>
            <h2 className="text-xl font-semibold tracking-tight">{group.title}</h2>
            <ul className="mt-3 divide-y divide-border-subtle">
              {group.targets.map((target) => (
                <li key={target.id} className="py-3 last:pb-0">
                  <Link className="inline-flex items-center gap-2 text-[14px] font-medium text-cyan-bright hover:underline"
                    href={{ pathname: "/atlas", query: { target: target.id, view: "images" } }}>
                    {target.name} <span aria-hidden="true">↗</span>
                  </Link>
                  <p className={`mt-1 ${sectionCopy}`}>{target.description}</p>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
      <section className={`mt-4 md:mt-6 ${sectionCard}`}>
        <h2 className="text-xl font-semibold tracking-tight">Comparing observations</h2>
        <p className={`mt-2 max-w-3xl ${sectionCopy}`}>
          Use Blink A/B to spot motion. For brightness changes, check the matched bandpass, coverage and quality flags before interpreting a difference image. The verification report records which measurements met those checks.
        </p>
        <a className={`mt-4 ${sectionLink}`}
          href="https://github.com/Pentexa/SpectraX/blob/main/docs/benchmarks/CHALLENGE_TARGETS.md">
          Read the target verification report <span aria-hidden="true" className="ml-2">↗</span>
        </a>
      </section>
    </SectionPage>
  );
}
