# Upstream and attribution

NiimStudio is a desktop adaptation/fork, not a new protocol implementation.

| Component | Source | Baseline |
| --- | --- | --- |
| Label editor | https://github.com/MultiMote/niimblue | `82c5605780818299422a6acdf3180d87c569578d`, release `2026.9.0` |
| Printer protocol | https://github.com/MultiMote/niimbluelib | npm `@mmote/niimbluelib` **0.47.0**, exact pin |
| Protocol reference | https://github.com/MultiMote/niimbot-wiki | Read-only reference; no copied implementation |
| B1 Pro alternative reference | https://github.com/iscarelli/niimbot-web-bluetooth | Referenced by the shared conversation; no copied implementation |

The editor and protocol library include MIT licenses with MultiMote's copyright.
Retain `LICENSE`, upstream notices, and dependency licenses when distributing.
The original editor README is preserved in `README.upstream.md`. NiimBlueLib's
README also includes a vendor-affiliation/commercial-use warning; review that
warning and relevant rights before any commercial distribution. This project
does not assert NIIMBOT endorsement or claim access to proprietary assets.

## Update approach

1. Keep `upstream` pointing at MultiMote's repository. Do not push there.
2. Review upstream release notes and compare the pinned commit before merging.
3. Keep native code under `native/niimstudio` and `src/desktop`.
4. Audit lockfile changes. Do not replace NiimBlueLib with hand-coded packets
   just to make a test pass.
5. Run `npm run check`, `npm run test:smoke`, `npm audit`, then the hardware
   checklist for USB and BLE before changing support claims.

Small upstream-editor fixes in this fork: undo branching at the initial state,
image insertion history/autosave, save prevalidation and quota rollback,
CSP-compatible CSV parsing, print-head/job validation, and page-boundary batch
cancellation. Code 128 table typos for `$` and `)` are corrected and independently
decoded; QR cache invalidation and optional serialized quiet zones are fixed.
These are deliberately separate from native transport behavior.

Sass was updated to remove dependency advisories; Bootstrap 5's known Sass
import deprecations are isolated through Vite configuration. The initial audit
after updating the lockfile reports no known npm advisories; rerun it regularly.

## UI reference review

The editor controls were reviewed against the
[NiimBlue feature inventory](https://github.com/MultiMote/niimblue/wiki) and
[NIIMBOT's software overview](https://www.niimbot.com/us/soft/chenXiaoYin).
Common text/alignment and image/code tools are directly accessible; uncommon
geometry, batch variables, and print settings remain progressively disclosed.
The app uses its own layout and does not copy proprietary template collections.
Highlighting is intentionally thermal-safe white-on-black, not a promise of
color printing on a monochrome B1 Pro.
