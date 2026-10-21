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
  performs no physical print; a user later confirmed one successful B1 Pro print
  (transport and label details not recorded).

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
