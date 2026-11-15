import type { ReactNode } from "react";

export const controlClass = "rounded-[3px] border border-[#354b61] bg-[#15202b] px-2 py-1.5 text-[11px] text-[#d6e2ee] focus-visible:border-cyan-bright hover:border-cyan disabled:opacity-50";
export const inputClass = "min-w-0 rounded-[3px] border border-[#354b61] bg-[#0d131a] px-2 py-1.5 font-mono text-[11px] text-[#d6e2ee] focus-visible:border-cyan-bright";

export function Panel({ title, children, actions, className = "" }: {
  title: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <section className={`min-w-0 overflow-hidden rounded-[3px] border border-border-panel bg-gradient-to-b from-[rgba(20,29,39,0.94)] to-[rgba(15,22,30,0.96)] ${className}`}>
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border-subtle bg-[rgba(24,34,46,0.45)] px-3 py-2">
        <h2 className="text-[11.5px] font-medium uppercase tracking-[0.06em] text-[#cad6e2]">{title}</h2>
        {actions}
      </div>
      <div className="px-3 py-2.5">{children}</div>
    </section>
  );
}

export function Status({ children, error = false }: { children: ReactNode; error?: boolean }) {
  return <p role={error ? "alert" : "status"} className={`text-[11px] leading-relaxed ${error ? "text-[#f6b596]" : "text-[#a6b9cc]"}`}>{children}</p>;
}
