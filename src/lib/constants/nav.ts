export interface NavSection {
  id: string;
  label: string;
  title: string;
  body: string;
}

/** Top navigation sections. `map` is the live dashboard, the rest open the info modal. */
export const NAV_SECTIONS: NavSection[] = [
  {
    id: "map",
    label: "ALL-SKY ATLAS",
    title: "ALADIN LITE — ALL-SKY ATLAS",
    body: "",
  },
  {
    id: "spectral",
    label: "SPECTRAL EXPLORER",
    title: "SPECTRAL EXPLORER — 102 NIR BANDS",
    body:
      "The SPHEREx space telescope scans the near-infrared spectrum between 0.75 and 5.0 microns in 102 separate wavelength bands. Use the multi-band selector in the right panel to activate the bands you are interested in and inspect the flux variations on the all-sky map.",
  },
  {
    id: "research",
    label: "RESEARCH",
    title: "RESEARCH — TRANSIENT & PLANET X",
    body:
      "Comparing all-sky maps refreshed every 6 months reveals high-proper-motion brown dwarfs, exoplanet candidates, and possible signals of a ninth planet (Planet X) beyond the Solar System.",
  },
  {
    id: "about",
    label: "ABOUT",
    title: "ABOUT SPECTREX",
    body:
      "Spectrex is an interactive analysis portal designed for citizen scientists to examine moving celestial objects and spectral anomalies in real time using the SPHEREx all-sky survey.",
  },
  {
    id: "contact",
    label: "CONTACT",
    title: "CONTACT — MISSION SUPPORT",
    body:
      "For data access and science collaborations: contact@spectrex.dev • Pasadena, CA.",
  },
];

export function getNavSection(id: string): NavSection | undefined {
  return NAV_SECTIONS.find((s) => s.id === id);
}
