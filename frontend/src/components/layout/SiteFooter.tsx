export function SiteFooter() {
  const items = ["SPECTRAX", "SPHEREX MISSION", "PLANET X PORTAL", "CALTECH", "2026"];

  return (
    <footer className="flex flex-wrap items-center justify-center gap-x-3.5 gap-y-1 px-3.5 pb-2 pt-1.5 text-[10px] tracking-[0.14em] text-[#6f8296]">
      {items.map((item, i) => (
        <span key={item} className="flex items-center gap-3.5">
          {i > 0 && <span className="text-[#6f8296]">•</span>}
          <span>{item}</span>
        </span>
      ))}
    </footer>
  );
}
