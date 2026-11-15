export const NAV_SECTIONS = [
  { id: "map", href: "/atlas", label: "ALL-SKY ATLAS" },
  { id: "spectral", href: "/spectral", label: "SPECTRAL EXPLORER" },
  { id: "research", href: "/research", label: "RESEARCH" },
  { id: "about", href: "/about", label: "ABOUT" },
  { id: "contact", href: "/contact", label: "CONTACT" },
] as const;

export type NavSectionId = typeof NAV_SECTIONS[number]["id"];
