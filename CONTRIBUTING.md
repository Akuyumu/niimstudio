# Contributing

Thanks for helping improve NiimStudio. Open issues and pull requests on
[Akuyumu/niimstudio](https://github.com/Akuyumu/niimstudio), not on NiimBlue's
repository unless you are deliberately contributing an upstream change.

## Layout and boundaries

- `native/niimstudio/`: GTK window, safe asset/bridge handling, themes, private
  device history, BlueZ pairing/BLE, and USB serial transport.
- `src/desktop/`: NiimStudio UI, template/code dialogs, bridge/client adapter,
  reconnect loop, styles, and isolated GUI test helpers.
  `media.ts`/`StockSetup.svelte` implement validated auto-stock setup and the
  fallback preset cards; keep technical size/DPI knobs out of the native UI.
- `src/components/`, `src/fabric-object/`, `src/utils/`: label engine derived from
  NiimBlue. Keep changes focused so upstream updates remain reviewable.
- `tests/`, `scripts/`, `packaging/`, `docs/`: checks, developer/user launchers,
  desktop icon, architecture, setup, and honest support status.
- `standalone-apps/`, `.gitea/`, Docker files and `README.upstream.md` are retained
  upstream reference material, not NiimStudio's Linux release targets.

## Development and checks

Use a feature branch based on `main`. Keep pull requests small, avoid unrelated
reformatting, and preserve attribution. AI-assisted contributions are welcome,
but disclose them, understand the changes, and test them.

```bash
npm ci --ignore-scripts
npm run check
npm run test:smoke
npm run test:restart
npm audit
```

`npm run dev` runs the retained browser editor for engine comparisons. The desktop
app uses the built `dist/` output: rebuild after editing Svelte/TypeScript/CSS,
then restart the app after saving work. Python changes take effect on restart.
Use `NIIMSTUDIO_DEBUG=1 ./scripts/niimstudio` for the WebKit inspector and logs.
The launcher prefers system Python with GI; `NIIMSTUDIO_PYTHON=/path/to/python`
overrides that choice. No Python pip packages are needed by the app itself.

For actual GUI snapshots and independent decoding of the rendered codes:

```bash
NIIMSTUDIO_TEST_ARTIFACTS="$PWD/.test-results/omarchy" \
NIIMSTUDIO_SNAPSHOT="$PWD/.test-results/workspace.png" \
NIIMSTUDIO_DEMO=1 ./scripts/niimstudio --smoke-test
uv run scripts/verify-code-scans.py .test-results/omarchy

# Exercise native appearance without changing desktop settings:
NIIMSTUDIO_THEME=gtk ADW_DEBUG_COLOR_SCHEME=prefer-light \
./scripts/niimstudio --smoke-test
```

Snapshot/artifact directories are created automatically. `uv` downloads
isolated, pinned decoder-test dependencies; Pillow/ZXing are not app dependencies.
Smoke profiles are temporary and disable real connect/write/pair/scan operations;
the chooser can open and be dismissed to verify cancellation behavior. Screenshots
use synthetic labels, never the real saved library.

## Release packaging

```bash
npm run check
npm run package:release
npm run test:install
```

`scripts/package-release.py` packages built assets and dependency notices into
`.release/niimstudio-linux.tar.gz`, plus an installer and SHA256SUMS. It needs the
locked node_modules for notices; end users do not need Node. `test:install` uses
an isolated HOME (including spaces), installs/reinstalls the actual bundle and
uninstalls it while asserting label data is retained. The `--version`, `--update`,
and `--uninstall` launcher paths do not import GTK and still work with broken GI.

Release CI builds the Flatpak manifest in `packaging/flatpak/` on x86-64/ARM64,
runs the real UI smoke test inside the sandbox, and publishes only after success.
Use **Package validation** (`package-validation.yml`, workflow_dispatch) to test
packaging without a release. **Release** runs only for version tags and reuses
those same checks before publishing. To publish, ensure
package.json/native version agree, update release notes, and push `v<version>`.
Do not retag or overwrite an existing release. No actual printer commands run in
release tests. Generated `.release/` and `.flatpak-*` directories stay ignored.

## Safety and support claims

Never run NiimStudio as root, disable WebKit's sandbox, replace the desktop's
default Bluetooth agent, broaden device permissions, flash firmware, or print
test labels without an explicit user action. Reconnect must not replay jobs.
Review [hardware acceptance](docs/HARDWARE.md) before claiming model/transport
support. Never attach unredacted personal labels or packet logs to public issues.
Document code structure in [architecture](docs/ARCHITECTURE.md), user-visible
changes in [status](docs/STATUS.md), and upstream base changes in [attribution](docs/UPSTREAM.md).
