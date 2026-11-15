/**
 * Early unhandled-rejection guard for the Aladin Lite runtime.
 *
 * Aladin's internals kick off network fetches (survey properties, HiPS tiles)
 * while creating the viewer. When the CDS server is unreachable, some of
 * those rejections escape without an internal handler and surface as
 * "TypeError: Failed to fetch" / "HiPS ... error" unhandled rejections.
 *
 * Next.js's dev overlay registers its own `unhandledrejection` listener and
 * records every rejection unconditionally (it never checks
 * `event.defaultPrevented`), so a late listener cannot stop the crash-style
 * overlay. This script is loaded with `strategy="beforeInteractive"`, which
 * registers BEFORE the Next.js client bundles, so it can claim these
 * rejections first:
 *
 *   1. preventDefault()           — suppress the default browser report
 *   2. stopImmediatePropagation() — keep the dev overlay listener out
 *   3. re-dispatch `aladin:tile-failure` — lets the atlas component degrade
 *      gracefully (offline badge / retry screen)
 *
 * Only network-failure-class messages are suppressed. The application's own
 * fetch layer (src/lib/api/client.ts) always catches its errors, so any
 * *unhandled* network rejection here originates from Aladin.
 */
(function () {
  "use strict";
  if (window.__spectraxAladinGuardInstalled) return;
  window.__spectraxAladinGuardInstalled = true;

  var NETWORK_FAILURE = /failed to fetch|networkerror|load failed|fetch failed/i;
  var HIPS_FAILURE = /^HiPS .+error/i;

  window.addEventListener("unhandledrejection", function (event) {
    var reason = event.reason;
    var message =
      reason instanceof Error
        ? reason.message
        : reason &&
          typeof reason === "object" &&
          typeof reason.message === "string"
          ? reason.message
          : String(reason == null ? "" : reason);

    var isNetworkFailure = NETWORK_FAILURE.test(message);
    var isHiPSFailure = HIPS_FAILURE.test(message);
    if (!isNetworkFailure && !isHiPSFailure) return;

    event.preventDefault();
    event.stopImmediatePropagation();

    window.dispatchEvent(
      new CustomEvent("aladin:tile-failure", {
        detail: { message: message, network: isNetworkFailure },
      }),
    );
  });
})();
