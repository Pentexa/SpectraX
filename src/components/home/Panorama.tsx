"use client";

import { useEffect, useRef, useState } from "react";

export function Panorama() {
  const video = useRef<HTMLVideoElement>(null);
  const [playing, setPlaying] = useState(false);
  const [unavailable, setUnavailable] = useState(false);

  useEffect(() => {
    const player = video.current;
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (!player) return;

    function applyMotionPreference() {
      if (motion.matches) player?.pause();
      else void player?.play().catch(() => setPlaying(false));
    }

    applyMotionPreference();
    motion.addEventListener("change", applyMotionPreference);
    return () => motion.removeEventListener("change", applyMotionPreference);
  }, []);

  return (
    <>
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[#061019]">
        <video ref={video} className="h-full w-full object-cover [object-position:50%_45%]" aria-hidden="true"
          src="/mission/spherex-panorama.mp4" poster="/mission/spherex-panorama.jpg" muted loop playsInline preload="none"
          onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onError={() => setUnavailable(true)} />
        <div className="absolute inset-0 bg-[linear-gradient(90deg,rgba(5,9,15,.65),rgba(5,9,15,.36)_58%,rgba(5,9,15,.1)),linear-gradient(0deg,rgba(5,9,15,.93),transparent_76%)]" />
      </div>
      {!unavailable && (
        <button type="button" className="absolute right-4 bottom-4 z-10 flex min-h-10 items-center gap-2 rounded-sm border border-white/30 bg-[#090d12]/70 px-3 text-[11px] text-[#eef5fc] backdrop-blur-sm hover:border-cyan-bright focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white sm:right-8 sm:bottom-7"
          onClick={() => {
            const player = video.current;
            if (!player) return;
            if (player.paused) void player.play().catch(() => setPlaying(false));
            else player.pause();
          }}>
          <span className="text-cyan-bright" aria-hidden="true">{playing ? "Ⅱ" : "▶"}</span>
          {playing ? "Pause video" : "Play video"}
        </button>
      )}
    </>
  );
}
