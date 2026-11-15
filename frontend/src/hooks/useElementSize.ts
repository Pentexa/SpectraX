import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Tracks an element's CSS size via ResizeObserver.
 * Returns a callback ref to attach and the current { width, height }.
 * Using a callback ref means the observer re-attaches whenever the node
 * mounts/unmounts (e.g. conditional rendering) — unlike an effect that
 * only runs once with a plain ref.
 */
export function useElementSize<T extends HTMLElement>() {
  const observerRef = useRef<ResizeObserver | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  const ref = useCallback((node: T | null) => {
    observerRef.current?.disconnect();
    observerRef.current = null;
    if (!node) return;

    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect) {
        setSize({ width: rect.width, height: rect.height });
      }
    });
    observer.observe(node);
    observerRef.current = observer;
    setSize({ width: node.clientWidth, height: node.clientHeight });
  }, []);

  // Final cleanup on unmount (the callback ref alone doesn't fire then).
  useEffect(() => {
    return () => {
      observerRef.current?.disconnect();
      observerRef.current = null;
    };
  }, []);

  return { ref, size };
}
