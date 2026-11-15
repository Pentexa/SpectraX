/**
 * Ambient module declaration for `aladin-lite` (npm package).
 * The package ships plain JS without types; declare the small API surface
 * we use. Shape is structurally compatible with `AladinInstance` in
 * `./aladin.d.ts`.
 */

declare module "aladin-lite" {
  export interface AladinLiteInstance {
    /** Project sky coordinates (degrees) to CSS pixels relative to the viewport. */
    world2pix: (ra: number, dec: number) => { 0: number; 1: number } | null;
    /** Project CSS pixels to sky coordinates (degrees). */
    pix2world: (x: number, y: number) => [number, number] | null;
    on: (event: string, handler: (payload?: unknown) => void) => void;
    remove: () => void;
    getSize: () => [number, number];
  }

  export interface AladinLiteModule {
    /** Readiness promise (resolves once the WebGL/wasm core is ready). */
    init: Promise<void>;
    aladin: (
      target: HTMLElement | string,
      options?: Record<string, unknown>,
    ) => AladinLiteInstance;
  }

  const Aladin: AladinLiteModule;
  export default Aladin;
}
