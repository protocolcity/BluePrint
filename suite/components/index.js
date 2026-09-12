/**
 * suite/components — reusable UI kit (pc-294).
 *
 * Contract: each export is mount(el, props) → { update, destroy }.
 * Pages own data; components own DOM. No framework.
 *
 * Load on a room host:
 *   <script type="module" src="/components/index.js"></script>
 *   // or: import { SuiteUI } from "/components/index.js";
 * Then: SuiteUI.ErrorBanner.mount(el, props)
 *
 * CSS auto-links /components/suite-ui.css on first mount.
 *
 * Adopter wiring (Desk tray / shared pathbar) is a follow-up slice —
 * multi-agent dispatch 2026-07-21: greenfield kit only this pass.
 */
import { mountErrorBanner } from "./error-banner.js";
import { mountEmptyState } from "./empty-state.js";
import { mountLoadingBlock } from "./loading-block.js";
import { mountPathbar } from "./pathbar.js";
import { mountSlip } from "./slip.js";
import { mountLiveTail } from "./live-tail.js";
import { esc, ensureSuiteUiCss, prefersReducedMotion } from "./util.js";

export var SuiteUI = {
  ErrorBanner: { mount: mountErrorBanner },
  EmptyState: { mount: mountEmptyState },
  LoadingBlock: { mount: mountLoadingBlock },
  Pathbar: { mount: mountPathbar },
  Slip: { mount: mountSlip },
  LiveTail: { mount: mountLiveTail },
  /** Optional theme hook (pages may set; components rarely read). */
  theme: null,
  /** Helpers re-exported for page authors. */
  esc: esc,
  ensureCss: ensureSuiteUiCss,
  prefersReducedMotion: prefersReducedMotion,
};

// Bridge for classic scripts / soft-nav hosts that expect a global.
if (typeof globalThis !== "undefined") {
  globalThis.SuiteUI = SuiteUI;
}

export {
  mountErrorBanner,
  mountEmptyState,
  mountLoadingBlock,
  mountPathbar,
  mountSlip,
  mountLiveTail,
};

export default SuiteUI;
