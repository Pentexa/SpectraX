import type { Metadata } from "next";
import Image from "next/image";
import { SectionPage, sectionCard, sectionCopy, sectionLink } from "@/components/layout/SectionPage";

export const metadata: Metadata = {
  title: "About · SpectraX",
  description: "Meet the team behind SpectraX and see where its astronomy data comes from.",
};

const bands = [
  { wavelength: "0.98 µm", src: "/mission/spherex-098.jpg", alt: "Blue false-color SPHEREx image of a star field at 0.98 micrometers" },
  { wavelength: "3.29 µm", src: "/mission/spherex-329.jpg", alt: "Red false-color image of the same field with a bright dust cloud at 3.29 micrometers" },
];

const dataSources = [
  {
    name: "SPHEREx DR1 and QR3 spectral images",
    use: "Calibrated FITS exposures from NASA/IPAC IRSA feed image comparison, observation timelines and SPHEREx photometry. The viewer uses their quality masks.",
    links: [
      { label: "DR1 spectral images", href: "https://doi.org/10.26131/IRSA678" },
      { label: "QR3 spectral images", href: "https://doi.org/10.26131/IRSA662" },
    ],
  },
  {
    name: "SPHEREx DR1 All-Sky Cube",
    use: "Spectral Explorer uses the NASA/IPAC IRSA cube to plot surface brightness in 102 near-infrared channels and display single-channel or combined detector images.",
    links: [{ label: "DR1 cube", href: "https://doi.org/10.26131/IRSA679" }],
  },
  {
    name: "Gaia DR3",
    use: "ESA’s Gaia catalog, queried through CDS VizieR, provides the positions for the Gaia overlay.",
    links: [{ label: "Gaia DR3 catalog", href: "https://vizier.cfa.harvard.edu/viz-bin/VizieR?-source=I/355/gaiadr3" }],
  },
  {
    name: "AllWISE",
    use: "The WISE source catalog, queried through CDS VizieR, provides the positions for the AllWISE overlay.",
    links: [{ label: "AllWISE catalog", href: "https://vizier.cfa.harvard.edu/viz-bin/VizieR?-source=II/328/allwise" }],
  },
  {
    name: "AAVSO International Database",
    use: "Observations submitted by AAVSO contributors supply the optical reference light curves for RW Aurigae and R Draconis.",
    links: [{ label: "AAVSO data access", href: "https://archive.aavso.org/index.php/data-access" }],
  },
  {
    name: "SIMBAD",
    use: "CDS SIMBAD supplies the catalog references for the five challenge targets, including their positions, proper motions and parallaxes where available.",
    links: [{ label: "SIMBAD Astronomical Database", href: "https://simbad.cds.unistra.fr/simbad/" }],
  },
  {
    name: "Digitized Sky Survey 2 (DSS2)",
    use: "DSS2 color tiles are the atlas background in CDS Aladin Lite. The app retrieves them from STScI’s MAST mirror or NASA/IPAC IRSA.",
    links: [{ label: "DSS at STScI", href: "https://archive.stsci.edu/dss/" }],
  },
  {
    name: "SPHEREx mission imagery",
    use: "NASA/JPL-Caltech provided the home page panorama and the two example infrared images on this page.",
    links: [
      { label: "All-sky panorama", href: "https://www.jpl.nasa.gov/images/pia26600-spherexs-first-all-sky-map/" },
      { label: "Example band images", href: "https://science.nasa.gov/open-science/spherex-universe-map/" },
    ],
  },
];

const team = ["Ahmet Aras Akyasan", "Mustafa Emir Yayla", "Korhan Erol", "Nisanur Cakir"];
const aiCredits = [
  { role: "Coding assistance", model: "GPT SOL 6.1" },
  { role: "Code review assistance", model: "GLM 5.3" },
];

export default function AboutPage() {
  return (
    <SectionPage section="about" title="About SpectraX"
      intro="A citizen science tool built for the Planet X and SPHEREx challenge at the 2026 NASA Space Apps Challenge.">
      <div className="grid items-start gap-4 md:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)] md:gap-6">
        <section className={sectionCard}>
          <h2 className="text-xl font-semibold tracking-tight">The mission and the data</h2>
          <p className={`mt-3 ${sectionCopy}`}>
            NASA’s SPHEREx telescope surveys the sky in 102 near-infrared channels from 0.75 to 5 µm. SpectraX uses the public NASA/IPAC Infrared Science Archive (IRSA) to compare observations and inspect how surface brightness changes with wavelength.
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
      <div className="mt-4 grid items-start gap-4 md:mt-6 md:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)] md:gap-6">
        <section aria-labelledby="data-sources" className={sectionCard}>
          <h2 id="data-sources" className="text-xl font-semibold tracking-tight">Data sources</h2>
          <ul className="mt-2 divide-y divide-border-subtle">
            {dataSources.map((source) => (
              <li key={source.name} className="py-3.5 last:pb-0">
                <h3 className="text-[14px] font-medium">{source.name}</h3>
                <p className={`mt-1 ${sectionCopy}`}>{source.use}</p>
                <ul className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
                  {source.links.map((link) => (
                    <li key={link.href}>
                      <a href={link.href} className="inline-flex min-h-6 items-center gap-1.5 text-[12px] text-cyan-bright hover:underline">
                        {link.label} <span aria-hidden="true">↗</span>
                      </a>
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        </section>
        <section aria-labelledby="project-credits" className={sectionCard}>
          <h2 id="project-credits" className="text-xl font-semibold tracking-tight">Project credits</h2>
          <h3 className="mt-4 text-[13px] font-medium text-[#a7b9ca]">Built by</h3>
          <ul className="mt-1 divide-y divide-border-subtle">
            {team.map((name) => <li key={name} className="py-2.5 text-[14px] font-medium">{name}</li>)}
          </ul>
          <h3 className="mt-5 border-t border-border-subtle pt-4 text-[13px] font-medium text-[#a7b9ca]">AI assistance</h3>
          <dl className="mt-2 grid gap-2.5">
            {aiCredits.map(({ role, model }) => (
              <div key={role} className="rounded-sm border border-border-subtle bg-void/50 px-3 py-2.5">
                <dt className="text-[12px] text-[#a7b9ca]">{role}</dt>
                <dd className="mt-0.5 font-mono text-[13px] text-cyan-bright">{model}</dd>
              </div>
            ))}
          </dl>
        </section>
      </div>
    </SectionPage>
  );
}
