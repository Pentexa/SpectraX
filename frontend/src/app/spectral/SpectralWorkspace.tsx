"use client";

import Link from "next/link";
import { useState } from "react";
import { sectionCard, sectionCopy, sectionLink } from "@/components/layout/SectionPage";
import { FieldPanel } from "@/components/home/science/FieldPanel";
import { SpectrumPanel } from "@/components/home/science/SpectrumPanel";
import type { SkyField } from "@/lib/api/science";

function fieldUrl(field: SkyField) {
  return `/spectral?${new URLSearchParams({ ra: String(field.ra), dec: String(field.dec), fov: String(field.fov) })}`;
}

export function SpectralWorkspace({ initialField }: { initialField: SkyField }) {
  const [field, setField] = useState(initialField);

  function updateField(next: SkyField) {
    setField(next);
    window.history.replaceState(null, "", fieldUrl(next));
  }

  return (
    <div className="grid items-start gap-4 md:grid-cols-[280px_minmax(0,1fr)] md:grid-rows-[auto_1fr] md:gap-6">
      <div className="min-w-0 md:col-start-1 md:row-start-1">
        <FieldPanel field={field} allowEmbed={false} onCoordinates={(position) => updateField({ ...field, ...position })}
          onFov={(fov) => updateField({ ...field, fov })}
          onShare={() => new URL(fieldUrl(field), window.location.origin).href} />
      </div>
      <div className="grid min-w-0 gap-4 md:col-start-2 md:row-span-2 md:row-start-1">
        <dl className="grid grid-cols-3 divide-x divide-border-panel rounded-sm border border-border-panel bg-panel">
          <div className="grid gap-1 px-3 py-3.5 sm:px-5">
            <dt className="text-[11px] text-[#a7b9ca]">Wavelength range</dt>
            <dd className="font-mono text-sm text-cyan-bright sm:text-base">0.75–5 µm</dd>
          </div>
          <div className="grid gap-1 px-3 py-3.5 sm:px-5">
            <dt className="text-[11px] text-[#a7b9ca]">Detectors</dt>
            <dd className="font-mono text-sm text-cyan-bright sm:text-base">6</dd>
          </div>
          <div className="grid gap-1 px-3 py-3.5 sm:px-5">
            <dt className="text-[11px] text-[#a7b9ca]">Data product</dt>
            <dd className="font-mono text-sm text-cyan-bright sm:text-base">DR1 cube</dd>
          </div>
        </dl>
        <SpectrumPanel key={`${field.ra}:${field.dec}`} field={field} explorer />
      </div>
      <section className={`md:col-start-1 md:row-start-2 ${sectionCard}`}>
        <h2 className="mb-2 text-base font-semibold">Reading the spectrum</h2>
        <p className={sectionCopy}>
          The spectrum measures surface brightness at the selected coordinate. Increase the field width to see more of the surrounding sky. DR1 cube pixels span 12.9 arcseconds.
        </p>
        <Link className={`mt-4 ${sectionLink}`} href={{ pathname: "/atlas", query: { ...field, view: "atlas" } }}>
          Open field in atlas <span aria-hidden="true" className="ml-2">↗</span>
        </Link>
      </section>
    </div>
  );
}
