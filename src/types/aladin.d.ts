/**
 * Ambient types for Aladin Lite v3 (CDS sky atlas).
 * Loaded from CDN at runtime — the API surface we touch is deliberately small.
 *
 * v3 shape: `A.init` is a readiness Promise; the viewer is created with
 * `A.aladin(target, options)`.
 */

export {};

declare global {
  interface Window {
    A?: {
      /** Readiness promise (resolves once the WebGL/wasm core is ready). */
      init: Promise<void>;
      aladin: (
        target: HTMLElement | string,
        options?: Record<string, unknown>,
      ) => AladinInstance;
    };
  }
}

export interface AladinInstance {
  /** Project sky coordinates (degrees) to CSS pixels relative to the viewport. */
  world2pix: (ra: number, dec: number) => { 0: number; 1: number } | null;
  /** Project CSS pixels to sky coordinates (degrees). */
  pix2world: (x: number, y: number) => [number, number] | null;
  on: (event: string, handler: (payload?: unknown) => void) => void;
  remove: () => void;
  getSize: () => [number, number];
}

declare module "aladin-lite" {
  const Aladin: {
    /** Readiness promise (resolves once the WebGL/wasm core is ready). */
    init: Promise<void>;
    aladin: (
      target: HTMLElement | string,
      options?: Record<string, unknown>,
    ) => AladinInstance;
  };
  export default Aladin;
}
