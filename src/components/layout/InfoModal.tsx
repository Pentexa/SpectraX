"use client";

import { useEffect, useRef } from "react";
import { getNavSection } from "@/lib/constants/nav";

interface InfoModalProps {
  sectionId: string | null;
  onClose: () => void;
}

const FOCUSABLE =
  "a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex='-1'])";

export function InfoModal({ sectionId, onClose }: InfoModalProps) {
  const section = sectionId ? getNavSection(sectionId) : undefined;
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  /* Focus management, Escape/focus-trap and scroll lock while open. */
  useEffect(() => {
    if (sectionId === null) return;

    const previouslyFocused = document.activeElement as HTMLElement | null;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    // Move focus into the dialog (first focusable, else the dialog itself).
    const dialog = dialogRef.current;
    const first = dialog?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? dialog)?.focus();

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onCloseRef.current();
        return;
      }
      if (event.key !== "Tab") return;

      // Minimal focus trap: cycle Tab within the dialog.
      const container = dialogRef.current;
      if (!container) return;
      const items = Array.from(
        container.querySelectorAll<HTMLElement>(FOCUSABLE),
      ).filter((el) => el.offsetParent !== null);
      if (items.length === 0) return;
      const active = document.activeElement;
      const firstItem = items[0];
      const lastItem = items[items.length - 1];
      if (event.shiftKey) {
        if (active === firstItem || !container.contains(active)) {
          event.preventDefault();
          lastItem.focus();
        }
      } else if (active === lastItem || !container.contains(active)) {
        event.preventDefault();
        firstItem.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);

    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousOverflow;
      previouslyFocused?.focus?.();
    };
  }, [sectionId]);

  if (!section) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-[rgba(6,10,15,0.78)] p-5 backdrop-blur-sm"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="info-modal-title"
        tabIndex={-1}
        className="w-full max-w-[520px] overflow-hidden rounded border border-[#354c63] bg-[#121b25] shadow-[0_18px_45px_rgba(0,0,0,0.65)] focus:outline-none"
      >
        <div className="flex items-center justify-between border-b border-[#223040] bg-[#16222f] px-4 py-3">
          <h3
            id="info-modal-title"
            className="text-[13px] font-medium tracking-[0.08em] text-cyan-bright"
          >
            {section.title}
          </h3>
          <button
            type="button"
            className="cursor-pointer border-0 bg-transparent text-lg leading-none text-[#96a8ba] transition-colors hover:text-white"
            onClick={onClose}
            aria-label="Close"
          >
            &times;
          </button>
        </div>
        <div className="px-4 py-4 text-[12px] leading-relaxed text-[#bfd0e0]">
          {section.body}
        </div>
      </div>
    </div>
  );
}
