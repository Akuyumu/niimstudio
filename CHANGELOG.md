# NiimStudio 0.3.1

Stable patch release. Includes the full model media-width audit and the B21S fix
confirmed after v0.3.0.

- Treat physical media width separately from printable head width for every model
  in the pinned NIIMBOT library. The documented head classes expose their real
  stock range: 12→15 mm, 24→25 mm, 48/50→50 mm, 56→60 mm, 72→75 mm, 80→82 mm and
  104→108 mm, with model-specific exceptions such as B1 SE (54 mm), M3 (78 mm),
  B31 (77 mm) and T2S (107 mm).
- This restores 50×30 mm stock for all 2-inch models (including B21S), 60×40 mm
  for K2 and the larger presets for 3-/4-inch printers. Reported rolls auto-detect
  with the printable canvas capped at the real head width and an edge-margin notice.

# NiimStudio 0.3.0

Stable release. Includes the printer and stock work from v0.2.0, plus the reconnect,
device-switching and canvas-navigation improvements below. v0.2.0 remains the
previous stable release.

- Startup auto-reconnect is capped at five attempts instead of looping indefinitely.
- A visible `Auto-connecting… / Retrying in Ns` indicator provides Cancel and opens
  Devices, including a native generation-safe cancel operation.
- Devices remains available during automatic connection attempts; only an active
  print job disables it. Retry exhaustion is reported with a clear action.
- Opening Devices while connected keeps the current link active. Closing the chooser
  changes nothing; selecting another device switches only after that explicit choice.
- Devices shows the current auto-connect target with a **Forget** action. It removes
  that printer name plus its USB/BLE variants from remembered history and stops
  auto-connect attempts without disconnecting the current printer.
- The editor starts at a computed fit zoom instead of a hardcoded 200%, so the whole
  label and its true aspect ratio are visible. Fit tracks window size changes.
- The large stage is the pan area. Space+left-drag moves the label, including when it
  is already fully visible; Ctrl+scroll zooms. No middle-click gesture is used.
- The redundant dotted viewport border was removed; a caption indicates when the
  current zoom is showing only part of the label.

# NiimStudio 0.2.0

Stable release; v0.1.3 remains available as the previous stable version.

- Reliable B1 Pro BLE discovery, one bounded transient retry, and clearer connection feedback.
- Connect is the normal action; Pair appears only after an authentication failure.
- Verified sound/sleep controls, hidden unavailable settings, inline confirmation.
- Correct B1 Pro label-height interpretation: 30 mm is not reduced by the separate 6 mm gap field.
- Explicit, session-scoped stock override and correctly available 50 mm stock presets.
- Simple print preview, Advanced tooltips, safe setup-failure recovery and offset validation.
- Sharper display zoom, expanding font picker and aligned transport-neutral Devices controls.
- Separate candidate/stable publication and update protections. Release automation
  performs no physical print; the user later confirmed successful B1 Pro prints over
  both USB and Bluetooth LE.

## Inherited NiimBlue changelog

# 2026.9.0

* Add changelog (starts from commit 48ce74).
* Add dual color printing support:.
  - Add red color to vector objects.
  - Add red/black threshold post-processing.
* Use single PrintStart/PrintEnd session for multi-page printing.
* Fix print progress calculation.
* Display more characteristics at the printer info menu.
* Fix status poll not stopped sometimes.
* Fix version detection for non-very-old printer models.
* Fail on connecting to a non-printer port.
* Add send progress (on printing).
* Printer menu rework:
  - Strings are i18n now.
  - Menu now display most important things.
  - Details moved to separate menu.
  - RFID usage progress bars.
  - RFID paper type and dimensions (for modern printers).
  - Sound settings sliders.
* Add datetime duration parsing (example: `{dt+3d}`, `{dt-3h}`, `{dt+1w|YYYY-MM-DD}`).
