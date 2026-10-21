---
name: Bug report
about: Report a reproducible problem with NiimStudio
title: ''
labels: bug
assignees: ''

---

### What happened?

<!-- Describe the problem and what you expected instead. -->

### Steps to reproduce

1.
2.
3.

### Printer and connection

- **Printer model:**
- **Transport:** USB / Bluetooth LE / offline
- **Connection state:** connected / disconnected / failed during connect
- **Firmware, if visible:** <!-- Settings → Printer and roll details -->
- **Label stock:** <!-- e.g. 50 × 30 mm, or "detected"; do not guess -->

<details>
<summary>Printer and roll details (optional)</summary>

```
Paste Settings → Printer and roll details here if relevant.
This section omits printer/roll serials, tag UUIDs and label artwork.
```
</details>

### Environment

- **NiimStudio version:** <!-- `niimstudio --version` -->
- **Install type:** native / Flatpak / source checkout
- **Distribution and desktop:**
- **Omarchy or system GTK appearance:**
- **Does it also happen in upstream NiimBlue?** yes / no / not tested

### Logs

For a source checkout:

```bash
NIIMSTUDIO_DEBUG=1 ./scripts/niimstudio
```

For a managed native install:

```bash
NIIMSTUDIO_DEBUG=1 ~/.local/bin/niimstudio
```

For Flatpak:

```bash
flatpak run --env=NIIMSTUDIO_DEBUG=1 io.github.niimstudio.App
```

<details>
<summary>Logs</summary>

```
Paste relevant logs here. Redact Bluetooth addresses, serial numbers, RFID/roll
identifiers, personal text, and anything else you do not want public.
```
</details>

### Label or screenshot

A minimal synthetic label or screenshot is usually enough. **Do not attach a real
private label or an unredacted packet capture.** Export JSON only after removing
personal content.

### Additional context

<!-- Recent changes, workarounds, or whether this started after an update. -->
