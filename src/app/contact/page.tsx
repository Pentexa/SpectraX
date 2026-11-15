import type { Metadata } from "next";
import { SectionPage, sectionCard, sectionCopy, sectionLink } from "@/components/layout/SectionPage";

export const metadata: Metadata = {
  title: "Contact · SpectraX",
  description: "Send SpectraX feedback, report a reproducible issue, or reach the IRSA Help Desk.",
};

export default function ContactPage() {
  return (
    <SectionPage section="contact" title="Contact"
      intro="Share feedback on SpectraX or find help with the SPHEREx archive.">
      <div className="grid gap-4 md:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)] md:gap-6">
        <section className={sectionCard}>
          <h2 className="text-xl font-semibold tracking-tight">SpectraX project</h2>
          <p className={`mt-3 ${sectionCopy}`}>
            Open a GitHub issue for a bug, feature request or research collaboration. For an unexpected result, include the share link, release, and the steps that led to it.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <a className={sectionLink} href="https://github.com/Pentexa/frsphere/issues/new">Report a website issue <span aria-hidden="true" className="ml-2">↗</span></a>
            <a className={sectionLink} href="https://github.com/Pentexa/SpectraX/issues/new">Report an API issue <span aria-hidden="true" className="ml-2">↗</span></a>
          </div>
        </section>
        <section className={sectionCard}>
          <h2 className="text-xl font-semibold tracking-tight">SPHEREx archive support</h2>
          <p className={`mt-3 ${sectionCopy}`}>For questions about a release, FITS products, or direct archive access, contact the NASA/IPAC IRSA Help Desk.</p>
          <a className={`mt-5 ${sectionLink}`} href="https://irsa.ipac.caltech.edu/docs/help_desk.html">
            Open IRSA Help Desk <span aria-hidden="true" className="ml-2">↗</span>
          </a>
        </section>
      </div>
    </SectionPage>
  );
}
