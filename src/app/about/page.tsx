import type { Metadata } from "next";
import Image from "next/image";
import { SectionPage, sectionCard, sectionCopy, sectionLink } from "@/components/layout/SectionPage";

export const metadata: Metadata = {
  title: "About · SpectreX",
  description: "Learn about the SpectreX project, SPHEREx and the data behind the explorer.",
};

const bands = [
  { wavelength: "0.98 µm", src: "/mission/spherex-098.jpg", alt: "Blue false-color SPHEREx image of a star field at 0.98 micrometers" },
  { wavelength: "3.29 µm", src: "/mission/spherex-329.jpg", alt: "Red false-color image of the same field with a bright dust cloud at 3.29 micrometers" },
];

export default function AboutPage() {
  return (
    <SectionPage section="about" title="About SpectreX"
      intro="A citizen science tool built for the Planet X and SPHEREx challenge at the 2026 NASA Space Apps Challenge.">
      <div className="grid items-start gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] md:gap-6">
        <section className={sectionCard}>
          <h2 className="text-xl font-semibold tracking-tight">The mission and the data</h2>
          <p className={`mt-3 ${sectionCopy}`}>
            NASA’s SPHEREx telescope surveys the sky in 102 near-infrared channels from 0.75 to 5 µm. SpectreX uses the public NASA/IPAC Infrared Science Archive (IRSA) to compare observations and inspect how surface brightness changes with wavelength.
          </p>
          <dl className="mt-5 grid gap-3 border-y border-border-subtle py-4">
            <div className="grid grid-cols-[4rem_minmax(0,1fr)] gap-2">
              <dt className="font-mono text-cyan-bright">DR1</dt>
              <dd className={sectionCopy}>Spectral images and the all-sky cube used by Spectral Explorer.</dd>
            </div>
            <div className="grid grid-cols-[4rem_minmax(0,1fr)] gap-2">
              <dt className="font-mono text-cyan-bright">QR3</dt>
              <dd className={sectionCopy}>Additional spectral images from later surveys.</dd>
            </div>
          </dl>
          <div className="mt-5 flex flex-wrap gap-2">
            <a className={sectionLink} href="https://science.nasa.gov/mission/spherex/">NASA mission overview <span aria-hidden="true" className="ml-2">↗</span></a>
            <a className={sectionLink} href="https://irsa.ipac.caltech.edu/spherex-archive-documentation/spherex-data-access/">IRSA data access <span aria-hidden="true" className="ml-2">↗</span></a>
          </div>
        </section>
        <figure className="min-w-0 overflow-hidden rounded-sm border border-border-panel bg-panel">
          <div className="grid grid-cols-2 divide-x divide-border-panel bg-void">
            {bands.map((band) => (
              <div key={band.wavelength} className="relative aspect-video">
                <Image src={band.src} alt={band.alt} fill sizes="(max-width: 767px) 48vw, 300px" className="object-contain" />
                <span className="absolute bottom-2 left-2 rounded-sm bg-[#090d12]/90 px-2 py-1 font-mono text-[11px] text-text-primary">{band.wavelength}</span>
              </div>
            ))}
          </div>
          <figcaption className="p-4 text-[12px] leading-relaxed text-[#a7b9ca]">
            The same field in two SPHEREx bands. The dust cloud is visible at 3.29 µm. Visible colors represent infrared wavelengths.
            <a className="mt-2 block text-cyan-bright hover:underline" href="https://science.nasa.gov/open-science/spherex-universe-map/">Image credit: NASA/JPL-Caltech</a>
          </figcaption>
        </figure>
      </div>
    </SectionPage>
  );
}
