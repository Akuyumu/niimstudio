# Unreleased

- Startup auto-reconnect is capped at five attempts instead of looping indefinitely.
- A visible `Auto-connecting… / Retrying in Ns` indicator now provides Cancel and
  opens Devices, including a native generation-safe cancel operation.
- Devices remains available during automatic connection attempts; only an active
  print job disables it. Automatic retry exhaustion is reported with a clear action.
- The editor starts at a computed fit zoom instead of a hardcoded 200%, so the whole
  label and its true aspect ratio are visible. The zoom control now returns to Fit.
- When zoomed in, a “Space+drag to see the full label” note distinguishes a cropped
  view from an incorrectly sized label. The large bordered stage is the pan area;
  Space+left-drag pans without using middle-click. Even a fully visible label can
  move within the empty stage space; Fit recenters it.
- Opening Devices while connected keeps the current link active. Closing the chooser
  changes nothing; selecting another device switches only after that explicit choice.

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
