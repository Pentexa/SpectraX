import { useEffect, useRef } from "react";

/**
 * Shared animation clock.
 *
 * A single `AnimationClock` instance is created per dashboard mount.
 * Each canvas component runs its own `requestAnimationFrame` loop and reads
 * `clock.current` — nothing re-renders at 60fps.
 */
export interface AnimationClock {
  current: number;
  /** Registers a consumer; returns a detach function. */
  attach: () => () => void;
}

/** Creates a clock that advances while at least one client is attached. */
export function createAnimationClock(): AnimationClock {
  const time = { current: 0 };
  let running = false;
  let last = performance.now();
  let rafId = 0;
  let clients = 0;

  const tick = (now: number) => {
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    time.current += dt;
    rafId = requestAnimationFrame(tick);
  };

  const start = () => {
    if (!running) {
      running = true;
      last = performance.now();
      rafId = requestAnimationFrame(tick);
    }
  };

  const stop = () => {
    if (running) {
      running = false;
      cancelAnimationFrame(rafId);
    }
  };

  return {
    get current() {
      return time.current;
    },
    attach() {
      clients += 1;
      start();
      return () => {
        clients -= 1;
        if (clients <= 0) stop();
      };
    },
  };
}

/**
 * Attaches a component to a shared clock.
 * The callback receives the current animation time on every frame.
 * When `clock` is null the hook is inert (no animation attached).
 */
export function useAnimationClock(
  clock: AnimationClock | null | undefined,
  callback: (time: number) => void,
) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  useEffect(() => {
    if (!clock) return;

    const detach = clock.attach();
    let rafId = 0;

    const loop = () => {
      cbRef.current(clock.current);
      rafId = requestAnimationFrame(loop);
    };
    rafId = requestAnimationFrame(loop);

    return () => {
      cancelAnimationFrame(rafId);
      detach();
    };
  }, [clock]);
}
