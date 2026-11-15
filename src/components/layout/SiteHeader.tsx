"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { NAV_SECTIONS, type NavSectionId } from "@/lib/constants/nav";

interface SiteHeaderProps {
  activeSection: NavSectionId;
  onOpenAtlas?: () => void;
  spectralHref?: string;
  dataSource?: "loading" | "api" | "mock" | "offline";
}

export function SiteHeader({ activeSection, onOpenAtlas, spectralHref, dataSource }: SiteHeaderProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement | null>(null);
  const navRef = useRef<HTMLElement | null>(null);

  /* Close the mobile menu on outside click or Escape. */
  useEffect(() => {
    if (!menuOpen) return;

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null;
      if (
        target &&
        !navRef.current?.contains(target) &&
        !menuButtonRef.current?.contains(target)
      ) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        menuButtonRef.current?.focus();
      }
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  return (
    <header className="relative flex h-[62px] flex-shrink-0 items-center justify-between gap-3 border-b border-border-subtle bg-gradient-to-b from-[#0f161f] to-[#0c1219] px-4 sm:px-[22px]">
      <div className="flex items-center gap-3.5">
        <Link href="/" className="text-[19px] font-semibold leading-tight tracking-[0.36em] text-[#eef4fa]">
          SPECTREX
        </Link>
        {dataSource === "mock" && (
          <span
            className="ml-2 rounded border border-cyan-muted/50 px-1.5 py-0.5 font-mono text-[9px] tracking-wider text-cyan-bright"
            title="Backend unreachable — showing mock data"
          >
            MOCK DATA
          </span>
        )}
        {dataSource === "api" && (
          <span className="ml-2 rounded border border-cyan-muted/50 px-1.5 py-0.5 font-mono text-[9px] tracking-wider text-cyan-bright">
            LIVE API
          </span>
        )}
        {dataSource === "offline" && (
          <span className="rounded border border-border-panel px-1.5 py-0.5 font-mono text-[9px] text-text-muted">
            API OFFLINE
          </span>
        )}
      </div>

      <button
        ref={menuButtonRef}
        className="rounded border border-border-panel bg-panel px-2.5 py-1.5 text-sm text-text-primary md:hidden"
        type="button"
        aria-label="Toggle navigation menu"
        aria-expanded={menuOpen}
        aria-controls="site-nav"
        onClick={() => setMenuOpen((open) => !open)}
      >
        ☰
      </button>

      <nav
        ref={navRef}
        id="site-nav"
        aria-label="Main navigation"
        className={`absolute left-0 right-0 top-[62px] z-50 flex-col gap-2.5 border-b border-border-panel bg-[#0f161f] px-5 py-3 md:static md:z-auto md:flex md:flex-row md:items-center md:gap-4 md:border-0 md:bg-transparent md:px-0 md:py-0 lg:gap-6 ${
          menuOpen ? "flex" : "hidden"
        }`}
      >
        {NAV_SECTIONS.map((section) => (
          <Link
            key={section.id}
            href={section.id === "spectral" ? spectralHref ?? section.href : section.href}
            aria-current={activeSection === section.id ? "page" : undefined}
            className={`relative self-start whitespace-nowrap pb-1.5 pt-1.5 text-[11.5px] font-normal tracking-[0.08em] transition-colors duration-200 ${
              activeSection === section.id
                ? "text-[#eef5fc] after:absolute after:inset-x-0 after:-bottom-0.5 after:h-px after:bg-cyan after:shadow-[0_0_6px_var(--color-cyan)]"
                : "text-[#96a7ba] hover:text-[#eef5fc]"
            }`}
            onClick={(event) => {
              if (section.id === "map" && onOpenAtlas && !event.metaKey && !event.ctrlKey && !event.shiftKey && !event.altKey) {
                event.preventDefault();
                onOpenAtlas();
              }
              setMenuOpen(false);
            }}
          >
            {section.label}
          </Link>
        ))}
      </nav>
    </header>
  );
}
