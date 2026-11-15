import type { Metadata } from "next";
import { SectionPage } from "@/components/layout/SectionPage";
import { SpectralWorkspace } from "./SpectralWorkspace";

export const metadata: Metadata = {
  title: "Spectral Explorer · SpectreX",
  description: "Explore the 102 calibrated near-infrared channels of the SPHEREx DR1 all-sky cube.",
};

function parseCoordinate(value: string | string[] | undefined) {
  return typeof value === "string" && value.trim() ? Number(value) : NaN;
}

export default async function SpectralPage({ searchParams }: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const ra = parseCoordinate(query.ra);
  const dec = parseCoordinate(query.dec);
  const fov = parseCoordinate(query.fov);
  const validPosition = ra >= 0 && ra < 360 && dec >= -90 && dec <= 90;
  const field = {
    ra: validPosition ? ra : 269.45,
    dec: validPosition ? dec : 4.7,
    fov: fov >= 0.01 && fov <= 0.2 ? fov : 0.05,
  };

  return (
    <SectionPage section="spectral" title="Spectral Explorer"
      intro="Inspect a sky position across 102 near-infrared bands in the SPHEREx DR1 cube.">
      <SpectralWorkspace key={`${field.ra}:${field.dec}:${field.fov}`} initialField={field} />
    </SectionPage>
  );
}
